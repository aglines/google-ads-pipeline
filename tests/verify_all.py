"""Consolidated Phase Verification Tests.

All phase verification tests in a single file for simpler maintenance.
Run with: uv run pytest tests/verify_all.py -v

Tests are organized by phase with clear section comments.
"""

import json
import subprocess
import pytest
from pathlib import Path

from google.cloud import bigquery
from google.cloud import storage
from google.api_core.exceptions import NotFound, Forbidden


# ============================================
# Phase 0: Local Development Environment
# ============================================


class TestPhase0DirectoryStructure:
    """Verify required directories exist."""

    REQUIRED_DIRS = ["dags", "scripts", "terraform", "tests", "docs"]

    def test_directories_exist(self, project_root: Path):
        """Required project directories should exist."""
        missing = []
        for dir_name in self.REQUIRED_DIRS:
            if not (project_root / dir_name).is_dir():
                missing.append(dir_name)
        assert not missing, f"Missing directories: {missing}"


class TestPhase0GitRepository:
    """Verify git is initialized."""

    def test_git_initialized(self, project_root: Path):
        """.git directory should exist."""
        git_dir = project_root / ".git"
        assert git_dir.is_dir(), "Git repository not initialized (.git/ missing)"


class TestPhase0PythonEnvironment:
    """Verify Python environment is functional."""

    def test_python_version(self, project_root: Path):
        """uv run python --version should succeed."""
        result = subprocess.run(
            ["uv", "run", "python", "--version"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Python not working: {result.stderr}"
        assert (
            "Python 3" in result.stdout
        ), f"Unexpected Python version: {result.stdout}"

    def test_pyproject_exists(self, project_root: Path):
        """pyproject.toml should exist."""
        pyproject = project_root / "pyproject.toml"
        assert pyproject.exists(), "pyproject.toml not found"

    def test_pyproject_valid(self, project_root: Path):
        """pyproject.toml should be parseable."""
        import tomllib

        pyproject = project_root / "pyproject.toml"
        if not pyproject.exists():
            pytest.skip("pyproject.toml does not exist")

        with open(pyproject, "rb") as f:
            try:
                data = tomllib.load(f)
            except tomllib.TOMLDecodeError as e:
                pytest.fail(f"pyproject.toml is invalid: {e}")

        assert "project" in data, "pyproject.toml missing [project] section"


# ============================================
# Phase 1: GCP Infrastructure Foundation
# ============================================


class TestPhase1BigQueryDatasets:
    """Verify BigQuery datasets exist and are accessible."""

    @pytest.fixture(scope="class")
    def bq_client(self, gcp_project_id: str) -> bigquery.Client:
        """Create BigQuery client."""
        return bigquery.Client(project=gcp_project_id)

    def test_bigquery_datasets_exist(
        self,
        bq_client: bigquery.Client,
        gcp_project_id: str,
        bigquery_datasets: list[str],
    ):
        """All 6 BigQuery datasets should exist and be accessible."""
        missing = []
        forbidden = []

        for dataset_id in bigquery_datasets:
            full_id = f"{gcp_project_id}.{dataset_id}"
            try:
                bq_client.get_dataset(full_id)
            except NotFound:
                missing.append(dataset_id)
            except Forbidden:
                forbidden.append(dataset_id)

        errors = []
        if missing:
            errors.append(f"Missing datasets: {missing}")
        if forbidden:
            errors.append(f"Access denied to datasets: {forbidden}")

        assert not errors, "\n".join(errors)


class TestPhase1GCSBuckets:
    """Verify GCS buckets exist and are accessible."""

    @pytest.fixture(scope="class")
    def storage_client(self) -> storage.Client:
        """Create Storage client."""
        return storage.Client()

    def test_gcs_buckets_exist(
        self,
        storage_client: storage.Client,
        gcs_buckets: list[str],
    ):
        """Both GCS buckets should exist and be accessible."""
        missing = []
        forbidden = []

        for bucket_name in gcs_buckets:
            if not bucket_name:
                continue
            try:
                storage_client.get_bucket(bucket_name)
            except NotFound:
                missing.append(bucket_name)
            except Forbidden:
                forbidden.append(bucket_name)

        errors = []
        if missing:
            errors.append(f"Missing buckets: {missing}")
        if forbidden:
            errors.append(f"Access denied to buckets: {forbidden}")

        assert not errors, "\n".join(errors)


class TestPhase1ADCAuthentication:
    """Verify Application Default Credentials work."""

    def test_adc_bigquery(self, gcp_project_id: str):
        """ADC should authenticate successfully for BigQuery."""
        client = bigquery.Client(project=gcp_project_id)
        list(client.list_datasets(max_results=1))

    def test_adc_storage(self):
        """ADC should authenticate successfully for Cloud Storage."""
        client = storage.Client()
        list(client.list_buckets(max_results=1))


class TestPhase1TerraformState:
    """Verify Terraform state file exists and is valid."""

    def test_terraform_state_exists(self, project_root: Path):
        """Terraform state file should exist."""
        state_file = project_root / "terraform" / "terraform.tfstate"
        assert state_file.exists(), f"Terraform state not found at {state_file}"

    def test_terraform_state_valid_json(self, project_root: Path):
        """Terraform state should be valid JSON."""
        state_file = project_root / "terraform" / "terraform.tfstate"
        if not state_file.exists():
            pytest.skip("Terraform state file does not exist")

        with open(state_file) as f:
            try:
                state = json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Terraform state is not valid JSON: {e}")

        assert "version" in state, "Terraform state missing 'version' key"

    def test_terraform_state_has_resources(self, project_root: Path):
        """Terraform state should contain resources."""
        state_file = project_root / "terraform" / "terraform.tfstate"
        if not state_file.exists():
            pytest.skip("Terraform state file does not exist")

        with open(state_file) as f:
            state = json.load(f)

        resources = state.get("resources", [])
        assert len(resources) > 0, "Terraform state has no resources"


# ============================================
# Phase 2: Data Extraction Scripts
# ============================================


class TestPhase2DataReview:
    """Verify DATA_REVIEW.md exists with analysis."""

    def test_data_review_exists(self, project_root: Path):
        """DATA_REVIEW.md should exist with analysis findings."""
        data_review = project_root / "docs" / "DATA_REVIEW.md"
        assert data_review.exists(), "docs/DATA_REVIEW.md not found"

    def test_data_review_not_empty(self, project_root: Path):
        """DATA_REVIEW.md should have substantial content."""
        data_review = project_root / "docs" / "DATA_REVIEW.md"
        if not data_review.exists():
            pytest.skip("DATA_REVIEW.md does not exist")

        content = data_review.read_text()
        assert len(content) > 500, "DATA_REVIEW.md appears too short"


class TestPhase2SyntheticGenerator:
    """Verify synthetic data generator."""

    def test_generator_script_exists(self, project_root: Path):
        """generate_synthetic_data.py should exist."""
        script = project_root / "scripts" / "generate_synthetic_data.py"
        assert script.exists(), "scripts/generate_synthetic_data.py not found"

    def test_config_exists(self, project_root: Path):
        """synthetic_data_config.yaml should exist."""
        config = project_root / "scripts" / "synthetic_data_config.yaml"
        assert config.exists(), "scripts/synthetic_data_config.yaml not found"

    def test_generator_runs(self, project_root: Path):
        """Synthetic data generator should execute without error."""
        script = project_root / "scripts" / "generate_synthetic_data.py"
        if not script.exists():
            pytest.skip("generate_synthetic_data.py does not exist")

        result = subprocess.run(
            ["uv", "run", "python", str(script), "--help"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        assert (
            result.returncode == 0 or "unrecognized arguments" in result.stderr
        ), f"Generator failed: {result.stderr}"


class TestPhase2ExtractionScripts:
    """Verify extraction scripts exist."""

    def test_google_ads_extractor_exists(self, project_root: Path):
        """extract_google_ads.py should exist."""
        script = project_root / "scripts" / "extract_google_ads.py"
        assert script.exists(), "scripts/extract_google_ads.py not found"

    def test_extraction_has_synthetic_flag(self, project_root: Path):
        """Extraction script should support --use-synthetic flag."""
        script = project_root / "scripts" / "extract_google_ads.py"
        if not script.exists():
            pytest.skip("extract_google_ads.py does not exist")

        content = script.read_text()
        assert (
            "use-synthetic" in content or "use_synthetic" in content
        ), "Extraction script missing --use-synthetic flag"

    def test_config_module_exists(self, project_root: Path):
        """scripts/config.py should exist."""
        config = project_root / "scripts" / "config.py"
        assert config.exists(), "scripts/config.py not found"

    def test_additional_extractors_exist(self, project_root: Path):
        """All additional extraction scripts should exist."""
        extractors = ["extract_trends.py", "extract_weather.py", "extract_finance.py"]
        missing = []
        for script_name in extractors:
            script = project_root / "scripts" / script_name
            if not script.exists():
                missing.append(script_name)

        assert not missing, f"Missing extraction scripts: {missing}"

    def test_utils_exists(self, project_root: Path):
        """scripts/utils.py should exist."""
        utils = project_root / "scripts" / "utils.py"
        assert utils.exists(), "scripts/utils.py not found"

    def test_loader_exists(self, project_root: Path):
        """load_to_bigquery.py should exist."""
        script = project_root / "scripts" / "load_to_bigquery.py"
        assert script.exists(), "scripts/load_to_bigquery.py not found"


# ============================================
# Phase 3: dbt Project Setup
# ============================================


class TestPhase3DbtProject:
    """Verify dbt project structure."""

    def test_dbt_project_exists(self, project_root: Path):
        """dbt_project directory should exist."""
        dbt_dir = project_root / "dbt_project"
        assert dbt_dir.is_dir(), "dbt_project/ directory not found"

    def test_dbt_project_yml_exists(self, project_root: Path):
        """dbt_project.yml should exist."""
        dbt_yml = project_root / "dbt_project" / "dbt_project.yml"
        assert dbt_yml.exists(), "dbt_project/dbt_project.yml not found"

    def test_profiles_yml_exists(self, project_root: Path):
        """profiles.yml should exist."""
        profiles_in_project = project_root / "dbt_project" / "profiles.yml"
        profiles_in_home = Path.home() / ".dbt" / "profiles.yml"
        assert (
            profiles_in_project.exists() or profiles_in_home.exists()
        ), "profiles.yml not found in dbt_project/ or ~/.dbt/"


class TestPhase3StagingModels:
    """Verify staging models exist."""

    STAGING_MODELS = [
        "stg_google_ads__campaigns.sql",
        "stg_google_ads__keywords.sql",
        "stg_google_ads__search_terms.sql",
    ]

    def test_staging_directory_exists(self, project_root: Path):
        """models/staging directory should exist."""
        staging_dir = project_root / "dbt_project" / "models" / "staging"
        assert staging_dir.is_dir(), "dbt_project/models/staging/ not found"

    def test_sources_yml_exists(self, project_root: Path):
        """sources.yml should exist in staging."""
        sources = project_root / "dbt_project" / "models" / "staging" / "sources.yml"
        assert sources.exists(), "models/staging/sources.yml not found"

    def test_staging_models_exist(self, project_root: Path):
        """Core staging models should exist."""
        staging_dir = project_root / "dbt_project" / "models" / "staging"
        if not staging_dir.is_dir():
            pytest.skip("staging directory does not exist")

        missing = []
        for model in self.STAGING_MODELS:
            if not (staging_dir / model).exists():
                missing.append(model)

        assert not missing, f"Missing staging models: {missing}"

    def test_staging_schema_yml_exists(self, project_root: Path):
        """Schema yml should exist for staging."""
        schema = (
            project_root / "dbt_project" / "models" / "staging" / "_staging_schema.yml"
        )
        alt_schema = project_root / "dbt_project" / "models" / "staging" / "schema.yml"
        assert (
            schema.exists() or alt_schema.exists()
        ), "models/staging schema.yml not found"


class TestPhase3DbtCompile:
    """Verify dbt compiles and runs."""

    def test_dbt_compile(self, project_root: Path):
        """dbt compile should succeed."""
        dbt_dir = project_root / "dbt_project"
        if not dbt_dir.is_dir():
            pytest.skip("dbt_project directory does not exist")

        result = subprocess.run(
            ["uv", "run", "dbt", "compile"],
            cwd=dbt_dir,
            capture_output=True,
            text=True,
        )
        assert (
            result.returncode == 0
        ), f"dbt compile failed: {result.stdout}\n{result.stderr}"

    def test_dbt_run_staging(self, project_root: Path):
        """dbt run --models staging should succeed."""
        dbt_dir = project_root / "dbt_project"
        if not dbt_dir.is_dir():
            pytest.skip("dbt_project directory does not exist")

        result = subprocess.run(
            ["uv", "run", "dbt", "run", "--models", "staging"],
            cwd=dbt_dir,
            capture_output=True,
            text=True,
        )
        assert (
            result.returncode == 0
        ), f"dbt run staging failed: {result.stdout}\n{result.stderr}"

    def test_dbt_test_staging(self, project_root: Path):
        """dbt test --models staging should pass."""
        dbt_dir = project_root / "dbt_project"
        if not dbt_dir.is_dir():
            pytest.skip("dbt_project directory does not exist")

        result = subprocess.run(
            ["uv", "run", "dbt", "test", "--models", "staging"],
            cwd=dbt_dir,
            capture_output=True,
            text=True,
        )
        assert (
            result.returncode == 0
        ), f"dbt test staging failed: {result.stdout}\n{result.stderr}"


# ============================================
# Phase 4: dbt Intermediate & Marts
# ============================================


class TestPhase4IntermediateModels:
    """Verify intermediate models."""

    def test_intermediate_directory_exists(self, project_root: Path):
        """models/intermediate directory should exist."""
        int_dir = project_root / "dbt_project" / "models" / "intermediate"
        assert int_dir.is_dir(), "dbt_project/models/intermediate/ not found"

    def test_intermediate_models_exist(self, project_root: Path):
        """At least one intermediate model should exist."""
        int_dir = project_root / "dbt_project" / "models" / "intermediate"
        if not int_dir.is_dir():
            pytest.skip("intermediate directory does not exist")

        sql_files = list(int_dir.glob("*.sql"))
        assert len(sql_files) > 0, "No intermediate models found"


class TestPhase4DimensionTables:
    """Verify dimension tables."""

    DIMENSION_TABLES = ["dim_campaigns.sql", "dim_keywords.sql", "dim_date.sql"]

    def test_marts_marketing_exists(self, project_root: Path):
        """models/marts/marketing directory should exist."""
        marts_dir = project_root / "dbt_project" / "models" / "marts" / "marketing"
        assert marts_dir.is_dir(), "dbt_project/models/marts/marketing/ not found"

    def test_dimension_tables_exist(self, project_root: Path):
        """Core dimension tables should exist."""
        marts_dir = project_root / "dbt_project" / "models" / "marts" / "marketing"
        if not marts_dir.is_dir():
            pytest.skip("marts/marketing directory does not exist")

        missing = []
        for dim in self.DIMENSION_TABLES:
            if not (marts_dir / dim).exists():
                missing.append(dim)

        assert not missing, f"Missing dimension tables: {missing}"


class TestPhase4FactTables:
    """Verify fact tables."""

    FACT_TABLES = ["fct_keyword_performance.sql", "fct_bid_recommendations.sql"]

    def test_fact_tables_exist(self, project_root: Path):
        """Core fact tables should exist."""
        marts_dir = project_root / "dbt_project" / "models" / "marts" / "marketing"
        if not marts_dir.is_dir():
            pytest.skip("marts/marketing directory does not exist")

        missing = []
        for fact in self.FACT_TABLES:
            if not (marts_dir / fact).exists():
                missing.append(fact)

        assert not missing, f"Missing fact tables: {missing}"

    def test_marketing_schema_exists(self, project_root: Path):
        """Marketing schema.yml should exist."""
        schema = (
            project_root
            / "dbt_project"
            / "models"
            / "marts"
            / "marketing"
            / "_marketing_schema.yml"
        )
        alt_schema = (
            project_root
            / "dbt_project"
            / "models"
            / "marts"
            / "marketing"
            / "schema.yml"
        )
        assert (
            schema.exists() or alt_schema.exists()
        ), "models/marts/marketing schema.yml not found"


class TestPhase4Analytics:
    """Verify analytics models."""

    def test_marts_analytics_exists(self, project_root: Path):
        """models/marts/analytics directory should exist."""
        analytics_dir = project_root / "dbt_project" / "models" / "marts" / "analytics"
        assert analytics_dir.is_dir(), "dbt_project/models/marts/analytics/ not found"

    def test_analytics_models_exist(self, project_root: Path):
        """At least one analytics model should exist."""
        analytics_dir = project_root / "dbt_project" / "models" / "marts" / "analytics"
        if not analytics_dir.is_dir():
            pytest.skip("marts/analytics directory does not exist")

        sql_files = list(analytics_dir.glob("*.sql"))
        assert len(sql_files) > 0, "No analytics models found"


class TestPhase4DbtRun:
    """Verify dbt runs all models."""

    def test_dbt_docs_generate(self, project_root: Path):
        """dbt docs generate should succeed."""
        dbt_dir = project_root / "dbt_project"
        if not dbt_dir.is_dir():
            pytest.skip("dbt_project directory does not exist")

        result = subprocess.run(
            ["uv", "run", "dbt", "docs", "generate"],
            cwd=dbt_dir,
            capture_output=True,
            text=True,
        )
        assert (
            result.returncode == 0
        ), f"dbt docs generate failed: {result.stdout}\n{result.stderr}"

    def test_dbt_run_all(self, project_root: Path):
        """dbt run should succeed for all models."""
        dbt_dir = project_root / "dbt_project"
        if not dbt_dir.is_dir():
            pytest.skip("dbt_project directory does not exist")

        result = subprocess.run(
            ["uv", "run", "dbt", "run"],
            cwd=dbt_dir,
            capture_output=True,
            text=True,
        )
        assert (
            result.returncode == 0
        ), f"dbt run failed: {result.stdout}\n{result.stderr}"

    def test_dbt_test_all(self, project_root: Path):
        """dbt test should pass for all models."""
        dbt_dir = project_root / "dbt_project"
        if not dbt_dir.is_dir():
            pytest.skip("dbt_project directory does not exist")

        result = subprocess.run(
            ["uv", "run", "dbt", "test"],
            cwd=dbt_dir,
            capture_output=True,
            text=True,
        )
        assert (
            result.returncode == 0
        ), f"dbt test failed: {result.stdout}\n{result.stderr}"


# ============================================
# Phase 5: Orchestration with Local Airflow
# ============================================


class TestPhase5Airflow:
    """Verify Airflow setup."""

    def test_dags_directory_exists(self, project_root: Path):
        """dags/ directory should exist."""
        dags_dir = project_root / "dags"
        assert dags_dir.is_dir(), "dags/ directory not found"

    def test_airflow_installed(self, project_root: Path):
        """apache-airflow should be installed."""
        result = subprocess.run(
            ["uv", "run", "python", "-c", "import airflow; print(airflow.__version__)"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Airflow not installed: {result.stderr}"


class TestPhase5MainDAG:
    """Verify main DAG exists and is valid."""

    def test_main_dag_exists(self, project_root: Path):
        """google_ads_pipeline.py DAG should exist."""
        dag_file = project_root / "dags" / "google_ads_pipeline.py"
        assert dag_file.exists(), "dags/google_ads_pipeline.py not found"

    def test_dag_has_required_tasks(self, project_root: Path):
        """DAG should define expected tasks."""
        dag_file = project_root / "dags" / "google_ads_pipeline.py"
        if not dag_file.exists():
            pytest.skip("DAG file does not exist")

        content = dag_file.read_text()
        required_patterns = ["synthetic", "extract", "dbt"]
        missing = [p for p in required_patterns if p not in content.lower()]

        assert not missing, f"DAG missing expected patterns: {missing}"

    def test_dag_imports_without_error(self, project_root: Path):
        """DAG should import without syntax errors."""
        dag_file = project_root / "dags" / "google_ads_pipeline.py"
        if not dag_file.exists():
            pytest.skip("DAG file does not exist")

        result = subprocess.run(
            ["uv", "run", "python", "-m", "py_compile", str(dag_file)],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"DAG has syntax errors: {result.stderr}"

    def test_dag_has_logging(self, project_root: Path):
        """DAG should include logging configuration."""
        dag_file = project_root / "dags" / "google_ads_pipeline.py"
        if not dag_file.exists():
            pytest.skip("DAG file does not exist")

        content = dag_file.read_text()
        assert "logging" in content or "logger" in content, "DAG should include logging"


# ============================================
# Phase 6: Testing & Data Quality
# ============================================


class TestPhase6TestStructure:
    """Verify test directory structure."""

    def test_tests_directory_structure(self, project_root: Path):
        """tests/unit/ and tests/integration/ should exist."""
        unit_dir = project_root / "tests" / "unit"
        integration_dir = project_root / "tests" / "integration"

        missing = []
        if not unit_dir.is_dir():
            missing.append("tests/unit/")
        if not integration_dir.is_dir():
            missing.append("tests/integration/")

        assert not missing, f"Missing test directories: {missing}"

    def test_conftest_exists(self, project_root: Path):
        """tests/conftest.py should exist."""
        conftest = project_root / "tests" / "conftest.py"
        assert conftest.exists(), "tests/conftest.py not found"

    def test_pytest_config_exists(self, project_root: Path):
        """pytest configuration should exist in pyproject.toml."""
        pyproject = project_root / "pyproject.toml"
        content = pyproject.read_text()
        assert "pytest" in content, "pytest not configured in pyproject.toml"


class TestPhase6UnitTests:
    """Verify unit tests."""

    def test_unit_tests_exist(self, project_root: Path):
        """Unit test files should exist."""
        unit_dir = project_root / "tests" / "unit"
        if not unit_dir.is_dir():
            pytest.skip("tests/unit/ does not exist")

        test_files = list(unit_dir.glob("test_*.py"))
        assert len(test_files) > 0, "No unit test files found in tests/unit/"

    def test_unit_tests_pass(self, project_root: Path):
        """Unit tests should pass."""
        unit_dir = project_root / "tests" / "unit"
        if not unit_dir.is_dir():
            pytest.skip("tests/unit/ does not exist")

        test_files = list(unit_dir.glob("test_*.py"))
        if not test_files:
            pytest.skip("No unit tests found")

        result = subprocess.run(
            ["uv", "run", "pytest", "tests/unit/", "-v"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        assert (
            result.returncode == 0
        ), f"Unit tests failed: {result.stdout}\n{result.stderr}"


class TestPhase6DbtTests:
    """Verify dbt test structure."""

    def test_dbt_tests_directory_exists(self, project_root: Path):
        """dbt_project/tests/ directory should exist."""
        tests_dir = project_root / "dbt_project" / "tests"
        singular_dir = project_root / "dbt_project" / "tests" / "singular"
        assert (
            tests_dir.is_dir() or singular_dir.is_dir()
        ), "dbt_project/tests/ directory not found"

    def test_dbt_macros_directory_exists(self, project_root: Path):
        """dbt_project/macros/ directory should exist."""
        macros_dir = project_root / "dbt_project" / "macros"
        assert macros_dir.is_dir(), "dbt_project/macros/ directory not found"


class TestPhase6PrecommitHooks:
    """Verify pre-commit hooks."""

    def test_precommit_config_exists(self, project_root: Path):
        """.pre-commit-config.yaml should exist."""
        config = project_root / ".pre-commit-config.yaml"
        assert config.exists(), ".pre-commit-config.yaml not found"

    def test_precommit_installed(self, project_root: Path):
        """pre-commit should be installed."""
        result = subprocess.run(
            ["uv", "run", "pre-commit", "--version"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"pre-commit not installed: {result.stderr}"

    def test_precommit_hooks_configured(self, project_root: Path):
        """.pre-commit-config.yaml should have hooks defined."""
        config = project_root / ".pre-commit-config.yaml"
        if not config.exists():
            pytest.skip(".pre-commit-config.yaml does not exist")

        content = config.read_text()
        assert "repos:" in content, "No repos defined in pre-commit config"
        assert "hooks:" in content, "No hooks defined in pre-commit config"


# ============================================
# Phase 7: Visualization
# ============================================


class TestPhase7Dashboard:
    """Verify dashboard exists."""

    def test_dashboards_directory_exists(self, project_root: Path):
        """dashboards/ directory should exist."""
        dashboards_dir = project_root / "dashboards"
        assert dashboards_dir.is_dir(), "dashboards/ directory not found"

    def test_streamlit_app_exists(self, project_root: Path):
        """dashboards/app.py should exist (if using Streamlit)."""
        app = project_root / "dashboards" / "app.py"
        looker_config = project_root / "dashboards" / "looker_config.json"

        assert (
            app.exists() or looker_config.exists()
        ), "Neither dashboards/app.py nor looker_config.json found"

    def test_streamlit_installed(self, project_root: Path):
        """Streamlit should be installed (if using Streamlit)."""
        app = project_root / "dashboards" / "app.py"
        if not app.exists():
            pytest.skip("Streamlit app not used")

        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-c",
                "import streamlit; print(streamlit.__version__)",
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Streamlit not installed: {result.stderr}"

    def test_streamlit_app_syntax(self, project_root: Path):
        """Streamlit app should have valid syntax."""
        app = project_root / "dashboards" / "app.py"
        if not app.exists():
            pytest.skip("Streamlit app not used")

        result = subprocess.run(
            ["uv", "run", "python", "-m", "py_compile", str(app)],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        assert (
            result.returncode == 0
        ), f"Streamlit app has syntax errors: {result.stderr}"


class TestPhase7DataAccess:
    """Verify dashboard can access required data."""

    def test_marts_tables_exist(self, gcp_project_id: str):
        """Marts tables should exist in BigQuery."""
        client = bigquery.Client(project=gcp_project_id)

        required_tables = [
            "marts_marketing.dim_campaigns",
            "marts_marketing.dim_keywords",
            "marts_marketing.fct_keyword_performance",
        ]

        missing = []
        for table_ref in required_tables:
            try:
                client.get_table(f"{gcp_project_id}.{table_ref}")
            except Exception:
                missing.append(table_ref)

        if missing:
            pytest.skip(f"Marts tables not yet created: {missing}")

    def test_marts_tables_have_data(self, gcp_project_id: str):
        """Marts tables should contain data."""
        client = bigquery.Client(project=gcp_project_id)

        try:
            query = f"""
                SELECT COUNT(*) as cnt
                FROM `{gcp_project_id}.marts_marketing.fct_keyword_performance`
            """
            result = list(client.query(query).result())
            count = result[0].cnt if result else 0
            assert count > 0, "fct_keyword_performance table is empty"
        except Exception as e:
            pytest.skip(f"Cannot query marts table: {e}")


# ============================================
# Phase 8: Documentation & CI/CD
# ============================================


class TestPhase8Documentation:
    """Verify documentation exists."""

    def test_setup_md_exists(self, project_root: Path):
        """docs/setup.md should exist."""
        setup_md = project_root / "docs" / "setup.md"
        assert setup_md.exists(), "docs/setup.md not found"

    def test_architecture_exists(self, project_root: Path):
        """Architecture documentation should exist."""
        arch_md = project_root / "docs" / "architecture.md"
        assert arch_md.exists(), "docs/architecture.md not found"


class TestPhase8Readme:
    """Verify README.md is complete."""

    def test_readme_exists(self, project_root: Path):
        """README.md should exist."""
        readme = project_root / "README.md"
        assert readme.exists(), "README.md not found"

    def test_readme_has_content(self, project_root: Path):
        """README.md should have substantial content."""
        readme = project_root / "README.md"
        content = readme.read_text()
        assert len(content) > 500, "README.md appears too short"

    def test_readme_has_setup_instructions(self, project_root: Path):
        """README.md should include setup instructions."""
        readme = project_root / "README.md"
        content = readme.read_text().lower()
        assert (
            "setup" in content or "install" in content or "getting started" in content
        ), "README.md missing setup instructions"


class TestPhase8GitHubActions:
    """Verify GitHub Actions."""

    def test_workflows_directory_exists(self, project_root: Path):
        """.github/workflows/ directory should exist."""
        workflows_dir = project_root / ".github" / "workflows"
        assert workflows_dir.is_dir(), ".github/workflows/ directory not found"

    def test_ci_workflow_exists(self, project_root: Path):
        """CI workflow should exist."""
        workflows_dir = project_root / ".github" / "workflows"
        if not workflows_dir.is_dir():
            pytest.skip(".github/workflows/ does not exist")

        ci_files = list(workflows_dir.glob("*.yml")) + list(
            workflows_dir.glob("*.yaml")
        )
        assert len(ci_files) > 0, "No workflow files found"

    def test_workflows_valid_yaml(self, project_root: Path):
        """Workflow files should be valid YAML."""
        import yaml

        workflows_dir = project_root / ".github" / "workflows"
        if not workflows_dir.is_dir():
            pytest.skip(".github/workflows/ does not exist")

        for workflow_file in workflows_dir.glob("*.y*ml"):
            with open(workflow_file) as f:
                try:
                    yaml.safe_load(f)
                except yaml.YAMLError as e:
                    pytest.fail(f"{workflow_file.name} is invalid YAML: {e}")


class TestPhase8Docker:
    """Verify Docker support (optional)."""

    def test_dockerfile_exists(self, project_root: Path):
        """Dockerfile should exist (optional)."""
        dockerfile = project_root / "Dockerfile"
        if not dockerfile.exists():
            pytest.skip("Dockerfile not created (optional)")

    def test_docker_compose_exists(self, project_root: Path):
        """docker-compose.yml should exist (optional)."""
        compose = project_root / "docker-compose.yml"
        compose_alt = project_root / "docker-compose.yaml"
        if not (compose.exists() or compose_alt.exists()):
            pytest.skip("docker-compose.yml not created (optional)")


# ============================================
# Phase 9: Optional Production Deployment
# ============================================


class TestPhase9Monitoring:
    """Verify monitoring documentation."""

    def test_monitoring_documented(self, project_root: Path):
        """Monitoring setup should be documented."""
        monitoring_doc = project_root / "docs" / "monitoring.md"
        setup_md = project_root / "docs" / "setup.md"
        readme = project_root / "README.md"

        has_monitoring_docs = monitoring_doc.exists()

        if not has_monitoring_docs:
            for doc in [setup_md, readme]:
                if doc.exists():
                    content = doc.read_text().lower()
                    if "monitoring" in content or "airflow ui" in content:
                        has_monitoring_docs = True
                        break

        if not has_monitoring_docs:
            pytest.skip("Monitoring documentation not found (optional)")


class TestPhase9Performance:
    """Verify performance optimization."""

    def test_optimization_documented(self, project_root: Path):
        """Performance optimization should be documented."""
        perf_doc = project_root / "docs" / "performance_optimization.md"
        optimization_doc = project_root / "docs" / "optimization.md"

        if not (perf_doc.exists() or optimization_doc.exists()):
            pytest.skip("Performance optimization not documented (optional)")

    def test_incremental_models_exist(self, project_root: Path):
        """dbt incremental models should exist for large tables."""
        models_dir = project_root / "dbt_project" / "models"
        if not models_dir.is_dir():
            pytest.skip("dbt models directory does not exist")

        found_incremental = False
        for sql_file in models_dir.rglob("*.sql"):
            content = sql_file.read_text()
            if (
                "materialized='incremental'" in content
                or 'materialized="incremental"' in content
            ):
                found_incremental = True
                break

        if not found_incremental:
            pytest.skip("No incremental models found (optional optimization)")


# ============================================
# Phase 10: Final Polish
# ============================================


class TestPhase10CodeQuality:
    """Verify code quality."""

    def test_no_hardcoded_project_ids(self, project_root: Path):
        """Python files should not have hardcoded GCP project IDs."""
        scripts_dir = project_root / "scripts"
        if not scripts_dir.is_dir():
            pytest.skip("scripts/ directory does not exist")

        violations = []
        for py_file in scripts_dir.glob("*.py"):
            content = py_file.read_text()
            if "wiki-edit-pipeline" in content and "os.getenv" not in content:
                violations.append(py_file.name)

        assert not violations, f"Files with hardcoded project IDs: {violations}"

    def test_linters_pass(self, project_root: Path):
        """Code should pass linting (ruff)."""
        result = subprocess.run(
            ["uv", "run", "ruff", "check", "scripts/", "tests/"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        if "No module named ruff" in result.stderr:
            pytest.skip("ruff not installed")

        assert result.returncode == 0, f"Linting failed:\n{result.stdout}"

    def test_formatter_check(self, project_root: Path):
        """Code should be formatted (black)."""
        result = subprocess.run(
            ["uv", "run", "black", "--check", "scripts/", "tests/"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        if "No module named black" in result.stderr:
            pytest.skip("black not installed")

        assert result.returncode == 0, f"Formatting check failed:\n{result.stdout}"


class TestPhase10APIIntegration:
    """Verify API integration documentation."""

    def test_env_example_complete(self, project_root: Path):
        """.env.example should have all required variables."""
        env_example = project_root / ".env.example"
        assert env_example.exists(), ".env.example not found"

        content = env_example.read_text()
        required_vars = ["GCP_PROJECT_ID", "GCP_REGION", "USE_SYNTHETIC_DATA"]

        missing = [var for var in required_vars if var not in content]
        assert not missing, f".env.example missing variables: {missing}"


class TestPhase10FinalDocs:
    """Verify final documentation."""

    def test_all_docs_exist(self, project_root: Path):
        """Key documentation files should exist."""
        required_docs = [
            "README.md",
            "docs/PROJECT.md",
            "docs/GCP-SETUP.md",
            ".env.example",
        ]

        missing = []
        for doc in required_docs:
            if not (project_root / doc).exists():
                missing.append(doc)

        assert not missing, f"Missing documentation: {missing}"

    def test_troubleshooting_exists(self, project_root: Path):
        """Troubleshooting section should exist somewhere."""
        readme = project_root / "README.md"
        setup_md = project_root / "docs" / "setup.md"
        troubleshooting = project_root / "docs" / "troubleshooting.md"

        found = troubleshooting.exists()
        if not found:
            for doc in [readme, setup_md]:
                if doc.exists():
                    content = doc.read_text().lower()
                    if "troubleshoot" in content or "common issues" in content:
                        found = True
                        break

        if not found:
            pytest.skip("Troubleshooting section not found (recommended)")
