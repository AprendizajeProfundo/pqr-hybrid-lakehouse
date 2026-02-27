# 📘 Guía Detallada: init-postgres.sql para Estudiantes

**Archivo:** `infra/local/init-scripts/init-postgres.sql`

Este documento explica línea por línea qué hace el script de inicialización de PostgreSQL 
para el proyecto pqr-hybrid-lakehouse. Es el "plano" que define toda la base de datos.

---

## 1. ¿Qué es este archivo y por qué existe?

### El problema
Cuando Docker inicia un contenedor PostgreSQL vacío, no tiene tablas, esquemas, ni estructura.
Sin estructura, tu aplicación no sabe dónde guardar datos.

### La solución
`init-postgres.sql` es un **script de inicialización automática**. 
- Docker lo detecta automáticamente en `/docker-entrypoint-initdb.d/`.
- Lo ejecuta **una vez** al primer arranque del contenedor.
- Crea toda la estructura necesaria (schemas, tablas, índices, vistas).

### Analogía
Es como un "plano de construcción" para la base de datos:
- Sin plano: caos, no sabes dónde guardar qué.
- Con plano: orden, cada cosa en su lugar.

---

## 2. Estructura del archivo

El archivo tiene 7 secciones principales:

```
1. CREAR SCHEMAS
   ↓
2. META SCHEMA (metadatos)
   ↓
3. BRONZE SCHEMA (eventos)
   ↓
4. SILVER SCHEMA (tablas curadas)
   ↓
5. GOLD SCHEMA (KPIs agregados)
   ↓
6. VISTAS ÚTILES
   ↓
7. EXTENSIONES Y CONFIGURACIÓN
```

Cada sección construye sobre la anterior. Es como armar un edificio: primero los cimientos,
luego las paredes, luego los pisos.

---

## 3. Schemas: Organizadores de tablas

### ¿Qué es un schema?

Un **schema** es como una carpeta dentro de PostgreSQL que agrupa tablas relacionadas.

```
PostgreSQL
├── Schema: public (por defecto, no la usamos)
├── Schema: meta (metadatos)
├── Schema: bronze (eventos)
├── Schema: silver (datos curados)
└── Schema: gold (KPIs finales)
```

### Código:

```sql
CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
```

**IF NOT EXISTS:** si el schema ya existe, no falla. Es **idempotente**.

### Comentarios:

```sql
COMMENT ON SCHEMA meta IS 'Esquema de metadatos: trazabilidad de ETL, calidad de datos.';
```

Los comentarios **documentan** la intención. Si alguien pregunta "¿para qué es `meta`?",
el comentario lo explica sin necesidad de googlear.

---

## 4. SCHEMA META: Trazabilidad y Auditoría

### ¿Para qué?

Meta almacena **quién hizo qué y cuándo**: logs de ejecuciones ETL, resultados de calidad.
Es el "diario" de la base de datos.

---

### Tabla: `meta.etl_runs`

Registro de cada **ejecución del pipeline**, incluyendo quién lo ejecutó.

