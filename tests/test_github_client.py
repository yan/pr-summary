"""
Tests for GitHub API client.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from src.github_client import (
    AuthenticationError,
    GitHubAPIError,
    GitHubClient,
    RateLimitError,
)


@pytest.fixture
def mock_response():
    """Create a mock response object."""
    response = Mock(spec=requests.Response)
    response.status_code = 200
    response.headers = {
        "X-RateLimit-Remaining": "5000",
        "X-RateLimit-Reset": "1234567890",
    }
    return response


@pytest.fixture
def github_client(mock_repo_data):
    """Create a GitHub client with mocked authentication."""
    with patch("src.github_client.GitHubClient._validate_auth"):
        client = GitHubClient(
            token="test_token",
            owner="owner",
            repo="repo",
        )
    return client


class TestGitHubClientInit:
    """Tests for GitHubClient initialization."""

    def test_client_initialization(self, mock_repo_data):
        """Test client initialization with valid auth."""
        with patch.object(GitHubClient, "_make_request", return_value=mock_repo_data):
            client = GitHubClient(
                token="test_token",
                owner="owner",
                repo="repo",
            )
            assert client.token == "test_token"
            assert client.owner == "owner"
            assert client.repo == "repo"

    def test_client_initialization_auth_failure(self):
        """Test client initialization with auth failure."""
        mock_response = Mock()
        mock_response.status_code = 401

        with patch("src.github_client.GitHubClient._create_session"):
            with patch.object(
                GitHubClient,
                "_make_request",
                side_effect=GitHubAPIError("Auth failed", status_code=401),
            ):
                with pytest.raises(AuthenticationError):
                    GitHubClient(token="bad_token", owner="owner", repo="repo")


class TestMakeRequest:
    """Tests for _make_request method."""

    def test_successful_request(self, github_client, mock_response):
        """Test successful API request."""
        mock_response.json.return_value = {"data": "value"}

        with patch.object(github_client.session, "request", return_value=mock_response):
            result = github_client._make_request("/test")
            assert result == {"data": "value"}

    def test_rate_limit_exceeded(self, github_client):
        """Test rate limit error handling."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1234567890",
        }
        mock_response.content = b'{"message": "rate limit exceeded"}'
        mock_response.json.return_value = {"message": "rate limit exceeded"}

        with patch.object(github_client.session, "request", return_value=mock_response):
            with pytest.raises(RateLimitError, match="Rate limit exceeded"):
                github_client._make_request("/test")

    def test_authentication_error(self, github_client):
        """Test authentication error handling."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.headers = {
            "X-RateLimit-Remaining": "5000",
        }

        with patch.object(github_client.session, "request", return_value=mock_response):
            with pytest.raises(AuthenticationError, match="Authentication failed"):
                github_client._make_request("/test")

    def test_timeout_error(self, github_client):
        """Test timeout error handling."""
        with patch.object(
            github_client.session,
            "request",
            side_effect=requests.exceptions.Timeout,
        ):
            with pytest.raises(GitHubAPIError, match="Request timeout"):
                github_client._make_request("/test")

    def test_http_error(self, github_client):
        """Test HTTP error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.headers = {
            "X-RateLimit-Remaining": "5000",
        }
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Server error")

        with patch.object(github_client.session, "request", return_value=mock_response):
            with pytest.raises(GitHubAPIError):
                github_client._make_request("/test")


