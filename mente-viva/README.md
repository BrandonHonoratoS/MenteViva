# Mente Viva · v1.0.2

**El gimnasio de habilidades blandas con agentes de IA.** Plataforma web (FastAPI + Gemini) donde las personas practican situaciones reales con avatares conversacionales que mantienen la presión, reciben retroalimentación con evidencia y siguen un roadmap que la IA recalcula después de cada sesión. Cinco perfiles ven lo que les importa: Colaborador, Director de área, Recursos Humanos, Dirección General y el equipo Mente Viva (superadministrador).

> *Crece desde adentro, impacta hacia afuera.*

## Los agentes

| Agente | Qué hace | Cómo razona |
|---|---|---|
| **Elena Ríos** · entrevistadora por competencias | Onboarding + entrevista de diagnóstico (BEI + STAR) en una sola experiencia: cuestionario de un toque (0 tokens) y luego conversación de ~25 min. Al cerrar entrega perfil de 10 competencias, fortalezas, oportunidades, blind spot, nivel de ventas, nivel en la Ruta DM y **un roadmap por cada habilidad con brecha**. También dirige la práctica de entrevista de trabajo (CAT-03). | Fases rapport → encuadre → desarrollo → profundización → cierre con repreguntas de 3 niveles; salida JSON con esquema. |
| **Celeste López** · Clínica de Ventas (CAT-01 v3.0) | Clienta analítica y escéptica calibrada con las 10 variables de onboarding del vendedor; 3 niveles (2, 3 y 5 objeciones en orden; NO al primer cierre en Avanzado). Evalúa KPI-1…KPI-6 con pesos por nivel, evidencia objetiva (técnicas T-01…T-08, SPIN por tipo, etapas PRAINCODERECI, turno del primer descuento, tipo de cierre). | Roleplay estricto (máx. 3 oraciones, nunca rompe personaje) y feedback en modo coach al terminar. |
| **Juan Artiaga** · Ruta Delivery Manager (escenario personalizado de Ingeniería Cóndor) | Diagnostica el nivel DM (Básico → DM1…DM5 → Emprendedor), **diseña la sesión** (roleplay, caso de decisión o reto práctico según la competencia del siguiente nivel) y entrega la retroalimentación profunda de 9 secciones con sub-dimensiones /10 y nivel de dominio. | Diseño de escenario + roleplay + rúbrica; propone ascensos con evidencia. |
| **El Analista** | Después de cada sesión aplica las reglas de nivel, actualiza el roadmap (siguiente objetivo, refuerzos, reniveles), escribe una lectura para el líder (riesgo, recomendación, señales), propone ascensos DM y activaciones de roadmap **para aprobación humana de RRHH**, alerta inactividad, redacta resúmenes semanales y conversa con managers **sólo con datos de sus herramientas**; investiga con Google Search citando fuentes. | Reglas deterministas + narrativa con IA + bucle de herramientas. |

**Reglas de nivel (documento funcional):** > 75 en dos sesiones seguidas sube; < 50 baja; 3 sesiones sin mejora insertan una sesión de refuerzo y avisan al director. **Ascenso DM:** todas las competencias del siguiente nivel entrenadas, promedio ≥ 7/10, ninguna < 5, al menos dos en 9–10 → propuesta que RRHH aprueba.

## Perfiles y tableros

- **Colaborador**: Hoy (siguiente sesión, evolución, racha), diagnóstico, planes, catálogo (3 habilidades activas + “próximamente”), sesión con avatar (fases, presión, cronómetro), reporte con KPIs/evidencia/plan de acción y chat con el coach, historial, autoevaluación.
- **Director de área**: su equipo (índices, evolución, atención, colaboradores), ficha por persona, evaluación mensual del líder, metas, chat con el Analista, análisis.
- **RRHH**: organización completa, áreas y personas (alta con contraseña temporal), aprobaciones, metas, evaluaciones, análisis, Analista, exportes Excel/PDF; único rol (además del propio colaborador) que puede leer transcripciones.
- **Dirección General**: tablero organizacional con IIHO, IDSS, madurez, participación, engagement, aplicación, transferencia, evolución; nombres en top/atención; lecturas del Analista.
- **Mente Viva (superadmin)**: empresas y habilidades personalizadas, usuarios RRHH, modelo de IA, presupuesto (tope duro en MXN), uso por origen, bitácora.

