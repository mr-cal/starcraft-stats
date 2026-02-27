"""Tests for ReleaseBranchInfo CSV model."""

from starcraft_stats.models.releases import ReleaseBranchInfo


class TestReleaseBranchInfo:
    """Tests for ReleaseBranchInfo model."""

    def test_create_branch_info(self):
        """Test creating branch info."""
        info = ReleaseBranchInfo(
            app="snapcraft",
            branch="main",
            latest_tag="8.14.0",
            commits_since_tag=57,
        )

        assert info.app == "snapcraft"
        assert info.branch == "main"
        assert info.latest_tag == "8.14.0"
        assert info.commits_since_tag == 57

    def test_csv_headers(self):
        """Test CSV headers are defined correctly."""
        expected = ["app", "branch", "latest tag", "commits since tag"]
        assert expected == ReleaseBranchInfo.CSV_HEADERS

    def test_to_csv_row(self):
        """Test converting to CSV row."""
        info = ReleaseBranchInfo(
            app="charmcraft",
            branch="hotfix/4.1",
            latest_tag="4.1.0",
            commits_since_tag=0,
        )

        row = info.to_csv_row()

        assert row == ["charmcraft", "hotfix/4.1", "4.1.0", "0"]

    def test_save_and_load_roundtrip(self, tmp_path):
        """Test saving and loading data maintains integrity."""
        csv_file = tmp_path / "releases.csv"
        data = [
            ReleaseBranchInfo(
                app="snapcraft",
                branch="main",
                latest_tag="8.14.0",
                commits_since_tag=57,
            ),
            ReleaseBranchInfo(
                app="charmcraft",
                branch="main",
                latest_tag="4.1.0",
                commits_since_tag=18,
            ),
        ]

        ReleaseBranchInfo.save_to_csv(data, csv_file)
        loaded = ReleaseBranchInfo.load_from_csv(csv_file)

        assert len(loaded) == 2
        assert loaded[0].app == "snapcraft"
        assert loaded[0].commits_since_tag == 57
        assert loaded[1].app == "charmcraft"

    def test_save_csv_format(self, tmp_path):
        """Test CSV file format is correct."""
        csv_file = tmp_path / "releases.csv"
        data = [
            ReleaseBranchInfo(
                app="rockcraft",
                branch="main",
                latest_tag="1.17.0",
                commits_since_tag=5,
            ),
        ]

        ReleaseBranchInfo.save_to_csv(data, csv_file)
        content = csv_file.read_text()

        lines = content.strip().split("\n")
        assert lines[0] == "app,branch,latest tag,commits since tag"
        assert lines[1] == "rockcraft,main,1.17.0,5"

    def test_zero_commits_since_tag(self):
        """Test handling zero commits since tag."""
        info = ReleaseBranchInfo(
            app="imagecraft",
            branch="hotfix/1.0",
            latest_tag="1.0.0",
            commits_since_tag=0,
        )

        assert info.commits_since_tag == 0
        row = info.to_csv_row()
        assert row[3] == "0"
