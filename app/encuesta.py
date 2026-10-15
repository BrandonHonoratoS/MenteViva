"""Encuesta de primera experiencia (fase productiva inicial): datos generales, experiencia, valor y precio, mejoras.

Se pide una sola vez, después de la primera práctica completada con cualquier avatar. Las preguntas viven aquí para poder
ajustarlas sin tocar plantillas; RRHH ve las respuestas de su empresa sin la sección de precio (es investigación de producto
del equipo Mente Viva), el superadmin ve todo y ambos pueden exportar a Excel.
"""
from __future__ import annotations

SECCIONES: list[dict] = [
    {"id": "general", "titulo": "Sobre ti", "preguntas": [
        {"id": "edad", "texto": "Rango de edad", "tipo": "opcion", "opciones": ["18–24", "25–34", "35–44", "45–54", "55+"]},
        {"id": "experiencia", "texto": "Años de experiencia profesional", "tipo": "opcion", "opciones": ["Menos de 2", "2 a 5", "6 a 10", "11 a 20", "Más de 20"]},
        {"id": "uso_ia", "texto": "¿Qué tanto usas herramientas de IA en tu trabajo?", "tipo": "opcion", "opciones": ["Nunca", "Ocasionalmente", "Cada semana", "Todos los días"]},
        {"id": "dispositivo", "texto": "¿Desde qué dispositivo usaste Mente Viva?", "tipo": "opcion", "opciones": ["Computadora", "Celular", "Ambos"]},
        {"id": "capacitacion_previa", "texto": "¿Has tomado antes capacitación en habilidades blandas (cursos, coaching, talleres)?", "tipo": "opcion", "opciones": ["No", "Sí, presencial", "Sí, en línea", "Sí, ambas"]},
    ]},
    {"id": "experiencia", "titulo": "Tu experiencia", "preguntas": [
        {"id": "calificacion", "texto": "¿Cómo calificas tu experiencia en general?", "tipo": "escala", "min": 1, "max": 10},
        {"id": "realismo", "texto": "¿Qué tan realista fue la conversación con el avatar?", "tipo": "escala", "min": 1, "max": 5},
        {"id": "utilidad_feedback", "texto": "¿Qué tan útil y accionable fue la retroalimentación?", "tipo": "escala", "min": 1, "max": 5},
        {"id": "facilidad", "texto": "¿Qué tan fácil fue usar la plataforma?", "tipo": "escala", "min": 1, "max": 5},
        {"id": "aprendizaje", "texto": "¿Sientes que aprendiste algo que puedes aplicar esta semana?", "tipo": "opcion", "opciones": ["Sí, claramente", "Algo", "Poco", "Nada"]},
        {"id": "nps", "texto": "¿Qué tan probable es que recomiendes Mente Viva a un colega? (0 = nada probable, 10 = seguro)", "tipo": "escala", "min": 0, "max": 10},
        {"id": "gusto", "texto": "¿Qué fue lo que más te gustó?", "tipo": "texto"},
        {"id": "mejora", "texto": "¿Qué cambiarías o mejorarías?", "tipo": "texto"},
        {"id": "fallo", "texto": "¿Algo falló o te confundió? Cuéntanos qué pasó", "tipo": "texto", "opcional": True},
    ]},
    {"id": "valor", "titulo": "Valor y precio", "precio": True, "preguntas": [
        {"id": "pagaria", "texto": "¿Pagarías por una solución como Mente Viva?", "tipo": "opcion", "opciones": ["Sí", "Tal vez", "No"]},
        {"id": "precio_unico", "texto": "¿Cuánto pagarías por esta solución (MXN, por persona)?", "tipo": "numero", "sufijo": "MXN"},
        {"id": "plan_mensual", "texto": "Si fuera un plan mensual, ¿lo pagarías?", "tipo": "opcion", "opciones": ["Sí", "Tal vez", "No"]},
        {"id": "precio_mensual", "texto": "¿Cuánto al mes te parecería justo?", "tipo": "opcion", "opciones": ["Menos de $200", "$200–$499", "$500–$999", "$1,000–$1,999", "$2,000 o más"]},
        {"id": "quien_paga", "texto": "¿Quién debería pagarlo?", "tipo": "opcion", "opciones": ["Mi empresa", "Yo", "Ambos (copago)"]},
        {"id": "funciones", "texto": "¿Qué te haría pagar más? (elige todas las que apliquen)", "tipo": "multiple",
         "opciones": ["Avatares con voz", "Avatares con video", "Realidad virtual", "Más escenarios y habilidades", "Certificado o constancia", "Reportes para mi líder", "App móvil", "Integración con mi ERP/CRM", "Sesiones con coach humano"]},
        {"id": "comparacion", "texto": "¿Con qué comparas esta solución (un curso, un coach, otra app)? ¿Qué pagas hoy por eso?", "tipo": "texto", "opcional": True},
    ]},
    {"id": "cierre", "titulo": "Para terminar", "preguntas": [
        {"id": "entrevista", "texto": "¿Podemos contactarte para una entrevista de 15 minutos sobre tu experiencia?", "tipo": "opcion", "opciones": ["Sí", "No"]},
        {"id": "comentario", "texto": "¿Algo más que quieras decirle al equipo de Mente Viva?", "tipo": "texto", "opcional": True},
    ]},
]

