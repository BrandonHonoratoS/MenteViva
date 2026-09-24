"""Catálogo de habilidades, niveles, KPIs, Ruta DM y variables de onboarding de Mente Viva.

Es la única fuente de verdad que comparten los agentes, el analista, las métricas y la interfaz.
"""
from __future__ import annotations

NIVELES_3 = ["Principiante", "Intermedio", "Avanzado"]

# ── Categorías del catálogo (documento funcional v2) ─────────────────────────
CATEGORIAS = [
    {"id": "CAT-01", "nombre": "Ventas y Cierre", "icono": "💼", "color": "#7C3AED", "escenarios": 6},
    {"id": "CAT-02", "nombre": "Negociación", "icono": "🤝", "color": "#06B6D4", "escenarios": 5},
    {"id": "CAT-03", "nombre": "Entrevistas y Selección de Personal", "icono": "👔", "color": "#3B82F6", "escenarios": 5},
    {"id": "CAT-04", "nombre": "Liderazgo y Gestión de Equipos", "icono": "🧭", "color": "#10B981", "escenarios": 6},
    {"id": "CAT-05", "nombre": "Presentaciones Ejecutivas y Comunicación en Público", "icono": "🎤", "color": "#F59E0B", "escenarios": 5},
    {"id": "CAT-06", "nombre": "Manejo de Conflictos", "icono": "⚡", "color": "#EF4444", "escenarios": 5},
    {"id": "CAT-07", "nombre": "Comunicación Asertiva", "icono": "💬", "color": "#EC4899", "escenarios": 5},
    {"id": "CAT-08", "nombre": "Gestión de Proyectos y Coordinación", "icono": "🚀", "color": "#6366F1", "escenarios": 5},
]

# ── Habilidades entrenables hoy ──────────────────────────────────────────────
HABILIDADES: dict[str, dict] = {
    "ventas": {
        "id": "ventas", "categoria": "CAT-01", "nombre": "Clínica de Ventas", "corto": "Ventas",
        "agente": "celeste", "avatar": "Celeste López", "rol_avatar": "Cliente exigente",
        "descripcion": "Practica el ciclo completo de venta (PRAINCODERECI, SPIN, 8 técnicas de objeciones) con una clienta analítica que no se deja convencer con discursos.",
        "niveles": NIVELES_3, "escala": "0-100", "activa": True, "personalizada": False,
        "duracion": {"Principiante": 15, "Intermedio": 20, "Avanzado": 25},
        "turnos": {"Principiante": 18, "Intermedio": 24, "Avanzado": 30},
        "kpis": [
            {"id": "KPI-1", "nombre": "Manejo de objeciones", "que": "Técnicas T-01 a T-08, Validar-Aislar-Diagnosticar, sin descuento prematuro."},
            {"id": "KPI-2", "nombre": "Escucha activa", "que": "SPIN por tipo, ratio Implicación+Necesidad / Situación+Problema > 1, personalización con datos del cliente."},
            {"id": "KPI-3", "nombre": "Estructura PRAINCODERECI", "que": "Etapas en orden; no salta a Cierre sin Convicción y Deseo."},
            {"id": "KPI-4", "nombre": "Control emocional", "que": "Tono uniforme bajo presión, no defensivo ante el NO, uso del silencio."},
            {"id": "KPI-5", "nombre": "Técnica de cierre", "que": "Señal de compra, lenguaje de presuposición, sobrevivió al primer NO."},
            {"id": "KPI-6", "nombre": "Valor vs precio", "que": "Precio después del valor, uso de T-04, negociación con contraprestación."},
        ],
        # pesos por nivel (documento CAT-01 v3.0); suman 100
        "pesos": {
            "Principiante": {"KPI-1": 25, "KPI-2": 25, "KPI-3": 30, "KPI-4": 20, "KPI-5": 0, "KPI-6": 0},
            "Intermedio": {"KPI-1": 35, "KPI-2": 0, "KPI-3": 25, "KPI-4": 0, "KPI-5": 20, "KPI-6": 20},
            "Avanzado": {"KPI-1": 25, "KPI-2": 20, "KPI-3": 15, "KPI-4": 15, "KPI-5": 15, "KPI-6": 10},
        },
    },
    "entrevistas": {
        "id": "entrevistas", "categoria": "CAT-03", "nombre": "Entrevista por competencias", "corto": "Entrevistas",
        "agente": "elena", "avatar": "Elena Ríos", "rol_avatar": "Entrevistadora BEI",
        "descripcion": "Practica una entrevista conductual (BEI + STAR): contar historias reales con evidencia, sin generalidades, bajo repreguntas exigentes.",
        "niveles": NIVELES_3, "escala": "0-100", "activa": True, "personalizada": False,
        "duracion": {"Principiante": 20, "Intermedio": 25, "Avanzado": 30},
        "turnos": {"Principiante": 18, "Intermedio": 22, "Avanzado": 26},
        "kpis": [
            {"id": "KPI-1", "nombre": "Evidencia conductual (STAR)", "que": "Historias con Situación, Tarea, Acción propia y Resultado medible; sin 'nosotros' ni verbos vagos."},
            {"id": "KPI-2", "nombre": "Claridad y estructura", "que": "Respuestas ordenadas, concretas, sin saltos temporales ni racionalizaciones."},
            {"id": "KPI-3", "nombre": "Autoconciencia", "que": "Reconoce errores, aprendizajes y lo que haría distinto; emociones nombradas con precisión."},
            {"id": "KPI-4", "nombre": "Presencia bajo presión", "que": "Mantiene calma y foco ante repreguntas incómodas; no evade."},
            {"id": "KPI-5", "nombre": "Orientación a resultados", "que": "Cuantifica impacto, conecta acciones con resultados del negocio."},
        ],
        "pesos": {
            "Principiante": {"KPI-1": 35, "KPI-2": 30, "KPI-3": 20, "KPI-4": 15, "KPI-5": 0},
            "Intermedio": {"KPI-1": 30, "KPI-2": 20, "KPI-3": 20, "KPI-4": 15, "KPI-5": 15},
            "Avanzado": {"KPI-1": 25, "KPI-2": 15, "KPI-3": 20, "KPI-4": 20, "KPI-5": 20},
        },
    },
    "ruta_dm": {
        "id": "ruta_dm", "categoria": "CAT-04", "nombre": "Ruta Delivery Manager", "corto": "Ruta DM",
        "agente": "juan", "avatar": "Juan Artiaga", "rol_avatar": "Mentor de desarrollo",
        "descripcion": "Escenario personalizado de Ingeniería Cóndor: diagnostica tu nivel en la Ruta DM y entrena, con roleplay, casos de decisión o retos prácticos, las competencias del siguiente nivel.",
        "niveles": ["DM Básico", "DM1", "DM2", "DM3", "DM4", "DM5", "Emprendedor"], "escala": "0-10 por competencia",
        "activa": True, "personalizada": True, "empresa": "Ingeniería Cóndor",
        "duracion": {"*": 20}, "turnos": {"*": 22},
    },
}

