# Guía Dashboard y App Analítica PQRS

## 1) Alcance
Esta guía cubre:
1. Consultas SQL para dashboard en Metabase.
2. App Streamlit analítica conectada a Postgres.
3. Validaciones rápidas para confirmar que todo está listo.

## 2) Precondiciones
1. ETL ejecutado con una corrida reciente (`RUN_ID` nuevo).
2. Tablas/vistas pobladas en Postgres:
- `gold.kpi_volume_national_daily`
- `gold.kpi_volume_dept_daily`
- `analytics.v_timeseries_national_daily`
- `analytics.v_timeseries_department_daily`
- `analytics.v_geo_daily`

Validar:

```bash
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT COUNT(*) FROM analytics.v_timeseries_national_daily;"
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT COUNT(*) FROM analytics.v_timeseries_department_daily;"
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT COUNT(*) FROM analytics.v_geo_daily;"
```

## 3) Dashboard SQL para Metabase
Archivo listo:
- `apps/dashboard-streamlit/sql/metabase_dashboard_queries.sql`

Incluye consultas para:
1. KPI de volumen total.
2. KPI de promedio móvil 7 días.
3. Serie nacional diaria por tipo PQRS.
4. Serie departamental diaria.
5. Top departamentos.
6. Dataset de mapa (lat/lon + volumen + backlog + SLA).
7. Variaciones diarias y semanales.

Uso recomendado en Metabase:
1. Crear una pregunta SQL por bloque.
2. Definir filtros:
- `date_from`
- `date_to`
- `pqrs_type`
- `channel`
- `department_name`
3. Armar tablero con:
- KPIs arriba,
- series al centro,
- mapa y tabla detalle abajo.

## 4) App Streamlit Analítica
Archivo de app:
- `apps/dashboard-streamlit/app.py`

Qué muestra:
1. KPIs nacionales y departamentales.
2. Serie nacional por tipo PQRS.
3. Serie comparativa por departamento.
4. Mapa departamental de Colombia (puntos) y tabla de métricas.
5. Comparativo por tipo PQRS.

Filtros:
1. Rango de fechas.
2. Tipo PQRS.
3. Canal.
4. Nivel geográfico (nacional/departamental).
5. Departamentos seleccionados.

## 5) Ejecutar app Streamlit (Docker Compose)
Reconstruir e iniciar solo Streamlit:

```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/local
docker compose up -d --build streamlit
```

Abrir:
- `http://localhost:8501`

## 6) Ejecutar app Streamlit (local sin Docker)
Si quieres correrla en el entorno conda:

```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse
conda run -n pqr-lakehouse env PGHOST=127.0.0.1 PGPORT=5432 PGUSER=postgres PGPASSWORD=localdev123 PGDATABASE=pqr_lakehouse streamlit run apps/dashboard-streamlit/app.py
```

## 7) Checklist de validación funcional
1. La app abre sin error de conexión.
2. Los KPIs cambian al ajustar fechas.
3. La serie nacional cambia al filtrar tipos PQRS.
4. La serie departamental responde al selector de departamentos.
5. El mapa muestra puntos para departamentos con datos.
6. La tabla del mapa muestra `tickets_count`, `backlog_count`, `within_sla_pct`.

## 8) Notas de diseño
1. El mapa actual es por puntos (lat/lon promedio de municipios por departamento).
2. Coroplético departamental puede añadirse después con GeoJSON (fase siguiente).
3. La app consume vistas `analytics` para mantener desacople con detalle transaccional.
