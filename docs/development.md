# Development Workflow

## Quick Start

```bash
# Create branch
git checkout -b feature/my-feature

# Install hooks
uv run pre-commit install

# Make changes, run tests
uv run pytest
uv run mypy scripts/ dags/ dashboards/

# Commit
git commit -m "feat: description"
```

## Adding dbt Model

```bash
# Create file in appropriate directory
touch dbt_project/models/marts/marketing/new_model.sql

# Write SQL with config
# {{ config(materialized='table') }}
# SELECT * FROM {{ ref('stg_source') }}

# Run from project root
./scripts/dbt.sh run --select new_model
./scripts/dbt.sh test --select new_model
```

**Schema/Dataset Configuration:**
- Models in `marts/marketing/` → `marts_marketing` dataset
- Models in `marts/analytics/` → `marts_analytics` dataset
- Models in `staging/` → `staging_google_ads` dataset

This is controlled by `dbt_project.yml` schema config and the custom `generate_schema_name` macro, which prevents dbt's default schema prefixing behavior.

## Adding BigQuery Table

```hcl
# In terraform/bigquery.tf
resource "google_bigquery_table" "new_table" {
  dataset_id = google_bigquery_dataset.raw.dataset_id
  table_id   = "new_table"
  schema = jsonencode([...])
}

# Apply
cd terraform && terraform apply
```

## Testing

```bash
# All tests
uv run pytest

# Coverage
uv run pytest --cov=scripts

# Type check
uv run mypy scripts/ dags/ dashboards/

# Lint
uv run ruff check --fix .
```

## CI/CD Setup

GitHub Actions requires a service account for BigQuery access.

### Create Service Account

```bash
# 1. Create service account
gcloud iam service-accounts create dbt-ci \
  --display-name="dbt CI Service Account"

# 2. Grant BigQuery permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:dbt-ci@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:dbt-ci@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

# 3. Create and download key
gcloud iam service-accounts keys create ~/dbt-ci-key.json \
  --iam-account=dbt-ci@YOUR_PROJECT_ID.iam.gserviceaccount.com

# 4. Add to GitHub secrets
gh secret set GCP_SA_KEY < ~/dbt-ci-key.json
gh secret set GCP_PROJECT_ID --body "YOUR_PROJECT_ID"

# 5. Delete local key
rm ~/dbt-ci-key.json
```

Replace `YOUR_PROJECT_ID` with your GCP project ID.

## DAG Testing

```bash
# Validate
docker compose exec airflow-webserver airflow dags list

# Test run
docker compose exec airflow-webserver airflow dags test google_ads_ingestion 2024-01-01
```

## Commit Convention

```
feat: new feature
fix: bug fix
docs: documentation
test: tests
refactor: code restructure
chore: maintenance
```
