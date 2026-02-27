# SPEC-0016 — Base de Seguimiento PQRS (V1) + Datos Sintéticos en Lakehouse

**Versión:** 1.0  
**Fecha:** 2026-02-25  
**Deriva de:** ADR-0016  

---

# 1. OBJETIVO

Definir la implementación del subsistema de seguimiento PQRS, incluyendo:

- Generación de datos sintéticos deterministas
- Layout y esquemas en S3 (RustFS)
- Esquemas en Postgres (Supabase)
- Pipelines de transformación (Raw → Bronze → Silver → Gold)
- Métricas y KPIs habilitados
- Validaciones de calidad de datos

---

# 2. DATOS SINTÉTICOS (GENERACIÓN)

## 2.1 Requisitos de Determinismo

- Cada run usa `seed` fijo para reproducibilidad.
- Parámetros: `seed`, `date_range`, `git_sha`, `config_hash`.
- Output: mismos conteos, checksums y distribuciones en re-runs.

## 2.2 Distribución de Volumen

- Volumen diario: promedio 50-200 tickets (configurable).
- Canales: email (40%), webform (30%), chat (20%), call (10%).
- Tipos PQRS: P (30%), Q (25%), R (30%), S (15%).
- SLA breach: 7-12% controlado.

## 2.3 Estructura de Eventos por Ticket

Cada ticket genera eventos JSONL en `raw/pqrs/source=<source>/day=YYYY-MM-DD/run_id=<RUN_ID>/events.jsonl`:

```json
{
  "event_id": "uuid",
  "ticket_id": "uuid",
  "event_type": "TICKET_CREATED|MESSAGE_ADDED|STATUS_CHANGED|ATTACHMENT_ADDED",
  "ts": "2026-02-25T10:00:00Z",
  "data": { /* event-specific */ }
}
```

Eventos obligatorios: RECEIVED → RADICATED → ... → CLOSED/ARCHIVED.

---

# 3. LAYOUT S3 (RUSTFS)

## 3.1 Raw Layer

- `raw/pqrs/source=email/day=2026-02-25/run_id=abc123/events.jsonl`
- `raw/pqrs/source=webform/day=2026-02-25/run_id=abc123/events.jsonl`
- `raw/pqrs/source=chat/day=2026-02-25/run_id=abc123/events.jsonl`
- `raw/pqrs/source=call/day=2026-02-25/run_id=abc123/events.jsonl`

Manifest: `manifests/day=2026-02-25/run_id=abc123/manifest.json` (conteos, rutas).

## 3.2 Bronze Layer

- `bronze/pqrs_events/source=email/day=2026-02-25/run_id=abc123/part-00000.parquet`

Esquema Parquet: normalización ligera (tipado, timestamps).

## 3.3 Silver Layer

- `silver/tickets/month=2026-02/run_id=abc123/part-00000.parquet`
- `silver/messages/month=2026-02/run_id=abc123/part-00000.parquet`
- `silver/status_events/month=2026-02/run_id=abc123/part-00000.parquet`
- `silver/attachments/month=2026-02/run_id=abc123/part-00000.parquet`

## 3.4 Gold Layer

- `gold/kpi_backlog/day=2026-02-25/run_id=abc123/part-00000.parquet`
- `gold/kpi_sla/day=2026-02-25/run_id=abc123/part-00000.parquet`
- `gold/kpi_volume/day=2026-02-25/run_id=abc123/part-00000.parquet`

---

# 4. ESQUEMAS POSTGRES

## 4.1 Meta Schemas

```sql
CREATE TABLE meta.etl_runs (
  run_id UUID PRIMARY KEY,
  seed INTEGER,
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  status VARCHAR(20),
  date_min DATE,
  date_max DATE,
  git_sha VARCHAR(40),
  config_hash VARCHAR(64),
  raw_objects_count INTEGER,
  bronze_rows INTEGER,
  silver_rows INTEGER,
  gold_rows INTEGER
);

CREATE TABLE meta.data_quality (
  run_id UUID,
  dataset VARCHAR(50),
  check_name VARCHAR(100),
  result VARCHAR(20),
  value NUMERIC,
  threshold NUMERIC,
  details_json JSONB
);
```

## 4.2 Bronze Schemas

