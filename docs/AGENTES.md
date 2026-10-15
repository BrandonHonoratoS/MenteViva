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

El diplomado en Administración de Proyectos (Lean Progress: PMBOK 7, charter, EDT, PERT/CPM y ruta crítica, costos, riesgos, Scrum, Lean, cierre;
`conocimiento.DIPLOMADO_PM`) y su módulo de liderazgo (`conocimiento.LIDERAZGO`) se añaden a Juan como materiales de referencia en el diseño y el
análisis de las competencias que los usan (PMBOK, Scrum, Toma de decisiones, PMO, Gestión del cambio, Delegación, Retroalimentación…), a la base
del Laboratorio DM y a Sócrates. La sesión 1 de "Manejo de objeciones para técnicos no tan técnicos" (`conocimiento.OBJECIONES_TECNICOS`) y la
imagen vendedora/neuroventas alimentan la Clínica de Ventas en Sócrates.

### Laboratorio Interactivo de Habilidades para Delivery Managers (`agents/laboratorio.py`)

- **Qué es**: simulación profesional de dos casos con eventos encadenados — *Proyecto Fénix* (entrega bajo presión: reunión, presión del cliente, riesgo oculto, cambio de alcance, CIO en 90 s) y *War Room* (incidente en producción: llamada, nueva evidencia, fatiga del equipo, presión ejecutiva, cierre operativo). Juan actúa como **evaluador neutral**: presenta, reacciona como los personajes, libera información, registra evidencia en silencio y sólo evalúa al final.
- **Dónde vive**: es el **primer ítem del plan de la Ruta DM** (punto de partida) y se repite como **checkpoint cada 6 sesiones**; también se puede tomar voluntariamente desde el catálogo (`/laboratorio`). La primera vez corre el guion fijo del documento; en checkpoints Juan genera dos casos equivalentes ambientados en el contexto de la persona (`JUAN_LAB_VARIANTE`, validados por `normalizar_casos`).
- **Motor (muy barato en tokens)**: bienvenida y Caso 1 · Evento 1 son texto fijo (0 llamadas); por cada respuesta hay UNA llamada corta en la que Juan escribe sólo la reacción de los personajes (regla de consecuencias) y el sistema añade el siguiente evento tal cual; máximo una pregunta neutral de profundización por evento (el motor la bloquea después); "Fin" cierra con lo respondido; un laboratorio sin respuestas se descarta.
- **Reglas del prompt** (`JUAN_LABORATORIO`): no contaminación (sin "muy bien", "te faltó", sin calificaciones parciales), inmersión (personajes creíbles), consecuencias, adaptación (no repreguntar lo que ya hizo), no revelar el motor, seguridad.
- **Reporte** (`FEEDBACK_LABORATORIO`, 100 puntos): Escucha activa 30 · Manejo del estrés y liderazgo bajo presión 25 · Gestión de proyectos/PMBOK 25 · Comunicación ejecutiva 20; escala 90+ sobresaliente / 80 sólido / 70 funcional / 60 en desarrollo / <60 requiere fortalecimiento; radar cualitativo, 3 fortalezas (evidencia + por qué), 3 oportunidades (observado, riesgo, cómo fortalecerlo), 3–5 momentos clave, lectura por habilidad, 3–5 recomendaciones, prioridad de desarrollo y cierre. Principio: evalúa lo que la persona HACE, no lo que dice que sabe; sin puntos por mencionar LEAD/PMBOK/PREP.
- **Fuente única de conocimiento** (`laboratorio.BASE_CONOCIMIENTO`): destilado compacto (~2.5k tokens) de los cuatro materiales del taller DM2 — *La escucha activa* (ciclo operativo, enemigos, parafraseo, preguntas útiles, L.E.A.D., checklist, 5 prácticas), *Manejo del estrés en equipos* (señales, priorizar, pausas, manejo saludable de incidentes, resiliencia, comunicación en incidentes, antes/durante/después), *Guía PMBOK* (5 grupos de procesos, 10 áreas, triángulo alcance-tiempo-costo, conductas observables) y *Cómo hablar en público* (PREP, Storytelling, 3 Actos, SCQA, 3 ideas, PEP, C.O.N.E.C.T.A., A.I.R.E., lenguaje corporal, audiencia). Viaja sólo en la llamada del reporte (no en cada turno) y, en el chat del coach sobre un reporte de laboratorio, sólo las dos dimensiones relevantes (prioridad + la más baja). El reporte no puede usar modelos ajenos a estos materiales y cada oportunidad cita el material con el que se relaciona.
- **Integración con la Ruta DM** (Analista): cada dimensión se registra como evidencia de las competencias DM que mapea (Escucha activa; Manejo de ansiedad y Resiliencia; PMBOK; Comunicación e Influencia) y cuenta para la regla de ascenso; el total /100 alimenta las reglas de nivel; la prioridad de desarrollo pasa a ser la **siguiente sesión del plan** (se reordena o se inserta) y el Analista programa el siguiente checkpoint.

