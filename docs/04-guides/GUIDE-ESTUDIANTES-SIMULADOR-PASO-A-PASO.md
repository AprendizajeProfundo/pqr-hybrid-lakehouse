# Guía para Estudiantes - Simulador PQRS paso a paso

## 1. ¿Qué hace este código?
Archivo principal:
- `apps/simulator/generate_pqrs_data.py`

Su objetivo es crear datos sintéticos de PQRS para practicar arquitectura de datos:
1. Genera tickets por día.
2. Asigna canal, tipo PQRS, prioridad y municipio.
3. Calcula tiempos y SLA.
4. Emite eventos de ciclo de vida en JSONL.

## 2. Flujo lógico del simulador

### Paso 1: Cargar configuración
La función `main()`:
- lee `--config`
- usa `seed`
- acepta rango por `--start-date` y `--end-date`
- escribe en `--output`

Si no se pasan fechas por CLI, toma `date_range` del YAML.

### Paso 2: Preparar probabilidades y catálogos
`generate_simulation_events(...)`:
- normaliza probabilidades de canales/tipos/prioridades.
- carga geografía desde `probabilidad_municipio.csv`.
- arma diccionario de SLA por tipo PQRS.

### Paso 3: Construir calendario del run
Con `date_range`:
- crea la lista de días del período.
- para cada día calcula volumen base (1150 promedio).
- aplica picos coyunturales (3000-4000 por ventanas consecutivas).

### Paso 4: Generar cada ticket
Por ticket:
1. crea `ticket_id` y `external_id`.
2. selecciona:
- `source_channel` (probabilístico)
- `pqrs_type` (probabilístico)
- `priority` (probabilístico)
- municipio por `dane_city_code` (probabilístico)
3. genera texto semántico (tema + preclasificador sintético).
4. calcula tiempos (`radicated_at`, `responded_at`, `closed_at`, `sla_due_at`).

### Paso 5: Emitir eventos
Por ticket se crean:
- 1 `TICKET_CREATED`
- 2 `MESSAGE_ADDED` (ciudadano/agente)
- varios `STATUS_CHANGED` (RECEIVED -> ... -> ARCHIVED)

Todos se ordenan por `ts` y se guardan en JSONL.

## 3. Estructura mínima de un evento
Cada línea del JSONL es un objeto:
- `event_id`
- `ticket_id`
- `event_type`
- `ts`
- `data`

Ejemplo conceptual:
- `event_type = TICKET_CREATED`
- `data` incluye `source_channel`, `pqrs_type`, `priority`, `dane_city_code`, `sla_due_at`.

## 4. Cómo ejecutar en clase

Desde raíz del repo:

```bash
make env
make test
```

Simulación completa del período base:

```bash
python3 apps/simulator/generate_pqrs_data.py \
  --config docs/07-config/pqrs_simulation_v1.yaml \
  --output data/raw/pqrs_events_20250901_20260228.jsonl
```

Simulación corta para laboratorio:

```bash
python3 apps/simulator/generate_pqrs_data.py \
  --config docs/07-config/pqrs_simulation_v1.yaml \
  --start-date 2025-09-01 \
  --end-date 2025-09-03 \
  --output data/raw/pqrs_events_lab_3dias.jsonl
```

## 5. Qué validar después de ejecutar

### Validación 1: Se creó el archivo

```bash
ls -lh data/raw/pqrs_events_20250901_20260228.jsonl
```

### Validación 2: Tipos de eventos esperados

```bash
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path

rows = [json.loads(x) for x in Path("data/raw/pqrs_events_20250901_20260228.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
print(dict(Counter(r["event_type"] for r in rows)))
PY
```

### Validación 3: Canal adicional `other_digital`

```bash
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path

rows = [json.loads(x) for x in Path("data/raw/pqrs_events_20250901_20260228.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
created = [r for r in rows if r["event_type"] == "TICKET_CREATED"]
print(dict(Counter(r["data"]["source_channel"] for r in created)))
PY
```

## 6. ¿Cómo ver datos en la plataforma?
Una vez corras tu ETL de carga a DB, revisa:

### SQL directo

```bash
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c \
"SELECT COUNT(*) FROM bronze.pqrs_events;"

docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c \
"SELECT COUNT(*) FROM silver.tickets;"

docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c \
"SELECT * FROM gold.kpi_volume_daily ORDER BY day DESC LIMIT 10;"
```

### UIs
- Supabase Studio: `http://localhost:3002` (explorar tablas)
- Metabase: `http://localhost:3000` (gráficas y consultas)
- Streamlit: `http://localhost:8501` (dashboard ejecutivo)

## 7. Preguntas frecuentes para clase
- ¿Por qué usar `seed`?
Permite reproducibilidad: mismo seed, mismos datos.

- ¿Por qué JSONL?
Es simple para eventos y fácil de ingerir en pipelines.

- ¿Por qué el SLA está en días hábiles?
Porque representa el compromiso operativo real de PQRS.

