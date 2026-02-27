# SPEC-0017-modelo-formal-estados-pqrs-v1.md
# SPEC-0017 — Especificación Técnica
# Modelo Formal de Estados PQRS (V1)

**Versión:** 1.0  
**Fecha:** 2026-02-25  
**Deriva de:** ADR-0017  
**Ámbito:** Lakehouse PoC (RustFS + Postgres)  
**Nivel:** Implementación ejecutable  

---

# 1. OBJETIVO

Definir formalmente:

- Catálogo de estados PQRS
- Máquina de estados (transiciones permitidas)
- Modelo relacional en Postgres
- Contrato de eventos (Raw/Silver)
- Reglas de validación
- Cálculo formal de SLA
- Procedimiento de bootstrap
- Pruebas mínimas obligatorias

Este documento es **vinculante para implementación**.

---

# 2. MODELO CONCEPTUAL

Cada PQRS evoluciona mediante eventos de cambio de estado.

La secuencia de estados debe:

- Ser coherente
- Respetar transiciones permitidas
- Permitir cálculo exacto de SLA
- Permitir auditoría temporal

---

# 3. ESTADOS CANÓNICOS (V1)

| code        | name        | terminal | sla_behavior | order |
|------------|------------|----------|-------------|-------|
| RECEIVED   | Recibido   | false    | NONE        | 1     |
| RADICATED  | Radicado   | false    | START       | 2     |
| CLASSIFIED | Clasificado| false    | RUN         | 3     |
| ASSIGNED   | Asignado   | false    | RUN         | 4     |
| IN_PROGRESS| En Gestión | false    | RUN         | 5     |
| ON_HOLD    | En Espera  | false    | PAUSE       | 6     |
| RESPONDED  | Respondido | false    | RUN         | 7     |
| CLOSED     | Cerrado    | true     | STOP        | 8     |
| ARCHIVED   | Archivado  | true     | NONE        | 9     |
| REOPENED   | Reabierto  | false    | RUN         | 10    |

---

# 4. MÁQUINA DE ESTADOS (TRANSICIONES PERMITIDAS)

ÚNICAS transiciones válidas:

- RECEIVED → RADICATED
- RADICATED → CLASSIFIED
- CLASSIFIED → ASSIGNED
- ASSIGNED → IN_PROGRESS
- IN_PROGRESS → RESPONDED
- IN_PROGRESS → ON_HOLD
- ON_HOLD → IN_PROGRESS
- RESPONDED → CLOSED
- CLOSED → ARCHIVED
- CLOSED → REOPENED
- REOPENED → IN_PROGRESS

Cualquier otra transición es inválida.

---

# 5. MODELO RELACIONAL (POSTGRES)

## 5.1 dim_status

```sql
CREATE TABLE IF NOT EXISTS dim_status (
  status_id SERIAL PRIMARY KEY,
  code VARCHAR(30) UNIQUE NOT NULL,
  name VARCHAR(60) NOT NULL,
  is_terminal BOOLEAN NOT NULL,
  sla_behavior VARCHAR(10) NOT NULL CHECK (
    sla_behavior IN ('NONE','START','RUN','PAUSE','STOP')
  ),
  order_index INT NOT NULL CHECK (order_index > 0)
);
```

## 5.2 dim_status_transition
```sql
CREATE TABLE IF NOT EXISTS dim_status_transition (
  from_status_id INT NOT NULL REFERENCES dim_status(status_id),
  to_status_id INT NOT NULL REFERENCES dim_status(status_id),
  PRIMARY KEY (from_status_id, to_status_id)
);
```

## 5.3 silver_status_events (tracking curado)
```sql
CREATE TABLE IF NOT EXISTS silver_status_events (
  event_id UUID PRIMARY KEY,
  run_id UUID NOT NULL,
  ticket_id UUID NOT NULL,
  ts TIMESTAMP NOT NULL,
  from_status_id INT NOT NULL REFERENCES dim_status(status_id),
  to_status_id INT NOT NULL REFERENCES dim_status(status_id),
  actor_role VARCHAR(20) NOT NULL
);
```

