# Plan Detallado de Analítica PQRS (KPIs + Mapas Colombia)

## 1. Objetivo
Diseñar e implementar una capa analítica integral para PQRS que permita:
1. Monitoreo operativo diario.
2. Seguimiento de cumplimiento SLA por tipo PQRS.
3. Análisis geográfico (región, departamento, municipio) con mapas de Colombia.
4. Detección de patrones, picos coyunturales y señales tempranas de riesgo.

## 2. Estado actual y brecha
Estado actual (ya disponible):
1. Pipeline ETL por etapas (`raw -> bronze -> silver -> gold`) y orquestación Prefect.
2. Gold con KPIs diarios base:
   - `gold.kpi_volume_daily`
   - `gold.kpi_backlog_daily`
   - `gold.kpi_sla_daily`
3. Dimensión geográfica cargada en `silver.dim_geo`.

Brecha identificada:
1. `silver.tickets` aún no persiste de forma robusta la granularidad geográfica completa para BI (`dane_city_code`, `department_name`, `city_name`).
2. Gold no tiene agregados por departamento/municipio.
3. No existe capa de datasets semánticos para mapas y tablero ejecutivo.

## 3. Preguntas de negocio a resolver
1. ¿Cómo evoluciona diariamente el volumen de PQRS por tipo/canal/geografía?
2. ¿Dónde se concentra el backlog y en qué zonas empeora?
3. ¿Qué departamentos/municipios presentan mayor riesgo de incumplimiento SLA?
4. ¿Qué tipos PQRS explican los picos coyunturales?
5. ¿Qué canales tienen más recurrencia de reclamos y sobre qué temas?

## 4. Modelo analítico objetivo
## 4.1 Granularidad recomendada
1. Ticket-level en Silver.
2. Daily aggregates en Gold.
3. Geografía con jerarquía: `region -> department -> city (dane_city_code)`.

## 4.2 Ajustes de datos (prioridad alta)
1. Persistir en `silver.tickets`:
   - `dane_city_code`
   - `city_name`
   - `department_name`
   - `region_name` (o mantener `region` estandarizada)
2. Completar `join` contra `silver.dim_geo` por `dane_city_code`.
3. Estandarizar catálogos de canal, tipo, estado y prioridad.

## 5. Catálogo de KPIs (mínimo viable + expansión)
## 5.1 Operación diaria (MVP)
1. Volumen diario de tickets (`count tickets`).
2. Volumen diario por tipo PQRS.
3. Volumen diario por canal.
4. Backlog diario total y por tipo.
5. `% cumplimiento SLA diario` por tipo.
6. Tickets vencidos y días promedio de atraso.

## 5.2 Geográficos (MVP de mapas)
1. Volumen diario por departamento.
2. Volumen diario por municipio (top N + mapa).
3. Backlog por departamento.
4. `% SLA cumplido` por departamento.
5. Densidad per cápita (fase 2, si se integra población DANE).

## 5.2.1 Series de tiempo (requisito explícito)
1. Serie diaria nacional por tipo PQRS.
2. Serie diaria departamental por tipo PQRS.
3. Comparativo multi-serie por tipo (`P`, `Q`, `R`, `S`) en el mismo gráfico.
4. Comparativo entre departamentos seleccionados (hasta 5 líneas).
5. Variación porcentual vs:
   - día anterior,
   - promedio móvil 7 días,
   - mismo día semana anterior.
6. Acumulado MTD y YTD por tipo y territorio.

## 5.2.2 Filtros obligatorios del tablero temporal
1. Nivel geográfico: `Nacional` o `Departamento` (por ahora).
2. Selector de departamento (single/multi) cuando el nivel sea departamental.
3. Rango de fechas (`date_from`, `date_to`).
4. Tipo PQRS (multi-select).
5. Canal (opcional en primera versión, recomendado activo).

## 5.3 Calidad de servicio y productividad (fase 2)
1. Tiempo medio de primera respuesta.
2. Tiempo medio de resolución.
3. Reaperturas por tipo/territorio.
4. Distribución por prioridad y envejecimiento de backlog.
5. Conversión entre estados (funnel operativo).

## 5.4 Temático/NLP (fase 3)
1. Tópicos dominantes por zona geográfica.
2. Tendencia de temas emergentes (semana a semana).
3. Correlación tema vs incumplimiento SLA.

## 6. Productos analíticos (dashboards)
## 6.1 Tablero Ejecutivo
1. KPIs globales del día/semana/mes.
2. Semáforos SLA.
3. Top 10 departamentos por backlog.
4. Alertas de pico vs baseline histórico.
5. Serie de tiempo nacional diaria con comparativo por tipo PQRS.

## 6.2 Tablero Operativo
1. Cola de backlog por estado y prioridad.
2. Tendencia de ingresos/cierres diarios.
3. Aging buckets (`0-3`, `4-7`, `8-15`, `>15 días`).
4. Drill-down geográfico y por tipo PQRS.
5. Panel comparativo nacional vs departamento seleccionado.

## 6.3 Tablero Geoespacial
1. Mapa coroplético por departamento:
   - volumen,
   - backlog,
   - `% SLA`.
2. Mapa municipal (puntos o coroplético según granularidad).
3. Series temporales sincronizadas con mapa.
4. Filtros: fecha, tipo, canal, prioridad.

## 6.4 Tablero de Series de Tiempo (nuevo)
1. Visual principal: línea diaria de volumen.
2. Modos de análisis:
   - `Nacional por tipo`
   - `Departamento por tipo`
   - `Comparar departamentos`
3. Métricas secundarias superpuestas:
   - promedio móvil 7 días,
   - banda de variación histórica (p25-p75),
   - marcadores de picos (`z-score` simple, fase 1.5).
