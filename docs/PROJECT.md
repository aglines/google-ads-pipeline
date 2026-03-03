# Google Ads Bid Optimization Platform - Build Guide

## Phase 0: Local Development Environment Setup (Day 1)

### Step 1: Initialize Project Structure
- Create project directory `google-ads-analytics`
- Initialize git repository
- Create directory structure: `dags/`, `dbt_project/`, `scripts/`, `terraform/`, `dashboards/`, `docs/`, `tests/`
- Create files: `README.md`, `.gitignore`, `.env.example`

### Step 2: Set Up Python Environment with uv
- Install uv package manager on Ubuntu
- Create Python virtual environment using uv venv
- Activate the virtual environment
- Initialize uv project with `pyproject.toml`

### Step 2.1: Phase 0 Verification
- Run `tests/verify_phase0.py` to confirm:
  - Required directories exist
  - Git repository initialized
  - Python environment functional (`uv run python --version`)
  - pyproject.toml valid

---

## Phase 1: GCP Infrastructure Foundation (Days 2-3)

**Note: We're skipping Cloud Composer to save costs. All orchestration will use local Airflow.**

### Step 3: GCP Prerequisites
- Follow `docs/GCP-SETUP.md` for project setup and authentication
- Create new GCP project in console (or use existing)
- Enable APIs: BigQuery API, Cloud Storage API
- Authenticate using Application Default Credentials (ADC): `gcloud auth application-default login`
- Populate `.env` with project ID, region, and bucket names (no credential paths)
- Note: NOT enabling Secret Manager or Cloud Composer (cost optimization)

### Step 4: Terraform Infrastructure - Base Configuration
- Create `terraform/providers.tf` with GCP provider configuration
- Create `terraform/variables.tf` for project_id, region, environment variables
- Create `terraform/backend.tf` for state management (local for now)
- Add `.terraform/` to `.gitignore`

### Step 5: Terraform Infrastructure - BigQuery
- Create `terraform/bigquery.tf`
- Define datasets: `raw_google_ads`, `staging_google_ads`, `staging_trends`, `intermediate`, `marts_marketing`, `marts_analytics`
- Configure dataset locations and default table expiration
- Add data retention policies

### Step 6: Terraform Infrastructure - Cloud Storage
- Create `terraform/storage.tf` with buckets for raw data (partitioned by date)
- Add lifecycle rules for old data cleanup
- Configure bucket versioning
- Note: Using .env file for configuration instead of Secret Manager (cost optimization)
- Note: NOT creating Cloud Composer infrastructure (using local Airflow)

### Step 7: Apply Terraform
- Run `terraform init` in terraform directory
- Run `terraform plan` and review changes
- Run `terraform apply` to create infrastructure
- Save outputs (bucket names, dataset IDs) to documentation

### Step 7.1: Phase 1 Verification
- Run `tests/verify_phase1.py` to confirm:
  - All 6 BigQuery datasets exist and are accessible
  - Both GCS buckets exist with correct lifecycle rules
  - ADC authentication works for BigQuery and Storage APIs
  - Terraform state file exists and is valid

---

## Phase 2: Data Extraction Scripts (Days 4-6)

**Note: Build synthetic data generator FIRST. This allows development without real API access and makes the project accessible to anyone.**

### Step 8: Examine Existing Synthetic Data Files
- Review existing Excel and CSV files containing synthetic sample data
- Analyze data structure, columns, relationships, and data types
- Document data schemas and patterns found in existing files
- Evaluate whether existing data is appropriate as template for synthetic generator
- Identify any gaps or modifications needed for our use case
- Document findings in `docs/DATA_REVIEW.md` including:
  - File inventory and descriptions
  - Schema documentation for each file
  - Data quality assessment
  - Recommendations for synthetic data generator design
  - Any data cleaning or transformation needs

### Step 9: Create Synthetic Data Generator
- Create `scripts/generate_synthetic_data.py`
- Add dependencies: `faker`, `numpy`, `pandas`, `python-dateutil`
- Create `scripts/synthetic_data_config.yaml` for configurable data generation parameters
- **Use findings from Step 8 to inform data structure and schema**
- Implement realistic campaign data generation (5-10 campaigns, varying budgets)
- Implement keyword data generation (100-200 keywords per campaign, realistic match types)
- Generate time-series performance data with:
  - Realistic trends (seasonality, day-of-week patterns)
  - Noise and variance (conversion rates 2-8%, CTR 1-5%)
  - Correlations (higher quality score → better conversion rate)
  - Anomalies (occasional cost spikes, conversion drops)
