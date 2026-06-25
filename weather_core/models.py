from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pandas as pd


@dataclass(frozen=True)
class RawFileInfo:
    path: Path
    row_count: int


@dataclass(frozen=True)
class ProcessedFileInfo:
    path: Path
    day_count: int
    ok_count: int
    warn_count: int
    bad_count: int


@dataclass(frozen=True)
class AnomalyFileInfo:
    path: Path
    anomaly_count: int
    total_days: int


@dataclass(frozen=True)
class ReportFileInfo:
    path: Path
    latest_status: str