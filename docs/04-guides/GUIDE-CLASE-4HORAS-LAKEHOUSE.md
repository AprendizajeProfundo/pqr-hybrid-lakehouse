# Guía de Clase: Arquitectura Híbrida Lakehouse para PQRS (4 Horas)

**Objetivo:** Introducir a los estudiantes al diseño, propósito y levantamiento local de una arquitectura de datos moderna K8s-ready, separando conceptualmente almacenamiento, cómputo, control y visualización.

**Duración:** 4 horas académicas.

---

## 🕒 Bloque 1: Introducción Teórica y Contexto del Proyecto (1 hora)

**Objetivo:** Entender *por qué* estamos construyendo esto y qué arquitectura subyace (ADR).

1. **Contexto del Problema (15 min)**
   - Caso de estudio: Sistema PQRS a gran escala.
   - ¿Por qué un Data Warehouse tradicional o un Data Lake puro no bastan? (El nacimiento del Lakehouse).

2. **La Arquitectura por Planos (25 min)**
   - Explicación de la separación de responsabilidades:
     - **Control Plane:** Gestión de metadatos, calidad y orquestación.
     - **Data Plane:** Almacenamiento crudo y refinado (Parquet/Delta).
     - **Compute Plane:** Procesamiento distribuido (Jobs).
     - **Serving Plane:** Dashboards y consumo final.
   - [👉 Ver ADR-0001: Separación de Planos de Arquitectura](../../docs/01-architecture/ADRs/ADR-0001-separacion-planos-arquitectura.md)

3. **Filosofía Cloud-Native y K8s-ready (20 min)**
   - El concepto de no depender del hardware local.
   - ¿Por qué usamos Docker Compose hoy si mañana iremos a la nube?
   - [👉 Ver Guía Conceptual: De Local a la Nube](GUIDE-MIGRATION-LOCAL-TO-CLOUD.md)

---

## 🕒 Bloque 2: Inmersión en el Diseño Desacoplado (1 hora)

**Objetivo:** Navegar el repositorio y entender cómo el código refleja la teoría de planos.

1. **Estructura del Proyecto (15 min)**
   - Paseo guiado por las carpetas: `/apps`, `/infra`, `/docs`, `/notebooks`, `/data`.
   - Explicación de por qué la infraestructura vive separada del código de las aplicaciones.

2. **Decisiones Clave de Cómputo y Almacenamiento (25 min)**
   - ¿Por qué no usamos Spark? (Polars + Dask).
     - [👉 Ver ADR-0003: Polars y Dask para Procesamiento](../../docs/01-architecture/ADRs/ADR-0003-polars-dask-procesamiento.md)
   - ¿Por qué usamos PostgreSQL como catálogo y RustFS como storage?
     - [👉 Ver ADR-0004: Postgres como Metadata Store](../../docs/01-architecture/ADRs/ADR-0004-postgres-metadata-store.md)

3. **Orquestación y Observabilidad (20 min)**
   - El rol de Prefect: No procesa datos, dirige el tráfico.
   - El rol de Prometheus y Grafana: Monitoreo *as-code*.
     - [👉 Ver ADR-0006: Prefect para Orquestación](../../docs/01-architecture/ADRs/ADR-0006-prefect-orquestacion.md)

---

## 🕒 Bloque 3: Infraestructura como Código (IaC) en Local (1 hora)

**Objetivo:** Desglosar el `docker-compose.yml` para entender cómo se conectan los servicios.

1. **Anatomía del Docker Compose (30 min)**
   - Lectura guiada del archivo maestro que levanta la arquitectura.
   - Explicación de Volúmenes (estado) vs Contenedores (sin estado).
   - [👉 Ver Guía: Explicación Detallada del docker-compose.yml](GUIDE-Docker-Compose-YML-Explicacion-Paso-a-Paso.md)

2. **Diseño de la Base de Datos Analítica (30 min)**
   - Análisis del script `init-postgres.sql`.
   - Concepto de Arquitectura Medallón (Bronze, Silver, Gold).
   - Modelado Dimensional (Tablas de Hechos y Dimensiones).
   - [👉 Ver Diseño de Base de Datos PQR](../../docs/04-guides/GUIA-DISEÑO-e-INFRA.md) *(O ajustar enlace al documento principal de BD si es otro)*.

---

## 🕒 Bloque 4: Taller Práctico - Levantando el Lakehouse (1 hora)

**Objetivo:** Ejecutar la infraestructura y comprobar que los servicios "hablan" entre sí.

1. **Revisión de Variables de Entorno (10 min)**
   - Creación y entendimiento del archivo `.env`.

2. **Despliegue Local (20 min)**
   - [👉 Ir a la Guía Paso a Paso Práctica](../../infra/docker/GUIA-INFRA-LOCAL-DOCKER.md)
   - Ejecución de `docker-compose up -d`.
   - Lectura de logs y resolución de problemas comunes (puertos ocupados, RAM).

3. **Verificación de Servicios (20 min)**
   - **Postgres:** Conexión con DBeaver/PgAdmin para ver el esquema generado.
   - **RustFS:** Entrar al puerto 9001 (si aplica) para ver el "S3" vacío.
   - **Grafana:** Entrar al puerto 3001 y verificar el Auto-Provisioning de Prometheus (Paso 6 reescrito).
   - **Prefect / Dask:** Entrar a sus UIs web para confirmar que el cómputo está esperando trabajo.

4. **Conclusiones y Siguientes Pasos (10 min)**
   - ¿Qué logramos hoy? Tenemos la base.
   - Próxima clase: Empezar a programar pipelines en Python (`apps/pipelines`) que inyecten datos a esta infraestructura.
