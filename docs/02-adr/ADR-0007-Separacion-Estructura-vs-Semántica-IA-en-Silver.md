# ADR-0007 — Separación Estructura vs Semántica: IA en Silver (no en Bronze)

**Estado:** Aceptado  
**Fecha:** 2026-02-18

## Contexto
El pipeline incorpora extracción semántica desde correos (clasificación, entidades, prioridad).
Si se mezcla IA con Bronze se pierde claridad, reproducibilidad y capacidad de debugging.

## Decisión
- **Bronze:** transformaciones mecánicas/deterministas (parseo, tipado, normalización mínima)
- **Silver:** enriquecimiento semántico con IA (PQRS type, entidades, prioridad, resumen opcional, embeddings opcional)

Se registra `model_version` y (si aplica) `prompt_version`/`pipeline_version` en Silver y meta.*

## Alternativas consideradas
- IA en Bronze: mezcla responsabilidades; dificulta re-ejecución por versión de modelo.
- IA “a demanda” en serving: penaliza performance y trazabilidad.

## Consecuencias
**Positivas**
- Reproducibilidad y comparabilidad entre versiones de modelo.
- Debugging claro: fallos estructurales vs semánticos.
- Gobierno de modelos y auditoría más sólida.

**Negativas**
- Silver se vuelve más “pesado” (pero es el lugar correcto).

## Notas de implementación
- Silver incluye campos: `pqrs_type`, `entities_json`, `priority_score`, `model_version`, `inference_timestamp`.