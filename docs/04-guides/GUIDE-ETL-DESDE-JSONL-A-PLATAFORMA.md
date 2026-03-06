# GUIDE - ETL desde JSONL hacia la Plataforma Lakehouse

Los datos estan en esta carpeta: `data/raw/`, es un archivo `jsonl` que se va a consumir como entrada del flujo ETL.

## 1) ¿Ese JSONL ya es la capa Raw?
Respuesta corta: **sí, como fuente raw local**.

Respuesta operacional del proyecto:
1. `data/raw/*.jsonl` = staging local (entrada sin transformar).
2. `s3://.../raw/...` en RustFS = **Raw canónica** del lakehouse (inmutable, versionada por `run_id` y día).

En otras palabras, el archivo local es válido como raw de entrada, pero para el flujo formal del lakehouse debemos subirlo a RustFS bajo el layout raw.

## 2) Qué sigue ahora (paso a paso ETL)

## Paso A - Ingesta a RustFS (Raw canónica)
Objetivo: mover el JSONL local a almacenamiento objeto S3-compatible.

Layout objetivo recomendado:
- `raw/pqrs/source=<canal>/day=YYYY-MM-DD/run_id=<RUN_ID>/events.jsonl`

Como hoy el simulador genera un archivo consolidado multicanal, en esta fase inicial usaremos:
- `raw/pqrs/source=mixed/day=<fecha_lote>/run_id=<RUN_ID>/events.jsonl`

Comandos base (AWS CLI contra RustFS local):

```bash
# 1) Crear bucket (una sola vez)
aws --endpoint-url http://localhost:9000 s3 mb s3://pqr-hybrid-lakehouse-datalake

# 2) Subir el JSONL generado
RUN_ID=sim-20250901-20260228-v1
DAY=2026-03-05
aws --endpoint-url http://localhost:9000 s3 cp \
  data/raw/pqrs_events_20250901_20260228.jsonl \
  s3://pqr-hybrid-lakehouse-datalake/raw/pqrs/source=mixed/day=${DAY}/run_id=${RUN_ID}/events.jsonl
```

## Paso B - Raw -> Bronze
Objetivo: normalizar eventos raw y tiparlos para análisis.

Qué hace:
1. Leer JSONL desde RustFS raw.
2. Validar estructura mínima de evento.
3. Estandarizar campos (`event_id`, `ticket_id`, `event_type`, `ts`, `source_channel`, `data`).
4. Escribir dataset Bronze (idealmente Parquet por partición).

Estado actual del repo:
- Implementado en `apps/pipelines/raw_to_bronze.py`.
- Genera bronze JSONL y archivo de rechazados por `run_id`.

## Paso C - Bronze -> Silver
Objetivo: curar y desnormalizar en entidades de negocio.

Entidades Silver objetivo:
1. `silver.tickets`
2. `silver.messages`
3. `silver.status_events`
4. `silver.preclassification`

Qué hace:
1. Separar por `event_type`.
2. Construir registro por entidad.
3. Validar consistencia (FK lógicas, timestamps, transiciones de estado).
4. Calcular campos operativos (`current_status`, fechas claves, etc.).

Estado actual del repo:
- Implementado en `apps/pipelines/bronze_to_silver.py`.
- Genera `tickets`, `messages`, `status_events`, `preclassification`.
- Incluye persistencia geográfica base (`dane_city_code`, `city_name`, `department_name`).

## Paso D - Silver -> Gold
Objetivo: generar KPIs agregados diarios para consumo BI.

KPIs objetivo:
1. `gold.kpi_volume_daily`
2. `gold.kpi_backlog_daily`
3. `gold.kpi_sla_daily`
4. `gold.kpi_volume_geo_daily`
5. `gold.kpi_backlog_geo_daily`
6. `gold.kpi_sla_geo_daily`
7. `gold.kpi_volume_dept_daily`
8. `gold.kpi_volume_national_daily`

