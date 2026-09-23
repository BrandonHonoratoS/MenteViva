"""Capa de datos de Mente Viva: SQLite en disco persistente (WAL), esquema y helpers.

Convenciones
- Fechas en ISO-8601 UTC (`now()`); el periodo mensual es 'YYYY-MM'.
- Los JSON se guardan como texto y se decodifican en `_row()`.
- Todo cambio de estado sensible (aprobaciones, ascensos, presupuesto) queda en `bitacora`.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from .config import settings

_LOCK = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS empresas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    industria TEXT DEFAULT '',
    activa INTEGER DEFAULT 1,
    habilidades_json TEXT DEFAULT '[]',      -- habilidades personalizadas habilitadas (p. ej. ruta_dm)
    config_json TEXT DEFAULT '{}',
    creado_en TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS areas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    nombre TEXT NOT NULL,
    director_id INTEGER,
    creado_en TEXT NOT NULL,
    UNIQUE(empresa_id, nombre)
);
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER REFERENCES empresas(id),
    area_id INTEGER REFERENCES areas(id),
    email TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    puesto TEXT DEFAULT '',
    rol TEXT NOT NULL,                       -- superadmin | dg | rrhh | director | colaborador
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    activo INTEGER DEFAULT 1,
    debe_cambiar_password INTEGER DEFAULT 1,
    color TEXT DEFAULT '',
    creado_en TEXT NOT NULL,
    ultimo_acceso TEXT
);
CREATE TABLE IF NOT EXISTS sesiones_auth (
    token TEXT PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    csrf TEXT NOT NULL,
    expira_en TEXT NOT NULL,
    creado_en TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS intentos_acceso (clave TEXT NOT NULL, momento REAL NOT NULL);
CREATE INDEX IF NOT EXISTS ix_intentos ON intentos_acceso(clave, momento);

CREATE TABLE IF NOT EXISTS perfiles (
    usuario_id INTEGER PRIMARY KEY REFERENCES usuarios(id),
    onboarding_json TEXT DEFAULT '{}',       -- variables declaradas (chips)
    diagnostico_json TEXT DEFAULT '{}',      -- resultado de la entrevista de Elena
    estado TEXT DEFAULT 'pendiente',         -- pendiente | onboarding | entrevista | analizando | completo
    sesion_diagnostico_id INTEGER,
    actualizado_en TEXT
);
CREATE TABLE IF NOT EXISTS niveles (
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    habilidad TEXT NOT NULL,
    nivel TEXT NOT NULL,
    score_inicial REAL,
    score_actual REAL,
    sesiones INTEGER DEFAULT 0,
    sin_mejora INTEGER DEFAULT 0,
    historial_json TEXT DEFAULT '[]',
    competencias_json TEXT DEFAULT '{}',     -- ruta DM: dominio por competencia
    actualizado_en TEXT,
    PRIMARY KEY (usuario_id, habilidad)
);
CREATE TABLE IF NOT EXISTS roadmaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    habilidad TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'propuesto',   -- propuesto | activo | pausado | completado | rechazado
    nivel_inicio TEXT,
    objetivo TEXT DEFAULT '',
    razon TEXT DEFAULT '',
    horizonte_semanas INTEGER DEFAULT 6,
    sesiones_semana INTEGER DEFAULT 2,
    version INTEGER DEFAULT 1,
    ajustes INTEGER DEFAULT 0,
    requiere_aprobacion INTEGER DEFAULT 0,
    aprobado_por INTEGER,
    creado_en TEXT NOT NULL,
    actualizado_en TEXT
);
CREATE TABLE IF NOT EXISTS roadmap_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    roadmap_id INTEGER NOT NULL REFERENCES roadmaps(id),
    orden INTEGER NOT NULL,
    semana INTEGER NOT NULL,
    tipo TEXT DEFAULT 'sesion',              -- sesion | refuerzo
    nivel TEXT,
    competencia TEXT DEFAULT '',
    formato TEXT DEFAULT '',
    objetivo TEXT DEFAULT '',
    porque TEXT DEFAULT '',
    estado TEXT DEFAULT 'pendiente',         -- pendiente | completada | omitida
    sesion_id INTEGER,
    agregado_por TEXT DEFAULT 'elena',
    creado_en TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_items_roadmap ON roadmap_items(roadmap_id, orden);

CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    habilidad TEXT NOT NULL,
    agente TEXT NOT NULL,                    -- elena | celeste | juan
    tipo TEXT NOT NULL DEFAULT 'practica',   -- diagnostico | practica
    roadmap_item_id INTEGER,
    nivel TEXT,
    competencia TEXT DEFAULT '',
    formato TEXT DEFAULT '',
    objetivo TEXT DEFAULT '',
    escenario_json TEXT DEFAULT '{}',
    resumen_json TEXT DEFAULT '{}',          -- memoria comprimida de la conversación
    estado TEXT NOT NULL DEFAULT 'en_curso', -- en_curso | analizando | completada | descartada | error
    inicio TEXT NOT NULL,
    fin TEXT,
    turnos INTEGER DEFAULT 0,
    tension_max INTEGER DEFAULT 0,
    score_global REAL,
    resultado_json TEXT DEFAULT '{}',
    error TEXT DEFAULT '',
    voluntaria INTEGER DEFAULT 0,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    costo_usd REAL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_sesiones_usuario ON sesiones(usuario_id, inicio);
CREATE TABLE IF NOT EXISTS mensajes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id INTEGER NOT NULL REFERENCES sesiones(id),
    rol TEXT NOT NULL,                       -- usuario | avatar | sistema
    texto TEXT NOT NULL,
    meta_json TEXT DEFAULT '{}',
    creado_en TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_mensajes_sesion ON mensajes(sesion_id, id);

CREATE TABLE IF NOT EXISTS evaluaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,                      -- lider | auto
    evaluador_id INTEGER NOT NULL REFERENCES usuarios(id),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    periodo TEXT NOT NULL,
    respuestas_json TEXT NOT NULL,
    promedio REAL,
    comentario TEXT DEFAULT '',
    creado_en TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS metas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    area_id INTEGER,
    usuario_id INTEGER,
    habilidad TEXT NOT NULL,
    competencia TEXT DEFAULT '',
    score_minimo REAL DEFAULT 75,
    plazo TEXT,
    prioridad TEXT DEFAULT 'media',
    descripcion TEXT DEFAULT '',
    creado_por INTEGER,
    estado TEXT DEFAULT 'activa',
    creado_en TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS propuestas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    usuario_id INTEGER REFERENCES usuarios(id),
    tipo TEXT NOT NULL,                      -- ascenso_dm | roadmap | refuerzo | alerta | ajuste
    titulo TEXT NOT NULL,
    detalle_json TEXT DEFAULT '{}',
    evidencia TEXT DEFAULT '',
    estado TEXT DEFAULT 'pendiente',         -- pendiente | aprobada | rechazada | atendida
    clave TEXT DEFAULT '',
    creado_por TEXT DEFAULT 'analista',
    decidido_por INTEGER,
    decidido_en TEXT,
    motivo TEXT DEFAULT '',
    creado_en TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_propuestas_empresa ON propuestas(empresa_id, estado);
CREATE TABLE IF NOT EXISTS analisis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    usuario_id INTEGER,
    area_id INTEGER,
    sesion_id INTEGER,
    tipo TEXT NOT NULL,                      -- post_sesion | semanal | area | organizacion | investigacion
    titulo TEXT NOT NULL,
    contenido_json TEXT DEFAULT '{}',
    fuentes_json TEXT DEFAULT '[]',
    creado_en TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_analisis ON analisis(empresa_id, tipo, creado_en);
CREATE TABLE IF NOT EXISTS notificaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    titulo TEXT NOT NULL,
    cuerpo TEXT DEFAULT '',
    enlace TEXT DEFAULT '',
    tipo TEXT DEFAULT 'info',
    leida INTEGER DEFAULT 0,
    creado_en TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_notif ON notificaciones(usuario_id, leida);
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    ambito TEXT NOT NULL,                    -- analista | reporte:<sesion_id>
    titulo TEXT DEFAULT '',
    creado_en TEXT NOT NULL,
    actualizado_en TEXT
);
CREATE TABLE IF NOT EXISTS chat_mensajes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL REFERENCES chats(id),
    rol TEXT NOT NULL,
    texto TEXT NOT NULL,
    meta_json TEXT DEFAULT '{}',
    creado_en TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS uso_llm (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    momento TEXT NOT NULL,
    periodo TEXT NOT NULL,
    modelo TEXT NOT NULL,
    origen TEXT NOT NULL,
    usuario_id INTEGER,
    tok_in INTEGER DEFAULT 0,
    tok_out INTEGER DEFAULT 0,
    tok_think INTEGER DEFAULT 0,
    tok_cache INTEGER DEFAULT 0,
    grounded INTEGER DEFAULT 0,
    costo_usd REAL DEFAULT 0,
    ms INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_uso_periodo ON uso_llm(periodo);
CREATE TABLE IF NOT EXISTS ajustes (clave TEXT PRIMARY KEY, valor TEXT NOT NULL, actualizado_en TEXT);
CREATE TABLE IF NOT EXISTS bitacora (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    momento TEXT NOT NULL,
    nivel TEXT NOT NULL,
    origen TEXT NOT NULL,
    evento TEXT NOT NULL,
    detalle TEXT DEFAULT '',
    usuario TEXT DEFAULT ''
);
"""

