# ADR-0014 — Hoja de Ruta Fase 2: Evolución a Lakehouse Transaccional y Escalamiento

**Estado:** Aceptado (Plan de Evolución)  
**Fecha:** 2026-02-18  
**Tipo:** ADR Estratégico de Arquitectura

---

## 1. Contexto

El PQR Hybrid Lakehouse MVP implementa un lakehouse minimalista basado en:

- RustFS (S3-compatible)
- Parquet (Raw/Bronze/Silver/Gold)
- Dask Distributed
- DuckDB
- Postgres (serving)
- Prefect
- Prometheus/Grafana

El MVP prioriza:

- Claridad arquitectónica
- Reproducibilidad
- Separación Control/Data/Compute
- IA aplicada en Silver
- Implementación en 10 días

Sin embargo, el diseño debe permitir evolucionar sin reescritura radical hacia:

- Lakehouse transaccional
- Escalamiento multi-tenant
- Procesamiento near-real-time
- Gobierno avanzado
- Query federation

---

## 2. Objetivo de Fase 2

Convertir el MVP en una plataforma de datos avanzada manteniendo:

- Layout físico compatible
- Separación de planos
- Gobierno por run_id
- Capas lakehouse

Sin rehacer:

- Modelo de datos
- Layout de particiones
- Lógica conceptual por capas
- Control plane

---

## 3. Decisiones para compatibilidad futura (Backwards-Compatible Design)

### 3.1 Layout S3 inmutable

El layout actual:

Debe mantenerse estable.

Fase 2 podrá:
- Registrar snapshots tabulares
- Agregar metadata layer (Iceberg/Delta)
- Mantener compatibilidad física

No se cambiará la organización conceptual Raw/Bronze/Silver/Gold.

---

### 3.2 Mantener Parquet como formato base

Fase 2 puede agregar:

- Iceberg metadata
- Delta transaction log

Pero el almacenamiento físico seguirá siendo Parquet.

Esto evita migraciones masivas de datos.

---

### 3.3 Separación clara de IA en Silver

Permite:

- Versionamiento de modelo
- Time travel semántico
- Comparación entre modelos

Fase 2 podrá:
- Agregar model registry
- Agregar tracking ML (MLflow)
- Versionar outputs Silver

Sin rediseñar pipeline.

---

### 3.4 Control Plane estable

Postgres seguirá siendo:

- Registro de runs
- Gobierno
- Serving Gold

Fase 2 podrá:
- Introducir catálogo tabular
- Integrar federated query engine (Trino)

Sin eliminar Postgres.

---

## 4. Evoluciones previstas en Fase 2

### 4.1 Lakehouse Transaccional

Posible incorporación de:

- Apache Iceberg
- Delta Lake
- Trino como federated query engine

Objetivos:
- Snapshot isolation
- Time travel
- Schema evolution avanzada
- Compaction automática

---

### 4.2 Escalamiento Compute

Opciones futuras:

- Kubernetes (K8s)
- Auto-scaling Dask
- Spark como motor alternativo
- Separación de clusters por tenant

---

### 4.3 Multi-Tenancy

Evolución hacia:

- Particiones por tenant
- Aislamiento lógico
- Métricas por cliente
- SLAs diferenciados

---

### 4.4 Streaming / Near Real-Time

Posible incorporación de:

- Kafka / Redpanda
- Micro-batch Dask
- Procesamiento incremental

Manteniendo lakehouse como destino final.

---

### 4.5 Gobierno Avanzado

Fase 2 puede incorporar:

- Data catalog
- Lineage automático
- Data contracts enforcement automatizado
- Policy-as-code

---

## 5. Decisiones explícitas para evitar retrabajo

El MVP debe:

- No hardcodear rutas físicas
- No acoplar Dask a estructura rígida
- No mezclar serving con Silver
- No usar estructuras que Iceberg no pueda mapear
- No depender de estado mutable en lakehouse

---

## 6. Qué NO cambia en Fase 2

- Concepto Raw/Bronze/Silver/Gold
- run_id como unidad de reproducibilidad
- Separación Control/Data/Compute
- Gold como API analítica oficial
- Observabilidad obligatoria

---

## 7. Principio Rector de Evolución

> Fase 2 debe extender la arquitectura, no reemplazarla.

El MVP es una base correcta, no un prototipo descartable.

---

## 8. Visión Arquitectónica a Largo Plazo

MVP (actual):
Lakehouse manual gobernado + Dask + Postgres

Fase 2:
Lakehouse transaccional + catálogo + federated query + auto-scaling

Fase 3 (opcional):
Plataforma multi-tenant SaaS con aislamiento fuerte y gobierno automatizado

---

## 9. Conclusión

El MVP no es una solución simplificada que deba ser descartada.

Es una base arquitectónica consciente que:

- Puede escalar
- Puede incorporar Iceberg/Delta
- Puede migrar a K8s
- Puede integrar streaming
- Puede soportar múltiples clientes

Sin reescritura conceptual.

---

End of ADR.