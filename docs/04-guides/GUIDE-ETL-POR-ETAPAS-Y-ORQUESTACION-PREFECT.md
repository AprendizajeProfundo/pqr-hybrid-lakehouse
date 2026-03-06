# Guía Única - ETL por Etapas + Orquestación con Prefect

Los datos estan en esta carpetas: `data/raw/`, es un archivo `jsonl` que se va a consumir como entrada del ETL.

Guía complementaria de comandos directos:
- `docs/04-guides/GUIDE-COMANDOS-ETL-RAPIDO.md`

## 1. Visión general
Este ETL está diseñado para ser **genérico**:
- No depende de cómo se generó el JSONL.
- Solo asume un archivo de eventos con estructura compatible (`event_id`, `ticket_id`, `event_type`, `ts`, `data`).

Flujo completo:
1. `JSONL local` -> (opcional) RustFS S3 `raw/`
2. `raw_to_bronze`
3. `bronze_to_silver`
4. `silver_to_gold`
5. `load_to_postgres`
6. Visualización en Supabase/Metabase/Streamlit

## 2. Qué script hace cada etapa

## Etapa 0 - Ingesta a RustFS (opcional pero recomendada)
Script:
- `apps/pipelines/ingest_raw_to_rustfs.py`

Qué hace:
1. Toma un JSONL local.
2. Se conecta a RustFS (`http://localhost:9000`) con `boto3`.
3. Crea bucket si no existe.
4. Sube el archivo con layout raw canónico:
- `raw/pqrs/source=mixed/day=YYYY-MM-DD/run_id=<RUN_ID>/events.jsonl`

Entrada:
- `--input`
- `--run-id`
- `--day`

Salida:
- objeto en bucket S3-compatible.

## Etapa 1 - Raw -> Bronze
Script:
- `apps/pipelines/raw_to_bronze.py`

Qué hace:
1. Lee JSONL raw.
2. Normaliza campos clave (`normalize_event`).
3. Valida eventos mínimos.
4. Escribe:
- bronze aceptados
- reject file con inválidos

Entrada:
- `--input`
- `--run-id`

Salida:
- `data/bronze/pqrs_events_bronze*.jsonl`
- `data/bronze/pqrs_events_rejected*.jsonl`

## Etapa 2 - Bronze -> Silver
Script:
- `apps/pipelines/bronze_to_silver.py`

Qué hace:
1. Separa por `event_type`.
2. Construye entidades Silver:
- `tickets`
- `messages`
- `status_events`
- `preclassification`
3. Actualiza `current_status` por último estado observado.

Entrada:
- `--input` bronze JSONL
- `--run-id`

Salida (directorio):
- `tickets.jsonl`
- `messages.jsonl`
- `status_events.jsonl`
- `preclassification.jsonl`

## Etapa 3 - Silver -> Gold
Script:
- `apps/pipelines/silver_to_gold.py`

Qué hace:
1. Calcula `kpi_volume_daily`.
2. Calcula `kpi_backlog_daily`.
3. Calcula `kpi_sla_daily`.
4. Calcula `kpi_volume_geo_daily`, `kpi_backlog_geo_daily`, `kpi_sla_geo_daily`.
5. Calcula series de tiempo `kpi_volume_dept_daily` y `kpi_volume_national_daily`.

Entrada:
- `--silver-dir`
- `--run-id`

Salida (directorio):
- `kpi_volume_daily.jsonl`
- `kpi_backlog_daily.jsonl`
- `kpi_sla_daily.jsonl`
- `kpi_volume_geo_daily.jsonl`
- `kpi_backlog_geo_daily.jsonl`
- `kpi_sla_geo_daily.jsonl`
- `kpi_volume_dept_daily.jsonl`
- `kpi_volume_national_daily.jsonl`

## Etapa 4 - Carga a Postgres/Supabase
Script:
- `apps/pipelines/gold_to_postgres.py`

Qué hace:
1. Lee JSONL Silver y Gold.
2. Inserta/actualiza tablas:
- `silver.tickets`
- `silver.messages`
- `silver.status_events`
- `silver.preclassification`
- `gold.kpi_volume_daily`
- `gold.kpi_backlog_daily`
- `gold.kpi_sla_daily`
- `gold.kpi_volume_geo_daily`
- `gold.kpi_backlog_geo_daily`
- `gold.kpi_sla_geo_daily`
- `gold.kpi_volume_dept_daily`
- `gold.kpi_volume_national_daily`
3. Publica vistas BI:
- `analytics.v_timeseries_national_daily`
- `analytics.v_timeseries_department_daily`
- `analytics.v_geo_daily`
4. Registra run en `meta.etl_runs`.

Entrada:
- `--run-id` (UUID)
- `--silver-dir`
- `--gold-dir`

Salida:
- datos disponibles para SQL y dashboards.

## 3. Ejecución paso a paso (manual por etapa)

Desde raíz del repo:

```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse
make env
make test
```

Definir variables:

```bash
RUN_ID=$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)
DAY=2026-03-05
INPUT_JSONL=data/raw/pqrs_events_20250901_20260228.jsonl
```

## 3.0 Opción rápida: correr todo de una con Make + Prefect

Si ya validaste el entorno y quieres ejecutar el pipeline completo:

```bash
RUN_ID=$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)

make etl-flow RUN_ID=$RUN_ID DAY=2026-03-05 INPUT_JSONL=data/raw/pqrs_events_20250901_20260228.jsonl
```

