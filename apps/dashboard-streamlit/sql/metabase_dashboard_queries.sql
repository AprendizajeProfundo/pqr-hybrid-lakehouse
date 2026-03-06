-- ============================================================================
-- METABASE: Dashboard Ejecutivo-Operativo PQRS
-- ============================================================================
-- Recomendación:
-- 1) Crear una "Pregunta SQL" por cada bloque.
-- 2) Asignar filtros de dashboard:
--    - date_from (Date)
--    - date_to (Date)
--    - pqrs_type (Category, multiple)
--    - channel (Category, multiple)
--    - department_name (Category, multiple)
-- 3) Vincular filtros a las variables del SQL.

-- ----------------------------------------------------------------------------
-- Q1. KPI: Volumen total nacional
-- ----------------------------------------------------------------------------
SELECT
  COALESCE(SUM(tickets_count), 0) AS total_tickets
FROM analytics.v_timeseries_national_daily
WHERE day BETWEEN {{date_from}} AND {{date_to}}
[[AND pqrs_type IN ({{pqrs_type}})]]
[[AND channel IN ({{channel}})]];

-- ----------------------------------------------------------------------------
-- Q2. KPI: Variación promedio diaria (%)
-- ----------------------------------------------------------------------------
SELECT
  ROUND(AVG(pct_vs_prev_day)::numeric, 2) AS avg_pct_vs_prev_day
FROM analytics.v_timeseries_national_daily
WHERE day BETWEEN {{date_from}} AND {{date_to}}
[[AND pqrs_type IN ({{pqrs_type}})]]
[[AND channel IN ({{channel}})]];

-- ----------------------------------------------------------------------------
-- Q3. KPI: SLA promedio (%)
-- ----------------------------------------------------------------------------
SELECT
  ROUND(AVG(within_sla_pct)::numeric, 2) AS within_sla_pct_avg
FROM analytics.v_geo_daily
WHERE day BETWEEN {{date_from}} AND {{date_to}}
[[AND pqrs_type IN ({{pqrs_type}})]]
[[AND channel IN ({{channel}})]]
[[AND department_name IN ({{department_name}})]];

-- ----------------------------------------------------------------------------
-- Q4. KPI: Backlog total
-- ----------------------------------------------------------------------------
SELECT
  COALESCE(SUM(backlog_count), 0) AS backlog_total
FROM analytics.v_geo_daily
WHERE day BETWEEN {{date_from}} AND {{date_to}}
[[AND pqrs_type IN ({{pqrs_type}})]]
[[AND channel IN ({{channel}})]]
[[AND department_name IN ({{department_name}})]];

-- ----------------------------------------------------------------------------
-- Q5. Serie temporal nacional por tipo
-- Chart: Line
-- X: day, Series: pqrs_type, Y: tickets_count
-- ----------------------------------------------------------------------------
SELECT
  day,
  pqrs_type,
  SUM(tickets_count) AS tickets_count
FROM analytics.v_timeseries_national_daily
WHERE day BETWEEN {{date_from}} AND {{date_to}}
[[AND pqrs_type IN ({{pqrs_type}})]]
[[AND channel IN ({{channel}})]]
GROUP BY day, pqrs_type
ORDER BY day ASC, pqrs_type ASC;

-- ----------------------------------------------------------------------------
-- Q6. Serie comparativa por departamento
-- Chart: Line
-- X: day, Series: department_name, Y: tickets_count
-- ----------------------------------------------------------------------------
SELECT
  day,
  department_name,
  SUM(tickets_count) AS tickets_count
FROM analytics.v_timeseries_department_daily
WHERE day BETWEEN {{date_from}} AND {{date_to}}
[[AND department_name IN ({{department_name}})]]
[[AND pqrs_type IN ({{pqrs_type}})]]
[[AND channel IN ({{channel}})]]
GROUP BY day, department_name
ORDER BY day ASC, department_name ASC;

-- ----------------------------------------------------------------------------
-- Q7. Ranking departamentos por volumen
-- Chart: Bar
-- ----------------------------------------------------------------------------
SELECT
  department_name,
  SUM(tickets_count) AS tickets_count
