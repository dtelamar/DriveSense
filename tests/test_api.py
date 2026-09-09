"""Tests for the DriveSense FastAPI interface."""

from __future__ import annotations

from pathlib import Path
import unittest

import httpx

from api import app


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = REPOSITORY_ROOT / "sample_data" / "drive_log.csv"


class TripAnalysisApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_analyzes_uploaded_sample_with_existing_pipeline(self) -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/analyze-trip",
                files={
                    "telemetry_csv": (
                        "drive_log.csv",
                        SAMPLE_PATH.read_bytes(),
                        "text/csv",
                    )
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["driver_score"], 67)
        self.assertEqual(payload["report"]["source_filename"], "drive_log.csv")
        self.assertEqual(payload["report"]["trip_summary"]["drive_time_s"], 600.0)
        self.assertEqual(
            payload["report"]["driving_behavior"],
            {
                "idle_time_s": 85.0,
                "aggressive_acceleration_events": 1,
                "hard_braking_events": 2,
                "high_coolant_temperature_events": 1,
                "classification": "Aggressive Driver",
            },
        )

    async def test_rejects_invalid_telemetry_with_validation_message(self) -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/analyze-trip",
                files={
                    "telemetry_csv": (
                        "invalid.csv",
                        b"timestamp_s,engine_rpm\n0,800\n",
                        "text/csv",
                    )
                },
            )

        self.assertEqual(response.status_code, 422)
        self.assertIn("Missing required columns", response.json()["detail"])

    async def test_requires_a_csv_upload(self) -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post("/analyze-trip")

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
