# Setup Guide

## Prerequisites

- **Python**: 3.11 or higher
- **uv**: Python package manager ([installation](https://github.com/astral-sh/uv))
- **Docker**: For running Airflow locally
- **Google Cloud SDK**: For BigQuery access
- **GCP Project**: With billing enabled

## Installation Steps

### 1. Clone Repository

```bash
git clone <repository-url>
cd google-ads-pipeline
```

### 2. Install Dependencies

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync project dependencies
uv sync
```

### 3. Configure Google Cloud

```bash
# Install gcloud SDK if needed
# https://cloud.google.com/sdk/docs/install

# Authenticate with ADC
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

### 4. Provision BigQuery Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Apply (creates datasets and tables)
terraform apply
```

Expected resources created:
- Dataset: `raw_google_ads`
- Dataset: `staging_google_ads`
- Dataset: `marts_google_ads`
- Tables in `raw_google_ads`: campaigns, ad_groups, ads, keywords, search_terms

### 5. Configure Accounts (Optional)

Edit `config/accounts.yaml` to add your Google Ads accounts:

```yaml
accounts:
  - customer_id: "1234567890"
    name: "Production Account"
    enabled: true
  - customer_id: "0987654321"
    name: "Test Account"
    enabled: false
```

For synthetic mode, the default config works as-is.

### 6. Start Airflow

#### Option A: Using Docker (Recommended)

```bash
# Build and start services (Airflow + Postgres)
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f airflow
```

Access Airflow UI at `http://localhost:8080`

#### Option B: Local Installation

```bash
# Initialize Airflow database
uv run airflow db migrate

# Start Airflow standalone (auto-creates admin user)
uv run airflow standalone
```

When Airflow starts, it will display:
```
Airflow is ready
Login with username: admin  password: <generated_password>
```

Access Airflow UI at `http://localhost:8080` and use the credentials shown above.

### 7. Run the Pipeline

#### Option A: Via Airflow UI
1. Navigate to `http://localhost:8080`
2. Enable the `google_ads_ingestion` DAG
3. Trigger manually or wait for scheduled run

#### Option B: Via CLI
```bash
# If using Docker
docker compose exec airflow airflow dags trigger google_ads_ingestion

# If using local Airflow
uv run airflow dags trigger google_ads_ingestion
```

### 8. Verify Data in BigQuery

```bash
# Query raw data
bq query --use_legacy_sql=false '
SELECT COUNT(*) as row_count
FROM `YOUR_PROJECT_ID.raw_google_ads.keywords`
'

# Query transformed data
bq query --use_legacy_sql=false '
SELECT *
FROM `YOUR_PROJECT_ID.marts_google_ads.fact_keyword_performance`
LIMIT 10
'
```

### 9. Launch Streamlit Dashboard

```bash
uv run streamlit run dashboards/app.py
```

Access dashboard at `http://localhost:8501`

## Configuration Files

### Environment Variables

Create `.env` file in project root:

```bash
# GCP Configuration
GCP_PROJECT_ID=your-project-id
BQ_DATASET_RAW=raw_google_ads
BQ_DATASET_STAGING=staging_google_ads
BQ_DATASET_MARTS=marts_google_ads

# Google Ads API (optional, for real data)
GOOGLE_ADS_DEVELOPER_TOKEN=your-dev-token
GOOGLE_ADS_CLIENT_ID=your-client-id
GOOGLE_ADS_CLIENT_SECRET=your-client-secret
GOOGLE_ADS_REFRESH_TOKEN=your-refresh-token

# Data Mode
USE_SYNTHETIC_DATA=true
```

### dbt Profile

`~/.dbt/profiles.yml`:

```yaml
google_ads_pipeline:
  outputs:
    dev:
      type: bigquery
      method: oauth
      project: your-project-id
      dataset: marts_google_ads
      threads: 4
      timeout_seconds: 300
      location: US
      priority: interactive

  target: dev
```

## Troubleshooting

### Airflow won't start

```bash
# Check Docker logs
docker compose logs airflow
docker compose logs postgres

# Restart services
docker compose down
docker compose up -d

# Rebuild if needed
docker compose build --no-cache
docker compose up -d
```

### BigQuery authentication errors

```bash
# Re-authenticate
gcloud auth application-default login

# Verify credentials
gcloud auth application-default print-access-token

# Check project is set
gcloud config get-value project
```

### dbt connection issues

```bash
# Test dbt connection
uv run dbt debug

# Common fixes:
# 1. Update ~/.dbt/profiles.yml with correct project ID
# 2. Ensure ADC is configured
# 3. Check BigQuery API is enabled in GCP
```

### Missing Python dependencies

```bash
# Resync environment
uv sync

# Clear cache and reinstall
rm -rf .venv
uv sync
```

## Next Steps

- Read [Architecture Overview](architecture.md)
- Review [Configuration Reference](configuration.md)
- Explore [Development Workflow](development.md)
- Check [Troubleshooting Guide](troubleshooting.md)
