# ADR-0010 — Estrategia de carga/serving en Postgres (Gold-only)

**Estado:** Aceptado  
**Fecha:** 2026-02-18

## Contexto
Metabase y Streamlit requieren:
- SQL estable, permisos, gobernanza
- Performance consistente
- Métricas oficiales (no queries ad-hoc sobre capas intermedias)

## Decisión
- Postgres expone **solo** `gold_*` y/o vistas `gold.v_*` como “API analítica”.
- Bronze/Silver no se exponen a BI.
- Carga de Gold a Postgres mediante bulk load (COPY/Parquet->COPY) o inserción por lotes, con estrategia por partición/run_id.

## Alternativas consideradas
- BI directo sobre Parquet: difícil gobernanza y permisos.
- Exponer Silver: riesgo de interpretación inconsistente.
- Cargar todo a Postgres: costo y complejidad innecesarios.

## Consecuencias
**Positivas**
- Gobernanza de métricas y acceso.
- Mejor performance para BI.
- Menos “caos SQL” en el curso.

**Negativas**
- Requiere diseñar tablas/vistas gold con cuidado.

## Notas de implementación
- `gold_*` con claves de partición (day, tenant si aplica).
- Vistas semánticas para Metabase (nombres amigables).