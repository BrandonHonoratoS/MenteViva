"""Garantía de actualización sin pérdida: arrancar una versión nueva sobre una base existente conserva usuarios, contraseñas y sesiones,
aunque cambien las variables de entorno del superadmin; el respaldo descargable es una base SQLite íntegra."""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from app import db
from tests.conftest import Sesion

RAIZ = Path(__file__).resolve().parents[1]


def _arrancar(data_dir: str, extra_env: dict, codigo: str) -> str:
    """Ejecuta código contra la base en data_dir en un proceso aparte (como un deploy nuevo de Render)."""
    env = {**os.environ, "DATA_DIR": data_dir, "LLM_PROVEEDOR": "stub", "SCHEDULE_ENABLED": "0", "APP_ENV": "production", **extra_env}
    r = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    return r.stdout


def test_redeploy_conserva_usuarios_y_sesiones():
    data_dir = tempfile.mkdtemp(prefix="mv-upgrade-")
    env1 = {"SUPERADMIN_EMAIL": "admin@menteviva.mx", "SUPERADMIN_PASSWORD": "ClaveOriginal123", "EMPRESA_INICIAL": "Cóndor", "RRHH_INICIAL_EMAIL": "rrhh@condor.mx", "RRHH_INICIAL_PASSWORD": "ClaveRRHH123"}
    # 1) "deploy 1": arranca, crea datos (empresa, usuarios, una sesión) y cambia una contraseña
    _arrancar(data_dir, env1, """
from app import db
db.init_db()
rrhh = db.verificar_credenciales("rrhh@condor.mx", "ClaveRRHH123")
db.cambiar_password(rrhh["id"], "MiClaveNueva123")
eid = rrhh["empresa_id"]
aid = db.crear_area(eid, "Odoo")
uid = db.crear_usuario("ana@condor.mx", "ClaveAna12345", "Ana", "colaborador", eid, aid, debe_cambiar=False)
sid = db.crear_sesion(uid, "ventas", "celeste", nivel="Principiante")
db.guardar_mensaje(sid, "usuario", "hola")
db.actualizar_sesion(sid, estado="completada", score_global=81.0)
print("ok")
""")
    antes = _conteos(data_dir)
    assert antes["usuarios"] == 3 and antes["sesiones"] == 1
    # 2) "deploy 2": versión nueva arrancando sobre la MISMA base, con otras variables de entorno (contraseña de superadmin distinta,
    #    otra empresa inicial): nada se recrea ni se sobreescribe
    env2 = {**env1, "SUPERADMIN_PASSWORD": "OtraClave999999", "EMPRESA_INICIAL": "Empresa Nueva", "RRHH_INICIAL_PASSWORD": "Otra999999"}
    salida = _arrancar(data_dir, env2, """
from app import db
db.init_db(); db.init_db()           # dos arranques seguidos (reinicio)
assert db.verificar_credenciales("admin@menteviva.mx", "ClaveOriginal123"), "la contraseña del superadmin cambió"
assert not db.verificar_credenciales("admin@menteviva.mx", "OtraClave999999")
assert db.verificar_credenciales("rrhh@condor.mx", "MiClaveNueva123"), "la contraseña cambiada por el usuario se perdió"
assert db.verificar_credenciales("ana@condor.mx", "ClaveAna12345")
assert [e["nombre"] for e in db.empresas()] == ["Cóndor"], "se creó otra empresa"
est = db.estado_datos()
print(est["conteos"]["usuarios"], est["conteos"]["sesiones"], est["usuarios_activos"])
""")
    assert salida.split() == ["3", "1", "3"]
    assert _conteos(data_dir) == antes


def _conteos(data_dir: str) -> dict:
    con = sqlite3.connect(str(Path(data_dir) / "mente_viva.db"))
    try:
        return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("empresas", "usuarios", "sesiones", "mensajes", "areas")}
    finally:
        con.close()


def test_respaldo_descargable_es_una_base_integra(client):
    admin = Sesion(client, "admin@menteviva.mx", "SuperClave123")
    r = admin.get("/admin")
    assert r.status_code == 200 and "Datos y respaldo" in r.text
    r = admin.get("/admin/respaldo.db")
    assert r.status_code == 200 and r.content[:16] == b"SQLite format 3\x00"
    tmp = Path(tempfile.mkdtemp()) / "copia.db"
    tmp.write_bytes(r.content)
    con = sqlite3.connect(str(tmp))
    try:
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert con.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == db.estado_datos()["conteos"]["usuarios"]
    finally:
        con.close()
