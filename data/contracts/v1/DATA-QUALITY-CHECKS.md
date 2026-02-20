# DATA-QUALITY-CHECKS.md

## 1. Bronze Checks

- event_id uniqueness
- non-null message_id
- body_length > 0
- valid timestamp formats

Fail policy: CRITICAL

---

## 2. Silver Checks

- pqrs_type not null
- model_version not null
- priority_score between 0 and 1
- entity JSON valid

Fail policy:
- Missing model_version → CRITICAL
- Sentiment missing → WARNING

---

## 3. Gold Checks

- total_emails >= 0
- category sums <= total
- no duplicate day+tenant

Fail policy:
- Aggregation mismatch → CRITICAL
- SLA anomaly → WARNING

---

## 4. Metadata Logging

Each check recorded in:

meta.quality_checks

Fields:
- run_id
- layer
- check_name
- status
- record_count
- timestamp