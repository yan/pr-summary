"""
Tests for summary formatter.
"""

from datetime import datetime, timezone

import pytest

from src.formatter import SummaryFormatter
from src.models import CheckRun, Commit, FileChange, PRActivity, PRComment, Review


@pytest.fixture
def sample_pr_activity(sample_datetime):
    """Create a sample PRActivity for testing."""
    commits = [
        Commit(
            sha="abc123",
            message="Add dark mode CSS",
            author="testuser",
            author_email="test@example.com",
            timestamp=sample_datetime,
            url="https://github.com/owner/repo/commit/abc123",
        )
    ]

    comments = [
        PRComment(
            id=1,
            author="reviewer1",
            created_at=sample_datetime,
            updated_at=None,
            body="Great work!",
            comment_type="conversation",
            url="https://github.com/owner/repo/pull/123#issuecomment-1",
        ),
        PRComment(
            id=2,
            author="reviewer2",
            created_at=sample_datetime,
            updated_at=None,
            body="Consider refactoring",
            comment_type="inline",
            url="https://github.com/owner/repo/pull/123#discussion_r2",
            file_path="src/main.py",
            line_number=42,
        ),
    ]

    reviews = [
        Review(
            id=100,
            author="reviewer1",
            state="APPROVED",
            submitted_at=sample_datetime,
            body="LGTM",
            url="https://github.com/owner/repo/pull/123#pullrequestreview-100",
        )
    ]

    checks = [
        CheckRun(
            id=1000,
            name="Tests",
            status="completed",
            conclusion="success",
            started_at=sample_datetime,
            completed_at=datetime(2025, 10, 14, 10, 35, 0, tzinfo=timezone.utc),
            html_url="https://github.com/owner/repo/runs/1000",
        )
    ]

    file_changes = [
        FileChange(
            filename="src/main.py",
            status="modified",
            additions=10,
            deletions=5,
            changes=15,
        )
    ]

    return PRActivity(
        number=123,
        title="Add dark mode",
        author="testuser",
        author_avatar_url="https://github.com/testuser.png",
        state="merged",
        base_branch="main",
        head_branch="feature/dark-mode",
        base_repo="owner/repo",
        head_repo="owner/repo",
        created_at=sample_datetime,
        updated_at=sample_datetime,
        closed_at=sample_datetime,
        merged_at=sample_datetime,
        merge_commit_sha="merge123",
        merged_by="maintainer",
        description="This PR adds dark mode support",
        labels=["enhancement"],
        linked_issues=[45],
        closes_issues=[45],
        commits=commits,
        comments=comments,
        reviews=reviews,
        check_runs=checks,
        file_changes=file_changes,
        html_url="https://github.com/owner/repo/pull/123",
    )


