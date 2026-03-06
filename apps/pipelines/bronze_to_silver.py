from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


def build_ticket_record(bronze_event: dict) -> dict:
    payload = bronze_event.get("data", {})
    return {
        "ticket_id": bronze_event.get("ticket_id"),
        "external_id": payload.get("external_id"),
        "source_channel": payload.get("source_channel"),
        "pqrs_type": payload.get("pqrs_type", "P"),
        "priority": payload.get("priority", "media"),
        "current_status": "RECEIVED",
        "dane_city_code": payload.get("dane_city_code"),
        "city_name": payload.get("geo_municipio"),
        "department_name": payload.get("geo_region"),
    }


def build_preclassification_record(bronze_event: dict, run_id: str = "local-dev-run") -> dict:
    payload = bronze_event.get("data", {})
    preclassifier = payload.get("preclassifier", {}) or {}
    text_value = payload.get("text")
    if not isinstance(text_value, str):
        text_value = ""

    explain = {
        "topic": preclassifier.get("topic"),
        "matched_keywords": preclassifier.get("matched_keywords", []),
        "subject": payload.get("subject"),
        "text_len": payload.get("text_len", len(text_value)),
    }

    return {
        "ticket_id": bronze_event.get("ticket_id"),
        "run_id": run_id,
        "model_type": "rules",
        "model_version": preclassifier.get("rules_version", "rules_pqrs_v1"),
        "predicted_type": preclassifier.get("predicted_pqrs_type", payload.get("pqrs_type", "P")),
        "predicted_priority": preclassifier.get("predicted_priority", payload.get("priority", "media")),
        "score": preclassifier.get("score", 0.0),
        "explain_json": explain,
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row, ensure_ascii=True) for row in rows)
    path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")


def _build_message_record(bronze_event: dict, run_id: str) -> dict:
    payload = bronze_event.get("data", {})
    text = payload.get("text") or ""
    return {
        "message_id": str(uuid4()),
        "ticket_id": bronze_event.get("ticket_id"),
        "ts": bronze_event.get("ts"),
        "role": str(payload.get("role", "citizen")).upper(),
        "text": text,
        "text_len": payload.get("text_len", len(text)),
        "run_id": run_id,
    }


def _build_status_event_record(bronze_event: dict, run_id: str) -> dict:
    payload = bronze_event.get("data", {})
    return {
        "event_id": bronze_event.get("event_id"),
        "ticket_id": bronze_event.get("ticket_id"),
        "ts": bronze_event.get("ts"),
        "status_from": payload.get("status_from"),
        "status_to": payload.get("status_to"),
        "actor_role": str(payload.get("actor_role", "system")).upper(),
        "reason": payload.get("reason"),
        "run_id": run_id,
    }


def run_bronze_to_silver(bronze_path: Path, output_dir: Path, run_id: str) -> dict[str, int]:
    bronze_events = _read_jsonl(bronze_path)

    tickets_map: dict[str, dict[str, Any]] = {}
    status_latest: dict[str, tuple[str, str]] = {}
    messages: list[dict[str, Any]] = []
    status_events: list[dict[str, Any]] = []
    preclass_rows: list[dict[str, Any]] = []

    for event in bronze_events:
        event_type = event.get("event_type")
        ticket_id = event.get("ticket_id")
        payload = event.get("data", {})

        if event_type == "TICKET_CREATED":
            ticket = build_ticket_record(event)
            ticket.update(
                {
                    "created_at": event.get("ts"),
                    "radicated_at": payload.get("radicated_at"),
                    "region": payload.get("geo_region"),
                    "sla_due_at": payload.get("sla_due_at"),
                    "closed_at": payload.get("closed_at"),
                    "run_id": run_id,
                }
            )
            tickets_map[ticket_id] = ticket
            preclass_rows.append(build_preclassification_record(event, run_id=run_id))

        elif event_type == "MESSAGE_ADDED":
            messages.append(_build_message_record(event, run_id=run_id))

        elif event_type == "STATUS_CHANGED":
            status_events.append(_build_status_event_record(event, run_id=run_id))
            status_latest[ticket_id] = (event.get("ts") or "", payload.get("status_to") or "RECEIVED")

    for ticket_id, (_, latest_status) in status_latest.items():
        if ticket_id in tickets_map:
            tickets_map[ticket_id]["current_status"] = latest_status

    tickets = list(tickets_map.values())

    _write_jsonl(output_dir / "tickets.jsonl", tickets)
    _write_jsonl(output_dir / "messages.jsonl", messages)
    _write_jsonl(output_dir / "status_events.jsonl", status_events)
    _write_jsonl(output_dir / "preclassification.jsonl", preclass_rows)

    return {
        "bronze_rows": len(bronze_events),
        "tickets_rows": len(tickets),
        "messages_rows": len(messages),
        "status_events_rows": len(status_events),
        "preclassification_rows": len(preclass_rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Transform Bronze JSONL to Silver datasets.")
    parser.add_argument("--input", required=True, help="Ruta del JSONL bronze.")
    parser.add_argument("--output-dir", default="data/silver")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    stats = run_bronze_to_silver(
        bronze_path=Path(args.input),
        output_dir=Path(args.output_dir),
        run_id=args.run_id,
    )
    print(json.dumps(stats, ensure_ascii=True))


if __name__ == "__main__":
    main()