class TestPagination:
    """Tests for pagination handling."""

    def test_paginate_single_page(self, github_client, mock_response):
        """Test pagination with single page of results."""
        mock_response.json.return_value = [{"id": 1}, {"id": 2}]

        with patch.object(github_client.session, "request", return_value=mock_response):
            results = github_client._paginate("/test")
            assert len(results) == 2
            assert results[0]["id"] == 1

    def test_paginate_multiple_pages(self, github_client):
        """Test pagination with multiple pages."""
        # First page returns 100 items, second page returns 50
        response1 = Mock()
        response1.status_code = 200
        response1.headers = {"X-RateLimit-Remaining": "5000"}
        response1.json.return_value = [{"id": i} for i in range(100)]

        response2 = Mock()
        response2.status_code = 200
        response2.headers = {"X-RateLimit-Remaining": "4999"}
        response2.json.return_value = [{"id": i} for i in range(100, 150)]

        with patch.object(
            github_client.session,
            "request",
            side_effect=[response1, response2],
        ):
            results = github_client._paginate("/test", per_page=100)
            assert len(results) == 150

    def test_paginate_empty_results(self, github_client, mock_response):
        """Test pagination with empty results."""
        mock_response.json.return_value = []

        with patch.object(github_client.session, "request", return_value=mock_response):
            results = github_client._paginate("/test")
            assert len(results) == 0


class TestPREndpoints:
    """Tests for PR-related endpoints."""

    def test_get_pull_request(self, github_client, mock_pr_data, mock_response):
        """Test getting PR metadata."""
        mock_response.json.return_value = mock_pr_data

        with patch.object(github_client.session, "request", return_value=mock_response):
            pr = github_client.get_pull_request(123)
            assert pr["number"] == 123
            assert pr["title"] == "Add dark mode support"

    def test_get_pr_commits(self, github_client, mock_commits_data, mock_response):
        """Test getting PR commits."""
        mock_response.json.return_value = mock_commits_data

        with patch.object(github_client.session, "request", return_value=mock_response):
            commits = github_client.get_pr_commits(123)
            assert len(commits) == 2
            assert commits[0]["sha"] == "abc123"

    def test_get_pr_files(self, github_client, mock_files_data, mock_response):
        """Test getting PR file changes."""
        mock_response.json.return_value = mock_files_data

        with patch.object(github_client.session, "request", return_value=mock_response):
            files = github_client.get_pr_files(123)
            assert len(files) == 3
            assert files[0]["filename"] == "styles/theme.css"

    def test_get_pr_comments(self, github_client, mock_review_comments_data, mock_response):
        """Test getting PR review comments."""
        mock_response.json.return_value = mock_review_comments_data

        with patch.object(github_client.session, "request", return_value=mock_response):
            comments = github_client.get_pr_comments(123)
            assert len(comments) == 1
            assert comments[0]["path"] == "styles/theme.css"

    def test_get_issue_comments(self, github_client, mock_issue_comments_data, mock_response):
        """Test getting issue (conversation) comments."""
        mock_response.json.return_value = mock_issue_comments_data

        with patch.object(github_client.session, "request", return_value=mock_response):
            comments = github_client.get_issue_comments(123)
            assert len(comments) == 2
            assert comments[0]["user"]["login"] == "reviewer1"

    def test_get_pr_reviews(self, github_client, mock_reviews_data, mock_response):
        """Test getting PR reviews."""
        mock_response.json.return_value = mock_reviews_data

        with patch.object(github_client.session, "request", return_value=mock_response):
            reviews = github_client.get_pr_reviews(123)
            assert len(reviews) == 2
            assert reviews[0]["state"] == "APPROVED"

    def test_get_check_runs(self, github_client, mock_check_runs_data, mock_response):
        """Test getting check runs."""
        mock_response.json.return_value = mock_check_runs_data

        with patch.object(github_client.session, "request", return_value=mock_response):
            checks = github_client.get_check_runs("abc123")
            assert len(checks) == 3
            assert checks[0]["name"] == "Unit Tests"


class TestRepositoryEndpoints:
    """Tests for repository-related endpoints."""

    def test_get_repository(self, github_client, mock_repo_data, mock_response):
        """Test getting repository metadata."""
        mock_response.json.return_value = mock_repo_data

        with patch.object(github_client.session, "request", return_value=mock_response):
            repo = github_client.get_repository()
            assert repo["full_name"] == "owner/repo"
            assert repo["name"] == "repo"
