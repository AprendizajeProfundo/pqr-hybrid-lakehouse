
# ADR-0016 — Base de Seguimiento PQRS + Datos Sintéticos en S3 (RustFS) para Analítica Lakehouse

**Estado:** Aprobado (Final)
**Fecha:** 2026-02-24
**Decisores:** Equipo PoC PQR (Arquitectura + Data Engineering)
**Contexto:** PoC académico/arquitectónico enfocado en ciencia de datos; se excluye operación/gestión transaccional (app) y automatización de respuestas.

## 1. Contexto y problema

Se requiere una **base de datos de seguimiento** (tracking) de PQRS que permita:

* reconstruir el ciclo de vida de cada ticket mediante eventos con timestamp,
* calcular métricas operativas y de cumplimiento (SLA),
* soportar analítica estadística (series de tiempo, distribuciones, geografía, backlog),
* mantener trazabilidad y reproducibilidad total (auditoría + reruns deterministas),
* almacenar **los datos simulados por PQRS en S3** como “fuente de verdad” (Raw), y
* servir consultas analíticas desde un warehouse relacional (Postgres/Supabase) y/o directamente desde Parquet (DuckDB).

La app de gestión (radicación real, asignación real, UI, workflows operativos) **queda explícitamente fuera**.

## 2. Decisión

### 2.1 Arquitectura adoptada (Lakehouse híbrido)

* **Data Plane:** RustFS (S3 compatible) como lakehouse con capas: `raw/`, `bronze/`, `silver/`, `gold/`.
* **Control Plane:** Postgres (Supabase) para:

  * `meta.*` (runs, data quality, manifests indexados),
  * `silver_*` (modelos curados para tracking),
  * `gold_*` (métricas/KPIs materializados para consumo).
* **Compute Plane:** pipelines batch (Python) para:

  * generación sintética determinista,
  * transformaciones raw→bronze→silver,
  * cálculo gold,
  * carga/refresh en Postgres.

### 2.2 “Source of truth” y regla de oro

* **La verdad vive en S3 Raw**: datos **append-only**, versionados por `run_id` y fecha.
* Postgres es **serving layer** (consulta rápida y dashboards), no almacén primario del histórico crudo.

### 2.3 Contrato del seguimiento PQRS (modelo lógico)

El tracking se basa en 4 entidades analíticas canónicas (mínimo viable, suficiente para métricas):

1. **Ticket** (identidad del caso)
2. **Message** (interacciones textuales: ciudadano/agente)
3. **StatusEvent** (transiciones de estado)
4. **Attachment** (adjuntos simulados)

Además:

* `dim_geo` (municipio/región con códigos DANE, coordenadas y geometría PostGIS), `dim_channel`, `dim_pqrs_type`, `dim_status` (dimensiones).
* `meta_runs`, `meta_data_quality` (observabilidad, auditoría, reproducibilidad).

## 3. Especificación de almacenamiento en S3 (RustFS)

### 3.1 Layout obligatorio (Hive-style + run_id)

**Raw (JSONL/CSV/TXT), inmutable:**

* `raw/pqrs/source=email/day=YYYY-MM-DD/run_id=<RUN_ID>/events.jsonl`
* `raw/pqrs/source=webform/day=YYYY-MM-DD/run_id=<RUN_ID>/events.jsonl`
* `raw/pqrs/source=chat/day=YYYY-MM-DD/run_id=<RUN_ID>/events.jsonl`
* `raw/pqrs/source=call/day=YYYY-MM-DD/run_id=<RUN_ID>/events.jsonl`

**Manifests y evidencia:**

* `manifests/day=YYYY-MM-DD/run_id=<RUN_ID>/manifest.json`
* `manifests/day=YYYY-MM-DD/run_id=<RUN_ID>/checksums.json`
* `logs/day=YYYY-MM-DD/run_id=<RUN_ID>/pipeline.log`

**Bronze (Parquet, normalización ligera):**

* `bronze/pqrs_events/source=<source>/day=YYYY-MM-DD/run_id=<RUN_ID>/part-*.parquet`

**Silver (Parquet, curado, esquema estable):**

* `silver/tickets/month=YYYY-MM/run_id=<RUN_ID>/part-*.parquet`
* `silver/messages/month=YYYY-MM/run_id=<RUN_ID>/part-*.parquet`
* `silver/status_events/month=YYYY-MM/run_id=<RUN_ID>/part-*.parquet`
* `silver/attachments/month=YYYY-MM/run_id=<RUN_ID>/part-*.parquet`

**Gold (Parquet, productos analíticos):**

* `gold/kpi_backlog/day=YYYY-MM-DD/run_id=<RUN_ID>/part-*.parquet`
* `gold/kpi_sla/day=YYYY-MM-DD/run_id=<RUN_ID>/part-*.parquet`
* `gold/kpi_volume/day=YYYY-MM-DD/run_id=<RUN_ID>/part-*.parquet`

