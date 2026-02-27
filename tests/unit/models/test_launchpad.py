"""Tests for LaunchpadDataPoint CSV model."""

from starcraft_stats.models.launchpad import LaunchpadDataPoint


class TestLaunchpadDataPoint:
    """Tests for LaunchpadDataPoint model."""

    def test_create_with_all_fields(self):
        """Test creating datapoint with all fields."""
        point = LaunchpadDataPoint(
            timestamp="2024-Jan-01 12:00:00",
            new=5,
            incomplete=3,
            opinion=1,
            invalid=2,
            wont_fix=0,
            expired=0,
            confirmed=10,
            triaged=8,
            in_progress=4,
            fix_committed=2,
            fix_released=100,
            does_not_exist=0,
        )

        assert point.timestamp == "2024-Jan-01 12:00:00"
        assert point.new == 5
        assert point.confirmed == 10
        assert point.fix_released == 100

    def test_create_with_defaults(self):
        """Test creating datapoint with default values."""
        point = LaunchpadDataPoint(timestamp="2024-Jan-01 12:00:00")

        assert point.new == 0
        assert point.incomplete == 0
        assert point.fix_released == 0

    def test_csv_headers(self):
        """Test CSV headers are defined correctly."""
        expected = [
            "timestamp",
            "New",
            "Incomplete",
            "Opinion",
            "Invalid",
            "Won't Fix",
            "Expired",
            "Confirmed",
            "Triaged",
            "In Progress",
            "Fix Committed",
            "Fix Released",
            "Does Not Exist",
        ]
        assert expected == LaunchpadDataPoint.CSV_HEADERS

    def test_to_csv_row(self):
        """Test converting to CSV row."""
        point = LaunchpadDataPoint(
            timestamp="2024-Jan-01 12:00:00",
            new=5,
            incomplete=3,
            opinion=1,
            invalid=2,
            wont_fix=0,
            expired=0,
            confirmed=10,
            triaged=8,
            in_progress=4,
            fix_committed=2,
            fix_released=100,
            does_not_exist=0,
        )

        row = point.to_csv_row()

        assert row[0] == "2024-Jan-01 12:00:00"
        assert row[1] == "5"  # new
        assert row[7] == "10"  # confirmed
        assert row[11] == "100"  # fix_released

    def test_save_and_load_roundtrip(self, tmp_path):
        """Test saving and loading data maintains integrity."""
        csv_file = tmp_path / "launchpad.csv"
        data = [
            LaunchpadDataPoint(
                timestamp="2024-Jan-01 12:00:00",
                new=5,
                confirmed=10,
                fix_released=100,
            ),
            LaunchpadDataPoint(
                timestamp="2024-Jan-02 12:00:00",
                new=6,
                confirmed=11,
                fix_released=101,
            ),
        ]

        LaunchpadDataPoint.save_to_csv(data, csv_file)
        loaded = LaunchpadDataPoint.load_from_csv(csv_file)

        assert len(loaded) == 2
        assert loaded[0].timestamp == "2024-Jan-01 12:00:00"
        assert loaded[0].new == 5
        assert loaded[1].confirmed == 11

    def test_append_mode(self, tmp_path):
        """Test appending data to existing file."""
        csv_file = tmp_path / "launchpad.csv"

        data1 = [
            LaunchpadDataPoint(timestamp="2024-Jan-01 12:00:00", new=5),
        ]
        LaunchpadDataPoint.save_to_csv(data1, csv_file)

        data2 = [
            LaunchpadDataPoint(timestamp="2024-Jan-02 12:00:00", new=6),
        ]
        LaunchpadDataPoint.save_to_csv(data2, csv_file, append=True)

        loaded = LaunchpadDataPoint.load_from_csv(csv_file)
        assert len(loaded) == 2
        assert loaded[0].new == 5
        assert loaded[1].new == 6

    def test_save_csv_format(self, tmp_path):
        """Test CSV file format is correct."""
        csv_file = tmp_path / "launchpad.csv"
        data = [
            LaunchpadDataPoint(
                timestamp="2024-Jan-01 12:00:00",
                new=1,
                incomplete=2,
                opinion=3,
                invalid=4,
                wont_fix=5,
                expired=6,
                confirmed=7,
                triaged=8,
                in_progress=9,
                fix_committed=10,
                fix_released=11,
                does_not_exist=12,
            ),
        ]

        LaunchpadDataPoint.save_to_csv(data, csv_file)
        content = csv_file.read_text()

        lines = content.strip().split("\n")
        assert "timestamp" in lines[0]
        assert "New" in lines[0]
        assert "Fix Released" in lines[0]
        assert lines[1] == "2024-Jan-01 12:00:00,1,2,3,4,5,6,7,8,9,10,11,12"
