# Guía de Comandos ETL (Rápida)

Esta guía es solo de comandos, lista para copiar/pegar.

## 1) Ir al proyecto

```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse
```

## 2) Preparar entorno

```bash
make env
make test
```

## 3) Definir variables del run

```bash
RUN_ID=$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)

DAY=2026-03-05
INPUT_JSONL=data/raw/pqrs_events_20250901_20260228.jsonl
```

## 4) ETL por etapas (recomendado primera vez)

### Etapa 0 - Subir raw a RustFS

```bash
make etl-ingest RUN_ID=$RUN_ID DAY=$DAY INPUT_JSONL=$INPUT_JSONL
```

### Etapa 1 - Raw -> Bronze

```bash
make etl-bronze RUN_ID=$RUN_ID INPUT_JSONL=$INPUT_JSONL
```

Validar:

```bash
wc -l data/bronze/pqrs_events_bronze_${RUN_ID}.jsonl
wc -l data/bronze/pqrs_events_rejected_${RUN_ID}.jsonl
```

### Etapa 2 - Bronze -> Silver

```bash
make etl-silver RUN_ID=$RUN_ID
```

Validar:

```bash
ls -lh data/silver/${RUN_ID}/
```

### Etapa 3 - Silver -> Gold

```bash
make etl-gold RUN_ID=$RUN_ID
```

Validar:

```bash
ls -lh data/gold/${RUN_ID}/
```

Deberías ver también estos archivos nuevos:
- `kpi_volume_geo_daily.jsonl`
- `kpi_backlog_geo_daily.jsonl`
- `kpi_sla_geo_daily.jsonl`
- `kpi_volume_dept_daily.jsonl`
- `kpi_volume_national_daily.jsonl`

### Etapa 4 - Cargar a Postgres

```bash
make etl-load RUN_ID=$RUN_ID
```

Validar en DB:

```bash
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT COUNT(*) FROM silver.tickets;"
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT COUNT(*) FROM gold.kpi_volume_daily;"
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT COUNT(*) FROM gold.kpi_volume_national_daily;"
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT COUNT(*) FROM gold.kpi_volume_dept_daily;"
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT COUNT(*) FROM analytics.v_timeseries_national_daily;"
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT COUNT(*) FROM analytics.v_timeseries_department_daily;"
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT COUNT(*) FROM analytics.v_geo_daily;"
```

## 5) Todo de una (Prefect)

```bash
make etl-flow RUN_ID=$RUN_ID DAY=$DAY INPUT_JSONL=$INPUT_JSONL
```

## 5.1) Probar Prefect si ya subiste/cargaste datos

Usa un `RUN_ID` nuevo para no pisar carpetas anteriores y ejecuta sin re-subir raw ni re-cargar DB:

```bash
RUN_ID=$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)

make etl-flow-skip-io RUN_ID=$RUN_ID DAY=$DAY INPUT_JSONL=$INPUT_JSONL
```

Alternativa equivalente en un solo comando:

```bash
make etl-flow RUN_ID=$RUN_ID DAY=$DAY INPUT_JSONL=$INPUT_JSONL PREFECT_UPLOAD_RAW=0 PREFECT_LOAD_DB=0
```

## 6) Ver en plataforma

- Prefect UI: `http://localhost:4200`
- Supabase Studio: `http://localhost:3002`
- Metabase: `http://localhost:3000`
- Streamlit: `http://localhost:8501`
