#!/usr/bin/env python3
# NOTE: This script is a stub for future real API integration.
# Currently not called from the main DAG pipeline.
# See docs/PROJECT.md Step 12 for integration plans.
"""Extract weather data for the pipeline.

This script extracts historical weather data for target markets.
By default, it uses synthetic data generation. Set --use-synthetic=false
to use the real OpenWeatherMap API.

Weather data helps correlate ad performance with weather conditions
(e.g., bathroom remodeling interest may increase during cold/rainy periods).

Usage:
    uv run scripts/extract_weather.py
    uv run scripts/extract_weather.py --use-synthetic=false
    uv run scripts/extract_weather.py --cities "New York,Los Angeles"
"""

import argparse
import os
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

# Target markets with coordinates for weather API
DEFAULT_CITIES = [
    {"name": "New York", "lat": 40.7128, "lon": -74.0060, "state": "NY"},
    {"name": "Los Angeles", "lat": 34.0522, "lon": -118.2437, "state": "CA"},
    {"name": "Chicago", "lat": 41.8781, "lon": -87.6298, "state": "IL"},
    {"name": "Houston", "lat": 29.7604, "lon": -95.3698, "state": "TX"},
    {"name": "Phoenix", "lat": 33.4484, "lon": -112.0740, "state": "AZ"},
    {"name": "Philadelphia", "lat": 39.9526, "lon": -75.1652, "state": "PA"},
    {"name": "San Antonio", "lat": 29.4241, "lon": -98.4936, "state": "TX"},
    {"name": "San Diego", "lat": 32.7157, "lon": -117.1611, "state": "CA"},
    {"name": "Dallas", "lat": 32.7767, "lon": -96.7970, "state": "TX"},
    {"name": "San Jose", "lat": 37.3382, "lon": -121.8863, "state": "CA"},
]

# Weather condition codes and descriptions
WEATHER_CONDITIONS = [
    {"code": 800, "main": "Clear", "description": "clear sky"},
    {"code": 801, "main": "Clouds", "description": "few clouds"},
    {"code": 802, "main": "Clouds", "description": "scattered clouds"},
    {"code": 803, "main": "Clouds", "description": "broken clouds"},
    {"code": 804, "main": "Clouds", "description": "overcast clouds"},
    {"code": 500, "main": "Rain", "description": "light rain"},
    {"code": 501, "main": "Rain", "description": "moderate rain"},
    {"code": 502, "main": "Rain", "description": "heavy rain"},
    {"code": 600, "main": "Snow", "description": "light snow"},
    {"code": 601, "main": "Snow", "description": "snow"},
]


