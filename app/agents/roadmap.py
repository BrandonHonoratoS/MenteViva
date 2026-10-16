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
    for hid in ids - {"ventas", "entrevistas", "ruta_dm"}:   # escenarios nuevos (presentaciones, imagen, comunicación, liderazgo): nivel por experiencia
        if not db.nivel(usuario["id"], hid):
            db.guardar_nivel(usuario["id"], hid, _nivel_inicial(hid, diag, ob), diag["score_inicial"], "diagnóstico de Elena")

    # PLAN INTEGRAL: un roadmap por cada habilidad que a la persona le sirve (todas las de su empresa si trabaja en una; las de su vida real si es
    # público general), con más sesiones donde Elena vio más brecha, y todas intercaladas semana a semana en un solo plan hacia su meta.
    usa = C.habilidades_que_usa(ob)
    orden = _orden_plan(ob, diag, habs)
    brechas = _brechas(diag, orden)
    spw_total = C.sesiones_por_semana(ob.get("tiempo_semana", ""))
    cantidades = _cantidades(brechas, spw_total)
    creados = []
    for hid in orden:
        try:
            rid = generar_roadmap(usuario, hid, brecha=brechas[hid], sesiones_semana=spw_total, requiere_aprobacion=hid not in usa, diagnostico=diag,
                                  n_items=cantidades[hid], reprogramar=False)
            creados.append((hid, rid))
        except (PresupuestoAgotado, ErrorLLM) as e:
            db.log("warn", "roadmap", f"No se pudo generar roadmap {hid} para {usuario['email']}", str(e))
    reprogramar_plan_integral(usuario)
    db.notificar(usuario["id"], "Tu diagnóstico está listo", "Elena terminó tu análisis y diseñó tus planes de desarrollo.", "/mi-diagnostico", "exito")
    for m in _managers_de(usuario):
        db.notificar(m["id"], f"Diagnóstico completado: {usuario['nombre']}",
                     f"Nivel ventas {diag.get('nivel_ventas')} · Ruta DM {diag.get('nivel_dm')} · {len(creados)} roadmaps", f"/colaborador/{usuario['id']}")
    db.log("info", "roadmap", f"Diagnóstico y {len(creados)} roadmaps para {usuario['email']}", ", ".join(h for h, _ in creados))


def generar_roadmaps_faltantes(usuario: dict) -> list[str]:
    """Completa el plan integral: crea los roadmaps de las habilidades relevantes que aún no tienen (fallo transitorio de la IA o habilidades
    nuevas en la plataforma) y vuelve a intercalar todo el plan semana a semana."""
    perfil = db.perfil(usuario["id"])
    diag = perfil.get("diagnostico") or {}
    if perfil.get("estado") != "completo" or not diag:
        return []
    ob = perfil.get("onboarding", {})
    habs = C.habilidades_empresa(db.empresa(usuario.get("empresa_id")))
    usa = C.habilidades_que_usa(ob)
    orden = _orden_plan(ob, diag, habs)
    existentes = _con_plan(usuario)
    brechas = _brechas(diag, orden)
    cantidades = _cantidades(brechas, C.sesiones_por_semana(ob.get("tiempo_semana", "")))
    creados = []
    for hid in orden:
        if hid in existentes:
            continue
        if not db.nivel(usuario["id"], hid):
            db.guardar_nivel(usuario["id"], hid, _nivel_inicial(hid, diag, ob), diag.get("score_inicial") if hid != "ruta_dm" else None, "diagnóstico de Elena")
        try:
            generar_roadmap(usuario, hid, brecha=brechas[hid], sesiones_semana=C.sesiones_por_semana(ob.get("tiempo_semana", "")),
                            requiere_aprobacion=hid not in usa, diagnostico=diag, n_items=cantidades[hid], reprogramar=False,
                            motivo="habilidad integrada a tu plan integral")
            creados.append(hid)
        except (PresupuestoAgotado, ErrorLLM) as e:
            db.log("warn", "roadmap", f"No se pudo generar roadmap {hid} para {usuario['email']}", str(e))
    reprogramar_plan_integral(usuario)
    return creados


