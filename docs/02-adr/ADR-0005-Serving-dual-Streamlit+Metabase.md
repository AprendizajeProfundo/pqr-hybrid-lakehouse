# ADR-0005 — Serving dual: Streamlit + Metabase

**Estado:** Aceptado  
**Fecha:** 2026-02-18

## Contexto
Se requiere:
- Tablero ejecutivo “curado” (storytelling)
- BI autoservicio multiusuario
- Gobierno de métricas y acceso

## Decisión
Implementar serving dual:
- **Streamlit:** tablero ejecutivo (KPIs críticos, narrativa, simulaciones)
- **Metabase:** BI autoservicio sobre **solo** `gold_*` (y/o `gold.v_*`) en Postgres

Ambos consumen Postgres (no leen Parquet directo).

## Alternativas consideradas
- Solo Streamlit: menos autoservicio y menos “enterprise feel”.
- Solo Metabase: menor control narrativo y experiencia demo.
- BI directo sobre Parquet: complica gobernanza y permisos.

## Consecuencias
**Positivas**
- Cobertura completa: demo + exploración.
- Fuerza disciplina de capa Gold.
- Separación clara de audiencias.

**Negativas**
- Dos herramientas UI; requiere definir “fuente de verdad” (Gold).

## Notas de implementación
- Metabase conectado a esquema controlado `gold`.
- Streamlit usa vistas/consultas definidas (no SQL libre en producción del curso).