## 5.4 gold_tickets_snapshot
```sql
CREATE TABLE IF NOT EXISTS gold_tickets_snapshot (
  ticket_id UUID PRIMARY KEY,
  current_status_id INT NOT NULL REFERENCES dim_status(status_id),
  last_update_ts TIMESTAMP NOT NULL,
  sla_days_target INT NOT NULL,
  sla_days_elapsed INT NOT NULL,
  sla_status VARCHAR(10) NOT NULL
);
```

## 5.5 gold_sla_metrics
```sql
CREATE TABLE IF NOT EXISTS gold_sla_metrics (
  metric_id UUID PRIMARY KEY,
  run_id UUID NOT NULL,
  ticket_id UUID NOT NULL,
  ts TIMESTAMP NOT NULL,
  sla_days_target INT NOT NULL,
  sla_days_elapsed INT NOT NULL,
  sla_status VARCHAR(10) NOT NULL
);
```                 

## 5.6 gold_sla_daily
```sql
CREATE TABLE IF NOT EXISTS gold_sla_daily (
  date DATE NOT NULL,
  sla_status VARCHAR(10) NOT NULL,
  count INT NOT NULL,
  PRIMARY KEY (date, sla_status)
);
```

---

# 6. EVENTOS Y TRANSICIONES (DETALLE)

## 6.1 RECEIVED → RADICATED

- **Actor:** SYSTEM
- **Condición:** ticket_id existe en raw_tickets
- **Acción:** Insertar en silver_status_events

## 6.2 RADICATED → CLASSIFIED

- **Actor:** SYSTEM
- **Condición:** classification_code existe en raw_tickets
- **Acción:** Insertar en silver_status_events

## 6.3 CLASSIFIED → ASSIGNED

- **Actor:** SYSTEM
- **Condición:** assigned_to_user_id existe en raw_tickets
- **Acción:** Insertar en silver_status_events

## 6.4 ASSIGNED → IN_PROGRESS

- **Actor:** SYSTEM
- **Condición:** first_response_ts existe en raw_tickets
- **Acción:** Insertar en silver_status_events

## 6.5 IN_PROGRESS → RESPONDED

- **Actor:** SYSTEM
- **Condición:** final_response_ts existe en raw_tickets
- **Acción:** Insertar en silver_status_events

## 6.6 IN_PROGRESS → ON_HOLD

- **Actor:** SYSTEM
- **Condición:** on_hold_ts existe en raw_tickets
- **Acción:** Insertar en silver_status_events

## 6.7 ON_HOLD → IN_PROGRESS

- **Actor:** SYSTEM
- **Condición:** on_hold_ts existe en raw_tickets
- **Acción:** Insertar en silver_status_events

## 6.8 RESPONDED → CLOSED

- **Actor:** SYSTEM
- **Condición:** closed_ts existe en raw_tickets
- **Acción:** Insertar en silver_status_events

## 6.9 CLOSED → ARCHIVED

- **Actor:** SYSTEM
- **Condición:** archived_ts existe en raw_tickets
- **Acción:** Insertar en silver_status_events

## 6.10 CLOSED → REOPENED

- **Actor:** SYSTEM
- **Condición:** reopened_ts existe en raw_tickets
- **Acción:** Insertar en silver_status_events

## 6.11 REOPENED → IN_PROGRESS

- **Actor:** SYSTEM
- **Condición:** first_response_ts existe en raw_tickets
- **Acción:** Insertar en silver_status_events

---

# 7. REGLAS DE VALIDACIÓN (BRONZE → SILVER)

## 7.1 Reglas de negocio