def habilidades_sin_plan(usuario: dict) -> list[str]:
    """Habilidades que deberían estar en el plan integral y aún no tienen roadmap (p. ej. escenarios nuevos para quien ya hizo su diagnóstico)."""
    perfil = db.perfil(usuario["id"])
    if perfil.get("estado") != "completo" or not perfil.get("diagnostico"):
        return []
    habs = C.habilidades_empresa(db.empresa(usuario.get("empresa_id")))
    existentes = _con_plan(usuario)
    return [h for h in _orden_plan(perfil.get("onboarding") or {}, perfil["diagnostico"], habs) if h not in existentes]


def _con_plan(usuario: dict) -> set[str]:
    """Habilidades que ya tienen roadmap (vigente, pausado o completado). Un roadmap rechazado por RRHH cuenta como decidido (no se vuelve a
    proponer), salvo que la persona se haya quedado sin ningún plan vigente: entonces se regenera todo."""
    rs = db.roadmaps(usuario["id"], ("activo", "propuesto", "pausado", "completado", "rechazado"))
    vigentes = any(r["estado"] in ("activo", "propuesto") for r in rs)
    return {r["habilidad"] for r in rs if r["estado"] != "rechazado" or vigentes}


def resumen_plan_integral(usuario: dict) -> dict:
    """Vista del plan como UNO solo: meta, habilidades, avance total y calendario semana a semana con las sesiones de todas las habilidades."""
    perfil = db.perfil(usuario["id"])
    ob = perfil.get("onboarding") or {}
    rms = [r for r in db.roadmaps(usuario["id"], ("activo", "propuesto", "completado"))]
    metas_lider = []
    if usuario.get("empresa_id"):
        for m in db.metas(usuario["empresa_id"], area_id=usuario.get("area_id"), usuario_id=usuario["id"]):
            h = C.HABILIDADES.get(m["habilidad"], {})
            metas_lider.append(f"{h.get('nombre', m['habilidad'])}{(' · ' + m['competencia']) if m.get('competencia') else ''}: score ≥ {m['score_minimo']}"
                               f"{(' para ' + str(m['plazo'])) if m.get('plazo') else ''}")
    semanas: dict[int, list] = {}
    total = hechas = 0
    for r in rms:
        for it in r["items"]:
            total += 1
            hechas += it["estado"] == "completada"
            semanas.setdefault(int(it["semana"] or 1), []).append({**it, "habilidad": r["habilidad"], "roadmap_estado": r["estado"]})
    for lst in semanas.values():
        lst.sort(key=lambda i: (i["estado"] != "completada", i["habilidad"], i["orden"]))
    pendientes = sorted(k for k, v in semanas.items() if any(i["estado"] == "pendiente" for i in v))
    return {
        "meta": ob.get("meta") or "", "metas_lider": metas_lider, "habilidades": [r["habilidad"] for r in rms if r["estado"] != "completado"],
        "total": total, "completadas": hechas, "semanas": sorted(semanas.items()), "sesiones_semana": C.sesiones_por_semana(ob.get("tiempo_semana", "")),
        "tiempo_semana": ob.get("tiempo_semana") or "", "semana_actual": pendientes[0] if pendientes else None,
        "ultima_semana": max(semanas) if semanas else 0, "faltan": habilidades_sin_plan(usuario),
    }


# ── plan integral: cuántas sesiones por habilidad y en qué semana ───────────
PESO_BRECHA = {"alta": 3, "media": 2, "baja": 1}
MIN_SESIONES = {"alta": 4, "media": 3, "baja": 2}


def _orden_plan(ob: dict, diag: dict, habs: list[dict]) -> list[str]:
    """Habilidades del plan, en orden de prioridad: primero las que Elena priorizó (por brecha), luego el resto de las relevantes."""
    relevantes = [h["id"] for h in C.habilidades_relevantes(ob, diag, habs)[0]]
    rango = {"alta": 0, "media": 1, "baja": 2}
    prior = sorted([p for p in diag.get("prioridades", []) if p.get("habilidad_id") in relevantes], key=lambda p: rango.get(p.get("brecha"), 1))
    orden = [p["habilidad_id"] for p in prior]
    for hid in relevantes:
        if hid not in orden and not (hid == "liderazgo" and not C.lidera(ob)):   # Liderazgo entra al plan sólo si lidera (o si Elena lo priorizó)
            orden.append(hid)
    return orden