PREGUNTAS = {p["id"]: {**p, "seccion": s["id"], "precio": bool(s.get("precio"))} for s in SECCIONES for p in s["preguntas"]}


def validar(form: dict) -> tuple[dict, list[str]]:
    """Normaliza las respuestas del formulario; devuelve (respuestas, faltantes)."""
    out, faltan = {}, []
    for pid, p in PREGUNTAS.items():
        if p["tipo"] == "multiple":
            vals = [v for v in form.getlist(pid) if v in p["opciones"]] if hasattr(form, "getlist") else [v for v in (form.get(pid) or []) if v in p["opciones"]]
            out[pid] = vals
            continue
        v = str(form.get(pid, "") or "").strip()
        if p["tipo"] == "escala":
            try:
                n = int(v)
                v = n if p["min"] <= n <= p["max"] else ""
            except ValueError:
                v = ""
        elif p["tipo"] == "numero":
            try:
                v = round(float(v.replace(",", "").replace("$", "")), 2) if v else ""
            except ValueError:
                v = ""
        elif p["tipo"] == "opcion":
            v = v if v in p["opciones"] else ""
        else:
            v = v[:1500]
        if v == "" and not p.get("opcional"):
            faltan.append(pid)
        out[pid] = v
    return out, faltan


def columnas(incluir_precio: bool) -> list[tuple[str, str]]:
    return [(pid, p["texto"]) for pid, p in PREGUNTAS.items() if incluir_precio or not p["precio"]]


def resumen(encuestas: list[dict], incluir_precio: bool) -> dict:
    """Promedios y distribuciones para la vista de RRHH / superadmin."""
    def prom(pid):
        vals = [float(e["respuestas"].get(pid)) for e in encuestas if isinstance(e["respuestas"].get(pid), (int, float))]
        return round(sum(vals) / len(vals), 1) if vals else None

    def dist(pid):
        d: dict[str, int] = {}
        for e in encuestas:
            v = e["respuestas"].get(pid)
            for x in (v if isinstance(v, list) else [v]):
                if x not in ("", None):
                    d[str(x)] = d.get(str(x), 0) + 1
        return dict(sorted(d.items(), key=lambda kv: -kv[1]))

    nps_vals = [int(e["respuestas"].get("nps")) for e in encuestas if isinstance(e["respuestas"].get("nps"), int)]
    nps = None
    if nps_vals:
        prom_ = sum(1 for v in nps_vals if v >= 9) / len(nps_vals)
        det = sum(1 for v in nps_vals if v <= 6) / len(nps_vals)
        nps = round((prom_ - det) * 100)
    out = {"n": len(encuestas), "calificacion": prom("calificacion"), "realismo": prom("realismo"), "utilidad_feedback": prom("utilidad_feedback"), "facilidad": prom("facilidad"),
           "nps": nps, "aprendizaje": dist("aprendizaje"), "entrevista": dist("entrevista")}
    if incluir_precio:
        out.update({"pagaria": dist("pagaria"), "plan_mensual": dist("plan_mensual"), "precio_mensual": dist("precio_mensual"), "quien_paga": dist("quien_paga"),
                    "funciones": dist("funciones"), "precio_unico": prom("precio_unico")})
    return out
