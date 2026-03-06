ENV_NAME ?= pqr-lakehouse
ENV_FILE ?= environment.yml
RUN_ID ?= 00000000-0000-0000-0000-000000000001
DAY ?= 2026-03-05
INPUT_JSONL ?= data/raw/pqrs_events_20250901_20260228.jsonl
PREFECT_UPLOAD_RAW ?= 1
PREFECT_LOAD_DB ?= 1

.PHONY: env test etl-ingest etl-bronze etl-silver etl-gold etl-load etl-flow etl-flow-skip-io dashboard-app

env:
	@conda env list | awk '{print $$1}' | grep -qx "$(ENV_NAME)" \
		&& conda env update -n "$(ENV_NAME)" -f "$(ENV_FILE)" --prune \
		|| conda env create -f "$(ENV_FILE)"

test:
	@conda run -n "$(ENV_NAME)" env PYTHONPATH=. pytest -q apps/tests/test_simulation.py apps/tests/test_pipelines.py

etl-ingest:
	@conda run -n "$(ENV_NAME)" env PYTHONPATH=. python apps/pipelines/ingest_raw_to_rustfs.py \
		--input "$(INPUT_JSONL)" \
		--run-id "$(RUN_ID)" \
		--day "$(DAY)"

etl-bronze:
	@conda run -n "$(ENV_NAME)" env PYTHONPATH=. python apps/pipelines/raw_to_bronze.py \
		--input "$(INPUT_JSONL)" \
		--output "data/bronze/pqrs_events_bronze_$(RUN_ID).jsonl" \
		--reject-output "data/bronze/pqrs_events_rejected_$(RUN_ID).jsonl" \
		--run-id "$(RUN_ID)"

etl-silver:
	@conda run -n "$(ENV_NAME)" env PYTHONPATH=. python apps/pipelines/bronze_to_silver.py \
		--input "data/bronze/pqrs_events_bronze_$(RUN_ID).jsonl" \
		--output-dir "data/silver/$(RUN_ID)" \
		--run-id "$(RUN_ID)"

etl-gold:
	@conda run -n "$(ENV_NAME)" env PYTHONPATH=. python apps/pipelines/silver_to_gold.py \
		--silver-dir "data/silver/$(RUN_ID)" \
		--output-dir "data/gold/$(RUN_ID)" \
		--run-id "$(RUN_ID)"

etl-load:
	@conda run -n "$(ENV_NAME)" env PYTHONPATH=. python apps/pipelines/gold_to_postgres.py \
		--run-id "$(RUN_ID)" \
		--silver-dir "data/silver/$(RUN_ID)" \
		--gold-dir "data/gold/$(RUN_ID)" \
		--seed 42 \
		--executed-by "make-etl"

etl-flow:
	@conda run -n "$(ENV_NAME)" env PYTHONPATH=. python apps/pipelines/prefect_etl_flow.py \
		--input-jsonl "$(INPUT_JSONL)" \
		--run-id "$(RUN_ID)" \
		--day "$(DAY)" \
		$(if $(filter 1 true TRUE yes YES,$(PREFECT_UPLOAD_RAW)),--upload-raw,) \
		$(if $(filter 1 true TRUE yes YES,$(PREFECT_LOAD_DB)),--load-db,) \
		--seed 42

etl-flow-skip-io:
	@$(MAKE) etl-flow PREFECT_UPLOAD_RAW=0 PREFECT_LOAD_DB=0

dashboard-app:
	@conda run -n "$(ENV_NAME)" env PGHOST=127.0.0.1 PGPORT=5432 PGUSER=postgres PGPASSWORD=localdev123 PGDATABASE=pqr_lakehouse streamlit run apps/dashboard-streamlit/app.py
