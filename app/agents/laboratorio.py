"""Laboratorio Interactivo de Habilidades para Delivery Managers (Ruta DM · Ingeniería Cóndor).

Simulación profesional de dos casos con eventos encadenados, conducida por Juan Artiaga como evaluador neutral: no enseña, no
sugiere, no evalúa en voz alta. Registra evidencias de conducta y al final entrega un reporte de 100 puntos en cuatro
dimensiones (escucha activa 30, manejo del estrés y liderazgo bajo presión 25, gestión de proyectos/PMBOK 25, comunicación
ejecutiva 20) con escala de dominio.

Este módulo contiene:
- la rúbrica (dimensiones, criterios, escala) y el mapeo a competencias de la Ruta DM;
- el guion fijo de los dos casos del documento (Proyecto Fénix y War Room) con sus eventos;
- utilidades deterministas del motor: texto de cada evento, avance de estado, puntaje total y nivel.

El guion fijo se usa la primera vez; en los checkpoints Juan genera casos equivalentes (misma estructura) para evitar memorización.
"""
from __future__ import annotations

ID = "laboratorio_dm"
NOMBRE = "Laboratorio Interactivo de Habilidades para Delivery Managers"
CORTO = "Laboratorio DM"
DURACION_MIN = 35
TURNOS_MAX = 26          # 10 eventos + hasta 1 pregunta de profundización por evento + margen
CHECKPOINT_CADA = 6      # cada N sesiones de práctica de la Ruta DM se vuelve a correr el laboratorio (con casos nuevos)

# ── Rúbrica ─────────────────────────────────────────────────────────────────
DIMENSIONES = [
    {"id": "escucha", "nombre": "Escucha activa", "corto": "Escucha", "puntos": 30,
     "competencias_dm": ["Escucha activa"],
     "criterios": "escuchar antes de responder; preguntas útiles; profundización; contextualización; evidencia; parafraseo; validación; identificación de "
                  "señales débiles; confirmación; cierre de acuerdos; seguimiento. Ciclo de referencia: Escuchar → Comprender → Preguntar → Confirmar → "
                  "Responder → Dar seguimiento. Modelo LEAD: Listen, Empathize, Ask, Deliver."},
    {"id": "estres", "nombre": "Manejo del estrés y liderazgo bajo presión", "corto": "Estrés y presión", "puntos": 25,
     "competencias_dm": ["Manejo de ansiedad", "Resiliencia"],
     "criterios": "calma; priorización; ausencia de culpabilización; colaboración; contención; distribución de carga; identificación de fatiga; reducción de "
                  "ruido; claridad de responsabilidades; sostenibilidad; orientar la conversación hacia solución; tomar decisiones con evidencia; documentar; "
                  "aprender del incidente."},
    {"id": "pmbok", "nombre": "Gestión de proyectos / PMBOK", "corto": "PMBOK", "puntos": 25,
     "competencias_dm": ["PMBOK"],
     "criterios": "alcance; tiempo; calidad; costos cuando sean relevantes; riesgos; recursos; interesados; comunicaciones; monitoreo; control de cambios; "
                  "cierre; aprendizaje. Relación ALCANCE ↔ TIEMPO ↔ COSTO y su impacto en la calidad. Diferencia hechos de supuestos; solicita información "
                  "antes de comprometer decisiones; analiza impacto; establece responsables y seguimiento. No exige terminología PMBOK."},
    {"id": "comunicacion", "nombre": "Comunicación ejecutiva y hablar en público", "corto": "Comunicación", "puntos": 20,
     "competencias_dm": ["Comunicación", "Influencia"],
     "criterios": "claridad; estructura; síntesis; relevancia; adaptación a audiencia; lenguaje simple; idea principal; problema; impacto; propuesta; acción "
                  "final; comunicar bajo presión sin perder claridad. Estructuras disponibles: PREP (Punto→Razón→Ejemplo→Reafirmación), Storytelling "
                  "(Situación→Problema→Solución→Aprendizaje), 3 Actos, SCQA (Situación→Complicación→Pregunta→Respuesta), Mensaje en 3 ideas, PEP "
                  "(Postura→Energía→Propósito), C.O.N.E.C.T.A., A.I.R.E. (Atención→Interés→Relevancia→Expectativa)."},
]
DIM_IDS = [d["id"] for d in DIMENSIONES]
PUNTOS_TOTAL = sum(d["puntos"] for d in DIMENSIONES)

