# Phase Verification Tests

This document details the verification tests for the project. All phase verification tests are consolidated in a single file for simpler maintenance.

## Test Structure

```
tests/
├── verify_all.py       # All phase verification tests (consolidated)
├── conftest.py         # Shared fixtures
├── unit/               # Unit tests
│   ├── test_utils.py
│   ├── test_extractors.py
│   └── test_data_quality.py
└── integration/        # Integration tests
```

---

## Running Tests

All phase verifications:
```bash
uv run pytest tests/verify_all.py -v
```

Specific phase (by class name pattern):
```bash
uv run pytest tests/verify_all.py -k "Phase0" -v
uv run pytest tests/verify_all.py -k "Phase3" -v
```

Unit tests only:
```bash
uv run pytest tests/unit/ -v
```

All tests with coverage:
```bash
uv run pytest tests/ --cov=scripts --cov-report=term-missing
```

---

## Phase Overview

### Phase 0: Local Development Environment
- Directory structure verification
- Git repository initialization
- Python environment (uv) functionality
- pyproject.toml validity

### Phase 1: GCP Infrastructure
- BigQuery datasets exist and accessible
- GCS buckets exist and accessible
- ADC authentication works
- Terraform state valid

**Dependencies**: Requires ADC configured (`gcloud auth application-default login`)

### Phase 2: Data Extraction
- Synthetic data generator runs
- All extraction scripts exist (google_ads, trends, weather, finance)
- Config module exists
- BigQuery loader exists

### Phase 3: dbt Staging
- dbt project structure valid
- Staging models exist and compile
- dbt run/test passes for staging

### Phase 4: dbt Intermediate & Marts
- Intermediate models exist
- Dimension and fact tables exist
- Analytics views exist
- dbt docs generate works

### Phase 5: Airflow Orchestration
- DAG file exists and parses
- Airflow installed
- DAG has required tasks and logging

### Phase 6: Testing & Data Quality
- Test directory structure (unit/, integration/)
- Unit tests exist and pass
- Pre-commit hooks configured
- dbt tests structure exists

### Phase 7: Visualization
- Dashboard directory exists
- Streamlit app valid (if used)
- Marts tables queryable

### Phase 8: Documentation & CI/CD
- Key documentation exists
- README complete
- GitHub Actions workflows valid
- Docker files exist (optional)

### Phase 9: Production (Optional)
- Monitoring documented
- Performance optimization documented
- Incremental models exist

### Phase 10: Final Polish
- No hardcoded values
- Linters pass
- Formatters pass
- All key docs exist