1. Todo ticket en raw_tickets debe tener al menos un evento en silver_status_events
2. Todo ticket debe tener exactamente un estado terminal (CLOSED o ARCHIVED)
3. No puede haber dos eventos consecutivos con el mismo from_status_id y to_status_id
4. No puede haber eventos con timestamps desordenados
5. No puede haber transiciones inválidas según dim_status_transition
6. No puede haber actor_role desconocido
7. No puede haber sla_behavior desconocido
8. No puede haber sla_status desconocido

## 7.2 Reglas de negocio

1. Todo ticket en raw_tickets debe tener al menos un evento en silver_status_events
2. Todo ticket debe tener exactamente un estado terminal (CLOSED o ARCHIVED)
3. No puede haber dos eventos consecutivos con el mismo from_status_id y to_status_id
4. No puede haber eventos con timestamps desordenados
5. No puede haber transiciones inválidas según dim_status_transition
6. No puede haber actor_role desconocido
7. No puede haber sla_behavior desconocido
8. No puede haber sla_status desconocido

---

# 8. CÁLCULO FORMAL DE SLA

## 8.1 SLA_DAYS_TARGET

```sql
SELECT 
  CASE 
    WHEN classification_code = 'PETICION' THEN 10
    WHEN classification_code = 'QUEJA' THEN 15
    WHEN classification_code = 'RECLAMO' THEN 15
    WHEN classification_code = 'SUGERENCIA' THEN 20
    ELSE 15
  END AS sla_days_target
FROM raw_tickets
WHERE ticket_id = :ticket_id;
```

## 8.2 SLA_DAYS_ELAPSED

```sql
SELECT 
  CASE 
    WHEN sla_behavior = 'NONE' THEN 0
    WHEN sla_behavior = 'START' THEN 0
    WHEN sla_behavior = 'RUN' THEN 
      EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - first_event_ts)) / 86400
    WHEN sla_behavior = 'PAUSE' THEN 
      EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_pause_ts)) / 86400
    WHEN sla_behavior = 'STOP' THEN 
      EXTRACT(EPOCH FROM (last_event_ts - first_event_ts)) / 86400
  END AS sla_days_elapsed
FROM (
  SELECT 
    sla_behavior,
    MIN(ts) AS first_event_ts,
    MAX(ts) AS last_event_ts,
    MAX(CASE WHEN sla_behavior = 'PAUSE' THEN ts END) AS last_pause_ts
  FROM silver_status_events
  WHERE ticket_id = :ticket_id
  GROUP BY sla_behavior
);
```

## 8.3 SLA_STATUS

```sql
SELECT 
  CASE 
    WHEN sla_days_elapsed <= sla_days_target THEN 'IN_TIME'
    ELSE 'LATE'
  END AS sla_status
FROM (
  SELECT 
    sla_days_target,
    sla_days_elapsed
  FROM gold_tickets_snapshot
  WHERE ticket_id = :ticket_id
);
```

---

# 9. PROCEDIMIENTO DE BOOTSTRAP

## 9.1 Inicializar dim_status
```sql
INSERT INTO dim_status (
  code,
  name,
  is_terminal,
  sla_behavior,
  order_index
) VALUES
('RECEIVED', 'Recibido', false, 'NONE', 1),
('RADICATED', 'Radicado', false, 'START', 2),
('CLASSIFIED', 'Clasificado', false, 'RUN', 3),
('ASSIGNED', 'Asignado', false, 'RUN', 4),
('IN_PROGRESS', 'En Gestión', false, 'RUN', 5),
('ON_HOLD', 'En Espera', false, 'PAUSE', 6),
('RESPONDED', 'Respondido', false, 'RUN', 7),
('CLOSED', 'Cerrado', true, 'STOP', 8),
('ARCHIVED', 'Archivado', true, 'NONE', 9),
('REOPENED', 'Reabierto', false, 'RUN', 10);
```