# ── Fuente única de conocimiento (destilado de los 4 materiales del taller DM2 de Ingeniería Cóndor) ──
# Se usa SOLO en el reporte y en el chat del coach (una llamada), nunca en los turnos del roleplay, para no encarecer cada turno.
BASE_CONOCIMIENTO = {
    "escucha": """Taller "La escucha activa" (Delivery Management).
- Idea central: escuchar activamente es entender antes de defender, confirmar antes de ejecutar y preguntar antes de asumir. "Una conversación bien escuchada evita tres reuniones de corrección." Cuando el delivery falla, suele iniciar en una conversación incompleta: "el cliente nunca lo dijo" (no se exploró la necesidad real), "yo entendí otra cosa" (no se confirmó el acuerdo), "pensé que estaba claro" (faltó evidenciar responsables y fechas).
- Cuatro objetivos del DM: detectar señales débiles (riesgos antes de que sean incidentes), validar entendimiento (cerrar brechas entre lo dicho, lo entendido y lo acordado), gestionar emociones (responder a presión, enojo o incertidumbre sin defensividad) y cerrar acuerdos (acciones, responsables y fechas).
- Cuatro enemigos: interrumpir ("ya sé la respuesta"), suponer ("seguro quiere decir…"), defenderse ("no fue culpa nuestra"), preparar la respuesta mientras el otro habla.
- Ciclo operativo: Escuchar sin interrumpir → Comprender mensaje + contexto → Preguntar para profundizar señales → Confirmar parafraseando acuerdos → Responder (decidir y orientar) → Dar seguimiento (cerrar el loop). Regla práctica: no respondas formalmente hasta que puedas resumir el problema mejor que quien lo planteó.
- Técnica 1, parafrasear para validar: comprobar intención e impacto, no repetir ("Entiendo que el cambio ayudó en parte, pero todavía perciben lentitud en procesos específicos. ¿En cuáles y en qué horarios?"); mueve la conversación de juicio a evidencia y muestra presencia sin prometer de más.
- Técnica 2, preguntas que abren información útil: en vez de "¿está bien?" → "¿qué aspecto consideran más crítico?"; "¿quién tuvo la culpa?" → "¿qué factores nos llevaron a este punto?"; "¿ya quedó?" → "¿qué evidencia necesitamos para darlo por cerrado?". Pregunta útil = contexto + impacto + evidencia + siguiente acción.
- Cliente difícil: no escuches el volumen, escucha la necesidad (incertidumbre, presión ejecutiva, pérdida económica, falta de información). Respuesta tipo: "Entiendo la preocupación. Ayúdame a ubicar horarios, impacto y evidencia para validar qué ocurrió y acordar contención."
- Equipo técnico: "todo está bien" no siempre significa que todo está bien (saturación, riesgo no verbalizado, bloqueo técnico, miedo a escalar). Pregunta del DM: "¿Qué tendría que cambiar para que esto deje de ser riesgo y pase a estar controlado?"
- Modelo L.E.A.D. para reuniones críticas (war rooms, estatus ejecutivos, CABs, conflicto): Listen (la historia completa), Empathize (reconocer impacto y urgencia), Ask (evidencia y prioridad), Deliver (confirmar acciones y seguimiento). Convierte una conversación emocional en un plan operativo.
- Checklist antes de responder: ¿terminó de hablar? ¿entendí problema e impacto? ¿validé su preocupación sin aceptar culpa prematura? ¿hice al menos una pregunta abierta? ¿confirmé lo entendido con mis palabras? ¿cerramos acciones, responsables y fechas?
- Las 5 prácticas: calla primero, parafrasea, pregunta mejor, valida la emoción, cierra el loop. Ejercicio: "dos minutos sin rescatar" (escuchar y preguntar sin solucionar, resumir en 30 s, el otro confirma).""",
    "estres": """Taller "Manejo del estrés en equipos" (TI).
- El estrés laboral es la respuesta física y emocional ante situaciones que exceden temporalmente la capacidad de adaptación; en TI aparece como fatiga mental, irritabilidad, dificultad para concentrarse, ansiedad, agotamiento, menor rendimiento y errores operativos. Detonantes típicos: incidentes críticos, errores en producción, saturación (CPU, memoria, conectividad), despliegues urgentes, guardias, trabajo fuera de horario, presión de usuarios, dependencia entre áreas, múltiples prioridades simultáneas.
- Señales de alerta: físicas (cansancio constante, dolor de cabeza, insomnio, tensión), emocionales (frustración, ansiedad, irritabilidad, desmotivación), laborales (errores frecuentes, dificultad para priorizar, baja concentración, agotamiento). Impacto si no se controla: burnout y rotación; más errores y conflictos en el equipo; incidentes repetitivos, mala toma de decisiones y recuperación lenta en la operación.
- Técnicas: (1) priorizar correctamente: no todo es crítico al mismo tiempo, clasificar incidentes, usar matrices de prioridad, evitar la multitarea excesiva; (2) pausas cortas y controladas (5 minutos cada hora, alejarse de la pantalla, respiración profunda); (3) manejo saludable de incidentes: evitar culpas personales y presión innecesaria, promover colaboración, análisis objetivo y enfoque en solución.
- Resiliencia y organización: aprendizaje continuo, documentación clara, runbooks actualizados, monitoreo preventivo, alertas inteligentes y automatización reducen la carga mental y los incidentes inesperados.
- Comunicación en incidentes: hablar con claridad, asignar responsables, evitar culpabilizar y generar pánico. Líderes: distribuir cargas equilibradamente, reconocer esfuerzos, evitar la cultura de sobrecarga, promover capacitación; respetar descanso y desconexión fuera de horario.
- Antes / durante / después de un incidente: validar monitoreo y revisar procedimientos; mantener la calma y comunicar tareas; analizar, documentar y mejorar procesos. Gestionar el estrés no significa disminuir compromiso: significa trabajar de forma sostenible, proteger la salud y mejorar la toma de decisiones.""",
    "pmbok": """Taller "La Guía PMBOK: tu hoja de ruta para el éxito en proyectos" (PMI).
- Tres pilares: marco conceptual (principios y fundamentos), norma para la dirección (procesos reconocidos como buenas prácticas) y áreas de conocimiento.
- Cinco grupos de procesos, que se superponen e interactúan (no son fases rígidas): Inicio (definir y autorizar; acta de constitución, objetivos, stakeholders clave), Planificación (alcance, cronograma con hitos, presupuesto, criterios de calidad, recursos, riesgos), Ejecución (llevar a cabo el trabajo, comunicación constante con stakeholders, resolver conflictos, administrar contratos), Monitoreo y Control (comparar avance real con la línea base, controles de calidad, gestionar riesgos nuevos, controlar cambios al alcance, informes de estado) y Cierre (aceptación, liberación de recursos, documentación final, lecciones aprendidas, informe de desempeño).
- Diez áreas de conocimiento: Integración (coordina todo), Alcance (qué está y qué no está incluido), Cronograma (planificación y control del tiempo), Costos (estimar y controlar presupuesto), Calidad (entregables que cumplen estándares), Recursos (equipos y materiales), Comunicaciones (flujo de información entre actores), Riesgos (identificar, analizar y responder), Adquisiciones (contratos y proveedores), Interesados (identificar y gestionar expectativas de stakeholders).
- Triángulo del diablo: alcance, tiempo y costo están interconectados; si una cambia, las demás se ven afectadas, y la calidad es el resultado del equilibrio entre las tres.
- Beneficios de seguirlo: menos riesgos, retrasos y desviaciones; mejor uso de tiempo, presupuesto y personas; cumplimiento consistente de expectativas y plazos; un lenguaje común que elimina ambigüedades.
- Conductas que lo reflejan sin usar jerga: diferenciar hechos de supuestos; pedir información antes de comprometer; analizar el impacto de cada cambio en alcance-tiempo-costo-calidad; registrar el cambio y decidir si entra o va a la siguiente ventana; definir responsables, hitos y seguimiento; proteger la calidad (pruebas) antes de la fecha; cerrar con evidencia, documentación y lecciones aprendidas.""",
    "comunicacion": """Taller "Cómo hablar en público" (Administración Óptima · soft skills).
- No se trata de hablar bonito ni de no tener nervios: la gente no recuerda todo lo que dices, recuerda lo que transmites. Nervios, sudor, voz temblorosa o bloqueo no son falta de talento. Beneficios: confianza, credibilidad, influir y persuadir, conectar.
- Estructuras: PREP (Punto → Razón → Ejemplo → Reafirmación; el favorito en entornos corporativos y presentaciones ejecutivas). Storytelling (Situación → Problema → Solución → Aprendizaje; el cerebro recuerda historias). 3 Actos (Apertura que capta atención con pregunta, dato o experiencia → Desarrollo con máximo 3 ideas → Cierre con mensaje poderoso + acción). SCQA (Situación → Complicación → Pregunta → Respuesta; usado por consultoras estratégicas). Mensaje en 3 ideas (el cerebro recuerda máximo 3 conceptos; idea 1, 2, 3 y resumen). PEP para controlar nervios (Postura abierta y estable → Energía con respiración profunda → Propósito: "voy a aportar valor"). C.O.N.E.C.T.A., el más utilizado (Claridad del mensaje → Objetivo definido → Naturalidad → Ejemplo real → Confianza corporal → Tiempo breve → Acción final). A.I.R.E. para los primeros 30 segundos (Atención con un gancho → Interés con un problema real → Relevancia: por qué importa → Expectativa: qué aprenderán).
- Lenguaje corporal consciente: hombros abiertos, barbilla paralela al piso, manos visibles, mirada a la audiencia, volumen modulado, energía dosificada; evitar balancearse, cruzar brazos, mirar al piso, hablar lento y bajo.
- Contenido y audiencia: dominio del tema, estructura, apoyos visuales con medida; conocer a la audiencia e interactuar, recuperar el interés si se pierde, mensaje claro, concreto, coherente y conciso, vocabulario simple, silencios cuando hagan falta, contacto visual, agradecer; no leer todo el tiempo.
- Tips: ensayar (frente al espejo, con un lápiz en la boca para la dicción), no memorizar (entender y priorizar permite improvisar), respiración 4-7-8, control emocional (mantener el mensaje pese a factores externos), aceptar la imperfección.
- En comunicación ejecutiva bajo presión: idea principal primero, problema, impacto, evidencia, propuesta y siguiente acción; lenguaje simple adaptado a la audiencia; tiempo breve; incertidumbre comunicada con claridad y una próxima actualización comprometida.""",
}


