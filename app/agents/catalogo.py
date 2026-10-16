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
    {"id": "CAT-09", "nombre": "Imagen Profesional y Etiqueta", "icono": "🪞", "color": "#D946EF", "escenarios": 4},
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
    "presentaciones": {
        "id": "presentaciones", "categoria": "CAT-05", "nombre": "Presentaciones de alto impacto", "corto": "Presentaciones",
        "agente": "valeria", "avatar": "Valeria Campos", "rol_avatar": "Audiencia exigente",
        "descripcion": "Presenta un tema de tu trabajo ante una audiencia que pregunta, objeta y se distrae: graba tu voz y recibe la rúbrica de 9 criterios (apertura, síntesis, voz, muletillas, interacción, cierre, tiempo).",
        "niveles": NIVELES_3, "escala": "0-100", "activa": True, "personalizada": False, "audio": True, "diseno": True,
        "duracion": {"Principiante": 12, "Intermedio": 18, "Avanzado": 25},
        "turnos": {"Principiante": 10, "Intermedio": 14, "Avanzado": 18},
        "kpis": [
            {"id": "KPI-1", "nombre": "Apertura e introducción", "que": "En 20–30 s engancha (pregunta, dato, situación), explica por qué importa y presenta propósito/agenda; sin saludos ni antecedentes largos."},
            {"id": "KPI-2", "nombre": "Claridad y síntesis", "que": "Una idea central explícita y máximo tres puntos de apoyo; dice lo necesario sin rodeos ni relleno."},
            {"id": "KPI-3", "nombre": "Estructura y orden lógico", "que": "Apertura → desarrollo → cierre con transiciones claras; no se pierde el hilo."},
            {"id": "KPI-4", "nombre": "Manejo de la voz", "que": "Volumen audible, ritmo variable, pausas intencionales y énfasis en ideas clave (se evalúa con la grabación).", "audio": True},
            {"id": "KPI-5", "nombre": "Fluidez, seguridad y muletillas", "que": "Entrega segura y natural; muletillas por minuto (≤1 alto impacto, 2–3 competente, 4–6 en desarrollo, >6 inicial); se recupera al perder el hilo (grabación).", "audio": True},
            {"id": "KPI-6", "nombre": "Conexión e interacción", "que": "Se dirige a la audiencia, plantea preguntas, comprueba comprensión con evidencia, escucha la pregunta completa y responde con R-C-E-C."},
            {"id": "KPI-7", "nombre": "Vocabulario y precisión", "que": "Lenguaje profesional, concreto y variado; traduce lo técnico y define términos la primera vez; sin expresiones vagas."},
            {"id": "KPI-8", "nombre": "Cierre", "que": "En 30–45 s recapitula máximo tres ideas, refuerza el valor y deja un siguiente paso, decisión o reflexión; última frase con intención."},
            {"id": "KPI-9", "nombre": "Manejo del tiempo", "que": "Respeta la duración pedida (±15 s = alto impacto; >60 s de desvío = inicial) con tiempos equilibrados (grabación).", "audio": True},
        ],
        "pesos": {n: {"KPI-1": 12, "KPI-2": 15, "KPI-3": 12, "KPI-4": 12, "KPI-5": 10, "KPI-6": 10, "KPI-7": 9, "KPI-8": 12, "KPI-9": 8} for n in NIVELES_3},
    },
    "imagen": {
        "id": "imagen", "categoria": "CAT-09", "nombre": "Imagen profesional y código de vestimenta", "corto": "Imagen",
        "agente": "renata", "avatar": "Renata Solís", "rol_avatar": "Consultora de imagen y etiqueta",
        "descripcion": "Renata te plantea situaciones reales (demo con cliente, junta de dirección, entrevista, viernes casual, comida de negocios): describe o fotografía tu outfit y resuelve dilemas de etiqueta; te evalúa con los 5 códigos y los tips de medidas, calzado, perfume y modales.",
        "niveles": NIVELES_3, "escala": "0-100", "activa": True, "personalizada": False, "foto": True, "diseno": True,
        "duracion": {"Principiante": 10, "Intermedio": 15, "Avanzado": 20},
        "turnos": {"Principiante": 10, "Intermedio": 14, "Avanzado": 16},
        "kpis": [
            {"id": "KPI-1", "nombre": "Adecuación al código y al contexto", "que": "Elige el código correcto (formal, business casual, smart casual, casual, viernes) según interlocutor, lugar y mensaje; un escalón por encima del cliente."},
            {"id": "KPI-2", "nombre": "Ajuste, medidas y proporciones", "que": "Talla correcta; hombro del saco, puño visible, caída del pantalón sin arrugas sobre el zapato, largo de falda a la rodilla o máx. 5 cm arriba, escote discreto."},
            {"id": "KPI-3", "nombre": "Pulcritud y cuidado", "que": "Prendas limpias y planchadas, calzado lustrado, cabello, uñas, barba o maquillaje sobrios; sin etiquetas, pelusas ni hilos."},
            {"id": "KPI-4", "nombre": "Color, combinación y coherencia", "que": "2–3 colores, neutros de base y un acento; cinturón y zapatos del mismo tono; calcetín del tono del pantalón; nada estridente en formal."},
            {"id": "KPI-5", "nombre": "Accesorios, perfume y detalles", "que": "Accesorios discretos que elevan; perfume recién bañado en puntos de pulso, 1–2 aplicaciones, nunca sobre la ropa ni reaplicado en la oficina; reloj, bolso o portafolio en buen estado."},
            {"id": "KPI-6", "nombre": "Etiqueta y modales", "que": "Puntualidad, saludo firme con contacto visual, presentaciones en orden jerárquico, 'usted' por defecto, celular en silencio, conducta en la mesa y en videollamada."},
        ],
        "pesos": {n: {"KPI-1": 25, "KPI-2": 20, "KPI-3": 15, "KPI-4": 15, "KPI-5": 10, "KPI-6": 15} for n in NIVELES_3},
    },
    "comunicacion": {
        "id": "comunicacion", "categoria": "CAT-07", "nombre": "Comunicación verbal efectiva", "corto": "Comunicación",
        "agente": "mateo", "avatar": "Mateo Ibarra", "rol_avatar": "Interlocutor cotidiano",
        "descripcion": "Comunica ideas con claridad y firmeza en el trabajo, la familia y la vida diaria: Mateo interpreta a tu pareja, un hijo, un compañero, tu jefe, un vecino o un cliente en conversaciones que suelen salir mal, y te evalúa claridad, escucha, asertividad y acuerdo.",
        "niveles": NIVELES_3, "escala": "0-100", "activa": True, "personalizada": False, "audio": True, "diseno": True,
        "duracion": {"Principiante": 12, "Intermedio": 15, "Avanzado": 20},
        "turnos": {"Principiante": 12, "Intermedio": 16, "Avanzado": 20},
        "kpis": [
            {"id": "KPI-1", "nombre": "Claridad del mensaje", "que": "Una idea central, concreta y breve; se entiende qué quiere que el otro entienda, sienta o haga; pide en vez de reclamar."},
            {"id": "KPI-2", "nombre": "Escucha y empatía", "que": "Deja terminar, parafrasea, nombra la emoción del otro, pregunta antes de responder; valida sin necesariamente dar la razón."},
            {"id": "KPI-3", "nombre": "Asertividad", "que": "Expresa lo que piensa, siente y necesita con respeto, sin agredir ni ceder: mensajes 'yo', DESC, disco rayado, banco de niebla, decir no con alternativa."},
            {"id": "KPI-4", "nombre": "Estructura y síntesis", "que": "Primero la idea principal, luego el porqué y un ejemplo; repite la petición al final; sin rodeos ni discursos largos."},
            {"id": "KPI-5", "nombre": "Regulación emocional", "que": "Tono y volumen estables, pausas en vez de interrumpir, no se engancha en provocaciones ni decide en el pico de la emoción."},
            {"id": "KPI-6", "nombre": "Acuerdo y cierre", "que": "Verifica comprensión, resume lo acordado, reparte responsabilidades y fija fecha o señal de seguimiento."},
        ],
        "pesos": {n: {"KPI-1": 20, "KPI-2": 20, "KPI-3": 20, "KPI-4": 15, "KPI-5": 10, "KPI-6": 15} for n in NIVELES_3},
    },
    "liderazgo": {
        "id": "liderazgo", "categoria": "CAT-04", "nombre": "Liderazgo", "corto": "Liderazgo",
        "agente": "patricia", "avatar": "Patricia Navarro", "rol_avatar": "Integrante del equipo",
        "descripcion": "Conoce tu estilo (test del grid gerencial) y entrena con Patricia, que interpreta a integrantes de tu equipo en situaciones reales: delegar, dar retroalimentación difícil, desmotivación, conflicto, resistencia al cambio; te evalúa dirección, adaptación situacional, escucha, reconocimiento, decisión y gestión del cambio.",
        "niveles": NIVELES_3, "escala": "0-100", "activa": True, "personalizada": False, "diseno": True, "test": "liderazgo", "para_directores": True,
        "duracion": {"Principiante": 15, "Intermedio": 20, "Avanzado": 25},
        "turnos": {"Principiante": 14, "Intermedio": 18, "Avanzado": 22},
        "kpis": [
            {"id": "KPI-1", "nombre": "Claridad de dirección", "que": "Objetivo, qué/quién/cuándo, criterio de éxito y el porqué; instrucciones claras sin microgestionar."},
            {"id": "KPI-2", "nombre": "Adaptación situacional", "que": "Ajusta el estilo (dirigir, persuadir, participar, delegar) a la madurez de la persona y la tarea; equilibra tarea y relación (grid)."},
            {"id": "KPI-3", "nombre": "Escucha y empatía", "que": "Pregunta y escucha antes de decidir; reconoce el impacto y la emoción del colaborador sin perder el foco."},
            {"id": "KPI-4", "nombre": "Retroalimentación y reconocimiento", "que": "Feedback de conducta (qué pasó, efecto, qué hacer distinto) sin etiquetas; reconoce esfuerzos y resultados concretos; corrige en privado."},
            {"id": "KPI-5", "nombre": "Decisión y accountability", "que": "Decide con evidencia, asume responsabilidad, no culpa; sostiene la decisión con firmeza y respeto."},
            {"id": "KPI-6", "nombre": "Gestión del cambio e influencia", "que": "Usa poder experto, referente y premiador (no coercitivo); gestiona la resistencia con información, participación y triunfos tempranos (Lewin, Kotter)."},
        ],
        "pesos": {n: {"KPI-1": 20, "KPI-2": 20, "KPI-3": 15, "KPI-4": 15, "KPI-5": 15, "KPI-6": 15} for n in NIVELES_3},
    },
}

