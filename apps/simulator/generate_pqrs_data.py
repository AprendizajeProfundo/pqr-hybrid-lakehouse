from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from random import Random
from typing import Any
from uuid import UUID, uuid4


DEFAULT_CONFIG_PATH = "docs/07-config/pqrs_simulation_v1.yaml"
DEFAULT_GEO_PROBABILITY_CSV = "data/dane/probabilidad_municipio.csv"
RULES_VERSION = "rules_pqrs_v1"
PRECLASS_METHOD = "rules_synthetic_v1"

CHANNEL_PROBS_DEFAULT = {
    "email": 0.38,
    "webform": 0.31,
    "chat": 0.14,
    "call": 0.11,
    "other_digital": 0.06,
}

PQRS_TYPE_PROBS_DEFAULT = {
    "P": 0.30,
    "Q": 0.25,
    "R": 0.30,
    "S": 0.15,
}

PRIORITY_PROBS_DEFAULT = {
    "alta": 0.10,
    "media": 0.50,
    "baja": 0.40,
}

SLA_BUSINESS_DAYS_DEFAULT = {
    "P": 15,
    "Q": 10,
    "R": 8,
    "S": 20,
}

STATUS_ACTORS = {
    "RECEIVED": "system",
    "RADICATED": "system",
    "CLASSIFIED": "agent",
    "ASSIGNED": "agent",
    "IN_PROGRESS": "agent",
    "ON_HOLD": "agent",
    "RESPONDED": "agent",
    "CLOSED": "agent",
    "ARCHIVED": "system",
    "REOPENED": "agent",
}

TOPIC_CATALOG = (
    {
        "topic": "solicitud_certificado",
        "pqrs_type": "P",
        "priority": "media",
        "keywords": ("solicitud", "informacion", "certificacion", "requiero"),
        "templates": (
            "Solicito informacion para obtener la certificacion del tramite {external_id}.",
            "Requiero certificacion y orientacion sobre el proceso asociado al caso {external_id}.",
        ),
    },
    {
        "topic": "queja_atencion_funcionario",
        "pqrs_type": "Q",
        "priority": "media",
        "keywords": ("queja", "funcionario", "irrespeto", "maltrato"),
        "templates": (
            "Presento queja por irrespeto de un funcionario durante la atencion del ticket {external_id}.",
            "Radico queja por maltrato recibido en el punto de atencion para el caso {external_id}.",
        ),
    },
    {
        "topic": "reclamo_facturacion",
        "pqrs_type": "R",
        "priority": "alta",
        "keywords": ("reclamo", "cobro", "factura", "error", "urgente"),
        "templates": (
            "Interpongo reclamo por error de factura y cobro indebido en el expediente {external_id}.",
            "Existe un cobro incorrecto en mi factura; solicito correccion urgente del caso {external_id}.",
        ),
    },
    {
        "topic": "sugerencia_mejora_servicio",
        "pqrs_type": "S",
        "priority": "baja",
        "keywords": ("sugiero", "mejorar", "idea", "sugerencia"),
        "templates": (
            "Sugiero mejorar el flujo digital de radicacion para el servicio asociado a {external_id}.",
            "Comparto una idea para mejorar tiempos de respuesta en el tramite {external_id}.",
        ),
    },
)


def _uuid_str(rng: Random | None = None) -> str:
    if rng is None:
        value = str(uuid4())
    else:
        value = str(UUID(int=rng.getrandbits(128), version=4))
    UUID(value)
    return value


def _weighted_choice(rng: Random, weighted_values: list[tuple[str, float]]) -> str:
    values = [item[0] for item in weighted_values]
    weights = [item[1] for item in weighted_values]
    return rng.choices(values, weights=weights, k=1)[0]


def _normalize_probabilities(probabilities: dict[str, float]) -> dict[str, float]:
    cleaned = {key: float(value) for key, value in probabilities.items() if float(value) > 0}
    total = sum(cleaned.values())
    if total <= 0:
        raise ValueError("La suma de probabilidades debe ser mayor a cero.")
    return {key: value / total for key, value in cleaned.items()}