class WeatherExtractor:
    """Extract data from OpenWeatherMap or synthetic generator."""

    def __init__(
        self,
        use_synthetic: bool = True,
        output_dir: Path | None = None,
        cities: list[dict] | None = None,
    ):
        """Initialize the extractor.

        Args:
            use_synthetic: If True, use synthetic data. If False, use real API.
            output_dir: Directory for output files.
            cities: List of city dicts with name, lat, lon, state.
        """
        self.use_synthetic = use_synthetic
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cities = cities or DEFAULT_CITIES

        self.api_key = os.getenv("OPENWEATHER_API_KEY", "")

        if use_synthetic:
            logger.info("Using synthetic data mode")
        else:
            logger.info("Using real OpenWeatherMap API mode")
            self._validate_api_key()

    def _validate_api_key(self):
        """Validate that API key is configured."""
        if not self.api_key:
            logger.warning(
                "OPENWEATHER_API_KEY not set. "
                "Real API mode requires an API key from openweathermap.org"
            )

    def extract_historical_weather(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract historical weather data for all cities.

        Args:
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            DataFrame with daily weather data.
        """
        logger.info(f"Extracting weather from {start_date.date()} to {end_date.date()}")

        if self.use_synthetic:
            return self._extract_weather_synthetic(start_date, end_date)
        else:
            return self._extract_weather_api(start_date, end_date)

    def _extract_weather_synthetic(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Generate synthetic historical weather data."""
        np.random.seed(45)

        records = []
        current_date = start_date

        while current_date <= end_date:
            month = current_date.month
            day_of_year = current_date.timetuple().tm_yday

            for city in self.cities:
                # Base temperature varies by latitude and season
                # Higher latitude = colder; winter = colder
                lat_factor = (city["lat"] - 25) / 25  # 0 to 1 range
                season_factor = np.cos((day_of_year - 172) * 2 * np.pi / 365)

                # Base temp in Fahrenheit
                base_temp = 70 - (lat_factor * 20) + (season_factor * 25)

                # Daily variation
                temp_high = base_temp + np.random.uniform(5, 15)
                temp_low = base_temp - np.random.uniform(5, 15)
                temp_avg = (temp_high + temp_low) / 2

                # Humidity varies by region
                base_humidity = 50 + (20 if city["state"] in ["FL", "TX", "LA"] else 0)
                humidity = base_humidity + np.random.uniform(-15, 15)
                humidity = max(20, min(100, humidity))

                # Weather conditions based on season and region
                if month in [12, 1, 2] and city["lat"] > 35:
                    # Winter in northern cities - more likely snow/clouds
                    condition_weights = [
                        0.1,
                        0.1,
                        0.15,
                        0.2,
                        0.2,
                        0.05,
                        0.05,
                        0.02,
                        0.08,
                        0.05,
                    ]
                elif month in [6, 7, 8]:
                    # Summer - more clear skies
                    condition_weights = [
                        0.35,
                        0.25,
                        0.15,
                        0.1,
                        0.05,
                        0.05,
                        0.03,
                        0.02,
                        0,
                        0,
                    ]
                else:
                    # Spring/Fall - mixed
                    condition_weights = [
                        0.2,
                        0.2,
                        0.2,
                        0.15,
                        0.1,
                        0.08,
                        0.05,
                        0.02,
                        0,
                        0,
                    ]

                # Normalize weights
                condition_weights = [
                    w / sum(condition_weights) for w in condition_weights
                ]
                condition = np.random.choice(WEATHER_CONDITIONS, p=condition_weights)

                # Precipitation
                if condition["main"] in ["Rain", "Snow"]:
                    precipitation = np.random.uniform(0.1, 1.5)
                else:
                    precipitation = 0.0

                # Wind speed
                wind_speed = np.random.lognormal(1.5, 0.5)
                wind_speed = min(wind_speed, 30)

                record = {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "city": city["name"],
                    "state": city["state"],
                    "lat": city["lat"],
                    "lon": city["lon"],
                    "temp_high_f": round(temp_high, 1),
                    "temp_low_f": round(temp_low, 1),
                    "temp_avg_f": round(temp_avg, 1),
                    "humidity_pct": round(humidity, 1),
                    "precipitation_in": round(precipitation, 2),
                    "wind_speed_mph": round(wind_speed, 1),
                    "weather_code": condition["code"],
                    "weather_main": condition["main"],
                    "weather_description": condition["description"],
                }
                records.append(record)

            current_date += timedelta(days=1)

        df = pd.DataFrame(records)
        df["extracted_at"] = datetime.now().isoformat()
        df["data_source"] = "synthetic"

        logger.info(f"Generated {len(df)} weather records (synthetic)")
        return df

    def _extract_weather_api(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract historical weather from OpenWeatherMap API.

        This is a placeholder showing the API structure.
        """
        if not self.api_key:
            raise RuntimeError("OPENWEATHER_API_KEY not set")

        # Real API integration would go here:
        #
        # import requests
        #
        # base_url = "https://api.openweathermap.org/data/2.5/onecall/timemachine"
        #
        # records = []
        # current_date = start_date
        #
        # while current_date <= end_date:
        #     for city in self.cities:
        #         timestamp = int(current_date.timestamp())
        #
        #         def fetch():
        #             response = requests.get(
        #                 base_url,
        #                 params={
        #                     "lat": city["lat"],
        #                     "lon": city["lon"],
        #                     "dt": timestamp,
        #                     "appid": self.api_key,
        #                     "units": "imperial",
        #                 },
        #             )
        #             response.raise_for_status()
        #             return response.json()
        #
        #         data = handle_api_rate_limit(fetch, logger=logger)
        #
        #         # Parse response...
        #         records.append({...})
        #
        #     current_date += timedelta(days=1)
        #
        # return pd.DataFrame(records)

        raise NotImplementedError(
            "Real API extraction not implemented. "
            "Use --use-synthetic=true or implement API integration."
        )

    def extract_weather_summary(
        self,
        weather_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Generate monthly weather summaries by city.

        Args:
            weather_df: Daily weather data.

        Returns:
            DataFrame with monthly aggregations.
        """
        logger.info("Generating weather summaries...")

        # Add month column
        weather_df = weather_df.copy()
        weather_df["month"] = pd.to_datetime(weather_df["date"]).dt.to_period("M")

        # Aggregate by city and month
        summary = (
            weather_df.groupby(["city", "state", "month"])
            .agg(
                {
                    "temp_high_f": "mean",
                    "temp_low_f": "mean",
                    "temp_avg_f": "mean",
                    "humidity_pct": "mean",
                    "precipitation_in": "sum",
                    "wind_speed_mph": "mean",
                }
            )
            .reset_index()
        )

        # Add dominant weather
        summary = summary.merge(
            weather_df.groupby(["city", "state", "month"])["weather_main"]
            .agg(lambda x: x.mode()[0] if len(x.mode()) > 0 else "Clear")
            .reset_index()
            .rename(columns={"weather_main": "dominant_weather"}),
            on=["city", "state", "month"],
        )

        # Count rainy days
        rainy_days = (
            weather_df[weather_df["precipitation_in"] > 0]
            .groupby(["city", "state", "month"])
            .size()
            .reset_index(name="rainy_days")
        )

        summary = summary.merge(rainy_days, on=["city", "state", "month"], how="left")
        summary["rainy_days"] = summary["rainy_days"].fillna(0).astype(int)

        # Convert month to string
        summary["month"] = summary["month"].astype(str)

        # Round numeric columns
        for col in [
            "temp_high_f",
            "temp_low_f",
            "temp_avg_f",
            "humidity_pct",
            "wind_speed_mph",
        ]:
            summary[col] = summary[col].round(1)
        summary["precipitation_in"] = summary["precipitation_in"].round(2)

        summary["extracted_at"] = datetime.now().isoformat()
        summary["data_source"] = weather_df["data_source"].iloc[0]

        logger.info(f"Generated {len(summary)} monthly summary records")
        return summary

    def run_extraction(
        self,
        start_date: datetime,
        end_date: datetime,
        upload: bool = True,
    ) -> dict[str, Path]:
        """Run full weather extraction pipeline.

        Args:
            start_date: Start of date range.
            end_date: End of date range.
            upload: If True, upload to GCS.

        Returns:
            Dictionary mapping data type to output file paths.
        """
        logger.info("Starting weather extraction...")
        metrics = ExtractionMetrics()

        output_files = {}
        date_suffix = get_date_suffix(start_date, end_date)

        # Extract daily weather
        weather_df = self.extract_historical_weather(start_date, end_date)
        is_valid, errors = validate_dataframe(
            weather_df,
            required_columns=["date", "city", "temp_avg_f", "weather_main"],
            logger=logger,
        )
        if is_valid:
            daily_path = save_to_json(
                weather_df,
                self.output_dir / f"weather_daily_{date_suffix}.json",
                logger=logger,
            )
            output_files["daily"] = daily_path
            metrics.add_records(len(weather_df))
            metrics.add_file(daily_path)

        # Generate monthly summary
        summary_df = self.extract_weather_summary(weather_df)
        if not summary_df.empty:
            summary_path = save_to_json(
                summary_df,
                self.output_dir / f"weather_summary_{date_suffix}.json",
                logger=logger,
            )
            output_files["summary"] = summary_path
            metrics.add_records(len(summary_df))
            metrics.add_file(summary_path)

        # Upload to GCS
        if upload:
            for data_type, path in output_files.items():
                try:
                    upload_to_gcs(path, f"raw/weather/{data_type}", logger=logger)
                    metrics.add_uploaded(1)
                except Exception as e:
                    logger.error(f"Failed to upload {data_type}: {e}")
                    metrics.add_error(str(e))

        metrics.log_summary(logger)
        return output_files


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Extract weather data")
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
        "--cities",
        type=str,
        default=None,
        help="Comma-separated list of city names (uses defaults if not specified)",
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

    # Filter cities if specified
    cities = None
    if args.cities:
        city_names = [c.strip() for c in args.cities.split(",")]
        cities = [c for c in DEFAULT_CITIES if c["name"] in city_names]
        if not cities:
            logger.warning(f"No matching cities found for: {args.cities}")
            cities = DEFAULT_CITIES

    extractor = WeatherExtractor(
        use_synthetic=use_synthetic,
        output_dir=output_dir,
        cities=cities,
    )

    extractor.run_extraction(
        start_date=start_date,
        end_date=end_date,
        upload=not args.no_upload,
    )


if __name__ == "__main__":
    main()
