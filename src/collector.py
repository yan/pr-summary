"""
PR activity data collection and transformation.

Orchestrates fetching data from GitHub API and transforms it into typed models.
"""

import logging
import re
from datetime import datetime
from typing import Any, Optional

from .github_client import GitHubClient
from .models import (
    CheckRun,
    Commit,
    FileChange,
    PRActivity,
    PRComment,
    Review,
)


logger = logging.getLogger(__name__)


class PRActivityCollector:
    """Collects and transforms PR activity data from GitHub API."""

    def __init__(self, client: GitHubClient):
        """
        Initialize collector with GitHub API client.

        Args:
            client: Configured GitHubClient instance
        """
        self.client = client

    def collect_all_activity(self, pr_number: int) -> PRActivity:
        """
        Collect all activity data for a PR.

        Args:
            pr_number: Pull request number

        Returns:
            Complete PRActivity with all data populated

        Raises:
            GitHubAPIError: If API requests fail
        """
        logger.info(f"Collecting activity for PR #{pr_number}")

        # Fetch base PR data
        pr_data = self.client.get_pull_request(pr_number)

        # Collect all activity data in parallel would be ideal, but we'll do it sequentially
        logger.info("Fetching commits...")
        commits = self._collect_commits(pr_number)

        logger.info("Fetching file changes...")
        file_changes = self._collect_file_changes(pr_number)

        logger.info("Fetching comments...")
        comments = self._collect_comments(pr_number)

        logger.info("Fetching reviews...")
        reviews = self._collect_reviews(pr_number)

        logger.info("Fetching check runs...")
        check_runs = []
        if pr_data.get("merge_commit_sha"):
            check_runs = self._collect_check_runs(pr_data["merge_commit_sha"])

        logger.info("Extracting linked issues...")
        linked_issues, closes_issues = self._extract_linked_issues(pr_data)

        # Build PRActivity object
        activity = PRActivity(
            number=pr_data["number"],
            title=pr_data["title"],
            author=pr_data["user"]["login"],
            author_avatar_url=pr_data["user"]["avatar_url"],
            state="merged" if pr_data.get("merged_at") else pr_data["state"],
            base_branch=pr_data["base"]["ref"],
            head_branch=pr_data["head"]["ref"],
            base_repo=pr_data["base"]["repo"]["full_name"],
            head_repo=pr_data["head"]["repo"]["full_name"] if pr_data["head"]["repo"] else "unknown",
            created_at=self._parse_datetime(pr_data["created_at"]),
            updated_at=self._parse_datetime(pr_data["updated_at"]),
            closed_at=self._parse_datetime(pr_data.get("closed_at")),
            merged_at=self._parse_datetime(pr_data.get("merged_at")),
            merge_commit_sha=pr_data.get("merge_commit_sha"),
            merged_by=pr_data["merged_by"]["login"] if pr_data.get("merged_by") else None,
            description=pr_data.get("body") or "",
            labels=[label["name"] for label in pr_data.get("labels", [])],
            linked_issues=linked_issues,
            closes_issues=closes_issues,
            commits=commits,
            comments=comments,
            reviews=reviews,
            check_runs=check_runs,
            file_changes=file_changes,
            html_url=pr_data["html_url"],
            diff_url=pr_data["diff_url"],
            patch_url=pr_data["patch_url"],
        )

        logger.info(
            f"Collected PR #{pr_number}: "
            f"{len(commits)} commits, "
            f"{len(comments)} comments, "
            f"{len(reviews)} reviews, "
            f"{len(check_runs)} checks, "
            f"{len(file_changes)} files changed"
        )

        return activity

    def _collect_commits(self, pr_number: int) -> list[Commit]:
        """Collect and transform commits."""
        commits_data = self.client.get_pr_commits(pr_number)

        commits = []
        for commit_data in commits_data:
            commit = Commit(
                sha=commit_data["sha"],
                message=commit_data["commit"]["message"],
                author=commit_data["commit"]["author"]["name"],
                author_email=commit_data["commit"]["author"]["email"],
                timestamp=self._parse_datetime(commit_data["commit"]["author"]["date"]),
                url=commit_data["html_url"],
            )
            commits.append(commit)

        return commits

    def _collect_file_changes(self, pr_number: int) -> list[FileChange]:
        """Collect and transform file changes."""
        files_data = self.client.get_pr_files(pr_number)

        file_changes = []
        for file_data in files_data:
            file_change = FileChange(
                filename=file_data["filename"],
                status=file_data["status"],
                additions=file_data["additions"],
                deletions=file_data["deletions"],
                changes=file_data["changes"],
                patch=file_data.get("patch"),
                previous_filename=file_data.get("previous_filename"),
            )
            file_changes.append(file_change)

        return file_changes

    def _collect_comments(self, pr_number: int) -> list[PRComment]:
        """Collect and transform all comments (conversation + review)."""
        comments = []

        # Get conversation comments (issue comments)
        issue_comments = self.client.get_issue_comments(pr_number)
        for comment_data in issue_comments:
            comment = PRComment(
                id=comment_data["id"],
                author=comment_data["user"]["login"],
                created_at=self._parse_datetime(comment_data["created_at"]),
                updated_at=self._parse_datetime(comment_data.get("updated_at")),
                body=comment_data["body"],
                comment_type="conversation",
                url=comment_data["html_url"],
            )
            comments.append(comment)

        # Get review comments (inline code comments)
        review_comments = self.client.get_pr_comments(pr_number)
        for comment_data in review_comments:
            comment = PRComment(
                id=comment_data["id"],
                author=comment_data["user"]["login"],
                created_at=self._parse_datetime(comment_data["created_at"]),
                updated_at=self._parse_datetime(comment_data.get("updated_at")),
                body=comment_data["body"],
                comment_type="inline",
                url=comment_data["html_url"],
                file_path=comment_data.get("path"),
                line_number=comment_data.get("line") or comment_data.get("original_line"),
                diff_hunk=comment_data.get("diff_hunk"),
                in_reply_to_id=comment_data.get("in_reply_to_id"),
            )
            comments.append(comment)

        # Sort by creation time
        comments.sort(key=lambda c: c.created_at)

        return comments

    def _collect_reviews(self, pr_number: int) -> list[Review]:
        """Collect and transform PR reviews."""
        reviews_data = self.client.get_pr_reviews(pr_number)

        reviews = []
        for review_data in reviews_data:
            # Skip reviews without a state (shouldn't happen, but defensive)
            if not review_data.get("state"):
                continue

            review = Review(
                id=review_data["id"],
                author=review_data["user"]["login"],
                state=review_data["state"],
                submitted_at=self._parse_datetime(review_data.get("submitted_at")),
                body=review_data.get("body"),
                url=review_data["html_url"],
                commit_sha=review_data.get("commit_id"),
            )
            reviews.append(review)

        # Sort by submission time
        reviews.sort(key=lambda r: r.submitted_at or datetime.min)

        return reviews

    def _collect_check_runs(self, ref: str) -> list[CheckRun]:
        """Collect and transform check runs for a commit."""
        try:
            check_runs_data = self.client.get_check_runs(ref)
        except Exception as e:
            logger.warning(f"Failed to fetch check runs for {ref}: {e}")
            return []

        check_runs = []
        for check_data in check_runs_data:
            check_run = CheckRun(
                id=check_data["id"],
                name=check_data["name"],
                status=check_data["status"],
                conclusion=check_data.get("conclusion"),
                started_at=self._parse_datetime(check_data["started_at"]),
                completed_at=self._parse_datetime(check_data.get("completed_at")),
                html_url=check_data["html_url"],
                app_name=check_data.get("app", {}).get("name"),
            )
            check_runs.append(check_run)

        return check_runs

    def _extract_linked_issues(self, pr_data: dict[str, Any]) -> tuple[list[int], list[int]]:
        """
        Extract linked and closing issue numbers from PR body.

        Args:
            pr_data: PR data from API

        Returns:
            Tuple of (all_linked_issues, closing_issues)
        """
        body = pr_data.get("body") or ""

        # Patterns for issue references
        # Matches: #123, owner/repo#123
        reference_pattern = r"(?:^|[\s(])(?:[\w-]+/[\w-]+)?#(\d+)"

        # Patterns for closing keywords
        # Matches: closes #123, fixes #123, resolves #123, etc.
        closing_pattern = r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)"

        # Find all issue references
        all_refs = re.findall(reference_pattern, body, re.IGNORECASE | re.MULTILINE)
        linked_issues = [int(num) for num in all_refs]

        # Find closing references
        closing_refs = re.findall(closing_pattern, body, re.IGNORECASE | re.MULTILINE)
        closes_issues = [int(num) for num in closing_refs]

        return sorted(set(linked_issues)), sorted(set(closes_issues))

    @staticmethod
    def _parse_datetime(dt_string: Optional[str]) -> Optional[datetime]:
        """
        Parse ISO 8601 datetime string from GitHub API.

        Args:
            dt_string: ISO 8601 datetime string or None

        Returns:
            Parsed datetime or None
        """
        if not dt_string:
            return None

        # GitHub returns ISO 8601 with Z suffix
        # Python 3.11+ can handle this natively
        return datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
