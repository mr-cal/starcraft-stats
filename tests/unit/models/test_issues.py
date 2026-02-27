"""Tests for IssueDataPoint CSV model."""

from starcraft_stats.models.issues import IssueDataPoint


class TestIssueDataPoint:
    """Tests for IssueDataPoint model."""

    def test_create_with_all_fields(self):
        """Test creating datapoint with all fields."""
        point = IssueDataPoint(
            date="2024-Jan-01",
            issues=10,
            age=30,
        )

        assert point.date == "2024-Jan-01"
        assert point.issues == 10
        assert point.age == 30

    def test_create_with_none_values(self):
        """Test creating datapoint with None values."""
        point = IssueDataPoint(
            date="2024-Jan-01",
            issues=10,
            age=None,
        )

        assert point.age is None

    def test_csv_headers(self):
        """Test CSV headers are defined correctly."""
        assert IssueDataPoint.CSV_HEADERS == ["date", "issues", "closed", "age"]

    def test_to_csv_row_all_values(self):
        """Test converting to CSV row with all values."""
        point = IssueDataPoint(
            date="2024-Jan-01",
            issues=10,
            closed=3,
            age=30,
        )

        row = point.to_csv_row()

        assert row == ["2024-Jan-01", "10", "3", "30"]

    def test_to_csv_row_with_none(self):
        """Test converting to CSV row with None values."""
        point = IssueDataPoint(
            date="2024-Jan-01",
            issues=10,
            age=None,
        )

        row = point.to_csv_row()

        assert row == ["2024-Jan-01", "10", "0", ""]

    def test_save_and_load_roundtrip(self, tmp_path):
        """Test saving and loading data maintains integrity."""
        csv_file = tmp_path / "issues.csv"
        data = [
            IssueDataPoint(date="2024-Jan-01", issues=10, closed=2, age=30),
            IssueDataPoint(date="2024-Jan-02", issues=15, closed=1, age=32),
        ]

        IssueDataPoint.save_to_csv(data, csv_file)
        loaded = IssueDataPoint.load_from_csv(csv_file)

        assert len(loaded) == 2
        assert loaded[0].date == "2024-Jan-01"
        assert loaded[0].issues == 10
        assert loaded[0].closed == 2
        assert loaded[1].issues == 15

    def test_save_csv_format(self, tmp_path):
        """Test CSV file format is correct."""
        csv_file = tmp_path / "issues.csv"
        data = [
            IssueDataPoint(date="2024-Jan-01", issues=10, closed=3, age=30),
        ]

        IssueDataPoint.save_to_csv(data, csv_file)
        content = csv_file.read_text()

        lines = content.strip().split("\n")
        assert lines[0] == "date,issues,closed,age"
        assert lines[1] == "2024-Jan-01,10,3,30"
