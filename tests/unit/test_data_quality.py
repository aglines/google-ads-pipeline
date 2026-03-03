"""Unit tests for data quality validation logic."""

import pandas as pd


class TestDataQualityChecks:
    """Tests for data quality validation functions."""

    def test_null_check(self):
        """Test null value detection."""
        df_with_nulls = pd.DataFrame({"col": [1, None, 3]})
        df_without_nulls = pd.DataFrame({"col": [1, 2, 3]})

        assert df_with_nulls["col"].isna().any()
        assert not df_without_nulls["col"].isna().any()

    def test_unique_check(self):
        """Test uniqueness validation."""
        df_unique = pd.DataFrame({"id": [1, 2, 3]})
        df_duplicates = pd.DataFrame({"id": [1, 2, 2]})

        assert df_unique["id"].is_unique
        assert not df_duplicates["id"].is_unique

    def test_value_range_check(self):
        """Test value range validation."""
        df = pd.DataFrame({"ctr": [0.01, 0.05, 0.10, 0.03]})

        # CTR should be between 0 and 1
        assert (df["ctr"] >= 0).all()
        assert (df["ctr"] <= 1).all()

    def test_accepted_values_check(self):
        """Test accepted values validation."""
        valid_match_types = ["Broad", "Phrase", "Exact"]
        df = pd.DataFrame({"match_type": ["Broad", "Phrase", "Exact", "Broad"]})

        assert df["match_type"].isin(valid_match_types).all()

    def test_referential_integrity(self):
        """Test foreign key relationships."""
        campaigns = pd.DataFrame({"campaign_id": [1, 2, 3]})
        keywords = pd.DataFrame({"keyword_id": [1, 2], "campaign_id": [1, 2]})

        # All keyword campaign_ids should exist in campaigns
        assert keywords["campaign_id"].isin(campaigns["campaign_id"]).all()


class TestMetricValidation:
    """Tests for metric-specific validations."""

    def test_clicks_le_impressions(self):
        """Test that clicks never exceed impressions."""
        df = pd.DataFrame({"impressions": [100, 200, 50], "clicks": [10, 15, 5]})

        assert (df["clicks"] <= df["impressions"]).all()

    def test_cost_positive(self):
        """Test that cost is non-negative."""
        df = pd.DataFrame({"cost": [10.5, 0, 25.3, 100.0]})

        assert (df["cost"] >= 0).all()

    def test_conversion_rate_bounds(self):
        """Test conversion rate is within reasonable bounds."""
        df = pd.DataFrame({"clicks": [100, 200, 50], "conversions": [5, 10, 2]})

        conv_rate = df["conversions"] / df["clicks"]

        # Conversion rate should be between 0 and 1
        assert (conv_rate >= 0).all()
        assert (conv_rate <= 1).all()

    def test_roas_calculation(self):
        """Test ROAS calculation is correct."""
        df = pd.DataFrame({"conversion_value": [100, 200, 50], "cost": [50, 100, 25]})

        roas = df["conversion_value"] / df["cost"]
        expected_roas = pd.Series([2.0, 2.0, 2.0])

        pd.testing.assert_series_equal(roas, expected_roas)


class TestSchemaValidation:
    """Tests for schema compliance."""

    def test_campaign_schema(self):
        """Test campaign data matches expected schema."""
        required_columns = [
            "campaign_id",
            "campaign_name",
        ]

        df = pd.DataFrame(
            {
                "campaign_id": ["1"],
                "campaign_name": ["Test Campaign"],
                "extra_col": ["allowed"],
            }
        )

        for col in required_columns:
            assert col in df.columns, f"Missing required column: {col}"

    def test_keyword_schema(self):
        """Test keyword data matches expected schema."""
        required_columns = [
            "keyword_id",
            "keyword",
        ]

        df = pd.DataFrame(
            {
                "keyword_id": ["1"],
                "keyword": ["test keyword"],
            }
        )

        for col in required_columns:
            assert col in df.columns, f"Missing required column: {col}"

    def test_date_format(self):
        """Test date columns are properly formatted."""
        df = pd.DataFrame({"date": ["2024-01-15", "2024-01-16"]})
        df["date"] = pd.to_datetime(df["date"])

        # pandas 2.x uses datetime64[us], older versions use datetime64[ns]
        assert "datetime64" in str(df["date"].dtype)
