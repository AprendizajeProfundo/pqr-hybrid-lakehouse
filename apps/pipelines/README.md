# apps/pipelines/

Esta carpeta contiene los pipelines ETL para transformación de datos.

- `ingest_raw_to_rustfs.py`: Ingesta de JSONL local a RustFS (S3 compatible).
- `raw_to_bronze.py`: Normalización Raw → Bronze.
- `bronze_to_silver.py`: Curación Bronze → Silver (con validaciones).
- `silver_to_gold.py`: Agregaciones Silver → Gold.
- `gold_to_postgres.py`: Carga Silver/Gold → Postgres.
- `prefect_etl_flow.py`: Orquestación end-to-end con Prefect.

Usar Dask para paralelismo. Orquestar con Prefect.
