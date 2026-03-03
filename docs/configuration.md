# Configuration Reference

## Environment Variables

### Required

| Variable | Description | Example | Default |
|----------|-------------|---------|---------|
| `GCP_PROJECT_ID` | Google Cloud project ID | `my-gcp-project` | None |

### Optional

| Variable | Description | Example | Default |
|----------|-------------|---------|---------|
| `BQ_DATASET_RAW` | BigQuery dataset for raw data | `raw_google_ads` | `raw_google_ads` |
| `BQ_DATASET_STAGING` | BigQuery dataset for staging | `staging_google_ads` | `staging_google_ads` |
| `BQ_DATASET_MARTS` | BigQuery dataset for marts | `marts_google_ads` | `marts_google_ads` |
| `USE_SYNTHETIC_DATA` | Use synthetic data generator | `true` or `false` | `true` |
| `SYNTHETIC_CAMPAIGNS` | Number of synthetic campaigns | `5` | `3` |
| `SYNTHETIC_ADGROUPS_PER_CAMPAIGN` | Ad groups per campaign | `10` | `5` |
| `SYNTHETIC_KEYWORDS_PER_ADGROUP` | Keywords per ad group | `50` | `20` |

### Google Ads API (Real Data Mode)

Required only if `USE_SYNTHETIC_DATA=false`:

| Variable | Description | How to Obtain |
|----------|-------------|---------------|
| `GOOGLE_ADS_DEVELOPER_TOKEN` | API developer token | [Google Ads API Center](https://ads.google.com/aw/apicenter) |
| `GOOGLE_ADS_CLIENT_ID` | OAuth2 client ID | [GCP Console](https://console.cloud.google.com/apis/credentials) |
| `GOOGLE_ADS_CLIENT_SECRET` | OAuth2 client secret | Same as above |
| `GOOGLE_ADS_REFRESH_TOKEN` | OAuth2 refresh token | Use `generate_refresh_token.py` script |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | Manager account ID (if applicable) | Google Ads UI |

## Accounts Configuration

**File**: `config/accounts.yaml`

```yaml
accounts:
  - customer_id: "1234567890"
    name: "Production Account"
    enabled: true

  - customer_id: "0987654321"
    name: "Test Account"
    enabled: false

  - customer_id: "1122334455"
    name: "Client XYZ"
    enabled: true
```

### Fields

- **customer_id**: Google Ads customer ID (10 digits, no dashes)
- **name**: Human-readable account name
- **enabled**: Whether to include in data pulls

## Airflow Configuration

**File**: `dags/google_ads_pipeline.py`

### DAG Parameters

```python
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'google_ads_ingestion',
    default_args=default_args,
    description='Daily Google Ads data ingestion',
    schedule_interval='0 2 * * *',  # 2 AM UTC daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['google-ads', 'ingestion'],
)
```

### Customization Options

**Change schedule**:
```python
schedule_interval='0 */6 * * *'  # Every 6 hours
schedule_interval='0 2 * * 1'     # Weekly on Monday
schedule_interval=None            # Manual only
```

**Enable email alerts**:
```python
default_args = {
    'email_on_failure': True,
    'email': ['team@example.com'],
    # ... other args
}
```

**Adjust retries**:
```python
default_args = {
    'retries': 5,
    'retry_delay': timedelta(minutes=10),
    'retry_exponential_backoff': True,
    # ... other args
}
```

## dbt Configuration

**File**: `dbt_project/dbt_project.yml`

```yaml
name: 'google_ads_analytics'
version: '1.0.0'
config-version: 2

profile: 'google_ads_analytics'

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

target-path: "target"
clean-targets:
  - "target"
  - "dbt_packages"

models:
  google_ads_analytics:
    staging:
      +materialized: view
      +schema: staging
    intermediate:
      +materialized: view
      +schema: staging
    marts:
      +materialized: table
      +schema: marts
```

### Model Materialization

**Change all marts to incremental**:
```yaml
models:
  google_ads_analytics:
    marts:
      +materialized: incremental
      +unique_key: id
      +on_schema_change: fail
```

**Enable partitioning**:
```yaml
models:
  google_ads_analytics:
    marts:
      fact_keyword_performance:
        +partition_by:
          field: date
          data_type: date
```

## BigQuery Schema

**File**: `terraform/bigquery.tf`

BigQuery table schemas are defined in Terraform. To add custom fields, modify the table definitions in the Terraform configuration.

### Updating Synthetic Data Generator

**File**: `scripts/generate_synthetic_data.py`

```python
def generate_keywords(ad_group_id, campaign_id, num_keywords=20):
    keywords = []
    for i in range(num_keywords):
        keyword = {
            # ... existing fields ...
            "custom_label": random.choice(["Label A", "Label B", "Label C"]),
        }
        keywords.append(keyword)
    return keywords
```

## Streamlit Dashboard

**File**: `dashboards/app.py`

### Page Configuration

```python
st.set_page_config(
    page_title="Google Ads Analytics",
    page_icon="📊",
    layout="wide",          # or "centered"
    initial_sidebar_state="expanded"
)
```

### BigQuery Configuration

```python
@st.cache_resource
def get_bigquery_client():
    return bigquery.Client(project=os.getenv("GCP_PROJECT_ID", "your-project"))
```

## Pre-commit Hooks

**File**: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

### Customizing Ruff

**File**: `pyproject.toml`

```toml
[tool.ruff]
line-length = 100  # Change line length
select = ["E", "F", "I", "N"]  # Select rules
ignore = ["E501"]  # Ignore specific rules

[tool.ruff.format]
quote-style = "double"  # or "single"
```

## Terraform Variables

**File**: `terraform/variables.tf`

```hcl
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "US"
}

variable "dataset_raw" {
  description = "Raw dataset name"
  type        = string
  default     = "raw_google_ads"
}
```

**File**: `terraform/terraform.tfvars`

```hcl
project_id  = "your-project-id"
region      = "US"
dataset_raw = "raw_google_ads"
```

## Docker Compose

**File**: `docker-compose.yaml`

### Resource Limits

```yaml
services:
  airflow-webserver:
    # ... other config ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Port Mappings

```yaml
services:
  airflow-webserver:
    ports:
      - "8080:8080"  # Change to "9090:8080" to use port 9090
```

## Logging Configuration

**Airflow** logs to: `./logs/`

**dbt** logs to: `./dbt_logs/`

**Streamlit** logs to: stdout (captured by Docker)

### Adjusting Log Levels

**Airflow** (`docker-compose.yaml`):
```yaml
environment:
  AIRFLOW__LOGGING__LOGGING_LEVEL: INFO  # or DEBUG, WARNING, ERROR
```

**dbt** (`dbt_project.yml`):
```yaml
flags:
  log_level: INFO  # or DEBUG, WARNING, ERROR
```
