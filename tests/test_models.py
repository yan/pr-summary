"""
Tests for data models.
"""

from datetime import datetime, timezone

import pytest

from src.models import CheckRun, Commit, FileChange, PRActivity, PRComment, Review


class TestCommit:
    """Tests for Commit model."""

    def test_commit_creation(self, sample_datetime):
        """Test creating a Commit instance."""
        commit = Commit(
            sha="abc123",
            message="Add feature",
            author="testuser",
            author_email="test@example.com",
            timestamp=sample_datetime,
            url="https://github.com/owner/repo/commit/abc123",
        )

        assert commit.sha == "abc123"
        assert commit.message == "Add feature"
        assert commit.author == "testuser"
        assert commit.timestamp == sample_datetime


class TestPRComment:
    """Tests for PRComment model."""

    def test_conversation_comment(self, sample_datetime):
        """Test creating a conversation comment."""
        comment = PRComment(
            id=1,
            author="testuser",
            created_at=sample_datetime,
            updated_at=None,
            body="Great work!",
            comment_type="conversation",
            url="https://github.com/owner/repo/pull/123#issuecomment-1",
        )

        assert comment.comment_type == "conversation"
        assert comment.file_path is None
        assert comment.line_number is None

    def test_inline_comment(self, sample_datetime):
        """Test creating an inline code review comment."""
        comment = PRComment(
            id=2,
            author="reviewer",
            created_at=sample_datetime,
            updated_at=None,
            body="Consider refactoring this",
            comment_type="inline",
            url="https://github.com/owner/repo/pull/123#discussion_r2",
            file_path="src/main.py",
            line_number=42,
            diff_hunk="@@ -40,3 +40,5 @@",
        )

        assert comment.comment_type == "inline"
        assert comment.file_path == "src/main.py"
        assert comment.line_number == 42


class TestReview:
    """Tests for Review model."""

    def test_approved_review(self, sample_datetime):
        """Test creating an approved review."""
        review = Review(
            id=100,
            author="reviewer",
            state="APPROVED",
            submitted_at=sample_datetime,
            body="LGTM",
            url="https://github.com/owner/repo/pull/123#pullrequestreview-100",
        )

        assert review.state == "APPROVED"
        assert review.body == "LGTM"

    def test_changes_requested_review(self, sample_datetime):
        """Test creating a changes requested review."""
        review = Review(
            id=101,
            author="reviewer",
            state="CHANGES_REQUESTED",
            submitted_at=sample_datetime,
            body="Please address comments",
            url="https://github.com/owner/repo/pull/123#pullrequestreview-101",
        )

        assert review.state == "CHANGES_REQUESTED"


class TestCheckRun:
    """Tests for CheckRun model."""

    def test_successful_check(self, sample_datetime):
        """Test creating a successful check run."""
        check = CheckRun(
            id=1000,
            name="Tests",
            status="completed",
            conclusion="success",
            started_at=sample_datetime,
            completed_at=datetime(2025, 10, 14, 10, 35, 0, tzinfo=timezone.utc),
            html_url="https://github.com/owner/repo/runs/1000",
        )

        assert check.conclusion == "success"
        assert check.duration_seconds == 300.0  # 5 minutes

    def test_failed_check(self, sample_datetime):
        """Test creating a failed check run."""
        check = CheckRun(
            id=1001,
            name="Lint",
            status="completed",
            conclusion="failure",
            started_at=sample_datetime,
            completed_at=sample_datetime,
            html_url="https://github.com/owner/repo/runs/1001",
        )

        assert check.conclusion == "failure"

    def test_check_duration_none(self, sample_datetime):
        """Test duration calculation when not completed."""
        check = CheckRun(
            id=1002,
            name="Build",
            status="in_progress",
            conclusion=None,
            started_at=sample_datetime,
            completed_at=None,
            html_url="https://github.com/owner/repo/runs/1002",
        )

        assert check.duration_seconds is None