def _brechas(diag: dict, hids: list[str]) -> dict[str, str]:
    out = {}
    for hid in hids:
        b = next((p.get("brecha") for p in diag.get("prioridades", []) if p.get("habilidad_id") == hid), None)
        out[hid] = b if b in PESO_BRECHA else ("media" if hid == "ruta_dm" else "baja")
    return out


def _cantidades(brechas: dict[str, str], sesiones_semana: int) -> dict[str, int]:
    """Reparte el tiempo semanal declarado: más sesiones a la brecha alta, nunca menos de 2 por habilidad."""
    if not brechas:
        return {}
    horizonte = 8 if "alta" in brechas.values() else 6
    total = horizonte * max(1, sesiones_semana)
    peso_total = sum(PESO_BRECHA[b] for b in brechas.values())
    return {h: min(16, max(MIN_SESIONES[b], round(total * PESO_BRECHA[b] / peso_total))) for h, b in brechas.items()}


def _intercalar(colas: dict[str, list], pesos: dict[str, int]) -> list[tuple[str, dict]]:
    """Round-robin ponderado suave: la habilidad con más sesiones aparece más seguido, repartida a lo largo de todo el plan; empata a favor de la
    prioridad (orden de las colas)."""
    colas = {h: list(q) for h, q in colas.items() if q}
    acumulado = {h: 0 for h in colas}
    out: list[tuple[str, dict]] = []
    while colas:
        total = sum(pesos.get(h, 1) for h in colas)
        for h in colas:
            acumulado[h] += pesos.get(h, 1)
        elegido = max(colas, key=lambda h: acumulado[h])
        acumulado[elegido] -= total
        out.append((elegido, colas[elegido].pop(0)))
        if not colas[elegido]:
            del colas[elegido]
            del acumulado[elegido]
    return out


def reprogramar_plan_integral(usuario: dict) -> int:
    """Reacomoda las sesiones pendientes de TODOS los roadmaps vigentes en un solo calendario: N sesiones por semana (el tiempo que la persona
    declaró), intercalando habilidades según su brecha. Respeta el orden interno de cada roadmap. Devuelve cuántas sesiones cambiaron de semana."""
    perfil = db.perfil(usuario["id"])
    ob = perfil.get("onboarding") or {}
    diag = perfil.get("diagnostico") or {}
    spw = max(1, C.sesiones_por_semana(ob.get("tiempo_semana", "")))
    rms = sorted(db.roadmaps(usuario["id"], ("activo", "propuesto")), key=lambda r: r["id"])
    colas = {}
    for r in rms:
        pend = [it for it in sorted(r["items"], key=lambda i: i["orden"]) if it["estado"] == "pendiente"]
        if pend:
            colas.setdefault(r["habilidad"], []).extend(pend)
    if not colas:
        return 0
    inicio = min(it["semana"] or 1 for q in colas.values() for it in q)
    orden = _orden_plan(ob, diag, C.habilidades_empresa(db.empresa(usuario.get("empresa_id")))) if diag else list(colas)
    colas = {h: colas[h] for h in sorted(colas, key=lambda h: orden.index(h) if h in orden else 99)}
    # la brecha ya decidió CUÁNTAS sesiones lleva cada habilidad (_cantidades); aquí se reparten proporcionalmente a lo que le falta a cada una,
    # así todas avanzan en paralelo hasta el final del plan (ninguna se termina en la semana 3 ni se queda sola al final)
    cambios = 0
    for k, (_h, it) in enumerate(_intercalar(colas, {h: len(q) for h, q in colas.items()})):
        semana = inicio + k // spw
        if int(it["semana"] or 0) != semana:
            db.actualizar_item(it["id"], semana=semana)
            cambios += 1
    return cambios


