# ADR-0012 — No Kubernetes en el MVP (Docker Compose) y diseño K8s-ready

**Estado:** Aceptado  
**Fecha:** 2026-02-18

## Contexto
Kubernetes aporta escalamiento y HA, pero el foco del curso es:
- Data Architecture + Lakehouse + Big Data + IA aplicada
y el tiempo es 10 días.

K8s agrega complejidad operativa (networking, PVC, YAML, debugging).

## Decisión
No usar Kubernetes en el MVP. Implementar con Docker Compose.

Aun así, el diseño debe ser “K8s-ready”:
- servicios desacoplados
- compute stateless
- storage externo (S3)
- métricas expuestas
- configuración vía variables de entorno

## Alternativas consideradas
- kind/k3s: añade overhead para poco beneficio en MVP.
- Managed K8s: fuera de alcance.

## Consecuencias
**Positivas**
- Máxima velocidad y reproducibilidad local.
- Menos fricción operativa para estudiantes.
- Foco en datos y no en YAML.

**Negativas**
- No se demuestra auto-escalado real.
- HA no implementada (se explica como evolución).

## Notas de implementación
- Compose con perfiles (core/extended).
- Documentar ruta de migración conceptual a K8s al final del curso.