class TestSummaryFormatter:
    """Tests for SummaryFormatter."""

    def test_format_complete_summary(self, sample_pr_activity):
        """Test formatting a complete PR summary."""
        formatter = SummaryFormatter()
        summary = formatter.format(sample_pr_activity)

        # Check header
        assert "# 🟣 PR #123: Add dark mode" in summary

        # Check metadata
        assert "**Author:** @testuser" in summary
        assert "**Merged:** 2025-10-14" in summary
        assert "**Labels:** `enhancement`" in summary

        # Check description
        assert "This PR adds dark mode support" in summary

        # Check commits
        assert "## Commits (1)" in summary
        assert "abc123" in summary

        # Check reviews
        assert "## Reviews (1)" in summary
        assert "✅ @reviewer1" in summary

        # Check discussion
        assert "## Discussion (2 comments)" in summary
        assert "Great work!" in summary

        # Check checks
        assert "## Checks (1)" in summary
        assert "✅" in summary

        # Check footer
        assert "Summary generated for PR #123" in summary

    def test_format_header_merged(self, sample_pr_activity):
        """Test header formatting for merged PR."""
        formatter = SummaryFormatter()
        header = formatter._format_header(sample_pr_activity)

        assert "🟣" in header
        assert "PR #123" in header
        assert "Add dark mode" in header

    def test_format_header_closed(self, sample_pr_activity):
        """Test header formatting for closed PR."""
        sample_pr_activity.state = "closed"
        sample_pr_activity.merged_at = None

        formatter = SummaryFormatter()
        header = formatter._format_header(sample_pr_activity)

        assert "🔴" in header

    def test_format_metadata(self, sample_pr_activity):
        """Test metadata formatting."""
        formatter = SummaryFormatter()
        metadata = formatter._format_metadata(sample_pr_activity)

        assert "@testuser" in metadata
        assert "`main`" in metadata
        assert "`feature/dark-mode`" in metadata
        assert "`enhancement`" in metadata
        assert "#45" in metadata

    def test_format_commits(self, sample_pr_activity):
        """Test commits formatting."""
        formatter = SummaryFormatter()
        commits_section = formatter._format_commits(sample_pr_activity)

        assert "## Commits (1)" in commits_section
        assert "`abc123`" in commits_section
        assert "Add dark mode CSS" in commits_section
        assert "@testuser" in commits_section

    def test_format_file_changes(self, sample_pr_activity):
        """Test file changes formatting."""
        formatter = SummaryFormatter()
        files_section = formatter._format_file_changes(sample_pr_activity)

        assert "## File Changes (1)" in files_section
        assert "**Total changes:** +10 -5" in files_section
        assert "src/main.py" in files_section

    def test_format_file_changes_by_status(self, sample_pr_activity):
        """Test file changes grouped by status."""
        sample_pr_activity.file_changes = [
            FileChange(filename="new.py", status="added", additions=20, deletions=0, changes=20),
            FileChange(filename="old.py", status="removed", additions=0, deletions=30, changes=30),
            FileChange(
                filename="renamed.py",
                status="renamed",
                additions=0,
                deletions=0,
                changes=0,
                previous_filename="old_name.py",
            ),
        ]

        formatter = SummaryFormatter()
        files_section = formatter._format_file_changes(sample_pr_activity)

        assert "### Added (1)" in files_section
        assert "### Removed (1)" in files_section
        assert "### Renamed (1)" in files_section

    def test_format_reviews(self, sample_pr_activity):
        """Test reviews formatting."""
        formatter = SummaryFormatter()
        reviews_section = formatter._format_reviews(sample_pr_activity)

        assert "## Reviews (1)" in reviews_section
        assert "### Approved (1)" in reviews_section
        assert "✅ @reviewer1" in reviews_section

    def test_format_reviews_with_changes_requested(self, sample_pr_activity):
        """Test formatting reviews with changes requested."""
        sample_pr_activity.reviews.append(
            Review(
                id=101,
                author="reviewer2",
                state="CHANGES_REQUESTED",
                submitted_at=sample_pr_activity.created_at,
                body="Please fix",
                url="url",
            )
        )

        formatter = SummaryFormatter()
        reviews_section = formatter._format_reviews(sample_pr_activity)

        assert "### Changes Requested (1)" in reviews_section
        assert "⚠️ @reviewer2" in reviews_section

    def test_format_discussion(self, sample_pr_activity):
        """Test discussion formatting."""
        formatter = SummaryFormatter()
        discussion_section = formatter._format_discussion(sample_pr_activity)

        assert "## Discussion (2 comments)" in discussion_section
        assert "### Conversation (1)" in discussion_section
        assert "### Code Review Comments (1)" in discussion_section
        assert "@reviewer1" in discussion_section
        assert "Great work!" in discussion_section
        assert "`src/main.py:42`" in discussion_section

    def test_format_checks(self, sample_pr_activity):
        """Test checks formatting."""
        formatter = SummaryFormatter()
        checks_section = formatter._format_checks(sample_pr_activity)

        assert "## Checks (1)" in checks_section
        assert "### Successful (1)" in checks_section
        assert "✅" in checks_section
        assert "Tests" in checks_section
        assert "(300.0s)" in checks_section  # Duration

    def test_format_checks_with_failures(self, sample_pr_activity):
        """Test formatting checks with failures."""
        sample_pr_activity.check_runs.append(
            CheckRun(
                id=1001,
                name="Lint",
                status="completed",
                conclusion="failure",
                started_at=sample_pr_activity.created_at,
                completed_at=sample_pr_activity.created_at,
                html_url="url",
            )
        )

        formatter = SummaryFormatter()
        checks_section = formatter._format_checks(sample_pr_activity)

        assert "### Failed (1)" in checks_section
        assert "❌" in checks_section

    def test_truncate_long_comment(self, sample_pr_activity):
        """Test comment truncation."""
        long_comment = "a" * 1000
        sample_pr_activity.comments[0].body = long_comment

        formatter = SummaryFormatter(max_comment_length=100)
        discussion_section = formatter._format_discussion(sample_pr_activity)

        # Should be truncated with "..."
        assert "..." in discussion_section
        assert len(discussion_section.split("Great")[0]) < 1000

    def test_empty_sections_not_included(self, sample_pr_activity):
        """Test that empty sections are not included."""
        sample_pr_activity.reviews = []
        sample_pr_activity.check_runs = []

        formatter = SummaryFormatter()
        summary = formatter.format(sample_pr_activity)

        assert "## Reviews" not in summary
        assert "## Checks" not in summary

    def test_format_footer(self, sample_pr_activity):
        """Test footer formatting."""
        formatter = SummaryFormatter()
        footer = formatter._format_footer(sample_pr_activity)

        assert "Summary generated for PR #123" in footer
        assert "1 commits" in footer
        assert "2 comments" in footer
        assert "1 reviews" in footer
        assert "1 checks" in footer