## 9.2 Inicializar dim_status_transition
```sql
INSERT INTO dim_status_transition (
  from_status_id,
  to_status_id
) VALUES
(1, 2),
(2, 3),
(3, 4),
(4, 5),
(5, 7),
(5, 6),
(6, 5),
(7, 8),
(8, 9),
(8, 10),
(10, 5);

# 8 CONTRATO DE EVENTO (RAW EN S3)
```json
{
  "run_id": "uuid",
  "ticket_id": "uuid",
  "event_type": "STATUS_CHANGE",
  "from_status": "ASSIGNED",
  "to_status": "IN_PROGRESS",
  "timestamp": "2026-02-21T10:15:22Z",
  "actor_role": "agent"
}
```

# 9. CONTRATO DE EVENTO (BRONZE EN S3)    

```json
{
  "run_id": "uuid",
  "ticket_id": "uuid",
  "event_type": "STATUS_CHANGE",
  "from_status": "ASSIGNED",
  "to_status": "IN_PROGRESS",
  "timestamp": "2026-02-21T10:15:22Z",
  "actor_role": "agent"
}
``` 

# 10. CONTRATO DE EVENTO (SILVER EN S3)

```json
{
  "run_id": "uuid",
  "ticket_id": "uuid",
  "event_type": "STATUS_CHANGE",
  "from_status": "ASSIGNED",
  "to_status": "IN_PROGRESS",
  "timestamp": "2026-02-21T10:15:22Z",
  "actor_role": "agent"
}
```
# 11. CONTRATO DE EVENTO (GOLD EN S3)

```json
{
  "run_id": "uuid",
  "ticket_id": "uuid",
  "event_type": "STATUS_CHANGE",
  "from_status": "ASSIGNED",
  "to_status": "IN_PROGRESS",
  "timestamp": "2026-02-21T10:15:22Z",
  "actor_role": "agent"
}
```
# 12. Reglas de contratos
+ from_status y to_status deben existir en dim_status.code
+ timestamp en ISO-8601 UTC
+ ticket_id UUID
+ run_id obligatorio

# 13. VALIDACIONES OBLIGATORIAS EN PIPELINE

Para cada evento:

1. Resolver from_status_id y to_status_id
2. Verificar existencia en dim_status_transition
3. Verificar orden temporal por ticket
4. Verificar que el primer estado del ticket sea RECEIVED
5. Verificar que exista transición a RADICATED
6. Verificar estado final ∈ {CLOSED, ARCHIVED}

Si falla:

+ Registrar en meta.data_quality
+ Marcar run como FAILED o WARN

# 14. CÁLCULO FORMAL DE SLA

Definición:

SLA_elapsed = suma de intervalos donde sla_behavior ∈ {START, RUN}

Algoritmo:

1. Ordenar eventos por ts
2. Para cada intervalo:

Si estado actual tiene:
  + START o RUN → acumular tiempo
  + PAUSE → no acumular
  + STOP → detener

3. Resultado en segundos u horas

El cálculo debe ser determinista.

# 15. BOOTSTRAP DE CATÁLOGO

Se debe ejecutar script de seed:

1. Insertar/actualizar dim_status
2. Insertar dim_status_transition

La fuente oficial es:

configs/pqrs_status_v1.yaml

# 16. PRUEBAS MÍNIMAS REQUERIDAS

Caso 1: Flujo normal completo
Caso 2: Flujo con ON_HOLD
Caso 3: Flujo con REOPENED
Caso 4: Transición inválida (debe fallar)
Caso 5: Desorden temporal (debe fallar)

# 17. CRITERIO DE ACEPTACIÓN FINAL

Se considera implementado correctamente si:

+ dim_status contiene 10 estados
+ dim_status_transition contiene 11 transiciones
+ silver_status_events valida correctamente
+ SLA se calcula sin ambigüedad
+ Pipeline rechaza transiciones inválidas

# 18. VERSIONADO

Cambios futuros requerirán:

1. Nueva versión YAML
2. Nuevo ADR
3. Nueva versión SPEC (V2)

No se alterará V1 en producción.

FIN DE SPEC-0017


