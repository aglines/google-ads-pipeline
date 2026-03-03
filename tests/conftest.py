"""Shared fixtures for phase verification tests."""

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def gcp_project_id() -> str:
    """Return the GCP project ID from environment."""
    project_id = os.getenv("GCP_PROJECT_ID")
    if not project_id:
        pytest.skip("GCP_PROJECT_ID not set in .env")
    return project_id


@pytest.fixture(scope="session")
def gcp_region() -> str:
    """Return the GCP region from environment."""
    return os.getenv("GCP_REGION", "us-central1")


@pytest.fixture(scope="session")
def bigquery_datasets() -> list[str]:
    """Return list of expected BigQuery dataset IDs."""
    return [
        os.getenv("BQ_DATASET_RAW", "raw_google_ads"),
        os.getenv("BQ_DATASET_STAGING", "staging_google_ads"),
        os.getenv("BQ_DATASET_STAGING_TRENDS", "staging_trends"),
        os.getenv("BQ_DATASET_INTERMEDIATE", "intermediate"),
        os.getenv("BQ_DATASET_MARTS_MARKETING", "marts_marketing"),
        os.getenv("BQ_DATASET_MARTS_ANALYTICS", "marts_analytics"),
    ]


@pytest.fixture(scope="session")
def gcs_buckets() -> list[str]:
    """Return list of expected GCS bucket names."""
    return [
        os.getenv("GCS_BUCKET_RAW_DATA", ""),
        os.getenv("GCS_BUCKET_PROCESSED", ""),
    ]
