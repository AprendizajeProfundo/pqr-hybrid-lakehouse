# GOLD — KPI Datasets Specification

## 1. Purpose

Gold layer provides business-facing datasets.

Consumed by:
- Streamlit
- Metabase
- Postgres serving layer

---

## 2. Example Table: gold_daily_kpis

| Column | Type | Description |
|--------|------|------------|
| day | date |
| tenant_id | string |
| total_emails | int |
| petitions | int |
| complaints | int |
| claims | int |
| suggestions | int |
| avg_priority | float |
| high_priority_ratio | float |
| sla_breach_ratio | float |
| run_id | string |

---

## 3. Constraints

- Gold datasets must be aggregated.
- No raw text fields.
- Stable schema.
- Governed by serving policy.

---

## 4. Postgres Loading

Gold datasets loaded into:

schema: `gold`

Tables:
- gold_daily_kpis
- gold_sla_metrics
- gold_priority_distribution