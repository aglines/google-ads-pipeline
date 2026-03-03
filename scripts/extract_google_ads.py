#!/usr/bin/env python3
"""Extract Google Ads data for the pipeline.

This script extracts Google Ads campaign and keyword performance data.
By default, it uses synthetic data generation. Set --use-synthetic=false
to use the real Google Ads API (requires credentials).

Usage:
    uv run scripts/extract_google_ads.py
    uv run scripts/extract_google_ads.py --use-synthetic=false
    uv run scripts/extract_google_ads.py --start-date 2024-01-01 --end-date 2024-03-31
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator

import pandas as pd
from dotenv import load_dotenv
from google.cloud import storage

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from generate_synthetic_data import SyntheticDataGenerator
from utils import parse_date

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
DEFAULT_CONFIG_PATH = Path(__file__).parent / "synthetic_data_config.yaml"
DEFAULT_OUTPUT_DIR = Path("data/extracted")
DEFAULT_PAGE_SIZE = 10000


class GoogleAdsExtractor:
    """Extract data from Google Ads API or synthetic generator."""

    def __init__(
        self,
        use_synthetic: bool = True,
        config_path: Path | None = None,
        output_dir: Path | None = None,
    ):
        """Initialize the extractor.

        Args:
            use_synthetic: If True, use synthetic data generator. If False, use real API.
            config_path: Path to synthetic data config (for synthetic mode).
            output_dir: Directory for output files.
        """
        self.use_synthetic = use_synthetic
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # GCP configuration
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.bucket_name = os.getenv("GCS_BUCKET_RAW_DATA")

        if use_synthetic:
            logger.info("Using synthetic data mode")
            self.generator = SyntheticDataGenerator(self.config_path)
        else:
            logger.info("Using real Google Ads API mode")
            self._init_google_ads_client()

    def _init_google_ads_client(self):
        """Initialize the Google Ads API client.

        This is a placeholder for real API integration.
        Requires google-ads library and proper credentials.
        """
        # Real API integration would go here:
        #
        # from google.ads.googleads.client import GoogleAdsClient
        #
        # Required environment variables:
        # - GOOGLE_ADS_DEVELOPER_TOKEN
        # - GOOGLE_ADS_CLIENT_ID
        # - GOOGLE_ADS_CLIENT_SECRET
        # - GOOGLE_ADS_REFRESH_TOKEN
        # - GOOGLE_ADS_CUSTOMER_ID
        #
        # self.client = GoogleAdsClient.load_from_env()
        # self.customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")

        logger.warning(
            "Real Google Ads API mode requires credentials. "
            "See docs/real_api_integration.md for setup instructions."
        )
        self.client = None
        self.customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")

    def extract_campaigns(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract campaign data for a date range.

        Args:
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            DataFrame with campaign data.
        """
        logger.info(
            f"Extracting campaigns from {start_date.date()} to {end_date.date()}"
        )

        if self.use_synthetic:
            return self._extract_campaigns_synthetic(start_date, end_date)
        else:
            return self._extract_campaigns_api(start_date, end_date)

    def _extract_campaigns_synthetic(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract campaigns from synthetic generator."""
        # Update generator date range
        self.generator.start_date = start_date
        self.generator.end_date = end_date

        # Generate campaign structure
        self.generator.generate_campaigns()

        # Convert to DataFrame
        df = pd.DataFrame(self.generator.campaigns)
        df["extracted_at"] = datetime.now().isoformat()
        df["data_source"] = "synthetic"

        logger.info(f"Extracted {len(df)} campaigns (synthetic)")
        return df

    def _extract_campaigns_api(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract campaigns from Google Ads API.

        This is a placeholder showing the API structure.
        """
        if not self.client:
            raise RuntimeError("Google Ads client not initialized. Check credentials.")

        # Real API query would look like:
        #
        # query = '''
        #     SELECT
        #         campaign.id,
        #         campaign.name,
        #         campaign.status,
        #         campaign.advertising_channel_type,
        #         metrics.impressions,
        #         metrics.clicks,
        #         metrics.cost_micros
        #     FROM campaign
        #     WHERE segments.date BETWEEN '{start}' AND '{end}'
        # '''.format(
        #     start=start_date.strftime('%Y-%m-%d'),
        #     end=end_date.strftime('%Y-%m-%d')
        # )
        #
        # ga_service = self.client.get_service("GoogleAdsService")
        # response = ga_service.search_stream(
        #     customer_id=self.customer_id,
        #     query=query
        # )
        #
        # records = []
        # for batch in response:
        #     for row in batch.results:
        #         records.append({
        #             'campaign_id': row.campaign.id,
        #             'campaign_name': row.campaign.name,
        #             ...
        #         })

        raise NotImplementedError(
            "Real API extraction not implemented. "
            "Use --use-synthetic=true or implement API integration."
        )

    def extract_keywords(
        self,
        start_date: datetime,
        end_date: datetime,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> Generator[pd.DataFrame, None, None]:
        """Extract keyword performance data with pagination.

        Args:
            start_date: Start of date range.
            end_date: End of date range.
            page_size: Number of records per page.

        Yields:
            DataFrames with keyword data (one per page).
        """
        logger.info(
            f"Extracting keywords from {start_date.date()} to {end_date.date()}"
        )

        if self.use_synthetic:
            yield from self._extract_keywords_synthetic(start_date, end_date, page_size)
        else:
            yield from self._extract_keywords_api(start_date, end_date, page_size)

    def _extract_keywords_synthetic(
        self,
        start_date: datetime,
        end_date: datetime,
        page_size: int,
    ) -> Generator[pd.DataFrame, None, None]:
        """Extract keywords from synthetic generator with pagination."""
        # Update generator date range
        self.generator.start_date = start_date
        self.generator.end_date = end_date

        # Generate full data
        self.generator.generate_campaigns()
        self.generator.generate_ad_groups()
        self.generator.generate_keywords()
        keyword_df = self.generator.generate_keyword_performance()

        # Add metadata
        keyword_df["extracted_at"] = datetime.now().isoformat()
        keyword_df["data_source"] = "synthetic"

        # Paginate results
        total_records = len(keyword_df)
        total_pages = (total_records + page_size - 1) // page_size

        logger.info(f"Total records: {total_records}, Pages: {total_pages}")

        for page_num in range(total_pages):
            start_idx = page_num * page_size
            end_idx = min(start_idx + page_size, total_records)

            page_df = keyword_df.iloc[start_idx:end_idx].copy()
            page_df["page_number"] = page_num + 1
            page_df["total_pages"] = total_pages

            logger.info(
                f"Yielding page {page_num + 1}/{total_pages} ({len(page_df)} records)"
            )
            yield page_df

    def _extract_keywords_api(
        self,
        start_date: datetime,
        end_date: datetime,
        page_size: int,
    ) -> Generator[pd.DataFrame, None, None]:
        """Extract keywords from Google Ads API with pagination.

        This is a placeholder showing the API structure.
        """
        if not self.client:
            raise RuntimeError("Google Ads client not initialized. Check credentials.")

        # Real API query with pagination would look like:
        #
        # query = '''
        #     SELECT
        #         ad_group_criterion.keyword.text,
        #         ad_group_criterion.keyword.match_type,
        #         campaign.name,
        #         ad_group.name,
        #         metrics.impressions,
        #         metrics.clicks,
        #         metrics.cost_micros,
        #         metrics.conversions,
        #         ad_group_criterion.quality_info.quality_score
        #     FROM keyword_view
        #     WHERE segments.date BETWEEN '{start}' AND '{end}'
        #     LIMIT {page_size}
        #     OFFSET {offset}
        # '''
        #
        # offset = 0
        # while True:
        #     response = ga_service.search(
        #         customer_id=self.customer_id,
        #         query=query.format(
        #             start=start_date.strftime('%Y-%m-%d'),
        #             end=end_date.strftime('%Y-%m-%d'),
        #             page_size=page_size,
        #             offset=offset
        #         )
        #     )
        #     records = [...]  # Process response
        #     if not records:
        #         break
        #     yield pd.DataFrame(records)
        #     offset += page_size

        raise NotImplementedError(
            "Real API extraction not implemented. "
            "Use --use-synthetic=true or implement API integration."
        )

    def extract_search_terms(
        self,
        start_date: datetime,
        end_date: datetime,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> Generator[pd.DataFrame, None, None]:
        """Extract search term data with pagination.

        Args:
            start_date: Start of date range.
            end_date: End of date range.
            page_size: Number of records per page.

        Yields:
            DataFrames with search term data (one per page).
        """
        logger.info(
            f"Extracting search terms from {start_date.date()} to {end_date.date()}"
        )

        if self.use_synthetic:
            yield from self._extract_search_terms_synthetic(
                start_date, end_date, page_size
            )
        else:
            yield from self._extract_search_terms_api(start_date, end_date, page_size)

    def _extract_search_terms_synthetic(
        self,
        start_date: datetime,
        end_date: datetime,
        page_size: int,
    ) -> Generator[pd.DataFrame, None, None]:
        """Extract search terms from synthetic generator with pagination."""
        # Generate keyword data first (needed for search terms)
        self.generator.start_date = start_date
        self.generator.end_date = end_date

        if not self.generator.keywords:
            self.generator.generate_campaigns()
            self.generator.generate_ad_groups()
            self.generator.generate_keywords()

        keyword_df = self.generator.generate_keyword_performance()
        search_term_df = self.generator.generate_search_terms(keyword_df)

        # Add metadata
        search_term_df["extracted_at"] = datetime.now().isoformat()
        search_term_df["data_source"] = "synthetic"

        # Paginate results
        total_records = len(search_term_df)
        total_pages = (total_records + page_size - 1) // page_size

        logger.info(f"Total search terms: {total_records}, Pages: {total_pages}")

        for page_num in range(total_pages):
            start_idx = page_num * page_size
            end_idx = min(start_idx + page_size, total_records)

            page_df = search_term_df.iloc[start_idx:end_idx].copy()
            page_df["page_number"] = page_num + 1
            page_df["total_pages"] = total_pages

            logger.info(
                f"Yielding page {page_num + 1}/{total_pages} ({len(page_df)} records)"
            )
            yield page_df

    def _extract_search_terms_api(
        self,
        start_date: datetime,
        end_date: datetime,
        page_size: int,
    ) -> Generator[pd.DataFrame, None, None]:
        """Extract search terms from Google Ads API."""
        raise NotImplementedError(
            "Real API extraction not implemented. "
            "Use --use-synthetic=true or implement API integration."
        )

    def extract_auction_insights(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract auction insights data.

        Args:
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            DataFrame with auction insights.
        """
        logger.info(
            f"Extracting auction insights from {start_date.date()} to {end_date.date()}"
        )

        if self.use_synthetic:
            return self._extract_auction_insights_synthetic(start_date, end_date)
        else:
            return self._extract_auction_insights_api(start_date, end_date)

    def _extract_auction_insights_synthetic(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract auction insights from synthetic generator."""
        self.generator.start_date = start_date
        self.generator.end_date = end_date

        df = self.generator.generate_auction_insights()
        df["extracted_at"] = datetime.now().isoformat()
        df["data_source"] = "synthetic"

        logger.info(f"Extracted {len(df)} auction insight records (synthetic)")
        return df

    def _extract_auction_insights_api(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract auction insights from Google Ads API."""
        raise NotImplementedError(
            "Real API extraction not implemented. "
            "Use --use-synthetic=true or implement API integration."
        )

    def save_to_json(
        self,
        df: pd.DataFrame,
        filename: str,
        append: bool = False,
    ) -> Path:
        """Save DataFrame to JSON file.

        Args:
            df: Data to save.
            filename: Output filename (without path).
            append: If True, append to existing file.

        Returns:
            Path to saved file.
        """
        output_path = self.output_dir / filename

        if append and output_path.exists():
            # Load existing data and append
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

    def upload_to_gcs(
        self,
        local_path: Path,
        gcs_prefix: str = "raw/google_ads",
        max_retries: int = 3,
    ) -> str:
        """Upload file to Google Cloud Storage.

        Args:
            local_path: Path to local file.
            gcs_prefix: Prefix for GCS object name.
            max_retries: Maximum retry attempts.

        Returns:
            GCS URI of uploaded file.
        """
        if not self.bucket_name:
            logger.warning("GCS_BUCKET_RAW_DATA not set, skipping upload")
            return ""

        blob_name = f"{gcs_prefix}/{local_path.name}"

        for attempt in range(max_retries):
            try:
                client = storage.Client(project=self.project_id)
                bucket = client.bucket(self.bucket_name)
                blob = bucket.blob(blob_name)

                blob.upload_from_filename(str(local_path))

                gcs_uri = f"gs://{self.bucket_name}/{blob_name}"
                logger.info(f"Uploaded to {gcs_uri}")
                return gcs_uri

            except Exception as e:
                logger.warning(f"Upload attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff
                else:
                    raise

        return ""

    def run_extraction(
        self,
        start_date: datetime,
        end_date: datetime,
        upload: bool = True,
    ) -> dict[str, Path]:
        """Run full extraction pipeline.

        Args:
            start_date: Start of date range.
            end_date: End of date range.
            upload: If True, upload to GCS after extraction.

        Returns:
            Dictionary mapping data type to output file paths.
        """
        logger.info("Starting Google Ads extraction...")
        start_time = datetime.now()

        output_files = {}
        date_suffix = start_date.strftime("%Y%m%d") + "_" + end_date.strftime("%Y%m%d")

        # Extract campaigns
        campaigns_df = self.extract_campaigns(start_date, end_date)
        campaigns_path = self.save_to_json(
            campaigns_df, f"campaigns_{date_suffix}.json"
        )
        output_files["campaigns"] = campaigns_path

        # Extract keywords (paginated)
        keywords_path = self.output_dir / f"keywords_{date_suffix}.json"
        all_keywords = []
        for page_df in self.extract_keywords(start_date, end_date):
            all_keywords.extend(page_df.to_dict(orient="records"))

        with open(keywords_path, "w") as f:
            json.dump(all_keywords, f, indent=2, default=str)
        logger.info(f"Saved {len(all_keywords)} keyword records to {keywords_path}")
        output_files["keywords"] = keywords_path

        # Extract search terms (paginated)
        search_terms_path = self.output_dir / f"search_terms_{date_suffix}.json"
        all_search_terms = []
        for page_df in self.extract_search_terms(start_date, end_date):
            all_search_terms.extend(page_df.to_dict(orient="records"))

        with open(search_terms_path, "w") as f:
            json.dump(all_search_terms, f, indent=2, default=str)
        logger.info(
            f"Saved {len(all_search_terms)} search term records to {search_terms_path}"
        )
        output_files["search_terms"] = search_terms_path

        # Extract auction insights
        auction_df = self.extract_auction_insights(start_date, end_date)
        auction_path = self.save_to_json(
            auction_df, f"auction_insights_{date_suffix}.json"
        )
        output_files["auction_insights"] = auction_path

        # Upload to GCS
        if upload:
            for data_type, path in output_files.items():
                try:
                    self.upload_to_gcs(path, f"raw/google_ads/{data_type}")
                except Exception as e:
                    logger.error(f"Failed to upload {data_type}: {e}")

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Extraction complete in {elapsed:.1f} seconds")

        return output_files


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Extract Google Ads data")
    parser.add_argument(
        "--use-synthetic",
        type=str,
        default="true",
        choices=["true", "false"],
        help="Use synthetic data (default: true)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=(datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=datetime.now().strftime("%Y-%m-%d"),
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/extracted",
        help="Output directory",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip GCS upload",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to synthetic data config",
    )

    args = parser.parse_args()

    use_synthetic = args.use_synthetic.lower() == "true"
    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)
    output_dir = Path(args.output_dir)
    config_path = Path(args.config) if args.config else None

    extractor = GoogleAdsExtractor(
        use_synthetic=use_synthetic,
        config_path=config_path,
        output_dir=output_dir,
    )

    extractor.run_extraction(
        start_date=start_date,
        end_date=end_date,
        upload=not args.no_upload,
    )


if __name__ == "__main__":
    main()