El esquema Bronze almacena los eventos JSON ya tipados y limpiados. Se trata de
una tabla única donde cada fila representa un evento generado por un ticket;
essa tabla facilita las transformaciones posteriores hacia Silver.

```sql
-- cada fila corresponde a un evento normalizado de la capa Bronze
CREATE TABLE bronze_pqrs_events (
  event_id UUID PRIMARY KEY,
  ticket_id UUID,
  source_channel VARCHAR(20),   -- email, webform, chat, call
  event_type VARCHAR(50),
  ts TIMESTAMP,
  data JSONB                    -- payload original enriquecido/parseado
);
```

## 4.3 Silver Schemas

```sql
CREATE TABLE silver_tickets (
  ticket_id UUID PRIMARY KEY,
  external_id VARCHAR(50),
  source_channel VARCHAR(20),
  pqrs_type VARCHAR(1),
  priority VARCHAR(10),
  created_at TIMESTAMP,
  radicated_at TIMESTAMP,
  current_status VARCHAR(20),
  geo_id INTEGER,               -- FK a dim_geo (incluye códigos DANE y geom PostGIS)
  sla_due_at TIMESTAMP,
  closed_at TIMESTAMP
);

CREATE TABLE silver_messages (
  message_id UUID PRIMARY KEY,
  ticket_id UUID REFERENCES silver_tickets(ticket_id),
  ts TIMESTAMP,
  role VARCHAR(10),
  text TEXT,
  text_len INTEGER
);

CREATE TABLE silver_status_events (
  event_id UUID PRIMARY KEY,
  ticket_id UUID REFERENCES silver_tickets(ticket_id),
  ts TIMESTAMP,
  status_from VARCHAR(20),
  status_to VARCHAR(20),
  actor_role VARCHAR(10)
);

-- Dimensiones ligeras que acompañan los hechos (tabla "dim_*"):
-- dim_geo: región/municipio con códigos DANE, coordenadas y geometría PostGIS
-- dim_channel: catálogo de canales (email, teléfono, web, etc.)
-- dim_pqrs_type: tipos P/Q/R/S con SLA por defecto
-- dim_status: lista de estados posibles
-- dim_priority: niveles de prioridad
-- dim_role: roles de actores (ciudadano, gestor, supervisor, admin)

```

## 4.4 Gold Schemas

```sql
CREATE TABLE gold_kpi_volume_daily (
  day DATE,
  channel VARCHAR(20),        -- 'email', 'webform', 'chat', 'call'
  pqrs_type VARCHAR(1),       -- 'P', 'Q', 'R', 'S'
  tickets_count INTEGER,
  PRIMARY KEY (day, channel, pqrs_type)
);

CREATE TABLE gold_kpi_backlog_daily (
  day DATE,
  pqrs_type VARCHAR(1),
  region VARCHAR(50),          -- 'Bogotá', 'Cali', 'Medellín', etc.
  backlog_count INTEGER,
  PRIMARY KEY (day, pqrs_type, region)
);

CREATE TABLE gold_kpi_sla_daily (
  day DATE,
  pqrs_type VARCHAR(1),
  within_sla_pct NUMERIC(5,2),
  overdue_count INTEGER,
  avg_overdue_days NUMERIC(5,2),
  PRIMARY KEY (day, pqrs_type)
);
```

---

# 5. PIPELINES DE TRANSFORMACIÓN

## 5.1 Raw → Bronze

- Leer JSONL, validar esquema.
- Convertir a Parquet con tipado.
- Checks: no duplicados, timestamps válidos.

## 5.2 Bronze → Silver

- Desnormalizar eventos en tablas curadas.
- Enriquecer con dimensiones (geo, channel, etc.).
- Validar transiciones de estado (contra pqrs_status_v1.yaml).
- Calcular SLA.

## 5.3 Silver → Gold

- Agregaciones diarias: volumen, backlog, SLA.
- Materializar en Parquet y cargar a Postgres.

---

# 6. VALIDACIONES DE CALIDAD

- Cobertura 100% de tickets con al menos 1 evento.
- Transiciones válidas según máquina de estados.
- SLA calculado correctamente.
- Checksums consistentes en re-runs.

---

# 7. CRITERIO DE ACEPTACIÓN

- Runs deterministas con seed fijo.
- Esquemas poblados en S3 y Postgres.
- KPIs calculados y accesibles.
- Reproducibilidad verificada.