- Generate search trends data (correlated with performance)
- Generate weather data (temperature, conditions)
- Generate finance data (market indicators)
- Output matches exact schema that real APIs would provide
- Add date range parameters (generate last 90 days of data)
- Include logging and progress indicators

### Step 10: Google Ads Extraction Script (API-Ready Interface)
- Create `scripts/extract_google_ads.py`
- Add dependencies: `google-ads`, `pandas`, `google-cloud-storage`, `python-dotenv`
- **Add `--use-synthetic` flag (default: True)**
- **Synthetic mode**: Call `generate_synthetic_data.py` functions to get data
- **Real API mode**: Implement authentication using service account
- Structure code as if calling real Google Ads API (same function signatures, data structures)
- Write function to extract campaign data for date range
- Write function to extract keyword performance data
- Implement pagination for large result sets (even in synthetic mode, to show the pattern)
- Add error handling and retry logic
- Add logging configuration
- Write extracted data to local JSON files first
- Add function to upload JSON to Cloud Storage bucket
- Ensure output format is identical regardless of synthetic vs real mode

### Step 11: Test Synthetic Data Extraction
- Run extraction script with `--use-synthetic` flag (default)
- Verify synthetic data is generated correctly
- Create `scripts/config.py` for configuration management (synthetic vs real mode)
- Test extraction script locally with small date range (last 7 days)
- Verify JSON structure and data quality
- Test Cloud Storage upload functionality
- Validate data has realistic distributions (CTR 1-5%, conversion rate 2-8%)
- Document API credentials in `.env.example` for future real API usage
- Add README section explaining synthetic vs real mode

### Step 12: Additional Data Source Extractors (Synthetic Mode)
- Create `scripts/extract_trends.py` with `--use-synthetic` flag
- Create `scripts/extract_weather.py` with `--use-synthetic` flag
- Create `scripts/extract_finance.py` with `--use-synthetic` flag
- Each script calls appropriate synthetic data generator functions by default
- Structure code as if calling real APIs (authentication stubs, API client patterns)
- Use consistent structure: authenticate (stub) → extract (synthetic/real) → validate → upload
- Add error handling for API rate limits (for future real API use)
- Create `scripts/utils.py` for shared functions (GCS upload, logging, validation)
- Add comments explaining where real API calls would go
- Ensure all scripts produce identical output format in synthetic vs real mode

### Step 13: BigQuery Loading Utility
- Create `scripts/load_to_bigquery.py`
- Write function to load JSON from GCS to BigQuery staging tables
- Implement schema auto-detection
- Add partitioning by date column
- Handle duplicate records (upsert logic)
- Add data validation before loading
- Create logging for successful/failed loads

### Step 13.1: Phase 2 Verification
- Run `tests/verify_phase2.py` to confirm:
  - Synthetic data generator produces valid output files
  - All extraction scripts run without errors in synthetic mode
  - Generated data matches expected schemas
  - Data loads successfully to BigQuery staging tables
  - Row counts and basic statistics are within expected ranges

---

## Phase 3: dbt Project Setup (Days 7-10)

### Step 14: Initialize dbt Project
- Install dbt-core and dbt-bigquery using uv
- Run `dbt init` in dbt_project directory
- Name project `google_ads_analytics`
- Configure project structure

### Step 15: Configure dbt
- Create `profiles.yml` with BigQuery connection settings
- Update `dbt_project.yml` with model configurations
- Set materialization strategies: staging (view), intermediate (ephemeral), marts (table)
- Configure dataset names to match Terraform outputs
- Set up variable definitions

### Step 16: Build Staging Models
- Create `models/staging/sources.yml` defining raw data sources
- Create `models/staging/stg_google_ads__campaigns.sql` with cleaning and type casting
- Create `models/staging/stg_google_ads__keywords.sql` with standardization
- Create `models/staging/stg_google_ads__search_terms.sql` with deduplication
- Create `models/staging/stg_trends__keyword_interest.sql` with normalization
- Add surrogate key generation using dbt_utils