Estado actual:
- Implementado en `apps/pipelines/silver_to_gold.py`.
- Incluye series de tiempo nacionales y departamentales (`mavg 7d`, variación diaria y semanal).

## Paso E - Carga a Postgres/Supabase
Objetivo: dejar tablas listas para consulta en plataforma.

Qué hace:
1. Upsert de métricas Gold.
2. Carga de Silver curado.
3. Registro de trazabilidad en `meta.etl_runs` y `meta.data_quality`.
4. Publica vistas semánticas en `analytics`.

Estado actual:
- Implementado en `apps/pipelines/gold_to_postgres.py`.
- Carga batch (`execute_values`), upsert idempotente, compatibilidad de esquema y enriquecimiento geográfico por `dim_geo`.

## Paso F - Visualización y validación en plataforma
Una vez cargado a Postgres:
1. Supabase Studio: `http://localhost:3002`
2. Metabase: `http://localhost:3000`
3. Streamlit: `http://localhost:8501`

Consultas SQL rápidas:

```sql
SELECT COUNT(*) FROM bronze.pqrs_events;
SELECT COUNT(*) FROM silver.tickets;
SELECT COUNT(*) FROM silver.messages;
SELECT COUNT(*) FROM silver.status_events;
SELECT day, channel, pqrs_type, tickets_count
FROM gold.kpi_volume_daily
ORDER BY day DESC
LIMIT 20;

SELECT day, pqrs_type, channel, tickets_count, tickets_mavg_7d, pct_vs_prev_day, pct_vs_prev_week
FROM analytics.v_timeseries_national_daily
ORDER BY day DESC
LIMIT 20;

SELECT day, department_name, pqrs_type, channel, tickets_count, tickets_mavg_7d, pct_vs_prev_day, pct_vs_prev_week
FROM analytics.v_timeseries_department_daily
ORDER BY day DESC
LIMIT 20;

SELECT day, department_name, dane_city_code, pqrs_type, channel, tickets_count, backlog_count, within_sla_pct
FROM analytics.v_geo_daily
ORDER BY day DESC
LIMIT 20;
```

## 3) Orquestación propuesta (Prefect)
Orquestación mínima recomendada en un flow:
1. `task_upload_raw_to_rustfs`
2. `task_raw_to_bronze`
3. `task_bronze_to_silver`
4. `task_silver_to_gold`
5. `task_load_postgres`
6. `task_quality_checks`
7. `task_publish_run_report`

Parámetros del flow:
1. `run_id`
2. `input_jsonl_path`
3. `s3_bucket`
4. `date_range_start`
5. `date_range_end`
6. `seed`

Resultado del flow:
1. datos en Bronze/Silver/Gold
2. trazabilidad en `meta.*`
3. evidencia de calidad por run

## 4) Qué haremos y qué no haremos (alcance inmediato)
Sí haremos:
1. ETL genérico que **siempre parte de un JSONL** (sin depender del simulador).
2. Ingesta a RustFS raw canónica.
3. Transformaciones Raw->Bronze->Silver->Gold.
4. Carga a Postgres para consultas en Supabase/Metabase/Streamlit.
5. Orquestación con Prefect (flow único end-to-end de MVP).

No haremos en esta fase:
1. Streaming en tiempo real.
2. CDC desde sistemas productivos.
3. ML avanzado de clasificación en línea.
4. Gestión de adjuntos binarios complejos (solo metadata en eventos).
5. Backfills multi-tenant complejos.

## 5) Criterio de “listo para plataforma”
Se considera listo cuando:
1. Un JSONL de entrada llega a RustFS raw con `run_id`.
2. Se pueblan tablas `bronze`, `silver`, `gold` sin errores.
3. `meta.etl_runs` y `meta.data_quality` registran el run.
4. Los dashboards/consultas muestran resultados consistentes.
5. Re-ejecutar con mismo input + seed produce resultados reproducibles.