JSON_COLS = {"habilidades_json", "config_json", "onboarding_json", "diagnostico_json", "historial_json", "competencias_json",
             "escenario_json", "resumen_json", "resultado_json", "respuestas_json", "detalle_json", "contenido_json",
             "fuentes_json", "meta_json"}
LIST_COLS = {"habilidades_json", "historial_json", "fuentes_json"}


# ── conexión ─────────────────────────────────────────────────────────────────
def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(settings.DB_PATH, timeout=30, check_same_thread=False, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    return con


@contextmanager
def conn():
    con = _connect()
    try:
        con.execute("BEGIN")
        yield con
        if con.in_transaction:
            con.execute("COMMIT")
    except Exception:
        try:
            if con.in_transaction:
                con.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        con.close()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def periodo(ts: str | None = None) -> str:
    d = datetime.fromisoformat(ts) if ts else datetime.now(timezone.utc)
    return d.strftime("%Y-%m")


def _row(r: sqlite3.Row | None) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    for k in list(d):
        if k in JSON_COLS and isinstance(d[k], str):
            vacio: Any = [] if k in LIST_COLS else {}
            try:
                d[k[:-5]] = json.loads(d[k]) if d[k] else vacio
            except json.JSONDecodeError:
                d[k[:-5]] = vacio
    return d


def _rows(rs: Iterable[sqlite3.Row]) -> list[dict]:
    return [_row(r) for r in rs]


def _j(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


def init_db() -> None:
    """Crea el esquema, el superadministrador y (si se configuró) la empresa inicial."""
    with _LOCK, conn() as con:
        con.executescript(SCHEMA)
        if con.execute("SELECT COUNT(*) c FROM usuarios WHERE rol='superadmin'").fetchone()["c"] == 0:
            crear_usuario(settings.SUPERADMIN_EMAIL, settings.SUPERADMIN_PASSWORD, settings.SUPERADMIN_NOMBRE,
                          "superadmin", empresa_id=None, debe_cambiar=False, _con=con)
        if settings.EMPRESA_INICIAL and con.execute("SELECT COUNT(*) c FROM empresas").fetchone()["c"] == 0:
            eid = con.execute("INSERT INTO empresas (nombre, creado_en, habilidades_json) VALUES (?,?,?)",
                              (settings.EMPRESA_INICIAL, now(), _j(["ruta_dm"]))).lastrowid
            if settings.RRHH_INICIAL_EMAIL and settings.RRHH_INICIAL_PASSWORD:
                crear_usuario(settings.RRHH_INICIAL_EMAIL, settings.RRHH_INICIAL_PASSWORD, settings.RRHH_INICIAL_NOMBRE,
                              "rrhh", empresa_id=eid, debe_cambiar=True, _con=con)
    log("info", "sistema", "Base de datos lista", str(settings.DB_PATH))


# ── usuarios y autenticación ─────────────────────────────────────────────────
def _hash(password: str, salt: str) -> str:
    return hashlib.scrypt(password.encode(), salt=salt.encode(), n=2 ** 14, r=8, p=1).hex()


COLORES = ["#7C3AED", "#06B6D4", "#10B981", "#F59E0B", "#EC4899", "#3B82F6", "#8B5CF6", "#14B8A6", "#F97316", "#6366F1"]


def crear_usuario(email: str, password: str, nombre: str, rol: str, empresa_id: int | None, area_id: int | None = None,
                  puesto: str = "", debe_cambiar: bool = True, _con: sqlite3.Connection | None = None) -> int:
    salt = secrets.token_hex(16)
    color = COLORES[sum(map(ord, email)) % len(COLORES)]
    sql = ("INSERT INTO usuarios (empresa_id, area_id, email, nombre, puesto, rol, password_hash, salt, debe_cambiar_password, color, creado_en) "
           "VALUES (?,?,?,?,?,?,?,?,?,?,?)")
    args = (empresa_id, area_id, email.strip().lower(), nombre.strip() or email, puesto, rol, _hash(password, salt), salt,
            1 if debe_cambiar else 0, color, now())
    if _con is not None:
        uid = _con.execute(sql, args).lastrowid
        _con.execute("INSERT OR IGNORE INTO perfiles (usuario_id, actualizado_en) VALUES (?,?)", (uid, now()))
        return uid
    with conn() as con:
        uid = con.execute(sql, args).lastrowid
        con.execute("INSERT OR IGNORE INTO perfiles (usuario_id, actualizado_en) VALUES (?,?)", (uid, now()))
        return uid


def verificar_credenciales(email: str, password: str) -> dict | None:
    with conn() as con:
        u = con.execute("SELECT * FROM usuarios WHERE email=? AND activo=1", (email.strip().lower(),)).fetchone()
    if not u:
        _hash(password or "", "0" * 32)   # tiempo constante
        return None
    if secrets.compare_digest(_hash(password, u["salt"]), u["password_hash"]):
        return dict(u)
    return None


def cambiar_password(usuario_id: int, password: str) -> None:
    salt = secrets.token_hex(16)
    with conn() as con:
        con.execute("UPDATE usuarios SET password_hash=?, salt=?, debe_cambiar_password=0 WHERE id=?", (_hash(password, salt), salt, usuario_id))


def intentos_recientes(clave: str, ventana_min: int) -> int:
    limite = time.time() - ventana_min * 60
    with conn() as con:
        con.execute("DELETE FROM intentos_acceso WHERE momento < ?", (limite - 3600,))
        return int(con.execute("SELECT COUNT(*) c FROM intentos_acceso WHERE clave=? AND momento>=?", (clave, limite)).fetchone()["c"])


def registrar_intento(clave: str) -> None:
    with conn() as con:
        con.execute("INSERT INTO intentos_acceso (clave, momento) VALUES (?,?)", (clave, time.time()))


def limpiar_intentos(clave: str) -> None:
    with conn() as con:
        con.execute("DELETE FROM intentos_acceso WHERE clave=?", (clave,))


def crear_sesion_auth(usuario_id: int, horas: int = 12) -> tuple[str, str]:
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
    with conn() as con:
        con.execute("INSERT INTO sesiones_auth (token, usuario_id, csrf, expira_en, creado_en) VALUES (?,?,?,?,?)",
                    (token, usuario_id, csrf, (datetime.now(timezone.utc) + timedelta(hours=horas)).isoformat(), now()))
        con.execute("UPDATE usuarios SET ultimo_acceso=? WHERE id=?", (now(), usuario_id))
        con.execute("DELETE FROM sesiones_auth WHERE expira_en < ?", (now(),))
    return token, csrf


def usuario_por_token(token: str) -> dict | None:
    if not token:
        return None
    with conn() as con:
        r = con.execute("SELECT u.*, s.expira_en, s.csrf, a.nombre AS area_nombre, e.nombre AS empresa_nombre FROM sesiones_auth s "
                        "JOIN usuarios u ON u.id=s.usuario_id LEFT JOIN areas a ON a.id=u.area_id LEFT JOIN empresas e ON e.id=u.empresa_id "
                        "WHERE s.token=? AND u.activo=1", (token,)).fetchone()
    if not r:
        return None
    if datetime.fromisoformat(r["expira_en"]) < datetime.now(timezone.utc):
        cerrar_sesion_auth(token)
        return None
    return dict(r)


def cerrar_sesion_auth(token: str) -> None:
    with conn() as con:
        con.execute("DELETE FROM sesiones_auth WHERE token=?", (token,))


def usuario(id_: int) -> dict | None:
    with conn() as con:
        return _row(con.execute("SELECT u.*, a.nombre AS area_nombre, e.nombre AS empresa_nombre FROM usuarios u "
                                "LEFT JOIN areas a ON a.id=u.area_id LEFT JOIN empresas e ON e.id=u.empresa_id WHERE u.id=?", (id_,)).fetchone())


def usuarios(empresa_id: int | None = None, area_id: int | None = None, rol: str | None = None, activos: bool | None = True) -> list[dict]:
    q = ("SELECT u.*, a.nombre AS area_nombre FROM usuarios u LEFT JOIN areas a ON a.id=u.area_id WHERE 1=1")
    args: list = []
    if empresa_id is not None:
        q += " AND u.empresa_id=?"; args.append(empresa_id)
    if area_id is not None:
        q += " AND u.area_id=?"; args.append(area_id)
    if rol:
        q += " AND u.rol=?"; args.append(rol)
    if activos is not None:
        q += " AND u.activo=?"; args.append(1 if activos else 0)
    q += " ORDER BY u.nombre"
    with conn() as con:
        return _rows(con.execute(q, args))


def actualizar_usuario(id_: int, **campos) -> None:
    permitidos = {"nombre", "puesto", "rol", "area_id", "activo", "empresa_id", "email"}
    campos = {k: v for k, v in campos.items() if k in permitidos}
    if not campos:
        return
    sets = ", ".join(f"{k}=?" for k in campos)
    with conn() as con:
        con.execute(f"UPDATE usuarios SET {sets} WHERE id=?", (*campos.values(), id_))


# ── empresas y áreas ─────────────────────────────────────────────────────────
def crear_empresa(nombre: str, industria: str = "", habilidades: list[str] | None = None) -> int:
    with conn() as con:
        return con.execute("INSERT INTO empresas (nombre, industria, habilidades_json, creado_en) VALUES (?,?,?,?)",
                           (nombre.strip(), industria, _j(habilidades or []), now())).lastrowid


def empresa(id_: int | None) -> dict | None:
    if id_ is None:
        return None
    with conn() as con:
        return _row(con.execute("SELECT * FROM empresas WHERE id=?", (id_,)).fetchone())


def empresas() -> list[dict]:
    with conn() as con:
        return _rows(con.execute("SELECT e.*, (SELECT COUNT(*) FROM usuarios u WHERE u.empresa_id=e.id AND u.activo=1) AS usuarios "
                                 "FROM empresas e ORDER BY e.nombre"))


def actualizar_empresa(id_: int, **campos) -> None:
    permitidos = {"nombre", "industria", "activa", "habilidades_json", "config_json"}
    campos = {k: (_j(v) if k.endswith("_json") and not isinstance(v, str) else v) for k, v in campos.items() if k in permitidos}
    if not campos:
        return
    with conn() as con:
        con.execute(f"UPDATE empresas SET {', '.join(f'{k}=?' for k in campos)} WHERE id=?", (*campos.values(), id_))


def crear_area(empresa_id: int, nombre: str, director_id: int | None = None) -> int:
    with conn() as con:
        aid = con.execute("INSERT INTO areas (empresa_id, nombre, director_id, creado_en) VALUES (?,?,?,?)",
                          (empresa_id, nombre.strip(), director_id, now())).lastrowid
        if director_id:
            con.execute("UPDATE usuarios SET area_id=? WHERE id=?", (aid, director_id))
        return aid


def areas(empresa_id: int) -> list[dict]:
    with conn() as con:
        return _rows(con.execute(
            "SELECT a.*, d.nombre AS director_nombre, "
            "(SELECT COUNT(*) FROM usuarios u WHERE u.area_id=a.id AND u.activo=1 AND u.rol='colaborador') AS colaboradores "
            "FROM areas a LEFT JOIN usuarios d ON d.id=a.director_id WHERE a.empresa_id=? ORDER BY a.nombre", (empresa_id,)))


def area(id_: int | None) -> dict | None:
    if id_ is None:
        return None
    with conn() as con:
        return _row(con.execute("SELECT a.*, d.nombre AS director_nombre FROM areas a LEFT JOIN usuarios d ON d.id=a.director_id WHERE a.id=?", (id_,)).fetchone())


def actualizar_area(id_: int, nombre: str | None = None, director_id: int | None = None) -> None:
    with conn() as con:
        if nombre:
            con.execute("UPDATE areas SET nombre=? WHERE id=?", (nombre.strip(), id_))
        if director_id is not None:
            con.execute("UPDATE areas SET director_id=? WHERE id=?", (director_id or None, id_))
            if director_id:
                con.execute("UPDATE usuarios SET area_id=? WHERE id=?", (id_, director_id))


# ── perfiles y niveles ───────────────────────────────────────────────────────
def perfil(usuario_id: int) -> dict:
    with conn() as con:
        r = _row(con.execute("SELECT * FROM perfiles WHERE usuario_id=?", (usuario_id,)).fetchone())
    if not r:
        with conn() as con:
            con.execute("INSERT OR IGNORE INTO perfiles (usuario_id, actualizado_en) VALUES (?,?)", (usuario_id, now()))
        return {"usuario_id": usuario_id, "onboarding": {}, "diagnostico": {}, "estado": "pendiente", "sesion_diagnostico_id": None}
    return r


def guardar_perfil(usuario_id: int, onboarding: dict | None = None, diagnostico: dict | None = None,
                   estado: str | None = None, sesion_diagnostico_id: int | None = None) -> None:
    with conn() as con:
        con.execute("INSERT OR IGNORE INTO perfiles (usuario_id, actualizado_en) VALUES (?,?)", (usuario_id, now()))
        if onboarding is not None:
            con.execute("UPDATE perfiles SET onboarding_json=? WHERE usuario_id=?", (_j(onboarding), usuario_id))
        if diagnostico is not None:
            con.execute("UPDATE perfiles SET diagnostico_json=? WHERE usuario_id=?", (_j(diagnostico), usuario_id))
        if estado is not None:
            con.execute("UPDATE perfiles SET estado=? WHERE usuario_id=?", (estado, usuario_id))
        if sesion_diagnostico_id is not None:
            con.execute("UPDATE perfiles SET sesion_diagnostico_id=? WHERE usuario_id=?", (sesion_diagnostico_id, usuario_id))
        con.execute("UPDATE perfiles SET actualizado_en=? WHERE usuario_id=?", (now(), usuario_id))


def nivel(usuario_id: int, habilidad: str) -> dict | None:
    with conn() as con:
        return _row(con.execute("SELECT * FROM niveles WHERE usuario_id=? AND habilidad=?", (usuario_id, habilidad)).fetchone())


def niveles(usuario_id: int) -> dict[str, dict]:
    with conn() as con:
        return {r["habilidad"]: r for r in _rows(con.execute("SELECT * FROM niveles WHERE usuario_id=?", (usuario_id,)))}


def guardar_nivel(usuario_id: int, habilidad: str, nivel_: str, score_inicial: float | None = None, motivo: str = "",
                  competencias: dict | None = None) -> None:
    with conn() as con:
        r = _row(con.execute("SELECT * FROM niveles WHERE usuario_id=? AND habilidad=?", (usuario_id, habilidad)).fetchone())
        if r is None:
            con.execute("INSERT INTO niveles (usuario_id, habilidad, nivel, score_inicial, score_actual, historial_json, competencias_json, actualizado_en) "
                        "VALUES (?,?,?,?,?,?,?,?)",
                        (usuario_id, habilidad, nivel_, score_inicial, score_inicial,
                         _j([{"momento": now(), "nivel": nivel_, "motivo": motivo or "diagnóstico inicial"}]), _j(competencias or {}), now()))
        else:
            hist = r["historial"] if isinstance(r.get("historial"), list) else []
            if r["nivel"] != nivel_:
                hist.append({"momento": now(), "nivel": nivel_, "motivo": motivo, "anterior": r["nivel"]})
            comp = r.get("competencias") or {}
            if competencias:
                comp.update(competencias)
            con.execute("UPDATE niveles SET nivel=?, historial_json=?, competencias_json=?, actualizado_en=?, "
                        "score_inicial=COALESCE(score_inicial, ?) WHERE usuario_id=? AND habilidad=?",
                        (nivel_, _j(hist), _j(comp), now(), score_inicial, usuario_id, habilidad))


def actualizar_nivel_stats(usuario_id: int, habilidad: str, score: float, sin_mejora: int) -> None:
    with conn() as con:
        con.execute("UPDATE niveles SET score_actual=?, sesiones=sesiones+1, sin_mejora=?, actualizado_en=?, "
                    "score_inicial=COALESCE(score_inicial, ?) WHERE usuario_id=? AND habilidad=?",
                    (score, sin_mejora, now(), score, usuario_id, habilidad))


# ── roadmaps ─────────────────────────────────────────────────────────────────
def crear_roadmap(usuario_id: int, habilidad: str, nivel_inicio: str, objetivo: str, razon: str, items: list[dict],
                  horizonte: int = 6, sesiones_semana: int = 2, requiere_aprobacion: bool = False, estado: str | None = None) -> int:
    with conn() as con:
        # un roadmap vigente por habilidad: los anteriores quedan 'completado' si no tenían pendientes, si no 'pausado'
        for r in con.execute("SELECT id FROM roadmaps WHERE usuario_id=? AND habilidad=? AND estado IN ('activo','propuesto')", (usuario_id, habilidad)):
            con.execute("UPDATE roadmaps SET estado='pausado', actualizado_en=? WHERE id=?", (now(), r["id"]))
        est = estado or ("propuesto" if requiere_aprobacion else "activo")
        rid = con.execute("INSERT INTO roadmaps (usuario_id, habilidad, estado, nivel_inicio, objetivo, razon, horizonte_semanas, sesiones_semana, "
                          "requiere_aprobacion, creado_en, actualizado_en) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                          (usuario_id, habilidad, est, nivel_inicio, objetivo, razon, horizonte, sesiones_semana, 1 if requiere_aprobacion else 0, now(), now())).lastrowid
        for i, it in enumerate(items, start=1):
            con.execute("INSERT INTO roadmap_items (roadmap_id, orden, semana, tipo, nivel, competencia, formato, objetivo, porque, agregado_por, creado_en) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (rid, i, int(it.get("semana", (i + 1) // 2) or 1), it.get("tipo", "sesion"), it.get("nivel", nivel_inicio),
                         it.get("competencia", ""), it.get("formato", ""), it.get("objetivo", ""), it.get("porque", ""), it.get("agregado_por", "elena"), now()))
        return rid


def roadmaps(usuario_id: int, estados: tuple = ("activo", "propuesto", "pausado", "completado")) -> list[dict]:
    with conn() as con:
        rs = _rows(con.execute(f"SELECT * FROM roadmaps WHERE usuario_id=? AND estado IN ({','.join('?' * len(estados))}) ORDER BY id DESC",
                               (usuario_id, *estados)))
        for r in rs:
            r["items"] = _rows(con.execute("SELECT * FROM roadmap_items WHERE roadmap_id=? ORDER BY orden", (r["id"],)))
            r["completadas"] = sum(1 for i in r["items"] if i["estado"] == "completada")
            r["total"] = len(r["items"])
        return rs


def roadmap(id_: int) -> dict | None:
    with conn() as con:
        r = _row(con.execute("SELECT * FROM roadmaps WHERE id=?", (id_,)).fetchone())
        if r:
            r["items"] = _rows(con.execute("SELECT * FROM roadmap_items WHERE roadmap_id=? ORDER BY orden", (id_,)))
        return r


def roadmap_activo(usuario_id: int, habilidad: str) -> dict | None:
    with conn() as con:
        r = _row(con.execute("SELECT * FROM roadmaps WHERE usuario_id=? AND habilidad=? AND estado='activo' ORDER BY id DESC LIMIT 1",
                             (usuario_id, habilidad)).fetchone())
        if r:
            r["items"] = _rows(con.execute("SELECT * FROM roadmap_items WHERE roadmap_id=? ORDER BY orden", (r["id"],)))
        return r


def siguiente_item(usuario_id: int, habilidad: str | None = None) -> dict | None:
    q = ("SELECT i.*, r.habilidad, r.usuario_id FROM roadmap_items i JOIN roadmaps r ON r.id=i.roadmap_id "
         "WHERE r.usuario_id=? AND r.estado='activo' AND i.estado='pendiente'")
    args: list = [usuario_id]
    if habilidad:
        q += " AND r.habilidad=?"; args.append(habilidad)
    q += " ORDER BY i.semana, i.orden LIMIT 1"
    with conn() as con:
        return _row(con.execute(q, args).fetchone())


def roadmap_item(id_: int) -> dict | None:
    with conn() as con:
        return _row(con.execute("SELECT i.*, r.habilidad, r.usuario_id, r.estado AS roadmap_estado FROM roadmap_items i "
                                "JOIN roadmaps r ON r.id=i.roadmap_id WHERE i.id=?", (id_,)).fetchone())


def actualizar_item(id_: int, **campos) -> None:
    permitidos = {"estado", "sesion_id", "objetivo", "nivel", "competencia", "formato", "porque", "semana"}
    campos = {k: v for k, v in campos.items() if k in permitidos}
    if not campos:
        return
    with conn() as con:
        con.execute(f"UPDATE roadmap_items SET {', '.join(f'{k}=?' for k in campos)} WHERE id=?", (*campos.values(), id_))


def insertar_item(roadmap_id: int, despues_de_orden: int, item: dict) -> int:
    with conn() as con:
        con.execute("UPDATE roadmap_items SET orden=orden+1 WHERE roadmap_id=? AND orden>?", (roadmap_id, despues_de_orden))
        iid = con.execute("INSERT INTO roadmap_items (roadmap_id, orden, semana, tipo, nivel, competencia, formato, objetivo, porque, agregado_por, creado_en) "
                          "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                          (roadmap_id, despues_de_orden + 1, item.get("semana", 1), item.get("tipo", "refuerzo"), item.get("nivel"),
                           item.get("competencia", ""), item.get("formato", ""), item.get("objetivo", ""), item.get("porque", ""),
                           item.get("agregado_por", "analista"), now())).lastrowid
        con.execute("UPDATE roadmaps SET ajustes=ajustes+1, version=version+1, actualizado_en=? WHERE id=?", (now(), roadmap_id))
        return iid


def actualizar_roadmap(id_: int, **campos) -> None:
    permitidos = {"estado", "objetivo", "razon", "aprobado_por", "ajustes", "version"}
    campos = {k: v for k, v in campos.items() if k in permitidos}
    if not campos:
        return
    with conn() as con:
        con.execute(f"UPDATE roadmaps SET {', '.join(f'{k}=?' for k in campos)}, actualizado_en=? WHERE id=?", (*campos.values(), now(), id_))


# ── sesiones de práctica ─────────────────────────────────────────────────────
def crear_sesion(usuario_id: int, habilidad: str, agente: str, tipo: str = "practica", roadmap_item_id: int | None = None,
                 nivel: str | None = None, competencia: str = "", formato: str = "", objetivo: str = "", escenario: dict | None = None,
                 voluntaria: bool = False) -> int:
    with conn() as con:
        return con.execute("INSERT INTO sesiones (usuario_id, habilidad, agente, tipo, roadmap_item_id, nivel, competencia, formato, objetivo, "
                           "escenario_json, inicio, voluntaria) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                           (usuario_id, habilidad, agente, tipo, roadmap_item_id, nivel, competencia, formato, objetivo, _j(escenario or {}), now(),
                            1 if voluntaria else 0)).lastrowid


