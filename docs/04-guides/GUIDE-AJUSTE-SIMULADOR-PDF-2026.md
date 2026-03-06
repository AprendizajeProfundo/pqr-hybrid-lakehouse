# GUIDE - Ajuste Simulador vs Documento Base (2026-02-07)

## Objetivo
Alinear la simulación PQRS al documento base académico:
- Volumen histórico diario: 1150.
- Picos coyunturales: 3000-4000 por 5-10 días.
- Canales: 38/31/14/11/6.
- SLA hábil por tipo: P=15, Q=10, R=8, S=20.
- Distribución geográfica municipal por probabilidad DANE.

## Cambios aplicados en código
- `apps/simulator/generate_pqrs_data.py`
  - Lee `data/dane/probabilidad_municipio.csv` (delimitador `;`).
  - Selecciona municipio con muestreo ponderado por `probability`.
  - Incluye `dane_city_code` en el payload del ticket.
  - Genera eventos de ciclo de vida: `TICKET_CREATED`, `MESSAGE_ADDED`, `STATUS_CHANGED`.
  - Calcula `sla_due_at` por días hábiles según tipo PQRS.
  - Soporta canal adicional `other_digital`.

## Cambios de contrato y SQL
- `data/contracts/v1/RAW-PQRS.schema.json`
  - Se agrega `other_digital` al enum de `source_channel`.
- `infra/local/init-scripts/init-postgres.sql`
  - Se agrega `other_digital` a `silver.dim_channel`.
  - Se actualizan SLA default de `silver.dim_pqrs_type` a 15/10/8/20.
- `infra/local/init-scripts/020-align-pdf-baseline.sql`
  - Migración idempotente para stacks ya inicializados.

## Ejecutar migración en stack ya levantado

```bash
docker exec -i local-postgres-1 psql -U postgres -d pqr_lakehouse \
  < infra/local/init-scripts/020-align-pdf-baseline.sql
```

## Verificación rápida

```bash
docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -Atc \
  "select channel_name from silver.dim_channel order by 1;"

docker exec local-postgres-1 psql -U postgres -d pqr_lakehouse -Atc \
  "select pqrs_code,sla_days_default from silver.dim_pqrs_type order by 1;"
```

## Nota
El CSV de probabilidades se consolida por `dane_city_code` dentro del simulador para manejar duplicados de fuente de forma determinista.
