# PQR Hybrid Lakehouse MVP
## Scope Definition (10-Day Implementation)

---

## 1. Objective

Deliver a functional hybrid data platform MVP in 10 days that:

- Simulates a realistic PQRS email ingestion system
- Demonstrates Big Data processing using Dask
- Implements a Lakehouse architecture
- Provides operational dashboards
- Supports reproducible runs

---

## 2. Functional Scope

### 2.1 Channel
Only Email (synthetic generation).

### 2.2 Ingestion
- Deterministic email generator
- JSONL Raw events
- Manifest file per run
- Hash validation

### 2.3 Lakehouse Layers
- Raw (JSONL, immutable)
- Bronze (typed Parquet)
- Silver (curated Parquet)
- Gold (aggregated Parquet + Postgres tables)

### 2.4 Big Data Simulation
- Partitioned processing
- Parallel Dask execution
- Synthetic peak simulation
- SLA breach simulation (configurable 7–12%)

### 2.5 Governance
- meta.runs
- meta.datasets
- meta.lineage
- meta.quality_checks

### 2.6 Operational PQRS Model
- core.tickets
- core.ticket_events
- SLA per PQRS type
- backlog calculation

### 2.7 Dashboards
- Streamlit executive view
- Metabase BI exploration
- Grafana operational metrics

---

## 3. Technical Scope

### Containerized Services

Core:
- Supabase (PostgreSQL + Auth)
- RustFS
- Dask Scheduler
- Dask Workers (min 2)
- Prefect Server
- DuckDB jobs container
- Streamlit
- Prometheus
- Grafana

Optional (if time permits):
- Loki
- Neo4j

---

## 4. Out of Scope (MVP)

- Real IMAP/SMTP integration
- Spark cluster
- Cassandra
- Kubernetes
- CI/CD pipelines
- Production-grade secret management
- Multi-tenant isolation enforcement
- Distributed storage redundancy

---

## 5. Definition of Done

The MVP is complete when:

1. A run generates raw events in RustFS.
2. Dask transforms data through all lakehouse layers.
3. Gold KPIs are loaded into Postgres.
4. Streamlit shows KPI dashboard.
5. Metabase connects and builds queries.
6. Grafana displays operational metrics.
7. A failed run can be retried.
8. The same seed reproduces identical raw output.

---

## 6. Timeline Constraint

Total implementation window: 10 days.

Architecture decisions must favor:
- Simplicity
- Container reproducibility
- Clarity over feature richness
- Educational value

---

## 7. Risk Considerations

- Dask cluster misconfiguration
- S3 permissions misalignment
- Schema drift
- Time constraints impacting observability setup

Mitigation: incremental build and daily validation.

---

End of document.