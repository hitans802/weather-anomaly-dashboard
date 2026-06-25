from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os

import pandas as pd
import requests

from src.config import AppConfig, AppPaths


class WeatherAPIClient:
    def fetch_hourly_payload(self) -> dict:
        params = {
            "latitude": AppConfig.LATITUDE,
            "longitude": AppConfig.LONGITUDE,
            "hourly": ",".join(AppConfig.HOURLY_VARS),
            "past_days": AppConfig.PAST_DAYS,
            "forecast_days": AppConfig.FORECAST_DAYS,
            "timezone": AppConfig.TIMEZONE,
        }

        response = requests.get(AppConfig.API_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()


class WeatherFileRepository:
    def __init__(self) -> None:
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        directories = [
            AppPaths.RAW_DIR,
            AppPaths.PROCESSED_DIR,
            AppPaths.REPORTS_DIR,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        

    def save_raw_dataframe(self, df: pd.DataFrame) -> Path:
        filename = f"weather_raw_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        path = AppPaths.RAW_DIR / filename
        df.to_csv(path, index=False)
        return path

    def load_latest_raw_dataframe(self) -> tuple[pd.DataFrame, Path]:
        files = sorted(AppPaths.RAW_DIR.glob("*.csv"), reverse=True)
        if not files:
            raise FileNotFoundError("No raw CSV files found in data/raw/")
        path = files[0]
        return pd.read_csv(path), path

    def save_processed_dataframe(self, df: pd.DataFrame) -> Path:
        filename = f"daily_weather_{datetime.now().strftime('%Y%m%d')}.csv"
        path = AppPaths.PROCESSED_DIR / filename
        df.to_csv(path, index=False)
        return path

    def load_latest_processed_dataframe(self) -> tuple[pd.DataFrame, Path]:
        files = sorted(
            AppPaths.PROCESSED_DIR.glob("daily_weather_*.csv"),
            reverse=True,
        )
        files = [f for f in files if "with_anomalies" not in f.name]
        if not files:
            raise FileNotFoundError("No processed daily_weather CSV found.")
        path = files[0]
        return pd.read_csv(path), path

    def save_anomaly_dataframe(self, df: pd.DataFrame) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")

        snapshot_path = AppPaths.PROCESSED_DIR / f"daily_weather_with_anomalies_{timestamp}.csv"
        latest_path = AppPaths.PROCESSED_DIR / "latest_weather_with_anomalies.csv"

        df.to_csv(snapshot_path, index=False)
        df.to_csv(latest_path, index=False)

        self.cleanup_old_processed_files()

        return latest_path

    def load_latest_anomaly_dataframe(self) -> tuple[pd.DataFrame, Path]:
        path = AppPaths.PROCESSED_DIR / "latest_weather_with_anomalies.csv"

        if not path.exists():
            raise FileNotFoundError(
                "No latest anomaly file found. Run the pipeline first."
            )

        return pd.read_csv(path), path

    def save_report(self, content: str) -> Path:
        filename = f"report_{datetime.now().strftime('%Y%m%d')}.md"
        path = AppPaths.REPORTS_DIR / filename
        path.write_text(content, encoding="utf-8")
        return path
    
    def cleanup_old_processed_files(self, keep_last: int = AppConfig.KEEP_LAST_N_FILES) -> None:
        patterns = [
            "daily_weather_*.csv",
            "daily_weather_with_anomalies_*.csv",
        ]

        for pattern in patterns:
            files = sorted(
                AppPaths.PROCESSED_DIR.glob(pattern),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            for old_file in files[keep_last:]:
                old_file.unlink()