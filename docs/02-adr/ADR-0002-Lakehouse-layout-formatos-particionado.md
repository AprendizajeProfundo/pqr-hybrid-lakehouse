# ADR-0002 — Lakehouse: layout, formatos y particionado

**Estado:** Aceptado  
**Fecha:** 2026-02-18

## Contexto
El sistema necesita almacenamiento histórico reproducible y eficiente para big data:
- Raw inmutable para auditoría
- Capas Parquet para procesamiento/consulta
- Particionado determinístico para re-ejecución e idempotencia

## Decisión
Implementar lakehouse por capas en RustFS:

- **Raw:** JSONL + manifest + hashes (append-only)
- **Bronze:** Parquet tipado, normalización mecánica
- **Silver:** Parquet curado + enriquecimiento IA
- **Gold:** Parquet agregados + carga a Postgres (gold_*)

**Particionado estándar:** `source=<...>/day=YYYY-MM-DD/run_id=<...>/`

## Alternativas consideradas
- Guardar todo en Postgres: caro e ineficiente para histórico y adjuntos.
- Formatos no columnar (CSV): pobre rendimiento analítico.
- Iceberg/Delta: útil, pero aumenta complejidad para MVP.

## Consecuencias
**Positivas**
- Rendimiento y costos coherentes con lakehouse.
- Trazabilidad por run_id.
- Facilita Dask y DuckDB sobre Parquet.

**Negativas**
- Requiere rigor en naming, particiones y control de schemas.
- Requiere tooling de validación en pipeline.

## Notas de implementación
- `Raw` debe ser append-only; nunca reescribir.
- Parquet con `pyarrow` y metadatos de run/model_version en Silver.