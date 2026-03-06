# Guía Operativa - Generación de Simulación PQRS

## 1. Objetivo
Generar datos sintéticos PQRS en formato JSONL para el período base:
- Inicio: `2025-09-01`
- Fin: `2026-02-28`

El simulador crea eventos:
- `TICKET_CREATED`
- `MESSAGE_ADDED`
- `STATUS_CHANGED`

con distribución geográfica por `dane_city_code`, canales, tipos PQRS, prioridad y SLA.

## 2. Prerrequisitos
Desde la raíz del repo:

```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse
```

Crear/actualizar entorno:

```bash
make env
```

Validar pruebas:

```bash
make test
```

## 3. Configuración base usada por defecto
Archivo:
- `docs/07-config/pqrs_simulation_v1.yaml`

Parámetros clave:
- `date_range.start: 2025-09-01`
- `date_range.end: 2026-02-28`
- `volume_daily_avg: 1150`
- `channel_probs: email 38%, webform 31%, chat 14%, call 11%, other_digital 6%`
- `sla_business_days: P=15, Q=10, R=8, S=20`
- `geo_probability_csv: data/dane/probabilidad_municipio.csv`

## 4. Ejecución recomendada (run completo)

```bash
python3 apps/simulator/generate_pqrs_data.py \
  --config docs/07-config/pqrs_simulation_v1.yaml \
  --output data/raw/pqrs_events_20250901_20260228.jsonl
```

## 5. Ejecución con rango custom (sin tocar YAML)

```bash
python3 apps/simulator/generate_pqrs_data.py \
  --config docs/07-config/pqrs_simulation_v1.yaml \
  --start-date 2025-10-01 \
  --end-date 2025-10-31 \
  --output data/raw/pqrs_events_202510.jsonl
```

## 6. Verificación rápida del archivo generado

Conteo de líneas:

```bash
wc -l data/raw/pqrs_events_20250901_20260228.jsonl
```

Distribución de tipos de evento:

```bash
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path

p = Path("data/raw/pqrs_events_20250901_20260228.jsonl")
rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
print("events_total:", len(rows))
print("event_types:", dict(Counter(r["event_type"] for r in rows)))
PY
```

## 7. Cómo ver datos en la plataforma (Postgres/Supabase/BI)

### 7.1 Verificar que el stack local esté arriba

```bash
cd infra/local
docker compose -f docker-compose.yml -f docker-compose.supabase.yml ps
```

### 7.2 Consultar tablas analíticas en Postgres

```bash
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c \
"SELECT table_schema, table_name
 FROM information_schema.tables
 WHERE table_schema IN ('bronze','silver','gold')
 ORDER BY 1,2;"
```

Ejemplos de validación de datos cargados:

```bash
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c \
"SELECT COUNT(*) AS bronze_events FROM bronze.pqrs_events;"

docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c \
"SELECT COUNT(*) AS silver_tickets FROM silver.tickets;"

docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -c \
"SELECT day, channel, pqrs_type, tickets_count
 FROM gold.kpi_volume_daily
 ORDER BY day DESC
 LIMIT 20;"
```

### 7.3 Visualizar por UI
- Supabase Studio: `http://localhost:3002`
- Metabase: `http://localhost:3000`
- Streamlit: `http://localhost:8501`

En Supabase Studio:
1. Abrir schema `bronze`, `silver` o `gold`.
2. Revisar `bronze.pqrs_events`, `silver.tickets`, `gold.kpi_volume_daily`.

## 8. Nota importante de operación
El simulador genera `raw` JSONL. Si tu flujo de carga a `bronze/silver/gold` es aparte, debes ejecutar tu pipeline ETL después de la generación para ver tablas pobladas en plataforma.

