"""Normalización defensiva de las salidas de la IA.

Gemini respeta el esquema JSON casi siempre, pero un campo ausente, un score fuera de rango o un id de KPI mal escrito no deben
romper una sesión. Cada función devuelve un dict completo y coherente; lo que falta se rellena con valores neutros y se registra.
"""
from __future__ import annotations

from .. import db
from . import catalogo as C


def _num(v, lo: float, hi: float, default: float = 0.0) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default


def _lista(v, n_min: int = 0) -> list:
    return v if isinstance(v, list) else []


def _texto(v, default: str = "") -> str:
    return v.strip() if isinstance(v, str) and v.strip() else default


def turno(js: dict | None, texto_bruto: str) -> dict:
    """Turno de un avatar: garantiza mensaje y valores válidos; si no hay JSON, usa el texto plano si parece texto."""
    js = js if isinstance(js, dict) else {}
    mensaje = _texto(js.get("mensaje"))
    if not mensaje:
        bruto = (texto_bruto or "").strip()
        if bruto and not bruto.startswith("{"):
            mensaje = bruto[:1500]
    out = {"mensaje": mensaje}
    if "tension" in js:
        out["tension"] = int(_num(js.get("tension"), 0, 100))
    if "estado" in js:
        out["estado"] = js["estado"] if js["estado"] in ("en_curso", "cerrando", "fin") else "en_curso"
    if "fase" in js:
        out["fase"] = js["fase"] if js["fase"] in ("rapport", "encuadre", "desarrollo", "profundizacion", "cierre", "fin") else "desarrollo"
    if "historias" in js:
        out["historias"] = int(_num(js.get("historias"), 0, 10))
    if "etapa" in js:
        out["etapa"] = _texto(js.get("etapa"))[:40]
    return out


def _kpis(lista, hab: dict) -> list[dict]:
    """Alinea los KPIs devueltos con el catálogo: por id, o por posición si el id viene mal."""
    defs = hab.get("kpis", [])
    por_id = {k.get("id"): k for k in _lista(lista) if isinstance(k, dict)}
    out = []
    for i, d in enumerate(defs):
        k = por_id.get(d["id"]) or (_lista(lista)[i] if i < len(_lista(lista)) and isinstance(_lista(lista)[i], dict) else {})
        out.append({"id": d["id"], "nombre": d["nombre"], "score": int(_num(k.get("score"), 0, 100)), "evidencia": _texto(k.get("evidencia"), "Sin evidencia citada."),
                    "bien": _texto(k.get("bien"), "—"), "mejora": _texto(k.get("mejora"), "—")})
    return out


def _items(lista, campos: dict, n_max: int) -> list[dict]:
    out = []
    for x in _lista(lista)[:n_max]:
        if isinstance(x, dict):
            out.append({k: _texto(x.get(k), d) for k, d in campos.items()})
        elif isinstance(x, str) and x.strip():
            out.append({k: (x.strip() if i == 0 else d) for i, (k, d) in enumerate(campos.items())})
    return out


def _momentos(lista) -> list[dict]:
    out = []
    for m in _lista(lista)[:5]:
        if isinstance(m, dict):
            out.append({"turno": int(_num(m.get("turno"), 0, 200)), "tipo": "destacó" if m.get("tipo") == "destacó" else "falló",
                        "que_paso": _texto(m.get("que_paso")), "que_habria_cambiado": _texto(m.get("que_habria_cambiado"), "—")})
    return out


def _recomendacion(r, niveles: list[str], nivel_actual: str) -> dict:
    r = r if isinstance(r, dict) else {}
    return {"nivel_sugerido": r.get("nivel_sugerido") if r.get("nivel_sugerido") in niveles else nivel_actual,
            "objetivo_siguiente": _texto(r.get("objetivo_siguiente"), "Consolidar lo trabajado en esta sesión")[:300], "razon": _texto(r.get("razon"))}


