# ADR-0015 — Fase 3: Industrialización Multi-Tenant, Seguridad, Streaming y MLOps

**Estado:** Planificado (Roadmap estratégico)  
**Fecha:** 2026-02-18  
**Tipo:** Evolución Arquitectónica Mayor  

---

## 1. Contexto

El MVP (Fase 1) establece:

- Arquitectura híbrida por planos
- Lakehouse Parquet gobernado
- Dask como motor distribuido
- IA en Silver
- Observabilidad básica
- Serving dual (Streamlit + Metabase)

Fase 2 introduce:

- Lakehouse transaccional (Iceberg/Delta)
- Query federation
- Escalamiento compute
- Gobierno avanzado

La Fase 3 busca industrializar la plataforma y convertirla en:

> Plataforma multi-tenant operable, segura, escalable y con MLOps formal.

---

## 2. Objetivos de Fase 3

Transformar el sistema en:

- Plataforma SaaS o Enterprise multi-cliente
- Infraestructura Kubernetes-ready y auto-escalable
- Sistema con seguridad y compliance robustos
- Arquitectura batch + streaming
- Plataforma de IA con ciclo completo MLOps
- Observabilidad y FinOps completos

---

## 3. Decisiones Arquitectónicas Clave

### 3.1 Multi-Tenancy Real

Adoptar aislamiento por tenant a nivel:

- Storage (S3 prefix por tenant)
- Compute (namespaces o clusters separados)
- Metadata (tenant_id en meta.*, core.*, gold_*)
- Observabilidad (dashboards por tenant)
- SLAs diferenciados

Modelo soportado:
- Logical isolation (mínimo)
- Namespace isolation (intermedio)
- Cluster isolation (alto)

---

### 3.2 Migración a Kubernetes

Adoptar Kubernetes como plano de ejecución:

- Dask sobre K8s (auto-scaling workers)
- Prefect Agents sobre K8s
- Horizontal Pod Autoscaling
- Configuración via ConfigMaps/Secrets

Principio:
> El sistema debe escalar horizontalmente sin rediseño.

---

### 3.3 Lakehouse Transaccional Formal

Integrar:

- Apache Iceberg o Delta Lake
- Catálogo centralizado
- Snapshot isolation
- Time travel
- Compaction automática

Manteniendo:
- Layout conceptual Raw/Bronze/Silver/Gold
- Parquet como formato base

---

### 3.4 Streaming / Near Real-Time

Introducir:

- Kafka / Redpanda
- Ingesta continua de eventos
- Micro-batching
- SLAs de latencia (minutos o segundos)

Batch y streaming deben converger en el mismo lakehouse.

---

### 3.5 Seguridad de Nivel Empresarial

Implementar:

- IAM granular (RBAC + ABAC)
- Secret management (Vault / KMS)
- Cifrado at-rest e in-transit
- Auditoría inmutable
- Data masking y PII governance
- Policy-as-code

---

### 3.6 MLOps Completo

Adoptar:

- Model registry (MLflow u otro)
- Versionado de modelo y prompt
- Evaluación continua (drift, precisión)
- Human-in-the-loop
- Monitoreo de inferencia
- Feature store (si aplica)
- Vector store (pgvector/Milvus/Qdrant)

IA pasa de ser componente a ser producto gestionado.

---

### 3.7 Observabilidad + FinOps

Incorporar:

- OpenTelemetry (metrics + logs + traces)
- Dashboards por tenant
- Alertas por SLA
- Cost allocation por cliente
- Métricas de uso y capacidad

---

## 4. Qué No Cambia

Se preserva:

- Separación Control/Data/Compute
- run_id como unidad de reproducibilidad
- Gold como API analítica oficial
- Principio estructura ≠ semántica
- Observabilidad obligatoria

Fase 3 extiende, no reemplaza.

---

## 5. Riesgos y Mitigación

Riesgo: Complejidad operacional alta  
Mitigación: Evolución progresiva por módulos

Riesgo: Sobrecarga de infraestructura  
Mitigación: Diseño modular y gradual

Riesgo: Desalineación con objetivos pedagógicos  
Mitigación: Separar claramente “curso” y “plataforma productiva”

---

## 6. Visión Final

MVP → Plataforma Educativa Profesional  
Fase 2 → Plataforma Lakehouse Transaccional  
Fase 3 → Plataforma de Datos Industrial Multi-Tenant con MLOps

---

## 7. Principio Rector

> Fase 3 industrializa la arquitectura sin traicionar los principios fundacionales definidos en Fase 1.

---

End of ADR.