def sesion(id_: int) -> dict | None:
    with conn() as con:
        return _row(con.execute("SELECT s.*, u.nombre AS usuario_nombre, u.area_id, u.empresa_id FROM sesiones s JOIN usuarios u ON u.id=s.usuario_id WHERE s.id=?", (id_,)).fetchone())


def sesiones(usuario_id: int | None = None, habilidad: str | None = None, estado: str | None = None, empresa_id: int | None = None,
             area_id: int | None = None, desde: str | None = None, limite: int = 500, tipo: str | None = None) -> list[dict]:
    q = "SELECT s.*, u.nombre AS usuario_nombre, u.area_id, u.empresa_id FROM sesiones s JOIN usuarios u ON u.id=s.usuario_id WHERE 1=1"
    args: list = []
    if usuario_id is not None:
        q += " AND s.usuario_id=?"; args.append(usuario_id)
    if habilidad:
        q += " AND s.habilidad=?"; args.append(habilidad)
    if estado:
        q += " AND s.estado=?"; args.append(estado)
    if tipo:
        q += " AND s.tipo=?"; args.append(tipo)
    if empresa_id is not None:
        q += " AND u.empresa_id=?"; args.append(empresa_id)
    if area_id is not None:
        q += " AND u.area_id=?"; args.append(area_id)
    if desde:
        q += " AND s.inicio>=?"; args.append(desde)
    q += " ORDER BY s.inicio DESC LIMIT ?"; args.append(limite)
    with conn() as con:
        return _rows(con.execute(q, args))


