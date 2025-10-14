"""Unit tests for data validation functions."""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch

from services.graph_index import validators


class TestLoadFirstRow:
    """Tests for _load_first_row helper."""

    def test_loads_header_from_csv(self, tmp_path):
        """Should load the first row from a CSV file."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("col1,col2,col3\nval1,val2,val3\n", encoding="utf-8")

        result = validators._load_first_row(csv_file)

        assert result == ["col1", "col2", "col3"]

    def test_handles_empty_csv(self, tmp_path):
        """Should raise StopIteration for empty CSV."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("", encoding="utf-8")

        with pytest.raises(StopIteration):
            validators._load_first_row(csv_file)


class TestLoadFirstDict:
    """Tests for _load_first_dict helper."""

    def test_loads_first_row_as_dict(self, tmp_path):
        """Should load first data row as dictionary."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "name,age,city\nAlice,30,NYC\nBob,25,LA\n",
            encoding="utf-8"
        )

        result = validators._load_first_dict(csv_file)

        assert result == {"name": "Alice", "age": "30", "city": "NYC"}

    def test_handles_csv_with_only_header(self, tmp_path):
        """Should raise StopIteration if no data rows."""
        csv_file = tmp_path / "header_only.csv"
        csv_file.write_text("col1,col2\n", encoding="utf-8")

        with pytest.raises(StopIteration):
            validators._load_first_dict(csv_file)


class TestValidateEiaCsv:
    """Tests for validate_eia_csv function."""

    def test_passes_for_valid_csv(self, tmp_path):
        """Should pass validation for CSV with expected header."""
        csv_file = tmp_path / "eia_dpr_latest.csv"
        csv_file.write_text("FieldA,FieldB,FieldC\nval1,val2,val3\n", encoding="utf-8")

        # Should not raise
        validators.validate_eia_csv(csv_file)

    def test_raises_for_missing_file(self, tmp_path):
        """Should raise FileNotFoundError if CSV doesn't exist."""
        csv_file = tmp_path / "nonexistent.csv"

        with pytest.raises(FileNotFoundError, match="EIA CSV not found"):
            validators.validate_eia_csv(csv_file)

    def test_raises_for_short_header(self, tmp_path):
        """Should raise ValueError if header is too short."""
        csv_file = tmp_path / "eia_dpr_latest.csv"
        csv_file.write_text("OnlyOneField\nval1\n", encoding="utf-8")

        with pytest.raises(ValueError, match="EIA header too short"):
            validators.validate_eia_csv(csv_file)

    @patch('services.graph_index.validators.paths')
    def test_uses_default_path_when_none_provided(self, mock_paths, tmp_path):
        """Should use default path from paths module when no path provided."""
        default_csv = tmp_path / "eia_dpr_latest.csv"
        default_csv.write_text("FieldA,FieldB\nval1,val2\n", encoding="utf-8")
        mock_paths.PROCESSED_TABLES_DIR = tmp_path

        # Should not raise
        validators.validate_eia_csv(None)


class TestValidateUsgsCsv:
    """Tests for validate_usgs_csv function."""

    def test_passes_for_valid_csv(self, tmp_path):
        """Should pass validation for CSV with all expected fields."""
        csv_file = tmp_path / "usgs_streamflow_latest.csv"
        header = ",".join(validators.EXPECTED_USGS_FIELDS)
        csv_file.write_text(f"{header}\nval1,val2,val3,val4,val5,val6,val7,val8\n", encoding="utf-8")

        # Should not raise
        validators.validate_usgs_csv(csv_file)

    def test_raises_for_missing_file(self, tmp_path):
        """Should raise FileNotFoundError if CSV doesn't exist."""
        csv_file = tmp_path / "nonexistent.csv"

        with pytest.raises(FileNotFoundError, match="USGS CSV not found"):
            validators.validate_usgs_csv(csv_file)

    def test_raises_for_missing_fields(self, tmp_path):
        """Should raise ValueError if required fields are missing."""
        csv_file = tmp_path / "usgs_streamflow_latest.csv"
        csv_file.write_text("site_code,site_name\nval1,val2\n", encoding="utf-8")

        with pytest.raises(ValueError, match="USGS CSV missing fields"):
            validators.validate_usgs_csv(csv_file)

    def test_allows_extra_fields(self, tmp_path):
        """Should allow CSVs with extra fields beyond required."""
        csv_file = tmp_path / "usgs_streamflow_latest.csv"
        all_fields = list(validators.EXPECTED_USGS_FIELDS) + ["extra_field"]
        header = ",".join(all_fields)
        csv_file.write_text(f"{header}\n" + ",".join(["val"] * len(all_fields)) + "\n", encoding="utf-8")

        # Should not raise
        validators.validate_usgs_csv(csv_file)


class TestValidateLasMetadata:
    """Tests for validate_las_metadata function."""

    def test_passes_for_valid_json(self, tmp_path):
        """Should pass validation for JSON with expected stats."""
        json_file = tmp_path / "kgs_las_metadata.json"
        data = {"stats": {"stat": "value"}}
        json_file.write_text(json.dumps(data), encoding="utf-8")

        # Should not raise
        validators.validate_las_metadata(json_file)

    def test_raises_for_missing_file(self, tmp_path):
        """Should raise FileNotFoundError if JSON doesn't exist."""
        json_file = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError, match="LAS metadata JSON not found"):
            validators.validate_las_metadata(json_file)

    def test_raises_for_missing_stats(self, tmp_path):
        """Should raise ValueError if stats key is missing."""
        json_file = tmp_path / "kgs_las_metadata.json"
        data = {"other_key": "value"}
        json_file.write_text(json.dumps(data), encoding="utf-8")

        with pytest.raises(ValueError, match="LAS metadata missing stats"):
            validators.validate_las_metadata(json_file)

    def test_raises_for_missing_stat_field(self, tmp_path):
        """Should raise ValueError if 'stat' field missing in stats."""
        json_file = tmp_path / "kgs_las_metadata.json"
        data = {"stats": {"other_stat": "value"}}
        json_file.write_text(json.dumps(data), encoding="utf-8")

        with pytest.raises(ValueError, match="LAS metadata missing stats"):
            validators.validate_las_metadata(json_file)

    def test_allows_extra_stats(self, tmp_path):
        """Should allow JSON with extra stats beyond required."""
        json_file = tmp_path / "kgs_las_metadata.json"
        data = {"stats": {"stat": "value", "extra_stat": "extra_value"}}
        json_file.write_text(json.dumps(data), encoding="utf-8")

        # Should not raise
        validators.validate_las_metadata(json_file)


class TestRunAllValidations:
    """Tests for run_all_validations function."""

    @patch('services.graph_index.validators.validate_las_metadata')
    @patch('services.graph_index.validators.validate_usgs_csv')
    @patch('services.graph_index.validators.validate_eia_csv')
    def test_calls_all_validators(self, mock_eia, mock_usgs, mock_las):
        """Should call all three validation functions."""
        validators.run_all_validations()

        mock_eia.assert_called_once()
        mock_usgs.assert_called_once()
        mock_las.assert_called_once()

    @patch('services.graph_index.validators.validate_las_metadata')
    @patch('services.graph_index.validators.validate_usgs_csv')
    @patch('services.graph_index.validators.validate_eia_csv')
    def test_propagates_validation_errors(self, mock_eia, mock_usgs, mock_las):
        """Should propagate errors from individual validators."""
        mock_usgs.side_effect = ValueError("USGS validation failed")

        with pytest.raises(ValueError, match="USGS validation failed"):
            validators.run_all_validations()
