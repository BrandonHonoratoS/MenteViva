# Arquitectura

```
Navegador ──HTTPS──▶ Render Web Service (FastAPI, 1 worker, uvicorn)
                        ├── app/routes    páginas Jinja2 + API JSON (chat de sesiones, onboarding, analista, coach)
                        ├── app/agents    Elena · Celeste · Juan · Analista · motor de sesiones · roadmaps
                        ├── app/llm       cliente Gemini (JSON schema, function calling, grounding) + presupuesto + simulador
                        ├── app/metrics   índices y tableros
                        ├── app/reports   PDF / Excel
                        ├── app/scheduler hilo: alertas de inactividad (diario) · resúmenes del Analista (lunes)
                        └── /data/mente_viva.db  SQLite (WAL) en disco persistente
                                              ▲
                        Gemini API (Google AI Studio) ◀── llamadas estructuradas con tope de presupuesto
```

## Flujo de una sesión

1. **Briefing** (`/entrenar/{habilidad}`): objetivo del roadmap o práctica voluntaria.
2. **Apertura** (`motor.iniciar`): crea la sesión; Juan primero *diseña* el escenario (formato, personaje, situación, sub-dimensiones) con una llamada; Celeste/Elena abren con su primer turno.
3. **Turnos** (`POST /api/sesiones/{id}/mensaje`): bloqueo por sesión; contenido = instrucciones estables + memoria comprimida + últimos 14 mensajes; salida JSON `{mensaje, tension, estado/fase}`; tope de turnos por nivel con cierre natural inducido.
4. **Cierre** (`motor.terminar`): estado `analizando`; hilo en segundo plano; la UI hace *polling* a `/estado`.
5. **Análisis** (`motor.analizar`): transcripción completa → rúbrica del avatar (JSON) → score ponderado → `analista.post_sesion` (reglas de nivel, roadmap, propuestas, narrativa para el líder, notificaciones).
6. **Reporte** (`/sesion/{id}/reporte`): KPIs, evidencia, momentos clave, plan, tips, siguiente paso, chat con el coach, PDF.

## Diagnóstico

Cuestionario de un toque (17 variables; 0 tokens) → entrevista con Elena → `roadmap.analizar_diagnostico`: perfil de competencias, niveles iniciales por habilidad y un roadmap por habilidad con brecha (andamiaje determinista + objetivos escritos por la IA). Los roadmaps de habilidades fuera del rol declarado quedan `propuesto` hasta que RRHH los aprueba.

## Modelo de datos (SQLite)

`empresas` · `areas` · `usuarios` · `sesiones_auth` · `perfiles` (onboarding + diagnóstico) · `niveles` (por habilidad; dominio por competencia DM) · `roadmaps` / `roadmap_items` · `sesiones` / `mensajes` · `evaluaciones` (líder/auto) · `metas` · `propuestas` (ascenso, roadmap, refuerzo, alerta, ajuste) · `analisis` · `notificaciones` · `chats` / `chat_mensajes` · `uso_llm` · `ajustes` · `bitacora`.

## Decisiones

- **SQLite en disco persistente** en lugar de Postgres: cero costo adicional, un solo proceso, suficiente para decenas de usuarios; migración trivial más adelante.
- **Reglas de negocio en código, juicio en la IA**: niveles, refuerzos, andamiaje de roadmaps y cálculo de scores son deterministas y auditables; la IA aporta escenarios, diálogo, evidencia, objetivos y lecturas.
- **Aprobación humana** para cualquier cambio de nivel DM o activación de planes fuera del rol.
- **Preparado para voz y video**: el motor recibe texto por turno; un transcriptor (Whisper/Gemini Live) y un avatar (HeyGen/D-ID) se conectan al mismo endpoint sin tocar los agentes.