def feedback_ventas(js: dict | None, sesion: dict) -> dict:
    js = js if isinstance(js, dict) else {}
    hab = C.HABILIDADES["ventas"]
    ev = js.get("evidencia") if isinstance(js.get("evidencia"), dict) else {}
    spin = ev.get("spin") if isinstance(ev.get("spin"), dict) else {}
    out = {
        "resumen": _texto(js.get("resumen"), "Sesión analizada."), "kpis": _kpis(js.get("kpis"), hab),
        "evidencia": {"tecnicas_usadas": [{"id": _texto(t.get("id")), "turno": int(_num(t.get("turno"), 0, 200))} for t in _lista(ev.get("tecnicas_usadas")) if isinstance(t, dict) and t.get("id")],
                      "spin": {k: int(_num(spin.get(k), 0, 50)) for k in ("S", "P", "I", "N")}, "etapas_cumplidas": [str(e) for e in _lista(ev.get("etapas_cumplidas"))][:10],
                      "turno_primer_descuento": int(_num(ev.get("turno_primer_descuento"), 0, 200)), "uso_silencio_activo": bool(ev.get("uso_silencio_activo")),
                      "objeciones_lanzadas": int(_num(ev.get("objeciones_lanzadas"), 0, 10)), "objeciones_resueltas": int(_num(ev.get("objeciones_resueltas"), 0, 10)),
                      "cierre": ev.get("cierre") if ev.get("cierre") in ("sin_cierre", "siguiente_paso", "venta", "fallido_por_ceder") else "sin_cierre"},
        "fortalezas": _items(js.get("fortalezas"), {"habilidad": "Fortaleza", "evidencia": "", "por_que_importa": ""}, 3),
        "oportunidades": _items(js.get("oportunidades"), {"habilidad": "Oportunidad", "evidencia": "", "impacto": "", "micro_practica": "Practica esto en tu siguiente sesión."}, 3),
        "momentos_clave": _momentos(js.get("momentos_clave")), "plan_accion": _items(js.get("plan_accion"), {"paso": "", "como_medir": ""}, 3),
        "tips": [str(t) for t in _lista(js.get("tips")) if str(t).strip()][:5], "pregunta_para_llevarse": _texto(js.get("pregunta_para_llevarse")),
        "metrica_etapa_debil": _texto(js.get("metrica_etapa_debil")), "recomendacion": _recomendacion(js.get("recomendacion"), hab["niveles"], sesion.get("nivel") or "Principiante"),
    }
    return out


def feedback_entrevistas(js: dict | None, sesion: dict) -> dict:
    js = js if isinstance(js, dict) else {}
    hab = C.HABILIDADES["entrevistas"]
    return {
        "resumen": _texto(js.get("resumen"), "Sesión analizada."), "kpis": _kpis(js.get("kpis"), hab),
        "fortalezas": _items(js.get("fortalezas"), {"habilidad": "Fortaleza", "evidencia": "", "por_que_importa": ""}, 3),
        "oportunidades": _items(js.get("oportunidades"), {"habilidad": "Oportunidad", "evidencia": "", "impacto": "", "micro_practica": "Practica esto en tu siguiente sesión."}, 3),
        "blind_spot": _texto(js.get("blind_spot")), "momentos_clave": _momentos(js.get("momentos_clave")),
        "plan_accion": _items(js.get("plan_accion"), {"paso": "", "como_medir": ""}, 3), "tips": [str(t) for t in _lista(js.get("tips")) if str(t).strip()][:5],
        "pregunta_para_llevarse": _texto(js.get("pregunta_para_llevarse")), "recomendacion": _recomendacion(js.get("recomendacion"), hab["niveles"], sesion.get("nivel") or "Principiante"),
    }


