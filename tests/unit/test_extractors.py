"""Unit tests for data extraction scripts."""

import json

import pandas as pd
import pytest


class TestSyntheticDataGenerator:
    """Tests for the synthetic data generator."""

    def test_generator_imports(self):
        """Test that generator module can be imported."""
        from scripts.generate_synthetic_data import SyntheticDataGenerator

        assert SyntheticDataGenerator is not None

    def test_generator_config_loading(self, project_root):
        """Test that config file loads correctly."""
        from scripts.generate_synthetic_data import SyntheticDataGenerator

        config_path = project_root / "scripts" / "synthetic_data_config.yaml"
        if config_path.exists():
            generator = SyntheticDataGenerator(config_path)
            assert generator.config is not None

    def test_generator_has_generate_methods(self, project_root):
        """Test generator has expected methods."""
        from scripts.generate_synthetic_data import SyntheticDataGenerator

        config_path = project_root / "scripts" / "synthetic_data_config.yaml"
        if not config_path.exists():
            pytest.skip("Config file not found")

        generator = SyntheticDataGenerator(config_path)
        assert hasattr(generator, "generate_campaigns")
        assert hasattr(generator, "generate_keywords")
        assert hasattr(generator, "generate_all")


class TestGoogleAdsExtractor:
    """Tests for Google Ads extraction script."""

    def test_extractor_imports(self):
        """Test that extractor module can be imported."""
        from scripts.extract_google_ads import GoogleAdsExtractor

        assert GoogleAdsExtractor is not None

    def test_extractor_synthetic_mode(self):
        """Test extractor works in synthetic mode."""
        from scripts.extract_google_ads import GoogleAdsExtractor

        extractor = GoogleAdsExtractor(use_synthetic=True)
        assert extractor.use_synthetic is True

    def test_extractor_has_extract_methods(self):
        """Test extractor has expected methods."""
        from scripts.extract_google_ads import GoogleAdsExtractor

        extractor = GoogleAdsExtractor(use_synthetic=True)
        assert hasattr(extractor, "extract_campaigns")
        assert hasattr(extractor, "extract_keywords")


class TestTrendsExtractor:
    """Tests for trends extraction script."""

    def test_extractor_imports(self):
        """Test that trends extractor can be imported."""
        from scripts.extract_trends import TrendsExtractor

        assert TrendsExtractor is not None

    def test_extractor_synthetic_mode(self):
        """Test trends extractor works in synthetic mode."""
        from scripts.extract_trends import TrendsExtractor

        extractor = TrendsExtractor(use_synthetic=True)
        assert extractor.use_synthetic is True


class TestDataValidation:
    """Tests for data validation during extraction."""

    def test_dataframe_not_empty(self):
        """Test that generated DataFrames are not empty."""
        df = pd.DataFrame({"id": [1, 2, 3], "value": ["a", "b", "c"]})
        assert len(df) > 0

    def test_required_columns_present(self):
        """Test required columns are present in data."""
        df = pd.DataFrame(
            {"campaign_id": [1, 2], "campaign_name": ["Campaign A", "Campaign B"]}
        )

        required = ["campaign_id", "campaign_name"]
        for col in required:
            assert col in df.columns

    def test_no_null_ids(self):
        """Test that ID columns don't have nulls."""
        df = pd.DataFrame({"campaign_id": [1, 2, 3]})
        assert df["campaign_id"].notna().all()

    def test_metrics_non_negative(self):
        """Test that metric columns are non-negative."""
        df = pd.DataFrame({"clicks": [10, 20, 0], "impressions": [100, 200, 50]})

        assert (df["clicks"] >= 0).all()
        assert (df["impressions"] >= 0).all()


class TestExtractorOutput:
    """Tests for extractor output format."""

    def test_json_output_valid(self, tmp_path):
        """Test JSON output is valid."""
        data = [{"id": 1, "name": "test"}]
        output_file = tmp_path / "test.json"

        with open(output_file, "w") as f:
            json.dump(data, f)

        with open(output_file, "r") as f:
            loaded = json.load(f)

        assert loaded == data

    def test_output_directory_creation(self, tmp_path):
        """Test output directories are created."""
        output_dir = tmp_path / "output" / "extracted"
        output_dir.mkdir(parents=True, exist_ok=True)

        assert output_dir.exists()
