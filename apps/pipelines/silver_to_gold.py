from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


def aggregate_volume_daily(tickets: list[dict]) -> dict[tuple[str, str], int]:
    counters: dict[tuple[str, str], int] = {}
    for ticket in tickets:
        key = (ticket.get("source_channel", "unknown"), ticket.get("pqrs_type", "P"))
        counters[key] = counters.get(key, 0) + 1
    return counters


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


def _to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _date_str(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.date().isoformat()


def _safe_text(value: Any, fallback: str = "unknown") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _safe_city_code(value: Any) -> str:
    if value is None:
        return "00000"
    text = str(value).strip()
    if not text:
        return "00000"
    if len(text) > 5:
        return text[:5]
    return text.zfill(5) if text.isdigit() and len(text) < 5 else text


def _date_range(min_day: str, max_day: str) -> list[str]:
    start = date.fromisoformat(min_day)
    end = date.fromisoformat(max_day)
    days: list[str] = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def _build_kpi_volume_daily(tickets: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    counters: dict[tuple[str, str, str], int] = defaultdict(int)

    for ticket in tickets:
        created = _to_dt(ticket.get("created_at"))
        day = _date_str(created)
        if day is None:
            continue
        channel = _safe_text(ticket.get("source_channel"))
        pqrs_type = _safe_text(ticket.get("pqrs_type"), "P")
        counters[(day, channel, pqrs_type)] += 1

    rows: list[dict[str, Any]] = []
    for (day, channel, pqrs_type), count in sorted(counters.items()):
        rows.append(
            {
                "day": day,
                "channel": channel,
                "pqrs_type": pqrs_type,
                "tickets_count": count,
                "run_id": run_id,
            }
        )
    return rows


def _build_kpi_backlog_daily(tickets: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    all_days = sorted({_date_str(_to_dt(ticket.get("created_at"))) for ticket in tickets if ticket.get("created_at")})
    rows: list[dict[str, Any]] = []

    for day in all_days:
        if day is None:
            continue
        day_dt = datetime.fromisoformat(day)
        counters: dict[tuple[str, str], int] = defaultdict(int)

        for ticket in tickets:
            created = _to_dt(ticket.get("created_at"))
            closed = _to_dt(ticket.get("closed_at"))
            if created is None:
                continue
            if created.date() > day_dt.date():
                continue
            if closed is not None and closed.date() <= day_dt.date():
                continue

            pqrs_type = _safe_text(ticket.get("pqrs_type"), "P")
            region = _safe_text(ticket.get("region"))
            counters[(pqrs_type, region)] += 1

        for (pqrs_type, region), backlog_count in sorted(counters.items()):
            rows.append(
                {
                    "day": day,
                    "pqrs_type": pqrs_type,
                    "region": region,
                    "backlog_count": backlog_count,
                    "run_id": run_id,
                }
            )

    return rows


def _build_kpi_sla_daily(tickets: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for ticket in tickets:
        closed = _to_dt(ticket.get("closed_at"))
        if closed is None:
            continue
        day = closed.date().isoformat()
        pqrs_type = _safe_text(ticket.get("pqrs_type"), "P")
        grouped[(day, pqrs_type)].append(ticket)

    rows: list[dict[str, Any]] = []
    for (day, pqrs_type), items in sorted(grouped.items()):
        total = len(items)
        within = 0
        overdue = 0
        overdue_days_values: list[float] = []

        for ticket in items:
            closed = _to_dt(ticket.get("closed_at"))
            due = _to_dt(ticket.get("sla_due_at"))
            if closed is None or due is None:
                continue
            if closed <= due:
                within += 1
            else:
                overdue += 1
                overdue_days_values.append((closed - due).total_seconds() / 86400)

        within_sla_pct = round((within / total) * 100, 2) if total else 0.0
        avg_overdue_days = round(sum(overdue_days_values) / len(overdue_days_values), 2) if overdue_days_values else 0.0

        rows.append(
            {
                "day": day,
                "pqrs_type": pqrs_type,
                "within_sla_pct": within_sla_pct,
                "overdue_count": overdue,
                "avg_overdue_days": avg_overdue_days,
                "run_id": run_id,
            }
        )

    return rows


def _geo_dims(ticket: dict[str, Any]) -> tuple[str, str, str]:
    region_name = _safe_text(ticket.get("region_name") or ticket.get("region"))
    department_name = _safe_text(ticket.get("department_name") or ticket.get("region"))
    dane_city_code = _safe_city_code(ticket.get("dane_city_code"))
    return region_name, department_name, dane_city_code


def _build_kpi_volume_geo_daily(tickets: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    counters: dict[tuple[str, str, str, str, str, str], int] = defaultdict(int)
    for ticket in tickets:
        created = _to_dt(ticket.get("created_at"))
        day = _date_str(created)
        if day is None:
            continue
        region_name, department_name, dane_city_code = _geo_dims(ticket)
        pqrs_type = _safe_text(ticket.get("pqrs_type"), "P")
        channel = _safe_text(ticket.get("source_channel"))
        counters[(day, region_name, department_name, dane_city_code, pqrs_type, channel)] += 1

    rows: list[dict[str, Any]] = []
    for (day, region_name, department_name, dane_city_code, pqrs_type, channel), count in sorted(counters.items()):
        rows.append(
            {
                "day": day,
                "region_name": region_name,
                "department_name": department_name,
                "dane_city_code": dane_city_code,
                "pqrs_type": pqrs_type,
                "channel": channel,
                "tickets_count": count,
                "run_id": run_id,
            }
        )
    return rows


def _build_kpi_backlog_geo_daily(tickets: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    all_days = sorted({_date_str(_to_dt(ticket.get("created_at"))) for ticket in tickets if ticket.get("created_at")})
    rows: list[dict[str, Any]] = []

    for day in all_days:
        if day is None:
            continue
        day_dt = datetime.fromisoformat(day)
        counters: dict[tuple[str, str, str, str], int] = defaultdict(int)

        for ticket in tickets:
            created = _to_dt(ticket.get("created_at"))
            closed = _to_dt(ticket.get("closed_at"))
            if created is None:
                continue
            if created.date() > day_dt.date():
                continue
            if closed is not None and closed.date() <= day_dt.date():
                continue

            region_name, department_name, dane_city_code = _geo_dims(ticket)
            pqrs_type = _safe_text(ticket.get("pqrs_type"), "P")
            counters[(region_name, department_name, dane_city_code, pqrs_type)] += 1

        for (region_name, department_name, dane_city_code, pqrs_type), backlog_count in sorted(counters.items()):
            rows.append(
                {
                    "day": day,
                    "region_name": region_name,
                    "department_name": department_name,
                    "dane_city_code": dane_city_code,
                    "pqrs_type": pqrs_type,
                    "backlog_count": backlog_count,
                    "run_id": run_id,
                }
            )

    return rows


def _build_kpi_sla_geo_daily(tickets: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)

    for ticket in tickets:
        closed = _to_dt(ticket.get("closed_at"))
        if closed is None:
            continue
        day = closed.date().isoformat()
        region_name, department_name, dane_city_code = _geo_dims(ticket)
        pqrs_type = _safe_text(ticket.get("pqrs_type"), "P")
        grouped[(day, region_name, department_name, dane_city_code, pqrs_type)].append(ticket)

    rows: list[dict[str, Any]] = []
    for (day, region_name, department_name, dane_city_code, pqrs_type), items in sorted(grouped.items()):
        total = len(items)
        within = 0
        overdue = 0
        overdue_days_values: list[float] = []

        for ticket in items:
            closed = _to_dt(ticket.get("closed_at"))
            due = _to_dt(ticket.get("sla_due_at"))
            if closed is None or due is None:
                continue
            if closed <= due:
                within += 1
            else:
                overdue += 1
                overdue_days_values.append((closed - due).total_seconds() / 86400)

        within_sla_pct = round((within / total) * 100, 2) if total else 0.0
        avg_overdue_days = round(sum(overdue_days_values) / len(overdue_days_values), 2) if overdue_days_values else 0.0
        rows.append(
            {
                "day": day,
                "region_name": region_name,
                "department_name": department_name,
                "dane_city_code": dane_city_code,
                "pqrs_type": pqrs_type,
                "within_sla_pct": within_sla_pct,
                "overdue_count": overdue,
                "avg_overdue_days": avg_overdue_days,
                "run_id": run_id,
            }
        )

    return rows


def _with_timeseries_metrics(rows: list[dict[str, Any]], key_fields: tuple[str, ...], run_id: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], dict[str, int]] = defaultdict(dict)
    all_days: set[str] = set()

    for row in rows:
        key = tuple(_safe_text(row.get(field)) for field in key_fields)
        day = _safe_text(row.get("day"))
        count = int(row.get("tickets_count", 0))
        grouped[key][day] = count
        all_days.add(day)

    if not all_days:
        return []

    min_day = min(all_days)
    max_day = max(all_days)
    days = _date_range(min_day, max_day)

    output: list[dict[str, Any]] = []
    for key in sorted(grouped.keys()):
        series = grouped[key]
        counts_by_day = [series.get(day, 0) for day in days]

        for idx, day in enumerate(days):
            current = counts_by_day[idx]
            prev_day = counts_by_day[idx - 1] if idx > 0 else 0
            prev_week = counts_by_day[idx - 7] if idx > 6 else 0
            win_start = max(0, idx - 6)
            rolling_window = counts_by_day[win_start : idx + 1]
            mavg_7d = round(sum(rolling_window) / len(rolling_window), 2)

            pct_vs_prev_day = round(((current - prev_day) / prev_day) * 100, 2) if prev_day > 0 else 0.0
            pct_vs_prev_week = round(((current - prev_week) / prev_week) * 100, 2) if prev_week > 0 else 0.0

            row: dict[str, Any] = {
                "day": day,
                "tickets_count": current,
                "tickets_mavg_7d": mavg_7d,
                "pct_vs_prev_day": pct_vs_prev_day,
                "pct_vs_prev_week": pct_vs_prev_week,
                "run_id": run_id,
            }
            for pos, field in enumerate(key_fields):
                row[field] = key[pos]
            output.append(row)

    return output


def _build_kpi_volume_dept_daily(kpi_volume_geo: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    aggregated: dict[tuple[str, str, str, str], int] = defaultdict(int)
    for row in kpi_volume_geo:
        key = (
            _safe_text(row.get("day")),
            _safe_text(row.get("department_name")),
            _safe_text(row.get("pqrs_type"), "P"),
            _safe_text(row.get("channel")),
        )
        aggregated[key] += int(row.get("tickets_count", 0))

    base_rows = [
        {
            "day": day,
            "department_name": department_name,
            "pqrs_type": pqrs_type,
            "channel": channel,
            "tickets_count": count,
        }
        for (day, department_name, pqrs_type, channel), count in sorted(aggregated.items())
    ]
    return _with_timeseries_metrics(base_rows, ("department_name", "pqrs_type", "channel"), run_id)


def _build_kpi_volume_national_daily(kpi_volume_geo: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    aggregated: dict[tuple[str, str, str], int] = defaultdict(int)
    for row in kpi_volume_geo:
        key = (
            _safe_text(row.get("day")),
            _safe_text(row.get("pqrs_type"), "P"),
            _safe_text(row.get("channel")),
        )
        aggregated[key] += int(row.get("tickets_count", 0))

    base_rows = [
        {
            "day": day,
            "pqrs_type": pqrs_type,
            "channel": channel,
            "tickets_count": count,
        }
        for (day, pqrs_type, channel), count in sorted(aggregated.items())
    ]
    return _with_timeseries_metrics(base_rows, ("pqrs_type", "channel"), run_id)


def run_silver_to_gold(silver_dir: Path, output_dir: Path, run_id: str) -> dict[str, int]:
    tickets_path = silver_dir / "tickets.jsonl"
    tickets = _read_jsonl(tickets_path)

    kpi_volume = _build_kpi_volume_daily(tickets=tickets, run_id=run_id)
    kpi_backlog = _build_kpi_backlog_daily(tickets=tickets, run_id=run_id)
    kpi_sla = _build_kpi_sla_daily(tickets=tickets, run_id=run_id)
    kpi_volume_geo = _build_kpi_volume_geo_daily(tickets=tickets, run_id=run_id)
    kpi_backlog_geo = _build_kpi_backlog_geo_daily(tickets=tickets, run_id=run_id)
    kpi_sla_geo = _build_kpi_sla_geo_daily(tickets=tickets, run_id=run_id)
    kpi_volume_dept = _build_kpi_volume_dept_daily(kpi_volume_geo=kpi_volume_geo, run_id=run_id)
    kpi_volume_national = _build_kpi_volume_national_daily(kpi_volume_geo=kpi_volume_geo, run_id=run_id)

    _write_jsonl(output_dir / "kpi_volume_daily.jsonl", kpi_volume)
    _write_jsonl(output_dir / "kpi_backlog_daily.jsonl", kpi_backlog)
    _write_jsonl(output_dir / "kpi_sla_daily.jsonl", kpi_sla)
    _write_jsonl(output_dir / "kpi_volume_geo_daily.jsonl", kpi_volume_geo)
    _write_jsonl(output_dir / "kpi_backlog_geo_daily.jsonl", kpi_backlog_geo)
    _write_jsonl(output_dir / "kpi_sla_geo_daily.jsonl", kpi_sla_geo)
    _write_jsonl(output_dir / "kpi_volume_dept_daily.jsonl", kpi_volume_dept)
    _write_jsonl(output_dir / "kpi_volume_national_daily.jsonl", kpi_volume_national)

    return {
        "silver_tickets_rows": len(tickets),
        "gold_kpi_volume_rows": len(kpi_volume),
        "gold_kpi_backlog_rows": len(kpi_backlog),
        "gold_kpi_sla_rows": len(kpi_sla),
        "gold_kpi_volume_geo_rows": len(kpi_volume_geo),
        "gold_kpi_backlog_geo_rows": len(kpi_backlog_geo),
        "gold_kpi_sla_geo_rows": len(kpi_sla_geo),
        "gold_kpi_volume_dept_rows": len(kpi_volume_dept),
        "gold_kpi_volume_national_rows": len(kpi_volume_national),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate Silver datasets into Gold KPIs.")
    parser.add_argument("--silver-dir", default="data/silver")
    parser.add_argument("--output-dir", default="data/gold")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    stats = run_silver_to_gold(
        silver_dir=Path(args.silver_dir),
        output_dir=Path(args.output_dir),
        run_id=args.run_id,
    )
    print(json.dumps(stats, ensure_ascii=True))


if __name__ == "__main__":
    main()
