"""Encuesta de primera experiencia (fase productiva inicial): datos generales, experiencia, valor y precio, mejoras.

Se pide una sola vez, después de la primera práctica completada con cualquier avatar. Las preguntas viven aquí para poder
ajustarlas sin tocar plantillas; RRHH ve las respuestas de su empresa sin la sección de precio (es investigación de producto
del equipo Mente Viva), el superadmin ve todo y ambos pueden exportar a Excel.
"""
from __future__ import annotations

INTRO = ("Mente Viva es un espacio para desarrollar habilidades mediante prácticas con Inteligencia Artificial. Queremos conocer tu experiencia y entender "
         "qué tan valiosa te resulta la plataforma. Responder esta encuesta no implica ningún compromiso de pago.")
SECCIONES: list[dict] = [
    {"id": "general", "titulo": "Conociendo al usuario", "preguntas": [
        {"id": "relacion", "texto": "¿Cuál es tu relación con Mente Viva?", "tipo": "opcion", "opciones": ["Colaborador de mi empresa", "Usuario externo / público general"]},
        {"id": "veces_uso", "texto": "¿Cuántas veces has utilizado Mente Viva?", "tipo": "opcion", "opciones": ["Una vez", "De 2 a 3 veces", "4 o más veces"]},
        {"id": "edad", "texto": "Rango de edad", "tipo": "opcion", "opciones": ["18–24", "25–34", "35–44", "45–54", "55+"]},
        {"id": "experiencia", "texto": "Años de experiencia profesional", "tipo": "opcion", "opciones": ["Menos de 2", "2 a 5", "6 a 10", "11 a 20", "Más de 20"]},
        {"id": "uso_ia", "texto": "¿Qué tanto usas herramientas de IA en tu trabajo?", "tipo": "opcion", "opciones": ["Nunca", "Ocasionalmente", "Cada semana", "Todos los días"]},
        {"id": "dispositivo", "texto": "¿Desde qué dispositivo usaste Mente Viva?", "tipo": "opcion", "opciones": ["Computadora", "Celular", "Ambos"]},
        {"id": "capacitacion_previa", "texto": "¿Has tomado antes capacitación en habilidades blandas (cursos, coaching, talleres)?", "tipo": "opcion", "opciones": ["No", "Sí, presencial", "Sí, en línea", "Sí, ambas"]},
    ]},
    {"id": "experiencia", "titulo": "Tu experiencia", "preguntas": [
        {"id": "utilidad", "texto": "¿Qué tan útil consideras Mente Viva para mejorar tus habilidades personales o profesionales?", "tipo": "opcion",
         "opciones": ["1 · Nada útil", "2 · Poco útil", "3 · Moderadamente útil", "4 · Muy útil", "5 · Extremadamente útil"]},
        {"id": "calificacion", "texto": "¿Cómo calificas tu experiencia en general?", "tipo": "escala", "min": 1, "max": 10},
        {"id": "realismo", "texto": "¿Qué tan realista fue la conversación con el avatar?", "tipo": "escala", "min": 1, "max": 5},
        {"id": "utilidad_feedback", "texto": "¿Qué tan útil y accionable fue la retroalimentación?", "tipo": "escala", "min": 1, "max": 5},
        {"id": "facilidad", "texto": "¿Qué tan fácil fue usar la plataforma?", "tipo": "escala", "min": 1, "max": 5},
        {"id": "valora", "texto": "¿Qué es lo que más valoras de Mente Viva? (elige todas las que apliquen)", "tipo": "multiple",
         "opciones": ["Simulaciones de conversaciones reales", "Retroalimentación de la IA", "Diagnóstico de habilidades", "Poder practicar sin temor a equivocarme",
                      "Variedad de escenarios y temas", "Las master class de Sócrates", "Aún no identifico un beneficio claro"]},
        {"id": "aprendizaje", "texto": "¿Sientes que aprendiste algo que puedes aplicar esta semana?", "tipo": "opcion", "opciones": ["Sí, claramente", "Algo", "Poco", "Nada"]},
        {"id": "frecuencia", "texto": "¿Con qué frecuencia te gustaría utilizar Mente Viva?", "tipo": "opcion",
         "opciones": ["Varias veces por semana", "Una vez por semana", "Una o dos veces al mes", "Solo cuando necesite practicar algo específico", "No planeo seguir utilizándola"]},
        {"id": "nps", "texto": "¿Qué tan probable es que recomiendes Mente Viva a un colega? (0 = nada probable, 10 = seguro)", "tipo": "escala", "min": 0, "max": 10},
        {"id": "gusto", "texto": "¿Qué fue lo que más te gustó?", "tipo": "texto"},
        {"id": "mejora", "texto": "¿Qué mejorarías o agregarías a Mente Viva?", "tipo": "texto"},
        {"id": "fallo", "texto": "¿Algo falló o te confundió? Cuéntanos qué pasó", "tipo": "texto", "opcional": True},
    ]},
    {"id": "valor", "titulo": "Valor y disposición de pago", "precio": True, "preguntas": [
        {"id": "pagaria", "texto": "Considerando tu experiencia, ¿estarías dispuesto(a) a pagar por utilizar Mente Viva?", "tipo": "opcion",
         "opciones": ["Sí, con las funcionalidades actuales", "Sí, si incorpora nuevas funcionalidades", "Tal vez, dependiendo del precio", "Preferiría que mi empresa pagara el acceso", "No estaría dispuesto(a) a pagar"]},
        {"id": "monto_mensual", "texto": "¿Cuál sería el monto máximo que estarías dispuesto(a) a pagar mensualmente por Mente Viva?", "tipo": "opcion",
         "opciones": ["Menos de $50 MXN", "$50 a $99 MXN", "$100 a $149 MXN", "$150 a $199 MXN", "$200 MXN o más", "No estoy seguro(a)"]},
        {"id": "precio_unico", "texto": "Si fuera un pago único por persona, ¿cuánto te parecería justo? (MXN)", "tipo": "numero", "sufijo": "MXN", "opcional": True},
        {"id": "modalidad_pago", "texto": "¿Qué modalidad de pago preferirías?", "tipo": "opcion",
         "opciones": ["Mensual", "Trimestral (cada 3 meses)", "Semestral (cada 6 meses)", "Anual (cada 12 meses)", "Pago único", "Pago por sesión o práctica"]},
        {"id": "cuando_pagar", "texto": "¿Cuándo considerarías comenzar a pagar por Mente Viva?", "tipo": "opcion",
         "opciones": ["De inmediato", "En 1 a 3 meses", "En 4 a 6 meses", "Después de probar más funcionalidades", "Cuando tenga una necesidad específica"]},
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
GRACIAS = ("¡Gracias por compartir tu opinión! Tu participación es muy valiosa para nosotros. Cada respuesta nos ayuda a seguir mejorando Mente Viva y construir una "
           "experiencia más útil, accesible y enfocada en tus necesidades.")

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
           "nps": nps, "aprendizaje": dist("aprendizaje"), "entrevista": dist("entrevista"), "utilidad": dist("utilidad"), "valora": dist("valora"), "frecuencia": dist("frecuencia"),
           "relacion": dist("relacion"), "veces_uso": dist("veces_uso")}
    if incluir_precio:
        out.update({"pagaria": dist("pagaria"), "monto_mensual": dist("monto_mensual"), "modalidad_pago": dist("modalidad_pago"), "cuando_pagar": dist("cuando_pagar"),
                    "quien_paga": dist("quien_paga"), "funciones": dist("funciones"), "precio_unico": prom("precio_unico")})
    return out
