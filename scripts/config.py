"""Configuration management for the Google Ads pipeline.

This module centralizes configuration for all extraction scripts,
managing synthetic vs real API mode and shared settings.

Usage:
    from config import get_config, is_synthetic_mode

    config = get_config()
    if is_synthetic_mode():
        # Use synthetic data
    else:
        # Use real API
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()


@dataclass
class GCPConfig:
    """Google Cloud Platform configuration."""

    project_id: str = field(default_factory=lambda: os.getenv("GCP_PROJECT_ID", ""))
    region: str = field(default_factory=lambda: os.getenv("GCP_REGION", "us-central1"))
    bucket_raw: str = field(
        default_factory=lambda: os.getenv("GCS_BUCKET_RAW_DATA", "")
    )
    bucket_processed: str = field(
        default_factory=lambda: os.getenv("GCS_BUCKET_PROCESSED", "")
    )


@dataclass
class BigQueryConfig:
    """BigQuery dataset configuration."""

    dataset_raw: str = field(
        default_factory=lambda: os.getenv("BQ_DATASET_RAW", "raw_google_ads")
    )
    dataset_staging: str = field(
        default_factory=lambda: os.getenv("BQ_DATASET_STAGING", "staging_google_ads")
    )
    dataset_staging_trends: str = field(
        default_factory=lambda: os.getenv("BQ_DATASET_STAGING_TRENDS", "staging_trends")
    )
    dataset_intermediate: str = field(
        default_factory=lambda: os.getenv("BQ_DATASET_INTERMEDIATE", "intermediate")
    )
    dataset_marts_marketing: str = field(
        default_factory=lambda: os.getenv(
            "BQ_DATASET_MARTS_MARKETING", "marts_marketing"
        )
    )
    dataset_marts_analytics: str = field(
        default_factory=lambda: os.getenv(
            "BQ_DATASET_MARTS_ANALYTICS", "marts_analytics"
        )
    )


@dataclass
class GoogleAdsConfig:
    """Google Ads API configuration (for real API mode)."""

    developer_token: str = field(
        default_factory=lambda: os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
    )
    client_id: str = field(
        default_factory=lambda: os.getenv("GOOGLE_ADS_CLIENT_ID", "")
    )
    client_secret: str = field(
        default_factory=lambda: os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
    )
    refresh_token: str = field(
        default_factory=lambda: os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
    )
    customer_id: str = field(
        default_factory=lambda: os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
    )

    def is_configured(self) -> bool:
        """Check if all required credentials are set."""
        return all(
            [
                self.developer_token,
                self.client_id,
                self.client_secret,
                self.refresh_token,
                self.customer_id,
            ]
        )


@dataclass
class ExternalAPIConfig:
    """External API configuration (for real API mode)."""

    openweather_api_key: str = field(
        default_factory=lambda: os.getenv("OPENWEATHER_API_KEY", "")
    )
    # Google Trends uses unofficial API, no key needed
    # Yahoo Finance typically doesn't require authentication


@dataclass
class ExtractionConfig:
    """Data extraction configuration."""

    use_synthetic: bool = field(
        default_factory=lambda: os.getenv("USE_SYNTHETIC_DATA", "true").lower()
        == "true"
    )
    start_date: datetime = field(
        default_factory=lambda: datetime.strptime(
            os.getenv(
                "DATA_START_DATE",
                (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
            ),
            "%Y-%m-%d",
        )
    )
    end_date: datetime = field(
        default_factory=lambda: datetime.strptime(
            os.getenv("DATA_END_DATE", datetime.now().strftime("%Y-%m-%d")),
            "%Y-%m-%d",
        )
    )
    output_dir: Path = field(default_factory=lambda: Path("data/extracted"))
    synthetic_config_path: Path = field(
        default_factory=lambda: Path("scripts/synthetic_data_config.yaml")
    )
    page_size: int = 10000
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class PipelineConfig:
    """Main pipeline configuration combining all sub-configs."""

    gcp: GCPConfig = field(default_factory=GCPConfig)
    bigquery: BigQueryConfig = field(default_factory=BigQueryConfig)
    google_ads: GoogleAdsConfig = field(default_factory=GoogleAdsConfig)
    external_apis: ExternalAPIConfig = field(default_factory=ExternalAPIConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)

    def validate(self) -> list[str]:
        """Validate configuration and return list of issues."""
        issues = []

        if not self.gcp.project_id:
            issues.append("GCP_PROJECT_ID not set")

        if not self.extraction.use_synthetic:
            if not self.google_ads.is_configured():
                issues.append("Real API mode requires Google Ads credentials")

        return issues

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary (for logging/debugging)."""
        return {
            "gcp": {
                "project_id": self.gcp.project_id,
                "region": self.gcp.region,
                "bucket_raw": self.gcp.bucket_raw,
            },
            "extraction": {
                "use_synthetic": self.extraction.use_synthetic,
                "start_date": self.extraction.start_date.isoformat(),
                "end_date": self.extraction.end_date.isoformat(),
                "output_dir": str(self.extraction.output_dir),
            },
            "google_ads_configured": self.google_ads.is_configured(),
        }


# Global config instance
_config: PipelineConfig | None = None


def get_config() -> PipelineConfig:
    """Get the pipeline configuration (singleton)."""
    global _config
    if _config is None:
        _config = PipelineConfig()
    return _config


def is_synthetic_mode() -> bool:
    """Check if running in synthetic data mode."""
    return get_config().extraction.use_synthetic


def get_date_range() -> tuple[datetime, datetime]:
    """Get the configured date range for extraction."""
    config = get_config()
    return config.extraction.start_date, config.extraction.end_date


if __name__ == "__main__":
    # Print current configuration when run directly
    import json

    config = get_config()
    issues = config.validate()

    print("Pipeline Configuration")
    print("=" * 50)
    print(json.dumps(config.to_dict(), indent=2))

    if issues:
        print("\nConfiguration Issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\nConfiguration valid.")