class TestFileChange:
    """Tests for FileChange model."""

    def test_modified_file(self):
        """Test creating a modified file change."""
        file_change = FileChange(
            filename="src/main.py",
            status="modified",
            additions=10,
            deletions=5,
            changes=15,
        )

        assert file_change.status == "modified"
        assert file_change.additions == 10
        assert file_change.deletions == 5

    def test_renamed_file(self):
        """Test creating a renamed file change."""
        file_change = FileChange(
            filename="new_name.py",
            status="renamed",
            additions=0,
            deletions=0,
            changes=0,
            previous_filename="old_name.py",
        )

        assert file_change.status == "renamed"
        assert file_change.previous_filename == "old_name.py"


class TestPRActivity:
    """Tests for PRActivity model."""

    def test_pr_activity_creation(self, sample_datetime):
        """Test creating a PRActivity instance."""
        commits = [
            Commit(
                sha="abc123",
                message="Fix bug",
                author="testuser",
                author_email="test@example.com",
                timestamp=sample_datetime,
                url="https://github.com/owner/repo/commit/abc123",
            )
        ]

        comments = [
            PRComment(
                id=1,
                author="reviewer",
                created_at=sample_datetime,
                updated_at=None,
                body="Looks good",
                comment_type="conversation",
                url="https://github.com/owner/repo/pull/123#issuecomment-1",
            )
        ]

        reviews = [
            Review(
                id=100,
                author="reviewer",
                state="APPROVED",
                submitted_at=sample_datetime,
                body="LGTM",
                url="https://github.com/owner/repo/pull/123#pullrequestreview-100",
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

        activity = PRActivity(
            number=123,
            title="Test PR",
            author="testuser",
            author_avatar_url="https://github.com/testuser.png",
            state="merged",
            base_branch="main",
            head_branch="feature/test",
            base_repo="owner/repo",
            head_repo="owner/repo",
            created_at=sample_datetime,
            updated_at=sample_datetime,
            closed_at=sample_datetime,
            merged_at=sample_datetime,
            merge_commit_sha="merge123",
            merged_by="maintainer",
            description="Test description",
            labels=["bug", "priority"],
            linked_issues=[45],
            closes_issues=[45],
            commits=commits,
            comments=comments,
            reviews=reviews,
            check_runs=[],
            file_changes=file_changes,
            html_url="https://github.com/owner/repo/pull/123",
        )

        assert activity.number == 123
        assert activity.title == "Test PR"
        assert len(activity.commits) == 1
        assert len(activity.comments) == 1
        assert len(activity.reviews) == 1

    def test_pr_activity_computed_stats(self, sample_datetime):
        """Test PRActivity computed statistics."""
        file_changes = [
            FileChange(
                filename="file1.py", status="modified", additions=10, deletions=5, changes=15
            ),
            FileChange(
                filename="file2.py", status="added", additions=20, deletions=0, changes=20
            ),
        ]

        activity = PRActivity(
            number=123,
            title="Test",
            author="user1",
            author_avatar_url="url",
            state="merged",
            base_branch="main",
            head_branch="feature",
            base_repo="owner/repo",
            head_repo="owner/repo",
            created_at=sample_datetime,
            updated_at=sample_datetime,
            closed_at=sample_datetime,
            merged_at=sample_datetime,
            merge_commit_sha="abc123",
            merged_by="user2",
            description="",
            labels=[],
            linked_issues=[],
            closes_issues=[],
            commits=[],
            comments=[],
            reviews=[],
            check_runs=[],
            file_changes=file_changes,
            html_url="url",
        )

        assert activity.total_additions == 30
        assert activity.total_deletions == 5
        assert activity.files_changed_count == 2

    def test_pr_activity_participants(self, sample_datetime):
        """Test PRActivity participants calculation."""
        commits = [
            Commit(
                sha="abc", message="msg", author="user1", author_email="email",
                timestamp=sample_datetime, url="url"
            ),
            Commit(
                sha="def", message="msg", author="user2", author_email="email",
                timestamp=sample_datetime, url="url"
            ),
        ]

        comments = [
            PRComment(
                id=1, author="user3", created_at=sample_datetime, updated_at=None,
                body="comment", comment_type="conversation", url="url"
            ),
        ]

        activity = PRActivity(
            number=123,
            title="Test",
            author="user1",
            author_avatar_url="url",
            state="merged",
            base_branch="main",
            head_branch="feature",
            base_repo="owner/repo",
            head_repo="owner/repo",
            created_at=sample_datetime,
            updated_at=sample_datetime,
            closed_at=sample_datetime,
            merged_at=sample_datetime,
            merge_commit_sha="abc123",
            merged_by="user4",
            description="",
            labels=[],
            linked_issues=[],
            closes_issues=[],
            commits=commits,
            comments=comments,
            reviews=[],
            check_runs=[],
            file_changes=[],
            html_url="url",
        )

        # Should include author, commit authors, comment authors, and merged_by
        assert set(activity.participants) == {"user1", "user2", "user3", "user4"}

    def test_is_merged_property(self, sample_datetime):
        """Test is_merged property."""
        merged_activity = PRActivity(
            number=123,
            title="Test",
            author="user",
            author_avatar_url="url",
            state="merged",
            base_branch="main",
            head_branch="feature",
            base_repo="owner/repo",
            head_repo="owner/repo",
            created_at=sample_datetime,
            updated_at=sample_datetime,
            closed_at=sample_datetime,
            merged_at=sample_datetime,
            merge_commit_sha="abc123",
            merged_by="user",
            description="",
            labels=[],
            linked_issues=[],
            closes_issues=[],
            commits=[],
            comments=[],
            reviews=[],
            check_runs=[],
            file_changes=[],
            html_url="url",
        )

        closed_activity = PRActivity(
            number=124,
            title="Test",
            author="user",
            author_avatar_url="url",
            state="closed",
            base_branch="main",
            head_branch="feature",
            base_repo="owner/repo",
            head_repo="owner/repo",
            created_at=sample_datetime,
            updated_at=sample_datetime,
            closed_at=sample_datetime,
            merged_at=None,
            merge_commit_sha=None,
            merged_by=None,
            description="",
            labels=[],
            linked_issues=[],
            closes_issues=[],
            commits=[],
            comments=[],
            reviews=[],
            check_runs=[],
            file_changes=[],
            html_url="url",
        )

        assert merged_activity.is_merged is True
        assert closed_activity.is_merged is False

    def test_filter_properties(self, sample_datetime):
        """Test filtering properties for comments, reviews, and checks."""
        comments = [
            PRComment(
                id=1, author="user1", created_at=sample_datetime, updated_at=None,
                body="conv", comment_type="conversation", url="url"
            ),
            PRComment(
                id=2, author="user2", created_at=sample_datetime, updated_at=None,
                body="inline", comment_type="inline", url="url", file_path="file.py", line_number=10
            ),
        ]

        reviews = [
            Review(
                id=100, author="user3", state="APPROVED", submitted_at=sample_datetime,
                body="approved", url="url"
            ),
            Review(
                id=101, author="user4", state="CHANGES_REQUESTED", submitted_at=sample_datetime,
                body="changes", url="url"
            ),
        ]

        checks = [
            CheckRun(
                id=1000, name="test1", status="completed", conclusion="success",
                started_at=sample_datetime, completed_at=sample_datetime, html_url="url"
            ),
            CheckRun(
                id=1001, name="test2", status="completed", conclusion="failure",
                started_at=sample_datetime, completed_at=sample_datetime, html_url="url"
            ),
        ]

        activity = PRActivity(
            number=123,
            title="Test",
            author="user",
            author_avatar_url="url",
            state="merged",
            base_branch="main",
            head_branch="feature",
            base_repo="owner/repo",
            head_repo="owner/repo",
            created_at=sample_datetime,
            updated_at=sample_datetime,
            closed_at=sample_datetime,
            merged_at=sample_datetime,
            merge_commit_sha="abc123",
            merged_by="user",
            description="",
            labels=[],
            linked_issues=[],
            closes_issues=[],
            commits=[],
            comments=comments,
            reviews=reviews,
            check_runs=checks,
            file_changes=[],
            html_url="url",
        )

        assert len(activity.conversation_comments) == 1
        assert len(activity.review_comments) == 1
        assert len(activity.approved_reviews) == 1
        assert len(activity.changes_requested_reviews) == 1
        assert len(activity.successful_checks) == 1
        assert len(activity.failed_checks) == 1
