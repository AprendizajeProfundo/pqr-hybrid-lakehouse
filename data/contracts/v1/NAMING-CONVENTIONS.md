# NAMING-CONVENTIONS.md

## 1. Tables

layer_entity

Examples:
- bronze_email
- silver_email
- gold_daily_kpis

---

## 2. Columns

snake_case only.

Primary keys:
- event_id
- message_id

Partition columns:
- day
- run_id
- tenant_id (future)

---

## 3. S3
```text
Lowercase only.
No spaces.
No camelCase.
```
