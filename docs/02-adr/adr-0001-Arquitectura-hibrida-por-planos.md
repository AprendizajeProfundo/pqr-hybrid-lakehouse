# ADR-0001 — Arquitectura híbrida por planos (Control/Data/Compute)

**Estado:** Aceptado  
**Fecha:** 2026-02-18

## Contexto
El MVP debe simular un sistema híbrido “real” en 10 días, con separación nítida entre:
- Gobierno/operación (estado y permisos)
- Persistencia histórica reproducible
- Cómputo escalable para procesamiento Big Data
- Serving para BI y tablero ejecutivo
- Observabilidad operativa

Se requiere arquitectura didáctica, auditable y extensible.

## Decisión
Adoptar una arquitectura por planos:

- **Control Plane:** Supabase/PostgreSQL (Auth+RBAC, core.*, meta.*, gold_* serving)
- **Data Plane:** RustFS (S3-compatible) como lakehouse (Raw/Bronze/Silver/Gold)
- **Compute Plane:** Dask Distributed (ETL por capas) + DuckDB (OLAP sobre Parquet)
- **Orquestación:** Prefect Server (container)
- **Observabilidad:** Prometheus + Grafana
- **Serving:** Streamlit (tablero ejecutivo curado) + Metabase (BI autoservicio)

## Alternativas consideradas
- Monolito (solo Postgres + scripts): pierde trazabilidad y escala didáctica.
- Solo lakehouse sin carga a Postgres: complica BI y gobierno de acceso.
- Spark como compute core: mayor complejidad operativa para 10 días.
- Airflow como orquestador: overhead alto para MVP.

## Consecuencias
**Positivas**
- Separación de responsabilidades y claridad pedagógica.
- Gobernanza y trazabilidad de corridas.
- Diseño listo para escalar sin re-trabajo conceptual.

**Negativas**
- Más servicios que un demo simple; requiere docker-compose bien mantenido.
- Requiere disciplina en contratos, particiones y meta-registros.

## Notas de implementación
- Definir esquemas `core`, `meta`, `gold` en Postgres.
- Definir layout S3 por `source/day/run_id`.
- Formalizar métricas y checks desde el inicio.