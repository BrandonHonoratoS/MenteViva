# Los agentes de Mente Viva

Todas las instrucciones viven en `app/agents/prompts.py`; los esquemas de salida en `app/agents/esquemas.py`; el catálogo (KPIs, pesos, Ruta DM, variables de onboarding) en `app/agents/catalogo.py`.

## Elena Ríos — diagnóstico y entrevistas (CAT-03)

- **Diagnóstico**: conoce el perfil declarado (no vuelve a preguntar nombre/rol/industria), recorre rapport → encuadre → desarrollo (3 historias) → profundización STAR (3+ repreguntas) → cierre. Un turno, una pregunta; nunca evalúa en voz alta. Salida por turno: `{mensaje, fase, historias}` (la UI muestra la fase y las historias STAR).
- **Análisis**: 10 competencias 1–5 con evidencia (0 = sin evidencia), fortalezas, oportunidades con micro-práctica, blind spot, estilo, nivel de ventas, nivel DM (confirma o corrige la estimación del cuestionario, conservador), nivel de entrevistas, prioridades por brecha → roadmaps.
- **Práctica de entrevista**: 3 niveles (cálida / exigente / panel) y 5 KPIs con pesos.

## Celeste López — Clínica de Ventas (CAT-01 v3.0)

- Personaje: dueña de logística (B2C) o directora de compras (B2B) según el modelo de venta declarado; se adapta al rubro y a las 10 variables (producto, modelo, industria, canal, tamaño, ticket, experiencia, estilo, etapa débil —60 % de la presión—, objetivo).
- Niveles: Principiante (2 objeciones), Intermedio (competidor en la mesa, 3 objeciones, cierre con fecha), Avanzado (abre con 30 %, 5 objeciones, NO al primer cierre, máx. 15 % con contraprestación; ceder sin negociar = cierre fallido y el score se acota a 59).
- Reglas absolutas: nunca rompe personaje, objeciones una a la vez, descuento prematuro sube presión, escucha genuina abre 20 %, silencio activo, máx. 3 oraciones, cierre por tiempo.
- Feedback: KPI-1…KPI-6 con pesos por nivel (Principiante 25/25/30/20/0/0 · Intermedio 35/0/25/0/20/20 · Avanzado 25/20/15/15/15/10), evidencia objetiva (técnicas, SPIN, etapas, primer descuento, silencio, objeciones, cierre), fortalezas, oportunidades, momentos clave, plan de 3 pasos, tips, métrica de la etapa débil, recomendación (nivel + objetivo siguiente).

## Juan Artiaga — Ruta Delivery Manager (Ingeniería Cóndor)

- Ruta de 7 niveles con sus competencias (`catalogo.RUTA_DM`); entrena siempre el **siguiente** nivel.
- **Diseño de sesión** (una llamada): formato (roleplay / caso / reto; sugerido por competencia, la IA decide), título, encuadre, personaje, situación, primer mensaje, 3–4 sub-dimensiones observables, dificultad inicial.
- Sesión: roleplay con obstáculos crecientes, caso con opciones y consecuencias, o reto con reacción realista; nunca evalúa en voz alta; seguridad ante malestar real.
- Feedback de 9 secciones: resumen, sub-dimensiones /10, global /10 + dominio (Principiante 1–4 · En desarrollo 5–6 · Sólido 7–8 · Listo 9–10), fortalezas, brechas para ascender, momento clave, plan (qué / cómo esta semana / señal), tips, siguiente competencia.
- Ascenso: propuesta automática con evidencia cuando todas las competencias del siguiente nivel cumplen la regla; RRHH aprueba y Juan diseña el nuevo plan.

### Laboratorio Interactivo de Habilidades para Delivery Managers (`agents/laboratorio.py`)

