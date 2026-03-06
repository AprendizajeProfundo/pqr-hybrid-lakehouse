from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from apps.pipelines.bronze_to_silver import run_bronze_to_silver
from apps.pipelines.gold_to_postgres import run_load_to_postgres
from apps.pipelines.ingest_raw_to_rustfs import run_ingest_raw_to_rustfs
from apps.pipelines.raw_to_bronze import run_raw_to_bronze
from apps.pipelines.silver_to_gold import run_silver_to_gold

try:
    from prefect import flow, task
except Exception as exc:
    raise RuntimeError("Prefect no esta instalado en el entorno Python actual.") from exc


@task(name="ingest_raw_to_rustfs")
def task_ingest_raw_to_rustfs(input_path: str, run_id: str, day: str, upload: bool) -> dict:
    if not upload:
        return {"skipped": True}
    return run_ingest_raw_to_rustfs(
        input_path=Path(input_path),
        run_id=run_id,
        day=day,
    )


@task(name="raw_to_bronze")
def task_raw_to_bronze(input_path: str, bronze_path: str, rejects_path: str, run_id: str) -> dict:
    return run_raw_to_bronze(
        input_path=Path(input_path),
        output_path=Path(bronze_path),
        reject_output_path=Path(rejects_path),
        run_id=run_id,
    )


@task(name="bronze_to_silver")
def task_bronze_to_silver(bronze_path: str, silver_dir: str, run_id: str) -> dict:
    return run_bronze_to_silver(
        bronze_path=Path(bronze_path),
        output_dir=Path(silver_dir),
        run_id=run_id,
    )


@task(name="silver_to_gold")
def task_silver_to_gold(silver_dir: str, gold_dir: str, run_id: str) -> dict:
    return run_silver_to_gold(
        silver_dir=Path(silver_dir),
        output_dir=Path(gold_dir),
        run_id=run_id,
    )


@task(name="load_to_postgres")
def task_load_to_postgres(silver_dir: str, gold_dir: str, run_id: str, seed: int, executed_by: str, load_db: bool) -> dict:
    if not load_db:
        return {"skipped": True}
    return run_load_to_postgres(
        run_id=run_id,
        silver_dir=Path(silver_dir),
        gold_dir=Path(gold_dir),
        seed=seed,
        executed_by=executed_by,
    )


@flow(name="pqrs_jsonl_etl_flow")
def pqrs_jsonl_etl_flow(
    input_jsonl: str,
    run_id: str | None = None,
    day: str | None = None,
    upload_raw: bool = False,
    load_db: bool = False,
    seed: int = 42,
    base_dir: str = "data",
) -> dict:
    run_id_value = run_id or str(uuid4())
    day_value = day or datetime.now(timezone.utc).date().isoformat()

    bronze_path = str(Path(base_dir) / "bronze" / f"pqrs_events_bronze_{run_id_value}.jsonl")
    rejects_path = str(Path(base_dir) / "bronze" / f"pqrs_events_rejected_{run_id_value}.jsonl")
    silver_dir = str(Path(base_dir) / "silver" / run_id_value)
    gold_dir = str(Path(base_dir) / "gold" / run_id_value)

    ingest_stats = task_ingest_raw_to_rustfs(input_path=input_jsonl, run_id=run_id_value, day=day_value, upload=upload_raw)
    bronze_stats = task_raw_to_bronze(input_path=input_jsonl, bronze_path=bronze_path, rejects_path=rejects_path, run_id=run_id_value)
    silver_stats = task_bronze_to_silver(bronze_path=bronze_path, silver_dir=silver_dir, run_id=run_id_value)
    gold_stats = task_silver_to_gold(silver_dir=silver_dir, gold_dir=gold_dir, run_id=run_id_value)
    db_stats = task_load_to_postgres(
        silver_dir=silver_dir,
        gold_dir=gold_dir,
        run_id=run_id_value,
        seed=seed,
        executed_by="prefect-flow",
        load_db=load_db,
    )

    return {
        "run_id": run_id_value,
        "day": day_value,
        "input_jsonl": input_jsonl,
        "bronze_path": bronze_path,
        "silver_dir": silver_dir,
        "gold_dir": gold_dir,
        "ingest_stats": ingest_stats,
        "bronze_stats": bronze_stats,
        "silver_stats": silver_stats,
        "gold_stats": gold_stats,
        "db_stats": db_stats,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run end-to-end JSONL ETL flow with Prefect.")
    parser.add_argument("--input-jsonl", required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--day", default=None)
    parser.add_argument("--upload-raw", action="store_true")
    parser.add_argument("--load-db", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--base-dir", default="data")
    args = parser.parse_args()

    summary = pqrs_jsonl_etl_flow(
        input_jsonl=args.input_jsonl,
        run_id=args.run_id,
        day=args.day,
        upload_raw=args.upload_raw,
        load_db=args.load_db,
        seed=args.seed,
        base_dir=args.base_dir,
    )
    print(json.dumps(summary, ensure_ascii=True))


if __name__ == "__main__":
    main()