def base_conocimiento_texto() -> str:
    return "\n\n".join(f"[{d['nombre'].upper()}]\n{BASE_CONOCIMIENTO[d['id']]}" for d in DIMENSIONES)


ESCALA = [
    (90, "Dominio sobresaliente", "Integra las habilidades de forma natural, consistente y efectiva incluso bajo presión."),
    (80, "Dominio sólido", "Demuestra buenas conductas de liderazgo y comunicación, con oportunidades puntuales de refinamiento."),
    (70, "Competencia funcional", "Resuelve adecuadamente buena parte de las situaciones, aunque presenta inconsistencias que podrían generar riesgos en escenarios complejos."),
    (60, "Competencia en desarrollo", "Existen comportamientos positivos, pero todavía aparecen brechas importantes en situaciones de presión o incertidumbre."),
    (0, "Requiere fortalecimiento", "Presenta oportunidades relevantes que pueden afectar toma de decisiones, comunicación, gestión de riesgos o desempeño del equipo."),
]
RADAR = ["Fortalecido", "Sólido", "En desarrollo", "Requiere atención"]


def nivel_dominio(total: float) -> tuple[str, str]:
    for minimo, nombre, desc in ESCALA:
        if total >= minimo:
            return nombre, desc
    return ESCALA[-1][1], ESCALA[-1][2]


