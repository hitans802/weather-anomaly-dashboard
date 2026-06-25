from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


@dataclass(frozen=True)
class LatestSummary:
    latest_date: date
    latest_status: str
    total_anomalous_days: int
    last_anomaly_date: str
    dataset_min_date: date
    dataset_max_date: date


class DashboardInsightService:
    @staticmethod
    def timing_offset(d: date) -> int:
        return (d - date.today()).days

    @classmethod
    def timing_label(cls, d: date) -> str:
        offset = cls.timing_offset(d)
        if offset == 0:
            return "Today"
        if offset > 0:
            return f"Forecast (+{offset} days)"
        return f"Historical ({abs(offset)} days ago)"

    @staticmethod
    def status_badge(is_anomaly: bool) -> str:
        return "ANOMALY" if is_anomaly else "NORMAL"

    @staticmethod
    def format_date(d) -> str:
        if d is None or d == "None" or pd.isna(d):
            return "None"
        return pd.to_datetime(d).strftime("%d/%m/%Y")
    @staticmethod
    def anomaly_reason(row: pd.Series) -> str:
        explanations = []

        if bool(row.get("temp_anomaly", False)):
            actual = row.get("temp_mean_c")
            baseline = row.get("temp_baseline_mean")
            z = row.get("temp_z")

            if pd.notna(actual) and pd.notna(baseline):
                diff = actual - baseline
                direction = "warmer" if diff > 0 else "colder"
                explanations.append(
                    f"Temperature averaged {actual:.1f}°C, which was "
                    f"{abs(diff):.1f}°C {direction} than the recent 14-day average "
                    f"of {baseline:.1f}°C (z={z:.2f})."
                )
            else:
                explanations.append("Temperature was unusually different from the recent baseline.")

        if bool(row.get("wind_anomaly", False)):
            actual = row.get("wind_mean_kmh")
            baseline = row.get("wind_baseline_mean")
            z = row.get("wind_z")

            if pd.notna(actual) and pd.notna(baseline):
                diff = actual - baseline
                direction = "stronger" if diff > 0 else "lower"
                explanations.append(
                    f"Wind speed averaged {actual:.1f} km/h, which was "
                    f"{abs(diff):.1f} km/h {direction} than the recent 14-day average "
                    f"of {baseline:.1f} km/h (z={z:.2f})."
                )
            else:
                explanations.append("Wind speed was unusually different from the recent baseline.")

        if bool(row.get("precip_anomaly", False)):
            actual = row.get("precip_total_mm")
            threshold = row.get("precip_p95")

            if pd.notna(actual) and pd.notna(threshold):
                diff = actual - threshold
                explanations.append(
                    f"Rainfall totalled {actual:.1f} mm, which was "
                    f"{diff:.1f} mm above the recent rainfall threshold "
                    f"of {threshold:.1f} mm."
                )
            else:
                explanations.append("Rainfall was unusually high compared with recent rainfall patterns.")

        return " ".join(explanations) if explanations else "No anomaly"

    @classmethod
    def build_latest_summary(cls, df: pd.DataFrame) -> LatestSummary:
        today = date.today()

        today_rows = df[df["date"] == today]

        if not today_rows.empty:
            latest = today_rows.iloc[-1]
        else:
            historical_rows = df[df["date"] <= today]
            latest = historical_rows.iloc[-1] if not historical_rows.empty else df.iloc[-1]

        last_anomaly = df.loc[df["any_anomaly"], "date"].max()

        return LatestSummary(
            latest_date=latest["date"],
            latest_status=cls.status_badge(bool(latest.get("any_anomaly", False))),
            total_anomalous_days=int(df["any_anomaly"].sum()),
            last_anomaly_date=cls.format_date(last_anomaly),
            dataset_min_date=df["date"].min(),
            dataset_max_date=df["date"].max(),
        )


class WeatherPlotRenderer:
    def render_metric_plot(
        self,
        df: pd.DataFrame,
        metric: str,
        ylabel: str,
        anomaly_flag: str,
        title: str,
        chart_type: str = "line",
    ) -> None:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])

        fig, ax = plt.subplots(figsize=(11, 4.2))
        fig.patch.set_facecolor("#07111f")
        ax.set_facecolor("#0b1728")

        if chart_type == "bar":
            ax.bar(df["date"], df[metric], label="Daily total", alpha=0.9, width=0.75)
        else:
            ax.plot(df["date"], df[metric], linewidth=2.4, label="Daily average")

        anomaly_df = df[df[anomaly_flag]]
        ax.scatter(
            anomaly_df["date"],
            anomaly_df[metric],
            s=80,
            label="Anomaly",
            zorder=5,
        )

        ax.set_title(title, color="white", fontsize=15, fontweight="bold", loc="left")
        ax.set_ylabel(ylabel, color="#dbeafe")
        ax.tick_params(colors="#cbd5e1", labelsize=10)
        ax.grid(alpha=0.22, color="#64748b")

        for spine in ax.spines.values():
            spine.set_color("#334155")

        # ✅ Fix graph dates here
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=8))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
        fig.autofmt_xdate(rotation=30, ha="right")

        ax.legend(facecolor="#0f172a", edgecolor="#334155", labelcolor="white")
        st.pyplot(fig, use_container_width=True)

    def render_trends_section(self, df: pd.DataFrame) -> None:
        st.markdown('<div class="section-title">Weather Trends</div>', unsafe_allow_html=True)

        self.render_metric_plot(
            df,
            "temp_mean_c",
            "Avg Temp (°C)",
            "temp_anomaly",
            "Average Daily Temperature",
            "line",
        )

        self.render_metric_plot(
            df,
            "precip_total_mm",
            "Rainfall (mm)",
            "precip_anomaly",
            "Total Daily Precipitation",
            "bar",
        )

        self.render_metric_plot(
            df,
            "wind_mean_kmh",
            "Avg Wind (km/h)",
            "wind_anomaly",
            "Average Daily Wind Speed",
            "line",
        )