def feedback_dm(js: dict | None, sesion: dict) -> dict:
    js = js if isinstance(js, dict) else {}
    esc = sesion.get("escenario") or {}
    subs = []
    for i, s in enumerate(_lista(js.get("subdimensiones"))[:4]):
        if isinstance(s, dict):
            subs.append({"nombre": _texto(s.get("nombre"), f"Sub-dimensión {i + 1}"), "score": round(_num(s.get("score"), 0, 10), 1), "evidencia": _texto(s.get("evidencia"), "Sin evidencia citada.")})
    if not subs:
        subs = [{"nombre": n, "score": round(_num(js.get("score_global"), 0, 10), 1), "evidencia": "Sin desglose."} for n in (esc.get("subdimensiones") or ["Desempeño"])[:4]]
    glob = round(_num(js.get("score_global"), 0, 10, default=sum(s["score"] for s in subs) / len(subs)), 1)
    sig = C.nivel_dm_siguiente(sesion.get("nivel") or "DM Básico") or (sesion.get("nivel") or "DM1")
    comps = C.competencias_dm(sig)
    sp = js.get("siguiente_paso") if isinstance(js.get("siguiente_paso"), dict) else {}
    comp_sig = sp.get("competencia") if sp.get("competencia") in comps else next((c for c in comps if c != sesion.get("competencia")), comps[0] if comps else "")
    mc = js.get("momento_clave") if isinstance(js.get("momento_clave"), dict) else {}
    return {
        "resumen": _texto(js.get("resumen"), "Ejercicio analizado."), "subdimensiones": subs, "score_global": glob,
        "nivel_dominio": js.get("nivel_dominio") if js.get("nivel_dominio") in ("Principiante", "En desarrollo", "Sólido", "Listo para el siguiente nivel") else C.dominio_dm(glob),
        "justificacion": _texto(js.get("justificacion")),
        "fortalezas": _items(js.get("fortalezas"), {"habilidad": "Fortaleza", "evidencia": "", "por_que_importa": ""}, 3),
        "brechas": _items(js.get("brechas"), {"brecha": "Brecha", "evidencia": "", "impacto_siguiente_nivel": "", "causa_probable": ""}, 3),
        "momento_clave": {"que_hizo": _texto(mc.get("que_hizo")), "alternativa": _texto(mc.get("alternativa")), "que_habria_cambiado": _texto(mc.get("que_habria_cambiado"))},
        "plan_accion": _items(js.get("plan_accion"), {"paso": "", "como_practicar_esta_semana": "", "senal_de_logro": ""}, 4),
        "tips": [str(t) for t in _lista(js.get("tips")) if str(t).strip()][:5], "siguiente_paso": {"competencia": comp_sig, "por_que": _texto(sp.get("por_que"))},
    }


def diseno_juan(js: dict | None, sesion: dict) -> dict:
    js = js if isinstance(js, dict) else {}
    comp = sesion.get("competencia") or "la competencia"
    formato = js.get("formato") if js.get("formato") in ("roleplay", "caso", "reto") else C.formato_sugerido(comp)
    subs = [str(s) for s in _lista(js.get("subdimensiones")) if str(s).strip()][:4] or ["Claridad", "Escucha", "Criterio", "Firmeza"]
    return {"formato": formato, "titulo": _texto(js.get("titulo"), f"Ejercicio de {comp}")[:120], "encuadre": _texto(js.get("encuadre"), f"Hoy entrenamos {comp}, clave para tu siguiente nivel."),
            "personaje": _texto(js.get("personaje")) if formato == "roleplay" else "", "situacion": _texto(js.get("situacion"), "Situación del contexto Cóndor."),
            "primer_mensaje": _texto(js.get("primer_mensaje")), "subdimensiones": subs, "dificultad_inicial": int(_num(js.get("dificultad_inicial"), 1, 5, default=2))}