def dimension(id_: str) -> dict | None:
    return next((d for d in DIMENSIONES if d["id"] == id_), None)


# ── Guion fijo (documento "Laboratorio Interactivo de Habilidades para Delivery Managers") ──
MENSAJE_BIENVENIDA = (
    "Bienvenido al Laboratorio de Habilidades para Delivery Managers.\n\n"
    "Participarás en dos situaciones profesionales. No hay respuestas de opción múltiple ni necesitas mencionar metodologías.\n\n"
    "Responde como actuarías realmente. Puedes escribir qué harías, qué dirías o ambas cosas.\n\n"
    "Las situaciones evolucionarán de acuerdo con tus decisiones y al terminar recibirás un reporte integral de retroalimentación.\n\n"
    "Cuando estés listo, comenzamos."
)

CASOS_FIJOS: list[dict] = [
    {
        "id": "fenix", "titulo": "Proyecto Fénix — “Tenemos que salir el viernes”",
        "contexto": ("Eres responsable de un proyecto tecnológico que está a pocos días de una liberación importante. El cliente espera una salida a "
                     "producción el viernes. Es miércoles a las 10:15 a. m. y se realiza una reunión extraordinaria."),
        "personajes": "Cliente / Director de Operaciones, Líder técnico, Consultor funcional, QA, CIO (entra al final).",
        "eventos": [
            {"id": "f1", "titulo": "La reunión extraordinaria",
             "texto": ("Cliente / Director de Operaciones: “Necesito que quede claro: esto tiene que salir el viernes. Ya lo comprometimos con Dirección. "
                       "Llevamos semanas escuchando que todo va bien y ahora me dicen que existen riesgos. No quiero explicaciones técnicas, quiero saber si vamos a cumplir.”\n\n"
                       "Líder técnico: “Sí podemos salir… creo. Todavía tenemos unas cosas por revisar, pero deberíamos llegar.”\n\n"
                       "Consultor funcional: “El cliente pidió ayer tres modificaciones adicionales. Dice que son pequeñas y que deberían entrar en esta liberación.”\n\n"
                       "QA: “No hemos terminado las pruebas. Si entran esos cambios tendríamos que volver a validar parte del flujo.”"),
             "pregunta": "Tú estás dirigiendo esta reunión. ¿Qué haces o qué dices en este momento?",
             "evalua": "identifica ambigüedad; pregunta antes de comprometer; explora evidencia; investiga riesgos; diferencia hechos de percepciones; considera QA, "
                       "alcance, fecha y calidad; evita responder solamente sí o no; estructura la conversación."},
            {"id": "f2", "titulo": "Presión del cliente",
             "texto": "Cliente: “No entiendo por qué estamos haciendo tantas preguntas. Necesito una respuesta: ¿sí o no salimos el viernes?”",
             "pregunta": "¿Qué respondes?",
             "evalua": "manejo de presión; escucha; claridad; empatía sin prometer de más; capacidad para sostener incertidumbre; orientación a evidencia; comunicación ejecutiva."},
            {"id": "f3", "titulo": "Riesgo oculto",
             "texto": ("Después de tu intervención, el líder técnico dice: “La verdad es que ayer encontramos una falla. No siempre ocurre, pero puede duplicar información "
                       "en determinadas operaciones. No lo comenté porque todavía estamos tratando de reproducirla y pensé que podríamos resolverla antes del viernes.”"),
             "pregunta": "La información cambia el escenario. ¿Qué haces ahora?",
             "evalua": "reacción ante riesgo oculto; ausencia o presencia de culpabilización; investigación; evidencia; priorización; calidad; gestión del equipo; "
                       "comunicación; acciones; responsables; seguimiento."},
            {"id": "f4", "titulo": "Cambio de alcance",
             "texto": "Cliente: “Entonces por lo menos incluyan los tres cambios que pedimos ayer. No deberían tomar más de un día.”",
             "pregunta": "¿Cómo manejarías esta solicitud?",
             "evalua": "alcance; tiempo; costo cuando corresponda; calidad; riesgo; control de cambios; negociación; expectativa del stakeholder; claridad de comunicación. No exige lenguaje técnico."},
            {"id": "f5", "titulo": "Comunicación ejecutiva",
             "texto": ("El CIO entra a la reunión y dice: “Me dijeron que existe un problema con el proyecto. Tengo otra reunión en dos minutos. Explícame dónde estamos y qué propones.”"),
             "pregunta": "Tienes aproximadamente 90 segundos. Respóndele como si estuvieras hablando directamente con el CIO.",
             "evalua": "idea principal; claridad; síntesis; estructura; problema; impacto; evidencia; propuesta; siguiente acción; adecuación a audiencia ejecutiva; lenguaje simple; seguridad comunicativa."},
        ],
    },
    {
        "id": "warroom", "titulo": "War Room — “Producción está caída”",
        "contexto": ("Son las 6:42 p. m. Hace aproximadamente 40 minutos se liberó una modificación a producción. Varios usuarios reportan que el sistema está "
                     "extremadamente lento. Se convoca una llamada de emergencia."),
        "personajes": "Cliente, DBA, Middleware, Desarrollador, Director del cliente, Director General (entra después).",
        "eventos": [
            {"id": "w1", "titulo": "La llamada de emergencia",
             "texto": ("Cliente: “Esto es inaceptable. Tenemos usuarios sin poder trabajar y ustedes hicieron el cambio. Necesito que reviertan todo ahora.”\n\n"
                       "DBA: “La base está consumiendo demasiados recursos, pero todavía no sabemos por qué.”\n\n"
                       "Middleware: “De nuestro lado no vemos nada fuera de lo normal.”\n\n"
                       "Desarrollador: “Mi cambio no toca base de datos. No creo que sea nuestro despliegue.”\n\n"
                       "Director del cliente: “Cada minuto que pasa nos afecta. ¿Quién se va a hacer responsable?”"),
             "pregunta": "Estás liderando la llamada. ¿Qué haces?",
             "evalua": "escucha antes de concluir; evita asumir causa; evita defenderse; evita entrar en discusión de culpas; reconoce impacto; prioriza; solicita evidencia; "
                       "asigna investigación; estructura responsables; contiene emocionalmente la conversación; comunica siguientes pasos; establece seguimiento."},
            {"id": "w2", "titulo": "Nueva evidencia",
             "texto": ("DBA: “CPU está al 95 %, pero también encontramos procesos que ya venían creciendo desde antes del despliegue.”\n\n"
                       "Cliente: “Entonces ¿el despliegue no tuvo nada que ver?”"),
             "pregunta": "¿Cómo respondes y qué haces a continuación?",
             "evalua": "diferencia correlación de causa; evidencia disponible; información todavía desconocida; necesidad de continuar investigando."},
            {"id": "w3", "titulo": "Fatiga del equipo",
             "texto": "El desarrollador comenta: “Yo ya llevo once horas conectado. Si necesitan revisar código lo hago, pero necesitaría un rato.”",
             "pregunta": "¿Cómo manejas esta situación sin perder el control del incidente?",
             "evalua": "detección de agotamiento; sostenibilidad; distribución de carga; colaboración; prioridad; protección de la calidad de las decisiones; liderazgo; "
                       "continuidad operativa. No penaliza automáticamente que continúe participando."},
            {"id": "w4", "titulo": "Presión ejecutiva",
             "texto": "El Director General solicita entrar a la llamada y dice: “Quiero saber qué pasó, qué estamos haciendo y cuándo recibiré la siguiente actualización. Tengo un minuto.”",
             "pregunta": "Respóndele directamente.",
             "evalua": "claridad; síntesis; hechos; incertidumbre correctamente comunicada; impacto; acciones; responsables cuando corresponda; próxima actualización; ausencia de culpabilización; cierre."},
            {"id": "w5", "titulo": "Cierre operativo",
             "texto": "El servicio comienza a estabilizarse. El incidente está bajo control, aunque todavía será necesario completar el análisis de causa y documentar lo ocurrido.",
             "pregunta": "Antes de dar por cerrado el incidente, ¿qué harías?",
             "evalua": "evidencia para cierre; documentación; análisis; aprendizaje; seguimiento; responsables; comunicación; acciones preventivas; monitoreo."},
        ],
    },
]


