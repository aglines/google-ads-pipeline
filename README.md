# Google Ads Performance Pipeline

Production-ready data pipeline for analyzing Google Ads performance with dbt, BigQuery, and Airflow. Features synthetic data generation, star schema modeling, and ML-driven bid recommendations.

## Features

- **Synthetic Data Generation**: Test pipeline without Google Ads API access
- **Star Schema Modeling**: Dimensional warehouse with fact and dimension tables
- **dbt Transformations**: Modular, tested SQL transformations
- **Airflow Orchestration**: Local Airflow with Docker support
- **BigQuery Analytics**: Scalable data warehouse on GCP
- **Streamlit Dashboard**: Interactive bid optimization visualizations
- **CI/CD**: GitHub Actions for automated testing and validation

## How It Works

The pipeline processes Google Ads data through four stages:

### 1. Data Generation & Extraction

**Purpose:** Create or extract advertising performance data

- **Synthetic Mode** (default): Generates realistic test data without API access
  - Creates campaigns, ad groups, keywords with performance metrics
  - Includes seasonality, day-of-week patterns, quality scores
  - Command: `uv run python scripts/generate_synthetic_data.py`

- **Real Mode** (production): Extracts from Google Ads API
  - Pulls campaign performance, keyword metrics, search terms
  - Command: `uv run python scripts/extract_google_ads.py`

**Output:** JSON files in `data/extracted/` (campaigns, keywords, search terms)

### 2. Data Loading

**Purpose:** Load extracted data into BigQuery raw tables

- Reads JSON files from local directory or GCS
- Creates/updates tables in `raw_google_ads` dataset
- Handles schema detection and partitioning
- Command: `uv run python scripts/load_to_bigquery.py --source local --input-dir data/extracted`

**Output:** Raw tables in BigQuery (`campaigns`, `keywords`, `search_terms`, etc.)

### 3. Data Validation

**Purpose:** Verify data loaded successfully before transformation

- Checks that required tables exist
- Validates minimum row counts
- Fails fast if data is missing or incomplete
- Command: `uv run python scripts/check_data_quality.py`

**Output:** Pass/fail status with row counts for each table

### 4. Data Transformation (dbt)

**Purpose:** Transform raw data into analytics-ready models

**Three-layer architecture:**

- **Staging Layer** (`staging_google_ads` dataset)
  - Cleans and type-casts raw data
  - Standardizes column names
  - Views for lightweight processing

- **Intermediate Layer** (ephemeral)
  - Business logic calculations
  - Quality score adjustments
  - Not persisted (CTEs only)

- **Marts Layer**
  - `marts_marketing`: Dimension tables (campaigns, keywords, dates) and fact tables (daily performance)
  - `marts_analytics`: Aggregated summaries, ROI analysis, bid recommendations

**Command:** `./scripts/dbt.sh run`

**Output:** Analytics tables ready for dashboard queries

### 5. Visualization (Streamlit)

**Purpose:** Interactive dashboard for bid optimization

- **Overview Tab**: KPIs, ROAS trends, cost vs revenue
- **Bid Recommendations Tab**: Actionable bid changes with confidence scores
- **Top Keywords Tab**: Performance rankings
- **What-If Calculator Tab**: Simulate bid change impacts

**Command:** `uv run streamlit run dashboards/app.py`

**Output:** Web dashboard at `http://localhost:8501`

### Optional: Orchestration (Airflow)

**Purpose:** Automate the entire pipeline on a schedule

- Runs all four stages in sequence
- Handles retries and error notifications
- Configurable schedule (default: daily at 2 AM)

**Command:** `uv run airflow standalone` (then enable DAG in UI)

## Quick Start

### Prerequisites

- Python 3.12+
- Google Cloud SDK with ADC configured
- Docker (optional, recommended)
- GCP project with BigQuery enabled

### Installation

```bash
# Clone repository
git clone <repo-url>
cd google-ads-pipeline

# Install dependencies
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# Authenticate with GCP
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# Provision BigQuery infrastructure
cd terraform && terraform init && terraform apply
cd ..
```

### Run Pipeline Manually

Execute each stage in sequence:

**Step 1: Generate Data**
```bash
uv run python scripts/generate_synthetic_data.py
# Creates CSV files in data/synthetic/ (campaigns, keywords, search terms)
```

**Step 2: Extract to JSON**
```bash
uv run python scripts/extract_google_ads.py
# Converts CSVs to JSON format in data/extracted/
```

**Step 3: Load to BigQuery**
```bash
uv run python scripts/load_to_bigquery.py --source local --input-dir data/extracted
# Creates tables in raw_google_ads dataset
```

**Step 4: Validate Data Quality**
```bash
uv run python scripts/check_data_quality.py
# Verifies required tables exist with minimum row counts
```

**Step 5: Run dbt Transformations**
```bash
./scripts/dbt.sh run
./scripts/dbt.sh test
# Creates analytics tables in marts_marketing and marts_analytics datasets
```

**Step 5: Launch Dashboard**
```bash
uv run streamlit run dashboards/app.py
# Opens dashboard at http://localhost:8501
```

### Run with Airflow (Automated)

For scheduled execution:

```bash
# Option A: Standalone (development)
uv run airflow standalone
# Access UI at http://localhost:8080
# Enable and trigger the google_ads_pipeline DAG

# Option B: Docker (production-like)
./scripts/docker-up.sh
# Access UI at http://localhost:8080
```

## Documentation

- [Architecture Overview](docs/architecture.md)
- [Setup Guide](docs/setup.md)
- [Configuration Reference](docs/configuration.md)
- [Development Workflow](docs/development.md)
- [Troubleshooting](docs/troubleshooting.md)

## Project Structure

```
google-ads-pipeline/
├── dags/                  # Airflow DAG definitions
├── dbt_project/           # dbt transformation models
├── scripts/               # Data generation and utilities
├── dashboards/            # Streamlit visualization
├── terraform/             # Infrastructure as code
├── tests/                 # Automated test suites
└── docs/                  # Comprehensive documentation
```

## Development

```bash
# Run tests
uv run pytest

# Format code
uv run black .

# Lint
uv run ruff check .

# Type check
uv run mypy .
```

## Methodology

Pipeline built following PROJECT.md specification with Claude-assisted development.
