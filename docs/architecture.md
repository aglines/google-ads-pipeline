# Architecture Overview

## System Components

```
┌─────────────────┐
│  Google Ads API │
│  (or Synthetic) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Apache Airflow │ ← Orchestration
│   (Local)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   BigQuery      │ ← Data Warehouse
│   - Raw Layer   │
│   - Staging     │
│   - Marts       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   dbt Core      │ ← Transformation
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Streamlit     │ ← Visualization
│   Dashboard     │
└─────────────────┘
```

## Data Flow

### 1. Ingestion (Airflow DAG)
- **Task**: `extract_google_ads_data`
- **Frequency**: Daily at 2 AM UTC
- **Source**: Google Ads API or synthetic data generator
- **Destination**: BigQuery `raw_google_ads` dataset
- **Tables**:
  - `campaigns`
  - `ad_groups`
  - `ads`
  - `keywords`
  - `search_terms`

### 2. Data Validation
- **Task**: `check_data_quality`
- **Script**: `scripts/check_data_quality.py`
- **Purpose**: Verify data loaded successfully before transformation
- **Checks**: Table existence, minimum row counts
- **Behavior**: Fails pipeline early if data is missing or incomplete

### 3. Transformation (dbt)
- **Task**: `transform_with_dbt`
- **Command**: `./scripts/dbt.sh run` (from project root)
- **Layers**:
  - **Staging**: Clean and type-cast raw data → `staging_google_ads` dataset
  - **Intermediate**: Business logic (ephemeral, not persisted)
  - **Marts**: Final analytics-ready models
    - `marts/marketing/` → `marts_marketing` dataset (dimensions and keyword facts)
    - `marts/analytics/` → `marts_analytics` dataset (aggregations and recommendations)

**Schema Configuration:**
This project uses a custom `generate_schema_name` macro to control BigQuery dataset naming. Without this macro, dbt would prefix custom schemas with the target schema (e.g., `staging_google_ads_marts_analytics`). The macro ensures clean dataset names that match environment variables and documentation.

### 4. Visualization (Streamlit)
- **Dashboard**: `dashboards/app.py`
- **Features**:
  - KPI summary cards
  - Performance trends
  - Bid optimization recommendations
  - What-if scenario calculator

## Infrastructure

### Local Development
- **Airflow**: Docker Compose (standalone mode)
- **Python**: uv package manager
- **dbt**: Runs via `./scripts/dbt.sh` wrapper (handles env setup and paths)
- **BigQuery**: GCP project (ADC authentication)

### Cost Optimization
- **Airflow**: Local deployment ($0 vs Cloud Composer ~$300-500/month)
- **Authentication**: ADC (no service account keys to manage)
- **Storage**: BigQuery on-demand pricing (~$5/TB scan)
- **Compute**: Local execution, minimal cloud compute

## Security

### Authentication
- **Google Cloud**: Application Default Credentials (ADC)
- **No service account keys**: Uses `gcloud auth application-default login`
- **Permissions required**:
  - BigQuery Data Editor
  - BigQuery Job User
  - Google Ads API access (if using real data)

### Data Privacy
- **Synthetic mode**: No real customer data by default
- **Real mode**: PII handled per Google Ads policies
- **Access control**: BigQuery IAM roles

## Scalability

### Current Scale
- **Data volume**: ~10k keywords/day (synthetic)
- **Processing time**: ~5-10 minutes per DAG run
- **Storage**: ~1 GB/year at current volume

### Growth Path
1. **More accounts**: Add accounts to `config/accounts.yaml`
2. **Higher frequency**: Change schedule from daily to hourly
3. **More metrics**: Extend schema in `terraform/bigquery.tf`
4. **Cloud Airflow**: Migrate to Cloud Composer when needed
5. **Streaming**: Switch to Pub/Sub + Dataflow for real-time

## Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Orchestration | Apache Airflow | 2.8+ | DAG scheduling |
| Data Warehouse | Google BigQuery | N/A | Storage & querying |
| Transformation | dbt Core | 1.7+ | SQL-based transforms |
| Visualization | Streamlit | 1.31+ | Analytics dashboard |
| Language | Python | 3.11+ | DAGs, data generation |
| Package Manager | uv | 0.1+ | Dependency management |
| IaC | Terraform | 1.7+ | BigQuery provisioning |
| Testing | pytest | 8.0+ | Unit & integration tests |
| Code Quality | pre-commit | 3.6+ | Linting & formatting |

## Deployment Models

### Option 1: Local Development (Current)
- Airflow runs in Docker locally
- dbt runs via `uv run dbt`
- Streamlit runs locally
- BigQuery in GCP

**Pros**: Zero compute cost, full control
**Cons**: Requires local machine running

### Option 2: Cloud Hybrid
- Airflow on Cloud Composer
- dbt runs in Composer environment
- Streamlit on Cloud Run
- BigQuery in GCP

**Pros**: Fully managed, auto-scaling
**Cons**: ~$300-500/month Composer cost

### Option 3: Fully Serverless
- Cloud Functions for ingestion
- Cloud Scheduler for triggers
- dbt Cloud for transforms
- Looker/Data Studio for viz

**Pros**: Pay-per-use, minimal management
**Cons**: Higher per-run cost at scale