PROXIMAMENTE = [c for c in CATEGORIAS if c["id"] not in ("CAT-01", "CAT-03")]

# ── Ruta Delivery Manager (Ingeniería Cóndor) ────────────────────────────────
RUTA_DM: list[dict] = [
    {"nivel": "DM Básico", "etapas": "Aspirante · Becario · Becario en paralelo", "valor": "Aprender a trabajar profesionalmente",
     "competencias": ["Comunicación", "Trabajo en equipo", "Resiliencia", "Accountability", "Autogestión", "Innovación básica"]},
    {"nivel": "DM1", "etapas": "Consultor con supervisión · Consultor autónomo · Consultor con autoliderazgo", "valor": "Aprender a asesorar",
     "competencias": ["Escucha activa", "Servicio", "Influencia", "Scrum", "Retroalimentación", "Manejo de ansiedad"]},
    {"nivel": "DM2", "etapas": "Supervisa una persona · Supervisa un equipo", "valor": "Aprender a liderar personas",
     "competencias": ["Gestión de clientes", "Gestión de conflictos", "Delegación", "PMBOK", "Innovación operativa", "Toma de decisiones"]},
    {"nivel": "DM3", "etapas": "Líder de equipos ≤ 5 personas", "valor": "Liderar conocimiento e innovación",
     "competencias": ["Investigación", "Innovación estratégica", "Ética profesional", "Administración de recursos"]},
    {"nivel": "DM4", "etapas": "Líder de equipos > 5 personas", "valor": "Construir soluciones",
     "competencias": ["PMO", "Gestión del cambio", "Desarrollo gerencial", "Innovación disruptiva"]},
    {"nivel": "DM5", "etapas": "Generación de negocio · Desarrollo de negocio", "valor": "Generar negocio",
     "competencias": ["ROI", "Finanzas", "Marketing", "Canvas", "Negociación", "Propuesta de valor", "IA aplicada a negocios", "XaaS"]},
    {"nivel": "Emprendedor", "etapas": "Crea empresas y circuitos de productividad", "valor": "Crear empresas y circuitos de productividad",
     "competencias": ["Escalabilidad", "Inversión", "Estrategia", "Innovación disruptiva", "Nuevos modelos de negocio"]},
]
NIVELES_DM = [n["nivel"] for n in RUTA_DM]