- **Qué es**: simulación profesional de dos casos con eventos encadenados — *Proyecto Fénix* (entrega bajo presión: reunión, presión del cliente, riesgo oculto, cambio de alcance, CIO en 90 s) y *War Room* (incidente en producción: llamada, nueva evidencia, fatiga del equipo, presión ejecutiva, cierre operativo). Juan actúa como **evaluador neutral**: presenta, reacciona como los personajes, libera información, registra evidencia en silencio y sólo evalúa al final.
- **Dónde vive**: es el **primer ítem del plan de la Ruta DM** (punto de partida) y se repite como **checkpoint cada 6 sesiones**; también se puede tomar voluntariamente desde el catálogo (`/laboratorio`). La primera vez corre el guion fijo del documento; en checkpoints Juan genera dos casos equivalentes ambientados en el contexto de la persona (`JUAN_LAB_VARIANTE`, validados por `normalizar_casos`).
- **Motor (muy barato en tokens)**: bienvenida y Caso 1 · Evento 1 son texto fijo (0 llamadas); por cada respuesta hay UNA llamada corta en la que Juan escribe sólo la reacción de los personajes (regla de consecuencias) y el sistema añade el siguiente evento tal cual; máximo una pregunta neutral de profundización por evento (el motor la bloquea después); "Fin" cierra con lo respondido; un laboratorio sin respuestas se descarta.
- **Reglas del prompt** (`JUAN_LABORATORIO`): no contaminación (sin "muy bien", "te faltó", sin calificaciones parciales), inmersión (personajes creíbles), consecuencias, adaptación (no repreguntar lo que ya hizo), no revelar el motor, seguridad.
- **Reporte** (`FEEDBACK_LABORATORIO`, 100 puntos): Escucha activa 30 · Manejo del estrés y liderazgo bajo presión 25 · Gestión de proyectos/PMBOK 25 · Comunicación ejecutiva 20; escala 90+ sobresaliente / 80 sólido / 70 funcional / 60 en desarrollo / <60 requiere fortalecimiento; radar cualitativo, 3 fortalezas (evidencia + por qué), 3 oportunidades (observado, riesgo, cómo fortalecerlo), 3–5 momentos clave, lectura por habilidad, 3–5 recomendaciones, prioridad de desarrollo y cierre. Principio: evalúa lo que la persona HACE, no lo que dice que sabe; sin puntos por mencionar LEAD/PMBOK/PREP.
- **Fuente única de conocimiento** (`laboratorio.BASE_CONOCIMIENTO`): destilado compacto (~2.5k tokens) de los cuatro materiales del taller DM2 — *La escucha activa* (ciclo operativo, enemigos, parafraseo, preguntas útiles, L.E.A.D., checklist, 5 prácticas), *Manejo del estrés en equipos* (señales, priorizar, pausas, manejo saludable de incidentes, resiliencia, comunicación en incidentes, antes/durante/después), *Guía PMBOK* (5 grupos de procesos, 10 áreas, triángulo alcance-tiempo-costo, conductas observables) y *Cómo hablar en público* (PREP, Storytelling, 3 Actos, SCQA, 3 ideas, PEP, C.O.N.E.C.T.A., A.I.R.E., lenguaje corporal, audiencia). Viaja sólo en la llamada del reporte (no en cada turno) y, en el chat del coach sobre un reporte de laboratorio, sólo las dos dimensiones relevantes (prioridad + la más baja). El reporte no puede usar modelos ajenos a estos materiales y cada oportunidad cita el material con el que se relaciona.
- **Integración con la Ruta DM** (Analista): cada dimensión se registra como evidencia de las competencias DM que mapea (Escucha activa; Manejo de ansiedad y Resiliencia; PMBOK; Comunicación e Influencia) y cuenta para la regla de ascenso; el total /100 alimenta las reglas de nivel; la prioridad de desarrollo pasa a ser la **siguiente sesión del plan** (se reordena o se inserta) y el Analista programa el siguiente checkpoint.

## El Analista

- **Recalibración tras cada sesión**: aplica reglas de nivel (sube/baja, refuerzo a las 3 sin mejora), renivela los ítems pendientes, reescribe el objetivo de la siguiente sesión del plan con su lectura (que integra la recomendación del avatar y las metas del líder), reordena/inserta la prioridad del laboratorio, propone ascensos DM y genera el siguiente plan al terminar uno. **Metas del líder**: entran al diseño del roadmap y a cada lectura; al cumplirse (promedio de las últimas 2 sesiones ≥ mínimo, por habilidad y competencia) la meta individual se marca *alcanzada* y se notifica a quien la creó, al director y al colaborador; las metas de área/empresa se avisan por persona. Las metas en sí sólo las cambian RRHH o el director (el Analista puede proponer ajustes como propuesta). **Meta nueva sobre un plan ya diseñado** (`recalibrar_por_meta`, en segundo plano al crearla): los planes activos afectados (la persona, o toda el área/empresa, hasta 40) se recalibran al momento: si la meta fija una competencia DM, pasa a ser la siguiente sesión; el Analista reescribe con el modelo ligero el objetivo y el porqué de las sesiones pendientes hacia el score mínimo, la competencia y el plazo, sin tocar semana/nivel/competencia; sube la versión del plan y avisa al colaborador y a quien creó la meta.

- **Post-sesión** (modelo ligero, entrada compacta): lectura para el líder, riesgo y motivo, recomendación accionable, siguiente objetivo (se escribe en el siguiente ítem del roadmap), ajuste de plan, señales. Las decisiones de nivel las aplica el sistema y el Analista las explica.
- **Periódico**: resumen semanal por área y organización (avanzan / atención / 3 recomendaciones con responsable y señal de éxito); alertas de inactividad (7 días).
- **Chat con herramientas** (director: su área; RRHH/DG: toda la empresa): `listar_colaboradores`, `ficha_colaborador`, `kpis`, `sesiones_recientes`, `metas_vigentes`, `investigar` (Google Search con fuentes, tope mensual), `proponer` (registra propuestas para aprobación). Nunca reproduce transcripciones ni inventa cifras: si no tiene el dato, lo dice.
- **Investigación anti-alucinación**: sólo afirma lo que sustentan las fuentes devueltas por la búsqueda; prefiere dominios oficiales/académicos; si no hay fuentes, lo marca como orientación no verificada; las fuentes se muestran con su dominio en la interfaz y se guardan en *Análisis*.

## Chat con el coach (reporte)

El colaborador puede preguntar a Celeste/Elena/Juan sobre su reporte; el contexto es el JSON del reporte (no la transcripción), por lo que cuesta pocos tokens y no inventa momentos.