def _nivel_inicial(hid: str, diag: dict, ob: dict) -> str:
    """Nivel de arranque por habilidad: lo que dijo Elena (ventas, entrevistas, Ruta DM) o la experiencia declarada, moderada por las competencias del diagnóstico."""
    if hid == "ventas":
        return diag.get("nivel_ventas") or C.nivel_ventas_estimado(ob)
    if hid == "entrevistas":
        return diag.get("nivel_entrevistas") or "Principiante"
    if hid == "ruta_dm":
        return diag.get("nivel_dm") or C.nivel_dm_estimado(ob)
    comps = {c.get("nombre"): int(c.get("nivel", 0)) for c in diag.get("competencias", []) if isinstance(c, dict)}
    clave = {"presentaciones": "Comunicación", "comunicacion": "Comunicación", "liderazgo": "Liderazgo / influencia", "imagen": "Adaptabilidad / aprendizaje"}.get(hid, "Comunicación")
    n = comps.get(clave, 0)
    estimado = C.nivel_generico_estimado(ob)
    if n >= 4:
        return "Avanzado" if estimado == "Avanzado" else "Intermedio"
    if n in (1, 2):
        return "Principiante"
    return estimado


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
                    diagnostico: dict | None = None, motivo: str = "diagnóstico inicial", agregado_por: str = "elena", n_items: int | None = None,
                    reprogramar: bool = True) -> int:
    hab = C.HABILIDADES[habilidad_id]
    perfil = db.perfil(usuario["id"])
    ob = perfil.get("onboarding", {})
    diag = diagnostico or perfil.get("diagnostico") or {}
    niv = db.nivel(usuario["id"], habilidad_id) or {}
    nivel = niv.get("nivel") or hab["niveles"][0]
    horizonte = _horizonte(brecha)
    n_items = max(2, min(16, n_items)) if n_items else max(3, min(16, horizonte * sesiones_semana))
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
    if habilidad_id == "ruta_dm":
        items = _intercalar_laboratorio(usuario, items, nivel)
    rid = db.crear_roadmap(usuario["id"], habilidad_id, nivel, objetivo=js.get("objetivo") or f"Avanzar en {hab['nombre']} desde {nivel}",
                           razon=js.get("razon") or motivo, items=items, horizonte=horizonte, sesiones_semana=sesiones_semana, requiere_aprobacion=requiere_aprobacion)
    if requiere_aprobacion and usuario.get("empresa_id"):
        db.crear_propuesta(usuario["empresa_id"], "roadmap", f"Aprobar roadmap de {hab['nombre']} para {usuario['nombre']}",
                           {"roadmap_id": rid, "habilidad": habilidad_id, "nivel": nivel, "sesiones": len(items), "horizonte": horizonte},
                           evidencia=f"La habilidad no forma parte del rol declarado ({', '.join(ob.get('funciones') or []) or 'sin funciones'}); "
                                     f"Elena la propone por brecha {brecha}.", usuario_id=usuario["id"], clave=f"roadmap:{rid}")
    if reprogramar:
        reprogramar_plan_integral(usuario)
    return rid


def _intercalar_laboratorio(usuario: dict, items: list[dict], nivel: str) -> list[dict]:
    """La Ruta DM arranca con el Laboratorio DM (si la persona nunca lo ha hecho) y repite un checkpoint cada CHECKPOINT_CADA sesiones."""
    from . import laboratorio as L
    hechos = db.sesiones(usuario_id=usuario["id"], habilidad="ruta_dm", estado="completada", tipo="laboratorio", limite=1)
    out: list[dict] = []
    if not hechos:
        out.append({"semana": 1, "nivel": nivel, "competencia": "", "formato": "laboratorio", "tipo": "laboratorio", "agregado_por": "elena",
                    "objetivo": "Laboratorio DM: dos casos reales (entrega bajo presión y war room) que miden escucha activa, manejo del estrés, gestión de proyectos y comunicación ejecutiva",
                    "porque": "Es el punto de partida de la Ruta DM: fija tu evidencia inicial en cuatro competencias y la prioridad de tu plan."})
    for i, it in enumerate(items, start=1):
        out.append(it)
        if i % L.CHECKPOINT_CADA == 0 and i < len(items):
            out.append({"semana": it["semana"], "nivel": nivel, "competencia": "", "formato": "laboratorio", "tipo": "laboratorio", "agregado_por": "elena",
                        "objetivo": "Checkpoint del Laboratorio DM: dos casos nuevos para medir tu avance en escucha, presión, gestión de proyectos y comunicación ejecutiva",
                        "porque": f"Cada {L.CHECKPOINT_CADA} sesiones el laboratorio vuelve a medirte con casos distintos (sin memorización)."})
    return out


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
