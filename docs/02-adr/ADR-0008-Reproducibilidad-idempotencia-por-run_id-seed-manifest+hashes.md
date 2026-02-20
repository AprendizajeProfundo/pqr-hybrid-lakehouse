# ADR-0008 — Reproducibilidad e idempotencia por run_id/seed/manifest (+ hashes)

**Estado:** Aceptado  
**Fecha:** 2026-02-18

## Contexto
El sistema debe soportar:
- Re-ejecución exacta (misma semilla)
- Auditoría por corrida
- Retries sin duplicación
- Evidencias de inputs/outputs

## Decisión
Toda corrida requiere:
- `run_id` (UUID) obligatorio
- `seed` determinístico para el generador (si aplica)
- `manifest.json` con parámetros, conteos, rutas, checksums
- hashes mínimos (al menos del manifest; idealmente de artefactos críticos)
- Outputs particionados por `run_id` y *no* sobrescritos

Política de idempotencia:
- Re-run del mismo run_id no debe duplicar ni corromper; se controla por partición y/o “replace partition”.

## Alternativas consideradas
- Corridas sin run_id: no auditables.
- Sobrescritura de datasets: rompe trazabilidad.
- Idempotencia “manual”: frágil.

## Consecuencias
**Positivas**
- Auditoría y trazabilidad robustas.
- Operación segura ante fallos.
- Comparación entre runs y versiones.

**Negativas**
- Overhead de metadatos (aceptable y didáctico).

## Notas de implementación
- Registrar en `meta.runs` (start/end/status/params).
- Guardar manifest en RustFS junto a Raw.