# ADR-0004 — Motor Big Data: Dask Distributed como compute core

**Estado:** Aceptado  
**Fecha:** 2026-02-18

## Contexto
El curso debe ilustrar procesamiento “Big Data” sin introducir complejidad de Spark.
Se requiere:
- Ejecución paralela/distribuida
- Particionado por day/run_id
- Integración con Python y modelos IA

## Decisión
Adoptar **Dask Distributed** como motor principal:
- 1 Scheduler + N Workers (contenedores)
- ETL por capas lakehouse
- Llamadas a IA dentro de tareas Dask (ver ADR-0007)

## Alternativas consideradas
- Spark: robusto, pero complejo para MVP.
- Pandas/Polars-only: no demuestra cluster distribuido.
- ClickHouse como compute: no es engine ETL general en Python.

## Consecuencias
**Positivas**
- Python-first, ideal para DS/devs.
- Escala horizontal simple en Compose.
- Facilita enseñanza de particionado y paralelismo.

**Negativas**
- Requiere tuning básico (memoria, particiones).
- Requiere buenas prácticas (evitar shuffles innecesarios).

## Notas de implementación
- Estandarizar tamaños de partición (por día/por lotes).
- Centralizar config de endpoint S3 y credenciales.