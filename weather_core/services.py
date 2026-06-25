from __future__ import annotations

from datetime import datetime
import pandas as pd

from weather_core.config import AppConfig


class WeatherIngestionService:
    @staticmethod
    def payload_to_dataframe(payload: dict) -> pd.DataFrame:
        if "hourly" not in payload:
            raise ValueError("Missing 'hourly' in API payload.")

        hourly = payload["hourly"]
        required = ["time"] + AppConfig.HOURLY_VARS
        missing = [col for col in required if col not in hourly]
        if missing:
            raise ValueError(f"Missing hourly fields: {missing}")

        n = len(hourly["time"])
        for col in AppConfig.HOURLY_VARS:
            if len(hourly[col]) != n:
                raise ValueError(f"Length mismatch for {col}")

        df = pd.DataFrame(
            {
                "time": hourly["time"],
                "temperature_2m": hourly["temperature_2m"],
                "precipitation": hourly["precipitation"],
                "wind_speed_10m": hourly["wind_speed_10m"],
            }
        )
        df["fetched_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        return df


class WeatherCleaningService:
    @staticmethod
    def clean_and_aggregate(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()

        out["time"] = pd.to_datetime(out["time"], errors="coerce")
        out = out.dropna(subset=["time"]).sort_values("time")
        out = out.drop_duplicates(subset=["time"], keep="last")

        for col in ["temperature_2m", "precipitation", "wind_speed_10m"]:
            out[col] = pd.to_numeric(out[col], errors="coerce")

        out.loc[
            (out["temperature_2m"] < AppConfig.TEMP_MIN_C)
            | (out["temperature_2m"] > AppConfig.TEMP_MAX_C),
            "temperature_2m",
        ] = pd.NA

        out.loc[out["precipitation"] < AppConfig.PRECIP_MIN_MM, "precipitation"] = pd.NA
        out.loc[out["wind_speed_10m"] < AppConfig.WIND_MIN, "wind_speed_10m"] = pd.NA

        out["date"] = out["time"].dt.date

        out = out.groupby("date", group_keys=False).apply(
            WeatherCleaningService._fill_short_gaps
        )

        return WeatherCleaningService._daily_aggregate(out)

    @staticmethod
    def _fill_short_gaps(group: pd.DataFrame) -> pd.DataFrame:
        group = group.sort_values("time").copy()
        group["temperature_2m"] = group["temperature_2m"].ffill(limit=2)
        group["wind_speed_10m"] = group["wind_speed_10m"].ffill(limit=2)
        return group

    @staticmethod
    def _daily_aggregate(df: pd.DataFrame) -> pd.DataFrame:
        hours_present = df.groupby("date")["time"].count().rename("n_hours_present")

        daily_metrics = df.groupby("date").agg(
            temp_mean_c=("temperature_2m", "mean"),
            wind_mean_kmh=("wind_speed_10m", "mean"),
            precip_total_mm=("precipitation", "sum"),
        )

        daily = pd.concat([daily_metrics, hours_present], axis=1).reset_index()
        daily["n_hours_expected"] = 24
        daily["missing_hours"] = daily["n_hours_expected"] - daily["n_hours_present"]
        daily["quality_flag"] = daily["missing_hours"].apply(
            WeatherCleaningService._quality_flag
        )
        return daily

    @staticmethod
    def _quality_flag(missing_hours: int) -> str:
        if missing_hours <= AppConfig.OK_MAX_MISSING:
            return "OK"
        if missing_hours <= AppConfig.WARN_MAX_MISSING:
            return "WARN"
        return "BAD"


class WeatherAnomalyService:
    @staticmethod
    def detect(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        out = out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

        valid_mask = out["quality_flag"].isin(["OK", "WARN"])

        temp = out["temp_mean_c"].where(valid_mask)
        out["temp_baseline_mean"] = (
            temp.rolling(AppConfig.BASELINE_DAYS, min_periods=AppConfig.BASELINE_DAYS)
            .mean()
            .shift(1)
        )
        out["temp_baseline_std"] = (
            temp.rolling(AppConfig.BASELINE_DAYS, min_periods=AppConfig.BASELINE_DAYS)
            .std(ddof=0)
            .shift(1)
            .fillna(0)
            .clip(lower=AppConfig.EPS_STD)
        )
        out["temp_z"] = (
            out["temp_mean_c"] - out["temp_baseline_mean"]
        ) / out["temp_baseline_std"]
        out["temp_anomaly"] = out["temp_z"].abs() >= AppConfig.Z_THRESHOLD

        wind = out["wind_mean_kmh"].where(valid_mask)
        out["wind_baseline_mean"] = (
            wind.rolling(AppConfig.BASELINE_DAYS, min_periods=AppConfig.BASELINE_DAYS)
            .mean()
            .shift(1)
        )
        out["wind_baseline_std"] = (
            wind.rolling(AppConfig.BASELINE_DAYS, min_periods=AppConfig.BASELINE_DAYS)
            .std(ddof=0)
            .shift(1)
            .fillna(0)
            .clip(lower=AppConfig.EPS_STD)
        )
        out["wind_z"] = (
            out["wind_mean_kmh"] - out["wind_baseline_mean"]
        ) / out["wind_baseline_std"]
        out["wind_anomaly"] = out["wind_z"].abs() >= AppConfig.Z_THRESHOLD

        precip = out["precip_total_mm"].where(valid_mask)
        out["precip_p95"] = (
            precip.rolling(
                AppConfig.PRECIP_LOOKBACK_DAYS,
                min_periods=AppConfig.BASELINE_DAYS,
            )
            .quantile(0.95)
            .shift(1)
        )
        out["precip_anomaly"] = out["precip_total_mm"] > out["precip_p95"]

        out["any_anomaly"] = out[
            ["temp_anomaly", "wind_anomaly", "precip_anomaly"]
        ].any(axis=1)

        return out


class WeatherReportService:
    @staticmethod
    def generate_report(df: pd.DataFrame) -> str:
        out = df.copy()
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        out = out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

        latest = out.iloc[-1]
        latest_date = latest["date"].date()
        total_days = len(out)
        total_anomalies = int(out["any_anomaly"].sum())
        latest_status = "ANOMALY" if bool(latest["any_anomaly"]) else "NORMAL"
        latest_reason = WeatherReportService._reason(latest)

        lines: list[str] = []
        lines.append(f"# Daily Weather Monitoring Report — {latest_date}")
        lines.append("")
        lines.append("## Summary")
        lines.append(f"- Days in dataset: **{total_days}**")
        lines.append(f"- Anomalous days flagged: **{total_anomalies}**")
        lines.append("")
        lines.append("## Latest Day Status")
        lines.append(f"- Date: **{latest_date}**")
        lines.append(f"- Status: **{latest_status}**")
        lines.append(f"- Reason: {latest_reason}")
        lines.append("")
        lines.append("## Recent Anomalies (last 10)")

        recent = out[out["any_anomaly"]].tail(10)
        if recent.empty:
            lines.append("- None")
        else:
            for _, row in recent.iterrows():
                lines.append(
                    f"- **{row['date'].date()}** — {WeatherReportService._reason(row)}"
                )

        return "\n".join(lines)

    @staticmethod
    def _reason(row: pd.Series) -> str:
        reasons = []

        if bool(row.get("temp_anomaly", False)):
            z = row.get("temp_z")
            reasons.append(f"Temperature anomaly (z={z:.2f})")

        if bool(row.get("wind_anomaly", False)):
            z = row.get("wind_z")
            reasons.append(f"Wind anomaly (z={z:.2f})")

        if bool(row.get("precip_anomaly", False)):
            p = row.get("precip_total_mm")
            reasons.append(f"High precipitation (total={p:.1f}mm)")

        return "; ".join(reasons) if reasons else "No anomaly"