### Step 17: Add Sources and Basic Tests
- Update `sources.yml` with source freshness checks
- Create `models/staging/_staging_schema.yml`
- Add column-level tests: not_null, unique, accepted_values
- Add source data freshness tests
- Document all staging model columns

### Step 18: Test Staging Models
- Run `dbt deps` to install packages
- Run `dbt run --models staging` to materialize models
- Run `dbt test --models staging` to validate data quality
- Fix any test failures
- Review compiled SQL in `target/` directory

### Step 18.1: Phase 3 Verification
- Run `tests/verify_phase3.py` to confirm:
  - dbt project compiles without errors (`dbt compile`)
  - All staging models materialize successfully
  - dbt tests pass for staging models
  - Source freshness checks work

---

## Phase 4: dbt Intermediate & Marts (Days 11-14)

### Step 19: Build Intermediate Models
- Create `models/intermediate/int_keyword_performance_daily.sql` joining ads data with costs
- Create `models/intermediate/int_keyword_trends_enriched.sql` merging with trends
- Create `models/intermediate/int_bid_efficiency_metrics.sql` calculating CPC, CTR, conversion rate, ROAS
- Add window functions for rolling averages
- Materialize as ephemeral or views

### Step 20: Build Dimension Tables
- Create `models/marts/marketing/dim_campaigns.sql` with campaign hierarchy
- Create `models/marts/marketing/dim_keywords.sql` with keyword metadata
- Create `models/marts/marketing/dim_date.sql` using dbt_utils.date_spine
- Create `models/marts/marketing/dim_ad_groups.sql` with ad group structure
- Add slowly changing dimension logic where needed
- Materialize as tables with appropriate partitioning

### Step 21: Build Fact Tables
- Create `models/marts/marketing/fct_keyword_performance.sql` at daily grain
- Create `models/marts/marketing/fct_bid_recommendations.sql` with optimization algorithm
- Implement bid calculation logic (increase/decrease/maintain based on performance)
- Add foreign keys to dimension tables
- Calculate expected impact scores
- Materialize as partitioned tables

### Step 22: Add Comprehensive Tests
- Create `models/marts/marketing/_marketing_schema.yml`
- Add relationship tests between facts and dimensions
- Create custom generic tests in `tests/generic/`
- Add custom singular tests in `tests/singular/` for business rules
- Test for data anomalies (cost spikes, missing data)
- Add dbt_utils tests: recency, expression_is_true, equality

### Step 23: Create Analytics Views
- Create `models/marts/analytics/keyword_roi_summary.sql` with aggregated metrics
- Create `models/marts/analytics/bid_optimization_candidates.sql` filtering actionable keywords
- Add performance segmentation queries
- Create budget pacing calculations
- Materialize as views for real-time querying

### Step 24: Document Models
- Update all schema.yml files with descriptions
- Add column descriptions and business logic explanations
- Run `dbt docs generate` to create documentation
- Review lineage graph
- Test `dbt docs serve` locally

### Step 24.1: Phase 4 Verification
- Run `tests/verify_phase4.py` to confirm:
  - All intermediate models compile and run
  - All dimension and fact tables materialize
  - Relationship tests pass (FK integrity)
  - Analytics views query successfully
  - dbt docs generate without errors

---

## Phase 5: Orchestration with Local Airflow (Days 15-17)

**Note:** Using local Airflow for development and demonstration. All patterns are production-ready and transferable to Cloud Composer, MWAA, or Astronomer.

### Step 25: Set Up Local Airflow
- Install apache-airflow and providers using uv
- Set AIRFLOW_HOME environment variable (e.g., `~/airflow`)
- Initialize Airflow database (SQLite - default, sufficient for demo)
- Create admin user with credentials
- Configure `airflow.cfg` if needed (executor: SequentialExecutor is fine)
- Start Airflow webserver and scheduler locally in separate terminals
- Verify access to UI at localhost:8080
- Create `dags/` folder in Airflow home if not exists

