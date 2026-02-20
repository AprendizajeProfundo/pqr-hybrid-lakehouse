# ADR-0011 — Estrategia de calidad de datos (checks por capa + política de fallo)

**Estado:** Aceptado  
**Fecha:** 2026-02-18

## Contexto
El sistema debe ser confiable y operable:
- Detectar errores temprano
- Evitar cargar Gold incorrecto
- Proveer evidencia de calidad por corrida

## Decisión
Implementar checks mínimos por etapa y registrar resultados en `meta.quality_checks`.

Checks típicos:
- Conteos in/out
- Duplicados por `event_id`/`message_id`
- Nulos críticos
- Distribución por tipo PQRS (drift simple)
- Validación de schema (ADR-0009)

Política:
- Checks críticos -> estado `FAILED` (fail-fast)
- Checks no críticos -> estado `DEGRADED` con advertencias

## Alternativas consideradas
- Validar solo al final: debugging costoso.
- Sin checks: BI no confiable.

## Consecuencias
**Positivas**
- Operación robusta y auditable.
- Enseña calidad como parte del producto.
- Reduce errores silenciosos.

**Negativas**
- Requiere mantenimiento de reglas de calidad.

## Notas de implementación
- Integrar checks como tasks en Prefect.
- Exponer métricas de checks en Grafana.