```sql
CREATE TABLE IF NOT EXISTS meta.etl_runs (
  run_id UUID PRIMARY KEY,           -- identificador único del run
  seed INTEGER NOT NULL,              -- semilla para reproducibilidad
  started_at TIMESTAMP NOT NULL,      -- cuándo empezó
  finished_at TIMESTAMP,              -- cuándo terminó (NULL si aún corre)
  status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
  date_min DATE,                      -- rango de fechas procesadas
  date_max DATE,
  git_sha VARCHAR(40),                -- versión del código usado
  config_hash VARCHAR(64),            -- hash de la configuración
  raw_objects_count INTEGER DEFAULT 0,-- cuántos objetos en Raw
  bronze_rows INTEGER DEFAULT 0,      -- cuántas filas en Bronze
  silver_rows INTEGER DEFAULT 0,      -- cuántas filas en Silver
  gold_rows INTEGER DEFAULT 0,        -- cuántas filas en Gold
  executed_by VARCHAR(100),           -- usuario/sistema que ejecutó
  executor_role VARCHAR(50),          -- rol: SYSTEM, ADMIN, USER, GITHUB_ACTION
  execution_context VARCHAR(255),     -- dónde: docker-compose, kubernetes, manual
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Ejemplo de datos:**

| run_id | seed | executed_by | executor_role | execution_context | status |
|--------|------|------------|---------------|-------------------|--------|
| abc-123 | 42 | admin | ADMIN | docker-compose | SUCCESS |
| def-456 | 42 | scheduler | SYSTEM | kubernetes | SUCCESS |
| ghi-789 | 42 | github-actions | GITHUB_ACTION | github-actions | SUCCESS |

**¿Por qué es importante?**

- Reproducibilidad: si usas el mismo `seed`, obtienes los mismos datos.
- Auditoría: saber **quién** y **cuándo** ejecutó un pipeline (cumplimiento normativo).
- Debugging: si algo falló, buscar en logs del run y quién fue responsable.
- Trazabilidad: hacer seguimiento de datos desde su origen hasta el usuario que los generó.

---

### Tabla: `meta.data_quality`

Resultados de **validaciones** que corre el pipeline.

```sql
CREATE TABLE IF NOT EXISTS meta.data_quality (
  id SERIAL PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES meta.etl_runs(run_id),
  dataset VARCHAR(50) NOT NULL,      -- qué se validó (ej: bronze_events)
  check_name VARCHAR(100) NOT NULL,  -- nombre del check (ej: no_duplicados)
  result VARCHAR(20) NOT NULL,       -- PASS, FAIL, WARN, SKIPPED
  value NUMERIC,                     -- valor medido
  threshold NUMERIC,                 -- valor mínimo/máximo esperado
  details_json JSONB,                -- detalles en JSON (flexible)
  checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Ejemplo de datos:**

| dataset | check_name | result | value | threshold | details |
|---------|-----------|--------|-------|-----------|---------|
| bronze_events | no_duplicados | PASS | 5000 | 5000 | {} |
| silver_tickets | fechas_validas | FAIL | 95.5 | 100.0 | {"invalidos": 22} |

**¿Para qué?**

- Saber si los datos están sanos.
- Alertas: si `result = FAIL`, algo necesita atención.
- Trazabilidad: todo registrado para auditoría.

---

## 5. SCHEMA BRONZE: Eventos Normalizados

### Tabla: `bronze.pqrs_events`

**Una tabla única** que almacena todos los eventos parseados desde el Raw layer.

```sql
CREATE TABLE IF NOT EXISTS bronze.pqrs_events (
  event_id UUID PRIMARY KEY,         -- uuid único del evento
  ticket_id UUID NOT NULL,           -- a qué ticket pertenece
  source_channel VARCHAR(20) NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  ts TIMESTAMP NOT NULL,             -- cuándo pasó
  data JSONB NOT NULL,               -- payload completo enriquecido
  run_id UUID REFERENCES meta.etl_runs(run_id),
  ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Ejemplo de datos:**

| event_id | ticket_id | source_channel | event_type | ts | data |
|----------|-----------|----------------|----------|----|----|
| evt-001 | tkt-abc | email | TICKET_CREATED | 2026-02-25 10:00 | {"citizen": "Juan", "subject": "..."} |
| evt-002 | tkt-abc | email | MESSAGE_ADDED | 2026-02-25 10:30 | {"from": "agent", "text": "..."} |
| evt-003 | tkt-abc | email | STATUS_CHANGED | 2026-02-25 11:00 | {"from": "RECEIVED", "to": "RADICATED"} |

**¿Por qué solo una tabla?**

Porque son **eventos puros**: ocurrencias aisladas. No necesita relaciones complejas.
El `data` JSONB contiene lo que sea necesario para ese evento específico.

**Índices:**

```sql
CREATE INDEX IF NOT EXISTS idx_pqrs_events_ticket_id ON bronze.pqrs_events(ticket_id);
```

Un índice es como un "catálogo de una librería":
- Sin índice: buscar un ticket es leer todos los eventos (lento).
- Con índice: saltar directo al ticket que buscas (rápido).

---

## 6. SCHEMA SILVER: Tablas Curadas para Análisis

### Tabla: `silver.tickets`

**"Foto actual"** de cada ticket, enriquecida con campos calculados.

```sql
CREATE TABLE IF NOT EXISTS silver.tickets (
  ticket_id UUID PRIMARY KEY,
  external_id VARCHAR(50),           -- ID en el sistema externo
  source_channel VARCHAR(20) NOT NULL,
  pqrs_type VARCHAR(1) NOT NULL,     -- P, Q, R, S
  priority VARCHAR(10) DEFAULT 'NORMAL',
  created_at TIMESTAMP NOT NULL,     -- cuándo llegó
  radicated_at TIMESTAMP,            -- cuándo se asignó a alguien
  current_status VARCHAR(20) NOT NULL DEFAULT 'RECEIVED',
  geo_id INTEGER,                    -- referencia a `dim_geo` (ubicación con códigos DANE + geo/geom)
  region VARCHAR(50),
  sla_due_at TIMESTAMP,              -- fecha límite del SLA
  closed_at TIMESTAMP,               -- cuándo se cerró (NULL = abierto)
  run_id UUID REFERENCES meta.etl_runs(run_id),
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Ejemplo de datos:**

| ticket_id | pqrs_type | created_at | current_status | sla_due_at | closed_at |
|-----------|-----------|-----------|----------------|-----------|-----------|
| tkt-abc | P | 2026-02-20 10:00 | IN_PROGRESS | 2026-03-02 | NULL |
| tkt-def | Q | 2026-02-19 12:00 | CLOSED | 2026-03-21 | 2026-02-25 |

**¿Por qué distintas tablas en Silver?**

Porque el **negocio piensa en entidades diferentes**:
- "¿Cuántos tickets abiertos?", "¿Quiénes respondieron?", "¿Qué cambios de estado hubo?"

Si todo estuviera en eventos Bronze, el analista tendría que descomponer JSON constantemente.
Silver lo "arma" para facilitar el análisis.

---

### Tabla: `silver.messages`

Línea temporal de **mensajes/respuestas** dentro de cada ticket.

```sql
CREATE TABLE IF NOT EXISTS silver.messages (
  message_id UUID PRIMARY KEY,
  ticket_id UUID NOT NULL REFERENCES silver.tickets(ticket_id),
  ts TIMESTAMP NOT NULL,
  role VARCHAR(10) NOT NULL,         -- AGENT, CITIZEN, SYSTEM, INTERNAL
  text TEXT NOT NULL,
  text_len INTEGER,
  run_id UUID REFERENCES meta.etl_runs(run_id),
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Ejemplo de datos:**

| message_id | ticket_id | ts | role | text | text_len |
|-----------|-----------|----|----|------|----------|
| msg-001 | tkt-abc | 2026-02-20 10:05 | CITIZEN | "Tengo problema con..." | 45 |
| msg-002 | tkt-abc | 2026-02-20 14:00 | AGENT | "Estamos investigando..." | 62 |
| msg-003 | tkt-abc | 2026-02-21 10:00 | CITIZEN | "¿Hay novedades?" | 22 |

**Foreign Key:** `ticket_id REFERENCES silver.tickets(ticket_id)`

Esto significa: "cada mensaje debe pertenecer a un ticket que existe en `silver.tickets`".
Es una **restricción de integridad**: no puedo insertar un mensaje huérfano.

---

### Tabla: `silver.status_events`

Histórico de **cambios de estado** de cada ticket.

```sql
CREATE TABLE IF NOT EXISTS silver.status_events (
  event_id UUID PRIMARY KEY,
  ticket_id UUID NOT NULL REFERENCES silver.tickets(ticket_id),
  ts TIMESTAMP NOT NULL,
  status_from VARCHAR(20),           -- estado anterior
  status_to VARCHAR(20) NOT NULL,    -- estado nuevo
  actor_role VARCHAR(10),            -- quién lo hizo
  reason VARCHAR(255),               -- por qué
  run_id UUID REFERENCES meta.etl_runs(run_id),
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Ejemplo de datos:**

| event_id | ticket_id | ts | status_from | status_to | actor_role | reason |
|----------|-----------|----|----|-------|----------|---------|
| se-001 | tkt-abc | 2026-02-20 10:10 | RECEIVED | RADICATED | SYSTEM | Auto-asignación |
| se-002 | tkt-abc | 2026-02-20 14:00 | RADICATED | IN_PROGRESS | AGENT | Inspector asignado |
| se-003 | tkt-abc | 2026-02-25 16:00 | IN_PROGRESS | CLOSED | AGENT | Problema resuelto |

**Traza completa:**

Con esta tabla, puedes responder: "¿en qué orden pasó este ticket por los estados?"

---

## 6. TABLAS DE DIMENSIONES (silver.dim_*)

Las dimensiones enriquecen los hechos con catálogos pequeños que se pueden
actualizar independientemente. En nuestro caso cargamos seis tablas:

* `dim_channel` – canales de entrada (email, teléfono, web, SMS, etc.).
* `dim_geo` – geografía de Colombia;
  **incluye códigos DANE de departamento y municipio, coordenadas decimales y
  columna `geom` PostGIS** para análisis espacial. Esta tabla permite
  responder preguntas geográficas y unir tickets por ubicación.
* `dim_pqrs_type` – tipos de caso (P, Q, R, S) según Decreto 2649.
* `dim_priority` – niveles de prioridad (Low/Medium/High/Urgent).
* `dim_status` – lista de estados posibles para la máquina de estados.
* `dim_role` – roles de los actores (CIUDADANO, GESTOR, SUPERVISOR, ADMIN).

Algunas notas importantes:

* `dim_geo` se pre‑puebla con ejemplos reales (Bogotá, Soacha, Cali, etc.)
  y se puede completar con los 33 departamentos y 1 100+ municipios.
* Todas las dimensiones usan `UNIQUE` o `PRIMARY KEY`+
  `ON CONFLICT DO NOTHING` para facilitar cargas repetidas.

---

## 7. SCHEMA GOLD: KPIs Agregados

### Tabla: `gold.kpi_volume_daily`

**Recuento diario** de tickets por canal y tipo.

```sql
CREATE TABLE IF NOT EXISTS gold.kpi_volume_daily (
  day DATE NOT NULL,
  channel VARCHAR(20) NOT NULL,
  pqrs_type VARCHAR(1) NOT NULL,
  tickets_count INTEGER NOT NULL DEFAULT 0,
  run_id UUID REFERENCES meta.etl_runs(run_id),
  calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (day, channel, pqrs_type)
);
```

**Ejemplo:**

| day | channel | pqrs_type | tickets_count |
|-----|---------|-----------|---------------|
| 2026-02-25 | email | P | 25 |
| 2026-02-25 | webform | P | 12 |
| 2026-02-25 | email | Q | 18 |

```
Interpretación:
- El 25/02 llegaron 25 Peticiones por email.
- El 25/02 llegaron 12 Peticiones por webform.
```

---

### Tabla: `gold.kpi_backlog_daily`

**Pendientes acumulados** por región y tipo.

```sql
CREATE TABLE IF NOT EXISTS gold.kpi_backlog_daily (
  day DATE NOT NULL,
  pqrs_type VARCHAR(1) NOT NULL,
  region VARCHAR(50) NOT NULL,
  backlog_count INTEGER NOT NULL DEFAULT 0,
  ...
  PRIMARY KEY (day, pqrs_type, region)
);
```

**Ejemplo:**

| day | pqrs_type | region | backlog_count |
|-----|-----------|--------|---------------|
| 2026-02-25 | P | Bogotá | 45 |
| 2026-02-26 | P | Bogotá | 52 |

```
Interpretación:
- Backlog en Bogotá subió de 45 a 52 en un día.
- Entrada > salida: llegan más tickets de los que se cierran.
```

---

### Tabla: `gold.kpi_sla_daily`

**Cumplimiento del SLA** (promesas de tiempo).

```sql
CREATE TABLE IF NOT EXISTS gold.kpi_sla_daily (
  day DATE NOT NULL,
  pqrs_type VARCHAR(1) NOT NULL,
  within_sla_pct NUMERIC(5,2) NOT NULL,
  overdue_count INTEGER NOT NULL DEFAULT 0,
  avg_overdue_days NUMERIC(5,2),
  ...
  PRIMARY KEY (day, pqrs_type)
);
```

**Ejemplo:**

| day | pqrs_type | within_sla_pct | overdue_count | avg_overdue_days |
|-----|-----------|----------------|---------------|------------------|
| 2026-02-25 | P | 92.50 | 3 | 1.2 |
| 2026-02-26 | P | 90.00 | 5 | 1.8 |

```
Interpretación:
- 92.5% de (Peticiones) cumplieron SLA el 25/02.
- 3 peticiones se demoraron de más, en promedio 1.2 días extra.
```

---

## 8. Vistas: "Consultas Guardadas"

Una **vista** es como un "atajo" para una consulta que haces constantemente.

### Vista: `v_tickets_open`

```sql
CREATE OR REPLACE VIEW silver.v_tickets_open AS
SELECT 
  ticket_id,
  pqrs_type,
  priority,
  created_at,
  CURRENT_DATE - created_at::DATE AS days_open,
  CASE 
    WHEN sla_due_at < CURRENT_TIMESTAMP THEN 'OVERDUE'
    WHEN sla_due_at < CURRENT_TIMESTAMP + INTERVAL '2 days' THEN 'AT_RISK'
    ELSE 'HEALTHY'
  END AS sla_status
FROM silver.tickets
WHERE closed_at IS NULL
ORDER BY sla_due_at ASC;
```

**¿Qué hace?**

- Filtra solo tickets abiertos (`closed_at IS NULL`).
- Calcula cuántos días lleva abierto.
- Determina si está en riesgo de incumplir SLA.
- Ordena por fecha de vencimiento (urgentes primero).

**Uso:**

```sql
SELECT * FROM silver.v_tickets_open;
```

Es más fácil que escribir la consulta completa cada vez.

---

### Vista: `v_sla_summary`

```sql
CREATE OR REPLACE VIEW silver.v_sla_summary AS
SELECT 
  pqrs_type,
  COUNT(*) AS total_tickets,
  COUNT(CASE WHEN closed_at IS NOT NULL THEN 1 END) AS closed_tickets,
  ROUND(
    100.0 * COUNT(CASE WHEN closed_at IS NOT NULL THEN 1 END) / COUNT(*),
    2
  ) AS closure_pct
FROM silver.tickets
GROUP BY pqrs_type;
```

**¿Qué hace?**

Resumen por tipo PQRS:
- Total de tickets.
- Cuántos cerrados.
- Porcentaje de cierre.

**Resultado esperado:**

| pqrs_type | total_tickets | closed_tickets | closure_pct |
|-----------|---------------|----------------|-------------|
| P | 100 | 92 | 92.00 |
| Q | 80 | 70 | 87.50 |

---

## 9. Índices: Optimización de Velocidad

### ¿Qué es un índice?

Imagina un libro sin índice:
- Sin índice: tienes que leer página por página para encontrar un tema (lento).
- Con índice: buscas la palabra en el índice y saltas directo (rápido).

En bases de datos es igual.

### Ejemplos en el script:

```sql
CREATE INDEX IF NOT EXISTS idx_tickets_status ON silver.tickets(current_status);
```

Si preguntas "¿cuántos tickets en estado CLOSED?", el índice saltaría directo a los CLOSED.
Sin índice, leyería todos los tickets.

### Índices usados:

- `ticket_id`: búsquedas "dame el ticket X".
- `pqrs_type`: filtros "solo Quejas".
- `status`: consultas "todos los CLOSED".
- `created_at DESC`: "tickets más recientes primero".
- `sla_due_at`: "cuál vence primero".
- `region`: "resultados por región".

---

## 10. Idempotencia: Ejecutar sin miedo

### El problema sin idempotencia:

```sql
CREATE TABLE meta.etl_runs (...)
```

Si ejecutas dos veces:
- 1ª vez: ✅ tabla creada.
- 2ª vez: ❌ ERROR "table already exists".

### La solución: IF NOT EXISTS

```sql
CREATE TABLE IF NOT EXISTS meta.etl_runs (...)
```

Si ejecutas dos veces:
- 1ª vez: ✅ tabla creada.
- 2ª vez: ✅ "ya existe, skip".

**Por qué importa:**

Docker reinicia contenedores constantemente. 
Si el script falla en la 2ª ejecución, el contenedor nunca arranca.
Con `IF NOT EXISTS`, todo es seguro.

---

## 11. Cómo se ejecuta en Docker

### Flujo:

```
1. docker-compose up -d
   ↓
2. Docker arranca contenedor postgres:15
   ↓
3. PostgreSQL inicia y busca en /docker-entrypoint-initdb.d/
   ↓
4. Encuentra init-postgres.sql
   ↓
5. Ejecuta el script línea por línea
   ↓
6. Schemas, tablas, índices, vistas → creados ✅
   ↓
7. Ahora la BD está lista para datos
```

### Verificar que funciona:

```bash
# Conectar a postgres
docker-compose exec postgres psql -U postgres -d pqrs_db

# Dentro de psql:
\dt                          # listar tablas
\dn                          # listar schemas
SELECT * FROM meta.etl_runs; # ver tablas vacías (normalmente)
\q                           # salir
```

---

## 12. Resumen Visual

```
PostgreSQL
│
├─ Schema META (auditoría)
│  ├─ etl_runs (qué se ejecutó)
│  └─ data_quality (pasó validación?)
│
├─ Schema BRONZE (eventos raw tipados)
│  └─ pqrs_events (todos los eventos)
│
├─ Schema SILVER (tablas curadas)
│  ├─ tickets (foto actual)
│  ├─ messages (historial de mensajes)
│  ├─ status_events (qué cambios hubo)
│  ├─ v_tickets_open (vista: urgentes)
│  └─ v_sla_summary (vista: resumen)
│
└─ Schema GOLD (KPIs para dashboard)
   ├─ kpi_volume_daily (recuento)
   ├─ kpi_backlog_daily (pendientes)
   └─ kpi_sla_daily (cumplimiento)
```

---

## 13. Preguntas para tus Estudiantes

### Nivel 1: Concepto

1. ¿Por qué necesitamos un script de inicialización?
   > Para crear toda la estructura antes de guardar datos.

2. ¿Cuál es la diferencia entre `CREATE TABLE` y `CREATE TABLE IF NOT EXISTS`?
   > El segundo es idempotente: no falla si ya existe.

---

### Nivel 2: Estructura

3. ¿Cuántos schemas hay y para qué es cada uno?
   > 4: meta (auditoría), bronze (eventos), silver (curado), gold (KPIs).

4. ¿Por qué Bronze tiene 1 tabla y Silver tiene 3?
   > Bronze es plano (eventos). Silver desnormaliza en entidades de negocio.

---

### Nivel 3: Análisis

5. Si ejecutas el script y luego lo ejecutas otra vez, ¿qué pasa?
   > Nada malo. IF NOT EXISTS hace que sea idempotente.

6. ¿Cómo responderías "¿cuántos tickets Petición sin cerrar en Bogotá?"
   > `SELECT COUNT(*) FROM silver.tickets WHERE pqrs_type='P' AND closed_at IS NULL AND region='Bogotá';`

7. ¿Qué índice usaría PostgreSQL para esa consulta?
   > Probablemente `idx_tickets_pqrs_type` (filtra por tipo primero).

---

### Nivel 4: Crítica

8. ¿Qué pasaría si alguien elimina una fila de `meta.etl_runs`?
   > Las filas de `meta.data_quality` que referenciaban ese run se borran también (CASCADE).

9. ¿Es mala idea tener todo en una sola tabla `bronze.pqrs_events`?
   > No, es buen diseño: eventos son eventos.

10. ¿Podrías cachondeo un evento "ghost" (sin ticket)?
    > En Silver no: hay FK constraint. En Bronze sí, porque no hay FK.

---

## 14. Conclusión

Este script es la **columna vertebral** de tu arquitectura de datos:

- ✅ Organiza en schemas lógicos.
- ✅ Define tablas desnormalizadas para cada propósito.
- ✅ Optimiza con índices estratégicos.
- ✅ Proporciona vistas lista para analistas.
- ✅ Es idempotente y seguro.

Cuando entiendas cómo funciona, verás que todo flujo de datos (Raw → Bronze → Silver → Gold)
tiene su "casa" correspondiente en PostgreSQL.

¡A practicar!