PROXIMAMENTE = [c for c in CATEGORIAS if c["id"] not in ("CAT-01", "CAT-03", "CAT-04", "CAT-05", "CAT-07", "CAT-09")]

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
    {"id": "contexto", "grupo": "Tu rol", "pregunta": "¿Cuál describe mejor tu situación hoy?",
     "opciones": ["Trabajo en una empresa", "Tengo mi negocio u oficio", "Estudio", "Me dedico al hogar y la familia", "Estoy buscando empleo", "Otra"]},
    {"id": "funciones", "grupo": "Tu rol", "pregunta": "¿Qué haces en tu día a día? (elige todo lo que aplique)", "multiple": True,
     "opciones": ["Vendo o asesoro a clientes", "Atiendo clientes en mi negocio u oficio", "Entrevisto o selecciono personas", "Lidero personas o proyectos",
                  "Ejecuto proyectos / consultoría", "Genero negocio nuevo", "Estudio", "Cuido mi hogar / familia", "Busco empleo", "Otro"]},
    {"id": "industria", "grupo": "Tu rol", "pregunta": "¿Con qué tipo de clientes o personas tratas?",
     "opciones": ["Manufactura / industria", "Salud / farmacéutico", "Retail / comercio", "Tecnología / startups", "Educación", "Construcción / bienes raíces",
                  "Servicios profesionales", "Gobierno", "Personas y familias (clientes particulares)", "Otra"]},
    {"id": "experiencia", "grupo": "Tu rol", "pregunta": "¿Cuánta experiencia tienes en lo que haces?",
     "opciones": ["Estoy empezando (0–6 meses)", "Menos de 2 años", "2 a 5 años", "Más de 5 años"]},
    {"id": "tipo_producto", "grupo": "Ventas", "pregunta": "¿Qué vendes o venderás?",
     "opciones": ["Software / SaaS", "Servicios profesionales", "Producto físico / retail", "Inmuebles / bienes raíces", "Seguros / finanzas",
                  "Oficio o servicio local (cerrajería, plomería, estética, reparaciones…)", "Comida, artesanía o venta por catálogo", "Otro"]},
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
     "opciones": ["Mejorar en mi rol actual", "Ascender en la ruta de desarrollo", "Capacitar a mi equipo", "Conseguir un nuevo puesto", "Certificarme",
                  "Vender más en mi negocio", "Comunicarme mejor con mi familia y comunidad", "Prepararme para mi primer empleo"]},
]
FUNCIONES_VENTA = {"Vendo o asesoro a clientes", "Atiendo clientes en mi negocio u oficio", "Genero negocio nuevo"}
FUNCIONES_ENTREVISTA = {"Entrevisto o selecciono personas", "Busco empleo"}

