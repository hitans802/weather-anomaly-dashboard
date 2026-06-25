from __future__ import annotations

from src.models import RawFileInfo, ProcessedFileInfo, AnomalyFileInfo, ReportFileInfo
from src.repository import WeatherAPIClient, WeatherFileRepository
from src.services import (
    WeatherIngestionService,
    WeatherCleaningService,
    WeatherAnomalyService,
    WeatherReportService,
)


class WeatherPipelineRunner:
    def __init__(self) -> None:
        self.api_client = WeatherAPIClient()
        self.file_repository = WeatherFileRepository()
        self.ingestion_service = WeatherIngestionService()
        self.cleaning_service = WeatherCleaningService()
        self.anomaly_service = WeatherAnomalyService()
        self.report_service = WeatherReportService()

    def run_ingestion(self) -> RawFileInfo:
        payload = self.api_client.fetch_hourly_payload()
        raw_df = self.ingestion_service.payload_to_dataframe(payload)
        path = self.file_repository.save_raw_dataframe(raw_df)
        return RawFileInfo(path=path, row_count=len(raw_df))

    def run_cleaning(self) -> ProcessedFileInfo:
        raw_df, _ = self.file_repository.load_latest_raw_dataframe()
        processed_df = self.cleaning_service.clean_and_aggregate(raw_df)
        path = self.file_repository.save_processed_dataframe(processed_df)

        counts = processed_df["quality_flag"].value_counts().to_dict()
        return ProcessedFileInfo(
            path=path,
            day_count=len(processed_df),
            ok_count=counts.get("OK", 0),
            warn_count=counts.get("WARN", 0),
            bad_count=counts.get("BAD", 0),
        )

    def run_anomaly_detection(self) -> AnomalyFileInfo:
        processed_df, _ = self.file_repository.load_latest_processed_dataframe()
        anomaly_df = self.anomaly_service.detect(processed_df)
        path = self.file_repository.save_anomaly_dataframe(anomaly_df)

        return AnomalyFileInfo(
            path=path,
            anomaly_count=int(anomaly_df["any_anomaly"].sum()),
            total_days=len(anomaly_df),
        )

    def run_reporting(self) -> ReportFileInfo:
        anomaly_df, _ = self.file_repository.load_latest_anomaly_dataframe()
        report_content = self.report_service.generate_report(anomaly_df)
        path = self.file_repository.save_report(report_content)

        latest_status = (
            "ANOMALY" if bool(anomaly_df.iloc[-1]["any_anomaly"]) else "NORMAL"
        )
        return ReportFileInfo(path=path, latest_status=latest_status)

    def run_all(self) -> None:
        raw_info = self.run_ingestion()
        print(f"SUCCESS: raw saved -> {raw_info.path} (rows={raw_info.row_count})")

        processed_info = self.run_cleaning()
        print(
            f"SUCCESS: processed saved -> {processed_info.path} "
            f"(days={processed_info.day_count}, OK={processed_info.ok_count}, "
            f"WARN={processed_info.warn_count}, BAD={processed_info.bad_count})"
        )

        anomaly_info = self.run_anomaly_detection()
        print(
            f"SUCCESS: anomalies saved -> {anomaly_info.path} "
            f"(anomalies={anomaly_info.anomaly_count}/{anomaly_info.total_days})"
        )

        report_info = self.run_reporting()
        print(f"SUCCESS: report saved -> {report_info.path} ({report_info.latest_status})")