## Valeria, Renata, Mateo y Patricia — escenarios por KPI (`agents/avatares.Generico`, `prompts.ESCENARIOS`, `conocimiento.py`)
Cuatro escenarios nuevos con la misma mecánica (una llamada de diseño con la base de conocimiento, turnos baratos sin base, un análisis final con
la misma base; KPIs ponderados y niveles Principiante/Intermedio/Avanzado; estándares de empresa con `{estandar}`):

- **Presentaciones de alto impacto** (Valeria Campos, audiencia · CAT-05). Programa de Capital Intelectual/Cóndor: rúbrica de 9 criterios (apertura 12,
  claridad 15, estructura 12, voz 12, fluidez/muletillas 10, interacción 10, vocabulario 9, cierre 12, tiempo 8) con equivalencia 1–4. La persona
  puede **grabar su voz**: `agents/adjuntos.transcribir_audio` manda el audio UNA vez a Gemini (entrada nativa) y obtiene transcripción + métricas
  (duración, ppm, muletillas/min, pausas, ritmo, variedad vocal, energía al cierre, seguridad 1–4); el audio no se guarda. Los turnos y el análisis
  trabajan con la transcripción y la nota `[Grabación de voz · …]`. Sin grabación, los KPIs de voz quedan "no evaluados" y el score se renormaliza.
- **Imagen profesional y código de vestimenta** (Renata Solís, consultora · CAT-09). Cinco códigos, medidas y ajuste (hombro, puño, caída del pantalón,
  largo de falda), calzado, color, accesorios, perfume, etiqueta y buenos modales, imagen vendedora (7 segundos) y neuroventas (Klarić). La persona
  describe su outfit o **envía una foto** (propia o de referencia): `describir_foto` devuelve una descripción objetiva de la ropa (nunca del cuerpo) y
  la imagen se descarta. 6 KPIs.
- **Comunicación verbal efectiva** (Mateo Ibarra, interlocutor · CAT-07). Para todos los contextos (trabajo, pareja, hijos, familia, vecinos,
  trámites): CNV de Rosenberg, escucha activa, asertividad (DESC, disco rayado, banco de niebla), conversaciones difíciles, Gottman. 6 KPIs; también
  admite voz.
- **Liderazgo** (Patricia Navarro, integrante del equipo · CAT-04). Diplomado de Lean Progress: grid gerencial, liderazgo situacional, pentágono del
  poder, Lewin y Kotter. Antes de la primera sesión, **test de estilo** (10 preguntas → directivo/productor/complaciente/indiferente), guardado en
  `niveles.competencias_json["estilo"]` y usado por Patricia para diseñar escenas que reten a flexibilizar. **Los directores también entrenan**
  (`/entrenar/liderazgo`, "Mis prácticas"); sus reportes los ven RRHH y DG, no su equipo. 6 KPIs.

Relevancia (`catalogo.habilidades_que_usa` / `habilidades_nucleo`): comunicación para todo el mundo; presentaciones a quien expone (empresa, estudio,
busca empleo, lidera, genera negocio); imagen a quien representa a su empresa o negocio o busca empleo; liderazgo sólo a quien lidera; Ruta DM sólo a
empresa. La experiencia de empresa no cambia: ven todo el catálogo habilitado y Elena decide qué lleva plan.

## El Analista

- **Recalibración tras cada sesión**: aplica reglas de nivel (sube/baja, refuerzo a las 3 sin mejora), renivela los ítems pendientes, reescribe el objetivo de la siguiente sesión del plan con su lectura (que integra la recomendación del avatar y las metas del líder), reordena/inserta la prioridad del laboratorio, propone ascensos DM y genera el siguiente plan al terminar uno. **Metas del líder**: entran al diseño del roadmap y a cada lectura; al cumplirse (promedio de las últimas 2 sesiones ≥ mínimo, por habilidad y competencia) la meta individual se marca *alcanzada* y se notifica a quien la creó, al director y al colaborador; las metas de área/empresa se avisan por persona. Las metas en sí sólo las cambian RRHH o el director (el Analista puede proponer ajustes como propuesta). **Meta nueva sobre un plan ya diseñado** (`recalibrar_por_meta`, en segundo plano al crearla): los planes activos afectados (la persona, o toda el área/empresa, hasta 40) se recalibran al momento: si la meta fija una competencia DM, pasa a ser la siguiente sesión; el Analista reescribe con el modelo ligero el objetivo y el porqué de las sesiones pendientes hacia el score mínimo, la competencia y el plazo, sin tocar semana/nivel/competencia; sube la versión del plan y avisa al colaborador y a quien creó la meta.

