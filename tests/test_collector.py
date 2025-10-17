"""
Tests for PR activity collector.
"""

from unittest.mock import Mock, patch

import pytest

from src.collector import PRActivityCollector
from src.github_client import GitHubClient


@pytest.fixture
def mock_github_client(
    mock_pr_data,
    mock_commits_data,
    mock_files_data,
    mock_issue_comments_data,
    mock_review_comments_data,
    mock_reviews_data,
    mock_check_runs_data,
):
    """Create a mock GitHub client with preset responses."""
    client = Mock(spec=GitHubClient)
    client.get_pull_request.return_value = mock_pr_data
    client.get_pr_commits.return_value = mock_commits_data
    client.get_pr_files.return_value = mock_files_data
    client.get_issue_comments.return_value = mock_issue_comments_data
    client.get_pr_comments.return_value = mock_review_comments_data
    client.get_pr_reviews.return_value = mock_reviews_data
    client.get_check_runs.return_value = mock_check_runs_data["check_runs"]
    return client


class TestPRActivityCollector:
    """Tests for PRActivityCollector."""

    def test_collect_all_activity(self, mock_github_client):
        """Test collecting complete PR activity."""
        collector = PRActivityCollector(mock_github_client)
        activity = collector.collect_all_activity(123)

        # Verify PR metadata
        assert activity.number == 123
        assert activity.title == "Add dark mode support"
        assert activity.author == "testuser"
        assert activity.state == "merged"

        # Verify data collection
        assert len(activity.commits) == 2
        assert len(activity.file_changes) == 3
        assert len(activity.comments) == 3  # 2 conversation + 1 review comment
        assert len(activity.reviews) == 2
        assert len(activity.check_runs) == 3

        # Verify statistics calculation
        assert activity.total_additions == 68  # 50 + 15 + 3
        assert activity.total_deletions == 15  # 10 + 5 + 0
        assert activity.files_changed_count == 3

        # Verify participants
        assert "testuser" in activity.participants
        assert "maintainer" in activity.participants

    def test_collect_commits(self, mock_github_client):
        """Test commit collection and transformation."""
        collector = PRActivityCollector(mock_github_client)
        commits = collector._collect_commits(123)

        assert len(commits) == 2
        assert commits[0].sha == "abc123"
        assert commits[0].message == "Add dark mode CSS variables"
        assert commits[0].author == "Test User"
        assert commits[0].author_email == "test@example.com"

    def test_collect_file_changes(self, mock_github_client):
        """Test file changes collection."""
        collector = PRActivityCollector(mock_github_client)
        files = collector._collect_file_changes(123)

        assert len(files) == 3
        assert files[0].filename == "styles/theme.css"
        assert files[0].status == "modified"
        assert files[0].additions == 50
        assert files[0].deletions == 10

    def test_collect_comments(self, mock_github_client):
        """Test comments collection (conversation + review)."""
        collector = PRActivityCollector(mock_github_client)
        comments = collector._collect_comments(123)

        # Should have 2 conversation + 1 review comment
        assert len(comments) == 3

        # Check conversation comments
        conversation_comments = [c for c in comments if c.comment_type == "conversation"]
        assert len(conversation_comments) == 2
        assert conversation_comments[0].author == "reviewer1"

        # Check review comments
        review_comments = [c for c in comments if c.comment_type == "inline"]
        assert len(review_comments) == 1
        assert review_comments[0].file_path == "styles/theme.css"
        assert review_comments[0].line_number == 42

    def test_collect_reviews(self, mock_github_client):
        """Test reviews collection."""
        collector = PRActivityCollector(mock_github_client)
        reviews = collector._collect_reviews(123)

        assert len(reviews) == 2
        assert reviews[0].state == "APPROVED"
        assert reviews[0].author == "reviewer1"
        assert reviews[1].state == "COMMENTED"

    def test_collect_check_runs(self, mock_github_client):
        """Test check runs collection."""
        collector = PRActivityCollector(mock_github_client)
        checks = collector._collect_check_runs("abc123")

        assert len(checks) == 3
        assert checks[0].name == "Unit Tests"
        assert checks[0].conclusion == "success"
        assert checks[2].conclusion == "failure"

    def test_collect_check_runs_failure(self, mock_github_client):
        """Test check runs collection with API failure."""
        mock_github_client.get_check_runs.side_effect = Exception("API Error")

        collector = PRActivityCollector(mock_github_client)
        checks = collector._collect_check_runs("abc123")

        # Should return empty list on failure
        assert checks == []

    def test_extract_linked_issues(self, mock_github_client, mock_pr_data):
        """Test linked issues extraction from PR body."""
        collector = PRActivityCollector(mock_github_client)

        # Test with closes keyword
        pr_data = {**mock_pr_data, "body": "This PR closes #45 and fixes #67"}
        linked, closes = collector._extract_linked_issues(pr_data)

        assert 45 in linked
        assert 67 in linked
        assert 45 in closes
        assert 67 in closes

    def test_extract_linked_issues_references(self, mock_github_client, mock_pr_data):
        """Test extracting issue references without closing keywords."""
        collector = PRActivityCollector(mock_github_client)

        pr_data = {**mock_pr_data, "body": "Related to #100 and #200"}
        linked, closes = collector._extract_linked_issues(pr_data)

        assert 100 in linked
        assert 200 in linked
        assert len(closes) == 0

    def test_extract_linked_issues_no_body(self, mock_github_client, mock_pr_data):
        """Test extraction with no PR body."""
        collector = PRActivityCollector(mock_github_client)

        pr_data = {**mock_pr_data, "body": None}
        linked, closes = collector._extract_linked_issues(pr_data)

        assert linked == []
        assert closes == []

    def test_parse_datetime(self, mock_github_client):
        """Test datetime parsing."""
        collector = PRActivityCollector(mock_github_client)

        # Test valid datetime
        dt = collector._parse_datetime("2025-10-14T10:30:00Z")
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 10
        assert dt.day == 14

        # Test None
        dt = collector._parse_datetime(None)
        assert dt is None

        # Test empty string
        dt = collector._parse_datetime("")
        assert dt is None
