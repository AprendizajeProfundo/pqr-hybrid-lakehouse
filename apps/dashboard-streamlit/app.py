import os
from datetime import date, timedelta
from typing import Any

import pandas as pd
import pydeck as pdk
import streamlit as st

try:
    import psycopg2
except Exception as exc:  # pragma: no cover
    raise RuntimeError("psycopg2-binary no esta instalado en el entorno actual.") from exc


st.set_page_config(
    page_title="PQRS Analytics",
    page_icon="PQ",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
      .block-container {padding-top: 1rem; padding-bottom: 1.5rem;}
      .kpi-title {font-size: 0.86rem; color: #4a5568; margin-bottom: 0.15rem;}
      .kpi-value {font-size: 1.7rem; font-weight: 700; color: #102a43; margin-bottom: 0.2rem;}
      .kpi-sub {font-size: 0.82rem; color: #627d98;}
      .section-title {font-size: 1.05rem; font-weight: 700; color: #102a43; margin-top: 0.2rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def _db_config() -> dict[str, Any]:
    return {
        "host": os.getenv("PGHOST", "postgres"),
        "port": int(os.getenv("PGPORT", "5432")),
        "user": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", "localdev123"),
        "dbname": os.getenv("PGDATABASE", "pqr_lakehouse"),
    }


@st.cache_resource
def get_connection():
    return psycopg2.connect(**_db_config())


def run_query(sql: str, params: list[Any] | tuple[Any, ...] | None = None) -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql_query(sql, conn, params=params)


@st.cache_data(ttl=120)
def load_catalogs() -> dict[str, Any]:
    dates = run_query(
        "SELECT MIN(day) AS min_day, MAX(day) AS max_day FROM analytics.v_timeseries_national_daily"
    )
    types = run_query(
        "SELECT DISTINCT pqrs_type FROM analytics.v_timeseries_national_daily ORDER BY pqrs_type"
    )
    channels = run_query(
        "SELECT DISTINCT channel FROM analytics.v_timeseries_national_daily ORDER BY channel"
    )
    departments = run_query(
        "SELECT DISTINCT department_name FROM analytics.v_timeseries_department_daily ORDER BY department_name"
    )

    min_day = dates.iloc[0]["min_day"] if not dates.empty else None
    max_day = dates.iloc[0]["max_day"] if not dates.empty else None

    return {
        "min_day": min_day if pd.notna(min_day) else (date.today() - timedelta(days=180)),
        "max_day": max_day if pd.notna(max_day) else date.today(),
        "pqrs_types": types["pqrs_type"].dropna().astype(str).tolist(),
        "channels": channels["channel"].dropna().astype(str).tolist(),
        "departments": departments["department_name"].dropna().astype(str).tolist(),
    }


def build_where(
    date_from: date,
    date_to: date,
    pqrs_types: list[str],
    channels: list[str],
    departments: list[str] | None = None,
    prefix: str = "",
) -> tuple[str, list[Any]]:
    day_col = f"{prefix}day"
    type_col = f"{prefix}pqrs_type"
    channel_col = f"{prefix}channel"
    dept_col = f"{prefix}department_name"

    clauses = [f"{day_col} BETWEEN %s AND %s"]
    params: list[Any] = [date_from, date_to]

    if pqrs_types:
        clauses.append(f"{type_col} = ANY(%s)")
        params.append(pqrs_types)
    if channels:
        clauses.append(f"{channel_col} = ANY(%s)")
        params.append(channels)
    if departments:
        clauses.append(f"{dept_col} = ANY(%s)")
        params.append(departments)
    return " WHERE " + " AND ".join(clauses), params


def _fmt_int(v: Any) -> str:
    try:
        return f"{int(v):,}"
    except Exception:
        return "0"


def render_kpi_card(title: str, value: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="kpi-title">{title}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{subtitle}</div>
        """,
        unsafe_allow_html=True,
    )


def load_exec_kpis(
    date_from: date,
    date_to: date,
    pqrs_types: list[str],
    channels: list[str],
    departments: list[str],
) -> dict[str, Any]:
    where_n, params_n = build_where(date_from, date_to, pqrs_types, channels)
    where_d, params_d = build_where(date_from, date_to, pqrs_types, channels, departments=departments)

    total_n = run_query(
        f"SELECT COALESCE(SUM(tickets_count), 0) AS n FROM analytics.v_timeseries_national_daily {where_n}",
        params_n,
    ).iloc[0]["n"]
    total_d = run_query(
        f"SELECT COALESCE(SUM(tickets_count), 0) AS n FROM analytics.v_timeseries_department_daily {where_d}",
        params_d,
    ).iloc[0]["n"]
    avg_sla = run_query(
        f"SELECT COALESCE(ROUND(AVG(within_sla_pct)::numeric,2),0) AS n FROM analytics.v_geo_daily {where_d}",
        params_d,
    ).iloc[0]["n"]
    backlog = run_query(
        f"SELECT COALESCE(SUM(backlog_count), 0) AS n FROM analytics.v_geo_daily {where_d}",
        params_d,
    ).iloc[0]["n"]

    latest_var = run_query(
        f"""
        SELECT day, COALESCE(SUM(pct_vs_prev_day), 0) AS n
        FROM analytics.v_timeseries_national_daily
        {where_n}
        GROUP BY day
        ORDER BY day DESC
        LIMIT 1
        """,
        params_n,
    )
    pct_prev_day = float(latest_var.iloc[0]["n"]) if not latest_var.empty else 0.0

    return {
        "total_n": total_n,
        "total_d": total_d,
        "avg_sla": float(avg_sla or 0),
        "backlog": backlog,
        "pct_prev_day": pct_prev_day,
    }


def load_series_national(date_from: date, date_to: date, pqrs_types: list[str], channels: list[str]) -> pd.DataFrame:
    where, params = build_where(date_from, date_to, pqrs_types, channels)
    return run_query(
        f"""
        SELECT day, pqrs_type, SUM(tickets_count) AS tickets_count
        FROM analytics.v_timeseries_national_daily
        {where}
        GROUP BY day, pqrs_type
        ORDER BY day ASC, pqrs_type ASC
        """,
        params,
    )


def load_series_dept(
    date_from: date,
    date_to: date,
    pqrs_types: list[str],
    channels: list[str],
    departments: list[str],
) -> pd.DataFrame:
    where, params = build_where(date_from, date_to, pqrs_types, channels, departments=departments)
    return run_query(
        f"""
        SELECT day, department_name, SUM(tickets_count) AS tickets_count
        FROM analytics.v_timeseries_department_daily
        {where}
        GROUP BY day, department_name
        ORDER BY day ASC, department_name ASC
        """,
        params,
    )


def load_geo_metrics(
    date_from: date,
    date_to: date,
    pqrs_types: list[str],
    channels: list[str],
    departments: list[str],
) -> pd.DataFrame:
    where, params = build_where(
        date_from=date_from,
        date_to=date_to,
        pqrs_types=pqrs_types,
        channels=channels,
        departments=departments if departments else None,
        prefix="v.",
    )
    return run_query(
        f"""
        WITH agg AS (
          SELECT
            v.department_name,
            SUM(v.tickets_count) AS tickets_count,
            SUM(COALESCE(v.backlog_count, 0)) AS backlog_count,
            ROUND(AVG(COALESCE(v.within_sla_pct, 0))::numeric, 2) AS within_sla_pct,
            SUM(COALESCE(v.overdue_count, 0)) AS overdue_count,
            AVG(g.latitude)::float AS lat,
            AVG(g.longitude)::float AS lon
          FROM analytics.v_geo_daily v
          LEFT JOIN silver.dim_geo g
            ON g.dane_city_code = v.dane_city_code
          {where}
          GROUP BY v.department_name
        )
        SELECT
          department_name,
          lat,
          lon,
          tickets_count,
          backlog_count,
          within_sla_pct,
          overdue_count
        FROM agg
        ORDER BY tickets_count DESC
        """,
        params,
    )


def build_map_dataframe(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    use = df.copy()
    use = use.dropna(subset=["lat", "lon"])
    if use.empty:
        return use

    vals = use[metric].astype(float)
    vmin, vmax = float(vals.min()), float(vals.max())
    span = (vmax - vmin) if (vmax - vmin) > 0 else 1.0

    use["radius"] = 20000 + ((vals - vmin) / span) * 70000
    use["intensity"] = ((vals - vmin) / span).clip(0, 1)
    # Gradiente de alto contraste (naranja -> rojo oscuro)
    use["r"] = (250 - use["intensity"] * 20).astype(int)
    use["g"] = (180 - use["intensity"] * 150).astype(int)
    use["b"] = (60 - use["intensity"] * 40).clip(lower=15).astype(int)
    use["a"] = 180
    use["color"] = use[["r", "g", "b", "a"]].values.tolist()
    return use


def render_geo_map(df: pd.DataFrame, metric: str) -> None:
    total_departments = len(df)
    map_df = build_map_dataframe(df, metric)
    mapped_departments = len(map_df)
    if mapped_departments < total_departments:
        missing = df[df["lat"].isna() | df["lon"].isna()]["department_name"].dropna().astype(str).tolist()
        if missing:
            st.warning(
                "Departamentos sin coordenadas para mapa: "
                + ", ".join(missing[:12])
                + ("..." if len(missing) > 12 else "")
            )
    if map_df.empty:
        st.warning("No hay coordenadas disponibles para mapear esta selección.")
        return

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position="[lon, lat]",
        get_fill_color="color",
        get_radius="radius",
        pickable=True,
        stroked=True,
        get_line_color=[20, 20, 20],
        line_width_min_pixels=1,
        opacity=0.7,
    )
    view_state = pdk.ViewState(latitude=4.5, longitude=-74.2, zoom=4.2, pitch=0)

    tooltip = {
        "html": (
            "<b>{department_name}</b><br/>"
            "Tickets: {tickets_count}<br/>"
            "Backlog: {backlog_count}<br/>"
            "SLA %: {within_sla_pct}<br/>"
            "Overdue: {overdue_count}"
        ),
        "style": {"backgroundColor": "#102a43", "color": "white"},
    }
    st.caption(f"Departamentos visibles en mapa: {mapped_departments} de {total_departments}.")
    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip=tooltip,
            map_style="mapbox://styles/mapbox/light-v10",
        ),
        use_container_width=True,
    )


def main() -> None:
    st.title("PQRS Analytics Dashboard")
    st.caption("Vista ejecutiva-operativa conectada a Postgres (`analytics.*`).")

    try:
        catalogs = load_catalogs()
    except Exception as exc:
        st.error(f"No fue posible conectar con Postgres o cargar catálogos: {exc}")
        st.stop()

    with st.sidebar:
        st.markdown("### Filtros")
        min_day, max_day = catalogs["min_day"], catalogs["max_day"]
        date_range = st.date_input("Rango de fechas", value=(min_day, max_day), min_value=min_day, max_value=max_day)
        if not isinstance(date_range, tuple) or len(date_range) != 2:
            st.warning("Selecciona fecha inicio y fecha fin.")
            st.stop()
        date_from, date_to = date_range

        pqrs_types = st.multiselect("Tipo PQRS", catalogs["pqrs_types"], default=catalogs["pqrs_types"])
        channels = st.multiselect("Canales", catalogs["channels"], default=catalogs["channels"])
        departments = st.multiselect("Departamentos", catalogs["departments"], default=catalogs["departments"][:6])
        map_metric = st.selectbox(
            "Métrica del mapa",
            ["tickets_count", "backlog_count", "within_sla_pct", "overdue_count"],
            index=0,
        )

    kpis = load_exec_kpis(date_from, date_to, pqrs_types, channels, departments)
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        render_kpi_card("Volumen Nacional", _fmt_int(kpis["total_n"]), "Total tickets en rango")
    with k2:
        render_kpi_card("Volumen Departamental", _fmt_int(kpis["total_d"]), "Departamentos seleccionados")
    with k3:
        render_kpi_card("Backlog", _fmt_int(kpis["backlog"]), "Acumulado en rango")
    with k4:
        render_kpi_card("SLA Promedio", f'{kpis["avg_sla"]:.2f}%', "Cumplimiento promedio")
    with k5:
        render_kpi_card("Var. vs dia anterior", f'{kpis["pct_prev_day"]:.2f}%', "Ultimo dia disponible")

    tabs = st.tabs(["Series Nacionales", "Comparativo Departamental", "Mapa y Ranking"])

    with tabs[0]:
        st.markdown('<div class="section-title">Evolución diaria nacional por tipo PQRS</div>', unsafe_allow_html=True)
        ndf = load_series_national(date_from, date_to, pqrs_types, channels)
        if ndf.empty:
            st.info("No hay datos para la selección.")
        else:
            pivot = ndf.pivot(index="day", columns="pqrs_type", values="tickets_count").fillna(0)
            st.line_chart(pivot, use_container_width=True)
            st.dataframe(ndf, use_container_width=True, hide_index=True)

    with tabs[1]:
        st.markdown('<div class="section-title">Comparativo diario por departamento</div>', unsafe_allow_html=True)
        ddf = load_series_dept(date_from, date_to, pqrs_types, channels, departments)
        if ddf.empty:
            st.info("No hay datos para departamentos seleccionados.")
        else:
            pivot = ddf.pivot(index="day", columns="department_name", values="tickets_count").fillna(0)
            st.line_chart(pivot, use_container_width=True)
            ranking = (
                ddf.groupby("department_name", as_index=False)["tickets_count"]
                .sum()
                .sort_values("tickets_count", ascending=False)
            )
            c1, c2 = st.columns([2, 1])
            with c1:
                st.dataframe(ddf, use_container_width=True, hide_index=True)
            with c2:
                st.markdown("**Ranking departamental (volumen)**")
                st.dataframe(ranking, use_container_width=True, hide_index=True)

    with tabs[2]:
        st.markdown('<div class="section-title">Mapa analítico departamental</div>', unsafe_allow_html=True)
        gdf = load_geo_metrics(date_from, date_to, pqrs_types, channels, departments)
        if gdf.empty:
            st.info("No hay datos geográficos para esta selección.")
        else:
            render_geo_map(gdf, map_metric)
            st.markdown(f"**Métrica visualizada:** `{map_metric}`")
            st.dataframe(gdf, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
