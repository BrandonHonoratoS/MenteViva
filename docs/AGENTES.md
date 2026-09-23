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

## El Analista

- **Post-sesión** (modelo ligero, entrada compacta): lectura para el líder, riesgo y motivo, recomendación accionable, siguiente objetivo (se escribe en el siguiente ítem del roadmap), ajuste de plan, señales. Las decisiones de nivel las aplica el sistema y el Analista las explica.
- **Periódico**: resumen semanal por área y organización (avanzan / atención / 3 recomendaciones con responsable y señal de éxito); alertas de inactividad (7 días).
- **Chat con herramientas** (director: su área; RRHH/DG: toda la empresa): `listar_colaboradores`, `ficha_colaborador`, `kpis`, `sesiones_recientes`, `metas_vigentes`, `investigar` (Google Search con fuentes, tope mensual), `proponer` (registra propuestas para aprobación). Nunca reproduce transcripciones ni inventa cifras: si no tiene el dato, lo dice.
- **Investigación anti-alucinación**: sólo afirma lo que sustentan las fuentes devueltas por la búsqueda; prefiere dominios oficiales/académicos; si no hay fuentes, lo marca como orientación no verificada; las fuentes se muestran con su dominio en la interfaz y se guardan en *Análisis*.

## Chat con el coach (reporte)

El colaborador puede preguntar a Celeste/Elena/Juan sobre su reporte; el contexto es el JSON del reporte (no la transcripción), por lo que cuesta pocos tokens y no inventa momentos.
