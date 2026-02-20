# PQR Hybrid Lakehouse MVP
## System Overview

---

## 1. Purpose

The **PQR Hybrid Lakehouse MVP** is a containerized, production-inspired hybrid data platform designed to simulate a real enterprise data system for managing PQRS (Peticiones, Quejas, Reclamos y Sugerencias) through a synthetic email channel.

The system is intentionally designed to:

- Teach modern cloud-native data engineering practices  
- Demonstrate hybrid architecture patterns (Control/Data/Compute planes)  
- Integrate AI-based semantic enrichment in a structured pipeline  
- Support reproducible analytics  
- Operate under realistic business constraints (SLA, backlog, observability)  

This is not a toy system. It models a real enterprise-grade architecture within a controlled educational environment.

---

## 2. Architectural Vision

The system enforces a strict separation of concerns across architectural planes.

---

### 2.1 Control Plane

**Supabase (PostgreSQL)** acts as the administrative backbone:

- Authentication & RBAC  
- Operational state (`core.tickets`, `core.ticket_events`, `core.messages`)  
- Governance metadata (`meta.runs`, `meta.lineage`, `meta.quality_checks`)  
- Serving layer (`gold_*` datasets exposed to BI)  

The Control Plane governs the system but does not store historical raw data.

---

### 2.2 Data Plane

**RustFS (S3-compatible object storage)** implements the lakehouse:

- Immutable Raw ingestion (JSONL + manifest + run_id)  
- Bronze layer (typed Parquet)  
- Silver layer (curated & AI-enriched Parquet)  
- Gold layer (aggregated Parquet datasets)  
- Partitioned layout: `source/day/run_id`  

RustFS is the historical source of truth and guarantees reproducibility.

---

### 2.3 Compute Plane

The Compute Plane is divided into three logical roles.

#### Dask Distributed (Primary Processing Engine)

- Parallel execution over partitioned data  
- Big Data simulation through distributed workloads  
- Raw → Bronze transformation  
- Bronze → Silver enrichment  
- Silver → Gold aggregation  

Dask orchestrates compute tasks but does not serve as storage.

---

#### AI Enrichment Layer (Executed within Dask tasks)

AI models are applied in the **Silver stage**, not Bronze.

AI responsibilities include:

- PQRS classification  
- Entity extraction (municipality, topic, etc.)  
- Priority estimation  
- Text summarization (optional)  
- Embedding generation (optional extension)  

This separation preserves deterministic Bronze processing and semantic interpretability in Silver.

---

#### DuckDB (Analytical Engine)

DuckDB provides:

- OLAP queries directly over Parquet in RustFS  
- Fast analytical exploration  
- Gold-level aggregation support  
- Demonstration of “query engine over lakehouse”  

DuckDB complements Dask but does not replace it.

---

#### Polars (Optional High-Performance DataFrame Engine)

Polars may be used:

- For local development acceleration  
- For benchmarking vs Dask  
- For specific transformation optimizations inside Dask tasks  

Polars is not the primary distributed engine but can act as an efficient intra-partition processor.

---

### 2.4 Orchestration

**Prefect Server (containerized)** coordinates:

- Pipeline execution  
- Retry policies  
- Scheduling  
- Run tracking  
- State visibility  

Prefect integrates with Dask to trigger distributed workloads.

---

### 2.5 Observability

**Prometheus + Grafana** provide:

- Pipeline duration metrics  
- Throughput monitoring  
- SLA compliance tracking  
- Failure alerts  
- Operational dashboards  

Observability is part of the MVP, not an afterthought.

---

### 2.6 Serving Layer

Two complementary serving strategies:

- **Streamlit** → curated executive dashboard  
- **Metabase** → self-service BI over `gold_*` tables  

Both connect exclusively to PostgreSQL.

---

## 3. Data Layer Semantics

The lakehouse layers have strict semantic boundaries.

### Raw
- Immutable  
- JSONL  
- Exact representation of received events  
- Append-only  
- Deterministic via seed + run_id  

### Bronze
- Structured and typed  
- Parquet  
- Mechanical normalization  
- No AI interpretation  

### Silver
- Curated  
- AI-enriched  
- Business-ready structure  
- Entities, classifications, derived fields  

### Gold
- Aggregated KPIs  
- SLA metrics  
- Backlog indicators  
- Analytical datasets for BI  

---

## 4. Core Design Principles

1. Event-first modeling  
2. Raw is immutable  
3. Deterministic reproducibility (run_id + seed + manifest)  
4. Idempotent pipelines  
5. AI enrichment isolated from structural transformation  
6. Separation of Control, Data, and Compute planes  
7. Observability from day one  
8. Containerized reproducibility  
9. Governance before dashboards  

---

## 5. Target Audience

- Data Scientists  
- Data Engineers  
- Backend Developers  
- DataOps / MLOps engineers  
- Technical leaders  

---

## 6. Non-Goals (MVP)

- Real email provider integration  
- High availability clustering  
- Kubernetes deployment  
- Multi-region storage  
- Spark cluster  
- Cassandra event store  
- Production-grade security hardening  

These may be discussed architecturally but are not implemented in MVP.

---

## 7. High-Level Flow

1. Email events are synthetically generated.  
2. Raw JSONL events are written to RustFS.  
3. Dask transforms Raw → Bronze (typed Parquet).  
4. Dask applies AI enrichment Bronze → Silver.  
5. Dask produces Gold aggregates.  
6. Gold datasets are loaded into PostgreSQL.  
7. Streamlit & Metabase serve dashboards.  
8. Grafana monitors pipeline execution and SLA metrics.  

---

## 8. Definition of Operational Readiness

The system is considered operational when:

- Raw ingestion is deterministic.  
- Bronze, Silver, and Gold layers are materialized.  
- AI enrichment outputs are traceable and versioned.  
- Gold KPIs are queryable in PostgreSQL.  
- Observability dashboards display live metrics.  
- A full pipeline run can be retried idempotently.  

---

End of document.