### Step 26: Build Main DAG with Synthetic Data
- Create `dags/google_ads_pipeline.py`
- Define DAG with daily schedule (or manual for demo)
- Create PythonOperator for `generate_synthetic_data` task (runs first)
- Create PythonOperator tasks for each extraction script (with --use-synthetic flag)
- Create PythonOperator for direct BigQuery loading (not GCSToBigQueryOperator)
- Create BashOperator for dbt run commands (ensure correct path to dbt executable)
- Create BashOperator for dbt test commands
- Set task dependencies: generate → extract → load → dbt_run → dbt_test
- Add default_args for retries and timeouts
- Add on_failure_callback for logging errors
- Ensure all Python tasks can find project scripts (add project root to sys.path)

### Step 27: Test DAG Locally
- Copy DAG to Airflow dags folder (or symlink for easier development)
- Refresh Airflow UI and check DAG appears without import errors
- Run `airflow dags test google_ads_analytics_pipeline <date>` from command line
- Trigger DAG manually in Airflow UI
- Monitor each task execution in real-time
- Verify synthetic data generation produces files
- Verify each task executes successfully and in correct order
- Check BigQuery for loaded data in staging tables
- Review task logs for any warnings or errors
- Verify dbt models run and tests pass

### Step 28: Add Data Quality Checks
- Create `dags/operators/` directory for custom operators
- Add BigQueryCheckOperator for row count validation
- Add BigQueryValueCheckOperator for metric thresholds
- Create BranchOperator for conditional logic on anomalies
- Add custom PythonOperator for complex validation
- Implement failure callbacks

### Step 29: Add Logging and Notifications
- Configure structured logging in all Python tasks (JSON format)
- Add success/failure logging callbacks to DAG
- Create summary report function that logs key metrics to console
- Optionally add terminal notifications (using notify-send on Linux)
- Document how to add email/Slack alerts for production (include commented code)
- Add dbt test result parsing and logging
- Create markdown summary of pipeline run in logs

### Step 29.1: Phase 5 Verification
- Run `tests/verify_phase5.py` to confirm:
  - Airflow DAG parses without import errors
  - DAG can be triggered and completes successfully
  - All tasks execute in correct order
  - Data quality checks pass
  - Logs are generated correctly

---

## Phase 6: Testing & Data Quality (Days 18-19)

### Step 30: Set Up Python Testing
- Install pytest and pytest-cov using uv
- Create `tests/unit/` and `tests/integration/` directories
- Create `tests/conftest.py` with fixtures
- Configure pytest.ini for test discovery

### Step 31: Write Unit Tests
- Create `tests/unit/test_extractors.py` testing extraction functions
- Create `tests/unit/test_data_quality.py` testing validation logic
- Create `tests/unit/test_utils.py` testing utility functions
- Mock external API calls
- Test error handling paths
- Aim for >80% code coverage

### Step 32: Add dbt Custom Tests
- Create `dbt_project/tests/singular/` for SQL-based assertions
- Write tests for business rules (e.g., cost should not exceed budget)
- Create `macros/` directory for reusable test logic
- Write generic tests for common patterns
- Test cross-table relationships

### Step 33: Set Up Pre-commit Hooks
- Install pre-commit using uv
- Create `.pre-commit-config.yaml`
- Add hooks: black (Python formatting), ruff (linting), sqlfluff (SQL linting)
- Add trailing whitespace and yaml validation
- Run `pre-commit install`
- Test hooks on sample commits

### Step 33.1: Phase 6 Verification
- Run `tests/verify_phase6.py` to confirm:
  - pytest discovers and runs all tests
  - Code coverage meets threshold (>80%)
  - Pre-commit hooks execute correctly
  - All linters pass on existing code

---

## Phase 7: Visualization (Days 20-21)

### Step 34: Build Looker Studio Dashboard
- Access Looker Studio (formerly Data Studio)
- Create new report connected to BigQuery
- Connect to marts_marketing and marts_analytics datasets
- Create visualizations: scorecard for KPIs, time series for trends, table for bid recommendations
- Add filters for date range, campaign, keyword
- Design clean layout with clear sections
- Export dashboard config to `dashboards/looker_config.json`
- Take screenshots for documentation

### Step 35: OR Build Streamlit App
- Install streamlit and plotly using uv
- Create `dashboards/app.py`
- Add sidebar filters for date range and campaign selection
- Create main page with KPI cards
- Build interactive charts using plotly
- Add bid recommendation explorer with sortable table
- Implement CSV export functionality
- Add what-if scenario calculator
- Test locally with `streamlit run dashboards/app.py`

