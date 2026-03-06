/**
 * INIT-POSTGRES.SQL
 * 
 * Inicialización completa de PostgreSQL para el proyecto pqr-hybrid-lakehouse
 * 
 * Crea:
 * - Schemas: meta, bronze, silver, gold
 * - Tablas de metadatos, eventos, y KPIs
 * - Índices para optimización de consultas
 * 
 * Ejecución: Docker Compose lee este archivo en /docker-entrypoint-initdb.d/
 * y lo ejecuta automáticamente al iniciar postgres.
 */

-- ============================================================================
-- 1. CREAR SCHEMAS
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS auth;

-- Extensiones requeridas antes de crear tablas con tipos/funciones específicas
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

COMMENT ON SCHEMA meta IS 'Esquema de metadatos: trazabilidad de ETL, calidad de datos.';
COMMENT ON SCHEMA bronze IS 'Esquema Bronze: eventos normalizados desde S3 (Raw layer).';
COMMENT ON SCHEMA silver IS 'Esquema Silver: tablas curadas y enriquecidas para análisis.';
COMMENT ON SCHEMA gold IS 'Esquema Gold: KPIs y métricas agregadas para executive dashboards.';
COMMENT ON SCHEMA analytics IS 'Esquema semántico: vistas para dashboards y consultas BI.';
COMMENT ON SCHEMA auth IS 'Esquema requerido por Supabase GoTrue para autenticación.';

-- ============================================================================
-- 2. META SCHEMA - TABLAS DE TRAZABILIDAD Y CALIDAD
-- ============================================================================