- **Post-sesión** (modelo ligero, entrada compacta): lectura para el líder, riesgo y motivo, recomendación accionable, siguiente objetivo (se escribe en el siguiente ítem del roadmap), ajuste de plan, señales. Las decisiones de nivel las aplica el sistema y el Analista las explica.
- **Periódico**: resumen semanal por área y organización (avanzan / atención / 3 recomendaciones con responsable y señal de éxito); alertas de inactividad (7 días).
- **Chat con herramientas** (director: su área; RRHH/DG: toda la empresa): `listar_colaboradores`, `ficha_colaborador`, `kpis`, `sesiones_recientes`, `metas_vigentes`, `investigar` (Google Search con fuentes, tope mensual), `proponer` (registra propuestas para aprobación). Nunca reproduce transcripciones ni inventa cifras: si no tiene el dato, lo dice.
- **Investigación anti-alucinación**: sólo afirma lo que sustentan las fuentes devueltas por la búsqueda; prefiere dominios oficiales/académicos; si no hay fuentes, lo marca como orientación no verificada; las fuentes se muestran con su dominio en la interfaz y se guardan en *Análisis*.

## Chat con el coach (reporte)

El colaborador puede preguntar a Celeste/Elena/Juan sobre su reporte; el contexto es el JSON del reporte (no la transcripción), por lo que cuesta pocos tokens y no inventa momentos.

## Sócrates — tutor (master class personalizada)

- **Qué hace**: imparte la parte teórica de cada habilidad como una master class de nivel maestría, personalizada al rol, industria, producto, nivel, objetivo de la siguiente sesión, metas del líder y brechas recientes de la persona (si vende sombreros, los ejemplos venden sombreros; si no vende, los ejemplos son de su trabajo real).
- **Dónde**: "Prepárate con Sócrates" en Hoy, en cada ítem pendiente del plan y en el briefing; biblioteca por habilidad (ventas: 7 temas; entrevistas: 4; Ruta DM: competencias del nivel actual y el siguiente). Nav "Sócrates".
- **Cómo se genera** (`agents/socrates.py`): dos llamadas, una sola vez por persona y tema (se guarda en `lecciones`; releer no cuesta): (1) dossier con búsqueda de Google (`SOCRATES_INVESTIGAR`): hechos, marcos y referencias verificables (libros/autores de referencia, PMI, HBR, académicas); (2) lección estructurada con esquema (`SOCRATES_LECCION`) a partir del dossier + materiales internos (CAT-01, Ruta DM, taller DM2 cuando la competencia mapea). Fuentes sólo las del dossier/búsqueda; el validador sanea el diagrama Mermaid y las URLs.
- **Formato de la lección**: gancho, idea central, mapa conceptual (Mermaid flowchart, renderizado en el navegador con respaldo en texto), 3–5 marcos con origen/aplicación/ejemplo en su contexto, proceso paso a paso, comparativa débil vs experto, errores comunes, caso resuelto, 4–6 preguntas socráticas con pista y respuesta modelo (ocultas), checklist para la práctica, cierre y fuentes. Lectura 12–20 min o en 3 bloques de 5 (pestañas).
- **Chat**: `SOCRATES_CHAT` con la lección como contexto y el perfil; responde con rigor (cita autor/obra) y preguntas socráticas; sin búsqueda, historial corto.
- **Base compartida** (`lecciones_base`): la primera lección de un tema para un perfil (tema + nivel + rol vende/lidera/ejecuta + giro o producto) queda como base; para la siguiente persona con el mismo perfil Sócrates no investiga ni construye de nuevo: con el modelo ligero adapta gancho, ejemplos, frases, caso, preguntas, checklist y cierre a su situación, nivel, plan y metas (`SOCRATES_ADAPTAR`), conservando marcos, comparativa, errores y fuentes (si la adaptación los pierde, se restauran de la base). Costo ≈ 1/5 de una lección nueva.
- **Dónde participa**: en modalidad completa, el briefing de cada sesión muestra "Sócrates en 60 segundos" (idea central + checklist de la lección ya generada; 0 tokens); en "Prepárate 5 minutos" Sócrates vive sólo en su apartado.
- **Topes**: `SOCRATES_MAX_MES` lecciones nuevas por persona (12) y `GROUNDING_MAX_MES` (150) además del presupuesto duro. Costo típico: 1.5–3 MXN una lección nueva, ~0.4 MXN una adaptada.

## Experiencia, modalidades, correo y ayuda

