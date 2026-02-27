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

COMMENT ON SCHEMA meta IS 'Esquema de metadatos: trazabilidad de ETL, calidad de datos.';
COMMENT ON SCHEMA bronze IS 'Esquema Bronze: eventos normalizados desde S3 (Raw layer).';
COMMENT ON SCHEMA silver IS 'Esquema Silver: tablas curadas y enriquecidas para análisis.';
COMMENT ON SCHEMA gold IS 'Esquema Gold: KPIs y métricas agregadas para executive dashboards.';

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
  priority VARCHAR(10) DEFAULT 'NORMAL',
  created_at TIMESTAMP NOT NULL,
  radicated_at TIMESTAMP,
  current_status VARCHAR(20) NOT NULL DEFAULT 'RECEIVED',
  geo_id INTEGER,
  region VARCHAR(50),
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
  ('phone', 'Peticiones vía llamada telefónica'),
  ('web_portal', 'Portal web de ciudadano'),
  ('in_person', 'Presentación presencial'),
  ('social_media', 'Redes sociales y WhatsApp'),
  ('sms', 'Mensajes de texto SMS'),
  ('api', 'Integraciones automatizadas')
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

INSERT INTO silver.dim_geo (
  region_name, department_name, city_name,
  dane_department_code, dane_city_code,
  latitude, longitude, geom
) 
VALUES 
  ('Andina', 'Cundinamarca', 'Bogotá', '11', '11001', 4.7110, -74.0721, ST_SetSRID(ST_MakePoint(-74.0721,4.7110),4326)),
  ('Andina', 'Cundinamarca', 'Soacha', '11', '25720', 4.5796, -74.2135, ST_SetSRID(ST_MakePoint(-74.2135,4.5796),4326)),
  ('Andina', 'Boyacá', 'Tunja', '15', '15001', 5.5378, -73.3678, ST_SetSRID(ST_MakePoint(-73.3678,5.5378),4326)),
  ('Andina', 'Nariño', 'Pasto', '52', '52001', 1.2136, -77.2811, ST_SetSRID(ST_MakePoint(-77.2811,1.2136),4326)),
  ('Caribe', 'Atlantico', 'Barranquilla', '08', '08001', 10.9685, -74.7813, ST_SetSRID(ST_MakePoint(-74.7813,10.9685),4326)),
  ('Caribe', 'Bolívar', 'Cartagena', '13', '13001', 10.3910, -75.4794, ST_SetSRID(ST_MakePoint(-75.4794,10.3910),4326)),
  ('Caribe', 'Magdalena', 'Santa Marta', '47', '47001', 11.2408, -74.1990, ST_SetSRID(ST_MakePoint(-74.1990,11.2408),4326)),
  ('Pacífico', 'Valle del Cauca', 'Cali', '76', '76001', 3.4516, -76.5320, ST_SetSRID(ST_MakePoint(-76.5320,3.4516),4326)),
  ('Pacífico', 'Valle del Cauca', 'Buenaventura', '76', '76001', 3.8683, -77.0560, ST_SetSRID(ST_MakePoint(-77.0560,3.8683),4326)),
  ('Orinoquía', 'Meta', 'Villavicencio', '50', '50001', 4.1420, -73.6317, ST_SetSRID(ST_MakePoint(-73.6317,4.1420),4326)),
  ('Amazonia', 'Amazonas', 'Leticia', '91', '91001', -4.2153, -69.9406, ST_SetSRID(ST_MakePoint(-69.9406,-4.2153),4326))
ON CONFLICT DO NOTHING;

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
  ('P', 'Petición', 'Derecho a presentar peticiones respetuosas a las autoridades', 'Decreto 2649/2012', 10),
  ('Q', 'Queja', 'Desconformidad con la prestación del servicio', 'Decreto 2649/2012', 15),
  ('R', 'Reclamo', 'Hechos o actos que causan daño pecuniario', 'Decreto 2649/2012', 20),
  ('S', 'Sugerencia', 'Propuestas de mejora en procesos y servicios', 'Decreto 2649/2012', 30)
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
  ('Low', 1, 'Requiere respuesta en tiempo normal', 72),
  ('Medium', 2, 'Requiere respuesta dentro de 48 horas', 48),
  ('High', 3, 'Requiere respuesta dentro de 24 horas', 24),
  ('Urgent', 4, 'Requiere respuesta inmediata', 4)
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
  ('OPEN', 'Abierto', 'Ticket recibido y asignado', FALSE),
  ('IN_PROCESS', 'En Proceso', 'Siendo atendido por el gestor', FALSE),
  ('PENDING_INFO', 'Pendiente Info', 'Aguardando información adicional del ciudadano', FALSE),
  ('RESOLVED', 'Resuelto', 'Respuesta dada al ciudadano', TRUE),
  ('CLOSED', 'Cerrado', 'Ticket finalizado y confirmado', TRUE),
  ('REJECTED', 'Rechazado', 'No procede (fuera de competencia, etc.)', TRUE),
  ('ESCALATED', 'Escalado', 'Escalado a nivel superior', FALSE)
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
-- 7. EXTENSIONES Y CONFIGURACIÓN
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

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