def sesion_en_curso(usuario_id: int) -> dict | None:
    with conn() as con:
        return _row(con.execute("SELECT * FROM sesiones WHERE usuario_id=? AND estado IN ('en_curso','analizando') ORDER BY id DESC LIMIT 1", (usuario_id,)).fetchone())


def actualizar_sesion(id_: int, **campos) -> None:
    permitidos = {"estado", "fin", "turnos", "tension_max", "score_global", "resultado_json", "resumen_json", "escenario_json", "error",
                  "nivel", "competencia", "formato", "objetivo", "roadmap_item_id"}
    campos = {k: (_j(v) if k.endswith("_json") and not isinstance(v, str) else v) for k, v in campos.items() if k in permitidos}
    if not campos:
        return
    with conn() as con:
        con.execute(f"UPDATE sesiones SET {', '.join(f'{k}=?' for k in campos)} WHERE id=?", (*campos.values(), id_))


def sumar_uso_sesion(id_: int, tok_in: int, tok_out: int, costo: float) -> None:
    with conn() as con:
        con.execute("UPDATE sesiones SET tokens_in=tokens_in+?, tokens_out=tokens_out+?, costo_usd=costo_usd+? WHERE id=?", (tok_in, tok_out, costo, id_))


def guardar_mensaje(sesion_id: int, rol: str, texto: str, meta: dict | None = None) -> int:
    with conn() as con:
        mid = con.execute("INSERT INTO mensajes (sesion_id, rol, texto, meta_json, creado_en) VALUES (?,?,?,?,?)",
                          (sesion_id, rol, texto, _j(meta or {}), now())).lastrowid
        if rol == "usuario":
            con.execute("UPDATE sesiones SET turnos=turnos+1 WHERE id=?", (sesion_id,))
        return mid


