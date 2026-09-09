"""FastAPI interface for DriveSense trip analysis."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import shutil
import tempfile
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from analyzer import TelemetryAnalysisError, summarize_trip
from data_loader import TelemetryValidationError, load_telemetry
from metrics import MetricsCalculationError, calculate_driving_metrics


class TripSummaryReport(BaseModel):
    """Trip-level statistics returned by the analysis endpoint."""

    drive_time_s: float
    average_rpm: float
    minimum_rpm: float
    maximum_rpm: float
    average_speed_kph: float
    maximum_speed_kph: float
    average_throttle_position_pct: float
    average_coolant_temperature_c: float
    maximum_coolant_temperature_c: float
    average_intake_air_temperature_c: float


class DrivingBehaviorReport(BaseModel):
    """Detected driving events and classification for one trip."""

    idle_time_s: float
    aggressive_acceleration_events: int
    hard_braking_events: int
    high_coolant_temperature_events: int
    classification: str


class TripReport(BaseModel):
    """Structured report generated from an uploaded telemetry CSV."""

    source_filename: str
    trip_summary: TripSummaryReport
    driving_behavior: DrivingBehaviorReport


class AnalyzeTripResponse(BaseModel):
    """Response returned after a successful trip analysis."""

    driver_score: int
    report: TripReport


app = FastAPI(
    title="DriveSense API",
    description="Analyze automotive telemetry with DriveSense.",
)


def _analyze_csv(csv_path: Path, source_filename: str) -> AnalyzeTripResponse:
    """Run the existing DriveSense analysis pipeline for one CSV path."""
    telemetry = load_telemetry(csv_path)
    summary = summarize_trip(telemetry)
    metrics = calculate_driving_metrics(telemetry)

    behavior = asdict(metrics)
    driver_score = behavior.pop("driver_score")
    return AnalyzeTripResponse(
        driver_score=driver_score,
        report=TripReport(
            source_filename=source_filename,
            trip_summary=TripSummaryReport(**asdict(summary)),
            driving_behavior=DrivingBehaviorReport(**behavior),
        ),
    )


@app.post(
    "/analyze-trip",
    response_model=AnalyzeTripResponse,
    status_code=status.HTTP_200_OK,
)
def analyze_trip(
    telemetry_csv: Annotated[
        UploadFile,
        File(description="Automotive telemetry CSV to analyze."),
    ],
) -> AnalyzeTripResponse:
    """Analyze an uploaded CSV with DriveSense's existing scoring functions."""
    source_filename = Path(telemetry_csv.filename or "telemetry.csv").name

    try:
        with tempfile.TemporaryDirectory(prefix="drivesense-") as directory:
            csv_path = Path(directory) / "telemetry.csv"
            with csv_path.open("wb") as destination:
                shutil.copyfileobj(telemetry_csv.file, destination)
            return _analyze_csv(csv_path, source_filename)
    except (
        TelemetryValidationError,
        TelemetryAnalysisError,
        MetricsCalculationError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