FORMATO_POR_COMPETENCIA = {
    "roleplay": ["Escucha activa", "Influencia", "Gestión de conflictos", "Gestión de clientes", "Negociación", "Retroalimentación", "Delegación",
                 "Comunicación", "Servicio", "Trabajo en equipo", "Resiliencia", "Manejo de ansiedad", "Desarrollo gerencial", "Ética profesional"],
    "caso": ["Toma de decisiones", "ROI", "Finanzas", "Innovación estratégica", "PMO", "Gestión del cambio", "Administración de recursos", "Canvas",
             "Propuesta de valor", "Escalabilidad", "Inversión", "Estrategia", "Nuevos modelos de negocio"],
    "reto": ["Scrum", "PMBOK", "Accountability", "Autogestión", "Investigación", "Marketing", "IA aplicada a negocios", "XaaS", "Innovación operativa",
             "Innovación disruptiva", "Innovación básica"],
}
NOMBRE_FORMATO = {"roleplay": "Roleplay", "caso": "Caso de decisión", "reto": "Reto práctico"}


def formato_sugerido(competencia: str) -> str:
    for f, comps in FORMATO_POR_COMPETENCIA.items():
        if competencia in comps:
            return f
    return "roleplay"


def nivel_dm_siguiente(nivel: str) -> str | None:
    if nivel not in NIVELES_DM:
        return NIVELES_DM[1]
    i = NIVELES_DM.index(nivel)
    return NIVELES_DM[i + 1] if i + 1 < len(NIVELES_DM) else None


def competencias_dm(nivel: str) -> list[str]:
    for n in RUTA_DM:
        if n["nivel"] == nivel:
            return n["competencias"]
    return []


def valor_dm(nivel: str) -> str:
    for n in RUTA_DM:
        if n["nivel"] == nivel:
            return n["valor"]
    return ""


DOMINIO_DM = [("Principiante", 0, 4.99), ("En desarrollo", 5, 6.99), ("Sólido", 7, 8.99), ("Listo para el siguiente nivel", 9, 10)]


def dominio_dm(score10: float) -> str:
    for nombre, lo, hi in DOMINIO_DM:
        if lo <= score10 <= hi:
            return nombre
    return "Principiante"


# Regla de ascenso (propuesta del analista; RRHH aprueba): todas las competencias del siguiente nivel entrenadas al menos una vez,
# promedio ≥ 7, ninguna < 5 y al menos dos en 9–10.
REGLA_ASCENSO_DM = {"promedio_min": 7.0, "minimo_por_competencia": 5.0, "listas_min": 2, "listas_umbral": 9.0}

# ── Competencias que evalúa Elena en el diagnóstico (catálogo del entrevistador) ──
COMPETENCIAS_DIAGNOSTICO = ["Comunicación", "Autoconciencia", "Inteligencia emocional", "Trabajo en equipo", "Liderazgo / influencia",
                            "Resolución de problemas", "Pensamiento crítico", "Adaptabilidad / aprendizaje", "Orientación a resultados", "Gestión de prioridades"]

# ── Reglas de nivel (documento funcional 4.3) ────────────────────────────────
REGLAS_NIVEL = {"sube": 75, "sube_sesiones": 2, "baja": 50, "refuerzo_sin_mejora": 3}
SEMAFORO = {"verde": 75, "amarillo": 50}      # dashboard: verde >75, amarillo 50-75, rojo <50


def semaforo(score: float | None) -> str:
    if score is None:
        return "gris"
    if score > SEMAFORO["verde"]:
        return "verde"
    if score >= SEMAFORO["amarillo"]:
        return "amarillo"
    return "rojo"


