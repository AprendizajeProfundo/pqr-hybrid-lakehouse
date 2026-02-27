# DATA-LAYOUT-S3.md

## 1. Root Structure

```text
s3://pqr-lakehouse/
raw/
bronze/
silver/
gold/
```
---

## 2. Partitioning Standard
```text
layer/entity/source=…/day=YYYY-MM-DD/run_id=UUID/
```

Example:
```text
s3://pqr-lakehouse/bronze/email/source=outlook/day=2026-01-15/run_id=a1b2c3d4-e5f6-7890-1234-567890abcdef/
```
---

## 3. Rules

- Raw is append-only.
- Bronze/Silver/Gold never overwrite across run_id.
- No hardcoded paths in code.
- All access via configuration.

---

## 4. Evolution Compatibility

Layout compatible with future Iceberg adoption.