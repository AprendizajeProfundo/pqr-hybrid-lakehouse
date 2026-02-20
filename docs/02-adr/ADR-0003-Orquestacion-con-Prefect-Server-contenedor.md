# ADR-0003 — Orquestación con Prefect Server (contenedor)

**Estado:** Aceptado  
**Fecha:** 2026-02-18

## Contexto
Se requiere:
- Scheduling/retries
- Estados de corridas y visibilidad (UI)
- Integración con Dask
- Operación didáctica “real” sin overhead excesivo

## Decisión
Usar **Prefect Server** desplegado en Docker Compose como orquestador del MVP.

Prefect será responsable de:
- Disparar flujos end-to-end (Raw→Bronze→Silver→Gold→Load)
- Reintentos controlados e idempotentes
- Registro básico de estado (y/o sincronización con meta.*)

## Alternativas consideradas
- Airflow: potente, pero pesado para 10 días.
- Dagster: excelente, pero curva mayor.
- Cron + scripts: sin estados, retries ni UI.
- “Solo Dask”: carece de scheduling y semántica de runs.

## Consecuencias
**Positivas**
- UI moderna y control operativo.
- Integración natural con Dask.
- Alineado con restricciones de tiempo.

**Negativas**
- Servicio adicional; requiere configuración inicial y runbook.

## Notas de implementación
- Definir flows por etapa + flow end-to-end.
- Política de retries: fail-fast en checks críticos, retries acotados.