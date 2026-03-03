#!/usr/bin/env python3
"""Data quality checks for the pipeline.

Verifies that required tables exist and have minimum row counts.
"""

import os
import sys
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()


def main():
    project_id = os.environ.get("GCP_PROJECT_ID")
    if not project_id:
        print("ERROR: GCP_PROJECT_ID not set")
        sys.exit(1)

    client = bigquery.Client(project=project_id)

    checks = [
        ("raw_google_ads.campaigns", 1),
        ("raw_google_ads.keywords", 100),
        ("raw_google_ads.trends_interest", 1),
    ]

    failed = False
    for table, min_rows in checks:
        try:
            query = f"SELECT COUNT(*) as cnt FROM `{project_id}.{table}`"
            result = list(client.query(query).result())[0]
            count = result.cnt
            print(f"{table}: {count} rows")
            if count < min_rows:
                print(f"  FAIL: Expected >= {min_rows} rows")
                failed = True
        except Exception as e:
            print(f"{table}: ERROR - {e}")
            failed = True

    if failed:
        print("\nData quality checks FAILED")
        sys.exit(1)
    else:
        print("\nAll data quality checks passed!")


if __name__ == "__main__":
    main()
