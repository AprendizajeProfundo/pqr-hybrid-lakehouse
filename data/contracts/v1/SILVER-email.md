# SILVER — Email Enriched Dataset Specification

## 1. Purpose

Silver layer adds semantic enrichment via AI.

Represents curated dataset ready for analytics.

---

## 2. Input

Source: bronze_email

---

## 3. Table: silver_email

| Column | Type | Description |
|--------|------|------------|
| event_id | string |
| tenant_id | string |
| message_id | string |
| sender_email | string |
| subject | string |
| body | string |
| pqrs_type | string | Petition / Complaint / Claim / Suggestion |
| priority_score | float | 0.0–1.0 |
| entities_json | string | JSON serialized entities |
| sentiment_score | float | Optional |
| model_version | string |
| inference_timestamp | timestamp |
| day | date |
| run_id | string |

---

## 4. AI Governance

- model_version mandatory
- inference_timestamp mandatory
- deterministic seed optional

---

## 5. Partitioning

S3 partition:

```text
silver/email/source=<provider>/day=YYYY-MM-DD/run_id=UUID/
```

---

## 6. Non-Goals

- No reescritura de campos estructurales de Bronze.
- No uso de este dataset para serving directo en BI (solo Gold).
