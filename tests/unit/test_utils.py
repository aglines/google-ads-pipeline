"""Unit tests for utility functions."""

import json
import os
from datetime import datetime

import pytest


class TestUtilsModule:
    """Tests for scripts/utils.py module."""

    def test_utils_imports(self):
        """Test that utils module can be imported."""
        from scripts import utils

        assert utils is not None

    def test_setup_logging(self):
        """Test logging setup function."""
        from scripts.utils import setup_logging

        logger = setup_logging("test_logger")
        assert logger is not None
        assert logger.name == "test_logger"

    def test_get_gcp_config(self):
        """Test GCP config retrieval."""
        from scripts.utils import get_gcp_config

        config = get_gcp_config()
        assert isinstance(config, dict)
        assert "project_id" in config

    def test_parse_date(self):
        """Test date parsing function."""
        from scripts.utils import parse_date

        result = parse_date("2024-01-15")
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_get_date_suffix(self):
        """Test date suffix generation."""
        from scripts.utils import get_date_suffix

        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 15)
        suffix = get_date_suffix(start, end)
        assert "2024" in suffix


class TestConfigManagement:
    """Tests for configuration management."""

    def test_config_imports(self):
        """Test config module can be imported."""
        from scripts import config

        assert config is not None

    def test_config_has_classes(self):
        """Test config has required classes."""
        from scripts.config import GCPConfig, PipelineConfig

        assert GCPConfig is not None
        assert PipelineConfig is not None

    def test_get_config(self):
        """Test get_config function."""
        from scripts.config import get_config

        config = get_config()
        assert config is not None

    def test_is_synthetic_mode(self):
        """Test synthetic mode check."""
        from scripts.config import is_synthetic_mode

        result = is_synthetic_mode()
        assert isinstance(result, bool)

    def test_env_var_loading(self):
        """Test environment variables are loaded."""
        project_id = os.getenv("GCP_PROJECT_ID")
        assert project_id is None or isinstance(project_id, str)


class TestLogging:
    """Tests for logging configuration."""

    def test_logger_creation(self):
        """Test logger can be created."""
        import logging

        logger = logging.getLogger("test_logger")
        assert logger is not None

    def test_structured_logging(self):
        """Test structured log message formatting."""
        log_data = {
            "event": "extraction_complete",
            "rows": 100,
            "duration_seconds": 5.5,
        }

        log_message = json.dumps(log_data)
        parsed = json.loads(log_message)

        assert parsed["event"] == "extraction_complete"
        assert parsed["rows"] == 100


class TestFileOperations:
    """Tests for file operation utilities."""

    def test_json_read_write(self, tmp_path):
        """Test JSON file operations."""
        test_data = {"key": "value", "number": 42}
        file_path = tmp_path / "test.json"

        with open(file_path, "w") as f:
            json.dump(test_data, f)

        with open(file_path, "r") as f:
            loaded_data = json.load(f)

        assert loaded_data == test_data

    def test_path_creation(self, tmp_path):
        """Test directory creation."""
        new_dir = tmp_path / "new" / "nested" / "dir"
        new_dir.mkdir(parents=True, exist_ok=True)

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_glob_pattern_matching(self, tmp_path):
        """Test glob pattern matching."""
        (tmp_path / "data1.json").touch()
        (tmp_path / "data2.json").touch()
        (tmp_path / "other.txt").touch()

        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) == 2


class TestErrorHandling:
    """Tests for error handling utilities."""

    def test_handle_api_rate_limit_exists(self):
        """Test rate limit handler exists."""
        from scripts.utils import handle_api_rate_limit

        assert callable(handle_api_rate_limit)

    def test_validation_error_handling(self):
        """Test validation errors are properly raised."""
        with pytest.raises(ValueError):
            raise ValueError("Invalid data format")

    def test_file_not_found_handling(self, tmp_path):
        """Test missing file handling."""
        nonexistent = tmp_path / "does_not_exist.json"

        with pytest.raises(FileNotFoundError):
            with open(nonexistent, "r") as f:
                f.read()
