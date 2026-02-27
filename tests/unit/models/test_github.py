"""Tests for GitHub models."""

from datetime import UTC, datetime

from starcraft_stats.models.github import (
    GithubIssue,
    GithubIssues,
    IntermediateData,
    IntermediateDataPoint,
    Projects,
)
from starcraft_stats.models.issues import IssueDataPoint


class TestGithubIssue:
    """Tests for GithubIssue model."""

    def test_create_issue(self):
        """Test creating a GitHub issue."""
        opened = datetime(2024, 1, 1, tzinfo=UTC)
        closed = datetime(2024, 1, 15, tzinfo=UTC)
        refreshed = datetime(2024, 2, 1, tzinfo=UTC)

        issue = GithubIssue(
            type="issue",
            date_opened=opened,
            date_closed=closed,
            refresh_date=refreshed,
        )

        assert issue.type == "issue"
        assert issue.date_opened == opened
        assert issue.date_closed == closed
        assert issue.refresh_date == refreshed

    def test_create_pr(self):
        """Test creating a pull request."""
        opened = datetime(2024, 1, 1, tzinfo=UTC)
        refreshed = datetime(2024, 2, 1, tzinfo=UTC)

        pr = GithubIssue(
            type="pr",
            date_opened=opened,
            date_closed=None,
            refresh_date=refreshed,
        )

        assert pr.type == "pr"
        assert pr.date_closed is None
        assert pr.refresh_date == refreshed

    def test_str_with_closed_issue(self):
        """Test string representation of closed issue."""
        opened = datetime(2024, 1, 1, tzinfo=UTC)
        closed = datetime(2024, 1, 15, tzinfo=UTC)
        refreshed = datetime(2024, 2, 1, tzinfo=UTC)

        issue = GithubIssue(
            type="issue",
            date_opened=opened,
            date_closed=closed,
            refresh_date=refreshed,
        )

        result = str(issue)
        assert "type: issue" in result
        assert "opened: 2024-01-01" in result
        assert "closed: 2024-01-15" in result

    def test_str_with_open_issue(self):
        """Test string representation of open issue."""
        opened = datetime(2024, 1, 1, tzinfo=UTC)
        refreshed = datetime(2024, 2, 1, tzinfo=UTC)

        issue = GithubIssue(
            type="issue",
            date_opened=opened,
            date_closed=None,
            refresh_date=refreshed,
        )

        result = str(issue)
        assert "type: issue" in result
        assert "opened: 2024-01-01" in result
        assert "closed" not in result

    def test_is_open_before_opened(self):
        """Test is_open returns False before issue was opened."""
        opened = datetime(2024, 1, 15, tzinfo=UTC)
        check_date = datetime(2024, 1, 1, tzinfo=UTC)
        refreshed = datetime(2024, 2, 1, tzinfo=UTC)

        issue = GithubIssue(
            type="issue",
            date_opened=opened,
            date_closed=None,
            refresh_date=refreshed,
        )

        assert not issue.is_open(check_date)

    def test_is_open_while_open(self):
        """Test is_open returns True while issue is open."""
        opened = datetime(2024, 1, 1, tzinfo=UTC)
        check_date = datetime(2024, 1, 15, tzinfo=UTC)
        refreshed = datetime(2024, 2, 1, tzinfo=UTC)

        issue = GithubIssue(
            type="issue",
            date_opened=opened,
            date_closed=None,
            refresh_date=refreshed,
        )

        assert issue.is_open(check_date)

    def test_is_open_after_closed(self):
        """Test is_open returns False after issue was closed."""
        opened = datetime(2024, 1, 1, tzinfo=UTC)
        closed = datetime(2024, 1, 15, tzinfo=UTC)
        check_date = datetime(2024, 2, 1, tzinfo=UTC)
        refreshed = datetime(2024, 2, 1, tzinfo=UTC)

        issue = GithubIssue(
            type="issue",
            date_opened=opened,
            date_closed=closed,
            refresh_date=refreshed,
        )

        assert not issue.is_open(check_date)

    def test_is_open_on_close_date(self):
        """Test is_open returns False on exact close date."""
        opened = datetime(2024, 1, 1, tzinfo=UTC)
        closed = datetime(2024, 1, 15, tzinfo=UTC)
        refreshed = datetime(2024, 2, 1, tzinfo=UTC)

        issue = GithubIssue(
            type="issue",
            date_opened=opened,
            date_closed=closed,
            refresh_date=refreshed,
        )

        assert not issue.is_open(closed)