# ── Utilidades del motor ────────────────────────────────────────────────────
def texto_evento(casos: list[dict], ci: int, ei: int) -> str:
    """Texto que ve el participante: encabezado de caso (sólo en el primer evento), guion del evento y pregunta."""
    caso = casos[ci]
    ev = caso["eventos"][ei]
    partes = []
    if ei == 0:
        partes.append(f"CASO {ci + 1} · {caso['titulo']}\n\n{caso['contexto']}")
    partes.append(ev["texto"])
    partes.append(f"➤ {ev['pregunta']}")
    return "\n\n".join(partes)


def siguiente(casos: list[dict], ci: int, ei: int) -> tuple[int, int] | None:
    if ei + 1 < len(casos[ci]["eventos"]):
        return ci, ei + 1
    if ci + 1 < len(casos):
        return ci + 1, 0
    return None


def total_eventos(casos: list[dict]) -> int:
    return sum(len(c["eventos"]) for c in casos)


def indice_evento(casos: list[dict], ci: int, ei: int) -> int:
    return sum(len(c["eventos"]) for c in casos[:ci]) + ei + 1


def guion_para_evaluacion(casos: list[dict]) -> str:
    """Guion compacto con la lógica interna de cada evento (lo que el evaluador analiza en silencio)."""
    out = []
    for i, c in enumerate(casos, start=1):
        out.append(f"CASO {i}: {c['titulo']}. Contexto: {c['contexto']}")
        for j, e in enumerate(c["eventos"], start=1):
            out.append(f"  Evento {i}.{j} {e['titulo']}: pregunta «{e['pregunta']}». Evalúa: {e['evalua']}")
    return "\n".join(out)


