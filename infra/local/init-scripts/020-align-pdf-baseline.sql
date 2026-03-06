-- Alinea el stack existente con los parámetros del documento base PoC 2026.
-- Este script es idempotente y puede ejecutarse manualmente en una base ya inicializada.

INSERT INTO silver.dim_channel (channel_name, description)
VALUES ('other_digital', 'Peticiones vía otros canales digitalizados')
ON CONFLICT (channel_name) DO UPDATE
SET description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;

UPDATE silver.dim_pqrs_type
SET sla_days_default = CASE pqrs_code
    WHEN 'P' THEN 15
    WHEN 'Q' THEN 10
    WHEN 'R' THEN 8
    WHEN 'S' THEN 20
    ELSE sla_days_default
  END,
  legal_reference = 'Documento base PoC 2026'
WHERE pqrs_code IN ('P', 'Q', 'R', 'S');