class TestGithubIssues:
    """Tests for GithubIssues collection model."""

    def test_create_empty_collection(self):
        """Test creating an empty issues collection."""
        issues = GithubIssues()

        assert issues.issues == {}

    def test_create_with_issues(self):
        """Test creating collection with issues."""
        opened = datetime(2024, 1, 1, tzinfo=UTC)
        refreshed = datetime(2024, 2, 1, tzinfo=UTC)
        issue1 = GithubIssue(
            type="issue", date_opened=opened, date_closed=None, refresh_date=refreshed
        )
        issue2 = GithubIssue(
            type="pr", date_opened=opened, date_closed=None, refresh_date=refreshed
        )

        issues = GithubIssues(issues={1: issue1, 2: issue2})

        assert len(issues.issues) == 2
        assert issues.issues[1].type == "issue"
        assert issues.issues[2].type == "pr"

    def test_add_issue_to_collection(self):
        """Test adding issues to collection."""
        issues = GithubIssues()
        opened = datetime(2024, 1, 1, tzinfo=UTC)
        refreshed = datetime(2024, 2, 1, tzinfo=UTC)

        issues.issues[1] = GithubIssue(
            type="issue",
            date_opened=opened,
            date_closed=None,
            refresh_date=refreshed,
        )

        assert len(issues.issues) == 1
        assert 1 in issues.issues


class TestProjects:
    """Tests for Projects collection model."""

    def test_create_empty_projects(self):
        """Test creating empty projects collection."""
        projects = Projects()

        assert projects.projects == {}

    def test_create_with_projects(self):
        """Test creating collection with projects."""
        opened = datetime(2024, 1, 1, tzinfo=UTC)
        refreshed = datetime(2024, 2, 1, tzinfo=UTC)
        issue = GithubIssue(
            type="issue",
            date_opened=opened,
            date_closed=None,
            refresh_date=refreshed,
        )
        issues1 = GithubIssues(issues={1: issue})
        issues2 = GithubIssues()

        projects = Projects(projects={"project1": issues1, "project2": issues2})

        assert len(projects.projects) == 2
        assert "project1" in projects.projects
        assert "project2" in projects.projects
        assert len(projects.projects["project1"].issues) == 1


class TestIntermediateDataPoint:
    """Tests for IntermediateDataPoint model."""

    def test_create_datapoint_with_all_fields(self):
        """Test creating datapoint with all fields."""
        point = IntermediateDataPoint(
            date="2024-Jan-01",
            open_issues=10,
            open_issues_avg=12,
            mean_age=30,
        )

        assert point.date == "2024-Jan-01"
        assert point.open_issues == 10
        assert point.open_issues_avg == 12
        assert point.mean_age == 30

    def test_create_datapoint_minimal(self):
        """Test creating datapoint with minimal fields."""
        point = IntermediateDataPoint(
            date="2024-Jan-01",
            open_issues=10,
            mean_age=None,
        )

        assert point.date == "2024-Jan-01"
        assert point.open_issues == 10
        assert point.open_issues_avg is None
        assert point.mean_age is None


class TestIntermediateData:
    """Tests for IntermediateData collection model."""

    def test_create_empty_data(self):
        """Test creating empty intermediate data."""
        data = IntermediateData()

        assert data.data == []

    def test_create_with_datapoints(self):
        """Test creating with datapoints."""
        points = [
            IntermediateDataPoint(date="2024-Jan-01", open_issues=10, mean_age=30),
            IntermediateDataPoint(date="2024-Jan-02", open_issues=12, mean_age=32),
        ]

        data = IntermediateData(data=points)

        assert len(data.data) == 2
        assert data.data[0].open_issues == 10
        assert data.data[1].open_issues == 12

    def test_to_csv_models_converts_correctly(self):
        """Test converting intermediate data to CSV models."""
        points = [
            IntermediateDataPoint(
                date="2024-Jan-01",
                open_issues=10,
                open_issues_avg=11,
                mean_age=30,
            ),
            IntermediateDataPoint(
                date="2024-Jan-02",
                open_issues=12,
                open_issues_avg=13,
                mean_age=32,
            ),
        ]
        data = IntermediateData(data=points)

        csv_models = data.to_csv_models()

        assert len(csv_models) == 2
        assert isinstance(csv_models[0], IssueDataPoint)
        assert csv_models[0].date == "2024-Jan-01"
        assert csv_models[0].issues == 10
        assert csv_models[0].issues_avg == 11
        assert csv_models[0].age == 30

    def test_to_csv_models_handles_none_values(self):
        """Test converting data with None values."""
        points = [
            IntermediateDataPoint(
                date="2024-Jan-01",
                open_issues=10,
                open_issues_avg=None,
                mean_age=None,
            ),
        ]
        data = IntermediateData(data=points)

        csv_models = data.to_csv_models()

        assert csv_models[0].issues_avg is None
        assert csv_models[0].age is None
