"""
Markdown summary formatter for PR activity.

Transforms PRActivity data into human-readable markdown summaries.
"""

from datetime import datetime
from typing import Optional

from .models import CheckRun, Commit, FileChange, PRActivity, PRComment, Review


class SummaryFormatter:
    """Formats PR activity data into markdown summaries."""

    def __init__(self, include_patches: bool = False, max_comment_length: int = 500):
        """
        Initialize formatter.

        Args:
            include_patches: Whether to include file patches in the summary
            max_comment_length: Maximum length for comment bodies before truncation
        """
        self.include_patches = include_patches
        self.max_comment_length = max_comment_length

    def format(self, activity: PRActivity) -> str:
        """
        Format complete PR activity summary.

        Args:
            activity: PR activity data

        Returns:
            Formatted markdown summary
        """
        sections = [
            self._format_header(activity),
            self._format_metadata(activity),
            self._format_description(activity),
            self._format_commits(activity),
            self._format_file_changes(activity),
            self._format_reviews(activity),
            self._format_discussion(activity),
            self._format_checks(activity),
            self._format_footer(activity),
        ]

        # Filter out empty sections and join with double newlines
        return "\n\n".join(section for section in sections if section.strip())

    def _format_header(self, activity: PRActivity) -> str:
        """Format PR header with title and basic info."""
        state_emoji = {
            "merged": "🟣",
            "closed": "🔴",
            "open": "🟢",
        }.get(activity.state, "⚪")

        return f"# {state_emoji} PR #{activity.number}: {activity.title}"

    def _format_metadata(self, activity: PRActivity) -> str:
        """Format PR metadata section."""
        lines = [
            "## Metadata",
            "",
            f"- **Author:** @{activity.author}",
            f"- **Base:** `{activity.base_branch}` ← **Head:** `{activity.head_branch}`",
            f"- **Created:** {self._format_datetime(activity.created_at)}",
        ]

        if activity.merged_at:
            lines.append(f"- **Merged:** {self._format_datetime(activity.merged_at)} by @{activity.merged_by}")
        elif activity.closed_at:
            lines.append(f"- **Closed:** {self._format_datetime(activity.closed_at)}")

        if activity.labels:
            labels_str = ", ".join(f"`{label}`" for label in activity.labels)
            lines.append(f"- **Labels:** {labels_str}")

        if activity.linked_issues:
            issues_str = ", ".join(f"#{issue}" for issue in activity.linked_issues)
            lines.append(f"- **Linked Issues:** {issues_str}")

        if activity.closes_issues:
            closes_str = ", ".join(f"#{issue}" for issue in activity.closes_issues)
            lines.append(f"- **Closes:** {closes_str}")

        lines.append(f"- **Participants:** {', '.join(f'@{p}' for p in activity.participants)}")
        lines.append(f"- **URL:** {activity.html_url}")

        return "\n".join(lines)

    def _format_description(self, activity: PRActivity) -> str:
        """Format PR description."""
        if not activity.description.strip():
            return ""

        return f"## Description\n\n{activity.description}"

    def _format_commits(self, activity: PRActivity) -> str:
        """Format commits section."""
        if not activity.commits:
            return ""

        lines = [
            f"## Commits ({len(activity.commits)})",
            "",
        ]

        for commit in activity.commits:
            # Get first line of commit message
            first_line = commit.message.split("\n")[0]
            if len(first_line) > 80:
                first_line = first_line[:77] + "..."

            lines.append(f"- [`{commit.sha[:7]}`]({commit.url}) {first_line} - @{commit.author}")

        return "\n".join(lines)

    def _format_file_changes(self, activity: PRActivity) -> str:
        """Format file changes section."""
        if not activity.file_changes:
            return ""

        lines = [
            f"## File Changes ({activity.files_changed_count})",
            "",
            f"**Total changes:** +{activity.total_additions} -{activity.total_deletions}",
            "",
        ]

        # Group files by status
        added = [f for f in activity.file_changes if f.status == "added"]
        modified = [f for f in activity.file_changes if f.status == "modified"]
        removed = [f for f in activity.file_changes if f.status == "removed"]
        renamed = [f for f in activity.file_changes if f.status == "renamed"]

        if added:
            lines.append(f"### Added ({len(added)})")
            lines.append("")
            for file in added:
                lines.append(f"- `{file.filename}` (+{file.additions})")
            lines.append("")

        if modified:
            lines.append(f"### Modified ({len(modified)})")
            lines.append("")
            for file in modified:
                lines.append(f"- `{file.filename}` (+{file.additions} -{file.deletions})")
            lines.append("")

        if removed:
            lines.append(f"### Removed ({len(removed)})")
            lines.append("")
            for file in removed:
                lines.append(f"- `{file.filename}` (-{file.deletions})")
            lines.append("")

        if renamed:
            lines.append(f"### Renamed ({len(renamed)})")
            lines.append("")
            for file in renamed:
                old = file.previous_filename or "unknown"
                lines.append(f"- `{old}` → `{file.filename}`")
            lines.append("")

        return "\n".join(lines).rstrip()

    def _format_reviews(self, activity: PRActivity) -> str:
        """Format reviews section."""
        if not activity.reviews:
            return ""

        lines = [
            f"## Reviews ({len(activity.reviews)})",
            "",
        ]

        # Group reviews by state
        approved = activity.approved_reviews
        changes_requested = activity.changes_requested_reviews
        commented = [r for r in activity.reviews if r.state == "COMMENTED"]

        if approved:
            lines.append(f"### Approved ({len(approved)})")
            lines.append("")
            for review in approved:
                timestamp = self._format_datetime(review.submitted_at)
                lines.append(f"- ✅ @{review.author} ({timestamp})")
                if review.body:
                    body = self._truncate(review.body)
                    lines.append(f"  > {body}")
            lines.append("")

        if changes_requested:
            lines.append(f"### Changes Requested ({len(changes_requested)})")
            lines.append("")
            for review in changes_requested:
                timestamp = self._format_datetime(review.submitted_at)
                lines.append(f"- ⚠️ @{review.author} ({timestamp})")
                if review.body:
                    body = self._truncate(review.body)
                    lines.append(f"  > {body}")
            lines.append("")

        if commented:
            lines.append(f"### Commented ({len(commented)})")
            lines.append("")
            for review in commented:
                timestamp = self._format_datetime(review.submitted_at)
                lines.append(f"- 💬 @{review.author} ({timestamp})")
                if review.body:
                    body = self._truncate(review.body)
                    lines.append(f"  > {body}")
            lines.append("")

        return "\n".join(lines).rstrip()

    def _format_discussion(self, activity: PRActivity) -> str:
        """Format discussion (comments) section."""
        if not activity.comments:
            return ""

        conversation = activity.conversation_comments
        review_comments = activity.review_comments

        lines = [
            f"## Discussion ({len(activity.comments)} comments)",
            "",
        ]

        if conversation:
            lines.append(f"### Conversation ({len(conversation)})")
            lines.append("")
            for comment in conversation:
                timestamp = self._format_datetime(comment.created_at)
                body = self._truncate(comment.body)
                lines.append(f"**@{comment.author}** ({timestamp})")
                lines.append(f"> {body}")
                lines.append("")

        if review_comments:
            lines.append(f"### Code Review Comments ({len(review_comments)})")
            lines.append("")
            for comment in review_comments:
                timestamp = self._format_datetime(comment.created_at)
                body = self._truncate(comment.body)
                location = f"`{comment.file_path}:{comment.line_number}`" if comment.file_path else "code"
                lines.append(f"**@{comment.author}** on {location} ({timestamp})")
                lines.append(f"> {body}")
                lines.append("")

        return "\n".join(lines).rstrip()

    def _format_checks(self, activity: PRActivity) -> str:
        """Format CI/CD checks section."""
        if not activity.check_runs:
            return ""

        lines = [
            f"## Checks ({len(activity.check_runs)})",
            "",
        ]

        # Group by conclusion
        successful = activity.successful_checks
        failed = activity.failed_checks
        other = [
            c
            for c in activity.check_runs
            if c.conclusion not in ("success", "failure") or c.conclusion is None
        ]

        def format_check(check: CheckRun) -> str:
            emoji = {
                "success": "✅",
                "failure": "❌",
                "neutral": "⚪",
                "cancelled": "🚫",
                "skipped": "⏭️",
                "timed_out": "⏱️",
                "action_required": "⚠️",
            }.get(check.conclusion or "", "🔵")

            duration = f" ({check.duration_seconds:.1f}s)" if check.duration_seconds else ""
            app = f" [{check.app_name}]" if check.app_name else ""
            return f"- {emoji} [{check.name}]({check.html_url}){app}{duration}"

        if successful:
            lines.append(f"### Successful ({len(successful)})")
            lines.append("")
            for check in successful:
                lines.append(format_check(check))
            lines.append("")

        if failed:
            lines.append(f"### Failed ({len(failed)})")
            lines.append("")
            for check in failed:
                lines.append(format_check(check))
            lines.append("")

        if other:
            lines.append(f"### Other ({len(other)})")
            lines.append("")
            for check in other:
                lines.append(format_check(check))
            lines.append("")

        return "\n".join(lines).rstrip()

    def _format_footer(self, activity: PRActivity) -> str:
        """Format footer with summary statistics."""
        return (
            "---\n\n"
            f"*Summary generated for PR #{activity.number} • "
            f"{len(activity.commits)} commits • "
            f"{len(activity.comments)} comments • "
            f"{len(activity.reviews)} reviews • "
            f"{len(activity.check_runs)} checks • "
            f"{activity.files_changed_count} files changed*"
        )

    def _format_datetime(self, dt: Optional[datetime]) -> str:
        """Format datetime in a human-readable way."""
        if not dt:
            return "unknown"
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    def _truncate(self, text: str) -> str:
        """Truncate text to max length and clean up formatting."""
        # Replace newlines with spaces for inline display
        text = " ".join(text.split())

        if len(text) <= self.max_comment_length:
            return text

        return text[: self.max_comment_length - 3] + "..."
