from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from weather_core.pipeline import WeatherPipelineRunner
from weather_core.repository import WeatherFileRepository
from dashboard.ui_renderers import (
    DashboardInsightService,
    WeatherPlotRenderer,
    WeatherTableRenderer,
    WeatherDashboardRenderer,
)


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    for col in ["temp_anomaly", "wind_anomaly", "precip_anomaly", "any_anomaly"]:
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].astype(str).str.lower().isin(["true", "1", "yes"])

    return df


def filter_by_mode(
    df: pd.DataFrame,
    mode: str,
    insight_service: DashboardInsightService,
) -> pd.DataFrame:
    if mode == "Historical only":
        return df[df["date"].apply(lambda d: insight_service.timing_offset(d) <= 0)].copy()

    if mode == "Forecast only":
        return df[df["date"].apply(lambda d: insight_service.timing_offset(d) > 0)].copy()

    return df.copy()


@st.cache_data(ttl=1800)
def refresh_pipeline_and_load_data() -> pd.DataFrame:
    """
    Refresh data when the dashboard opens.
    Cached for 30 minutes so Streamlit reruns don't spam the API.
    """
    runner = WeatherPipelineRunner()
    runner.run_all()

    repo = WeatherFileRepository()
    df, _ = repo.load_latest_anomaly_dataframe()
    return df


def main() -> None:
    st.set_page_config(page_title="Weather Dashboard", layout="wide")

    insight_service = DashboardInsightService()
    plot_renderer = WeatherPlotRenderer()
    table_renderer = WeatherTableRenderer(insight_service)
    dashboard_renderer = WeatherDashboardRenderer(
        insight_service=insight_service,
        plot_renderer=plot_renderer,
        table_renderer=table_renderer,
    )

    try:
        with st.spinner("Updating latest weather data..."):
            df_all = refresh_pipeline_and_load_data()
            df_all = normalize_dataframe(df_all)
    except Exception as exc:
        st.error(f"Dashboard couldn't load data: {exc}")
        st.stop()

    dashboard_renderer.render_header()

    mode = dashboard_renderer.render_sidebar()
    df_view = filter_by_mode(df_all, mode, insight_service)

    if df_view.empty:
        st.warning("No data available for this filter.")
        st.stop()

    summary = insight_service.build_latest_summary(df_all)

    dashboard_renderer.render_kpis(summary=summary, mode=mode)
    dashboard_renderer.render_latest_day_insight(df_all)
    dashboard_renderer.render_tabs(df_view)


if __name__ == "__main__":
    main()