- **Encuesta de primera experiencia** (`encuesta.py`): se invita una vez tras la primera práctica completada (Hoy y reporte); secciones: sobre ti, experiencia (calificación, realismo, utilidad, facilidad, aprendizaje, NPS, abiertas), valor y precio (¿pagarías?, pago único MXN, plan mensual y rango, quién paga, qué funciones harían pagar más, comparación) y cierre (entrevista). RRHH ve y exporta las respuestas de su empresa sin la sección de precio; el superadmin ve todo con resumen (NPS, promedios, distribuciones) y Excel.
- **Modalidades**: `completa` (sesión de 15–25 min) o `micro` "Prepárate 5 minutos" (tres bloques al día, avisos a `MICRO_HORAS` lun–vie sólo si falta el bloque de la franja, racha diaria tipo Duolingo basada en `actividad`: turnos, lecturas y bloques). La elige cada persona en Mi cuenta según sus tiempos (RRHH la ve, no la fija); contenido, sesiones y análisis son idénticos en ambas. Las sesiones ya eran reanudables; la pantalla muestra el temporizador del bloque.
- **Correo** (`correo.py`): cada aviso in-app se reenvía por SMTP (hilo aparte, nunca bloquea) si está configurado y la persona no lo desactivó; prueba desde Admin; fallos en bitácora (máx. uno cada 5 min).
- **Ayuda**: página por rol con instrucciones y FAQ + contacto de soporte (WhatsApp y correo, variables `SOPORTE_*`); acceso desde la barra superior y el menú.

## Encuesta de experiencia (`encuesta.py`)
Tras la primera práctica completada es **obligatoria**: `/entrenar/*`, `/laboratorio` e iniciar sesiones redirigen a `/encuesta?obligatoria=1`
hasta responderla (no bloquea Sócrates ni el reporte). Preguntas del documento "Preguntas Mente Viva" integradas: relación y veces de uso, utilidad
1–5, lo que más valora, frecuencia deseada, disposición de pago (5 opciones), monto mensual máximo (rangos MXN), modalidad de pago y cuándo pagaría,
además de las originales. RRHH ve resumen, lista y **detalle por persona** (`/encuestas/{id}`) sin la sección de precio; el superadmin todo
(`/admin/encuestas/{id}`); Excel en ambos.

## Público general y externos (sin tocar la experiencia de empresa)

- El onboarding abre con la situación de vida (empresa · negocio u oficio · estudio · hogar y familia · búsqueda de empleo) y amplía las funciones y los tipos de producto (oficio o servicio local, comida/artesanía/catálogo, clientes particulares). Para quien trabaja en una empresa **nada cambia**: mismas preguntas, mismos escenarios, mismos planes (todas las habilidades habilitadas, prioridades de Elena con propuestas a RRHH fuera del rol, Ruta DM si la empresa la tiene).
- Fuera de empresa (`catalogo.habilidades_relevantes`): el cuestionario omite el grupo Ruta DM; Elena prioriza sólo lo que a esa persona le sirve (un cerrajero → ventas/atención a clientes; un estudiante o quien busca empleo → entrevistas) y pone brecha baja al resto; se crean planes sólo para esas habilidades; la Ruta DM no aparece; el catálogo y Sócrates muestran lo relevante y dejan el resto plegado en "Otras habilidades" para práctica libre.
- Los avatares se adaptan por perfil: Elena entrevista con historias de taller, escuela, familia o comunidad (sin asumir jefes ni corporativo); Celeste se convierte en clienta particular (presupuesto familiar, dudas de vida real, compra pequeña) cuando el producto es un oficio, servicio local, comida o catálogo; Sócrates personaliza ejemplos con ese contexto.

## Metodología y estándares por empresa (`agents/estandares.py`)

- RRHH (menú **Estándares**) o el equipo Mente Viva (Admin → empresa → Metodología y estándares) capturan en lenguaje natural, por habilidad: metodología y etapas (p. ej. "vendemos con AIDA, no usamos PRAINCODERECI"), terminología y reglas propias, y qué NO exigir; además un estilo general (comunicación y presentaciones: "breves con una gráfica por idea" o "largas con datos duros"; valores y cultura).
- Si un campo está vacío se usa el estándar de Mente Viva: los prompts quedan **idénticos** a los actuales (Cóndor no cambia nada). Si hay texto, entra como bloque "ESTÁNDAR DE <EMPRESA>" prioritario en: Celeste (roleplay y feedback: sus etapas sustituyen a PRAINCODERECI/SPIN/T-01…T-08 donde difieran y los KPIs se mapean a ellas), Elena en práctica de entrevistas y su feedback, Juan (sólo el estilo general; la Ruta DM es la metodología de Cóndor y no se sustituye) y Sócrates (enseña la metodología de la empresa antes que la genérica).
- Las lecciones base compartidas de Sócrates llevan en su clave una huella del estándar: dos empresas con metodologías distintas nunca comparten base.
