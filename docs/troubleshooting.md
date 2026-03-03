# Troubleshooting Guide

## Airflow Issues

**DAG not appearing**:
```bash
# Standalone mode
AIRFLOW_HOME=/path/to/project uv run airflow dags list-import-errors

# Docker mode
docker compose exec airflow-webserver airflow dags list-import-errors
```

**Module not found**:
```bash
uv add <package>
# Restart Airflow after adding dependencies
```

**Tasks stuck**:
```bash
# Clear failed tasks
uv run airflow tasks clear google_ads_analytics_pipeline -t task_name

# Check logs in Airflow UI or:
tail -f ~/airflow/logs/dag_id=google_ads_analytics_pipeline/...
```

**Running Airflow standalone** (recommended for development):
```bash
AIRFLOW_HOME=/home/ad/code/google-ads-pipeline uv run airflow standalone
# Access UI at http://localhost:8080
```

## BigQuery Issues

**Auth errors**:
```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

**Permission denied**:
```bash
gcloud projects add-iam-policy-binding PROJECT \
  --member="user:email" \
  --role="roles/bigquery.dataEditor"
```

**Table not found**:
```bash
cd terraform && terraform apply
```

## dbt Issues

**Connection failed**:
```bash
./scripts/dbt.sh debug
# Check dbt_project/profiles.yml (not ~/.dbt/)
```

**Model not found**:
```bash
rm -rf dbt_project/target/
./scripts/dbt.sh clean
```

**Test failures**:
```bash
./scripts/dbt.sh test --select model_name
# Check data in BigQuery
```

**Tables in wrong dataset** (e.g., `staging_google_ads_marts_analytics`):
```bash
# Verify custom schema macro exists
cat dbt_project/macros/generate_schema_name.sql
# Re-run with full refresh
./scripts/dbt.sh run --full-refresh
```

## Streamlit Issues

**Won't start**:
```bash
uv add streamlit
uv run streamlit run dashboards/app.py --logger.level=debug
```

**No data**:
```bash
# Verify mart tables exist
bq ls PROJECT_ID:marts_marketing
bq ls PROJECT_ID:marts_analytics

# Check row counts
uv run python scripts/check_data_quality.py
```

**Slider error** (min_value equals max_value):
This happens when all values in a column are identical. The dashboard handles this gracefully.

## Docker Issues

**Container won't start**:
```bash
docker compose logs
docker compose down -v
docker compose up -d
```

**Port in use**:
```bash
lsof -i :8080
kill -9 <PID>
# Or change port in docker-compose.yaml
```

## Diagnostic Collection

```bash
mkdir diagnostics
docker compose logs > diagnostics/docker.log
uv run dbt debug > diagnostics/dbt.log
gcloud config list > diagnostics/gcloud.log
tar -czf diag-$(date +%Y%m%d).tar.gz diagnostics/
```