GRUPO_VENTAS_IDS = [v["id"] for v in ONBOARDING if v["grupo"] == "Ventas"]
GRUPO_DM_IDS = [v["id"] for v in ONBOARDING if v["grupo"] == "Ruta DM"]


def sesiones_por_semana(tiempo_semana: str) -> int:
    return {"15 min": 1, "30 min": 2, "1 hora": 3, "Más de 1 hora": 4}.get(tiempo_semana or "", 2)


def habilidades_que_usa(onboarding: dict) -> set[str]:
    """Habilidades que forman parte de la vida real declarada (sus roadmaps se activan sin aprobación)."""
    f = set(onboarding.get("funciones") or [])
    ctx = onboarding.get("contexto", "")
    meta = onboarding.get("meta", "")
    usa: set[str] = set()
    if f & FUNCIONES_VENTA or ctx == "Tengo mi negocio u oficio" or meta == "Vender más en mi negocio":
        usa.add("ventas")
    if f & FUNCIONES_ENTREVISTA or ctx in ("Estoy buscando empleo", "Estudio") or meta in ("Conseguir un nuevo puesto", "Prepararme para mi primer empleo"):
        usa.add("entrevistas")
    if ctx in ("Trabajo en una empresa", "Otra", ""):
        usa.add("ruta_dm")   # la ruta de desarrollo aplica a colaboradores de una empresa que la tenga habilitada (no a negocio propio, estudios u hogar)
    usa.add("comunicacion")   # comunicarse mejor le sirve a todo el mundo (trabajo, familia, comunidad)
    if ctx != "Me dedico al hogar y la familia" or meta == "Comunicarme mejor con mi familia y comunidad":
        if f & (FUNCIONES_LIDERA | {"Ejecuto proyectos / consultoría", "Genero negocio nuevo", "Estudio"}) or ctx in ("Trabajo en una empresa", "Estudio", "Estoy buscando empleo", "Otra", ""):
            usa.add("presentaciones")
    if f & (FUNCIONES_VENTA | FUNCIONES_ENTREVISTA) or ctx in ("Trabajo en una empresa", "Estoy buscando empleo", "Tengo mi negocio u oficio", "Otra", ""):
        usa.add("imagen")
    if lidera(onboarding):
        usa.add("liderazgo")
    return usa


