from pathlib import Path

from apps.simulator.generate_pqrs_data import (
    build_event,
    generate_events,
    generate_simulation_events,
    load_geo_probability_rows,
)


def test_build_event_has_required_keys() -> None:
    event = build_event(seed=42)
    assert set(("event_id", "ticket_id", "event_type", "ts", "data")).issubset(event.keys())
    assert event["data"]["priority"] in {"baja", "media", "alta"}


def test_generate_events_count() -> None:
    events = generate_events(count=3, seed=10)
    assert len(events) == 3


def test_load_geo_probability_rows_merges_duplicate_codes(tmp_path: Path) -> None:
    csv_path = tmp_path / "probabilidad_municipio.csv"
    csv_path.write_text(
        "\"dane_department_code\";\"department_name\";\"dane_city_code\";\"city_name\";\"probability\"\n"
        "\"68\";\"Santander\";\"68081\";\"Barrancabermeja\";\"0.2\"\n"
        "\"68\";\"Santander\";\"68081\";\"Barrancabermeja\";\"0.3\"\n"
        "\"11\";\"Bogota\";\"11001\";\"Bogota\";\"0.5\"\n",
        encoding="utf-8",
    )

    rows = load_geo_probability_rows(csv_path)
    assert len(rows) == 2
    probs = {row["dane_city_code"]: row["probability"] for row in rows}
    assert round(probs["68081"], 6) == 0.5
    assert round(probs["11001"], 6) == 0.5


def test_generate_simulation_events_has_multiple_event_types(tmp_path: Path) -> None:
    csv_path = tmp_path / "probabilidad_municipio.csv"
    csv_path.write_text(
        "\"dane_department_code\";\"department_name\";\"dane_city_code\";\"city_name\";\"probability\"\n"
        "\"11\";\"Bogota\";\"11001\";\"Bogota\";\"1.0\"\n",
        encoding="utf-8",
    )
    config = {
        "seed": 123,
        "date_range": {"start": "2026-01-01", "end": "2026-01-01"},
        "volume_daily_avg": 3,
        "spike": {"window_count": 0},
        "geo_probability_csv": str(csv_path),
        "channel_probs": {"email": 0.38, "webform": 0.31, "chat": 0.14, "call": 0.11, "other_digital": 0.06},
        "sla_business_days": {"P": 15, "Q": 10, "R": 8, "S": 20},
    }

    events = generate_simulation_events(config=config, seed=123)
    event_types = {event["event_type"] for event in events}
    assert {"TICKET_CREATED", "MESSAGE_ADDED", "STATUS_CHANGED"}.issubset(event_types)
    created = [event for event in events if event["event_type"] == "TICKET_CREATED"]
    assert created
    assert all("dane_city_code" in event["data"] for event in created)