def mensajes(sesion_id: int, limite: int = 1000) -> list[dict]:
    with conn() as con:
        return _rows(con.execute("SELECT * FROM mensajes WHERE sesion_id=? ORDER BY id LIMIT ?", (sesion_id, limite)))


# ── evaluaciones (líder / auto) ──────────────────────────────────────────────
def guardar_evaluacion(tipo: str, evaluador_id: int, usuario_id: int, periodo_: str, respuestas: dict, comentario: str = "") -> int:
    vals = [float(v) for v in respuestas.values() if isinstance(v, (int, float)) or str(v).replace(".", "", 1).isdigit()]
    prom = round(sum(vals) / len(vals), 2) if vals else None
    with conn() as con:
        con.execute("DELETE FROM evaluaciones WHERE tipo=? AND evaluador_id=? AND usuario_id=? AND periodo=?", (tipo, evaluador_id, usuario_id, periodo_))
        return con.execute("INSERT INTO evaluaciones (tipo, evaluador_id, usuario_id, periodo, respuestas_json, promedio, comentario, creado_en) VALUES (?,?,?,?,?,?,?,?)",
                           (tipo, evaluador_id, usuario_id, periodo_, _j(respuestas), prom, comentario, now())).lastrowid


def evaluaciones(usuario_id: int | None = None, tipo: str | None = None, empresa_id: int | None = None, area_id: int | None = None) -> list[dict]:
    q = "SELECT e.*, u.nombre AS usuario_nombre, ev.nombre AS evaluador_nombre FROM evaluaciones e JOIN usuarios u ON u.id=e.usuario_id JOIN usuarios ev ON ev.id=e.evaluador_id WHERE 1=1"
    args: list = []
    if usuario_id is not None:
        q += " AND e.usuario_id=?"; args.append(usuario_id)
    if tipo:
        q += " AND e.tipo=?"; args.append(tipo)
    if empresa_id is not None:
        q += " AND u.empresa_id=?"; args.append(empresa_id)
    if area_id is not None:
        q += " AND u.area_id=?"; args.append(area_id)
    q += " ORDER BY e.periodo DESC, e.id DESC"
    with conn() as con:
        return _rows(con.execute(q, args))


