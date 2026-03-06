from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4


def build_upsert_statement() -> str:
    return (
        "INSERT INTO gold.kpi_volume_daily (day, channel, pqrs_type, tickets_count) "
        "VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (day, channel, pqrs_type) "
        "DO UPDATE SET tickets_count = EXCLUDED.tickets_count"
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _as_uuid(value: str | None) -> str:
    if value is None:
        return str(uuid4())
    return str(UUID(value))


def _fit_varchar(value: Any, max_len: int) -> Any:
    if value is None:
        return None
    text = str(value)
    if len(text) <= max_len:
        return text
    return text[:max_len]


def _connect():
    try:
        import psycopg2  # type: ignore
    except Exception as exc:
        raise RuntimeError("No se encontro psycopg2. Instala dependencia para cargar a Postgres.") from exc

    host = os.getenv("PGHOST", "127.0.0.1")
    port = int(os.getenv("PGPORT", "5432"))
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD", "localdev123")
    db_env = os.getenv("PGDATABASE")
    db_candidates = [db_env] if db_env else ["pqr_lakehouse", "moodledb", "postgres"]
    last_exc: Exception | None = None

    for dbname in db_candidates:
        try:
            conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'meta' AND table_name = 'etl_runs'
                    )
                    """
                )
                has_meta = bool(cur.fetchone()[0])
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'silver' AND table_name = 'tickets'
                    )
                    """
                )
                has_silver = bool(cur.fetchone()[0])

            if has_meta and has_silver:
                return conn, dbname

            conn.close()
        except psycopg2.OperationalError as exc:  # type: ignore[attr-defined]
            last_exc = exc
            if 'does not exist' in str(exc):
                continue
            raise

    if last_exc is not None:
        raise RuntimeError(
            "No se encontro una base Postgres valida para ETL. "
            "Define PGDATABASE apuntando a una DB con esquemas meta/silver/gold inicializados."
        ) from last_exc
    raise RuntimeError(
        "No se encontro una base Postgres valida para ETL. "
        "Define PGDATABASE apuntando a una DB con esquemas meta/silver/gold inicializados."
    )


def _insert_meta_run(cur, run_id: str, seed: int, date_min: str | None, date_max: str | None, executed_by: str) -> None:
    cur.execute(
        """
        INSERT INTO meta.etl_runs (
            run_id, seed, started_at, finished_at, status, date_min, date_max,
            executed_by, executor_role, execution_context, raw_objects_count,
            bronze_rows, silver_rows, gold_rows
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'SYSTEM', 'manual-cli', 1, 0, 0, 0)
        ON CONFLICT (run_id) DO UPDATE SET
            finished_at = EXCLUDED.finished_at,
            status = EXCLUDED.status,
            date_min = EXCLUDED.date_min,
            date_max = EXCLUDED.date_max,
            executed_by = EXCLUDED.executed_by,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            run_id,
            seed,
            datetime.now(timezone.utc),
            datetime.now(timezone.utc),
            "SUCCESS",
            date_min,
            date_max,
            executed_by,
        ),
    )


def _table_exists(cur, schema: str, table: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
        )
        """,
        (schema, table),
    )
    return bool(cur.fetchone()[0])


