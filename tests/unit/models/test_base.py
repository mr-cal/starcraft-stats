"""Tests for base CSV model."""

from typing import ClassVar

import pytest
from starcraft_stats.models.base import CsvModel


class SampleModel(CsvModel):
    """Sample model for testing."""

    CSV_HEADERS: ClassVar[list[str]] = ["name", "age", "active"]

    name: str
    age: int
    active: bool

    def to_csv_row(self) -> list[str]:
        """Convert to CSV row."""
        return [self.name, str(self.age), str(self.active)]


class TestCsvModel:
    """Tests for CsvModel base class."""

    def test_save_to_csv_creates_file(self, tmp_path):
        """Test saving data to a new CSV file."""
        csv_file = tmp_path / "test.csv"
        data = [
            SampleModel(name="Alice", age=30, active=True),
            SampleModel(name="Bob", age=25, active=False),
        ]

        SampleModel.save_to_csv(data, csv_file)

        assert csv_file.exists()
        content = csv_file.read_text()
        assert "name,age,active" in content
        assert "Alice,30,True" in content
        assert "Bob,25,False" in content

    def test_save_to_csv_overwrites_existing(self, tmp_path):
        """Test that save_to_csv overwrites existing file by default."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("old,data\n1,2\n")

        data = [SampleModel(name="Alice", age=30, active=True)]
        SampleModel.save_to_csv(data, csv_file)

        content = csv_file.read_text()
        assert "old,data" not in content
        assert "name,age,active" in content

    def test_save_to_csv_append_mode(self, tmp_path):
        """Test saving data in append mode."""
        csv_file = tmp_path / "test.csv"

        # Write initial data
        data1 = [SampleModel(name="Alice", age=30, active=True)]
        SampleModel.save_to_csv(data1, csv_file)

        # Append more data
        data2 = [SampleModel(name="Bob", age=25, active=False)]
        SampleModel.save_to_csv(data2, csv_file, append=True)

        content = csv_file.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 3  # header + 2 data rows
        assert lines[0] == "name,age,active"
        assert "Alice,30,True" in content
        assert "Bob,25,False" in content

    def test_save_to_csv_append_to_nonexistent_adds_header(self, tmp_path):
        """Test that append mode adds header if file doesn't exist."""
        csv_file = tmp_path / "test.csv"

        data = [SampleModel(name="Alice", age=30, active=True)]
        SampleModel.save_to_csv(data, csv_file, append=True)

        content = csv_file.read_text()
        assert "name,age,active" in content

    def test_save_to_csv_empty_list(self, tmp_path):
        """Test saving an empty list creates file with just headers."""
        csv_file = tmp_path / "test.csv"

        SampleModel.save_to_csv([], csv_file)

        content = csv_file.read_text()
        assert content == "name,age,active\n"

    def test_save_to_csv_missing_headers_raises(self, tmp_path):
        """Test that model without CSV_HEADERS raises ValueError."""

        class BadModel(CsvModel):
            value: str

            def to_csv_row(self) -> list[str]:
                return [self.value]

        csv_file = tmp_path / "test.csv"
        with pytest.raises(ValueError, match="must define CSV_HEADERS"):
            BadModel.save_to_csv([BadModel(value="test")], csv_file)

    def test_load_from_csv_reads_data(self, tmp_path):
        """Test loading data from CSV file."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,age,active\nAlice,30,True\nBob,25,False\n")

        models = SampleModel.load_from_csv(csv_file)

        assert len(models) == 2
        assert models[0].name == "Alice"
        assert models[0].age == 30
        assert models[0].active is True
        assert models[1].name == "Bob"
        assert models[1].age == 25
        assert models[1].active is False

    def test_load_from_csv_nonexistent_returns_empty(self, tmp_path):
        """Test loading from nonexistent file returns empty list."""
        csv_file = tmp_path / "nonexistent.csv"

        models = SampleModel.load_from_csv(csv_file)

        assert models == []

    def test_load_from_csv_empty_file(self, tmp_path):
        """Test loading from file with only headers."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,age,active\n")

        models = SampleModel.load_from_csv(csv_file)

        assert models == []

    def test_to_csv_row_not_implemented(self):
        """Test that base CsvModel raises NotImplementedError for to_csv_row."""

        class IncompleteModel(CsvModel):
            CSV_HEADERS: ClassVar[list[str]] = ["value"]
            value: str

        model = IncompleteModel(value="test")
        with pytest.raises(NotImplementedError, match="must implement to_csv_row"):
            model.to_csv_row()
