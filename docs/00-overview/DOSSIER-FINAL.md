# Dossier Final: PQR Hybrid Lakehouse - Implementación Completa

**Proyecto:** Sistema de Seguimiento y Analítica PQRS con Datos Sintéticos  
**Versión:** 1.0  
**Fecha:** 2026-02-25  
**Autor:** Equipo PQR Hybrid Lakehouse  

---

## 1. Introducción

Este dossier consolida el diseño y planificación del proyecto PQR Hybrid Lakehouse, un sistema híbrido para seguimiento de PQRS (Peticiones, Quejas, Reclamos, Sugerencias) usando datos sintéticos. Sirve como:

- **Base de desarrollo**: Guía técnica para implementación.
- **Material educativo**: Explicación para estudiantes de ciencia de datos e ingeniería.
- **Referencia**: Arquitectura, decisiones y pasos de implementación.

El proyecto demuestra un lakehouse moderno con simulación determinista, pipelines ETL distribuidos y dashboards analíticos.

---

## 2. Arquitectura General

### 2.1 Visión General
Basado en ADR-0001: Arquitectura por planos (Control/Data/Compute).

- **Control Plane:** Postgres (Supabase) para metadatos y serving.
- **Data Plane:** RustFS (S3-compatible) para lakehouse (Raw/Bronze/Silver/Gold).
- **Compute Plane:** Dask Distributed para ETL, Prefect para orquestación.

### 2.2 Diagrama C4 - Contexto
![C4 Contexto](/docs/01-architecture/C4-CONTEXT_V2.svg)

### 2.3 Flujo de Datos
Raw (JSONL) → Bronze (Parquet) → Silver (Curado) → Gold (KPIs) → Postgres (Serving).

![Flujo Lakehouse](/docs/01-architecture/ARCH-PRINCIPLES-MAP.svg)

---

## 3. Componentes Clave

### 3.1 ADRs Fundamentales
- ADR-0016: Base de seguimiento PQRS + Lakehouse.
- ADR-0017: Modelo formal de estados PQRS.
- ADR-0018: Clasificación PQRS (rules/ML/embeddings).
- ADR-0004: Dask como compute core.

### 3.2 SPECs de Implementación
- SPEC-0016: Seguimiento y esquemas.
- SPEC-0016.1: Generación de datos sintéticos.
- SPEC-0017: Estados y transiciones.
- SPEC-0018: Clasificación.

### 3.3 Configs y Contratos
- `pqrs_simulation_v1.yaml`: Parámetros de simulación.
- `pqrs_status_v1.yaml`: Estados y SLA.
- `pqrs_preclass_rules_v1.yaml`: Reglas de clasificación.
- `RAW-PQRS.schema.json`: Contrato de eventos.

---

## 4. Paso a Paso de Implementación

### Paso 1: Montar Infraestructura Local
1. Instalar Docker y Docker Compose.
2. Clonar repo y navegar a `infra/docker/`.
3. Configurar `.env` con credenciales locales.
4. Ejecutar `docker-compose up -d`.
5. Verificar servicios: Postgres, RustFS (almacenamiento nativo), Dask, Prefect, Grafana, Streamlit, Metabase.

**Tiempo estimado:** 30 min.  
**Resultado:** Infra corriendo en localhost.

### Paso 2: Generar Datos Sintéticos
1. Activar entorno Python (usar venv o conda).
2. Instalar dependencias: `pip install faker pandas pyarrow dask boto3`.
3. Ejecutar simulador: `python apps/simulator/generate_pqrs_data.py --config docs/07-config/pqrs_simulation_v1.yaml`.
4. Verificar output en `raw/pqrs/` (JSONL events).

**Tiempo estimado:** 5-10 min.  
**Resultado:** Eventos raw generados determinísticamente.

### Paso 3: Ejecutar Pipelines ETL
1. Configurar Dask client: `from dask.distributed import Client; client = Client('tcp://localhost:8786')`.
2. Ejecutar Raw → Bronze: `python apps/pipelines/raw_to_bronze.py`.
3. Ejecutar Bronze → Silver: `python apps/pipelines/bronze_to_silver.py` (valida estados/SLA).
4. Ejecutar Silver → Gold: `python apps/pipelines/silver_to_gold.py` (agregaciones KPIs).
5. Cargar Gold → Postgres: `python apps/pipelines/gold_to_postgres.py`.

**Tiempo estimado:** 15-30 min.  
**Resultado:** Datos curados en Silver/Gold, KPIs en Postgres.

### Paso 4: Orquestar con Prefect
1. Crear flows en `apps/pipelines/` usando `@flow` decorator.
2. Registrar en Prefect: `prefect deploy`.
3. Ejecutar desde UI Prefect (localhost:4200).

**Tiempo estimado:** 10 min.  
**Resultado:** Pipelines automatizados.

### Paso 5: Construir Dashboards
1. En Streamlit (`apps/dashboard-streamlit/`): Conectar a Postgres, crear gráficos de volumen/SLA/backlog.
2. En Metabase (localhost:3000): Configurar conexión Postgres, crear dashboards analíticos.
3. En Grafana (localhost:3001): Dashboards de monitoreo (Dask metrics).

**Tiempo estimado:** 20-30 min.  
**Resultado:** Dashboards interactivos con datos PQRS.

### Paso 6: Validar y Monitorear
1. Ejecutar tests: `pytest apps/tests/`.
2. Verificar re-runs idénticos.
3. Monitorear en Grafana/Prometheus.
4. Generar reportes de calidad.

**Tiempo estimado:** 10 min.  
**Resultado:** Sistema validado y listo para uso.

---

## 5. Diagramas Adicionales

### 5.1 Máquina de Estados PQRS
![Estados PQRS](/docs/06-spec/diagramas/Estados-PQRS-V1.svg)

### 5.2 Pipeline ETL
![Pipeline ETL](/docs/06-spec/diagramas/pipeline-etl.svg)

*(Nota: Crear diagramas en PlantUML o Draw.io y referenciar aquí)*

---

## 6. Lecciones Aprendidas y Mejores Prácticas

- **Determinismo:** Siempre usar seeds para reproducibilidad.
- **Separación de capas:** Mantener Raw inmutable, Silver curado.
- **Validaciones:** Implementar checks en cada pipeline.
- **Escalabilidad:** Dask permite crecer de local a cluster.
- **Documentación:** ADRs/SPECs facilitan evolución.

---

## 7. Próximos Pasos
- Migrar a AWS (ECS/S3/RDS).
- Agregar ML para clasificación.
- Integrar datos reales.

Este dossier cierra la fase de diseño. ¡Implementación exitosa!