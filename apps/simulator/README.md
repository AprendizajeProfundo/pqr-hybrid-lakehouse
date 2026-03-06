# apps/simulator/

Esta carpeta contiene el código Python para generar datos sintéticos PQRS.

- `generate_pqrs_data.py`: Script principal para simulación determinista (volumen histórico, picos, canales, geo y SLA).
- `models/`: Modelos de datos y esquemas.
- `utils/`: Utilidades para Faker, seeds, etc.

## Simulación principal (rango de fechas)

Genera eventos `TICKET_CREATED`, `MESSAGE_ADDED` y `STATUS_CHANGED`:

```bash
python3 apps/simulator/generate_pqrs_data.py \
  --config docs/07-config/pqrs_simulation_v1.yaml \
  --output data/raw/pqrs_events.jsonl
```

Características implementadas:
- Distribución geográfica ponderada desde `data/dane/probabilidad_municipio.csv` (`dane_city_code`).
- Volumen histórico diario base `1150` con picos configurables `3000-4000` por `5-10` días.
- Distribución por canal: `email 38%`, `webform 31%`, `chat 14%`, `call 11%`, `other_digital 6%`.
- SLA por tipo (días hábiles): `P=15`, `Q=10`, `R=8`, `S=20`.

## Modo rápido (smoke)

Solo genera eventos `TICKET_CREATED`:

```bash
python3 apps/simulator/generate_pqrs_data.py --count 50 --seed 42
```