def _build_semantic_payload(rng: Random, external_id: str) -> dict[str, Any]:
    topic_cfg = rng.choice(TOPIC_CATALOG)
    text = rng.choice(topic_cfg["templates"]).format(external_id=external_id)
    score = round(rng.uniform(0.80, 0.99), 2)
    return {
        "subject": f"{topic_cfg['topic']} - {external_id}",
        "text": text,
        "text_len": len(text),
        "topic_preclassified": topic_cfg["topic"],
        "preclassifier": {
            "method": PRECLASS_METHOD,
            "rules_version": RULES_VERSION,
            "topic": topic_cfg["topic"],
            "predicted_pqrs_type": topic_cfg["pqrs_type"],
            "predicted_priority": topic_cfg["priority"],
            "score": score,
            "matched_keywords": list(topic_cfg["keywords"]),
        },
    }


def _parse_iso_date(value: str) -> date:
    return datetime.fromisoformat(value).date()


def _iter_days(start: date, end: date) -> list[date]:
    if end < start:
        raise ValueError("date_range.end no puede ser menor que date_range.start")
    days: list[date] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def _add_business_days(base_dt: datetime, business_days: int) -> datetime:
    result = base_dt
    pending = max(0, business_days)
    while pending > 0:
        result += timedelta(days=1)
        if result.weekday() < 5:
            pending -= 1
    return result


def _merge_probability_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = (row.get("dane_city_code") or "").strip()
        if not code:
            continue
        prob = float((row.get("probability") or "0").strip() or 0)
        if prob <= 0:
            continue

        if code not in merged:
            merged[code] = {
                "dane_city_code": code,
                "city_name": (row.get("city_name") or "").strip(),
                "department_name": (row.get("department_name") or "").strip(),
                "probability": prob,
            }
        else:
            merged[code]["probability"] += prob
    if not merged:
        raise ValueError("No se encontraron probabilidades geograficas validas en el CSV.")

    total = sum(item["probability"] for item in merged.values())
    for item in merged.values():
        item["probability"] /= total
    return list(merged.values())


