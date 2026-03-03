#!/usr/bin/env python3
"""Load extracted data into BigQuery staging tables.

This script loads JSON data from GCS or local files into BigQuery.
Supports schema auto-detection, date partitioning, and upsert logic.

Usage:
    uv run scripts/load_to_bigquery.py
    uv run scripts/load_to_bigquery.py --source local --input-dir data/extracted
    uv run scripts/load_to_bigquery.py --source gcs --gcs-prefix raw/google_ads
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

sys.path.insert(0, str(Path(__file__).parent))

from config import get_config
from utils import (
    ExtractionMetrics,
    setup_logging,
)

load_dotenv()

logger = setup_logging(__name__)

DEFAULT_INPUT_DIR = Path("data/extracted")

# Table configurations with partition and clustering settings
TABLE_CONFIGS = {
    "campaigns": {
        "partition_field": None,
        "clustering_fields": ["campaign_id"],
    },
    "keywords": {
        "partition_field": "date",
        "clustering_fields": ["campaign", "ad_group"],
    },
    "search_terms": {
        "partition_field": None,
        "clustering_fields": ["campaign", "keyword"],
    },
    "auction_insights": {
        "partition_field": None,
        "clustering_fields": ["month"],
    },
    "trends_interest": {
        "partition_field": "date",
        "clustering_fields": ["keyword"],
    },
    "trends_regional": {
        "partition_field": None,
        "clustering_fields": ["keyword", "region_code"],
    },
    "trends_related": {
        "partition_field": None,
        "clustering_fields": ["keyword"],
    },
    "weather_daily": {
        "partition_field": "date",
        "clustering_fields": ["city", "state"],
    },
    "weather_summary": {
        "partition_field": None,
        "clustering_fields": ["city", "month"],
    },
    "finance_stocks": {
        "partition_field": "date",
        "clustering_fields": ["symbol"],
    },
    "finance_summary": {
        "partition_field": None,
        "clustering_fields": ["symbol", "month"],
    },
    "finance_indicators": {
        "partition_field": "date",
        "clustering_fields": ["indicator_id"],
    },
}


class BigQueryLoader:
    """Load data into BigQuery staging tables."""

    def __init__(
        self,
        project_id: str | None = None,
        dataset_id: str | None = None,
        input_dir: Path | None = None,
    ):
        """Initialize the loader.

        Args:
            project_id: GCP project ID. Uses env var if not specified.
            dataset_id: BigQuery dataset ID. Uses config if not specified.
            input_dir: Directory containing JSON files to load.
        """
        config = get_config()
        self.project_id = project_id or config.gcp.project_id
        self.dataset_id = dataset_id or config.bigquery.dataset_raw
        self.input_dir = input_dir or DEFAULT_INPUT_DIR

        if not self.project_id:
            logger.warning("GCP_PROJECT_ID not set")

        self.client = None
        if self.project_id:
            try:
                self.client = bigquery.Client(project=self.project_id)
                logger.info(f"Connected to BigQuery project: {self.project_id}")
            except Exception as e:
                logger.warning(f"Could not initialize BigQuery client: {e}")

    def _get_table_ref(self, table_name: str) -> str:
        """Get fully qualified table reference."""
        return f"{self.project_id}.{self.dataset_id}.{table_name}"

    def _ensure_dataset_exists(self) -> bool:
        """Ensure the target dataset exists, create if not."""
        if not self.client:
            return False

        dataset_ref = f"{self.project_id}.{self.dataset_id}"
        try:
            self.client.get_dataset(dataset_ref)
            logger.debug(f"Dataset {dataset_ref} exists")
            return True
        except NotFound:
            logger.info(f"Creating dataset {dataset_ref}")
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = os.getenv("GCP_REGION", "us-central1")
            self.client.create_dataset(dataset)
            return True
        except Exception as e:
            logger.error(f"Error checking dataset: {e}")
            return False

    def load_json_file(
        self,
        file_path: Path,
        table_name: str | None = None,
        write_disposition: str = "WRITE_TRUNCATE",
    ) -> dict:
        """Load a JSON file into BigQuery.

        Args:
            file_path: Path to JSON file.
            table_name: Target table name. Inferred from filename if not specified.
            write_disposition: WRITE_TRUNCATE, WRITE_APPEND, or WRITE_EMPTY.

        Returns:
            Dict with load status and row count.
        """
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        # Infer table name from filename if not provided
        if table_name is None:
            # Extract table name: trends_interest_20240101_20240331.json -> trends_interest
            stem = file_path.stem
            parts = stem.rsplit("_", 2)
            if len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit():
                table_name = "_".join(parts[:-2])
            else:
                table_name = stem

        logger.info(f"Loading {file_path.name} -> {table_name}")

        # Load and validate data
        try:
            with open(file_path) as f:
                data = json.load(f)

            if not data:
                return {"success": False, "error": "Empty JSON file", "rows": 0}

            df = pd.DataFrame(data)
        except Exception as e:
            return {"success": False, "error": f"Failed to read JSON: {e}"}

        # Validate required structure
        if df.empty:
            return {"success": False, "error": "DataFrame is empty", "rows": 0}

        # Handle mixed-type columns by converting to string (before date conversion)
        for col in df.columns:
            if df[col].dtype == object:
                # Check if column has mixed types (e.g., int and "--")
                unique_types = df[col].dropna().apply(type).unique()
                if len(unique_types) > 1:
                    df[col] = df[col].astype(str)

        # Convert date columns to proper format (after mixed-type handling)
        date_columns_converted = []
        for col in df.columns:
            if "date" in col.lower() and df[col].dtype == object:
                try:
                    df[col] = pd.to_datetime(df[col])
                    date_columns_converted.append(col)
                except Exception:
                    pass  # Keep as string if conversion fails

        row_count = len(df)

        # If no BigQuery client, just validate and return
        if not self.client:
            logger.info(f"Validated {row_count} rows (BigQuery client not available)")
            return {
                "success": True,
                "rows": row_count,
                "table": table_name,
                "validated_only": True,
            }

        # Ensure dataset exists
        if not self._ensure_dataset_exists():
            return {"success": False, "error": "Could not create dataset"}

        # Configure load job
        table_ref = self._get_table_ref(table_name)
        table_config = TABLE_CONFIGS.get(table_name, {})

        job_config = bigquery.LoadJobConfig(
            write_disposition=write_disposition,
            autodetect=True,
        )

        # Add partitioning if configured and date column was converted
        partition_field = table_config.get("partition_field")
        if partition_field and partition_field in df.columns:
            # Only add partitioning if the column is datetime type
            if pd.api.types.is_datetime64_any_dtype(df[partition_field]):
                job_config.time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.DAY,
                    field=partition_field,
                )

        # Add clustering if configured
        clustering_fields = table_config.get("clustering_fields", [])
        valid_clustering = [f for f in clustering_fields if f in df.columns]
        if valid_clustering:
            job_config.clustering_fields = valid_clustering

        # Execute load
        try:
            job = self.client.load_table_from_dataframe(
                df,
                table_ref,
                job_config=job_config,
            )
            job.result()  # Wait for completion

            logger.info(f"Loaded {row_count} rows to {table_ref}")
            return {
                "success": True,
                "rows": row_count,
                "table": table_ref,
            }

        except Exception as e:
            logger.error(f"Load failed: {e}")
            return {"success": False, "error": str(e)}

    def load_directory(
        self,
        pattern: str = "*.json",
        write_disposition: str = "WRITE_TRUNCATE",
    ) -> dict[str, dict]:
        """Load all matching JSON files from input directory.

        Args:
            pattern: Glob pattern for files to load.
            write_disposition: BigQuery write disposition.

        Returns:
            Dict mapping filename to load result.
        """
        results = {}
        files = sorted(self.input_dir.glob(pattern))

        if not files:
            logger.warning(f"No files matching {pattern} in {self.input_dir}")
            return results

        logger.info(f"Found {len(files)} files to load")

        for file_path in files:
            result = self.load_json_file(file_path, write_disposition=write_disposition)
            results[file_path.name] = result

        return results

    def upsert_table(
        self,
        file_path: Path,
        table_name: str,
        key_columns: list[str],
    ) -> dict:
        """Upsert data using MERGE statement.

        Args:
            file_path: Path to JSON file.
            table_name: Target table name.
            key_columns: Columns to use for matching existing rows.

        Returns:
            Dict with upsert status.
        """
        if not self.client:
            return {"success": False, "error": "BigQuery client not available"}

        # Load to temp table first
        temp_table = f"{table_name}_temp_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        load_result = self.load_json_file(
            file_path,
            table_name=temp_table,
            write_disposition="WRITE_TRUNCATE",
        )

        if not load_result.get("success"):
            return load_result

        # Build MERGE statement
        table_ref = self._get_table_ref(table_name)
        temp_ref = self._get_table_ref(temp_table)

        # Get columns from temp table
        temp_table_obj = self.client.get_table(temp_ref)
        columns = [field.name for field in temp_table_obj.schema]
        non_key_columns = [c for c in columns if c not in key_columns]

        join_condition = " AND ".join(f"T.{col} = S.{col}" for col in key_columns)
        update_clause = ", ".join(f"T.{col} = S.{col}" for col in non_key_columns)
        insert_columns = ", ".join(columns)
        insert_values = ", ".join(f"S.{col}" for col in columns)

        merge_sql = f"""
        MERGE `{table_ref}` T
        USING `{temp_ref}` S
        ON {join_condition}
        WHEN MATCHED THEN
            UPDATE SET {update_clause}
        WHEN NOT MATCHED THEN
            INSERT ({insert_columns})
            VALUES ({insert_values})
        """

        try:
            job = self.client.query(merge_sql)
            job.result()

            # Clean up temp table
            self.client.delete_table(temp_ref)

            logger.info(f"Upserted data to {table_ref}")
            return {"success": True, "rows": load_result["rows"], "table": table_ref}

        except Exception as e:
            logger.error(f"Upsert failed: {e}")
            # Try to clean up temp table
            try:
                self.client.delete_table(temp_ref)
            except Exception:
                pass
            return {"success": False, "error": str(e)}

    def run_load(
        self,
        pattern: str = "*.json",
        write_disposition: str = "WRITE_TRUNCATE",
    ) -> dict:
        """Run full load pipeline.

        Args:
            pattern: Glob pattern for files.
            write_disposition: BigQuery write disposition.

        Returns:
            Summary of load results.
        """
        logger.info("Starting BigQuery load...")
        metrics = ExtractionMetrics()

        results = self.load_directory(pattern, write_disposition)

        # Summarize results
        successful = sum(1 for r in results.values() if r.get("success"))
        failed = len(results) - successful
        total_rows = sum(r.get("rows", 0) for r in results.values() if r.get("success"))

        for name, result in results.items():
            if result.get("success"):
                metrics.add_records(result.get("rows", 0))
            else:
                metrics.add_error(result.get("error", "Unknown error"))

        metrics.log_summary(logger)

        return {
            "files_processed": len(results),
            "successful": successful,
            "failed": failed,
            "total_rows": total_rows,
            "details": results,
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load data into BigQuery staging tables"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="data/extracted",
        help="Directory containing JSON files",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.json",
        help="Glob pattern for files to load",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Target BigQuery dataset",
    )
    parser.add_argument(
        "--write-mode",
        type=str,
        choices=["truncate", "append", "empty"],
        default="truncate",
        help="Write disposition (truncate, append, empty)",
    )

    args = parser.parse_args()

    write_disposition_map = {
        "truncate": "WRITE_TRUNCATE",
        "append": "WRITE_APPEND",
        "empty": "WRITE_EMPTY",
    }

    loader = BigQueryLoader(
        input_dir=Path(args.input_dir),
        dataset_id=args.dataset,
    )

    loader.run_load(
        pattern=args.pattern,
        write_disposition=write_disposition_map[args.write_mode],
    )


if __name__ == "__main__":
    main()