CREATE TABLE IF NOT EXISTS meta.etl_runs (
  run_id UUID PRIMARY KEY,
  seed INTEGER NOT NULL,
  started_at TIMESTAMP NOT NULL,
  finished_at TIMESTAMP,
  status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
  date_min DATE,
  date_max DATE,
  git_sha VARCHAR(40),
  config_hash VARCHAR(64),
  raw_objects_count INTEGER DEFAULT 0,
  bronze_rows INTEGER DEFAULT 0,
  silver_rows INTEGER DEFAULT 0,
  gold_rows INTEGER DEFAULT 0,
  executed_by VARCHAR(100),                -- usuario o sistema que ejecutó
  executor_role VARCHAR(50),               -- rol: SYSTEM, ADMIN, USER, GITHUB_ACTION
  execution_context VARCHAR(255),          -- contexto: docker-compose, kubernetes, manual
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE meta.etl_runs IS 
  'Registro de ejecuciones ETL: cada run captura seed, fechas, hashes, conteos finales, y quién ejecutó.';
COMMENT ON COLUMN meta.etl_runs.status IS 
  'Estado del run: PENDING, RUNNING, SUCCESS, FAILED, PARTIAL.';
COMMENT ON COLUMN meta.etl_runs.executed_by IS 
  'Usuario, sistema o proceso que ejecutó el run (ej: admin, scheduler, github-actions).';
COMMENT ON COLUMN meta.etl_runs.executor_role IS 
  'Rol del ejecutor: SYSTEM (automático), ADMIN, USER, GITHUB_ACTION.';
COMMENT ON COLUMN meta.etl_runs.execution_context IS 
  'Dónde se ejecutó: docker-compose, kubernetes, manual, airflow, prefect, etc.';

CREATE INDEX IF NOT EXISTS idx_etl_runs_status ON meta.etl_runs(status);
CREATE INDEX IF NOT EXISTS idx_etl_runs_started_at ON meta.etl_runs(started_at DESC);

-- ============================================================================

CREATE TABLE IF NOT EXISTS meta.data_quality (
  id SERIAL PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES meta.etl_runs(run_id) ON DELETE CASCADE,
  dataset VARCHAR(50) NOT NULL,
  check_name VARCHAR(100) NOT NULL,
  result VARCHAR(20) NOT NULL,
  value NUMERIC,
  threshold NUMERIC,
  details_json JSONB,
  checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(run_id, dataset, check_name)
);

COMMENT ON TABLE meta.data_quality IS 
  'Resultados de validaciones de calidad por run y dataset.';
COMMENT ON COLUMN meta.data_quality.result IS 
  'PASS, FAIL, WARN, SKIPPED.';

CREATE INDEX IF NOT EXISTS idx_data_quality_run_id ON meta.data_quality(run_id);
CREATE INDEX IF NOT EXISTS idx_data_quality_dataset ON meta.data_quality(dataset);
CREATE INDEX IF NOT EXISTS idx_data_quality_result ON meta.data_quality(result);

-- ============================================================================
-- 3. BRONZE SCHEMA - EVENTOS NORMALIZADOS
-- ============================================================================

CREATE TABLE IF NOT EXISTS bronze.pqrs_events (
  event_id UUID PRIMARY KEY,
  ticket_id UUID NOT NULL,
  source_channel VARCHAR(20) NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  ts TIMESTAMP NOT NULL,
  data JSONB NOT NULL,
  run_id UUID REFERENCES meta.etl_runs(run_id),
  ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE bronze.pqrs_events IS 
  'Almacén de eventos normalizados: cada fila es un evento JSONL parseado a Parquet.';
COMMENT ON COLUMN bronze.pqrs_events.source_channel IS 
  'Canal de origen: email, webform, chat, call.';
COMMENT ON COLUMN bronze.pqrs_events.event_type IS 
  'Tipo de evento: TICKET_CREATED, MESSAGE_ADDED, STATUS_CHANGED, ATTACHMENT_ADDED, etc.';

CREATE INDEX IF NOT EXISTS idx_pqrs_events_ticket_id ON bronze.pqrs_events(ticket_id);
CREATE INDEX IF NOT EXISTS idx_pqrs_events_source_channel ON bronze.pqrs_events(source_channel);
CREATE INDEX IF NOT EXISTS idx_pqrs_events_ts ON bronze.pqrs_events(ts DESC);
CREATE INDEX IF NOT EXISTS idx_pqrs_events_run_id ON bronze.pqrs_events(run_id);
CREATE INDEX IF NOT EXISTS idx_pqrs_events_event_type ON bronze.pqrs_events(event_type);

-- ============================================================================
-- 4. SILVER SCHEMA - TABLAS CURADAS Y ENRIQUECIDAS
-- ============================================================================

CREATE TABLE IF NOT EXISTS silver.tickets (
  ticket_id UUID PRIMARY KEY,
  external_id VARCHAR(50),
  source_channel VARCHAR(20) NOT NULL,
  pqrs_type VARCHAR(1) NOT NULL,
  priority VARCHAR(10) DEFAULT 'media',
  created_at TIMESTAMP NOT NULL,
  radicated_at TIMESTAMP,
  current_status VARCHAR(20) NOT NULL DEFAULT 'RECEIVED',
  geo_id INTEGER,
  region VARCHAR(50),
  region_name VARCHAR(50),
  department_name VARCHAR(50),
  city_name VARCHAR(100),
  dane_city_code VARCHAR(5),
  sla_due_at TIMESTAMP,
  closed_at TIMESTAMP,
  
  run_id UUID REFERENCES meta.etl_runs(run_id),
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE silver.tickets IS 
  'Dimensión principal: foto actual de cada ticket con estado, tiempos clave, ubicación.';
COMMENT ON COLUMN silver.tickets.pqrs_type IS 
  'Tipo PQRS: P (Petición), Q (Queja), R (Reclamo), S (Sugerencia).';
COMMENT ON COLUMN silver.tickets.sla_due_at IS 
  'Fecha de vencimiento del SLA calculada en base al tipo PQRS y fecha de creación.';
COMMENT ON COLUMN silver.tickets.current_status IS 
  'Estado actual: RECEIVED, RADICATED, IN_PROGRESS, PENDING_INFO, CLOSED, ARCHIVED.';

CREATE INDEX IF NOT EXISTS idx_tickets_pqrs_type ON silver.tickets(pqrs_type);
CREATE INDEX IF NOT EXISTS idx_tickets_source_channel ON silver.tickets(source_channel);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON silver.tickets(current_status);
CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON silver.tickets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_closed_at ON silver.tickets(closed_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_region ON silver.tickets(region);
CREATE INDEX IF NOT EXISTS idx_tickets_region_name ON silver.tickets(region_name);
CREATE INDEX IF NOT EXISTS idx_tickets_department_name ON silver.tickets(department_name);
CREATE INDEX IF NOT EXISTS idx_tickets_dane_city_code ON silver.tickets(dane_city_code);
CREATE INDEX IF NOT EXISTS idx_tickets_sla_due_at ON silver.tickets(sla_due_at);

-- ============================================================================

CREATE TABLE IF NOT EXISTS silver.messages (
  message_id UUID PRIMARY KEY,
  ticket_id UUID NOT NULL REFERENCES silver.tickets(ticket_id) ON DELETE CASCADE,
  ts TIMESTAMP NOT NULL,
  role VARCHAR(10) NOT NULL,
  text TEXT NOT NULL,
  text_len INTEGER,
  
  run_id UUID REFERENCES meta.etl_runs(run_id),
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE silver.messages IS 
  'Línea temporal de mensajes: correspondencia, notas internas, respuestas del solicitante.';
COMMENT ON COLUMN silver.messages.role IS 
  'Rol: INTERNAL, EXTERNAL, SYSTEM, AGENT, CITIZEN.';
COMMENT ON COLUMN silver.messages.text_len IS 
  'Longitud del mensaje en caracteres (para análisis de complejidad).';

CREATE INDEX IF NOT EXISTS idx_messages_ticket_id ON silver.messages(ticket_id);
CREATE INDEX IF NOT EXISTS idx_messages_ts ON silver.messages(ts DESC);
CREATE INDEX IF NOT EXISTS idx_messages_role ON silver.messages(role);

-- ============================================================================

CREATE TABLE IF NOT EXISTS silver.status_events (
  event_id UUID PRIMARY KEY,
  ticket_id UUID NOT NULL REFERENCES silver.tickets(ticket_id) ON DELETE CASCADE,
  ts TIMESTAMP NOT NULL,
  status_from VARCHAR(20),
  status_to VARCHAR(20) NOT NULL,
  actor_role VARCHAR(10),
  reason VARCHAR(255),
  
  run_id UUID REFERENCES meta.etl_runs(run_id),
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE silver.status_events IS 
  'Histórico de transiciones de estado: trazabilidad completa del ciclo de vida del ticket.';
COMMENT ON COLUMN silver.status_events.actor_role IS 
  'Quién hizo el cambio: SYSTEM, AGENT, CITIZEN, ADMIN.';

CREATE INDEX IF NOT EXISTS idx_status_events_ticket_id ON silver.status_events(ticket_id);
CREATE INDEX IF NOT EXISTS idx_status_events_ts ON silver.status_events(ts DESC);
CREATE INDEX IF NOT EXISTS idx_status_events_status_from ON silver.status_events(status_from);
CREATE INDEX IF NOT EXISTS idx_status_events_status_to ON silver.status_events(status_to);

-- ============================================================================
-- 4.1 SILVER SCHEMA - PRECLASIFICACION PQRS
-- ============================================================================

CREATE TABLE IF NOT EXISTS silver.preclassification (
  ticket_id UUID NOT NULL REFERENCES silver.tickets(ticket_id) ON DELETE CASCADE,
  run_id UUID NOT NULL REFERENCES meta.etl_runs(run_id),
  model_type VARCHAR(30) NOT NULL,            -- rules / tfidf_lr / embeddings
  model_version VARCHAR(50) NOT NULL,
  predicted_type VARCHAR(1) NOT NULL,         -- P/Q/R/S
  predicted_priority VARCHAR(10) NOT NULL,    -- alta/media/baja
  score NUMERIC(5,4) NOT NULL,
  explain_json JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (ticket_id, run_id, model_version)
);

COMMENT ON TABLE silver.preclassification IS
  'Resultado de preclasificación por ticket y run, versionado por modelo/reglas.';
COMMENT ON COLUMN silver.preclassification.model_type IS
  'Tipo de clasificador: rules, tfidf_lr o embeddings.';
COMMENT ON COLUMN silver.preclassification.model_version IS
  'Versión de reglas/modelo utilizada para inferencia.';

CREATE INDEX IF NOT EXISTS idx_preclassification_run_id ON silver.preclassification(run_id);
CREATE INDEX IF NOT EXISTS idx_preclassification_predicted_type ON silver.preclassification(predicted_type);
CREATE INDEX IF NOT EXISTS idx_preclassification_predicted_priority ON silver.preclassification(predicted_priority);
CREATE INDEX IF NOT EXISTS idx_preclassification_created_at ON silver.preclassification(created_at DESC);

-- ============================================================================
-- 5. GOLD SCHEMA - KPIs Y MÉTRICAS AGREGADAS
-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.kpi_volume_daily (
  day DATE NOT NULL,
  channel VARCHAR(20) NOT NULL,
  pqrs_type VARCHAR(1) NOT NULL,
  tickets_count INTEGER NOT NULL DEFAULT 0,
  
  run_id UUID REFERENCES meta.etl_runs(run_id),
  calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (day, channel, pqrs_type)
);

COMMENT ON TABLE gold.kpi_volume_daily IS 
  'KPI de volumen: recuento diario de tickets por canal de entrada y tipo PQRS.';
COMMENT ON COLUMN gold.kpi_volume_daily.channel IS 
  'Canal: email, webform, chat, call.';
COMMENT ON COLUMN gold.kpi_volume_daily.pqrs_type IS 
  'Tipo: P, Q, R, S.';

CREATE INDEX IF NOT EXISTS idx_kpi_volume_day ON gold.kpi_volume_daily(day DESC);
CREATE INDEX IF NOT EXISTS idx_kpi_volume_channel ON gold.kpi_volume_daily(channel);
CREATE INDEX IF NOT EXISTS idx_kpi_volume_pqrs_type ON gold.kpi_volume_daily(pqrs_type);

-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.kpi_backlog_daily (
  day DATE NOT NULL,
  pqrs_type VARCHAR(1) NOT NULL,
  region VARCHAR(50) NOT NULL,
  backlog_count INTEGER NOT NULL DEFAULT 0,
  
  run_id UUID REFERENCES meta.etl_runs(run_id),
  calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (day, pqrs_type, region)
);

COMMENT ON TABLE gold.kpi_backlog_daily IS 
  'KPI de backlog: cantidad de tickets abiertos al final de cada día, por tipo y región.';
COMMENT ON COLUMN gold.kpi_backlog_daily.backlog_count IS 
  'Conteo de tickets con current_status != CLOSED/ARCHIVED.';

CREATE INDEX IF NOT EXISTS idx_kpi_backlog_day ON gold.kpi_backlog_daily(day DESC);
CREATE INDEX IF NOT EXISTS idx_kpi_backlog_pqrs_type ON gold.kpi_backlog_daily(pqrs_type);
CREATE INDEX IF NOT EXISTS idx_kpi_backlog_region ON gold.kpi_backlog_daily(region);

-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.kpi_sla_daily (
  day DATE NOT NULL,
  pqrs_type VARCHAR(1) NOT NULL,
  within_sla_pct NUMERIC(5,2) NOT NULL,
  overdue_count INTEGER NOT NULL DEFAULT 0,
  avg_overdue_days NUMERIC(5,2),
  
  run_id UUID REFERENCES meta.etl_runs(run_id),
  calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (day, pqrs_type)
);

COMMENT ON TABLE gold.kpi_sla_daily IS 
  'KPI de SLA: porcentaje de cumplimiento de tiempos prometidos, y estadísticas de incumplimiento.';
COMMENT ON COLUMN gold.kpi_sla_daily.within_sla_pct IS 
  'Porcentaje de tickets cerrados dentro del SLA legal (0.00 a 100.00).';
COMMENT ON COLUMN gold.kpi_sla_daily.overdue_count IS 
  'Número de tickets que excedieron el SLA.';
COMMENT ON COLUMN gold.kpi_sla_daily.avg_overdue_days IS 
  'Promedio de días de atraso para tickets fuera de SLA.';

CREATE INDEX IF NOT EXISTS idx_kpi_sla_day ON gold.kpi_sla_daily(day DESC);
CREATE INDEX IF NOT EXISTS idx_kpi_sla_pqrs_type ON gold.kpi_sla_daily(pqrs_type);

-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.kpi_volume_geo_daily (
  day DATE NOT NULL,
  region_name VARCHAR(50) NOT NULL,
  department_name VARCHAR(50) NOT NULL,
  dane_city_code VARCHAR(5) NOT NULL,
  pqrs_type VARCHAR(1) NOT NULL,
  channel VARCHAR(20) NOT NULL,
  tickets_count INTEGER NOT NULL DEFAULT 0,
  run_id UUID REFERENCES meta.etl_runs(run_id),
  calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (day, region_name, department_name, dane_city_code, pqrs_type, channel)
);

CREATE INDEX IF NOT EXISTS idx_kpi_volume_geo_day ON gold.kpi_volume_geo_daily(day DESC);
CREATE INDEX IF NOT EXISTS idx_kpi_volume_geo_department ON gold.kpi_volume_geo_daily(department_name);
CREATE INDEX IF NOT EXISTS idx_kpi_volume_geo_city_code ON gold.kpi_volume_geo_daily(dane_city_code);
CREATE INDEX IF NOT EXISTS idx_kpi_volume_geo_type ON gold.kpi_volume_geo_daily(pqrs_type);

-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.kpi_backlog_geo_daily (
  day DATE NOT NULL,
  region_name VARCHAR(50) NOT NULL,
  department_name VARCHAR(50) NOT NULL,
  dane_city_code VARCHAR(5) NOT NULL,
  pqrs_type VARCHAR(1) NOT NULL,
  backlog_count INTEGER NOT NULL DEFAULT 0,
  run_id UUID REFERENCES meta.etl_runs(run_id),
  calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (day, region_name, department_name, dane_city_code, pqrs_type)
);

CREATE INDEX IF NOT EXISTS idx_kpi_backlog_geo_day ON gold.kpi_backlog_geo_daily(day DESC);
CREATE INDEX IF NOT EXISTS idx_kpi_backlog_geo_department ON gold.kpi_backlog_geo_daily(department_name);
CREATE INDEX IF NOT EXISTS idx_kpi_backlog_geo_city_code ON gold.kpi_backlog_geo_daily(dane_city_code);
CREATE INDEX IF NOT EXISTS idx_kpi_backlog_geo_type ON gold.kpi_backlog_geo_daily(pqrs_type);

-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.kpi_sla_geo_daily (
  day DATE NOT NULL,
  region_name VARCHAR(50) NOT NULL,
  department_name VARCHAR(50) NOT NULL,
  dane_city_code VARCHAR(5) NOT NULL,
  pqrs_type VARCHAR(1) NOT NULL,
  within_sla_pct NUMERIC(5,2) NOT NULL,
  overdue_count INTEGER NOT NULL DEFAULT 0,
  avg_overdue_days NUMERIC(5,2),
  run_id UUID REFERENCES meta.etl_runs(run_id),
  calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (day, region_name, department_name, dane_city_code, pqrs_type)
);

CREATE INDEX IF NOT EXISTS idx_kpi_sla_geo_day ON gold.kpi_sla_geo_daily(day DESC);
CREATE INDEX IF NOT EXISTS idx_kpi_sla_geo_department ON gold.kpi_sla_geo_daily(department_name);
CREATE INDEX IF NOT EXISTS idx_kpi_sla_geo_city_code ON gold.kpi_sla_geo_daily(dane_city_code);
CREATE INDEX IF NOT EXISTS idx_kpi_sla_geo_type ON gold.kpi_sla_geo_daily(pqrs_type);

-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.kpi_volume_dept_daily (
  day DATE NOT NULL,
  department_name VARCHAR(50) NOT NULL,
  pqrs_type VARCHAR(1) NOT NULL,
  channel VARCHAR(20) NOT NULL,
  tickets_count INTEGER NOT NULL DEFAULT 0,
  tickets_mavg_7d NUMERIC(12,2) NOT NULL DEFAULT 0,
  pct_vs_prev_day NUMERIC(8,2) NOT NULL DEFAULT 0,
  pct_vs_prev_week NUMERIC(8,2) NOT NULL DEFAULT 0,
  run_id UUID REFERENCES meta.etl_runs(run_id),
  calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (day, department_name, pqrs_type, channel)
);

CREATE INDEX IF NOT EXISTS idx_kpi_volume_dept_day ON gold.kpi_volume_dept_daily(day DESC);
CREATE INDEX IF NOT EXISTS idx_kpi_volume_dept_department ON gold.kpi_volume_dept_daily(department_name);
CREATE INDEX IF NOT EXISTS idx_kpi_volume_dept_type ON gold.kpi_volume_dept_daily(pqrs_type);
CREATE INDEX IF NOT EXISTS idx_kpi_volume_dept_channel ON gold.kpi_volume_dept_daily(channel);

-- ============================================================================

CREATE TABLE IF NOT EXISTS gold.kpi_volume_national_daily (
  day DATE NOT NULL,
  pqrs_type VARCHAR(1) NOT NULL,
  channel VARCHAR(20) NOT NULL,
  tickets_count INTEGER NOT NULL DEFAULT 0,
  tickets_mavg_7d NUMERIC(12,2) NOT NULL DEFAULT 0,
  pct_vs_prev_day NUMERIC(8,2) NOT NULL DEFAULT 0,
  pct_vs_prev_week NUMERIC(8,2) NOT NULL DEFAULT 0,
  run_id UUID REFERENCES meta.etl_runs(run_id),
  calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (day, pqrs_type, channel)
);

CREATE INDEX IF NOT EXISTS idx_kpi_volume_national_day ON gold.kpi_volume_national_daily(day DESC);
CREATE INDEX IF NOT EXISTS idx_kpi_volume_national_type ON gold.kpi_volume_national_daily(pqrs_type);
CREATE INDEX IF NOT EXISTS idx_kpi_volume_national_channel ON gold.kpi_volume_national_daily(channel);

-- ============================================================================
-- 5. SILVER SCHEMA - TABLAS DE DIMENSIONES
-- ============================================================================

CREATE TABLE IF NOT EXISTS silver.dim_channel (
  channel_id SERIAL PRIMARY KEY,
  channel_name VARCHAR(50) NOT NULL UNIQUE,
  description VARCHAR(255),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE silver.dim_channel IS 
  'Dimensión: Canales de entrada de PQRS (email, teléfono, portal web, etc.).';

INSERT INTO silver.dim_channel (channel_name, description) 
VALUES 
  ('email', 'Peticiones vía correo electrónico'),
  ('webform', 'Peticiones vía formulario web'),
  ('chat', 'Peticiones vía chat digital'),
  ('call', 'Peticiones vía llamada telefónica'),
  ('other_digital', 'Peticiones vía otros canales digitalizados')
ON CONFLICT DO NOTHING;

-- ============================================================================

CREATE TABLE IF NOT EXISTS silver.dim_geo (
  geo_id SERIAL PRIMARY KEY,
  region_name VARCHAR(50) NOT NULL,
  department_name VARCHAR(50) NOT NULL,
  city_name VARCHAR(100) NOT NULL,
  dane_department_code VARCHAR(3),            -- código DANE de departamento (ej: 11 para Cundinamarca)
  dane_city_code VARCHAR(5),                  -- código DANE de municipio (ej: 11001 para Bogotá)
  latitude NUMERIC(9,6),                      -- coordenadas decimales para análisis geo
  longitude NUMERIC(9,6),
  geom GEOMETRY(Point,4326),                  -- PostGIS geometry, útil para cálculos espaciales
  postal_code VARCHAR(10),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(region_name, department_name, city_name)
);

COMMENT ON TABLE silver.dim_geo IS 
  'Dimensión: Geografía de Colombia (regiones, departamentos, ciudades) con códigos DANE, coordenadas y geometría PostGIS.';


-- ============================================================================

CREATE TABLE IF NOT EXISTS silver.dim_pqrs_type (
  pqrs_type_id SERIAL PRIMARY KEY,
  pqrs_code CHAR(1) NOT NULL UNIQUE,
  pqrs_name VARCHAR(30) NOT NULL UNIQUE,
  description VARCHAR(255),
  legal_reference VARCHAR(100),
  sla_days_default INTEGER DEFAULT 10,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE silver.dim_pqrs_type IS 
  'Dimensión: Tipos de PQRS según Decreto 2649 de 2012 (P, Q, R, S).';
COMMENT ON COLUMN silver.dim_pqrs_type.sla_days_default IS 
  'SLA por defecto en días (Decreto 2649: 10 días para Peticiones).';

INSERT INTO silver.dim_pqrs_type (pqrs_code, pqrs_name, description, legal_reference, sla_days_default) 
VALUES 
  ('P', 'Petición', 'Derecho a presentar peticiones respetuosas a las autoridades', 'Documento base PoC 2026', 15),
  ('Q', 'Queja', 'Desconformidad con la prestación del servicio', 'Documento base PoC 2026', 10),
  ('R', 'Reclamo', 'Hechos o actos que causan daño pecuniario', 'Documento base PoC 2026', 8),
  ('S', 'Sugerencia', 'Propuestas de mejora en procesos y servicios', 'Documento base PoC 2026', 20)
ON CONFLICT DO NOTHING;

-- ============================================================================

CREATE TABLE IF NOT EXISTS silver.dim_priority (
  priority_id SERIAL PRIMARY KEY,
  priority_name VARCHAR(20) NOT NULL UNIQUE,
  priority_level INTEGER NOT NULL UNIQUE,
  description VARCHAR(255),
  response_time_hours INTEGER,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE silver.dim_priority IS 
  'Dimensión: Niveles de prioridad (baja, media, alta, urgente).';

INSERT INTO silver.dim_priority (priority_name, priority_level, description, response_time_hours) 
VALUES 
  ('baja', 1, 'Requiere respuesta en tiempo normal', 72),
  ('media', 2, 'Requiere respuesta dentro de 48 horas', 48),
  ('alta', 3, 'Requiere respuesta dentro de 24 horas', 24)
ON CONFLICT DO NOTHING;

-- ============================================================================

CREATE TABLE IF NOT EXISTS silver.dim_status (
  status_id SERIAL PRIMARY KEY,
  status_code VARCHAR(20) NOT NULL UNIQUE,
  status_name VARCHAR(50) NOT NULL UNIQUE,
  description VARCHAR(255),
  is_terminal BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE silver.dim_status IS 
  'Dimensión: Estados posibles de un ticket PQRS.';
COMMENT ON COLUMN silver.dim_status.is_terminal IS 
  'TRUE si es estado final (cerrado, resuelto, rechazado).';

INSERT INTO silver.dim_status (status_code, status_name, description, is_terminal) 
VALUES 
  ('RECEIVED', 'Recibido', 'Ticket recibido, pendiente de radicación', FALSE),
  ('RADICATED', 'Radicado', 'Ticket radicado oficialmente', FALSE),
  ('CLASSIFIED', 'Clasificado', 'Ticket clasificado por tipo y prioridad', FALSE),
  ('ASSIGNED', 'Asignado', 'Ticket asignado a un gestor', FALSE),
  ('IN_PROGRESS', 'En Progreso', 'Ticket siendo atendido', FALSE),
  ('ON_HOLD', 'En Espera', 'Atención pausada por información faltante o dependencia externa', FALSE),
  ('RESPONDED', 'Respondido', 'Se entregó respuesta al ciudadano', FALSE),
  ('CLOSED', 'Cerrado', 'Ticket cerrado formalmente', TRUE),
  ('ARCHIVED', 'Archivado', 'Ticket finalizado y archivado', TRUE),
  ('REOPENED', 'Reabierto', 'Ticket reabierto tras cierre', FALSE)
ON CONFLICT DO NOTHING;

-- ============================================================================

CREATE TABLE IF NOT EXISTS silver.dim_role (
  role_id SERIAL PRIMARY KEY,
  role_code VARCHAR(20) NOT NULL UNIQUE,
  role_name VARCHAR(50) NOT NULL UNIQUE,
  description VARCHAR(255),
  permissions JSONB,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE silver.dim_role IS 
  'Dimensión: Roles de actores que interactúan en PQRS.';

INSERT INTO silver.dim_role (role_code, role_name, description, permissions) 
VALUES 
  ('CITIZEN', 'Ciudadano', 'Usuario que presenta el PQRS', '{"submit": true, "view_own": true}'),
  ('GESTOR', 'Gestor', 'Funcionario que atiende el PQRS', '{"view_all": true, "update_status": true, "add_comments": true}'),
  ('SUPERVISOR', 'Supervisor', 'Supervisa gestores y escalamientos', '{"view_all": true, "escalate": true, "override_sla": true}'),
  ('ADMIN', 'Administrador', 'Acceso completo al sistema', '{"all": true}')
ON CONFLICT DO NOTHING;

-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_dim_channel_active ON silver.dim_channel(is_active);
CREATE INDEX IF NOT EXISTS idx_dim_geo_region ON silver.dim_geo(region_name);
CREATE INDEX IF NOT EXISTS idx_dim_pqrs_code ON silver.dim_pqrs_type(pqrs_code);
CREATE INDEX IF NOT EXISTS idx_dim_priority_level ON silver.dim_priority(priority_level);
CREATE INDEX IF NOT EXISTS idx_dim_status_code ON silver.dim_status(status_code);
CREATE INDEX IF NOT EXISTS idx_dim_role_code ON silver.dim_role(role_code);

-- ============================================================================
-- 6. VISTAS ÚTILES PARA CONSULTAS FRECUENTES
-- ============================================================================

CREATE OR REPLACE VIEW silver.v_tickets_open AS
SELECT 
  ticket_id,
  external_id,
  source_channel,
  pqrs_type,
  priority,
  created_at,
  current_status,
  region,
  CURRENT_DATE - created_at::DATE AS days_open,
  CASE 
    WHEN sla_due_at < CURRENT_TIMESTAMP THEN 'OVERDUE'
    WHEN sla_due_at < CURRENT_TIMESTAMP + INTERVAL '2 days' THEN 'AT_RISK'
    ELSE 'HEALTHY'
  END AS sla_status
FROM silver.tickets
WHERE closed_at IS NULL
ORDER BY sla_due_at ASC;

COMMENT ON VIEW silver.v_tickets_open IS 
  'Vista: tickets abiertos con indicador de riesgo de SLA.';

-- ============================================================================

CREATE OR REPLACE VIEW silver.v_sla_summary AS
SELECT 
  pqrs_type,
  COUNT(*) AS total_tickets,
  COUNT(CASE WHEN closed_at IS NOT NULL THEN 1 END) AS closed_tickets,
  COUNT(CASE WHEN closed_at IS NULL THEN 1 END) AS open_tickets,
  ROUND(
    100.0 * COUNT(CASE WHEN closed_at IS NOT NULL THEN 1 END) / COUNT(*),
    2
  ) AS closure_pct,
  AVG(EXTRACT(DAY FROM (COALESCE(closed_at, CURRENT_TIMESTAMP) - created_at))) AS avg_days_to_close
FROM silver.tickets
GROUP BY pqrs_type;

COMMENT ON VIEW silver.v_sla_summary IS 
  'Vista: resumen de SLA por tipo PQRS (cierre, velocidad).';

-- ============================================================================
-- 7. VISTAS SEMANTICAS ANALYTICS
-- ============================================================================

CREATE OR REPLACE VIEW analytics.v_timeseries_national_daily AS
SELECT
  day,
  pqrs_type,
  channel,
  tickets_count,
  tickets_mavg_7d,
  pct_vs_prev_day,
  pct_vs_prev_week,
  run_id,
  calculated_at
FROM gold.kpi_volume_national_daily;

CREATE OR REPLACE VIEW analytics.v_timeseries_department_daily AS
SELECT
  day,
  department_name,
  pqrs_type,
  channel,
  tickets_count,
  tickets_mavg_7d,
  pct_vs_prev_day,
  pct_vs_prev_week,
  run_id,
  calculated_at
FROM gold.kpi_volume_dept_daily;

CREATE OR REPLACE VIEW analytics.v_geo_daily AS
SELECT
  v.day,
  v.region_name,
  v.department_name,
  v.dane_city_code,
  v.pqrs_type,
  v.channel,
  v.tickets_count,
  b.backlog_count,
  s.within_sla_pct,
  s.overdue_count,
  s.avg_overdue_days
FROM gold.kpi_volume_geo_daily v
LEFT JOIN gold.kpi_backlog_geo_daily b
  ON v.day = b.day
 AND v.region_name = b.region_name
 AND v.department_name = b.department_name
 AND v.dane_city_code = b.dane_city_code
 AND v.pqrs_type = b.pqrs_type
LEFT JOIN gold.kpi_sla_geo_daily s
  ON v.day = s.day
 AND v.region_name = s.region_name
 AND v.department_name = s.department_name
 AND v.dane_city_code = s.dane_city_code
 AND v.pqrs_type = s.pqrs_type;

-- Comentarios sobre la base de datos
COMMENT ON DATABASE postgres IS 
  'Base de datos PQR Hybrid Lakehouse - Control Plane para metadatos y Gold layer.';

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================

-- Verificación final
SELECT 
  'PostgreSQL inicializado correctamente' AS status,
  NOW() AS timestamp;
