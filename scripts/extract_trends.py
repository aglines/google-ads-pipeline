#!/usr/bin/env python3
"""Extract Google Trends data for the pipeline.

This script extracts Google Trends interest data for relevant keywords.
By default, it uses synthetic data generation. Set --use-synthetic=false
to use the real Google Trends API (pytrends library).

Usage:
    uv run scripts/extract_trends.py
    uv run scripts/extract_trends.py --use-synthetic=false
    uv run scripts/extract_trends.py --keywords "bathroom remodel,kitchen remodel"
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    ExtractionMetrics,
    get_date_suffix,
    parse_date,
    save_to_json,
    setup_logging,
    upload_to_gcs,
    validate_dataframe,
)

logger = setup_logging(__name__)

DEFAULT_OUTPUT_DIR = Path("data/extracted")
DEFAULT_KEYWORDS = [
    "bathroom remodel",
    "bathroom renovation",
    "shower installation",
    "bathtub replacement",
    "bathroom contractor",
    "kitchen remodel",
    "home renovation",
]

# Geographic regions (DMA codes for major metros)
DEFAULT_REGIONS = [
    {"geo": "US-NY", "name": "New York"},
    {"geo": "US-CA", "name": "California"},
    {"geo": "US-TX", "name": "Texas"},
    {"geo": "US-FL", "name": "Florida"},
    {"geo": "US-IL", "name": "Illinois"},
]


class TrendsExtractor:
    """Extract data from Google Trends or synthetic generator."""

    def __init__(
        self,
        use_synthetic: bool = True,
        output_dir: Path | None = None,
        keywords: list[str] | None = None,
        regions: list[dict] | None = None,
    ):
        """Initialize the extractor.

        Args:
            use_synthetic: If True, use synthetic data. If False, use pytrends.
            output_dir: Directory for output files.
            keywords: List of keywords to track.
            regions: List of region dicts with 'geo' and 'name' keys.
        """
        self.use_synthetic = use_synthetic
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.keywords = keywords or DEFAULT_KEYWORDS
        self.regions = regions or DEFAULT_REGIONS

        if use_synthetic:
            logger.info("Using synthetic data mode")
        else:
            logger.info("Using real Google Trends API mode")
            self._init_trends_client()

    def _init_trends_client(self):
        """Initialize the pytrends client.

        This is a placeholder for real API integration.
        Requires pytrends library.
        """
        # Real API integration would go here:
        #
        # from pytrends.request import TrendReq
        #
        # self.pytrends = TrendReq(
        #     hl='en-US',
        #     tz=360,
        #     timeout=(10, 25),
        #     retries=2,
        #     backoff_factor=0.1,
        # )
        #
        # Note: pytrends is an unofficial API and may break.
        # Consider rate limiting and error handling.

        logger.warning(
            "Real Google Trends API requires pytrends library. "
            "Install with: uv add pytrends"
        )
        self.pytrends = None

    def extract_interest_over_time(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract interest over time data for keywords.

        Args:
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            DataFrame with daily interest data.
        """
        logger.info(f"Extracting trends from {start_date.date()} to {end_date.date()}")

        if self.use_synthetic:
            return self._extract_interest_synthetic(start_date, end_date)
        else:
            return self._extract_interest_api(start_date, end_date)

    def _extract_interest_synthetic(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Generate synthetic interest over time data."""
        np.random.seed(42)  # Reproducibility

        records = []
        current_date = start_date

        # Generate seasonal patterns
        while current_date <= end_date:
            # Base seasonality: higher in spring, lower in winter
            month = current_date.month
            seasonal_factor = 1.0 + 0.3 * np.sin((month - 3) * np.pi / 6)

            # Day of week: slightly higher on weekends
            dow = current_date.weekday()
            dow_factor = 1.1 if dow >= 5 else 1.0

            for keyword in self.keywords:
                # Keyword-specific base level
                base = hash(keyword) % 50 + 30  # 30-80 range

                # Add noise and seasonality
                interest = int(
                    base * seasonal_factor * dow_factor * np.random.uniform(0.8, 1.2)
                )
                interest = max(0, min(100, interest))  # Clamp to 0-100

                record = {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "keyword": keyword,
                    "interest": interest,
                    "is_partial": current_date >= end_date - timedelta(days=1),
                }
                records.append(record)

            current_date += timedelta(days=1)

        df = pd.DataFrame(records)
        df["extracted_at"] = datetime.now().isoformat()
        df["data_source"] = "synthetic"

        logger.info(f"Generated {len(df)} trend records (synthetic)")
        return df

    def _extract_interest_api(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract interest over time from Google Trends API.

        This is a placeholder showing the API structure.
        """
        if not self.pytrends:
            raise RuntimeError("pytrends client not initialized")

        # Real API query would look like:
        #
        # timeframe = f"{start_date.strftime('%Y-%m-%d')} {end_date.strftime('%Y-%m-%d')}"
        #
        # # Process keywords in batches of 5 (API limit)
        # all_data = []
        # for i in range(0, len(self.keywords), 5):
        #     batch = self.keywords[i:i+5]
        #     self.pytrends.build_payload(
        #         kw_list=batch,
        #         timeframe=timeframe,
        #         geo='US',
        #     )
        #     df = self.pytrends.interest_over_time()
        #     if not df.empty:
        #         all_data.append(df)
        #     time.sleep(1)  # Rate limit
        #
        # return pd.concat(all_data, axis=1)

        raise NotImplementedError(
            "Real API extraction not implemented. "
            "Use --use-synthetic=true or implement API integration."
        )

    def extract_interest_by_region(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract interest by region data.

        Args:
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            DataFrame with regional interest data.
        """
        logger.info("Extracting regional interest data...")

        if self.use_synthetic:
            return self._extract_regional_synthetic(start_date, end_date)
        else:
            return self._extract_regional_api(start_date, end_date)

    def _extract_regional_synthetic(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Generate synthetic regional interest data."""
        np.random.seed(43)

        records = []

        for region in self.regions:
            # Region-specific factor (some regions have higher search volume)
            region_factor = 0.7 + (hash(region["name"]) % 30) / 100

            for keyword in self.keywords:
                # Base interest varies by keyword
                base = hash(keyword) % 40 + 40  # 40-80 range

                interest = int(base * region_factor * np.random.uniform(0.85, 1.15))
                interest = max(0, min(100, interest))

                record = {
                    "keyword": keyword,
                    "region_code": region["geo"],
                    "region_name": region["name"],
                    "interest": interest,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                }
                records.append(record)

        df = pd.DataFrame(records)
        df["extracted_at"] = datetime.now().isoformat()
        df["data_source"] = "synthetic"

        logger.info(f"Generated {len(df)} regional trend records (synthetic)")
        return df

    def _extract_regional_api(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract regional interest from Google Trends API."""
        if not self.pytrends:
            raise RuntimeError("pytrends client not initialized")

        # Real API query would look like:
        #
        # for keyword in self.keywords:
        #     self.pytrends.build_payload([keyword], geo='US')
        #     df = self.pytrends.interest_by_region(resolution='REGION')
        #     ...

        raise NotImplementedError(
            "Real API extraction not implemented. "
            "Use --use-synthetic=true or implement API integration."
        )

    def extract_related_queries(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract related queries for keywords.

        Args:
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            DataFrame with related query data.
        """
        logger.info("Extracting related queries...")

        if self.use_synthetic:
            return self._extract_related_synthetic(start_date, end_date)
        else:
            return self._extract_related_api(start_date, end_date)

    def _extract_related_synthetic(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Generate synthetic related queries data."""
        np.random.seed(44)

        related_queries = {
            "bathroom remodel": [
                "bathroom remodel cost",
                "small bathroom remodel",
                "bathroom remodel ideas",
                "diy bathroom remodel",
                "bathroom remodel near me",
            ],
            "bathroom renovation": [
                "bathroom renovation ideas",
                "bathroom renovation cost",
                "modern bathroom renovation",
            ],
            "shower installation": [
                "walk in shower installation",
                "shower installation cost",
                "frameless shower installation",
            ],
            "kitchen remodel": [
                "kitchen remodel cost",
                "small kitchen remodel",
                "kitchen remodel ideas",
            ],
        }

        records = []

        for keyword in self.keywords:
            queries = related_queries.get(
                keyword, [f"{keyword} near me", f"{keyword} cost"]
            )

            for i, query in enumerate(queries):
                # Top queries have higher values
                value = 100 - (i * 15) + np.random.randint(-5, 5)
                value = max(10, min(100, value))

                record = {
                    "keyword": keyword,
                    "related_query": query,
                    "query_type": "top",
                    "value": value,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                }
                records.append(record)

        df = pd.DataFrame(records)
        df["extracted_at"] = datetime.now().isoformat()
        df["data_source"] = "synthetic"

        logger.info(f"Generated {len(df)} related query records (synthetic)")
        return df

    def _extract_related_api(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract related queries from Google Trends API."""
        raise NotImplementedError(
            "Real API extraction not implemented. "
            "Use --use-synthetic=true or implement API integration."
        )

    def run_extraction(
        self,
        start_date: datetime,
        end_date: datetime,
        upload: bool = True,
    ) -> dict[str, Path]:
        """Run full trends extraction pipeline.

        Args:
            start_date: Start of date range.
            end_date: End of date range.
            upload: If True, upload to GCS.

        Returns:
            Dictionary mapping data type to output file paths.
        """
        logger.info("Starting Google Trends extraction...")
        metrics = ExtractionMetrics()

        output_files = {}
        date_suffix = get_date_suffix(start_date, end_date)

        # Extract interest over time
        interest_df = self.extract_interest_over_time(start_date, end_date)
        is_valid, errors = validate_dataframe(
            interest_df,
            required_columns=["date", "keyword", "interest"],
            logger=logger,
        )
        if is_valid:
            interest_path = save_to_json(
                interest_df,
                self.output_dir / f"trends_interest_{date_suffix}.json",
                logger=logger,
            )
            output_files["interest"] = interest_path
            metrics.add_records(len(interest_df))
            metrics.add_file(interest_path)

        # Extract regional interest
        regional_df = self.extract_interest_by_region(start_date, end_date)
        if not regional_df.empty:
            regional_path = save_to_json(
                regional_df,
                self.output_dir / f"trends_regional_{date_suffix}.json",
                logger=logger,
            )
            output_files["regional"] = regional_path
            metrics.add_records(len(regional_df))
            metrics.add_file(regional_path)

        # Extract related queries
        related_df = self.extract_related_queries(start_date, end_date)
        if not related_df.empty:
            related_path = save_to_json(
                related_df,
                self.output_dir / f"trends_related_{date_suffix}.json",
                logger=logger,
            )
            output_files["related"] = related_path
            metrics.add_records(len(related_df))
            metrics.add_file(related_path)

        # Upload to GCS
        if upload:
            for data_type, path in output_files.items():
                try:
                    upload_to_gcs(path, f"raw/trends/{data_type}", logger=logger)
                    metrics.add_uploaded(1)
                except Exception as e:
                    logger.error(f"Failed to upload {data_type}: {e}")
                    metrics.add_error(str(e))

        metrics.log_summary(logger)
        return output_files


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Extract Google Trends data")
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
        "--keywords",
        type=str,
        default=None,
        help="Comma-separated list of keywords to track",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip GCS upload",
    )

    args = parser.parse_args()

    use_synthetic = args.use_synthetic.lower() == "true"
    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)
    output_dir = Path(args.output_dir)

    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",")]

    extractor = TrendsExtractor(
        use_synthetic=use_synthetic,
        output_dir=output_dir,
        keywords=keywords,
    )

    extractor.run_extraction(
        start_date=start_date,
        end_date=end_date,
        upload=not args.no_upload,
    )


if __name__ == "__main__":
    main()