def normalizar_casos(js: dict | None) -> list[dict] | None:
    """Valida casos generados por la IA (variantes): misma estructura que los fijos; None si no sirven."""
    casos = (js or {}).get("casos") if isinstance(js, dict) else None
    if not isinstance(casos, list) or len(casos) != 2:
        return None
    out = []
    for i, c in enumerate(casos):
        if not isinstance(c, dict):
            return None
        evs = c.get("eventos")
        if not isinstance(evs, list) or not 4 <= len(evs) <= 5:
            return None
        eventos = []
        for j, e in enumerate(evs):
            if not isinstance(e, dict) or not str(e.get("texto", "")).strip() or not str(e.get("pregunta", "")).strip():
                return None
            eventos.append({"id": f"v{i + 1}{j + 1}", "titulo": str(e.get("titulo") or f"Evento {j + 1}")[:80], "texto": str(e["texto"]).strip()[:1800],
                            "pregunta": str(e["pregunta"]).strip()[:300], "evalua": str(e.get("evalua") or "")[:600]})
        out.append({"id": f"variante{i + 1}", "titulo": str(c.get("titulo") or f"Caso {i + 1}")[:120], "contexto": str(c.get("contexto") or "")[:900],
                    "personajes": str(c.get("personajes") or "")[:300], "eventos": eventos})
    return out


def puntaje(dimensiones: list[dict]) -> tuple[float, str, str]:
    total = round(sum(float(d.get("puntos", 0)) for d in dimensiones), 1)
    nombre, desc = nivel_dominio(total)
    return total, nombre, desc
