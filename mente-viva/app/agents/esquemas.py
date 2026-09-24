"""Esquemas JSON de las salidas de los agentes (se pasan a Gemini como response_json_schema)."""
from __future__ import annotations


def _s(desc: str = "") -> dict:
    return {"type": "string", "description": desc} if desc else {"type": "string"}


def _n(lo: float, hi: float, desc: str = "") -> dict:
    d = {"type": "number", "minimum": lo, "maximum": hi}
    if desc:
        d["description"] = desc
    return d


def _i(lo: int, hi: int, desc: str = "") -> dict:
    d = {"type": "integer", "minimum": lo, "maximum": hi}
    if desc:
        d["description"] = desc
    return d


def _arr(items: dict, mn: int = 1, mx: int | None = None) -> dict:
    d = {"type": "array", "items": items, "minItems": mn}
    if mx:
        d["maxItems"] = mx
    return d


def _obj(props: dict, req: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": req or list(props.keys())}


# ── turnos de conversación ───────────────────────────────────────────────────
TURNO_ELENA_DIAG = _obj({"mensaje": _s(), "fase": {"type": "string", "enum": ["rapport", "encuadre", "desarrollo", "profundizacion", "cierre", "fin"]},
                         "historias": _i(0, 10)})
TURNO_ELENA_PRACT = _obj({"mensaje": _s(), "fase": {"type": "string", "enum": ["rapport", "encuadre", "desarrollo", "profundizacion", "cierre", "fin"]},
                          "tension": _i(0, 100)})
TURNO_CELESTE = _obj({"mensaje": _s(), "tension": _i(0, 100), "estado": {"type": "string", "enum": ["en_curso", "cerrando", "fin"]}, "etapa": _s()})
TURNO_JUAN = _obj({"mensaje": _s(), "tension": _i(0, 100), "estado": {"type": "string", "enum": ["en_curso", "cerrando", "fin"]}})
RESUMEN = _obj({"memoria": _s()})

# ── diagnóstico de Elena ─────────────────────────────────────────────────────
COMPETENCIA = _obj({"nombre": _s(), "nivel": _i(0, 5), "justificacion": _s("evidencia observada o 'sin evidencia'")})
FORTALEZA = _obj({"habilidad": _s(), "evidencia": _s("frase textual o momento"), "por_que_importa": _s()})
OPORTUNIDAD = _obj({"habilidad": _s(), "evidencia": _s(), "impacto": _s(), "micro_practica": _s("práctica concreta para esta semana")})
PRIORIDAD = _obj({"habilidad_id": _s("id del catálogo"), "brecha": {"type": "string", "enum": ["alta", "media", "baja"]}, "razon": _s(),
                  "competencias_relacionadas": _arr(_s(), 0)})
ELENA_DIAGNOSTICO = _obj({
    "resumen_ejecutivo": _s("3-4 líneas"),
    "fortalezas": _arr(FORTALEZA, 1, 3),
    "oportunidades": _arr(OPORTUNIDAD, 1, 3),
    "blind_spot": _s(),
    "pregunta_para_llevarse": _s(),
    "competencias": _arr(COMPETENCIA, 10, 10),
    "estilo_comunicacion": _s(),
    "nivel_ventas": {"type": "string", "enum": ["Principiante", "Intermedio", "Avanzado"]},
    "nivel_ventas_justificacion": _s(),
    "nivel_dm": {"type": "string", "enum": ["DM Básico", "DM1", "DM2", "DM3", "DM4", "DM5", "Emprendedor"]},
    "nivel_dm_justificacion": _s(),
    "nivel_entrevistas": {"type": "string", "enum": ["Principiante", "Intermedio", "Avanzado"]},
    "prioridades": _arr(PRIORIDAD, 1, 4),
    "mensaje_para_la_persona": _s("cierre cálido de 2-3 líneas en voz de Elena"),
})

# ── feedback de sesiones ─────────────────────────────────────────────────────
KPI_EVAL = _obj({"id": _s("KPI-1..KPI-6"), "score": _i(0, 100), "evidencia": _s("turno y frase"), "bien": _s(), "mejora": _s()})
MOMENTO = _obj({"turno": _i(0, 200), "tipo": {"type": "string", "enum": ["destacó", "falló"]}, "que_paso": _s(), "que_habria_cambiado": _s()})
PASO = _obj({"paso": _s(), "como_medir": _s()})
RECOMENDACION = _obj({"nivel_sugerido": {"type": "string", "enum": ["Principiante", "Intermedio", "Avanzado"]}, "objetivo_siguiente": _s("objetivo medible"), "razon": _s()})

TECNICA = _obj({"id": _s("T-01..T-08"), "turno": _i(0, 200)})
EVIDENCIA_VENTAS = _obj({
    "tecnicas_usadas": _arr(TECNICA, 0),
    "spin": _obj({"S": _i(0, 50), "P": _i(0, 50), "I": _i(0, 50), "N": _i(0, 50)}),
    "etapas_cumplidas": _arr(_s(), 0),
    "turno_primer_descuento": _i(0, 200, "0 si no ofreció descuento"),
    "uso_silencio_activo": {"type": "boolean"},
    "objeciones_lanzadas": _i(0, 10), "objeciones_resueltas": _i(0, 10),
    "cierre": {"type": "string", "enum": ["sin_cierre", "siguiente_paso", "venta", "fallido_por_ceder"]},
})
FEEDBACK_VENTAS = _obj({
    "resumen": _s(), "kpis": _arr(KPI_EVAL, 6, 6), "evidencia": EVIDENCIA_VENTAS,
    "fortalezas": _arr(FORTALEZA, 1, 3), "oportunidades": _arr(OPORTUNIDAD, 1, 3), "momentos_clave": _arr(MOMENTO, 1, 5),
    "plan_accion": _arr(PASO, 3, 3), "tips": _arr(_s(), 3, 5), "pregunta_para_llevarse": _s(),
    "metrica_etapa_debil": _s("cómo le fue en la etapa débil declarada, con número"), "recomendacion": RECOMENDACION,
})
FEEDBACK_ENTREVISTAS = _obj({
    "resumen": _s(), "kpis": _arr(KPI_EVAL, 5, 5),
    "fortalezas": _arr(FORTALEZA, 1, 3), "oportunidades": _arr(OPORTUNIDAD, 1, 3), "blind_spot": _s(), "momentos_clave": _arr(MOMENTO, 1, 5),
    "plan_accion": _arr(PASO, 3, 3), "tips": _arr(_s(), 3, 5), "pregunta_para_llevarse": _s(), "recomendacion": RECOMENDACION,
})
SUBDIM = _obj({"nombre": _s(), "score": _n(0, 10), "evidencia": _s()})
BRECHA = _obj({"brecha": _s(), "evidencia": _s(), "impacto_siguiente_nivel": _s(), "causa_probable": _s()})
PASO_DM = _obj({"paso": _s(), "como_practicar_esta_semana": _s(), "senal_de_logro": _s()})
FEEDBACK_DM = _obj({
    "resumen": _s(), "subdimensiones": _arr(SUBDIM, 3, 4), "score_global": _n(0, 10),
    "nivel_dominio": {"type": "string", "enum": ["Principiante", "En desarrollo", "Sólido", "Listo para el siguiente nivel"]}, "justificacion": _s(),
    "fortalezas": _arr(FORTALEZA, 1, 3), "brechas": _arr(BRECHA, 1, 3),
    "momento_clave": _obj({"que_hizo": _s(), "alternativa": _s(), "que_habria_cambiado": _s()}),
    "plan_accion": _arr(PASO_DM, 3, 4), "tips": _arr(_s(), 3, 5),
    "siguiente_paso": _obj({"competencia": _s(), "por_que": _s()}),
})
JUAN_DISENO = _obj({
    "formato": {"type": "string", "enum": ["roleplay", "caso", "reto"]}, "titulo": _s(), "encuadre": _s(), "personaje": _s(),
    "situacion": _s(), "primer_mensaje": _s(), "subdimensiones": _arr(_s(), 3, 4), "dificultad_inicial": _i(1, 5),
})

# ── analista ─────────────────────────────────────────────────────────────────
ANALISTA_POST = _obj({
    "lectura": _s(), "riesgo": {"type": "string", "enum": ["bajo", "medio", "alto"]}, "riesgo_motivo": _s(), "recomendacion_lider": _s(),
    "siguiente_objetivo": _s(), "ajuste_plan": {"type": "string", "enum": ["ninguno", "refuerzo", "subir_nivel", "bajar_nivel", "cambiar_foco"]},
    "ajuste_motivo": _s(), "senales": _arr(_s(), 2, 4),
})
RECO = _obj({"accion": _s(), "responsable": _s(), "senal_exito": _s(), "prioridad": {"type": "string", "enum": ["alta", "media", "baja"]}})
ANALISTA_RESUMEN = _obj({"titulo": _s(), "resumen": _s(), "avanzan": _arr(_s(), 0, 5), "atencion": _arr(_s(), 0, 5), "recomendaciones": _arr(RECO, 1, 3)})
HALLAZGO = _obj({"hallazgo": _s(), "fuente": _s("dominio o título")})
INVESTIGACION = _obj({"hallazgos": _arr(HALLAZGO, 1, 5), "aplicacion": _s(), "confianza": {"type": "string", "enum": ["alto", "medio", "bajo"]}, "confianza_motivo": _s()})

# ── roadmaps ─────────────────────────────────────────────────────────────────
ITEM_RM = _obj({"semana": _i(1, 12), "nivel": _s(), "competencia": _s("sólo ruta_dm; vacío en otras"), "objetivo": _s("objetivo medible de la sesión"), "porque": _s("una línea")})
ROADMAP = _obj({"objetivo": _s("meta del plan en una línea"), "razon": _s("por qué este orden, 2-3 líneas"), "items": _arr(ITEM_RM, 3, 16)})
