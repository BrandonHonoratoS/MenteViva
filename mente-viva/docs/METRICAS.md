# Métricas de Mente Viva

Todas se calculan en `app/metrics.py` y cada índice devuelve valor, fórmula y componentes (tooltip “¿Cómo se calcula?”). Periodo por defecto: últimos 30 días. Scores de sesión 0–100 (la Ruta DM convierte /10 → /100). Evaluaciones 1–5.

## Por sesión
- **Score global**: promedio ponderado de los KPIs con los pesos del nivel (ventas/entrevistas) o promedio de sub-dimensiones y global /10 × 10 (Ruta DM). En ventas, un cierre “fallido por ceder” acota el score a 59.
- **Semáforo**: verde > 75 · amarillo 50–75 · rojo < 50.

## Por colaborador
- **Score reciente**: promedio de las últimas 3 sesiones de práctica. **Tendencia**: diferencia contra las 3 anteriores.
- **Racha**: semanas consecutivas con al menos una sesión.
- **Nivel por habilidad** y, en la Ruta DM, **dominio por competencia** (score, dominio, sesiones, mejor).
- **Plan**: sesiones completadas / total de los roadmaps activos.

## Organización / área (marco KPI: Desarrollo · Práctica · Aplicación · Cultura)

| Índice | Fórmula |
|---|---|
| **IDSS** Desarrollo de Soft Skills | (score posterior − score inicial) / score inicial × 100; inicial = diagnóstico de Elena (promedio de competencias /5 → /100), posterior = promedio de las últimas 3 sesiones; promedio entre colaboradores con ambos datos |
| **Nivel de habilidad** | promedio del score reciente de los colaboradores |
| **Índice de Práctica** | sesiones del roadmap completadas / sesiones planeadas a la fecha × 100 |
| **Participación** | colaboradores con ≥ 1 sesión en el periodo / colaboradores activos × 100 |
| **Engagement** | colaboradores con sesiones en ≥ 2 semanas distintas del periodo / activos × 100 |
| **Autodesarrollo** | sesiones voluntarias (fuera del roadmap) / sesiones del periodo × 100 |
| **Aplicación en el entorno laboral** | colaboradores cuya última evaluación del líder marca “aplica” ≥ 4 / evaluados × 100 |
| **Transferencia del aprendizaje** | habilidades aplicadas / habilidades aprendidas × 100 (aprendida: promedio de últimas 3 sesiones ≥ 75; aplicada: además el líder marca “aplica” ≥ 4) |
| **Evolución conductual** | (última evaluación del líder − primera) / primera × 100, promedio entre colaboradores con ≥ 2 evaluaciones |
| **Madurez organizacional (1–5)** | puntaje ponderado: Participación 25 %, Engagement 25 %, Práctica 20 %, Aplicación 15 %, Nivel de habilidad 15 % → 1 Inicial (< 20) · 2 En desarrollo (< 40) · 3 Funcional (< 60) · 4 Integrado (< 80) · 5 Cultura consolidada (≥ 80) |
| **IIHO** Inteligencia Humana Organizacional | promedio de las dimensiones disponibles: Desarrollo = nivel de habilidad; Práctica = media(Participación, Engagement, Práctica); Aplicación = media(Aplicación, Transferencia); Cultura = madurez × 20 |
| Interacción colaborativa | próximamente (requiere sesiones grupales) |

También: distribución de niveles DM, serie semanal de sesiones y score (8 semanas), radar de KPIs promedio por habilidad, tabla por área, top 3 y “requieren atención” (≥ 7 días sin practicar, semáforo rojo o tendencia ≤ −10).

## Evaluación del líder (mensual, 5 preguntas 1–5)
aplica · comunicación · escucha · presión · resultados. La respuesta “aplica” alimenta Aplicación y Transferencia; el promedio alimenta Evolución conductual.

## Autoevaluación (mensual, 4 preguntas 1–5)
aplica · confianza · hábito · utilidad. Se muestra en la ficha y en Evaluaciones (RRHH).
