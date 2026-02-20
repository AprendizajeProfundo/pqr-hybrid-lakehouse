# ADR-0013 — No utilizar Iceberg / Delta Lake / Hudi en el MVP

**Estado:** Aceptado  
**Fecha:** 2026-02-18  
**Decisión estratégica del MVP**

---

## 1. Contexto

El proyecto PQR Hybrid Lakehouse MVP implementa una arquitectura lakehouse sobre:

- RustFS (S3-compatible)
- Parquet (Bronze / Silver / Gold)
- Dask Distributed (compute)
- DuckDB (OLAP)
- Postgres (serving controlado)

En arquitecturas lakehouse modernas, herramientas como:

- Apache Iceberg
- Delta Lake
- Apache Hudi

son comúnmente utilizadas para agregar:

- ACID transactions sobre S3
- Snapshot isolation
- Time travel
- Schema evolution avanzada
- Compaction automática
- Hidden partitioning
- Catálogos transaccionales

La pregunta arquitectónica es si deben incluirse en el MVP.

---

## 2. Decisión

**No incorporar Iceberg, Delta Lake ni Hudi en el MVP de 10 días.**

El lakehouse del MVP será:

- Parquet-based
- Particionado explícito (`source/day/run_id`)
- Gobernado por manifest + run_id + hashes
- Idempotente por diseño
- Carga controlada a Postgres para serving

---

## 3. Justificación técnica

### 3.1 Enfoque del MVP

El objetivo del proyecto es:

> Enseñar arquitectura de datos híbrida, gobierno, reproducibilidad e IA aplicada.

No es:

- Construir una plataforma transaccional ACID sobre S3
- Enseñar internals de motores tabulares lakehouse

Incorporar Iceberg/Delta desplazaría el foco del curso hacia:

- Catálogos
- Metadatos distribuidos
- Compaction
- Versionado snapshot

lo cual no es el objetivo central.

---

### 3.2 Complejidad operativa

Iceberg/Delta requieren típicamente:

- Spark / Trino / Flink
- Catálogo (Hive / Glue)
- Gestión de snapshots
- Manejo de compaction
- Configuración adicional de metadatos

Esto introduce:

- Mayor superficie de fallo
- Mayor tiempo de debugging
- Mayor carga cognitiva para estudiantes

Para un MVP de 10 días, el costo/beneficio es negativo.

---

### 3.3 Reproducibilidad ya cubierta

El MVP implementa reproducibilidad mediante:

- `run_id` obligatorio
- `seed` determinístico
- `manifest.json`
- particiones por run
- control de carga a Postgres
- registros en `meta.runs`

Para el alcance del proyecto:

> No se requiere snapshot isolation multi-writer ni time-travel automático.

La trazabilidad se logra por diseño, sin necesidad de tabla transaccional avanzada.

---

### 3.4 Control explícito vs abstracción SaaS

El proyecto busca que los estudiantes comprendan:

- Layout físico del lakehouse
- Particionado real
- Estrategias de idempotencia
- Gobierno explícito

Iceberg/Delta abstraen parte de estas decisiones.

Para fines pedagógicos:

> Es preferible primero entender el lakehouse “manual”, antes de usar una capa transaccional.

---

## 4. Alternativas consideradas

### A. Usar Delta Lake con Spark

Rechazado por:

- Mayor complejidad
- Dependencia fuerte de Spark
- Desplazamiento del foco del curso

### B. Usar Iceberg con Trino

Rechazado por:

- Requiere catálogo adicional
- Añade capa infra innecesaria en MVP

### C. No usar lakehouse (solo Postgres)

Rechazado por:

- No representa arquitectura moderna
- No permite demostrar separación Data/Compute

---

## 5. Consecuencias

### Positivas

- Arquitectura clara y didáctica
- Control explícito del layout
- Implementación en 10 días viable
- Menor complejidad operativa
- Enfoque centrado en datos e IA

### Negativas

- No hay time travel automático
- No hay snapshot isolation multi-writer
- No hay compaction automática
- No se demuestra ACID sobre S3

Estas limitaciones son aceptadas conscientemente dentro del alcance del MVP.

---

## 6. Evolución futura (Fase 2)

En una segunda fase del proyecto podría evaluarse:

- Integrar Iceberg como capa tabular
- Introducir Trino como query engine federado
- Enseñar time travel y schema evolution avanzada
- Comparar lakehouse manual vs transaccional

Esta evolución sería explícitamente una ampliación del alcance, no una corrección del MVP.

---

## 7. Principio rector

> El MVP prioriza claridad arquitectónica, reproducibilidad y valor pedagógico por encima de sofisticación infraestructural.

---

End of ADR.