FUNCIONES_LIDERA = {"Lidero personas o proyectos"}


def habilidades_nucleo(onboarding: dict) -> set[str]:
    """Para público general: las habilidades que llevan plan automático aunque Elena no las liste (el corazón de su situación de vida).
    Las demás relevantes (imagen, presentaciones, comunicación fuera del hogar…) aparecen en su catálogo y sólo llevan plan si Elena marca brecha alta/media."""
    ob = onboarding or {}
    f = set(ob.get("funciones") or [])
    ctx = ob.get("contexto", "")
    meta = ob.get("meta", "")
    nucleo: set[str] = set()
    if f & FUNCIONES_VENTA or ctx == "Tengo mi negocio u oficio" or meta == "Vender más en mi negocio":
        nucleo.add("ventas")
    if f & FUNCIONES_ENTREVISTA or ctx in ("Estoy buscando empleo", "Estudio") or meta in ("Conseguir un nuevo puesto", "Prepararme para mi primer empleo"):
        nucleo.add("entrevistas")
    if ctx == "Me dedico al hogar y la familia" or meta == "Comunicarme mejor con mi familia y comunidad":
        nucleo.add("comunicacion")
    if lidera(ob):
        nucleo.add("liderazgo")
    return nucleo or {"comunicacion"}


def lidera(onboarding: dict) -> bool:
    """¿Tiene gente a cargo (o aspira a tenerla) según lo declarado?"""
    ob = onboarding or {}
    f = set(ob.get("funciones") or [])
    return bool(f & FUNCIONES_LIDERA) or ob.get("dm_lidera", "") in ("Superviso a una persona", "Lidero un equipo de hasta 5", "Lidero un equipo de más de 5") \
        or ob.get("meta") in ("Capacitar a mi equipo",) or ob.get("dm_trabajo") in ("Liderar personas y proyectos", "Generar negocio nuevo", "Crear empresas o nuevos modelos")