class WeatherTableRenderer:
    def __init__(self, insight_service: DashboardInsightService) -> None:
        self.insight_service = insight_service

    def render_anomalies_table(self, df: pd.DataFrame) -> None:
        st.markdown('<div class="section-title">Detected Anomalies</div>', unsafe_allow_html=True)

        anomaly_df = df[df["any_anomaly"]].copy()
        if anomaly_df.empty:
            st.success("No anomalies in the selected view.")
            return

        anomaly_df["timing"] = anomaly_df["date"].apply(self.insight_service.timing_label)
        anomaly_df["reason"] = anomaly_df.apply(self.insight_service.anomaly_reason, axis=1)
        anomaly_df["date"] = pd.to_datetime(anomaly_df["date"]).dt.strftime("%d/%m/%Y")

        st.dataframe(
            anomaly_df[
                ["date", "timing", "reason", "temp_z", "wind_z", "precip_total_mm"]
            ],
            use_container_width=True,
            hide_index=True,
        )


class WeatherDashboardRenderer:
    def __init__(
        self,
        insight_service: DashboardInsightService,
        plot_renderer: WeatherPlotRenderer,
        table_renderer: WeatherTableRenderer,
    ) -> None:
        self.insight_service = insight_service
        self.plot_renderer = plot_renderer
        self.table_renderer = table_renderer

    def _css(self) -> None:
        st.markdown(
            """
            <style>
            .stApp {
                background: #06111f;
            }

            section[data-testid="stSidebar"] {
                background: linear-gradient(180deg, #07111f, #020617);
                border-right: 1px solid rgba(148,163,184,.2);
            }

            .hero {
                min-height: 230px;
                padding: 36px;
                border-radius: 28px;
                background:
                    linear-gradient(90deg, rgba(2,6,23,.82), rgba(15,23,42,.45)),
                    url("https://images.unsplash.com/photo-1545044846-351ba102b6d5?auto=format&fit=crop&w=1600&q=80");
                background-size: cover;
                background-position: center;
                border: 1px solid rgba(255,255,255,.16);
                box-shadow: 0 25px 70px rgba(0,0,0,.45);
                margin-bottom: 24px;
            }

            .hero h1 {
                font-size: 52px;
                font-weight: 900;
                color: white;
                margin-bottom: 8px;
            }

            .hero p {
                color: #dbeafe;
                font-size: 18px;
                max-width: 720px;
            }

            .hero-badge {
                display: inline-block;
                padding: 8px 14px;
                border-radius: 999px;
                background: rgba(59,130,246,.28);
                color: #bfdbfe;
                font-weight: 700;
                margin-bottom: 16px;
            }

            .kpi-card {
                padding: 22px;
                border-radius: 24px;
                background: linear-gradient(135deg, rgba(15,23,42,.90), rgba(30,58,138,.28));
                border: 1px solid rgba(147,197,253,.22);
                box-shadow: 0 18px 40px rgba(0,0,0,.28);
                min-height: 145px;
            }

            .kpi-icon {
                font-size: 18px;
                color: #93c5fd;
                margin-bottom: 8px;
                font-weight: 800;
            }

            .kpi-label {
                color: #94a3b8;
                font-size: 14px;
                font-weight: 700;
            }

            .kpi-value {
                color: white;
                font-size: 32px;
                font-weight: 900;
                margin-top: 8px;
            }

            .info-strip {
                padding: 18px 20px;
                border-radius: 20px;
                background: rgba(37,99,235,.14);
                border: 1px solid rgba(96,165,250,.35);
                color: #dbeafe;
                margin: 22px 0;
            }

            .section-title {
                font-size: 26px;
                font-weight: 900;
                color: white;
                margin: 24px 0 14px;
            }

            .insight-card {
                padding: 24px;
                border-radius: 24px;
                background: linear-gradient(135deg, rgba(15,23,42,.92), rgba(30,41,59,.72));
                border: 1px solid rgba(148,163,184,.22);
                box-shadow: 0 18px 40px rgba(0,0,0,.30);
            }

            .mini-card {
                padding: 20px;
                border-radius: 22px;
                background: rgba(15,23,42,.82);
                border: 1px solid rgba(148,163,184,.18);
                text-align: center;
            }

            .mini-card .big {
                font-size: 30px;
                font-weight: 900;
                color: white;
            }

            .mini-card .label {
                color: #94a3b8;
                font-size: 13px;
                font-weight: 700;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    def render_header(self) -> None:
        self._css()
        st.markdown(
            """
            <div class="hero">
                <div class="hero-badge">Melbourne Weather Intelligence</div>
                <h1>Weather Dashboard</h1>
                <p>
                    Daily weather monitoring for Melbourne with anomaly detection across
                    temperature, rainfall and wind patterns.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def render_sidebar(self) -> str:
        st.sidebar.markdown("## Weather Monitor")
        st.sidebar.caption("Melbourne, Australia")
        st.sidebar.image(
            "https://images.unsplash.com/photo-1545044846-351ba102b6d5?auto=format&fit=crop&w=600&q=80",
            use_container_width=True,
        )

        st.sidebar.markdown("### Data View")
        mode = st.sidebar.radio(
            "Choose view",
            ["All", "Historical only", "Forecast only"],
            index=0,
        )

        st.sidebar.markdown("---")
        st.sidebar.markdown(
            """
            **About**  
            This dashboard uses hourly weather data aggregated into daily metrics.

            **Temperature & wind:** daily average  
            **Precipitation:** daily total  
            **Anomalies:** unusual patterns vs historical baseline
            """
        )

        return mode

    def render_kpis(self, summary: LatestSummary, mode: str) -> None:
        cards = [
            ("Status", "Latest Status", summary.latest_status),
            ("Date", "Latest Day", self.insight_service.format_date(summary.latest_date)),
            ("Alerts", "Anomalous Days", str(summary.total_anomalous_days)),
            ("Event", "Last Anomaly", summary.last_anomaly_date),
        ]

        cols = st.columns(4)
        for col, (icon, label, value) in zip(cols, cards):
            with col:
                st.markdown(
                    f"""
                    <div class="kpi-card">
                        <div class="kpi-icon">{icon}</div>
                        <div class="kpi-label">{label}</div>
                        <div class="kpi-value">{value}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.caption(
            f"Date range: "
            f"{self.insight_service.format_date(summary.dataset_min_date)} → "
            f"{self.insight_service.format_date(summary.dataset_max_date)} "
            f"• Showing: {mode}"
        )

        st.markdown(
            """
            <div class="info-strip">
                <b>Data note:</b> Metrics are aggregated from hourly weather observations.
                Temperature and wind are daily averages; precipitation is total daily rainfall.
            </div>
            """,
            unsafe_allow_html=True,
        )

    def render_latest_day_insight(self, df: pd.DataFrame) -> None:
        today = date.today()

        today_rows = df[df["date"].apply(lambda d: d == today)].copy()
        historical_rows = df[df["date"].apply(lambda d: d <= today)].copy()

        if not today_rows.empty:
            latest = today_rows.iloc[-1]
        elif not historical_rows.empty:
            latest = historical_rows.iloc[-1]
        else:
            latest = df.iloc[-1]

        latest_date = latest["date"]
        latest_is_anomaly = bool(latest.get("any_anomaly", False))

        st.markdown('<div class="section-title">Latest Day Insight</div>', unsafe_allow_html=True)

        left, right = st.columns([1.25, 1])

        with left:
            st.markdown(
                f"""
                <div class="insight-card">
                    <h2>{self.insight_service.status_badge(latest_is_anomaly)}</h2>
                    <p><b>Date:</b> {self.insight_service.format_date(latest_date)}</p>
                    <p><b>Timing:</b> {self.insight_service.timing_label(latest_date)}</p>
                    <p><b>Reason:</b> {self.insight_service.anomaly_reason(latest)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with right:
            c1, c2, c3 = st.columns(3)

            with c1:
                st.markdown(
                    f"""
                    <div class="mini-card">
                        <div class="big">🌡️</div>
                        <div class="label">Avg Temp</div>
                        <div class="big">{latest.get('temp_mean_c'):.1f}°C</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with c2:
                st.markdown(
                    f"""
                    <div class="mini-card">
                        <div class="big">💨</div>
                        <div class="label">Avg Wind</div>
                        <div class="big">{latest.get('wind_mean_kmh'):.1f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with c3:
                st.markdown(
                    f"""
                    <div class="mini-card">
                        <div class="big">🌧️</div>
                        <div class="label">Rainfall</div>
                        <div class="big">{latest.get('precip_total_mm'):.1f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    def render_tabs(self, df: pd.DataFrame) -> None:
        today = date.today()

        historical_df = df[df["date"].apply(lambda d: d <= today)].copy()
        forecast_df = df[df["date"].apply(lambda d: d > today)].copy()

        tab1, tab2, tab3 = st.tabs(
            ["Trends", "Anomalies to Date", "Forecast Anomalies"]
        )

        with tab1:
            self.plot_renderer.render_trends_section(df)

        with tab2:
            self.table_renderer.render_anomalies_table(historical_df)

        with tab3:
            self.table_renderer.render_anomalies_table(forecast_df)