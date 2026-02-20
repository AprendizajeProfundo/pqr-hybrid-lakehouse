# ADR-0006 — Observabilidad: Prometheus + Grafana (Loki opcional)

**Estado:** Aceptado  
**Fecha:** 2026-02-18

## Contexto
El MVP debe operar como sistema real:
- Duración por etapa
- Throughput
- Errores/retries
- Indicadores de SLA

## Decisión
Adoptar:
- **Prometheus** para métricas
- **Grafana** para dashboards y alertas
- **Loki**  para logs centralizados

## Alternativas consideradas
- Sin observabilidad: no operable.
- Logs solamente: insuficiente para SLAs/metrics.
- Stack cloud: fuera del alcance MVP.

## Consecuencias
**Positivas**
- Operación profesional y medible.
- Enseña SLO/SLA y performance.
- Facilita troubleshooting.

**Negativas**
- Requiere configurar exporters/metrics endpoints.

## Notas de implementación
- Métricas mínimas: job_duration, records_in/out, failures, retries, sla_breaches.