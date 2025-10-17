"""
Data models for PR activity tracking.

All models use dataclasses with full type annotations for type safety.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal


@dataclass
class Commit:
    """Represents a single commit in a PR."""

    sha: str
    message: str
    author: str
    author_email: str
    timestamp: datetime
    url: str


@dataclass
class PRComment:
    """Represents a comment in a PR (conversation, review, or inline code comment)."""

    id: int
    author: str
    created_at: datetime
    updated_at: Optional[datetime]
    body: str
    comment_type: Literal["conversation", "review", "inline"]
    url: str

    # For inline code comments
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    diff_hunk: Optional[str] = None

    # For review comments
    in_reply_to_id: Optional[int] = None


@dataclass
class Review:
    """Represents a PR review (approval, changes requested, or comment-only)."""

    id: int
    author: str
    state: Literal["APPROVED", "CHANGES_REQUESTED", "COMMENTED", "DISMISSED", "PENDING"]
    submitted_at: Optional[datetime]
    body: Optional[str]
    url: str
    commit_sha: Optional[str] = None


@dataclass
class CheckRun:
    """Represents a CI/CD check run or status check."""

    id: int
    name: str
    status: Literal["queued", "in_progress", "completed"]
    conclusion: Optional[Literal["success", "failure", "neutral", "cancelled", "skipped", "timed_out", "action_required"]]
    started_at: datetime
    completed_at: Optional[datetime]
    html_url: str
    app_name: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate duration of the check run in seconds."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class FileChange:
    """Represents changes to a single file in the PR."""

    filename: str
    status: Literal["added", "removed", "modified", "renamed"]
    additions: int
    deletions: int
    changes: int
    patch: Optional[str] = None
    previous_filename: Optional[str] = None  # For renamed files


@dataclass
class PRActivity:
    """Complete PR activity data including all metadata, comments, reviews, and checks."""

    # Basic metadata
    number: int
    title: str
    author: str
    author_avatar_url: str
    state: Literal["open", "closed", "merged"]

    # Branch information
    base_branch: str
    head_branch: str
    base_repo: str
    head_repo: str

    # Timestamps
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    merged_at: Optional[datetime]

    # Merge information
    merge_commit_sha: Optional[str]
    merged_by: Optional[str]

    # Content
    description: str
    labels: list[str]

    # Related issues
    linked_issues: list[int]
    closes_issues: list[int]

    # Activity data
    commits: list[Commit]
    comments: list[PRComment]
    reviews: list[Review]
    check_runs: list[CheckRun]
    file_changes: list[FileChange]

    # Statistics
    total_additions: int = 0
    total_deletions: int = 0
    files_changed_count: int = 0

    # Participants (unique users involved)
    participants: list[str] = field(default_factory=list)

    # URLs
    html_url: str = ""
    diff_url: str = ""
    patch_url: str = ""

    def __post_init__(self) -> None:
        """Calculate derived fields after initialization."""
        # Calculate file statistics
        self.total_additions = sum(fc.additions for fc in self.file_changes)
        self.total_deletions = sum(fc.deletions for fc in self.file_changes)
        self.files_changed_count = len(self.file_changes)

        # Calculate unique participants
        participants_set = {self.author}
        participants_set.update(commit.author for commit in self.commits)
        participants_set.update(comment.author for comment in self.comments)
        participants_set.update(review.author for review in self.reviews)
        if self.merged_by:
            participants_set.add(self.merged_by)

        self.participants = sorted(participants_set)

    @property
    def is_merged(self) -> bool:
        """Check if the PR was merged."""
        return self.merged_at is not None

    @property
    def conversation_comments(self) -> list[PRComment]:
        """Get only conversation-level comments."""
        return [c for c in self.comments if c.comment_type == "conversation"]

    @property
    def review_comments(self) -> list[PRComment]:
        """Get only review comments (inline code comments)."""
        return [c for c in self.comments if c.comment_type in ("review", "inline")]

    @property
    def approved_reviews(self) -> list[Review]:
        """Get only approved reviews."""
        return [r for r in self.reviews if r.state == "APPROVED"]

    @property
    def changes_requested_reviews(self) -> list[Review]:
        """Get only reviews that requested changes."""
        return [r for r in self.reviews if r.state == "CHANGES_REQUESTED"]

    @property
    def successful_checks(self) -> list[CheckRun]:
        """Get only successful check runs."""
        return [c for c in self.check_runs if c.conclusion == "success"]

    @property
    def failed_checks(self) -> list[CheckRun]:
        """Get only failed check runs."""
        return [c for c in self.check_runs if c.conclusion == "failure"]


@dataclass
class GitHubRepository:
    """Represents a GitHub repository."""

    owner: str
    name: str
    full_name: str

    @property
    def slug(self) -> str:
        """Return the repository slug (owner/name)."""
        return f"{self.owner}/{self.name}"