def es_kpi(habilidad_id: str) -> bool:
    """Habilidades evaluadas por KPIs ponderados (todas salvo la Ruta DM, que usa competencias /10)."""
    return bool((HABILIDADES.get(habilidad_id) or {}).get("kpis"))


def habilidades_kpi() -> list[str]:
    return [h for h in HABILIDADES if es_kpi(h)]


def kpis_audio(habilidad_id: str) -> set[str]:
    return {k["id"] for k in (HABILIDADES.get(habilidad_id) or {}).get("kpis", []) if k.get("audio")}


def nivel_generico_estimado(onboarding: dict) -> str:
    return nivel_ventas_estimado(onboarding)


def es_contexto_empresa(onboarding: dict) -> bool:
    return (onboarding or {}).get("contexto", "") in ("Trabajo en una empresa", "Otra", "")


def habilidades_relevantes(onboarding: dict, diagnostico: dict | None, habs_empresa: list[dict]) -> tuple[list[dict], list[dict]]:
    """Qué escenarios le sirven a ESTA persona: los de su rol/contexto + los que Elena marcó con brecha alta o media. El resto queda como 'otras'.
    Las habilidades personalizadas (Ruta DM) sólo si su empresa las tiene y su contexto es de empresa."""
    usa = habilidades_que_usa(onboarding or {})
    if es_contexto_empresa(onboarding or {}):
        return list(habs_empresa), []   # colaboradores de empresa: la experiencia completa (todas las habilidades habilitadas), como hasta ahora
    prior = {p.get("habilidad_id") for p in (diagnostico or {}).get("prioridades", []) if p.get("brecha") in ("alta", "media")}
    relevantes, otras = [], []
    for h in habs_empresa:
        if h["id"] == "ruta_dm":
            (relevantes if "ruta_dm" in usa else otras).append(h)
        elif h["id"] in usa or h["id"] in prior:
            relevantes.append(h)
        else:
            otras.append(h)
    if not relevantes and habs_empresa:   # nunca dejamos a alguien sin escenario: el de menor barrera (ventas trata con personas)
        relevantes.append(habs_empresa[0])
        otras = [h for h in habs_empresa if h["id"] != relevantes[0]["id"]]
    return relevantes, otras


def nivel_dm_estimado(onboarding: dict) -> str:
    """Estimación previa (la confirma Elena en la entrevista)."""
    if onboarding.get("contexto") in ("Tengo mi negocio u oficio", "Estudio", "Me dedico al hogar y la familia", "Estoy buscando empleo"):
        return "DM Básico"
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


def turnos_minimos(habilidad_id: str, nivel: str | None) -> int:
    """Antes de este intercambio el avatar no puede cerrar por su cuenta (la persona sí, escribiendo Fin)."""
    return max(6, (turnos_max(habilidad_id, nivel) * 6 + 9) // 10)


def duracion_min(habilidad_id: str, nivel: str | None) -> int:
    h = HABILIDADES.get(habilidad_id) or {}
    d = h.get("duracion", {})
    return int(d.get(nivel or "", d.get("*", 20)))


def turnos_max_sesion(sesion: dict) -> int:
    if sesion.get("tipo") == "laboratorio":
        from .laboratorio import TURNOS_MAX
        return TURNOS_MAX
    return turnos_max(sesion["habilidad"], sesion.get("nivel"))


def duracion_sesion(sesion: dict) -> int:
    if sesion.get("tipo") == "laboratorio":
        from .laboratorio import DURACION_MIN
        return DURACION_MIN
    return duracion_min(sesion["habilidad"], sesion.get("nivel"))