Nota:
- `etl-flow` ejecuta el flujo orquestado por `apps/pipelines/prefect_etl_flow.py`.
- Para primera ejecución del proyecto, se recomienda revisar al menos una vez por etapas (secciones 3.1 a 3.5).

Si ya tienes datos subidos/cargados y solo quieres validar la orquestación de Prefect sin duplicar carga:

```bash
make etl-flow-skip-io RUN_ID=$RUN_ID DAY=$DAY INPUT_JSONL=$INPUT_JSONL
```

Equivalente:

```bash
make etl-flow RUN_ID=$RUN_ID DAY=$DAY INPUT_JSONL=$INPUT_JSONL PREFECT_UPLOAD_RAW=0 PREFECT_LOAD_DB=0
```

## 3.1 Subir Raw a RustFS (opcional)

```bash
python3 apps/pipelines/ingest_raw_to_rustfs.py \
  --input "$INPUT_JSONL" \
  --run-id "$RUN_ID" \
  --day "$DAY"
```

## 3.2 Raw -> Bronze

```bash
python3 apps/pipelines/raw_to_bronze.py \
  --input "$INPUT_JSONL" \
  --output "data/bronze/pqrs_events_bronze_${RUN_ID}.jsonl" \
  --reject-output "data/bronze/pqrs_events_rejected_${RUN_ID}.jsonl" \
  --run-id "$RUN_ID"
```

## 3.3 Bronze -> Silver

```bash
python3 apps/pipelines/bronze_to_silver.py \
  --input "data/bronze/pqrs_events_bronze_${RUN_ID}.jsonl" \
  --output-dir "data/silver/${RUN_ID}" \
  --run-id "$RUN_ID"
```

## 3.4 Silver -> Gold

```bash
python3 apps/pipelines/silver_to_gold.py \
  --silver-dir "data/silver/${RUN_ID}" \
  --output-dir "data/gold/${RUN_ID}" \
  --run-id "$RUN_ID"
```

## 3.5 Cargar a Postgres

```bash
export PGHOST=127.0.0.1
export PGPORT=5432
export PGUSER=postgres
export PGPASSWORD=localdev123
export PGDATABASE=pqr_lakehouse

python3 apps/pipelines/gold_to_postgres.py \
  --run-id "$RUN_ID" \
  --silver-dir "data/silver/${RUN_ID}" \
  --gold-dir "data/gold/${RUN_ID}" \
  --seed 42 \
  --executed-by "manual-etl"
```

## 4. Orquestación con Prefect
Script:
- `apps/pipelines/prefect_etl_flow.py`

Flow:
1. `task_ingest_raw_to_rustfs` (opcional)
2. `task_raw_to_bronze`
3. `task_bronze_to_silver`
4. `task_silver_to_gold`
5. `task_load_to_postgres` (opcional)

## 4.1 Ejecutar flow local

```bash
python3 apps/pipelines/prefect_etl_flow.py \
  --input-jsonl data/raw/pqrs_events_20250901_20260228.jsonl \
  --run-id "$RUN_ID" \
  --day "$DAY" \
  --upload-raw \
  --load-db \
  --seed 42
```

Si no quieres volver a subir raw ni volver a cargar Postgres:

```bash
python3 apps/pipelines/prefect_etl_flow.py \
  --input-jsonl data/raw/pqrs_events_20250901_20260228.jsonl \
  --run-id "$RUN_ID" \
  --day "$DAY" \
  --seed 42
```

## 4.2 ¿Cuándo entra Prefect?
- Entra cuando ya quieres ejecutar todo el pipeline en un solo comando con trazabilidad de tareas y reintentos.
- Para depuración fina, puedes seguir corriendo las etapas una a una.

## 5. Cómo ver los datos ya subidos/cargados

## 5.1 SQL directo

```bash
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT COUNT(*) FROM bronze.pqrs_events;"
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT COUNT(*) FROM silver.tickets;"
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT COUNT(*) FROM silver.messages;"
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT COUNT(*) FROM silver.status_events;"
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT day,channel,pqrs_type,tickets_count FROM gold.kpi_volume_daily ORDER BY day DESC LIMIT 20;"
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT day,pqrs_type,channel,tickets_count,tickets_mavg_7d,pct_vs_prev_day,pct_vs_prev_week FROM analytics.v_timeseries_national_daily ORDER BY day DESC LIMIT 20;"
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT day,department_name,pqrs_type,channel,tickets_count,tickets_mavg_7d,pct_vs_prev_day,pct_vs_prev_week FROM analytics.v_timeseries_department_daily ORDER BY day DESC LIMIT 20;"
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c "SELECT day,department_name,dane_city_code,pqrs_type,channel,tickets_count,backlog_count,within_sla_pct FROM analytics.v_geo_daily ORDER BY day DESC LIMIT 20;"
```

## 5.2 UIs
- Supabase Studio: `http://localhost:3002`
- Metabase: `http://localhost:3000`
- Streamlit: `http://localhost:8501`
- Prefect UI: `http://localhost:4200`

## 6. Qué hacemos y qué no hacemos en esta fase
Sí:
1. ETL batch por etapas desde JSONL.
2. Orquestación E2E con Prefect.
3. Carga a plataforma local (Postgres/Supabase/BI).

No:
1. Streaming en tiempo real.
2. CDC productivo.
3. Multi-tenant avanzado.
4. ML online en tiempo real.

## 7. Dependencias Python requeridas
Definidas en `environment.yml`:
- `pytest`
- `pyyaml`
- `boto3`
- `psycopg2-binary`
- `prefect`

Actualizar entorno:

```bash
make env
```