def load_geo_probability_rows(csv_path: Path) -> list[dict[str, Any]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe archivo de probabilidades geograficas: {csv_path}")

    with csv_path.open(encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp, delimiter=";", quotechar='"')
        rows = [row for row in reader]
    return _merge_probability_rows(rows)


def _build_spike_days(
    rng: Random,
    days: list[date],
    window_count: int,
    min_window_days: int,
    max_window_days: int,
) -> set[date]:
    if len(days) < min_window_days or window_count <= 0:
        return set()

    spike_days: set[date] = set()
    max_start = len(days) - min_window_days
    if max_start < 0:
        return set()

    attempts = 0
    while len(spike_days) < window_count * min_window_days and attempts < window_count * 40:
        attempts += 1
        start_idx = rng.randint(0, max_start)
        window_size = rng.randint(min_window_days, min(max_window_days, len(days) - start_idx))
        candidate = set(days[start_idx : start_idx + window_size])

        if spike_days.intersection(candidate):
            continue

        spike_days.update(candidate)
        if len(spike_days) >= len(days):
            break

    return spike_days


def _generate_daily_volumes(rng: Random, days: list[date], config: dict[str, Any]) -> dict[date, int]:
    volume_daily_avg = int(config.get("volume_daily_avg", 1150))

    spike_cfg = config.get("spike", {}) or {}
    spike_min_volume = int(spike_cfg.get("min_daily", 3000))
    spike_max_volume = int(spike_cfg.get("max_daily", 4000))
    spike_min_days = int(spike_cfg.get("min_consecutive_days", 5))
    spike_max_days = int(spike_cfg.get("max_consecutive_days", 10))
    spike_window_count = int(spike_cfg.get("window_count", max(1, len(days) // 90) if len(days) >= 30 else 0))

    spike_days = _build_spike_days(
        rng=rng,
        days=days,
        window_count=spike_window_count,
        min_window_days=spike_min_days,
        max_window_days=spike_max_days,
    )

    volumes: dict[date, int] = {}
    std_dev = max(1.0, volume_daily_avg * 0.08)

    for day in days:
        if day in spike_days:
            volumes[day] = rng.randint(spike_min_volume, spike_max_volume)
            continue

        sampled = int(round(rng.gauss(volume_daily_avg, std_dev)))
        volumes[day] = max(1, sampled)

    return volumes


def _read_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}

    try:
        import yaml  # type: ignore
        with config_path.open("r", encoding="utf-8") as fp:
            payload = yaml.safe_load(fp) or {}
    except Exception:
        payload = _parse_simple_yaml(config_path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("El archivo de configuracion debe contener un objeto YAML en el nivel raiz.")
    return payload


def _parse_scalar(raw: str) -> Any:
    text = raw.strip()
    if text == "":
        return None
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1]
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def _parse_simple_yaml(content: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    for raw_line in content.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        container = stack[-1][1]

        if stripped.startswith("- "):
            value = _parse_scalar(stripped[2:])
            if not isinstance(container, list):
                raise ValueError("YAML invalido: item de lista fuera de contexto.")
            container.append(value)
            continue

        if ":" not in stripped:
            raise ValueError(f"YAML invalido: no se pudo parsear linea '{raw_line}'")

        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        if raw_value == "":
            next_container: Any
            if key in ("geo_regions",):
                next_container = []
            else:
                next_container = {}
            if isinstance(container, dict):
                container[key] = next_container
            else:
                raise ValueError("YAML invalido: clave fuera de objeto.")
            stack.append((indent, next_container))
            continue

        if isinstance(container, dict):
            container[key] = _parse_scalar(raw_value)
        else:
            raise ValueError("YAML invalido: asignacion clave-valor fuera de objeto.")

    return root


def _generate_ticket_timestamps(
    rng: Random,
    created_at: datetime,
    pqrs_type: str,
    sla_breach_rate: float,
    sla_business_days: dict[str, int],
) -> dict[str, datetime]:
    radicated_at = created_at + timedelta(minutes=rng.randint(5, 180))
    sla_days = int(sla_business_days.get(pqrs_type, 10))
    is_breach = rng.random() < sla_breach_rate

    if is_breach:
        target_days = sla_days + rng.randint(1, 6)
    else:
        target_days = max(1, sla_days - rng.randint(0, 4))

    closed_at = _add_business_days(radicated_at, target_days) + timedelta(hours=rng.randint(1, 20))
    responded_at = closed_at - timedelta(hours=rng.randint(1, 12))
    responded_at = max(responded_at, radicated_at + timedelta(hours=2))
    archived_at = closed_at + timedelta(hours=rng.randint(4, 72))

    return {
        "radicated_at": radicated_at,
        "responded_at": responded_at,
        "closed_at": closed_at,
        "archived_at": archived_at,
    }


def _generate_status_sequence(
    rng: Random,
    ticket_id: str,
    timestamps: dict[str, datetime],
) -> list[dict[str, Any]]:
    radicated_at = timestamps["radicated_at"]
    responded_at = timestamps["responded_at"]
    closed_at = timestamps["closed_at"]
    archived_at = timestamps["archived_at"]

    classified_at = radicated_at + timedelta(hours=rng.randint(1, 6))
    assigned_at = classified_at + timedelta(hours=rng.randint(1, 8))
    in_progress_at = assigned_at + timedelta(hours=rng.randint(1, 24))

    status_rows: list[tuple[str, str, datetime]] = [
        ("RECEIVED", "RADICATED", radicated_at),
        ("RADICATED", "CLASSIFIED", classified_at),
        ("CLASSIFIED", "ASSIGNED", assigned_at),
        ("ASSIGNED", "IN_PROGRESS", in_progress_at),
    ]

    if rng.random() < 0.18:
        hold_at = in_progress_at + timedelta(hours=rng.randint(4, 24))
        resume_at = hold_at + timedelta(hours=rng.randint(4, 48))
        if resume_at < responded_at:
            status_rows.append(("IN_PROGRESS", "ON_HOLD", hold_at))
            status_rows.append(("ON_HOLD", "IN_PROGRESS", resume_at))

    status_rows.extend(
        [
            ("IN_PROGRESS", "RESPONDED", responded_at),
            ("RESPONDED", "CLOSED", closed_at),
            ("CLOSED", "ARCHIVED", archived_at),
        ]
    )

    events: list[dict[str, Any]] = []
    for status_from, status_to, ts in sorted(status_rows, key=lambda item: item[2]):
        events.append(
            {
                "event_id": _uuid_str(rng),
                "ticket_id": ticket_id,
                "event_type": "STATUS_CHANGED",
                "ts": ts.isoformat(),
                "data": {
                    "status_from": status_from,
                    "status_to": status_to,
                    "actor_role": STATUS_ACTORS.get(status_to, "agent"),
                },
            }
        )
    return events


def _generate_message_events(
    rng: Random,
    ticket_id: str,
    created_at: datetime,
    responded_at: datetime,
    citizen_text: str,
) -> list[dict[str, Any]]:
    citizen_ts = created_at + timedelta(minutes=rng.randint(1, 120))
    agent_ts = responded_at - timedelta(minutes=rng.randint(10, 180))
    if agent_ts <= citizen_ts:
        agent_ts = citizen_ts + timedelta(minutes=30)

    agent_reply = "Hemos recibido su solicitud y estamos gestionando su caso."

    return [
        {
            "event_id": _uuid_str(rng),
            "ticket_id": ticket_id,
            "event_type": "MESSAGE_ADDED",
            "ts": citizen_ts.isoformat(),
            "data": {
                "role": "citizen",
                "text": citizen_text,
                "text_len": len(citizen_text),
            },
        },
        {
            "event_id": _uuid_str(rng),
            "ticket_id": ticket_id,
            "event_type": "MESSAGE_ADDED",
            "ts": agent_ts.isoformat(),
            "data": {
                "role": "agent",
                "text": agent_reply,
                "text_len": len(agent_reply),
            },
        },
    ]


def _generate_ticket_events(
    rng: Random,
    ticket_counter: int,
    event_counter: int,
    day_value: date,
    channel_probs: dict[str, float],
    pqrs_type_probs: dict[str, float],
    priority_probs: dict[str, float],
    geo_rows: list[dict[str, Any]],
    sla_breach_rate: float,
    sla_business_days: dict[str, int],
) -> tuple[list[dict[str, Any]], int]:
    created_at = datetime.combine(day_value, time(hour=rng.randint(0, 23), minute=rng.randint(0, 59)), tzinfo=timezone.utc)
    external_id = f"PQRS-{day_value.strftime('%Y%m%d')}-{ticket_counter:06d}"
    ticket_id = _uuid_str(rng)

    semantic_payload = _build_semantic_payload(rng, external_id)
    pqrs_type = _weighted_choice(rng, list(pqrs_type_probs.items()))
    priority = _weighted_choice(rng, list(priority_probs.items()))
    source_channel = _weighted_choice(rng, list(channel_probs.items()))

    geo_choice = rng.choices(geo_rows, weights=[row["probability"] for row in geo_rows], k=1)[0]
    timestamps = _generate_ticket_timestamps(
        rng=rng,
        created_at=created_at,
        pqrs_type=pqrs_type,
        sla_breach_rate=sla_breach_rate,
        sla_business_days=sla_business_days,
    )

    ticket_created = {
        "event_id": _uuid_str(rng),
        "ticket_id": ticket_id,
        "event_type": "TICKET_CREATED",
        "ts": created_at.isoformat(),
        "data": {
            "external_id": external_id,
            "source_channel": source_channel,
            "pqrs_type": pqrs_type,
            "priority": priority,
            "geo_region": geo_choice["department_name"],
            "geo_municipio": geo_choice["city_name"],
            "dane_city_code": geo_choice["dane_city_code"],
            "sla_business_days": int(sla_business_days.get(pqrs_type, 10)),
            "radicated_at": timestamps["radicated_at"].isoformat(),
            "sla_due_at": _add_business_days(timestamps["radicated_at"], int(sla_business_days.get(pqrs_type, 10))).isoformat(),
            "closed_at": timestamps["closed_at"].isoformat(),
            "subject": semantic_payload["subject"],
            "text": semantic_payload["text"],
            "text_len": semantic_payload["text_len"],
            "topic_preclassified": semantic_payload["topic_preclassified"],
            "preclassifier": semantic_payload["preclassifier"],
        },
    }

    message_events = _generate_message_events(
        rng=rng,
        ticket_id=ticket_id,
        created_at=created_at,
        responded_at=timestamps["responded_at"],
        citizen_text=semantic_payload["text"],
    )
    status_events = _generate_status_sequence(rng=rng, ticket_id=ticket_id, timestamps=timestamps)

    events = [ticket_created, *message_events, *status_events]
    events.sort(key=lambda item: item["ts"])
    event_counter += len(events)
    return events, event_counter


def generate_simulation_events(config: dict[str, Any], seed: int) -> list[dict[str, Any]]:
    rng = Random(seed)

    date_cfg = config.get("date_range", {}) or {}
    start = _parse_iso_date(date_cfg.get("start", "2025-09-01"))
    end = _parse_iso_date(date_cfg.get("end", "2026-02-28"))
    days = _iter_days(start, end)

    channel_probs = _normalize_probabilities(config.get("channel_probs", CHANNEL_PROBS_DEFAULT))
    pqrs_type_probs = _normalize_probabilities(config.get("pqrs_type_probs", PQRS_TYPE_PROBS_DEFAULT))
    priority_probs = _normalize_probabilities(config.get("priority_probs", PRIORITY_PROBS_DEFAULT))
    sla_business_days = {**SLA_BUSINESS_DAYS_DEFAULT, **(config.get("sla_business_days", {}) or {})}
    sla_breach_rate = float(config.get("sla_breach_rate", 0.10))

    geo_csv = Path(config.get("geo_probability_csv", DEFAULT_GEO_PROBABILITY_CSV))
    geo_rows = load_geo_probability_rows(geo_csv)

    daily_volumes = _generate_daily_volumes(rng=rng, days=days, config=config)

    all_events: list[dict[str, Any]] = []
    ticket_counter = 1
    event_counter = 1

    for day_value in days:
        day_count = daily_volumes[day_value]
        for _ in range(day_count):
            ticket_events, event_counter = _generate_ticket_events(
                rng=rng,
                ticket_counter=ticket_counter,
                event_counter=event_counter,
                day_value=day_value,
                channel_probs=channel_probs,
                pqrs_type_probs=pqrs_type_probs,
                priority_probs=priority_probs,
                geo_rows=geo_rows,
                sla_breach_rate=sla_breach_rate,
                sla_business_days=sla_business_days,
            )
            all_events.extend(ticket_events)
            ticket_counter += 1

    all_events.sort(key=lambda item: item["ts"])
    return all_events


def build_event(seed: int = 42) -> dict[str, Any]:
    rng = Random(seed)
    external_id = f"EXT-{rng.randint(1000, 9999)}"
    semantic_payload = _build_semantic_payload(rng, external_id)
    geo_rows = load_geo_probability_rows(Path(DEFAULT_GEO_PROBABILITY_CSV))
    geo_choice = rng.choices(geo_rows, weights=[row["probability"] for row in geo_rows], k=1)[0]
    pqrs_type = _weighted_choice(rng, list(PQRS_TYPE_PROBS_DEFAULT.items()))

    return {
        "event_id": _uuid_str(rng),
        "ticket_id": _uuid_str(rng),
        "event_type": "TICKET_CREATED",
        "ts": datetime.now(timezone.utc).isoformat(),
        "data": {
            "external_id": external_id,
            "source_channel": _weighted_choice(rng, list(CHANNEL_PROBS_DEFAULT.items())),
            "pqrs_type": pqrs_type,
            "priority": _weighted_choice(rng, list(PRIORITY_PROBS_DEFAULT.items())),
            "geo_region": geo_choice["department_name"],
            "geo_municipio": geo_choice["city_name"],
            "dane_city_code": geo_choice["dane_city_code"],
            "sla_business_days": SLA_BUSINESS_DAYS_DEFAULT[pqrs_type],
            "subject": semantic_payload["subject"],
            "text": semantic_payload["text"],
            "text_len": semantic_payload["text_len"],
            "topic_preclassified": semantic_payload["topic_preclassified"],
            "preclassifier": semantic_payload["preclassifier"],
        },
    }


def generate_events(count: int, seed: int = 42) -> list[dict[str, Any]]:
    return [build_event(seed + i) for i in range(count)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic PQRS raw events (JSONL).")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--count", type=int, default=None, help="Si se define, genera solo TICKET_CREATED simples (modo smoke).")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="data/raw/pqrs_events.jsonl")
    parser.add_argument("--start-date", default=None, help="Fecha inicial del run en formato YYYY-MM-DD.")
    parser.add_argument("--end-date", default=None, help="Fecha final del run en formato YYYY-MM-DD.")
    args = parser.parse_args()

    if args.count is not None:
        events = generate_events(count=args.count, seed=args.seed)
    else:
        config = _read_config(Path(args.config))
        date_cfg = config.get("date_range", {}) or {}
        if args.start_date is not None:
            date_cfg["start"] = args.start_date
        if args.end_date is not None:
            date_cfg["end"] = args.end_date
        config["date_range"] = date_cfg
        config_seed = int(config.get("seed", args.seed))
        events = generate_simulation_events(config=config, seed=config_seed)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(json.dumps(event, ensure_ascii=True) for event in events) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
