"""El Analista: aplica las reglas de nivel, ajusta roadmaps, propone ascensos (con aprobación humana), escribe análisis para líderes,
genera resúmenes periódicos, alerta inactividad y conversa con managers usando herramientas sobre los datos (nunca inventa cifras).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from .. import db, metrics
from ..config import settings
from ..llm import PresupuestoAgotado, llm
from ..llm.gemini import ErrorLLM
from . import catalogo as C
from . import esquemas as E
from . import prompts as P
from . import validar as V
from .avatares import json_compacto

log = logging.getLogger("mv.analista")


# ── después de cada sesión ───────────────────────────────────────────────────
def post_sesion(sesion: dict, usuario: dict) -> None:
    hab = C.HABILIDADES[sesion["habilidad"]]
    resultado = sesion.get("resultado") or {}
    score = float(sesion.get("score_global") or 0)
    decisiones: list[str] = []
    historial = [s for s in reversed(db.sesiones(usuario_id=usuario["id"], habilidad=sesion["habilidad"], estado="completada", limite=50)) if s["tipo"] == "practica"]
    scores = [float(s["score_global"] or 0) for s in historial]
    niv = db.nivel(usuario["id"], sesion["habilidad"]) or {}
    nivel_actual = niv.get("nivel") or sesion.get("nivel") or hab["niveles"][0]
    nuevo_nivel = nivel_actual
    sin_mejora = int(niv.get("sin_mejora") or 0)
    sin_mejora = sin_mejora + 1 if len(scores) >= 2 and scores[-1] <= scores[-2] else 0

    if sesion["habilidad"] in ("ventas", "entrevistas"):
        niveles = hab["niveles"]
        i = niveles.index(nivel_actual) if nivel_actual in niveles else 0
        mismos = [s for s in historial if (s.get("nivel") or nivel_actual) == nivel_actual]
        ult = [float(s["score_global"] or 0) for s in mismos[-C.REGLAS_NIVEL["sube_sesiones"]:]]
        if len(ult) >= C.REGLAS_NIVEL["sube_sesiones"] and all(x > C.REGLAS_NIVEL["sube"] for x in ult) and i + 1 < len(niveles):
            nuevo_nivel = niveles[i + 1]
            decisiones.append(f"Sube a {nuevo_nivel}: {len(ult)} sesiones seguidas con score > {C.REGLAS_NIVEL['sube']} ({', '.join(f'{x:.0f}' for x in ult)}).")
            sin_mejora = 0
        elif score < C.REGLAS_NIVEL["baja"] and i > 0:
            nuevo_nivel = niveles[i - 1]
            decisiones.append(f"Regresa a {nuevo_nivel}: score {score:.0f} < {C.REGLAS_NIVEL['baja']}.")
            sin_mejora = 0
        if nuevo_nivel != nivel_actual:
            db.guardar_nivel(usuario["id"], sesion["habilidad"], nuevo_nivel, motivo=decisiones[-1])
            _renivelar_pendientes(usuario["id"], sesion["habilidad"], nuevo_nivel)
            db.notificar(usuario["id"], f"{hab['corto']}: ahora estás en nivel {nuevo_nivel}", decisiones[-1], "/roadmaps", "exito" if niveles.index(nuevo_nivel) > i else "aviso")
        db.actualizar_nivel_stats(usuario["id"], sesion["habilidad"], score, sin_mejora)
    else:  # ruta_dm: dominio por competencia y regla de ascenso con aprobación de RRHH
        comp = sesion.get("competencia") or ""
        s10 = float(resultado.get("score_global") or score / 10)
        dom = niv.get("competencias") or {}
        prev = dom.get(comp) if isinstance(dom.get(comp), dict) else {}
        dom[comp] = {"score": round(s10, 1), "dominio": C.dominio_dm(s10), "fecha": db.now(), "sesiones": int(prev.get("sesiones", 0)) + 1,
                     "mejor": max(s10, float(prev.get("mejor", 0)))}
        db.guardar_nivel(usuario["id"], "ruta_dm", nivel_actual, competencias={comp: dom[comp]})
        db.actualizar_nivel_stats(usuario["id"], "ruta_dm", score, sin_mejora)
        decisiones.append(f"{comp}: {s10:.1f}/10 ({C.dominio_dm(s10)}).")
        prop = evaluar_ascenso_dm(usuario, nivel_actual, dom)
        if prop:
            decisiones.append(prop)

    # refuerzo por estancamiento
    refuerzo = False
    if sin_mejora >= C.REGLAS_NIVEL["refuerzo_sin_mejora"]:
        refuerzo = _insertar_refuerzo(usuario, sesion, resultado)
        if refuerzo:
            decisiones.append(f"Sesión de refuerzo insertada: {sin_mejora} sesiones sin mejora.")
            db.actualizar_nivel_stats(usuario["id"], sesion["habilidad"], score, 0)
            for d in _director_de(usuario):
                db.notificar(d["id"], f"Refuerzo para {usuario['nombre']}", f"{hab['corto']}: {sin_mejora} sesiones sin mejora; el Analista insertó una sesión de refuerzo.",
                             f"/colaborador/{usuario['id']}", "aviso")

    # metas del líder alcanzadas
    for m in db.metas(usuario["empresa_id"], area_id=usuario.get("area_id"), usuario_id=usuario["id"]) if usuario.get("empresa_id") else []:
        if m["habilidad"] == sesion["habilidad"] and len(scores) >= 2 and sum(scores[-2:]) / 2 >= float(m["score_minimo"] or 0) and sesion["habilidad"] != "ruta_dm":
            decisiones.append(f"Meta del líder alcanzada: promedio de las últimas 2 sesiones ≥ {m['score_minimo']:.0f}.")

    # narrativa del analista (modelo ligero, entrada compacta) + siguiente objetivo
    analisis = _narrativa_post_sesion(sesion, usuario, hab, scores, nivel_actual, nuevo_nivel, decisiones, resultado)
    if analisis:
        _aplicar_siguiente_objetivo(usuario, sesion, analisis.get("siguiente_objetivo") or (resultado.get("recomendacion") or {}).get("objetivo_siguiente"))
        db.guardar_analisis(usuario["empresa_id"], "post_sesion", f"{hab['corto']} · {usuario['nombre']} · {score:.0f}", {**analisis, "decisiones": decisiones, "score": score,
                            "habilidad": sesion["habilidad"], "nivel": nuevo_nivel}, usuario_id=usuario["id"], area_id=usuario.get("area_id"), sesion_id=sesion["id"])
        if analisis.get("riesgo") == "alto":
            for d in _director_de(usuario) + db.usuarios(usuario["empresa_id"], rol="rrhh"):
                db.notificar(d["id"], f"Atención: {usuario['nombre']}", analisis.get("riesgo_motivo", ""), f"/colaborador/{usuario['id']}", "alerta")
    else:
        _aplicar_siguiente_objetivo(usuario, sesion, (resultado.get("recomendacion") or {}).get("objetivo_siguiente"))
    _completar_roadmap_si_termino(usuario, sesion["habilidad"])


def _narrativa_post_sesion(sesion, usuario, hab, scores, nivel_actual, nuevo_nivel, decisiones, resultado) -> dict | None:
    kpis = [{"id": k.get("id"), "nombre": k.get("nombre", ""), "score": k.get("score")} for k in resultado.get("kpis", [])]
    subs = [{"nombre": s.get("nombre"), "score": s.get("score")} for s in resultado.get("subdimensiones", [])]
    metas = [{"habilidad": m["habilidad"], "score_minimo": m["score_minimo"], "plazo": m.get("plazo"), "competencia": m.get("competencia")}
             for m in (db.metas(usuario["empresa_id"], area_id=usuario.get("area_id"), usuario_id=usuario["id"]) if usuario.get("empresa_id") else [])
             if m["habilidad"] == sesion["habilidad"]]
    datos = {
        "colaborador": usuario["nombre"], "habilidad": hab["nombre"], "nivel_antes": nivel_actual, "nivel_despues": nuevo_nivel,
        "sesion": {"score": sesion.get("score_global"), "turnos": sesion.get("turnos"), "objetivo": sesion.get("objetivo"), "competencia": sesion.get("competencia"),
                   "kpis": kpis, "subdimensiones": subs, "resumen_avatar": resultado.get("resumen", ""),
                   "recomendacion_avatar": resultado.get("recomendacion") or resultado.get("siguiente_paso") or {},
                   "oportunidades": [o.get("habilidad") for o in resultado.get("oportunidades", [])] or [b.get("brecha") for b in resultado.get("brechas", [])],
                   "evidencia": resultado.get("evidencia") or {}},
        "historial_scores": scores[-6:], "decisiones": decisiones, "metas_lider": metas,
    }
    try:
        r = llm.generar(origen="analista.post_sesion", system=P.ANALISTA_POST_SESION.format(sube=C.REGLAS_NIVEL["sube"], sube_sesiones=C.REGLAS_NIVEL["sube_sesiones"],
                                                                                          baja=C.REGLAS_NIVEL["baja"], refuerzo=C.REGLAS_NIVEL["refuerzo_sin_mejora"]),
                        contents=[{"role": "user", "text": json_compacto(datos)}], schema=E.ANALISTA_POST, clase="ligero", thinking="low", max_tokens=2000,
                        temperatura=0.3, usuario_id=usuario["id"], sesion_id=sesion["id"])
        return V.analista_post(r.json)
    except (PresupuestoAgotado, ErrorLLM) as e:
        db.log("warn", "analista", "Sin narrativa post-sesión", str(e), usuario["email"])
        return None


def _aplicar_siguiente_objetivo(usuario: dict, sesion: dict, objetivo: str | None) -> None:
    if not objetivo:
        return
    sig = db.siguiente_item(usuario["id"], sesion["habilidad"])
    if sig and sig.get("estado") == "pendiente":
        db.actualizar_item(sig["id"], objetivo=objetivo[:300], porque=f"Ajustado por el Analista tras la sesión #{sesion['id']}")


def _renivelar_pendientes(usuario_id: int, habilidad: str, nivel: str) -> None:
    rm = db.roadmap_activo(usuario_id, habilidad)
    if rm:
        for it in rm["items"]:
            if it["estado"] == "pendiente":
                db.actualizar_item(it["id"], nivel=nivel)
        db.actualizar_roadmap(rm["id"], ajustes=int(rm.get("ajustes") or 0) + 1, version=int(rm.get("version") or 1) + 1)


def _insertar_refuerzo(usuario: dict, sesion: dict, resultado: dict) -> bool:
    rm = db.roadmap_activo(usuario["id"], sesion["habilidad"])
    if not rm:
        return False
    ultimo = max([it["orden"] for it in rm["items"] if it["estado"] == "completada"], default=0)
    reco = resultado.get("recomendacion") or {}
    foco = (resultado.get("oportunidades") or [{}])[0].get("habilidad") if resultado.get("oportunidades") else (resultado.get("brechas") or [{}])[0].get("brecha", "")
    semana = next((it["semana"] for it in rm["items"] if it["estado"] == "pendiente"), rm["items"][-1]["semana"] if rm["items"] else 1)
    db.insertar_item(rm["id"], ultimo, {"semana": semana, "tipo": "refuerzo", "nivel": sesion.get("nivel"), "competencia": sesion.get("competencia", ""),
                                        "formato": sesion.get("formato", ""), "objetivo": f"Refuerzo: {reco.get('objetivo_siguiente') or foco or 'consolidar lo trabajado'}",
                                        "porque": "Tres sesiones sin mejora en esta habilidad; el Analista inserta una práctica enfocada antes de continuar.",
                                        "agregado_por": "analista"})
    db.notificar(usuario["id"], "Sesión de refuerzo agregada", "El Analista agregó una práctica enfocada a tu plan para consolidar antes de continuar.", "/roadmaps", "aviso")
    return True


def _completar_roadmap_si_termino(usuario: dict, habilidad: str) -> None:
    rm = db.roadmap_activo(usuario["id"], habilidad)
    if rm and rm["items"] and all(it["estado"] != "pendiente" for it in rm["items"]):
        db.actualizar_roadmap(rm["id"], estado="completado")
        db.notificar(usuario["id"], f"Completaste tu plan de {C.HABILIDADES[habilidad]['corto']}", "El Analista diseñará tu siguiente plan.", "/roadmaps", "exito")
        try:
            from .roadmap import generar_roadmap
            generar_roadmap(usuario, habilidad, brecha="media", sesiones_semana=int(rm.get("sesiones_semana") or 2), requiere_aprobacion=False,
                            motivo="continuación tras completar el plan anterior", agregado_por="analista")
        except (PresupuestoAgotado, ErrorLLM) as e:
            db.log("warn", "analista", "No se pudo generar el siguiente roadmap", str(e), usuario["email"])


# ── ascenso en la Ruta DM (propuesta → RRHH) ────────────────────────────────
def evaluar_ascenso_dm(usuario: dict, nivel_actual: str, dominio: dict) -> str | None:
    sig = C.nivel_dm_siguiente(nivel_actual)
    if not sig:
        return None
    comps = C.competencias_dm(sig)
    scores = {c: float(dominio.get(c, {}).get("score", 0)) if isinstance(dominio.get(c), dict) else 0.0 for c in comps}
    entrenadas = [c for c in comps if isinstance(dominio.get(c), dict)]
    if len(entrenadas) < len(comps):
        return None
    R = C.REGLA_ASCENSO_DM
    prom = sum(scores.values()) / len(scores)
    listas = sum(1 for v in scores.values() if v >= R["listas_umbral"])
    if prom >= R["promedio_min"] and min(scores.values()) >= R["minimo_por_competencia"] and listas >= R["listas_min"]:
        evidencia = "; ".join(f"{c} {v:.1f}/10" for c, v in scores.items())
        pid = db.crear_propuesta(usuario["empresa_id"], "ascenso_dm", f"Ascenso propuesto: {usuario['nombre']} → {sig}",
                                 {"de": nivel_actual, "a": sig, "promedio": round(prom, 2), "listas": listas, "scores": scores},
                                 evidencia=f"Todas las competencias de {sig} entrenadas; promedio {prom:.1f}/10; {listas} en 9–10. {evidencia}",
                                 usuario_id=usuario["id"], clave=f"ascenso:{usuario['id']}:{sig}")
        if pid:
            for m in db.usuarios(usuario["empresa_id"], rol="rrhh"):
                db.notificar(m["id"], f"Propuesta de ascenso: {usuario['nombre']} → {sig}", "El Analista reunió la evidencia; requiere tu aprobación.", "/aprobaciones", "exito")
            return f"Propuesta de ascenso a {sig} enviada a RRHH (promedio {prom:.1f}/10)."
    return None


def aplicar_ascenso_dm(propuesta: dict, aprobador: dict) -> None:
    det = propuesta.get("detalle") or {}
    u = db.usuario(propuesta["usuario_id"])
    if not u:
        return
    db.guardar_nivel(u["id"], "ruta_dm", det.get("a"), motivo=f"Ascenso aprobado por {aprobador['nombre']} (propuesta #{propuesta['id']})")
    db.notificar(u["id"], f"¡Ascendiste a {det.get('a')} en la Ruta DM!", f"Aprobado por {aprobador['nombre']}. Juan diseñará tu nuevo plan.", "/roadmaps", "exito")
    rm = db.roadmap_activo(u["id"], "ruta_dm")
    if rm:
        db.actualizar_roadmap(rm["id"], estado="completado")
    try:
        from .roadmap import generar_roadmap
        generar_roadmap(u, "ruta_dm", brecha="media", sesiones_semana=int((rm or {}).get("sesiones_semana") or 2), requiere_aprobacion=False,
                        motivo=f"nuevo nivel {det.get('a')}", agregado_por="analista")
    except (PresupuestoAgotado, ErrorLLM) as e:
        db.log("warn", "analista", "No se pudo generar roadmap tras ascenso", str(e), u["email"])
    db.log("info", "analista", f"Ascenso aplicado: {u['email']} → {det.get('a')}", "", aprobador["email"])


def _director_de(usuario: dict) -> list[dict]:
    a = db.area(usuario.get("area_id"))
    if a and a.get("director_id"):
        d = db.usuario(a["director_id"])
        return [d] if d else []
    return []


# ── tareas periódicas ────────────────────────────────────────────────────────
def alertas_inactividad(empresa_id: int) -> int:
    limite = (datetime.now(timezone.utc) - timedelta(days=settings.INACTIVIDAD_DIAS)).isoformat()
    n = 0
    for u in db.usuarios(empresa_id, rol="colaborador"):
        ult = db.sesiones(usuario_id=u["id"], limite=1)
        ultima = ult[0]["inicio"] if ult else None
        if ultima and ultima >= limite:
            continue
        if db.perfil(u["id"]).get("estado") != "completo" and not ultima:
            continue
        clave = f"inactivo:{u['id']}:{db.periodo()}"
        pid = db.crear_propuesta(empresa_id, "alerta", f"Sin actividad: {u['nombre']}", {"ultima_sesion": ultima, "dias": settings.INACTIVIDAD_DIAS},
                                 evidencia=f"Sin sesiones desde {ultima[:10] if ultima else 'nunca'}.", usuario_id=u["id"], clave=clave)
        if pid:
            n += 1
            db.notificar(u["id"], "Te extrañamos en Mente Viva", "Una sesión de 15 minutos esta semana mantiene tu progreso.", "/hoy", "aviso")
            for d in _director_de(u):
                db.notificar(d["id"], f"{u['nombre']} lleva {settings.INACTIVIDAD_DIAS}+ días sin practicar", "", f"/colaborador/{u['id']}", "aviso")
    return n


def resumen_periodico(empresa_id: int, audiencia: str = "organizacion", area_id: int | None = None, dias: int = 7) -> int | None:
    """Resumen ejecutivo semanal (área) o mensual (organización) escrito por el Analista con datos del módulo de métricas."""
    datos = metrics.resumen_para_analista(empresa_id, area_id=area_id, dias=dias)
    if not datos.get("sesiones"):
        return None
    aud = "el director del área" if audiencia == "area" else "Dirección General y RRHH"
    try:
        r = llm.generar(origen="analista.resumen", system=P.ANALISTA_RESUMEN.format(audiencia=aud), contents=[{"role": "user", "text": json_compacto(datos)}],
                        schema=E.ANALISTA_RESUMEN, clase="ligero", thinking="low", max_tokens=2000, temperatura=0.3)
    except (PresupuestoAgotado, ErrorLLM) as e:
        db.log("warn", "analista", "Sin resumen periódico", str(e))
        return None
    js = r.json if isinstance(r.json, dict) else {"titulo": "Resumen", "resumen": r.texto, "recomendaciones": []}
    aid = db.guardar_analisis(empresa_id, "area" if audiencia == "area" else "organizacion", js.get("titulo") or "Resumen del periodo", {**js, "datos": datos}, area_id=area_id)
    destinatarios = db.usuarios(empresa_id, rol="rrhh") + db.usuarios(empresa_id, rol="dg")
    if area_id:
        a = db.area(area_id)
        destinatarios = [db.usuario(a["director_id"])] if a and a.get("director_id") else []
    for d in destinatarios:
        if d:
            db.notificar(d["id"], js.get("titulo") or "Resumen del Analista", (js.get("resumen") or "")[:180], "/analisis", "info")
    return aid


# ── investigación con fuentes ────────────────────────────────────────────────
def investigar(tema: str, usuario: dict, guardar: bool = True) -> dict:
    r = llm.generar(origen="analista.investigar", system=P.INVESTIGAR, contents=[{"role": "user", "text": tema[:500]}], grounding=True, thinking="low",
                    max_tokens=2000, temperatura=0.2, usuario_id=usuario["id"])
    fuentes = r.fuentes
    texto = r.texto
    if not fuentes:
        texto = ("(Sin búsqueda disponible este mes o sin fuentes recuperadas: lo siguiente es orientación general sin verificar, trátalo como hipótesis.)\n" + texto)
    out = {"tema": tema, "texto": texto, "fuentes": fuentes, "fecha": db.now()}
    if guardar and usuario.get("empresa_id"):
        db.guardar_analisis(usuario["empresa_id"], "investigacion", f"Investigación: {tema[:80]}", out, usuario_id=None, fuentes=fuentes)
    return out


# ── chat con herramientas para managers ──────────────────────────────────────
HERRAMIENTAS = [
    {"name": "listar_colaboradores", "description": "Lista colaboradores visibles con nivel por habilidad, score promedio, última actividad y semáforo.",
     "parameters": {"type": "object", "properties": {"area": {"type": "string", "description": "nombre del área (opcional)"}}}},
    {"name": "ficha_colaborador", "description": "Ficha completa de un colaborador: niveles, últimas sesiones con scores y recomendaciones, roadmaps, evaluaciones, metas y propuestas.",
     "parameters": {"type": "object", "properties": {"nombre": {"type": "string", "description": "nombre o parte del nombre"}}, "required": ["nombre"]}},
    {"name": "kpis", "description": "Indicadores del periodo (organización o un área): IDSS, práctica, participación, engagement, aplicación, transferencia, madurez, IIHO, y ranking.",
     "parameters": {"type": "object", "properties": {"area": {"type": "string", "description": "nombre del área (opcional)"}}}},
    {"name": "sesiones_recientes", "description": "Sesiones completadas en los últimos N días con score, habilidad y colaborador.",
     "parameters": {"type": "object", "properties": {"dias": {"type": "integer"}}}},
    {"name": "metas_vigentes", "description": "Metas activas definidas por RRHH o directores."},
    {"name": "investigar", "description": "Busca evidencia externa confiable (fuentes oficiales/académicas) sobre un tema y devuelve hallazgos con sus fuentes.",
     "parameters": {"type": "object", "properties": {"tema": {"type": "string"}}, "required": ["tema"]}},
    {"name": "proponer", "description": "Registra una propuesta para aprobación humana: refuerzo, ajuste de roadmap o meta sugerida para un colaborador.",
     "parameters": {"type": "object", "properties": {"tipo": {"type": "string", "enum": ["refuerzo", "ajuste", "meta"]}, "nombre": {"type": "string"},
                                                     "titulo": {"type": "string"}, "detalle": {"type": "string"}}, "required": ["tipo", "titulo", "detalle"]}},
]


def _visibles(u: dict) -> list[dict]:
    from ..security import alcance_usuarios
    return [x for x in alcance_usuarios(u) if x["rol"] == "colaborador"]


def _buscar(u: dict, nombre: str) -> dict | None:
    n = (nombre or "").strip().lower()
    for x in _visibles(u):
        if n and (n in x["nombre"].lower() or n in x["email"].lower()):
            return x
    return None


def ejecutar_herramienta(u: dict, nombre: str, args: dict) -> dict:
    try:
        if nombre == "listar_colaboradores":
            vis = _visibles(u)
            if args.get("area"):
                vis = [x for x in vis if (x.get("area_nombre") or "").lower() == args["area"].strip().lower()]
            return {"colaboradores": [metrics.resumen_colaborador(x) for x in vis][:60]}
        if nombre == "ficha_colaborador":
            x = _buscar(u, args.get("nombre", ""))
            if not x:
                return {"error": "No encuentro a esa persona dentro de tu alcance."}
            return metrics.ficha(x, incluir_feedback=True)
        if nombre == "kpis":
            area_id = None
            if u["rol"] == "director":
                area_id = u.get("area_id")
            elif args.get("area"):
                area_id = next((a["id"] for a in db.areas(u["empresa_id"]) if a["nombre"].lower() == args["area"].strip().lower()), None)
            return metrics.kpis_organizacion(u["empresa_id"], area_id=area_id)
        if nombre == "sesiones_recientes":
            dias = int(args.get("dias") or 7)
            desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
            ids = {x["id"] for x in _visibles(u)}
            ss = [s for s in db.sesiones(empresa_id=u["empresa_id"], estado="completada", desde=desde, limite=200) if s["usuario_id"] in ids]
            return {"sesiones": [{"fecha": s["inicio"][:10], "colaborador": s["usuario_nombre"], "habilidad": s["habilidad"], "nivel": s.get("nivel"),
                                  "score": s.get("score_global"), "objetivo": s.get("objetivo")} for s in ss]}
        if nombre == "metas_vigentes":
            ms = db.metas(u["empresa_id"], area_id=u.get("area_id") if u["rol"] == "director" else None)
            return {"metas": [{"habilidad": m["habilidad"], "competencia": m.get("competencia"), "score_minimo": m["score_minimo"], "plazo": m.get("plazo"),
                               "area": m.get("area_nombre"), "colaborador": m.get("usuario_nombre"), "prioridad": m["prioridad"]} for m in ms]}
        if nombre == "investigar":
            inv = investigar(args.get("tema", ""), u)
            return {"texto": inv["texto"], "fuentes": inv["fuentes"]}
        if nombre == "proponer":
            x = _buscar(u, args.get("nombre", "")) if args.get("nombre") else None
            pid = db.crear_propuesta(u["empresa_id"], args.get("tipo", "ajuste"), args.get("titulo", "Propuesta del Analista")[:200],
                                     {"detalle": args.get("detalle", ""), "solicitado_por": u["nombre"]}, evidencia=args.get("detalle", "")[:1000],
                                     usuario_id=x["id"] if x else None, creado_por=f"analista (chat de {u['nombre']})")
            return {"ok": True, "propuesta_id": pid, "mensaje": "Propuesta registrada; queda pendiente de aprobación en Aprobaciones."}
        return {"error": f"Herramienta desconocida: {nombre}"}
    except Exception as e:  # noqa: BLE001
        log.exception("herramienta %s", nombre)
        return {"error": f"Fallo al ejecutar {nombre}: {e}"}


def chat(u: dict, texto: str) -> dict:
    """Conversación del manager con el Analista (bucle de herramientas, máx. 5 rondas)."""
    empresa = db.empresa(u["empresa_id"]) or {}
    ch = db.obtener_chat(u["id"], "analista", "Analista")
    db.guardar_chat_mensaje(ch["id"], "usuario", texto)
    alcance = {"director": f"sólo tu área ({u.get('area_nombre') or 'sin área'})", "rrhh": "toda la empresa", "dg": "toda la empresa (consulta)"}.get(u["rol"], "limitado")
    system = P.ANALISTA_CHAT.format(nombre=u["nombre"], rol=u["rol"], empresa=empresa.get("nombre", ""), alcance=alcance, hoy=db.now()[:10])
    historial = [m for m in ch["mensajes"] if m["rol"] in ("usuario", "analista")][-12:]
    contents = [{"role": "user" if m["rol"] == "usuario" else "model", "text": m["texto"]} for m in historial]
    if not contents or contents[-1]["text"] != texto:
        contents.append({"role": "user", "text": texto})
    fuentes: list[dict] = []
    herramientas_usadas: list[str] = []
    respuesta = ""
    for _ in range(5):
        r = llm.generar(origen="analista.chat", system=system, contents=contents, herramientas=HERRAMIENTAS, thinking="low", max_tokens=2500, temperatura=0.3, usuario_id=u["id"])
        if not r.llamadas_funcion:
            respuesta = r.texto
            break
        for fc in r.llamadas_funcion:
            res = ejecutar_herramienta(u, fc["name"], fc.get("args") or {})
            herramientas_usadas.append(fc["name"])
            if fc["name"] == "investigar":
                fuentes += res.get("fuentes", [])
            contents.append({"function_call": {"name": fc["name"], "args": fc.get("args") or {}}})
            contents.append({"function_response": {"name": fc["name"], "response": {"resultado": json.loads(json.dumps(res, default=str))}}})
    else:
        respuesta = r.texto or "Consulté los datos pero no logré concluir; inténtalo con una pregunta más acotada."
    if not respuesta:
        respuesta = "No obtuve una respuesta; intenta de nuevo."
    meta = {"herramientas": herramientas_usadas, "fuentes": fuentes}
    db.guardar_chat_mensaje(ch["id"], "analista", respuesta, meta)
    return {"texto": respuesta, **meta}


def coach_reporte(u: dict, sesion: dict, texto: str) -> dict:
    """Chat del colaborador con su coach sobre el reporte de una sesión (usa el reporte, no la transcripción)."""
    from .avatares import AVATARES
    ambito = f"reporte:{sesion['id']}"
    ch = db.obtener_chat(u["id"], ambito, "Coach")
    db.guardar_chat_mensaje(ch["id"], "usuario", texto)
    avatar = AVATARES[sesion["agente"]]["nombre"]
    res = sesion.get("resultado") or {}
    compacto = {k: res.get(k) for k in ("resumen", "kpis", "subdimensiones", "fortalezas", "oportunidades", "brechas", "momentos_clave", "momento_clave",
                                        "plan_accion", "tips", "recomendacion", "siguiente_paso", "evidencia", "score_global_100") if res.get(k) is not None}
    system = P.COACH_REPORTE.format(avatar=avatar, nombre=u["nombre"]) + "\nREPORTE:\n" + json_compacto(compacto)
    hist = [m for m in ch["mensajes"] if m["rol"] in ("usuario", "coach")][-8:]
    contents = [{"role": "user" if m["rol"] == "usuario" else "model", "text": m["texto"]} for m in hist]
    if not contents or contents[-1]["text"] != texto:
        contents.append({"role": "user", "text": texto})
    r = llm.generar(origen="coach.reporte", system=system, contents=contents, thinking="low", max_tokens=1200, temperatura=0.5, usuario_id=u["id"], sesion_id=sesion["id"])
    db.guardar_chat_mensaje(ch["id"], "coach", r.texto)
    return {"texto": r.texto}
