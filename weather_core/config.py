from __future__ import annotations

from pathlib import Path


class AppConfig:
    API_URL = "https://api.open-meteo.com/v1/forecast"
    LATITUDE = -37.8136
    LONGITUDE = 144.9631
    HOURLY_VARS = ["temperature_2m", "precipitation", "wind_speed_10m"]
    PAST_DAYS = 60
    FORECAST_DAYS = 5
    KEEP_LAST_N_FILES = 5
    TIMEZONE = "auto"
    

    TEMP_MIN_C = -20.0
    TEMP_MAX_C = 50.0
    PRECIP_MIN_MM = 0.0
    WIND_MIN = 0.0

    OK_MAX_MISSING = 2
    WARN_MAX_MISSING = 6

    BASELINE_DAYS = 14
    PRECIP_LOOKBACK_DAYS = 60
    Z_THRESHOLD = 3.0
    EPS_STD = 1e-6

    


class AppPaths:
    ROOT = Path(__file__).resolve().parent.parent
    DATA_DIR = ROOT / "data"
    RAW_DIR = DATA_DIR / "raw"
    PROCESSED_DIR = DATA_DIR / "processed"
    REPORTS_DIR = ROOT / "reports"
    