Las fórmulas de todos los índices están en `docs/METRICAS.md` y en el tooltip “¿Cómo se calcula?” de cada indicador.

## Eficiencia de tokens y costo

- Gemini **3.8 Flash** para avatares/feedback/analista y **3.5 Flash-Lite** para resúmenes y lecturas breves (configurable).
- Instrucciones estables primero (caché implícita), perfil y escenario al final; cada turno viaja con memoria comprimida + últimos 14 mensajes; el análisis final recibe la transcripción una sola vez; salidas JSON con esquema (sin re-parseo); `thinking_level=low` en roleplay.
- Tope duro mensual (500 MXN por defecto) verificado **antes** de cada llamada; aviso al 80 %; contador de tokens/costo por origen; búsquedas de Google acotadas por mes.
- Estimación: una sesión de 20 turnos ≈ 1–2 MXN; 10 personas × 3 sesiones/semana ≈ 150–250 MXN/mes.

## Seguridad y privacidad (resumen; detalle en `docs/SEGURIDAD.md`)

Sesiones por cookie HttpOnly/SameSite, contraseñas con scrypt, límite de intentos por usuario e IP, CSRF de doble barrera (Sec-Fetch-Site + token), cabeceras CSP/HSTS/nosniff, roles y alcance por área, transcripciones sólo para el colaborador y RRHH, la API key sólo en variables de entorno, bitácora de eventos. La IA no emite veredictos de empleabilidad ni etiquetas de personalidad.

## Estructura

```
app/
  config.py        variables de entorno · db.py  SQLite/WAL, esquema y helpers · security.py  roles, CSRF, alcance
  llm/gemini.py    cliente Gemini (JSON schema, function calling, grounding), presupuesto, simulador para pruebas
  agents/          catalogo (habilidades, KPIs, Ruta DM, onboarding) · prompts · esquemas · avatares · motor (sesiones) · roadmap · analista
  metrics.py       índices IDSS, práctica, participación, engagement, aplicación, transferencia, evolución, madurez, IIHO
  reports/         PDF (reportlab) y Excel (openpyxl) · scheduler.py  alertas e informes semanales
  routes/          auth · colaborador · api · gestion (RRHH) · tableros (DG/director) · admin · exportes
  web/             plantillas Jinja2 + estilos claros/futuristas + app.js (chat, wizard, gráficas Chart.js)
tests/             flujo completo con LLM simulado + resiliencia ante fallos de la IA (13 pruebas)
scripts/demo_local.py  datos de demostración locales (sin API key) · scripts/probar_agentes.py  prueba real de los 4 agentes
docs/              DESPLIEGUE · ARQUITECTURA · AGENTES · METRICAS · SEGURIDAD
```

## Correr en local

```bash
pip install -r requirements.txt
cp .env.example .env            # captura GEMINI_API_KEY (o deja LLM_PROVEEDOR=stub para simular)
set -a; source .env; set +a
uvicorn app.main:app --reload
# demo con datos simulados (sin key): DATA_DIR=./data_demo LLM_PROVEEDOR=stub ANALISIS_SINCRONO=1 python scripts/demo_local.py
pytest -q                                   # 14 pruebas con IA simulada
python scripts/probar_agentes.py            # con GEMINI_API_KEY: recorre los 4 agentes con IA real y reporta cada paso
```

Despliegue paso a paso en Render + AI Studio: `docs/DESPLIEGUE.md`.
