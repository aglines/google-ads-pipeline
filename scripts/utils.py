"""Shared utilities for extraction scripts.

This module provides common functions for GCS upload, logging,
data validation, and other shared operations across all extractors.

Usage:
    from utils import setup_logging, upload_to_gcs, validate_dataframe
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv()


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """Set up logging for a script.

    Args:
        name: Logger name (typically __name__).
        level: Logging level.

    Returns:
        Configured logger instance.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger(name)


def get_gcp_config() -> dict[str, str]:
    """Get GCP configuration from environment.

    Returns:
        Dictionary with project_id, bucket_raw, region.
    """
    return {
        "project_id": os.getenv("GCP_PROJECT_ID", ""),
        "bucket_raw": os.getenv("GCS_BUCKET_RAW_DATA", ""),
        "region": os.getenv("GCP_REGION", "us-central1"),
    }


def upload_to_gcs(
    local_path: Path,
    gcs_prefix: str,
    bucket_name: str | None = None,
    project_id: str | None = None,
    max_retries: int = 3,
    logger: logging.Logger | None = None,
) -> str:
    """Upload a file to Google Cloud Storage with retry logic.

    Args:
        local_path: Path to local file.
        gcs_prefix: Prefix for GCS object name (e.g., "raw/trends").
        bucket_name: GCS bucket name. If None, uses GCS_BUCKET_RAW_DATA env var.
        project_id: GCP project ID. If None, uses GCP_PROJECT_ID env var.
        max_retries: Maximum retry attempts.
        logger: Logger instance for output.

    Returns:
        GCS URI of uploaded file, or empty string if upload skipped/failed.

    Raises:
        Exception: If all retry attempts fail.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    bucket_name = bucket_name or os.getenv("GCS_BUCKET_RAW_DATA", "")
    project_id = project_id or os.getenv("GCP_PROJECT_ID", "")

    if not bucket_name:
        logger.warning("GCS_BUCKET_RAW_DATA not set, skipping upload")
        return ""

    blob_name = f"{gcs_prefix}/{local_path.name}"

    for attempt in range(max_retries):
        try:
            client = storage.Client(project=project_id)
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            blob.upload_from_filename(str(local_path))

            gcs_uri = f"gs://{bucket_name}/{blob_name}"
            logger.info(f"Uploaded to {gcs_uri}")
            return gcs_uri

        except Exception as e:
            logger.warning(f"Upload attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                sleep_time = 2**attempt  # Exponential backoff
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                raise

    return ""


def save_to_json(
    df: pd.DataFrame,
    output_path: Path,
    append: bool = False,
    logger: logging.Logger | None = None,
) -> Path:
    """Save DataFrame to JSON file.

    Args:
        df: Data to save.
        output_path: Full path to output file.
        append: If True, append to existing file.
        logger: Logger instance.

    Returns:
        Path to saved file.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if append and output_path.exists():
        with open(output_path) as f:
            existing = json.load(f)
        new_records = df.to_dict(orient="records")
        existing.extend(new_records)
        data = existing
    else:
        data = df.to_dict(orient="records")

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    logger.info(f"Saved {len(data)} records to {output_path}")
    return output_path


def validate_dataframe(
    df: pd.DataFrame,
    required_columns: list[str],
    min_rows: int = 1,
    logger: logging.Logger | None = None,
) -> tuple[bool, list[str]]:
    """Validate a DataFrame has required structure.

    Args:
        df: DataFrame to validate.
        required_columns: List of column names that must be present.
        min_rows: Minimum number of rows required.
        logger: Logger instance.

    Returns:
        Tuple of (is_valid, list of error messages).
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    errors = []

    # Check for required columns
    missing_cols = set(required_columns) - set(df.columns)
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")

    # Check minimum rows
    if len(df) < min_rows:
        errors.append(f"Expected at least {min_rows} rows, got {len(df)}")

    # Check for completely empty DataFrame
    if df.empty:
        errors.append("DataFrame is empty")

    is_valid = len(errors) == 0

    if not is_valid:
        for error in errors:
            logger.warning(f"Validation error: {error}")
    else:
        logger.debug(f"Validation passed: {len(df)} rows, {len(df.columns)} columns")

    return is_valid, errors


def parse_date(date_str: str, fmt: str = "%Y-%m-%d") -> datetime:
    """Parse a date string to datetime.

    Args:
        date_str: Date string to parse.
        fmt: Date format string.

    Returns:
        Parsed datetime object.
    """
    return datetime.strptime(date_str, fmt)


def get_date_suffix(start_date: datetime, end_date: datetime) -> str:
    """Generate a date suffix for filenames.

    Args:
        start_date: Start of date range.
        end_date: End of date range.

    Returns:
        String like "20240101_20240331".
    """
    return f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"


def handle_api_rate_limit(
    func: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    logger: logging.Logger | None = None,
) -> Any:
    """Decorator/wrapper for handling API rate limits with exponential backoff.

    Args:
        func: Function to call.
        max_retries: Maximum retry attempts.
        base_delay: Base delay in seconds.
        logger: Logger instance.

    Returns:
        Result of function call.

    Raises:
        Exception: If all retry attempts fail.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    last_exception = None

    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            error_str = str(e).lower()

            # Check for rate limit errors
            is_rate_limit = any(
                term in error_str
                for term in ["rate limit", "quota", "too many requests", "429"]
            )

            if is_rate_limit and attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                logger.warning(
                    f"Rate limit hit, attempt {attempt + 1}/{max_retries}. "
                    f"Waiting {delay:.1f}s..."
                )
                time.sleep(delay)
            elif attempt < max_retries - 1:
                logger.warning(f"Error on attempt {attempt + 1}: {e}")
                time.sleep(base_delay)
            else:
                raise

    raise last_exception


class ExtractionMetrics:
    """Track extraction metrics for logging and monitoring."""

    def __init__(self):
        self.start_time = datetime.now()
        self.records_extracted = 0
        self.records_uploaded = 0
        self.errors = []
        self.files_created = []

    def add_records(self, count: int) -> None:
        """Add to extracted record count."""
        self.records_extracted += count

    def add_uploaded(self, count: int) -> None:
        """Add to uploaded record count."""
        self.records_uploaded += count

    def add_error(self, error: str) -> None:
        """Record an error."""
        self.errors.append(error)

    def add_file(self, path: Path) -> None:
        """Record a created file."""
        self.files_created.append(path)

    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        return (datetime.now() - self.start_time).total_seconds()

    def summary(self) -> dict[str, Any]:
        """Get metrics summary."""
        return {
            "elapsed_seconds": self.elapsed_seconds(),
            "records_extracted": self.records_extracted,
            "records_uploaded": self.records_uploaded,
            "files_created": len(self.files_created),
            "errors": len(self.errors),
        }

    def log_summary(self, logger: logging.Logger) -> None:
        """Log a summary of extraction metrics."""
        summary = self.summary()
        logger.info(
            f"Extraction complete in {summary['elapsed_seconds']:.1f}s: "
            f"{summary['records_extracted']} records, "
            f"{summary['files_created']} files, "
            f"{summary['errors']} errors"
        )
