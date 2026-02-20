# PQR Hybrid Lakehouse MVP
## ARCH-PRINCIPLES.md — Principios Arquitectónicos

---

## 1. Separación estricta de planos (Control / Data / Compute)

La arquitectura se fundamenta en una separación explícita de responsabilidades.

### 1.1 Control Plane (Supabase / PostgreSQL)

Responsabilidades:

- Autenticación y RBAC
- Estado operativo (core.*)
- Metadatos de gobierno (meta.runs, meta.lineage, meta.quality_checks)
- Capa de serving (gold_*)

Regla:
> El plano de control gobierna el sistema, pero no almacena histórico crudo.

---

### 1.2 Data Plane (RustFS – S3 Compatible)

Responsabilidades:

- Lakehouse por capas: Raw, Bronze, Silver, Gold
- Almacenamiento inmutable de eventos
- Evidencias por run_id (manifest + hashes)
- Particionamiento estructurado (source/day/run_id)

Regla:
> RustFS es la fuente histórica de verdad.

---

### 1.3 Compute Plane

Se compone de tres roles diferenciados:

#### Dask Distributed (Motor Principal)

- Paralelización distribuida
- Transformación Raw → Bronze
- Enriquecimiento Bronze → Silver
- Agregación Silver → Gold

Dask coordina y ejecuta, pero no persiste estado de negocio.

---

#### AI Enrichment Layer (Ubicada en Silver)

Responsabilidades:

- Clasificación PQRS
- Extracción de entidades
- Estimación de prioridad
- Resumen opcional
- Generación de embeddings (extensible)

Principio:
> La IA no modifica la estructura mecánica del dato (Bronze).
> La IA agrega semántica (Silver).

---

#### DuckDB (OLAP sobre Parquet)

Responsabilidades:

- Consultas analíticas sobre Parquet
- Agregaciones rápidas
- Demostración de “query engine over lakehouse”

Principio:
> DuckDB complementa Dask; no lo reemplaza.

---

#### Polars (Motor opcional intra-partición)

Responsabilidades:

- Transformaciones de alto rendimiento en desarrollo local
- Benchmark frente a Dask
- Optimización dentro de tareas Dask

Principio:
> Polars es acelerador local, no motor distribuido primario.

---

## 2. Event-First Modeling

Todo se modela como evento:

- Email recibido → evento Raw
- Actualización de ticket → evento operativo
- Cambios de SLA → derivado de eventos

Principio:
> El sistema debe poder reconstruirse desde eventos.

---

## 3. Raw es Inmutable

Raw representa:

- Lo que llegó
- Sin interpretación
- Sin clasificación
- Sin enriquecimiento

Características:

- JSONL
- Append-only
- Versionado por run_id
- Manifest asociado

Principio:
> Raw nunca se reescribe.

---

## 4. Separación entre Estructura y Semántica

Bronze:

- Tipado
- Normalización mecánica
- Campos derivados determinísticos

Silver:

- Interpretación semántica
- IA
- Enriquecimiento

Principio:
> Nunca mezclar parseo estructural con interpretación semántica.

---

## 5. Reproducibilidad Científica

Cada corrida incluye:

- run_id (UUID)
- seed determinístico
- manifest.json
- registro en meta.runs
- version de modelo IA

Principio:
> Toda corrida debe ser reproducible.

---

## 6. Idempotencia Operativa

Reintentos no deben:

- Duplicar datos
- Corromper Gold
- Alterar histórico Raw

Estrategia:

- Particiones por run_id
- Cargas controladas en Postgres
- Registros explícitos de estado

Principio:
> Retry seguro por diseño.

---

## 7. Lakehouse Estricto por Capas

Raw → Bronze → Silver → Gold

Reglas:

- No saltar capas
- No hacer dashboards sobre Bronze
- Gold es la API analítica oficial

Principio:
> La arquitectura enseña disciplina de datos.

---

## 8. Observabilidad desde el Día 1

Componentes obligatorios:

- Métricas de duración por etapa
- Conteos in/out
- Fallos y retries
- Indicadores SLA

Principio:
> No hay sistema serio sin métricas.

---

## 9. Gobernanza de Datos Integrada

Se registra:

- Lineage
- Quality checks
- Model version
- Parámetros de corrida

Principio:
> Gobierno antes que visualización.

---

## 10. Simplicidad Estructural

Restricciones del MVP:

- Docker Compose
- Sin Kubernetes
- Sin Spark
- Sin Cassandra

Principio:
> Minimizar complejidad sin sacrificar arquitectura.

---

## 11. Diseño Kubernetes-Ready (Sin Implementarlo)

Aunque no se implementa Kubernetes:

- Servicios son desacoplados
- Compute es stateless
- Storage es externo
- Métricas son expuestas

Principio:
> Arquitectura lista para escalar, pero enfocada en datos.

---

## 12. Enseñabilidad como Criterio Arquitectónico

La arquitectura debe poder:

- Explicarse con C4
- Implementarse en 10 días
- Ejecutarse end-to-end
- Demostrarse con evidencia operativa

Principio:
> Si no puede enseñarse con claridad, debe simplificarse.

---

## 13. Prioridad del Enfoque

El foco del proyecto es:

> Data Architecture + Lakehouse + Big Data + IA aplicada

No:

- Platform Engineering pesado
- Infraestructura de orquestación avanzada
- DevOps complejo

---

End of document.