## 4. Esquema del Warehouse (Postgres/Supabase)

### 4.1 Esquema `meta.*` (mínimo obligatorio)

* `meta.etl_runs`

  * `run_id (pk)`, `seed`, `started_at`, `finished_at`, `status`, `date_min`, `date_max`, `git_sha`, `config_hash`, `raw_objects_count`, `bronze_rows`, `silver_rows`, `gold_rows`
* `meta.data_quality`

  * `run_id`, `dataset`, `check_name`, `result`, `value`, `threshold`, `details_json`
* `meta.manifest_index`

  * `run_id`, `s3_manifest_path`, `s3_checksums_path`

### 4.2 Esquemas `silver_*` (tracking curado)

* `silver_tickets`

  * `ticket_id (pk)`, `external_id`, `source_channel`, `pqrs_type`, `priority`, `created_at`, `radicated_at`, `current_status`, `geo_id`, `sla_due_at`, `closed_at`
* `silver_messages`

  * `message_id (pk)`, `ticket_id (fk)`, `ts`, `role (citizen/agent)`, `text`, `text_len`
* `silver_status_events`

  * `event_id (pk)`, `ticket_id (fk)`, `ts`, `status_from`, `status_to`, `actor_role`
* `silver_attachments`

  * `attachment_id (pk)`, `ticket_id (fk)`, `ts`, `file_type`, `size_kb`, `source_channel`

Dimensiones (ligeras):

* `dim_geo(geo_id, region, municipio, dane_codes… y ahora también coordenadas + geometría PostGIS para análisis espacial)`
* `dim_channel(channel_id, name)`
* `dim_pqrs_type(type_id, name, sla_business_days)`
* `dim_status(status_id, name, is_terminal)`

### 4.3 Esquemas `gold_*` (métricas)

* `gold_kpi_volume_daily(day, channel, pqrs_type, tickets_count)`
* `gold_kpi_backlog_daily(day, pqrs_type, region, backlog_count)`
* `gold_kpi_sla_daily(day, pqrs_type, within_sla_pct, overdue_count, avg_overdue_days)`
* `gold_kpi_first_response_daily(day, pqrs_type, avg_hours_to_first_response)`
* `gold_kpi_close_time_daily(day, pqrs_type, avg_hours_to_close)`

## 5. Generación sintética (requisitos no negociables)

* **Determinista:** todo run tiene `seed` fijo y produce los mismos resultados si:

  * mismo `seed`, mismo rango de fechas, misma versión de código (`git_sha`), misma config (`config_hash`).
* **Distribuciones realistas:** según documento:

  * volumen diario promedio y picos,
  * proporción por canal,
  * SLA breach 7–12% controlado,
  * duraciones variables por estados.
* **Eventos obligatorios por ticket:** al menos:

  * `RECEIVED → RADICATED → CLASSIFIED → ASSIGNED → IN_PROGRESS → RESPONDED → CLOSED → ARCHIVED`
  * (permitir variantes y loops controlados para realismo, pero acotados).

## 6. Métricas habilitadas (alcance del MVP)

Con lo anterior quedan habilitadas, sin app:

* Volumen por día/canal/tipo
* Backlog por día/tipo/región
* Tiempo a primera respuesta
* Tiempo a cierre
* Cumplimiento SLA por día/tipo
* Vencidas y retraso promedio
* Flujos de estado (matriz transición)

## 7. Alternativas consideradas (y por qué no)

1. **Solo Postgres (sin lake):** descartado

   * pierde evidencia cruda, auditoría, backfills y separación lakehouse.
2. **Solo Parquet (sin Postgres):** no ideal para serving rápido y herramientas BI; se mantiene DuckDB ad-hoc, pero Postgres acelera.
3. **Data Vault / 3NF estricta:** sobredimensionado para PoC; se prioriza tracking analítico.

## 8. Consecuencias

**Positivas**

* Trazabilidad y reproducibilidad auditables.
* Escala natural a AWS (S3 real + RDS/Supabase).
* Métricas completas sin construir operación.

**Costos**

* Disciplina: manifests, run_id, y append-only desde el día 1.
* Un pipeline mínimo real (no notebooks sueltos).

## 9. Fuera de alcance (explícito)

* UI/App de gestión PQRS (radicación real, asignación real, flujo humano).
* Integración con sistemas productivos reales.
* Automatización de respuestas.
* Modelos ML avanzados (se pueden agregar después, no ahora).

## 10. Criterio de aceptación (Definition of Done)

Un “run” se considera completo si:

1. Existe `raw/.../run_id=<RUN_ID>/events.jsonl` para al menos 1 canal y 1 día.
2. Existe `manifest.json` con conteos y rutas.
3. Existe `bronze` en Parquet y `silver` con esquema estable.
4. Postgres contiene `meta.etl_runs` y al menos 3 tablas `gold_*` llenas.
5. Re-ejecutar el run con mismo seed produce mismos conteos y checksums.

---
