#!/usr/bin/env python3
# NOTE: This script is a stub for future real API integration.
# Currently not called from the main DAG pipeline.
# See docs/PROJECT.md Step 12 for integration plans.
"""Extract financial/economic data for the pipeline.

This script extracts market indicators and economic data relevant to
home improvement industry performance (housing starts, consumer confidence,
building materials prices, etc.).

By default, it uses synthetic data generation. Set --use-synthetic=false
to use real APIs (Yahoo Finance, FRED, etc.).

Usage:
    uv run scripts/extract_finance.py
    uv run scripts/extract_finance.py --use-synthetic=false
    uv run scripts/extract_finance.py --indicators "housing_starts,consumer_confidence"
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

# Stock tickers relevant to home improvement industry
STOCK_TICKERS = [
    {"symbol": "HD", "name": "Home Depot", "sector": "Home Improvement Retail"},
    {"symbol": "LOW", "name": "Lowe's", "sector": "Home Improvement Retail"},
    {"symbol": "BLDR", "name": "Builders FirstSource", "sector": "Building Products"},
    {"symbol": "MAS", "name": "Masco Corporation", "sector": "Building Products"},
    {"symbol": "SHW", "name": "Sherwin-Williams", "sector": "Building Products"},
    {"symbol": "MLM", "name": "Martin Marietta", "sector": "Construction Materials"},
    {"symbol": "VMC", "name": "Vulcan Materials", "sector": "Construction Materials"},
]

# Economic indicators
ECONOMIC_INDICATORS = [
    {
        "id": "housing_starts",
        "name": "Housing Starts",
        "unit": "thousands",
        "frequency": "monthly",
    },
    {
        "id": "building_permits",
        "name": "Building Permits",
        "unit": "thousands",
        "frequency": "monthly",
    },
    {
        "id": "consumer_confidence",
        "name": "Consumer Confidence Index",
        "unit": "index",
        "frequency": "monthly",
    },
    {
        "id": "home_price_index",
        "name": "Case-Shiller Home Price Index",
        "unit": "index",
        "frequency": "monthly",
    },
    {
        "id": "mortgage_rate_30y",
        "name": "30-Year Mortgage Rate",
        "unit": "percent",
        "frequency": "weekly",
    },
    {
        "id": "unemployment_rate",
        "name": "Unemployment Rate",
        "unit": "percent",
        "frequency": "monthly",
    },
]


class FinanceExtractor:
    """Extract financial and economic data."""

    def __init__(
        self,
        use_synthetic: bool = True,
        output_dir: Path | None = None,
        tickers: list[dict] | None = None,
        indicators: list[dict] | None = None,
    ):
        """Initialize the extractor.

        Args:
            use_synthetic: If True, use synthetic data. If False, use real APIs.
            output_dir: Directory for output files.
            tickers: List of stock ticker dicts with symbol, name, sector.
            indicators: List of economic indicator dicts.
        """
        self.use_synthetic = use_synthetic
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tickers = tickers or STOCK_TICKERS
        self.indicators = indicators or ECONOMIC_INDICATORS

        if use_synthetic:
            logger.info("Using synthetic data mode")
        else:
            logger.info("Using real finance API mode")
            self._init_api_clients()

    def _init_api_clients(self):
        """Initialize finance API clients.

        This is a placeholder for real API integration.
        """
        # Real API integration would go here:
        #
        # For Yahoo Finance:
        # import yfinance as yf
        # self.yf = yf
        #
        # For FRED (Federal Reserve Economic Data):
        # from fredapi import Fred
        # self.fred = Fred(api_key=os.getenv("FRED_API_KEY"))
        #
        # Note: yfinance doesn't require authentication
        # FRED requires a free API key

        logger.warning(
            "Real finance APIs require additional libraries. "
            "Install with: uv add yfinance fredapi"
        )
        self.yf = None
        self.fred = None

    def extract_stock_prices(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract daily stock prices for relevant tickers.

        Args:
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            DataFrame with daily stock data.
        """
        logger.info(
            f"Extracting stock prices from {start_date.date()} to {end_date.date()}"
        )

        if self.use_synthetic:
            return self._extract_stocks_synthetic(start_date, end_date)
        else:
            return self._extract_stocks_api(start_date, end_date)

    def _extract_stocks_synthetic(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Generate synthetic stock price data."""
        np.random.seed(46)

        records = []

        # Generate realistic base prices and volatilities
        ticker_params = {
            "HD": {"base_price": 350, "volatility": 0.02, "trend": 0.0003},
            "LOW": {"base_price": 220, "volatility": 0.022, "trend": 0.0002},
            "BLDR": {"base_price": 150, "volatility": 0.03, "trend": 0.0004},
            "MAS": {"base_price": 70, "volatility": 0.025, "trend": 0.0001},
            "SHW": {"base_price": 280, "volatility": 0.018, "trend": 0.0003},
            "MLM": {"base_price": 450, "volatility": 0.02, "trend": 0.0002},
            "VMC": {"base_price": 220, "volatility": 0.022, "trend": 0.0001},
        }

        for ticker in self.tickers:
            params = ticker_params.get(
                ticker["symbol"],
                {"base_price": 100, "volatility": 0.025, "trend": 0.0002},
            )

            current_date = start_date
            price = params["base_price"]

            while current_date <= end_date:
                # Skip weekends
                if current_date.weekday() >= 5:
                    current_date += timedelta(days=1)
                    continue

                # Random walk with drift
                daily_return = (
                    params["trend"] + params["volatility"] * np.random.randn()
                )
                price = price * (1 + daily_return)
                price = max(price, params["base_price"] * 0.5)  # Floor at 50%

                # Generate OHLC data
                intraday_vol = params["volatility"] * 0.5
                high = price * (1 + abs(np.random.randn() * intraday_vol))
                low = price * (1 - abs(np.random.randn() * intraday_vol))
                open_price = low + (high - low) * np.random.random()

                # Volume varies with volatility
                base_volume = (
                    5_000_000 if ticker["symbol"] in ["HD", "LOW"] else 1_000_000
                )
                volume = int(base_volume * np.random.lognormal(0, 0.5))

                record = {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "symbol": ticker["symbol"],
                    "name": ticker["name"],
                    "sector": ticker["sector"],
                    "open": round(open_price, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(price, 2),
                    "volume": volume,
                    "adj_close": round(price, 2),
                }
                records.append(record)

                current_date += timedelta(days=1)

        df = pd.DataFrame(records)
        df["extracted_at"] = datetime.now().isoformat()
        df["data_source"] = "synthetic"

        logger.info(f"Generated {len(df)} stock price records (synthetic)")
        return df

    def _extract_stocks_api(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract stock prices from Yahoo Finance API.

        This is a placeholder showing the API structure.
        """
        if not self.yf:
            raise RuntimeError("yfinance not initialized")

        # Real API integration would go here:
        #
        # import yfinance as yf
        #
        # records = []
        # for ticker in self.tickers:
        #     stock = yf.Ticker(ticker["symbol"])
        #     hist = stock.history(
        #         start=start_date.strftime("%Y-%m-%d"),
        #         end=end_date.strftime("%Y-%m-%d"),
        #     )
        #
        #     for date, row in hist.iterrows():
        #         records.append({
        #             "date": date.strftime("%Y-%m-%d"),
        #             "symbol": ticker["symbol"],
        #             "open": row["Open"],
        #             "high": row["High"],
        #             "low": row["Low"],
        #             "close": row["Close"],
        #             "volume": row["Volume"],
        #         })
        #
        # return pd.DataFrame(records)

        raise NotImplementedError(
            "Real API extraction not implemented. "
            "Use --use-synthetic=true or implement API integration."
        )

    def extract_economic_indicators(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract economic indicators.

        Args:
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            DataFrame with economic indicator data.
        """
        logger.info("Extracting economic indicators...")

        if self.use_synthetic:
            return self._extract_indicators_synthetic(start_date, end_date)
        else:
            return self._extract_indicators_api(start_date, end_date)

    def _extract_indicators_synthetic(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Generate synthetic economic indicator data."""
        np.random.seed(47)

        # Base values and trends for indicators
        indicator_params = {
            "housing_starts": {"base": 1500, "volatility": 50, "trend": 2},
            "building_permits": {"base": 1600, "volatility": 40, "trend": 3},
            "consumer_confidence": {"base": 100, "volatility": 5, "trend": 0.5},
            "home_price_index": {"base": 300, "volatility": 2, "trend": 1.5},
            "mortgage_rate_30y": {"base": 6.5, "volatility": 0.1, "trend": 0.02},
            "unemployment_rate": {"base": 4.0, "volatility": 0.2, "trend": -0.02},
        }

        records = []

        for indicator in self.indicators:
            params = indicator_params.get(
                indicator["id"], {"base": 100, "volatility": 5, "trend": 0}
            )

            # Generate monthly data
            current_date = start_date.replace(day=1)
            value = params["base"]

            while current_date <= end_date:
                # Add trend and noise
                value = (
                    value + params["trend"] + np.random.randn() * params["volatility"]
                )

                # Ensure reasonable bounds
                if indicator["id"] == "unemployment_rate":
                    value = max(2.0, min(10.0, value))
                elif indicator["id"] == "mortgage_rate_30y":
                    value = max(3.0, min(10.0, value))
                elif indicator["id"] in ["housing_starts", "building_permits"]:
                    value = max(800, min(2500, value))

                record = {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "indicator_id": indicator["id"],
                    "indicator_name": indicator["name"],
                    "value": round(value, 2),
                    "unit": indicator["unit"],
                    "frequency": indicator["frequency"],
                }
                records.append(record)

                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(
                        year=current_date.year + 1, month=1
                    )
                else:
                    current_date = current_date.replace(month=current_date.month + 1)

        df = pd.DataFrame(records)
        df["extracted_at"] = datetime.now().isoformat()
        df["data_source"] = "synthetic"

        logger.info(f"Generated {len(df)} economic indicator records (synthetic)")
        return df

    def _extract_indicators_api(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Extract economic indicators from FRED API.

        This is a placeholder showing the API structure.
        """
        if not self.fred:
            raise RuntimeError("FRED API not initialized")

        # Real API integration would go here:
        #
        # from fredapi import Fred
        #
        # # FRED series IDs for our indicators
        # fred_series = {
        #     "housing_starts": "HOUST",
        #     "building_permits": "PERMIT",
        #     "consumer_confidence": "UMCSENT",
        #     "home_price_index": "CSUSHPINSA",
        #     "mortgage_rate_30y": "MORTGAGE30US",
        #     "unemployment_rate": "UNRATE",
        # }
        #
        # records = []
        # for indicator in self.indicators:
        #     series_id = fred_series.get(indicator["id"])
        #     if series_id:
        #         data = self.fred.get_series(
        #             series_id,
        #             observation_start=start_date.strftime("%Y-%m-%d"),
        #             observation_end=end_date.strftime("%Y-%m-%d"),
        #         )
        #         for date, value in data.items():
        #             records.append({
        #                 "date": date.strftime("%Y-%m-%d"),
        #                 "indicator_id": indicator["id"],
        #                 "value": value,
        #             })
        #
        # return pd.DataFrame(records)

        raise NotImplementedError(
            "Real API extraction not implemented. "
            "Use --use-synthetic=true or implement API integration."
        )

    def extract_market_summary(
        self,
        stocks_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Generate monthly market summary.

        Args:
            stocks_df: Daily stock data.

        Returns:
            DataFrame with monthly aggregations.
        """
        logger.info("Generating market summary...")

        df = stocks_df.copy()
        df["month"] = pd.to_datetime(df["date"]).dt.to_period("M")

        # Calculate monthly returns and stats
        summary = (
            df.groupby(["symbol", "name", "sector", "month"])
            .agg(
                {
                    "open": "first",
                    "close": "last",
                    "high": "max",
                    "low": "min",
                    "volume": "sum",
                }
            )
            .reset_index()
        )

        # Calculate monthly return
        summary["monthly_return"] = (
            (summary["close"] - summary["open"]) / summary["open"] * 100
        ).round(2)

        summary["month"] = summary["month"].astype(str)
        summary["extracted_at"] = datetime.now().isoformat()
        summary["data_source"] = stocks_df["data_source"].iloc[0]

        logger.info(f"Generated {len(summary)} monthly summary records")
        return summary

    def run_extraction(
        self,
        start_date: datetime,
        end_date: datetime,
        upload: bool = True,
    ) -> dict[str, Path]:
        """Run full finance extraction pipeline.

        Args:
            start_date: Start of date range.
            end_date: End of date range.
            upload: If True, upload to GCS.

        Returns:
            Dictionary mapping data type to output file paths.
        """
        logger.info("Starting finance extraction...")
        metrics = ExtractionMetrics()

        output_files = {}
        date_suffix = get_date_suffix(start_date, end_date)

        # Extract stock prices
        stocks_df = self.extract_stock_prices(start_date, end_date)
        is_valid, errors = validate_dataframe(
            stocks_df,
            required_columns=["date", "symbol", "close", "volume"],
            logger=logger,
        )
        if is_valid:
            stocks_path = save_to_json(
                stocks_df,
                self.output_dir / f"finance_stocks_{date_suffix}.json",
                logger=logger,
            )
            output_files["stocks"] = stocks_path
            metrics.add_records(len(stocks_df))
            metrics.add_file(stocks_path)

        # Generate market summary
        summary_df = self.extract_market_summary(stocks_df)
        if not summary_df.empty:
            summary_path = save_to_json(
                summary_df,
                self.output_dir / f"finance_summary_{date_suffix}.json",
                logger=logger,
            )
            output_files["summary"] = summary_path
            metrics.add_records(len(summary_df))
            metrics.add_file(summary_path)

        # Extract economic indicators
        indicators_df = self.extract_economic_indicators(start_date, end_date)
        if not indicators_df.empty:
            indicators_path = save_to_json(
                indicators_df,
                self.output_dir / f"finance_indicators_{date_suffix}.json",
                logger=logger,
            )
            output_files["indicators"] = indicators_path
            metrics.add_records(len(indicators_df))
            metrics.add_file(indicators_path)

        # Upload to GCS
        if upload:
            for data_type, path in output_files.items():
                try:
                    upload_to_gcs(path, f"raw/finance/{data_type}", logger=logger)
                    metrics.add_uploaded(1)
                except Exception as e:
                    logger.error(f"Failed to upload {data_type}: {e}")
                    metrics.add_error(str(e))

        metrics.log_summary(logger)
        return output_files


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Extract financial and economic data")
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

    args = parser.parse_args()

    use_synthetic = args.use_synthetic.lower() == "true"
    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)
    output_dir = Path(args.output_dir)

    extractor = FinanceExtractor(
        use_synthetic=use_synthetic,
        output_dir=output_dir,
    )

    extractor.run_extraction(
        start_date=start_date,
        end_date=end_date,
        upload=not args.no_upload,
    )


if __name__ == "__main__":
    main()