### Step 35.1: Phase 7 Verification
- Run `tests/verify_phase7.py` to confirm:
  - Dashboard connects to BigQuery successfully
  - Required tables/views exist and return data
  - Streamlit app starts without errors (if using Streamlit)

---

## Phase 8: Documentation & CI/CD (Days 22-24)

### Step 36: Create Comprehensive Documentation
- Create `docs/setup_guide.md` with step-by-step setup instructions
- Create architecture diagram using draw.io or mermaid
- Save diagram as `docs/architecture_diagram.png`
- Create ERD for data model using dbdiagram.io
- Save as `docs/data_model_erd.png`
- Document all API configurations needed
- Create `docs/api_documentation.md` for custom functions

### Step 37: Polish README.md
- Write compelling project overview with business problem
- Add architecture diagram image
- Create quick start guide (prerequisites, setup commands)
- Add example queries and expected outputs
- List technologies used with badges
- Document skills demonstrated
- Add screenshots of dashboard
- Include contact information

### Step 38: Set Up GitHub Actions
- Create `.github/workflows/` directory
- Create `ci.yml` for running tests on pull requests
- Create `dbt-docs.yml` for deploying dbt docs to GitHub Pages
- Add workflow for Python linting (black, ruff)
- Add workflow for SQL linting (sqlfluff)
- Test workflows by pushing to GitHub
- Add status badges to README

### Step 39: Add Docker Support (Optional)
- Create `Dockerfile` for development environment
- Create `docker-compose.yml` for local stack (Airflow, Postgres)
- Document Docker setup in README
- Test container builds successfully
- Add Docker instructions to setup guide

### Step 39.1: Phase 8 Verification
- Run `tests/verify_phase8.py` to confirm:
  - dbt docs generate successfully
  - GitHub Actions workflows have valid syntax
  - Docker builds without errors (if applicable)
  - All documentation files exist and are non-empty

---

## Phase 9: Optional Production Deployment (Days 25-26)

**Note: This phase is OPTIONAL. The project is complete and production-ready with local Airflow. This documents how to deploy to Cloud Composer if desired in the future.**

### Step 40: (OPTIONAL) Deploy to Cloud Composer
- **This step is optional and for documentation purposes**
- Add Cloud Composer to `terraform/composer.tf` if not already present
- Document the deployment process without actually deploying
- Write deployment instructions in `docs/production_deployment_guide.md`
- Include cost estimates (~$300-500/month)
- Document steps: Apply Terraform, upload DAGs, install packages, configure connections
- Add section to README explaining local vs production deployment

### Step 41: Set Up Monitoring
- **Local Monitoring (Required)**:
  - Document Airflow UI usage for monitoring (localhost:8080)
  - Configure email alerts for DAG failures in Airflow
  - Add logging best practices documentation
  - Create monitoring checklist for operators
- **Cloud Monitoring (Optional, for future Composer deployment)**:
  - Create `terraform/monitoring.tf` as documentation only
  - Document Cloud Monitoring dashboard setup
  - Document log-based metrics for errors
  - Document alert creation for DAG failures and cost thresholds
  - Document budget alert setup

### Step 42: Performance Optimization
- Query `INFORMATION_SCHEMA.JOBS_BY_PROJECT` to analyze BigQuery costs
- Add clustering to large fact tables
- Review dbt model materializations (table vs view vs incremental)
- Add incremental models for large tables
- Optimize expensive queries identified in query analysis
- Document optimization decisions

### Step 42.1: Phase 9 Verification
- Run `tests/verify_phase9.py` to confirm:
  - Monitoring documentation exists
  - Performance baseline documented
  - (If deployed) Cloud Composer DAG accessible

---

## Phase 10: Final Polish (Days 27-28)

### Step 43: Code Review and Refactoring
- Remove all hardcoded values, use configuration files
- Ensure consistent naming conventions across all files
- Add Python type hints to all functions
- Add docstrings to all functions and classes
- Refactor duplicate code into shared utilities
- Run linters and fix all issues
- Ensure all SQL follows consistent style

