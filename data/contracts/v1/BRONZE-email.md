# BRONZE — Email Dataset Specification

## 1. Purpose

Bronze layer represents structured, typed transformation of RAW email events.

No semantic enrichment.
No AI outputs.
Only deterministic transformations.

---

## 2. Source

Input: RAW-EMAIL.schema.json  
Output format: Parquet

---

## 3. Table: bronze_email

| Column | Type | Description |
|--------|------|------------|
| event_id | string | From raw |
| tenant_id | string | Optional |
| ingestion_timestamp | timestamp | From raw |
| message_id | string | Email message ID |
| sender_email | string | Normalized sender |
| recipient_count | int | Count of TO recipients |
| subject | string | Original subject |
| body | string | Original body |
| body_length | int | Character length |
| has_attachments | boolean | Derived |
| attachment_count | int | Derived |
| received_timestamp | timestamp | From raw |
| day | date | Partition column |
| run_id | string | Ingestion run identifier |

---

## 4. Transform Rules

- Emails normalized to lowercase.
- Timestamps converted to UTC.
- body_length computed deterministically.
- No filtering allowed at Bronze.

---

## 5. Partitioning

S3 partition:
```text
silver/email/day=YYYY-MM-DD/run_id=UUID/
```
---

## 6. Principles

- Structure ≠ Semantics
- Reproducible enrichment
- Version-aware outputs
