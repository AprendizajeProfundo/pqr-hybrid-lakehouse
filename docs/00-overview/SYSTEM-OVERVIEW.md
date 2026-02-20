# PQR Hybrid Lakehouse MVP
## System Overview

---

## 1. Purpose

The PQR Hybrid Lakehouse MVP is a containerized, production-inspired data platform designed to simulate a real hybrid cloud data system for managing PQRS (Peticiones, Quejas, Reclamos y Sugerencias) through an email channel.

The system is intentionally designed for:

- Teaching modern cloud-native data engineering practices
- Demonstrating hybrid architecture patterns
- Supporting reproducible analytics
- Operating under realistic business constraints (SLA, backlog, observability)

This is not a toy project. It models a real enterprise-grade architecture within a controlled educational environment.

---

## 2. Architectural Vision

The system follows a strict separation of concerns:

### Control Plane
Supabase (PostgreSQL) acts as the administrative backbone:
- Authentication & RBAC
- Operational state (tickets, events)
- Governance metadata (runs, lineage, quality checks)
- Serving layer (gold_* datasets)

### Data Plane
RustFS (S3-compatible object storage):
- Immutable Raw ingestion
- Bronze / Silver / Gold lakehouse layers
- Parquet-based columnar storage
- Historical traceability

### Compute Plane
Dask Distributed:
- Parallel data processing
- Big Data simulation via partitioned workloads
- ETL across lakehouse layers

DuckDB:
- OLAP queries over Parquet
- Ad-hoc analytics
- Fast gold aggregations

### Orchestration
Prefect Server:
- Workflow coordination
- Retries & scheduling
- Run state tracking

### Observability
Prometheus + Grafana:
- Pipeline metrics
- SLA monitoring
- Job duration tracking
- Operational dashboards

### Serving Layer
- Streamlit (curated executive dashboard)
- Metabase (self-service BI over gold_*)

---

## 3. Core Design Principles

1. Event-first modeling
2. Raw data is immutable
3. Reproducibility via run_id + seed + manifest
4. Idempotent pipelines
5. Lakehouse by design (Raw → Bronze → Silver → Gold)
6. Separation of control, data, and compute planes
7. Observability from day one
8. Containerized reproducibility

---

## 4. Target Audience

- Data Scientists
- Data Engineers
- Backend Developers
- DevOps / DataOps engineers
- Technical leaders

---

## 5. Non-Goals (for MVP)

- Real email provider integration
- High availability clustering
- Production-grade security hardening
- Kubernetes deployment
- Multi-region storage
- Cassandra or Spark integration

These may be discussed architecturally but are not implemented in MVP.

---

## 6. High-Level Flow

1. Email events are synthetically generated.
2. Raw JSONL events are written to RustFS.
3. Dask transforms data into Bronze (Parquet).
4. Dask produces Silver curated datasets.
5. Gold KPIs are generated.
6. Gold datasets are loaded into PostgreSQL.
7. Streamlit & Metabase serve dashboards.
8. Grafana monitors system health.

---

## 7. Definition of the System

The system is considered operational when:

- Raw ingestion is deterministic.
- Lakehouse layers are materialized.
- Gold KPIs are queryable in Postgres.
- Observability dashboards show pipeline metrics.
- A full end-to-end run can be re-executed idempotently.

---

End of document.