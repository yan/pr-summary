"""
Pytest configuration and shared fixtures.
"""

from datetime import datetime, timezone
from typing import Any

import pytest


@pytest.fixture
def sample_datetime() -> datetime:
    """Provide a sample datetime for testing."""
    return datetime(2025, 10, 14, 10, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_pr_data() -> dict[str, Any]:
    """Mock GitHub API PR data."""
    return {
        "number": 123,
        "title": "Add dark mode support",
        "state": "closed",
        "user": {
            "login": "testuser",
            "avatar_url": "https://github.com/testuser.png",
        },
        "body": "This PR adds dark mode support.\n\nCloses #45",
        "labels": [
            {"name": "enhancement"},
            {"name": "ui"},
        ],
        "base": {
            "ref": "main",
            "repo": {"full_name": "owner/repo"},
        },
        "head": {
            "ref": "feature/dark-mode",
            "repo": {"full_name": "owner/repo"},
        },
        "created_at": "2025-10-14T10:00:00Z",
        "updated_at": "2025-10-14T15:30:00Z",
        "closed_at": "2025-10-14T15:30:00Z",
        "merged_at": "2025-10-14T15:30:00Z",
        "merge_commit_sha": "abc123def456",
        "merged_by": {"login": "maintainer"},
        "html_url": "https://github.com/owner/repo/pull/123",
        "diff_url": "https://github.com/owner/repo/pull/123.diff",
        "patch_url": "https://github.com/owner/repo/pull/123.patch",
    }


@pytest.fixture
def mock_commits_data() -> list[dict[str, Any]]:
    """Mock GitHub API commits data."""
    return [
        {
            "sha": "abc123",
            "commit": {
                "message": "Add dark mode CSS variables",
                "author": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "date": "2025-10-14T10:15:00Z",
                },
            },
            "html_url": "https://github.com/owner/repo/commit/abc123",
        },
        {
            "sha": "def456",
            "commit": {
                "message": "Update components for dark mode",
                "author": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "date": "2025-10-14T11:00:00Z",
                },
            },
            "html_url": "https://github.com/owner/repo/commit/def456",
        },
    ]


@pytest.fixture
def mock_files_data() -> list[dict[str, Any]]:
    """Mock GitHub API files data."""
    return [
        {
            "filename": "styles/theme.css",
            "status": "modified",
            "additions": 50,
            "deletions": 10,
            "changes": 60,
            "patch": "@@ -1,5 +1,10 @@\n+:root {\n+  --bg-color: white;\n+}",
        },
        {
            "filename": "components/Button.tsx",
            "status": "modified",
            "additions": 15,
            "deletions": 5,
            "changes": 20,
        },
        {
            "filename": "README.md",
            "status": "modified",
            "additions": 3,
            "deletions": 0,
            "changes": 3,
        },
    ]


@pytest.fixture
def mock_issue_comments_data() -> list[dict[str, Any]]:
    """Mock GitHub API issue comments (conversation comments)."""
    return [
        {
            "id": 1,
            "user": {"login": "reviewer1"},
            "body": "This looks great! Could you add tests?",
            "created_at": "2025-10-14T12:00:00Z",
            "updated_at": "2025-10-14T12:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/123#issuecomment-1",
        },
        {
            "id": 2,
            "user": {"login": "testuser"},
            "body": "Added tests in latest commit!",
            "created_at": "2025-10-14T13:00:00Z",
            "updated_at": "2025-10-14T13:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/123#issuecomment-2",
        },
    ]


@pytest.fixture
def mock_review_comments_data() -> list[dict[str, Any]]:
    """Mock GitHub API review comments (inline code comments)."""
    return [
        {
            "id": 10,
            "user": {"login": "reviewer1"},
            "body": "Consider using CSS variables here",
            "path": "styles/theme.css",
            "line": 42,
            "diff_hunk": "@@ -40,3 +40,5 @@",
            "created_at": "2025-10-14T12:30:00Z",
            "updated_at": "2025-10-14T12:30:00Z",
            "html_url": "https://github.com/owner/repo/pull/123#discussion_r10",
            "in_reply_to_id": None,
        },
    ]


@pytest.fixture
def mock_reviews_data() -> list[dict[str, Any]]:
    """Mock GitHub API reviews data."""
    return [
        {
            "id": 100,
            "user": {"login": "reviewer1"},
            "state": "APPROVED",
            "body": "LGTM! Great work",
            "submitted_at": "2025-10-14T14:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/123#pullrequestreview-100",
            "commit_id": "def456",
        },
        {
            "id": 101,
            "user": {"login": "reviewer2"},
            "state": "COMMENTED",
            "body": "Looks good overall",
            "submitted_at": "2025-10-14T14:30:00Z",
            "html_url": "https://github.com/owner/repo/pull/123#pullrequestreview-101",
            "commit_id": "def456",
        },
    ]


@pytest.fixture
def mock_check_runs_data() -> dict[str, Any]:
    """Mock GitHub API check runs data."""
    return {
        "check_runs": [
            {
                "id": 1000,
                "name": "Unit Tests",
                "status": "completed",
                "conclusion": "success",
                "started_at": "2025-10-14T15:00:00Z",
                "completed_at": "2025-10-14T15:05:00Z",
                "html_url": "https://github.com/owner/repo/runs/1000",
                "app": {"name": "GitHub Actions"},
            },
            {
                "id": 1001,
                "name": "Build",
                "status": "completed",
                "conclusion": "success",
                "started_at": "2025-10-14T15:00:00Z",
                "completed_at": "2025-10-14T15:10:00Z",
                "html_url": "https://github.com/owner/repo/runs/1001",
                "app": {"name": "GitHub Actions"},
            },
            {
                "id": 1002,
                "name": "Lint",
                "status": "completed",
                "conclusion": "failure",
                "started_at": "2025-10-14T15:00:00Z",
                "completed_at": "2025-10-14T15:02:00Z",
                "html_url": "https://github.com/owner/repo/runs/1002",
                "app": {"name": "GitHub Actions"},
            },
        ]
    }


@pytest.fixture
def mock_repo_data() -> dict[str, Any]:
    """Mock GitHub API repository data."""
    return {
        "name": "repo",
        "full_name": "owner/repo",
        "owner": {"login": "owner"},
        "description": "A test repository",
        "html_url": "https://github.com/owner/repo",
    }
