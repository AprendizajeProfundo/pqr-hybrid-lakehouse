from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_EVENT_TYPES = {"TICKET_CREATED", "MESSAGE_ADDED", "STATUS_CHANGED", "ATTACHMENT_ADDED"}


def normalize_event(raw_event: dict) -> dict:
    data = raw_event.get("data", {})
    return {
        "event_id": raw_event.get("event_id"),
        "ticket_id": raw_event.get("ticket_id"),
        "event_type": raw_event.get("event_type"),
        "ts": raw_event.get("ts"),
        "source_channel": data.get("source_channel"),
        "data": data,
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row, ensure_ascii=True) for row in rows)
    path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")


def _is_valid_event(event: dict[str, Any]) -> bool:
    if not event.get("event_id"):
        return False
    if not event.get("ticket_id"):
        return False
    if event.get("event_type") not in VALID_EVENT_TYPES:
        return False
    if not event.get("ts"):
        return False
    if not isinstance(event.get("data"), dict):
        return False
    return True


def run_raw_to_bronze(input_path: Path, output_path: Path, reject_output_path: Path | None, run_id: str) -> dict[str, int]:
    raw_events = _read_jsonl(input_path)
    normalized: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    ingested_at = datetime.now(timezone.utc).isoformat()

    for raw_event in raw_events:
        event = normalize_event(raw_event)
        if not _is_valid_event(event):
            rejected.append(raw_event)
            continue
        event["source_channel"] = event.get("source_channel") or "unknown"
        event["run_id"] = run_id
        event["ingested_at"] = ingested_at
        normalized.append(event)

    _write_jsonl(output_path, normalized)
    if reject_output_path is not None:
        _write_jsonl(reject_output_path, rejected)

    return {
        "raw_rows": len(raw_events),
        "bronze_rows": len(normalized),
        "rejected_rows": len(rejected),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize raw PQRS JSONL to Bronze JSONL.")
    parser.add_argument("--input", required=True, help="Ruta del JSONL raw de entrada.")
    parser.add_argument("--output", default="data/bronze/pqrs_events_bronze.jsonl")
    parser.add_argument("--reject-output", default="data/bronze/pqrs_events_rejected.jsonl")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    stats = run_raw_to_bronze(
        input_path=Path(args.input),
        output_path=Path(args.output),
        reject_output_path=Path(args.reject_output),
        run_id=args.run_id,
    )
    print(json.dumps(stats, ensure_ascii=True))


if __name__ == "__main__":
    main()