# ── Variables de onboarding (chips) ──────────────────────────────────────────
# Cada variable: id, pregunta, opciones (valor→efecto), grupo. `multiple` permite varias.
ONBOARDING: list[dict] = [
    {"id": "funciones", "grupo": "Tu rol", "pregunta": "¿Qué haces en tu trabajo? (elige todo lo que aplique)", "multiple": True,
     "opciones": ["Vendo o asesoro a clientes", "Entrevisto o selecciono personas", "Lidero personas o proyectos", "Ejecuto proyectos / consultoría",
                  "Genero negocio nuevo", "Otro"]},
    {"id": "industria", "grupo": "Tu rol", "pregunta": "¿En qué industria operan tus clientes?",
     "opciones": ["Manufactura / industria", "Salud / farmacéutico", "Retail / comercio", "Tecnología / startups", "Educación", "Construcción / bienes raíces",
                  "Servicios profesionales", "Gobierno", "Otra"]},
    {"id": "experiencia", "grupo": "Tu rol", "pregunta": "¿Cuánta experiencia profesional tienes?",
     "opciones": ["Estoy empezando (0–6 meses)", "Menos de 2 años", "2 a 5 años", "Más de 5 años"]},
    {"id": "tipo_producto", "grupo": "Ventas", "pregunta": "¿Qué vendes o venderás?",
     "opciones": ["Software / SaaS", "Servicios profesionales", "Producto físico / retail", "Inmuebles / bienes raíces", "Seguros / finanzas", "Otro"]},
    {"id": "modelo_venta", "grupo": "Ventas", "pregunta": "¿A quién le vendes?",
     "opciones": ["A personas (B2C)", "A empresas (B2B)", "A gobierno / instituciones (B2G)", "A ambos (mixto)"]},
    {"id": "canal_venta", "grupo": "Ventas", "pregunta": "¿Cómo contactas a tus prospectos?",
     "opciones": ["Cara a cara / visita presencial", "Videollamada", "Teléfono / llamada fría", "WhatsApp / chat", "E-commerce / sin contacto", "Multicanal"]},
    {"id": "tamano_cliente", "grupo": "Ventas", "pregunta": "¿De qué tamaño son tus clientes típicos?",
     "opciones": ["Persona independiente / freelance", "PYME (1 a 100 empleados)", "Mediana empresa (100–500)", "Corporativo / enterprise (+500)"]},
    {"id": "ticket", "grupo": "Ventas", "pregunta": "¿Cuál es tu ticket promedio?",
     "opciones": ["Menos de $500", "$500 — $5,000", "$5,000 — $50,000", "Más de $50,000"]},
    {"id": "estilo", "grupo": "Ventas", "pregunta": "¿Cómo describirías tu estilo de comunicación?",
     "opciones": ["Analítico / basado en datos", "Relacional / empático", "Directo / orientado al cierre", "Consultivo / asesor", "No sé cómo soy"]},
    {"id": "etapa_debil", "grupo": "Ventas", "pregunta": "¿En qué etapa sientes que fallas más?",
     "opciones": ["Prospectar / conseguir contactos", "Generar interés en los primeros segundos", "Hacer las preguntas correctas", "Manejar objeciones",
                  "Cerrar la venta", "El seguimiento post-reunión"]},
    {"id": "objetivo_ventas", "grupo": "Ventas", "pregunta": "¿Qué quieres lograr con tu entrenamiento en ventas?",
     "opciones": ["Cerrar más ventas este mes", "Aumentar mi ticket promedio", "Sentirme más seguro al vender", "Aprender a vender desde cero",
                  "Preparar a mi equipo de ventas", "Mejorar mi tasa de conversión"]},
    {"id": "dm_lidera", "grupo": "Ruta DM", "pregunta": "¿Lideras a alguien actualmente?",
     "opciones": ["No lidero a nadie", "Superviso a una persona", "Lidero un equipo de hasta 5", "Lidero un equipo de más de 5"]},
    {"id": "dm_trabajo", "grupo": "Ruta DM", "pregunta": "¿Cuál describe mejor tu trabajo hoy?",
     "opciones": ["Ejecutar tareas con supervisión", "Ejecutar de forma autónoma", "Asesorar al cliente", "Liderar personas y proyectos", "Generar negocio nuevo",
                  "Crear empresas o nuevos modelos"]},
    {"id": "dm_antiguedad", "grupo": "Ruta DM", "pregunta": "¿Cuánto llevas en Cóndor o en consultoría?",
     "opciones": ["Menos de 6 meses", "6 meses a 2 años", "2 a 5 años", "Más de 5 años"]},
    {"id": "dm_representa", "grupo": "Ruta DM", "pregunta": "¿Representas a la empresa frente a clientes o integradores?",
     "opciones": ["No todavía", "A veces, acompañado", "Sí, de forma habitual", "Sí, y negocio contratos"]},
    {"id": "tiempo_semana", "grupo": "Tu plan", "pregunta": "¿Cuánto tiempo puedes dedicar a practicar cada semana?",
     "opciones": ["15 min", "30 min", "1 hora", "Más de 1 hora"]},
    {"id": "meta", "grupo": "Tu plan", "pregunta": "¿Cuál es tu meta principal?",
     "opciones": ["Mejorar en mi rol actual", "Ascender en la ruta de desarrollo", "Capacitar a mi equipo", "Conseguir un nuevo puesto", "Certificarme"]},
]