4. Interacción:
   - click en punto de tiempo para filtrar mapa y tabla detalle.
   - brush de ventana temporal para zoom.

## 7. Diseño de mapas Colombia
## 7.1 Capas
1. Capa 1: Departamentos (coroplético principal).
2. Capa 2: Municipios (detalle bajo demanda).
3. Capa 3: Marcadores de eventos extremos (picos).

## 7.2 Métricas cartográficas
1. `tickets_count` (absoluto).
2. `backlog_count`.
3. `within_sla_pct`.
4. `overdue_count`.
5. `tickets_per_100k` (fase 2, con población).

## 7.3 Reglas visuales
1. Escala secuencial para volumen/backlog.
2. Escala divergente para `% SLA` vs meta objetivo.
3. Tooltips con: departamento/municipio, valor actual, variación vs periodo previo.
4. Evitar interpretación errónea con valores absolutos sin contexto poblacional.

## 8. Cambios técnicos propuestos en ETL
## 8.1 Silver (obligatorio)
1. En `bronze_to_silver.py`, mapear y persistir `dane_city_code`.
2. Enriquecer `department_name` y `region_name` por `dim_geo`.
3. Normalizar faltantes (`unknown`) con reglas explícitas.

## 8.2 Gold (obligatorio)
Crear nuevas tablas:
1. `gold.kpi_volume_geo_daily(day, region_name, department_name, dane_city_code, pqrs_type, channel, tickets_count, run_id)`
2. `gold.kpi_backlog_geo_daily(day, region_name, department_name, dane_city_code, pqrs_type, backlog_count, run_id)`
3. `gold.kpi_sla_geo_daily(day, region_name, department_name, dane_city_code, pqrs_type, within_sla_pct, overdue_count, run_id)`
4. `gold.kpi_volume_dept_daily(day, department_name, pqrs_type, channel, tickets_count, tickets_mavg_7d, pct_vs_prev_day, pct_vs_prev_week, run_id)`
5. `gold.kpi_volume_national_daily(day, pqrs_type, channel, tickets_count, tickets_mavg_7d, pct_vs_prev_day, pct_vs_prev_week, run_id)`

## 8.3 Exposición semántica (recomendado)
1. Vistas SQL para BI:
   - `analytics.v_ticket_daily`
   - `analytics.v_geo_daily`
   - `analytics.v_sla_daily`
   - `analytics.v_timeseries_national_daily`
   - `analytics.v_timeseries_department_daily`
   - `analytics.v_timeseries_compare_types`
2. Convenciones de nombres consistentes para Metabase/Supabase.

## 8.4 Reglas de cálculo de series (estándar)
1. `tickets_count`: conteo diario de tickets creados.
2. `tickets_mavg_7d`: promedio móvil simple de 7 días calendario.
3. `pct_vs_prev_day`: `(hoy - ayer) / ayer * 100`.
4. `pct_vs_prev_week`: `(hoy - mismo_dia_semana_pasada) / mismo_dia_semana_pasada * 100`.
5. Completar fechas faltantes con `0` para continuidad de series.
6. Todas las series con zona horaria unificada (`America/Bogota` o UTC definido en contrato).

## 9. Orquestación y operación
## 9.1 Prefect
1. Mantener flow único E2E para producción local.
2. Añadir sub-flows analíticos:
   - `flow_build_gold_geo`
   - `flow_refresh_analytics_views`
3. Parámetros por corrida:
   - `run_id`
   - `date_from`
   - `date_to`
   - `load_db`

## 9.2 Frecuencia sugerida
1. Carga principal: diaria.
2. Reproceso histórico: bajo demanda.
3. Validaciones automáticas: cada corrida.

## 10. Data quality y control
Checks mínimos por corrida:
1. Integridad de `ticket_id` y `event_id`.
2. Cobertura geográfica (`% tickets con dane_city_code válido`).
3. Coherencia SLA (`closed_at >= created_at`, `sla_due_at` no nulo por tipo).
4. Duplicados de evento.
5. Volumen diario fuera de umbral esperado (alerta).

## 11. Roadmap por fases
## Fase 1 (rápida, 1-2 semanas)
1. Completar geografía en Silver.
2. Generar KPIs geo en Gold.
3. Generar KPIs de series nacional/departamental.
4. Dashboard ejecutivo + mapa departamental + tablero temporal base.

## Fase 2 (2-4 semanas)
1. Mapa municipal y análisis comparativo temporal.
2. Métricas de productividad operativa.
3. Vistas semánticas y diccionario de datos para estudiantes.

## Fase 3 (4+ semanas)
1. Analítica temática/NLP.
2. Detección de anomalías y alertas automáticas.
3. Benchmark regional y priorización inteligente.

## 12. Qué haremos y qué no haremos (alcance controlado)
Haremos:
1. Métricas accionables con trazabilidad ETL.
2. Dashboards filtrables por fecha/tipo/canal/geografía.
3. Mapas de Colombia útiles para gestión pública/operativa.

No haremos aún:
1. Predicción avanzada en tiempo real.
2. Streaming continuo tipo CDC en esta fase.
3. Modelos ML online en producción.

## 13. Entregables concretos
1. Scripts ETL ajustados (Silver + Gold geo).
2. DDL SQL de tablas y vistas analíticas.
3. Flujo Prefect actualizado.
4. Dashboard ejecutivo.
5. Dashboard geoespacial.
6. Guía de uso para operación y estudiantes.

## 14. Criterios de éxito
1. Dashboard responde en <5 segundos para filtros comunes.
2. 95%+ de tickets con georreferencia válida.
3. KPIs de Gold consistentes con tablas Silver (pruebas de reconciliación).
4. Proceso ETL reproducible por `run_id`.
5. Trazabilidad completa en `meta.etl_runs`.