# ── metas ────────────────────────────────────────────────────────────────────
def crear_meta(empresa_id: int, habilidad: str, creado_por: int, area_id: int | None = None, usuario_id: int | None = None,
               competencia: str = "", score_minimo: float = 75, plazo: str | None = None, prioridad: str = "media", descripcion: str = "") -> int:
    with conn() as con:
        return con.execute("INSERT INTO metas (empresa_id, area_id, usuario_id, habilidad, competencia, score_minimo, plazo, prioridad, descripcion, creado_por, creado_en) "
                           "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                           (empresa_id, area_id, usuario_id, habilidad, competencia, score_minimo, plazo, prioridad, descripcion, creado_por, now())).lastrowid


def metas(empresa_id: int, area_id: int | None = None, usuario_id: int | None = None, solo_activas: bool = True) -> list[dict]:
    q = ("SELECT m.*, a.nombre AS area_nombre, u.nombre AS usuario_nombre, c.nombre AS creador_nombre, c.rol AS creador_rol FROM metas m "
         "LEFT JOIN areas a ON a.id=m.area_id LEFT JOIN usuarios u ON u.id=m.usuario_id LEFT JOIN usuarios c ON c.id=m.creado_por WHERE m.empresa_id=?")
    args: list = [empresa_id]
    if area_id is not None:
        q += " AND (m.area_id=? OR m.area_id IS NULL)"; args.append(area_id)
    if usuario_id is not None:
        q += " AND (m.usuario_id=? OR m.usuario_id IS NULL)"; args.append(usuario_id)
    if solo_activas:
        q += " AND m.estado='activa'"
    q += " ORDER BY m.prioridad='alta' DESC, m.plazo"
    with conn() as con:
        return _rows(con.execute(q, args))


def cerrar_meta(id_: int, estado: str = "cerrada") -> None:
    with conn() as con:
        con.execute("UPDATE metas SET estado=? WHERE id=?", (estado, id_))


# ── propuestas del analista ──────────────────────────────────────────────────
def crear_propuesta(empresa_id: int, tipo: str, titulo: str, detalle: dict, evidencia: str = "", usuario_id: int | None = None,
                    clave: str = "", creado_por: str = "analista") -> int | None:
    with conn() as con:
        if clave and con.execute("SELECT 1 FROM propuestas WHERE clave=? AND estado='pendiente'", (clave,)).fetchone():
            return None
        return con.execute("INSERT INTO propuestas (empresa_id, usuario_id, tipo, titulo, detalle_json, evidencia, clave, creado_por, creado_en) VALUES (?,?,?,?,?,?,?,?,?)",
                           (empresa_id, usuario_id, tipo, titulo, _j(detalle), evidencia, clave, creado_por, now())).lastrowid


def propuestas(empresa_id: int, estado: str | None = "pendiente", usuario_id: int | None = None, area_id: int | None = None, tipo: str | None = None, limite: int = 200) -> list[dict]:
    q = ("SELECT p.*, u.nombre AS usuario_nombre, u.area_id, a.nombre AS area_nombre, d.nombre AS decisor_nombre FROM propuestas p "
         "LEFT JOIN usuarios u ON u.id=p.usuario_id LEFT JOIN areas a ON a.id=u.area_id LEFT JOIN usuarios d ON d.id=p.decidido_por WHERE p.empresa_id=?")
    args: list = [empresa_id]
    if estado:
        q += " AND p.estado=?"; args.append(estado)
    if usuario_id is not None:
        q += " AND p.usuario_id=?"; args.append(usuario_id)
    if area_id is not None:
        q += " AND u.area_id=?"; args.append(area_id)
    if tipo:
        q += " AND p.tipo=?"; args.append(tipo)
    q += " ORDER BY p.id DESC LIMIT ?"; args.append(limite)
    with conn() as con:
        return _rows(con.execute(q, args))


def propuesta(id_: int) -> dict | None:
    with conn() as con:
        return _row(con.execute("SELECT p.*, u.nombre AS usuario_nombre, u.area_id FROM propuestas p LEFT JOIN usuarios u ON u.id=p.usuario_id WHERE p.id=?", (id_,)).fetchone())


def decidir_propuesta(id_: int, estado: str, decidido_por: int, motivo: str = "") -> bool:
    with conn() as con:
        cur = con.execute("UPDATE propuestas SET estado=?, decidido_por=?, decidido_en=?, motivo=? WHERE id=? AND estado='pendiente'",
                          (estado, decidido_por, now(), motivo, id_))
        return cur.rowcount == 1


# ── análisis, notificaciones, chats ──────────────────────────────────────────
def guardar_analisis(empresa_id: int, tipo: str, titulo: str, contenido: dict, usuario_id: int | None = None, area_id: int | None = None,
                     sesion_id: int | None = None, fuentes: list | None = None) -> int:
    with conn() as con:
        return con.execute("INSERT INTO analisis (empresa_id, usuario_id, area_id, sesion_id, tipo, titulo, contenido_json, fuentes_json, creado_en) VALUES (?,?,?,?,?,?,?,?,?)",
                           (empresa_id, usuario_id, area_id, sesion_id, tipo, titulo, _j(contenido), _j(fuentes or []), now())).lastrowid


def analisis(empresa_id: int, tipo: str | None = None, usuario_id: int | None = None, area_id: int | None = None, sesion_id: int | None = None, limite: int = 100) -> list[dict]:
    q = "SELECT an.*, u.nombre AS usuario_nombre, a.nombre AS area_nombre FROM analisis an LEFT JOIN usuarios u ON u.id=an.usuario_id LEFT JOIN areas a ON a.id=an.area_id WHERE an.empresa_id=?"
    args: list = [empresa_id]
    if tipo:
        q += " AND an.tipo=?"; args.append(tipo)
    if usuario_id is not None:
        q += " AND an.usuario_id=?"; args.append(usuario_id)
    if area_id is not None:
        q += " AND (an.area_id=? OR u.area_id=?)"; args += [area_id, area_id]
    if sesion_id is not None:
        q += " AND an.sesion_id=?"; args.append(sesion_id)
    q += " ORDER BY an.id DESC LIMIT ?"; args.append(limite)
    with conn() as con:
        return _rows(con.execute(q, args))


def notificar(usuario_id: int, titulo: str, cuerpo: str = "", enlace: str = "", tipo: str = "info") -> None:
    with conn() as con:
        con.execute("INSERT INTO notificaciones (usuario_id, titulo, cuerpo, enlace, tipo, creado_en) VALUES (?,?,?,?,?,?)",
                    (usuario_id, titulo, cuerpo, enlace, tipo, now()))


def notificaciones(usuario_id: int, solo_no_leidas: bool = False, limite: int = 50) -> list[dict]:
    q = "SELECT * FROM notificaciones WHERE usuario_id=?"
    if solo_no_leidas:
        q += " AND leida=0"
    q += " ORDER BY id DESC LIMIT ?"
    with conn() as con:
        return _rows(con.execute(q, (usuario_id, limite)))


def marcar_leidas(usuario_id: int) -> None:
    with conn() as con:
        con.execute("UPDATE notificaciones SET leida=1 WHERE usuario_id=?", (usuario_id,))


def obtener_chat(usuario_id: int, ambito: str, titulo: str = "") -> dict:
    with conn() as con:
        r = _row(con.execute("SELECT * FROM chats WHERE usuario_id=? AND ambito=? ORDER BY id DESC LIMIT 1", (usuario_id, ambito)).fetchone())
        if r is None:
            cid = con.execute("INSERT INTO chats (usuario_id, ambito, titulo, creado_en, actualizado_en) VALUES (?,?,?,?,?)",
                              (usuario_id, ambito, titulo, now(), now())).lastrowid
            r = _row(con.execute("SELECT * FROM chats WHERE id=?", (cid,)).fetchone())
        r["mensajes"] = _rows(con.execute("SELECT * FROM chat_mensajes WHERE chat_id=? ORDER BY id", (r["id"],)))
        return r


def guardar_chat_mensaje(chat_id: int, rol: str, texto: str, meta: dict | None = None) -> None:
    with conn() as con:
        con.execute("INSERT INTO chat_mensajes (chat_id, rol, texto, meta_json, creado_en) VALUES (?,?,?,?,?)", (chat_id, rol, texto, _j(meta or {}), now()))
        con.execute("UPDATE chats SET actualizado_en=? WHERE id=?", (now(), chat_id))


def borrar_chat(usuario_id: int, ambito: str) -> None:
    with conn() as con:
        for r in con.execute("SELECT id FROM chats WHERE usuario_id=? AND ambito=?", (usuario_id, ambito)):
            con.execute("DELETE FROM chat_mensajes WHERE chat_id=?", (r["id"],))
            con.execute("DELETE FROM chats WHERE id=?", (r["id"],))


# ── uso de IA y presupuesto ──────────────────────────────────────────────────
def registrar_uso(modelo: str, origen: str, tok_in: int, tok_out: int, tok_think: int = 0, tok_cache: int = 0, grounded: bool = False,
                  costo_usd: float = 0.0, usuario_id: int | None = None, ms: int = 0) -> None:
    with conn() as con:
        con.execute("INSERT INTO uso_llm (momento, periodo, modelo, origen, usuario_id, tok_in, tok_out, tok_think, tok_cache, grounded, costo_usd, ms) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (now(), periodo(), modelo, origen, usuario_id, tok_in, tok_out, tok_think, tok_cache, 1 if grounded else 0, costo_usd, ms))


def uso_periodo(p: str | None = None) -> dict:
    p = p or periodo()
    with conn() as con:
        r = con.execute("SELECT COUNT(*) llamadas, COALESCE(SUM(tok_in),0) tok_in, COALESCE(SUM(tok_out),0) tok_out, COALESCE(SUM(tok_think),0) tok_think, "
                        "COALESCE(SUM(tok_cache),0) tok_cache, COALESCE(SUM(grounded),0) grounded, COALESCE(SUM(costo_usd),0) costo_usd FROM uso_llm WHERE periodo=?", (p,)).fetchone()
        por_origen = _rows(con.execute("SELECT origen, COUNT(*) llamadas, SUM(tok_in) tok_in, SUM(tok_out) tok_out, SUM(costo_usd) costo_usd FROM uso_llm WHERE periodo=? GROUP BY origen ORDER BY costo_usd DESC", (p,)))
        por_dia = _rows(con.execute("SELECT substr(momento,1,10) dia, SUM(costo_usd) costo_usd, COUNT(*) llamadas FROM uso_llm WHERE periodo=? GROUP BY dia ORDER BY dia", (p,)))
    d = dict(r)
    d.update(periodo=p, por_origen=por_origen, por_dia=por_dia)
    return d


def presupuesto() -> dict:
    mxn = float(get_ajuste("presupuesto_mxn", settings.PRESUPUESTO_MXN))
    tc = float(get_ajuste("tipo_cambio", settings.TIPO_CAMBIO_MXN_USD))
    uso = uso_periodo()
    gastado_mxn = uso["costo_usd"] * tc
    pct = (gastado_mxn / mxn * 100) if mxn > 0 else 100.0
    return {"presupuesto_mxn": mxn, "tipo_cambio": tc, "gastado_mxn": round(gastado_mxn, 2), "gastado_usd": round(uso["costo_usd"], 4),
            "pct": round(pct, 1), "aviso": pct >= settings.PRESUPUESTO_AVISO_PCT, "agotado": pct >= 100.0, "uso": uso,
            "grounded_mes": int(uso["grounded"]), "grounding_max": int(get_ajuste("grounding_max_mes", settings.GROUNDING_MAX_MES))}


# ── ajustes y bitácora ───────────────────────────────────────────────────────
def set_ajuste(clave: str, valor: Any) -> None:
    with conn() as con:
        con.execute("INSERT INTO ajustes (clave, valor, actualizado_en) VALUES (?,?,?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor, actualizado_en=excluded.actualizado_en",
                    (clave, _j(valor), now()))


def get_ajuste(clave: str, default: Any = None) -> Any:
    with conn() as con:
        r = con.execute("SELECT valor FROM ajustes WHERE clave=?", (clave,)).fetchone()
    if not r:
        return default
    try:
        return json.loads(r["valor"])
    except json.JSONDecodeError:
        return default


def log(nivel: str, origen: str, evento: str, detalle: str = "", usuario: str | None = None) -> None:
    try:
        with conn() as con:
            con.execute("INSERT INTO bitacora (momento, nivel, origen, evento, detalle, usuario) VALUES (?,?,?,?,?,?)",
                        (now(), nivel, origen, evento, (detalle or "")[:4000], usuario or ""))
    except sqlite3.Error:
        pass


def bitacora(limite: int = 300, nivel: str | None = None) -> list[dict]:
    q = "SELECT * FROM bitacora"
    args: list = []
    if nivel:
        q += " WHERE nivel=?"; args.append(nivel)
    q += " ORDER BY id DESC LIMIT ?"; args.append(limite)
    with conn() as con:
        return _rows(con.execute(q, args))