### Step 44: Document Real API Integration Path
- **Note: Synthetic data is the default mode, not a separate demo**
- Create documentation in `docs/real_api_integration.md`
- Document how to switch from synthetic to real API mode
- List required API credentials and setup steps for each API:
  - Google Ads API (developer token, OAuth setup)
  - Google Trends (no auth, but unofficial API)
  - OpenWeather API (API key)
  - Yahoo Finance (no auth typically)
- Add validation that real API mode produces identical schema
- Document testing approach when transitioning to real APIs
- Add troubleshooting section for common API issues

### Step 45: Record Demo Video (Optional)
- Prepare 5-minute demo script
- Screen record: pipeline execution in Airflow UI
- Show data flowing through BigQuery
- Demonstrate dashboard with insights
- Highlight key technical features
- Upload to YouTube or Loom
- Add video link to README

### Step 46: Final Documentation Review
- Test setup guide on fresh Ubuntu VM
- Verify all commands work as documented
- Add troubleshooting section for common issues
- Include sample outputs and screenshots in docs
- Review all code comments for clarity
- Ensure `.env.example` has all required variables
- Add "Next Steps" or "Future Enhancements" section to README
- Proofread all documentation

### Step 46.1: Phase 10 Verification (Final)
- Run `tests/verify_all.py` to confirm:
  - All phase verification tests pass
  - End-to-end pipeline runs successfully
  - All linters and formatters pass
  - Documentation is complete

---

## Deployment Checklist

Before considering the project complete:

- [ ] All tests pass locally
- [ ] Synthetic data generator produces realistic data
- [ ] Extraction scripts work in synthetic mode
- [ ] dbt models documented with descriptions
- [ ] DAG runs successfully end-to-end with synthetic data
- [ ] Dashboard displays meaningful insights
- [ ] README clearly explains synthetic vs real API mode
- [ ] README has clear setup instructions
- [ ] Code is linted and formatted
- [ ] Sensitive data is not committed
- [ ] Terraform state is managed properly
- [ ] Local Airflow monitoring documented
- [ ] Cost optimization is documented
- [ ] Real API integration path is documented
- [ ] GitHub repo is public with good README
- [ ] (Optional) Cloud Composer deployment guide is written

---

## Key Technologies Used

**Core Stack:**
- **Python**: Data extraction and processing
- **uv**: Modern Python package management
- **dbt**: SQL-based transformations
- **BigQuery**: Cloud data warehouse
- **Local Airflow**: Workflow orchestration
- **Terraform**: Infrastructure as code
- **GCP**: Cloud platform (Cloud Storage, BigQuery)
- **pytest**: Unit and integration testing
- **Looker Studio/Streamlit**: Data visualization
- **GitHub Actions**: CI/CD pipeline

**Development Approach:**
- **Synthetic Data Generation**: Enables development without API access
- **API-Ready Architecture**: Easy transition to real APIs
- **Cost-Conscious Design**: Local Airflow instead of Cloud Composer ($0 vs $300-500/month)

**Optional Production Services:**
- **Cloud Composer**: Managed Airflow (documented but not deployed)
- **Cloud Monitoring**: Observability (documented for production use)

---

## Notes for Working with Claude Code

When asking Claude Code to implement each step:

1. **Be specific about file paths** - Always mention the exact file location
2. **Reference dependencies** - Mention when a step depends on previous steps
3. **Request error handling** - Ask for proper exception handling and logging
4. **Ask for documentation** - Request inline comments and docstrings
5. **Specify testing** - Ask to write tests alongside implementation
6. **Request validation** - Ask to add data validation and quality checks
7. **Configuration first** - Ask to use config files instead of hardcoding
8. **Modular code** - Request functions be broken into small, reusable pieces

Example prompt format:
"Please implement Step 8: Create the synthetic data generator at scripts/generate_synthetic_data.py. Generate realistic Google Ads campaign and keyword performance data with time-series trends, seasonality, and realistic distributions. Include configuration via YAML file for parameters like number of campaigns, keywords, date ranges. Use faker for campaign names, numpy for distributions, and pandas for data manipulation."

"Please implement Step 9: Create the Google Ads extraction script at scripts/extract_google_ads.py. Add a --use-synthetic flag (default True) that calls the synthetic data generator. Structure the code as if calling the real Google Ads API with authentication, pagination, and error handling, but have it call synthetic functions instead. Include comments showing where real API calls would go. Ensure output format matches what real API would return."
