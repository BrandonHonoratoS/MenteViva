"""Diagnóstico de Elena → perfil de competencias, niveles por habilidad y roadmaps (uno por habilidad con brecha).

El roadmap se arma en dos capas:
1. Andamiaje determinista: horizonte (4–8 semanas según la brecha), sesiones por semana (según el tiempo declarado, repartido entre
   los roadmaps) y, en la Ruta DM, el ciclo de competencias del siguiente nivel.
2. La IA (Elena/Analista) escribe el objetivo medible y el "por qué" de cada sesión y el "por qué este orden" del plan.
Así el plan siempre es coherente con las reglas y la IA aporta el juicio, no la aritmética.
"""
from __future__ import annotations

from .. import db
from ..config import settings
from ..llm import PresupuestoAgotado, llm
from ..llm.gemini import ErrorLLM
from . import catalogo as C
from . import esquemas as E
from . import prompts as P
from . import validar as V
from .avatares import _texto_perfil, json_compacto


def analizar_diagnostico(sesion: dict, usuario: dict, transcript: str) -> None:
    perfil = db.perfil(usuario["id"])
    ob = perfil.get("onboarding", {})
    empresa = db.empresa(usuario.get("empresa_id"))
    habs = C.habilidades_empresa(empresa)
    prompt = P.ELENA_ANALISIS.format(competencias=", ".join(C.COMPETENCIAS_DIAGNOSTICO), niveles_dm=", ".join(C.NIVELES_DM),
                                     nivel_dm_estimado=C.nivel_dm_estimado(ob), habilidades=", ".join(h["id"] for h in habs), reglas=P.REGLAS_FEEDBACK)
    contenido = "PERFIL DECLARADO:\n" + _texto_perfil(usuario, ob) + "\n\nTRANSCRIPCIÓN:\n" + transcript
    r = llm.generar(origen="elena.analisis", system=prompt, contents=[{"role": "user", "text": contenido}], schema=E.ELENA_DIAGNOSTICO,
                    thinking=settings.GEMINI_THINKING_ANALISIS, max_tokens=8000, temperatura=0.3, usuario_id=usuario["id"], sesion_id=sesion["id"])
    if not isinstance(r.json, dict):
        raise ErrorLLM("El diagnóstico no devolvió un resultado válido. Pulsa Reintentar análisis.")
    diag = V.diagnostico(r.json, ob)
    diag["fecha"] = db.now()
    comp_validas = [c for c in diag.get("competencias", []) if int(c.get("nivel", 0)) > 0]
    diag["score_inicial"] = round(sum(int(c["nivel"]) for c in comp_validas) / (5 * len(comp_validas)) * 100, 1) if comp_validas else None
    db.actualizar_sesion(sesion["id"], estado="completada", score_global=diag["score_inicial"], resultado_json=diag)
    db.guardar_perfil(usuario["id"], diagnostico=diag, estado="completo", sesion_diagnostico_id=sesion["id"])

    # niveles iniciales por habilidad
    ids = {h["id"] for h in habs}
    if "ventas" in ids:
        db.guardar_nivel(usuario["id"], "ventas", diag.get("nivel_ventas") or C.nivel_ventas_estimado(ob), diag["score_inicial"], "diagnóstico de Elena")
    if "entrevistas" in ids:
        db.guardar_nivel(usuario["id"], "entrevistas", diag.get("nivel_entrevistas") or "Principiante", diag["score_inicial"], "diagnóstico de Elena")
    if "ruta_dm" in ids:
        db.guardar_nivel(usuario["id"], "ruta_dm", diag.get("nivel_dm") or C.nivel_dm_estimado(ob), None, "diagnóstico de Elena")

    # roadmaps: uno por habilidad con brecha (según Elena) + la Ruta DM siempre que esté habilitada
    prioridades = [p for p in diag.get("prioridades", []) if p.get("habilidad_id") in ids]
    orden = [p["habilidad_id"] for p in prioridades]
    if "ruta_dm" in ids and "ruta_dm" not in orden:
        orden.append("ruta_dm")
    usa = C.habilidades_que_usa(ob)
    spw_total = C.sesiones_por_semana(ob.get("tiempo_semana", ""))
    creados = []
    for i, hid in enumerate(orden):
        brecha = next((p.get("brecha") for p in prioridades if p["habilidad_id"] == hid), "media")
        spw = max(1, spw_total // max(1, len(orden)) + (1 if i < spw_total % max(1, len(orden)) else 0))
        try:
            rid = generar_roadmap(usuario, hid, brecha=brecha, sesiones_semana=spw, requiere_aprobacion=hid not in usa, diagnostico=diag)
            creados.append((hid, rid))
        except (PresupuestoAgotado, ErrorLLM) as e:
            db.log("warn", "roadmap", f"No se pudo generar roadmap {hid} para {usuario['email']}", str(e))
    db.notificar(usuario["id"], "Tu diagnóstico está listo", "Elena terminó tu análisis y diseñó tus planes de desarrollo.", "/mi-diagnostico", "exito")
    for m in _managers_de(usuario):
        db.notificar(m["id"], f"Diagnóstico completado: {usuario['nombre']}",
                     f"Nivel ventas {diag.get('nivel_ventas')} · Ruta DM {diag.get('nivel_dm')} · {len(creados)} roadmaps", f"/colaborador/{usuario['id']}")
    db.log("info", "roadmap", f"Diagnóstico y {len(creados)} roadmaps para {usuario['email']}", ", ".join(h for h, _ in creados))


def generar_roadmaps_faltantes(usuario: dict) -> list[str]:
    """Vuelve a crear los roadmaps que no se generaron (p. ej. por un fallo transitorio de la IA tras el diagnóstico)."""
    perfil = db.perfil(usuario["id"])
    diag = perfil.get("diagnostico") or {}
    if perfil.get("estado") != "completo" or not diag:
        return []
    ob = perfil.get("onboarding", {})
    ids = {h["id"] for h in C.habilidades_empresa(db.empresa(usuario.get("empresa_id")))}
    prioridades = [p for p in diag.get("prioridades", []) if p.get("habilidad_id") in ids]
    orden = [p["habilidad_id"] for p in prioridades]
    if "ruta_dm" in ids and "ruta_dm" not in orden:
        orden.append("ruta_dm")
    existentes = {r["habilidad"] for r in db.roadmaps(usuario["id"], ("activo", "propuesto"))}
    usa = C.habilidades_que_usa(ob)
    spw_total = C.sesiones_por_semana(ob.get("tiempo_semana", ""))
    creados = []
    for i, hid in enumerate(orden):
        if hid in existentes:
            continue
        if not db.nivel(usuario["id"], hid):
            nivel = {"ventas": diag.get("nivel_ventas") or C.nivel_ventas_estimado(ob), "entrevistas": diag.get("nivel_entrevistas") or "Principiante",
                     "ruta_dm": diag.get("nivel_dm") or C.nivel_dm_estimado(ob)}[hid]
            db.guardar_nivel(usuario["id"], hid, nivel, diag.get("score_inicial") if hid != "ruta_dm" else None, "diagnóstico de Elena")
        brecha = next((p.get("brecha") for p in prioridades if p["habilidad_id"] == hid), "media")
        spw = max(1, spw_total // max(1, len(orden)) + (1 if i < spw_total % max(1, len(orden)) else 0))
        generar_roadmap(usuario, hid, brecha=brecha, sesiones_semana=spw, requiere_aprobacion=hid not in usa, diagnostico=diag)
        creados.append(hid)
    return creados


def _managers_de(usuario: dict) -> list[dict]:
    out = []
    if usuario.get("empresa_id"):
        out += db.usuarios(usuario["empresa_id"], rol="rrhh")
        a = db.area(usuario.get("area_id"))
        if a and a.get("director_id"):
            d = db.usuario(a["director_id"])
            if d:
                out.append(d)
    return out


def _horizonte(brecha: str) -> int:
    return {"alta": 8, "media": 6, "baja": 4}.get(brecha or "media", 6)


def generar_roadmap(usuario: dict, habilidad_id: str, brecha: str = "media", sesiones_semana: int = 2, requiere_aprobacion: bool = False,
                    diagnostico: dict | None = None, motivo: str = "diagnóstico inicial", agregado_por: str = "elena") -> int:
    hab = C.HABILIDADES[habilidad_id]
    perfil = db.perfil(usuario["id"])
    ob = perfil.get("onboarding", {})
    diag = diagnostico or perfil.get("diagnostico") or {}
    niv = db.nivel(usuario["id"], habilidad_id) or {}
    nivel = niv.get("nivel") or hab["niveles"][0]
    horizonte = _horizonte(brecha)
    n_items = max(3, min(16, horizonte * sesiones_semana))
    # andamiaje
    andamiaje = []
    if habilidad_id == "ruta_dm":
        sig = C.nivel_dm_siguiente(nivel) or nivel
        comps = _orden_competencias_dm(sig, diag, niv.get("competencias") or {})
        for i in range(n_items):
            comp = comps[i % len(comps)]
            andamiaje.append({"semana": i // sesiones_semana + 1, "nivel": nivel, "competencia": comp, "formato": C.formato_sugerido(comp)})
    else:
        for i in range(n_items):
            andamiaje.append({"semana": i // sesiones_semana + 1, "nivel": nivel, "competencia": "", "formato": "roleplay"})
    metas = db.metas(usuario["empresa_id"], area_id=usuario.get("area_id"), usuario_id=usuario["id"]) if usuario.get("empresa_id") else []
    metas_txt = "; ".join(f"{m['habilidad']}: {m.get('competencia') or ''} score mínimo {m['score_minimo']} para {m.get('plazo') or 'sin plazo'} ({m['prioridad']})"
                          for m in metas if m["habilidad"] == habilidad_id) or "sin metas del líder"
    contexto = {
        "habilidad": hab["nombre"], "nivel_actual": nivel, "brecha": brecha, "horizonte_semanas": horizonte, "sesiones_por_semana": sesiones_semana,
        "andamiaje": andamiaje, "metas_del_lider": metas_txt,
        "diagnostico": {"fortalezas": [f.get("habilidad") for f in diag.get("fortalezas", [])], "oportunidades": [o.get("habilidad") for o in diag.get("oportunidades", [])],
                        "prioridad": next((p for p in diag.get("prioridades", []) if p.get("habilidad_id") == habilidad_id), {})},
        "onboarding": {k: ob.get(k) for k in ("etapa_debil", "objetivo_ventas", "meta", "estilo", "experiencia") if ob.get(k)},
    }
    if habilidad_id == "ruta_dm":
        sig = C.nivel_dm_siguiente(nivel) or nivel
        contexto["siguiente_nivel"] = {"nivel": sig, "valor": C.valor_dm(sig), "competencias": C.competencias_dm(sig)}
    system = ("Eres Elena Ríos diseñando un plan de desarrollo personalizado en Mente Viva. Recibes un andamiaje fijo (número de sesiones, semana, nivel y, "
              "en la Ruta DM, la competencia de cada sesión) y escribes para CADA sesión, en el mismo orden y sin cambiar semana/nivel/competencia, un objetivo "
              "medible y concreto (ej. 'Maneja 3 objeciones sin ceder en precio', 'Cierra con un siguiente paso con fecha') y una línea de por qué. "
              "Los objetivos deben progresar: primero fundamentos, luego presión, luego integración; el 60 % del plan de ventas ataca la etapa débil declarada; "
              "respeta las metas del líder. Escribe también el objetivo del plan (una línea) y 'por qué este orden' (2–3 líneas). Español de México. Responde SOLO con JSON.")
    r = llm.generar(origen="elena.roadmap", system=system, contents=[{"role": "user", "text": json_compacto(contexto)}], schema=E.ROADMAP,
                    thinking="low", max_tokens=5000, temperatura=0.5, usuario_id=usuario["id"])
    js = r.json if isinstance(r.json, dict) else {}
    items_ia = js.get("items") or []
    items = []
    for i, a in enumerate(andamiaje):
        ia = items_ia[i] if i < len(items_ia) else {}
        items.append({**a, "objetivo": (ia.get("objetivo") or f"Sesión {i + 1}: practicar {a['competencia'] or hab['corto']} en nivel {a['nivel']}")[:300],
                      "porque": (ia.get("porque") or "")[:300], "agregado_por": agregado_por})
    rid = db.crear_roadmap(usuario["id"], habilidad_id, nivel, objetivo=js.get("objetivo") or f"Avanzar en {hab['nombre']} desde {nivel}",
                           razon=js.get("razon") or motivo, items=items, horizonte=horizonte, sesiones_semana=sesiones_semana, requiere_aprobacion=requiere_aprobacion)
    if requiere_aprobacion and usuario.get("empresa_id"):
        db.crear_propuesta(usuario["empresa_id"], "roadmap", f"Aprobar roadmap de {hab['nombre']} para {usuario['nombre']}",
                           {"roadmap_id": rid, "habilidad": habilidad_id, "nivel": nivel, "sesiones": len(items), "horizonte": horizonte},
                           evidencia=f"La habilidad no forma parte del rol declarado ({', '.join(ob.get('funciones') or []) or 'sin funciones'}); "
                                     f"Elena la propone por brecha {brecha}.", usuario_id=usuario["id"], clave=f"roadmap:{rid}")
    return rid


def _orden_competencias_dm(nivel_siguiente: str, diag: dict, dominio: dict) -> list[str]:
    """Competencias del siguiente nivel: primero las no entrenadas o con menor dominio; luego las que ya van bien."""
    comps = list(C.competencias_dm(nivel_siguiente)) or ["Comunicación"]
    oportunidades = " ".join(o.get("habilidad", "").lower() for o in diag.get("oportunidades", []))

    def clave(c: str):
        d = dominio.get(c, {})
        score = float(d.get("score", 0)) if isinstance(d, dict) else 0.0
        afin = 0 if any(w in oportunidades for w in c.lower().split()) else 1
        return (score >= 9.0, score, afin)
    return sorted(comps, key=clave)
