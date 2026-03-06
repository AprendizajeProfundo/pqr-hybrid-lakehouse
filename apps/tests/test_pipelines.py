from apps.pipelines.bronze_to_silver import build_preclassification_record, build_ticket_record
from apps.pipelines.gold_to_postgres import build_upsert_statement
from apps.pipelines.raw_to_bronze import normalize_event
from apps.pipelines.silver_to_gold import aggregate_volume_daily


def test_normalize_event_maps_source_channel() -> None:
    raw = {
        "event_id": "e1",
        "ticket_id": "t1",
        "event_type": "TICKET_CREATED",
        "ts": "2026-01-01T00:00:00Z",
        "data": {"source_channel": "email", "pqrs_type": "P", "priority": "media"},
    }
    normalized = normalize_event(raw)
    assert normalized["source_channel"] == "email"


def test_build_ticket_record_defaults_status() -> None:
    ticket = build_ticket_record({"ticket_id": "t1", "data": {"source_channel": "chat", "pqrs_type": "Q"}})
    assert ticket["current_status"] == "RECEIVED"


def test_aggregate_volume_daily_counts() -> None:
    counters = aggregate_volume_daily([
        {"source_channel": "email", "pqrs_type": "P"},
        {"source_channel": "email", "pqrs_type": "P"},
        {"source_channel": "chat", "pqrs_type": "Q"},
    ])
    assert counters[("email", "P")] == 2
    assert counters[("chat", "Q")] == 1


def test_upsert_statement_contains_conflict_clause() -> None:
    statement = build_upsert_statement()
    assert "ON CONFLICT" in statement


def test_build_preclassification_record_maps_fields() -> None:
    bronze_event = {
        "ticket_id": "t-123",
        "data": {
            "pqrs_type": "R",
            "priority": "alta",
            "subject": "reclamo_facturacion - EXT-1001",
            "text": "Interpongo reclamo por error de factura.",
            "text_len": 39,
            "preclassifier": {
                "rules_version": "rules_pqrs_v1",
                "topic": "reclamo_facturacion",
                "predicted_pqrs_type": "R",
                "predicted_priority": "alta",
                "score": 0.93,
                "matched_keywords": ["reclamo", "factura", "error"],
            },
        },
    }
    row = build_preclassification_record(bronze_event, run_id="run-001")
    assert row["ticket_id"] == "t-123"
    assert row["run_id"] == "run-001"
    assert row["model_type"] == "rules"
    assert row["model_version"] == "rules_pqrs_v1"
    assert row["predicted_type"] == "R"
    assert row["predicted_priority"] == "alta"
    assert row["score"] == 0.93
    assert row["explain_json"]["topic"] == "reclamo_facturacion"


def test_build_preclassification_record_fallbacks() -> None:
    bronze_event = {"ticket_id": "t-999", "data": {"pqrs_type": "Q", "priority": "media"}}
    row = build_preclassification_record(bronze_event)
    assert row["model_version"] == "rules_pqrs_v1"
    assert row["predicted_type"] == "Q"
    assert row["predicted_priority"] == "media"
    assert row["score"] == 0.0