def diagnostico(js: dict | None, onboarding: dict) -> dict:
    js = js if isinstance(js, dict) else {}
    comps_in = {c.get("nombre"): c for c in _lista(js.get("competencias")) if isinstance(c, dict)}
    competencias = []
    for i, nombre in enumerate(C.COMPETENCIAS_DIAGNOSTICO):
        c = comps_in.get(nombre) or (_lista(js.get("competencias"))[i] if i < len(_lista(js.get("competencias"))) and isinstance(_lista(js.get("competencias"))[i], dict) else {})
        competencias.append({"nombre": nombre, "nivel": int(_num(c.get("nivel"), 0, 5)), "justificacion": _texto(c.get("justificacion"), "Sin evidencia en la entrevista.")})
    prioridades = []
    for p in _lista(js.get("prioridades")):
        if isinstance(p, dict) and p.get("habilidad_id") in C.HABILIDADES:
            prioridades.append({"habilidad_id": p["habilidad_id"], "brecha": p.get("brecha") if p.get("brecha") in ("alta", "media", "baja") else "media",
                                "razon": _texto(p.get("razon")), "competencias_relacionadas": [str(x) for x in _lista(p.get("competencias_relacionadas"))][:5]})
    if not prioridades:
        usa = C.habilidades_que_usa(onboarding)
        prioridades = [{"habilidad_id": h, "brecha": "media", "razon": "Habilidad del rol declarado.", "competencias_relacionadas": []} for h in ("ventas", "entrevistas") if h in usa]
    return {
        "resumen_ejecutivo": _texto(js.get("resumen_ejecutivo"), "Diagnóstico completado."),
        "fortalezas": _items(js.get("fortalezas"), {"habilidad": "Fortaleza", "evidencia": "", "por_que_importa": ""}, 3),
        "oportunidades": _items(js.get("oportunidades"), {"habilidad": "Oportunidad", "evidencia": "", "impacto": "", "micro_practica": ""}, 3),
        "blind_spot": _texto(js.get("blind_spot")), "pregunta_para_llevarse": _texto(js.get("pregunta_para_llevarse")), "competencias": competencias,
        "estilo_comunicacion": _texto(js.get("estilo_comunicacion"), onboarding.get("estilo", "")),
        "nivel_ventas": js.get("nivel_ventas") if js.get("nivel_ventas") in C.NIVELES_3 else C.nivel_ventas_estimado(onboarding),
        "nivel_ventas_justificacion": _texto(js.get("nivel_ventas_justificacion")),
        "nivel_dm": js.get("nivel_dm") if js.get("nivel_dm") in C.NIVELES_DM else C.nivel_dm_estimado(onboarding),
        "nivel_dm_justificacion": _texto(js.get("nivel_dm_justificacion")),
        "nivel_entrevistas": js.get("nivel_entrevistas") if js.get("nivel_entrevistas") in C.NIVELES_3 else "Principiante",
        "prioridades": prioridades, "mensaje_para_la_persona": _texto(js.get("mensaje_para_la_persona")),
    }


def analista_post(js: dict | None) -> dict | None:
    if not isinstance(js, dict) or not js.get("lectura"):
        return None
    return {"lectura": _texto(js.get("lectura")), "riesgo": js.get("riesgo") if js.get("riesgo") in ("bajo", "medio", "alto") else "medio",
            "riesgo_motivo": _texto(js.get("riesgo_motivo")), "recomendacion_lider": _texto(js.get("recomendacion_lider")),
            "siguiente_objetivo": _texto(js.get("siguiente_objetivo"))[:300],
            "ajuste_plan": js.get("ajuste_plan") if js.get("ajuste_plan") in ("ninguno", "refuerzo", "subir_nivel", "bajar_nivel", "cambiar_foco") else "ninguno",
            "ajuste_motivo": _texto(js.get("ajuste_motivo")), "senales": [str(s) for s in _lista(js.get("senales"))][:4]}


def registrar_si_incompleto(origen: str, js, usuario: str = "") -> None:
    if not isinstance(js, dict):
        db.log("warn", "llm", f"Salida no estructurada en {origen}; se normalizó", str(js)[:200], usuario)