GRUPO_VENTAS_IDS = [v["id"] for v in ONBOARDING if v["grupo"] == "Ventas"]
GRUPO_DM_IDS = [v["id"] for v in ONBOARDING if v["grupo"] == "Ruta DM"]


def sesiones_por_semana(tiempo_semana: str) -> int:
    return {"15 min": 1, "30 min": 2, "1 hora": 3, "Más de 1 hora": 4}.get(tiempo_semana or "", 2)


def habilidades_que_usa(onboarding: dict) -> set[str]:
    """Habilidades que forman parte del rol declarado (sus roadmaps se activan sin aprobación)."""
    f = set(onboarding.get("funciones") or [])
    usa: set[str] = set()
    if f & {"Vendo o asesoro a clientes", "Genero negocio nuevo"}:
        usa.add("ventas")
    if "Entrevisto o selecciono personas" in f:
        usa.add("entrevistas")
    usa.add("ruta_dm")   # la ruta de desarrollo aplica a todo colaborador de una empresa que la tenga habilitada
    return usa


def nivel_dm_estimado(onboarding: dict) -> str:
    """Estimación previa (la confirma Elena en la entrevista)."""
    lidera = onboarding.get("dm_lidera", "")
    trabajo = onboarding.get("dm_trabajo", "")
    if trabajo == "Crear empresas o nuevos modelos":
        return "DM5"
    if trabajo == "Generar negocio nuevo":
        return "DM4"
    if lidera == "Lidero un equipo de más de 5":
        return "DM4"
    if lidera == "Lidero un equipo de hasta 5":
        return "DM3"
    if lidera == "Superviso a una persona" or trabajo == "Liderar personas y proyectos":
        return "DM2"
    if trabajo in ("Asesorar al cliente", "Ejecutar de forma autónoma"):
        return "DM1"
    return "DM Básico"


def nivel_ventas_estimado(onboarding: dict) -> str:
    exp = onboarding.get("experiencia", "")
    if exp == "Más de 5 años":
        return "Avanzado"
    if exp == "2 a 5 años":
        return "Intermedio"
    return "Principiante"


# ── Evaluación del líder y autoevaluación (1–5) ──────────────────────────────
PREGUNTAS_LIDER = [
    {"id": "aplica", "texto": "Aplica en su trabajo diario lo que practica en Mente Viva (se nota en reuniones, clientes o equipo)."},
    {"id": "comunicacion", "texto": "Se comunica con más claridad y estructura que hace un mes."},
    {"id": "escucha", "texto": "Escucha y hace mejores preguntas antes de proponer."},
    {"id": "presion", "texto": "Mantiene el control y la calma en situaciones de presión o conflicto."},
    {"id": "resultados", "texto": "Sus conversaciones producen mejores resultados (cierres, acuerdos, decisiones)."},
]
PREGUNTAS_AUTO = [
    {"id": "aplica", "texto": "Esta semana apliqué en una situación real algo que practiqué en Mente Viva."},
    {"id": "confianza", "texto": "Me siento más seguro(a) en conversaciones difíciles."},
    {"id": "habito", "texto": "Estoy practicando con la frecuencia que me propuse."},
    {"id": "utilidad", "texto": "El feedback de los agentes me resulta útil y accionable."},
]

# ── Habilidades disponibles para una empresa ─────────────────────────────────
def habilidades_empresa(empresa: dict | None) -> list[dict]:
    habilitadas = set((empresa or {}).get("habilidades") or [])
    out = []
    for h in HABILIDADES.values():
        if h["personalizada"] and h["id"] not in habilitadas:
            continue
        out.append(h)
    return out


def habilidad(id_: str) -> dict | None:
    return HABILIDADES.get(id_)


def turnos_max(habilidad_id: str, nivel: str | None) -> int:
    h = HABILIDADES.get(habilidad_id) or {}
    t = h.get("turnos", {})
    return int(t.get(nivel or "", t.get("*", 22)))


def duracion_min(habilidad_id: str, nivel: str | None) -> int:
    h = HABILIDADES.get(habilidad_id) or {}
    d = h.get("duracion", {})
    return int(d.get(nivel or "", d.get("*", 20)))