def _ensure_schema_compatibility(cur) -> None:
    cur.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    cur.execute("ALTER TABLE silver.tickets ADD COLUMN IF NOT EXISTS region_name VARCHAR(50)")
    cur.execute("ALTER TABLE silver.tickets ADD COLUMN IF NOT EXISTS department_name VARCHAR(50)")
    cur.execute("ALTER TABLE silver.tickets ADD COLUMN IF NOT EXISTS city_name VARCHAR(100)")
    cur.execute("ALTER TABLE silver.tickets ADD COLUMN IF NOT EXISTS dane_city_code VARCHAR(5)")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS gold.kpi_volume_geo_daily (
          day DATE NOT NULL,
          region_name VARCHAR(50) NOT NULL,
          department_name VARCHAR(50) NOT NULL,
          dane_city_code VARCHAR(5) NOT NULL,
          pqrs_type VARCHAR(1) NOT NULL,
          channel VARCHAR(20) NOT NULL,
          tickets_count INTEGER NOT NULL DEFAULT 0,
          run_id UUID REFERENCES meta.etl_runs(run_id),
          calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (day, region_name, department_name, dane_city_code, pqrs_type, channel)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS gold.kpi_backlog_geo_daily (
          day DATE NOT NULL,
          region_name VARCHAR(50) NOT NULL,
          department_name VARCHAR(50) NOT NULL,
          dane_city_code VARCHAR(5) NOT NULL,
          pqrs_type VARCHAR(1) NOT NULL,
          backlog_count INTEGER NOT NULL DEFAULT 0,
          run_id UUID REFERENCES meta.etl_runs(run_id),
          calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (day, region_name, department_name, dane_city_code, pqrs_type)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS gold.kpi_sla_geo_daily (
          day DATE NOT NULL,
          region_name VARCHAR(50) NOT NULL,
          department_name VARCHAR(50) NOT NULL,
          dane_city_code VARCHAR(5) NOT NULL,
          pqrs_type VARCHAR(1) NOT NULL,
          within_sla_pct NUMERIC(5,2) NOT NULL,
          overdue_count INTEGER NOT NULL DEFAULT 0,
          avg_overdue_days NUMERIC(5,2),
          run_id UUID REFERENCES meta.etl_runs(run_id),
          calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (day, region_name, department_name, dane_city_code, pqrs_type)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS gold.kpi_volume_dept_daily (
          day DATE NOT NULL,
          department_name VARCHAR(50) NOT NULL,
          pqrs_type VARCHAR(1) NOT NULL,
          channel VARCHAR(20) NOT NULL,
          tickets_count INTEGER NOT NULL DEFAULT 0,
          tickets_mavg_7d NUMERIC(12,2) NOT NULL DEFAULT 0,
          pct_vs_prev_day NUMERIC(8,2) NOT NULL DEFAULT 0,
          pct_vs_prev_week NUMERIC(8,2) NOT NULL DEFAULT 0,
          run_id UUID REFERENCES meta.etl_runs(run_id),
          calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (day, department_name, pqrs_type, channel)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS gold.kpi_volume_national_daily (
          day DATE NOT NULL,
          pqrs_type VARCHAR(1) NOT NULL,
          channel VARCHAR(20) NOT NULL,
          tickets_count INTEGER NOT NULL DEFAULT 0,
          tickets_mavg_7d NUMERIC(12,2) NOT NULL DEFAULT 0,
          pct_vs_prev_day NUMERIC(8,2) NOT NULL DEFAULT 0,
          pct_vs_prev_week NUMERIC(8,2) NOT NULL DEFAULT 0,
          run_id UUID REFERENCES meta.etl_runs(run_id),
          calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (day, pqrs_type, channel)
        )
        """
    )

    cur.execute(
        """
        CREATE OR REPLACE VIEW analytics.v_timeseries_national_daily AS
        SELECT
          day, pqrs_type, channel, tickets_count, tickets_mavg_7d, pct_vs_prev_day,
          pct_vs_prev_week, run_id, calculated_at
        FROM gold.kpi_volume_national_daily
        """
    )
    cur.execute(
        """
        CREATE OR REPLACE VIEW analytics.v_timeseries_department_daily AS
        SELECT
          day, department_name, pqrs_type, channel, tickets_count, tickets_mavg_7d,
          pct_vs_prev_day, pct_vs_prev_week, run_id, calculated_at
        FROM gold.kpi_volume_dept_daily
        """
    )
    cur.execute(
        """
        CREATE OR REPLACE VIEW analytics.v_geo_daily AS
        SELECT
          v.day,
          v.region_name,
          v.department_name,
          v.dane_city_code,
          v.pqrs_type,
          v.channel,
          v.tickets_count,
          b.backlog_count,
          s.within_sla_pct,
          s.overdue_count,
          s.avg_overdue_days
        FROM gold.kpi_volume_geo_daily v
        LEFT JOIN gold.kpi_backlog_geo_daily b
          ON v.day = b.day
         AND v.region_name = b.region_name
         AND v.department_name = b.department_name
         AND v.dane_city_code = b.dane_city_code
         AND v.pqrs_type = b.pqrs_type
        LEFT JOIN gold.kpi_sla_geo_daily s
          ON v.day = s.day
         AND v.region_name = s.region_name
         AND v.department_name = s.department_name
         AND v.dane_city_code = s.dane_city_code
         AND v.pqrs_type = s.pqrs_type
        """
    )


def _load_geo_lookup(cur) -> dict[str, tuple[str, str, str]]:
    if not _table_exists(cur, "silver", "dim_geo"):
        return {}
    cur.execute(
        """
        SELECT
          COALESCE(dane_city_code, '') AS dane_city_code,
          COALESCE(region_name, '') AS region_name,
          COALESCE(department_name, '') AS department_name,
          COALESCE(city_name, '') AS city_name
        FROM silver.dim_geo
        WHERE dane_city_code IS NOT NULL AND dane_city_code <> ''
        """
    )
    rows = cur.fetchall()
    return {
        str(dane_city_code).strip(): (str(region_name).strip(), str(department_name).strip(), str(city_name).strip())
        for dane_city_code, region_name, department_name, city_name in rows
    }


def run_load_to_postgres(
    run_id: str,
    silver_dir: Path,
    gold_dir: Path,
    seed: int = 42,
    executed_by: str = "etl-cli",
) -> dict[str, int]:
    try:
        from psycopg2.extras import Json, execute_values  # type: ignore
    except Exception as exc:
        raise RuntimeError("No se encontro psycopg2.extras para carga batch.") from exc

    run_id = _as_uuid(run_id)
    batch_size = int(os.getenv("ETL_BATCH_SIZE", "2000"))

    tickets = _read_jsonl(silver_dir / "tickets.jsonl")
    messages = _read_jsonl(silver_dir / "messages.jsonl")
    status_events = _read_jsonl(silver_dir / "status_events.jsonl")
    preclass = _read_jsonl(silver_dir / "preclassification.jsonl")

    kpi_volume = _read_jsonl(gold_dir / "kpi_volume_daily.jsonl")
    kpi_backlog = _read_jsonl(gold_dir / "kpi_backlog_daily.jsonl")
    kpi_sla = _read_jsonl(gold_dir / "kpi_sla_daily.jsonl")
    kpi_volume_geo = _read_jsonl(gold_dir / "kpi_volume_geo_daily.jsonl")
    kpi_backlog_geo = _read_jsonl(gold_dir / "kpi_backlog_geo_daily.jsonl")
    kpi_sla_geo = _read_jsonl(gold_dir / "kpi_sla_geo_daily.jsonl")
    kpi_volume_dept = _read_jsonl(gold_dir / "kpi_volume_dept_daily.jsonl")
    kpi_volume_national = _read_jsonl(gold_dir / "kpi_volume_national_daily.jsonl")

    date_min = min((row.get("day") for row in kpi_volume), default=None)
    date_max = max((row.get("day") for row in kpi_volume), default=None)

    conn, target_db = _connect()
    # _connect() valida tablas con SELECT; limpiamos estado transaccional previo
    # antes de entrar al bloque principal de escritura.
    try:
        conn.rollback()
    except Exception:
        pass
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            _ensure_schema_compatibility(cur)
            _insert_meta_run(cur, run_id=run_id, seed=seed, date_min=date_min, date_max=date_max, executed_by=executed_by)
            has_preclassification = _table_exists(cur, "silver", "preclassification")
            geo_lookup = _load_geo_lookup(cur)

            ticket_values = [
                (
                    row.get("ticket_id"),
                    row.get("external_id"),
                    row.get("source_channel"),
                    row.get("pqrs_type"),
                    row.get("priority"),
                    row.get("created_at"),
                    row.get("radicated_at"),
                    row.get("current_status"),
                    _fit_varchar(row.get("region"), 50),
                    _fit_varchar((geo_lookup.get(str(row.get("dane_city_code") or "").strip(), ("", "", ""))[0] or row.get("region_name") or row.get("region")), 50),
                    _fit_varchar((geo_lookup.get(str(row.get("dane_city_code") or "").strip(), ("", "", ""))[1] or row.get("department_name") or row.get("region")), 50),
                    _fit_varchar((geo_lookup.get(str(row.get("dane_city_code") or "").strip(), ("", "", ""))[2] or row.get("city_name")), 100),
                    _fit_varchar(row.get("dane_city_code"), 5),
                    row.get("sla_due_at"),
                    row.get("closed_at"),
                    run_id,
                )
                for row in tickets
            ]
            if ticket_values:
                execute_values(
                    cur,
                    """
                    INSERT INTO silver.tickets (
                        ticket_id, external_id, source_channel, pqrs_type, priority,
                        created_at, radicated_at, current_status, region,
                        region_name, department_name, city_name, dane_city_code,
                        sla_due_at, closed_at, run_id
                    ) VALUES %s
                    ON CONFLICT (ticket_id) DO UPDATE SET
                        source_channel = EXCLUDED.source_channel,
                        pqrs_type = EXCLUDED.pqrs_type,
                        priority = EXCLUDED.priority,
                        current_status = EXCLUDED.current_status,
                        region = EXCLUDED.region,
                        region_name = EXCLUDED.region_name,
                        department_name = EXCLUDED.department_name,
                        city_name = EXCLUDED.city_name,
                        dane_city_code = EXCLUDED.dane_city_code,
                        sla_due_at = EXCLUDED.sla_due_at,
                        closed_at = EXCLUDED.closed_at,
                        updated_ts = CURRENT_TIMESTAMP
                    """,
                    ticket_values,
                    page_size=batch_size,
                )

            message_values = [
                (
                    row.get("message_id"),
                    row.get("ticket_id"),
                    row.get("ts"),
                    row.get("role"),
                    row.get("text"),
                    row.get("text_len"),
                    run_id,
                )
                for row in messages
            ]
            if message_values:
                execute_values(
                    cur,
                    """
                    INSERT INTO silver.messages (message_id, ticket_id, ts, role, text, text_len, run_id)
                    VALUES %s
                    ON CONFLICT (message_id) DO NOTHING
                    """,
                    message_values,
                    page_size=batch_size,
                )

            status_values = [
                (
                    row.get("event_id"),
                    row.get("ticket_id"),
                    row.get("ts"),
                    row.get("status_from"),
                    row.get("status_to"),
                    row.get("actor_role"),
                    run_id,
                )
                for row in status_events
            ]
            if status_values:
                execute_values(
                    cur,
                    """
                    INSERT INTO silver.status_events (event_id, ticket_id, ts, status_from, status_to, actor_role, run_id)
                    VALUES %s
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    status_values,
                    page_size=batch_size,
                )

            preclass_loaded_rows = 0
            if has_preclassification:
                preclass_values = [
                    (
                        row.get("ticket_id"),
                        run_id,
                        row.get("model_type"),
                        row.get("model_version"),
                        row.get("predicted_type"),
                        row.get("predicted_priority"),
                        row.get("score"),
                        Json(row.get("explain_json", {})),
                    )
                    for row in preclass
                ]
                if preclass_values:
                    execute_values(
                        cur,
                        """
                        INSERT INTO silver.preclassification (
                            ticket_id, run_id, model_type, model_version,
                            predicted_type, predicted_priority, score, explain_json
                        ) VALUES %s
                        ON CONFLICT (ticket_id, run_id, model_version) DO UPDATE SET
                            predicted_type = EXCLUDED.predicted_type,
                            predicted_priority = EXCLUDED.predicted_priority,
                            score = EXCLUDED.score,
                            explain_json = EXCLUDED.explain_json
                        """,
                        preclass_values,
                        page_size=batch_size,
                    )
                    preclass_loaded_rows = len(preclass_values)

            kpi_volume_values = [
                (
                    row.get("day"),
                    row.get("channel"),
                    row.get("pqrs_type"),
                    row.get("tickets_count"),
                    run_id,
                )
                for row in kpi_volume
            ]
            if kpi_volume_values:
                execute_values(
                    cur,
                    """
                    INSERT INTO gold.kpi_volume_daily (day, channel, pqrs_type, tickets_count, run_id)
                    VALUES %s
                    ON CONFLICT (day, channel, pqrs_type) DO UPDATE SET
                        tickets_count = EXCLUDED.tickets_count,
                        run_id = EXCLUDED.run_id,
                        calculated_at = CURRENT_TIMESTAMP
                    """,
                    kpi_volume_values,
                    page_size=batch_size,
                )

            kpi_backlog_values = [
                (
                    row.get("day"),
                    row.get("pqrs_type"),
                    _fit_varchar(row.get("region"), 50),
                    row.get("backlog_count"),
                    run_id,
                )
                for row in kpi_backlog
            ]
            if kpi_backlog_values:
                execute_values(
                    cur,
                    """
                    INSERT INTO gold.kpi_backlog_daily (day, pqrs_type, region, backlog_count, run_id)
                    VALUES %s
                    ON CONFLICT (day, pqrs_type, region) DO UPDATE SET
                        backlog_count = EXCLUDED.backlog_count,
                        run_id = EXCLUDED.run_id,
                        calculated_at = CURRENT_TIMESTAMP
                    """,
                    kpi_backlog_values,
                    page_size=batch_size,
                )

            kpi_sla_values = [
                (
                    row.get("day"),
                    row.get("pqrs_type"),
                    row.get("within_sla_pct"),
                    row.get("overdue_count"),
                    row.get("avg_overdue_days"),
                    run_id,
                )
                for row in kpi_sla
            ]
            if kpi_sla_values:
                execute_values(
                    cur,
                    """
                    INSERT INTO gold.kpi_sla_daily (day, pqrs_type, within_sla_pct, overdue_count, avg_overdue_days, run_id)
                    VALUES %s
                    ON CONFLICT (day, pqrs_type) DO UPDATE SET
                        within_sla_pct = EXCLUDED.within_sla_pct,
                        overdue_count = EXCLUDED.overdue_count,
                        avg_overdue_days = EXCLUDED.avg_overdue_days,
                        run_id = EXCLUDED.run_id,
                        calculated_at = CURRENT_TIMESTAMP
                    """,
                    kpi_sla_values,
                    page_size=batch_size,
                )

            kpi_volume_geo_values = [
                (
                    row.get("day"),
                    _fit_varchar(row.get("region_name"), 50),
                    _fit_varchar(row.get("department_name"), 50),
                    _fit_varchar(row.get("dane_city_code"), 5),
                    row.get("pqrs_type"),
                    row.get("channel"),
                    row.get("tickets_count"),
                    run_id,
                )
                for row in kpi_volume_geo
            ]
            if kpi_volume_geo_values:
                execute_values(
                    cur,
                    """
                    INSERT INTO gold.kpi_volume_geo_daily (
                        day, region_name, department_name, dane_city_code, pqrs_type, channel, tickets_count, run_id
                    ) VALUES %s
                    ON CONFLICT (day, region_name, department_name, dane_city_code, pqrs_type, channel) DO UPDATE SET
                        tickets_count = EXCLUDED.tickets_count,
                        run_id = EXCLUDED.run_id,
                        calculated_at = CURRENT_TIMESTAMP
                    """,
                    kpi_volume_geo_values,
                    page_size=batch_size,
                )

            kpi_backlog_geo_values = [
                (
                    row.get("day"),
                    _fit_varchar(row.get("region_name"), 50),
                    _fit_varchar(row.get("department_name"), 50),
                    _fit_varchar(row.get("dane_city_code"), 5),
                    row.get("pqrs_type"),
                    row.get("backlog_count"),
                    run_id,
                )
                for row in kpi_backlog_geo
            ]
            if kpi_backlog_geo_values:
                execute_values(
                    cur,
                    """
                    INSERT INTO gold.kpi_backlog_geo_daily (
                        day, region_name, department_name, dane_city_code, pqrs_type, backlog_count, run_id
                    ) VALUES %s
                    ON CONFLICT (day, region_name, department_name, dane_city_code, pqrs_type) DO UPDATE SET
                        backlog_count = EXCLUDED.backlog_count,
                        run_id = EXCLUDED.run_id,
                        calculated_at = CURRENT_TIMESTAMP
                    """,
                    kpi_backlog_geo_values,
                    page_size=batch_size,
                )

            kpi_sla_geo_values = [
                (
                    row.get("day"),
                    _fit_varchar(row.get("region_name"), 50),
                    _fit_varchar(row.get("department_name"), 50),
                    _fit_varchar(row.get("dane_city_code"), 5),
                    row.get("pqrs_type"),
                    row.get("within_sla_pct"),
                    row.get("overdue_count"),
                    row.get("avg_overdue_days"),
                    run_id,
                )
                for row in kpi_sla_geo
            ]
            if kpi_sla_geo_values:
                execute_values(
                    cur,
                    """
                    INSERT INTO gold.kpi_sla_geo_daily (
                        day, region_name, department_name, dane_city_code, pqrs_type,
                        within_sla_pct, overdue_count, avg_overdue_days, run_id
                    ) VALUES %s
                    ON CONFLICT (day, region_name, department_name, dane_city_code, pqrs_type) DO UPDATE SET
                        within_sla_pct = EXCLUDED.within_sla_pct,
                        overdue_count = EXCLUDED.overdue_count,
                        avg_overdue_days = EXCLUDED.avg_overdue_days,
                        run_id = EXCLUDED.run_id,
                        calculated_at = CURRENT_TIMESTAMP
                    """,
                    kpi_sla_geo_values,
                    page_size=batch_size,
                )

            kpi_volume_dept_values = [
                (
                    row.get("day"),
                    _fit_varchar(row.get("department_name"), 50),
                    row.get("pqrs_type"),
                    row.get("channel"),
                    row.get("tickets_count"),
                    row.get("tickets_mavg_7d"),
                    row.get("pct_vs_prev_day"),
                    row.get("pct_vs_prev_week"),
                    run_id,
                )
                for row in kpi_volume_dept
            ]
            if kpi_volume_dept_values:
                execute_values(
                    cur,
                    """
                    INSERT INTO gold.kpi_volume_dept_daily (
                        day, department_name, pqrs_type, channel, tickets_count, tickets_mavg_7d,
                        pct_vs_prev_day, pct_vs_prev_week, run_id
                    ) VALUES %s
                    ON CONFLICT (day, department_name, pqrs_type, channel) DO UPDATE SET
                        tickets_count = EXCLUDED.tickets_count,
                        tickets_mavg_7d = EXCLUDED.tickets_mavg_7d,
                        pct_vs_prev_day = EXCLUDED.pct_vs_prev_day,
                        pct_vs_prev_week = EXCLUDED.pct_vs_prev_week,
                        run_id = EXCLUDED.run_id,
                        calculated_at = CURRENT_TIMESTAMP
                    """,
                    kpi_volume_dept_values,
                    page_size=batch_size,
                )

            kpi_volume_national_values = [
                (
                    row.get("day"),
                    row.get("pqrs_type"),
                    row.get("channel"),
                    row.get("tickets_count"),
                    row.get("tickets_mavg_7d"),
                    row.get("pct_vs_prev_day"),
                    row.get("pct_vs_prev_week"),
                    run_id,
                )
                for row in kpi_volume_national
            ]
            if kpi_volume_national_values:
                execute_values(
                    cur,
                    """
                    INSERT INTO gold.kpi_volume_national_daily (
                        day, pqrs_type, channel, tickets_count, tickets_mavg_7d, pct_vs_prev_day, pct_vs_prev_week, run_id
                    ) VALUES %s
                    ON CONFLICT (day, pqrs_type, channel) DO UPDATE SET
                        tickets_count = EXCLUDED.tickets_count,
                        tickets_mavg_7d = EXCLUDED.tickets_mavg_7d,
                        pct_vs_prev_day = EXCLUDED.pct_vs_prev_day,
                        pct_vs_prev_week = EXCLUDED.pct_vs_prev_week,
                        run_id = EXCLUDED.run_id,
                        calculated_at = CURRENT_TIMESTAMP
                    """,
                    kpi_volume_national_values,
                    page_size=batch_size,
                )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "database": target_db,
        "silver_tickets_rows": len(tickets),
        "silver_messages_rows": len(messages),
        "silver_status_events_rows": len(status_events),
        "silver_preclassification_rows": preclass_loaded_rows,
        "silver_preclassification_input_rows": len(preclass),
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
    parser = argparse.ArgumentParser(description="Load Silver and Gold JSONL datasets into Postgres.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--silver-dir", default="data/silver")
    parser.add_argument("--gold-dir", default="data/gold")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--executed-by", default="etl-cli")
    args = parser.parse_args()

    stats = run_load_to_postgres(
        run_id=args.run_id,
        silver_dir=Path(args.silver_dir),
        gold_dir=Path(args.gold_dir),
        seed=args.seed,
        executed_by=args.executed_by,
    )
    print(json.dumps(stats, ensure_ascii=True))


if __name__ == "__main__":
    main()