FROM analytics.v_timeseries_department_daily
WHERE day BETWEEN {{date_from}} AND {{date_to}}
[[AND department_name IN ({{department_name}})]]
[[AND pqrs_type IN ({{pqrs_type}})]]
[[AND channel IN ({{channel}})]]
GROUP BY department_name
ORDER BY tickets_count DESC
LIMIT 20;

-- ----------------------------------------------------------------------------
-- Q8. Ranking departamentos por backlog
-- Chart: Bar
-- ----------------------------------------------------------------------------
SELECT
  department_name,
  SUM(backlog_count) AS backlog_count
FROM analytics.v_geo_daily
WHERE day BETWEEN {{date_from}} AND {{date_to}}
[[AND department_name IN ({{department_name}})]]
[[AND pqrs_type IN ({{pqrs_type}})]]
[[AND channel IN ({{channel}})]]
GROUP BY department_name
ORDER BY backlog_count DESC
LIMIT 20;

-- ----------------------------------------------------------------------------
-- Q9. SLA por departamento
-- Chart: Bar (descending)
-- ----------------------------------------------------------------------------
SELECT
  department_name,
  ROUND(AVG(within_sla_pct)::numeric, 2) AS within_sla_pct
FROM analytics.v_geo_daily
WHERE day BETWEEN {{date_from}} AND {{date_to}}
[[AND department_name IN ({{department_name}})]]
[[AND pqrs_type IN ({{pqrs_type}})]]
[[AND channel IN ({{channel}})]]
GROUP BY department_name
ORDER BY within_sla_pct ASC
LIMIT 20;

-- ----------------------------------------------------------------------------
-- Q10. Dataset para mapa departamental (lat/lon + métricas)
-- Chart: Map (pin map)
-- ----------------------------------------------------------------------------
WITH geo_base AS (
  SELECT
    department_name,
    AVG(latitude)::float AS lat,
    AVG(longitude)::float AS lon
  FROM silver.dim_geo
  WHERE latitude IS NOT NULL AND longitude IS NOT NULL
  GROUP BY department_name
),
geo_kpi AS (
  SELECT
    v.department_name,
    SUM(v.tickets_count) AS tickets_count,
    SUM(COALESCE(v.backlog_count, 0)) AS backlog_count,
    ROUND(AVG(COALESCE(v.within_sla_pct, 0))::numeric, 2) AS within_sla_pct,
    SUM(COALESCE(v.overdue_count, 0)) AS overdue_count
  FROM analytics.v_geo_daily v
  WHERE v.day BETWEEN {{date_from}} AND {{date_to}}
  [[AND v.department_name IN ({{department_name}})]]
  [[AND v.pqrs_type IN ({{pqrs_type}})]]
  [[AND v.channel IN ({{channel}})]]
  GROUP BY v.department_name
)
SELECT
  k.department_name,
  b.lat,
  b.lon,
  k.tickets_count,
  k.backlog_count,
  k.within_sla_pct,
  k.overdue_count
FROM geo_kpi k
JOIN geo_base b
  ON k.department_name = b.department_name
ORDER BY k.tickets_count DESC;

-- ----------------------------------------------------------------------------
-- Q11. Composición por tipo PQRS
-- Chart: Pie / Donut
-- ----------------------------------------------------------------------------
SELECT
  pqrs_type,
  SUM(tickets_count) AS tickets_count
FROM analytics.v_timeseries_national_daily
WHERE day BETWEEN {{date_from}} AND {{date_to}}
[[AND pqrs_type IN ({{pqrs_type}})]]
[[AND channel IN ({{channel}})]]
GROUP BY pqrs_type
ORDER BY pqrs_type;

-- ----------------------------------------------------------------------------
-- Q12. Tabla detalle ejecutiva
-- ----------------------------------------------------------------------------
SELECT
  day,
  department_name,
  pqrs_type,
  channel,
  SUM(tickets_count) AS tickets_count,
  SUM(COALESCE(backlog_count, 0)) AS backlog_count,
  ROUND(AVG(COALESCE(within_sla_pct, 0))::numeric, 2) AS within_sla_pct
FROM analytics.v_geo_daily
WHERE day BETWEEN {{date_from}} AND {{date_to}}
[[AND department_name IN ({{department_name}})]]
[[AND pqrs_type IN ({{pqrs_type}})]]
[[AND channel IN ({{channel}})]]
GROUP BY day, department_name, pqrs_type, channel
ORDER BY day DESC, department_name ASC;
