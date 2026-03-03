"""
Google Ads Analytics Pipeline DAG

This DAG orchestrates the complete data pipeline:
1. Generate synthetic data (or extract from real APIs)
2. Load data to BigQuery staging
3. Run data quality checks
4. Run dbt transformations
5. Run dbt tests
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.python import PythonOperator

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DBT_DIR = PROJECT_ROOT / "dbt_project"

# Environment setup for all commands
ENV_SETUP = f"set -a && source {PROJECT_ROOT}/.env && set +a"
UV_RUN = "uv run"

logger = logging.getLogger(__name__)


def on_failure_callback(context):
    """Log failure details when a task fails."""
    task_instance = context["task_instance"]
    dag_id = context["dag"].dag_id
    task_id = task_instance.task_id
    execution_date = context["execution_date"]
    exception = context.get("exception", "Unknown error")

    logger.error(
        json.dumps(
            {
                "event": "task_failure",
                "dag_id": dag_id,
                "task_id": task_id,
                "execution_date": str(execution_date),
                "error": str(exception),
            }
        )
    )


def on_success_callback(context):
    """Log success details when a task completes."""
    task_instance = context["task_instance"]
    dag_id = context["dag"].dag_id
    task_id = task_instance.task_id
    execution_date = context["execution_date"]
    duration = task_instance.duration

    logger.info(
        json.dumps(
            {
                "event": "task_success",
                "dag_id": dag_id,
                "task_id": task_id,
                "execution_date": str(execution_date),
                "duration_seconds": duration,
            }
        )
    )


def generate_summary(**context):
    """Generate pipeline run summary."""
    dag_run = context["dag_run"]
    task_instance = context["task_instance"]

    summary = {
        "dag_id": dag_run.dag_id,
        "run_id": dag_run.run_id,
        "logical_date": str(dag_run.logical_date),
        "state": str(dag_run.state),
        "current_task": task_instance.task_id,
    }

    logger.info(f"Pipeline Summary:\n{json.dumps(summary, indent=2)}")
    print(f"Pipeline completed: {dag_run.dag_id} - {dag_run.run_id}")
    return summary


# Default arguments for the DAG
default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": on_failure_callback,
    "on_success_callback": on_success_callback,
}

with DAG(
    dag_id="google_ads_analytics_pipeline",
    default_args=default_args,
    description="Google Ads bid optimization data pipeline",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["google-ads", "dbt", "analytics"],
) as dag:

    # Task 1: Generate synthetic data
    generate_data = BashOperator(
        task_id="generate_synthetic_data",
        bash_command=f"cd {PROJECT_ROOT} && {UV_RUN} python {SCRIPTS_DIR}/generate_synthetic_data.py",
    )

    # Task 2: Extract Google Ads data
    extract_ads = BashOperator(
        task_id="extract_google_ads",
        bash_command=f"cd {PROJECT_ROOT} && {UV_RUN} python {SCRIPTS_DIR}/extract_google_ads.py --use-synthetic true",
    )

    # Task 3: Extract trends data
    extract_trends = BashOperator(
        task_id="extract_trends",
        bash_command=f"cd {PROJECT_ROOT} && {UV_RUN} python {SCRIPTS_DIR}/extract_trends.py --use-synthetic true",
    )

    # Task 4: Load to BigQuery
    load_data = BashOperator(
        task_id="load_to_bigquery",
        bash_command=f"{ENV_SETUP} && cd {PROJECT_ROOT} && {UV_RUN} python {SCRIPTS_DIR}/load_to_bigquery.py",
    )

    # Task 5: Data quality check - verify row counts
    check_data_quality = BashOperator(
        task_id="check_data_quality",
        bash_command=f"cd {PROJECT_ROOT} && {UV_RUN} python {SCRIPTS_DIR}/check_data_quality.py",
    )

    # Task 6: Run dbt models
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {PROJECT_ROOT} && ./scripts/dbt.sh run",
    )

    # Task 7: Run dbt tests
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {PROJECT_ROOT} && ./scripts/dbt.sh test",
    )

    # Task 8: Generate summary
    summary = PythonOperator(
        task_id="generate_summary",
        python_callable=generate_summary,
        trigger_rule="all_done",  # Run even if upstream fails
    )

    # Task dependencies
    # generate -> extract (parallel) -> load -> check -> dbt_run -> dbt_test -> summary
    generate_data >> [extract_ads, extract_trends]
    [extract_ads, extract_trends] >> load_data
    load_data >> check_data_quality >> dbt_run >> dbt_test >> summary
