"""
Git notes integration for storing PR summaries.

Handles creation and management of git notes attached to commits.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


class GitNotesError(Exception):
    """Base exception for git notes operations."""

    pass


class GitNotesManager:
    """Manages git notes for PR summaries."""

    def __init__(self, repo_path: str = ".", notes_ref: str = "refs/notes/pr-summary"):
        """
        Initialize git notes manager.

        Args:
            repo_path: Path to git repository
            notes_ref: Git notes ref namespace (default: refs/notes/pr-summary)
        """
        self.repo_path = Path(repo_path).resolve()
        self.notes_ref = notes_ref

        # Validate repository
        self._validate_repo()

    def _validate_repo(self) -> None:
        """Validate that repo_path is a git repository."""
        try:
            self._run_git_command(["git", "rev-parse", "--git-dir"])
        except GitNotesError as e:
            raise GitNotesError(f"Not a git repository: {self.repo_path}") from e

    def _run_git_command(
        self, cmd: list[str], input_data: Optional[str] = None, capture_stderr: bool = True
    ) -> str:
        """
        Run a git command and return output.

        Args:
            cmd: Command and arguments
            input_data: Optional stdin data
            capture_stderr: Whether to capture stderr

        Returns:
            Command stdout

        Raises:
            GitNotesError: If command fails
        """
        logger.debug(f"Running git command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                input=input_data.encode() if input_data else None,
                capture_output=True,
                check=True,
                timeout=30,
            )

            output = result.stdout.decode().strip()
            logger.debug(f"Git command output: {output[:200]}")

            return output

        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode().strip() if capture_stderr else ""
            error_msg = f"Git command failed: {' '.join(cmd)}\n{stderr}"
            logger.error(error_msg)
            raise GitNotesError(error_msg) from e

        except subprocess.TimeoutExpired as e:
            raise GitNotesError(f"Git command timeout: {' '.join(cmd)}") from e

    def add_note(self, commit_sha: str, content: str, force: bool = True) -> None:
        """
        Add a git note to a commit.

        Args:
            commit_sha: Commit SHA to attach note to
            content: Note content (markdown summary)
            force: Overwrite existing note if present

        Raises:
            GitNotesError: If adding note fails
        """
        logger.info(f"Adding git note to commit {commit_sha[:7]} in {self.notes_ref}")

        # Validate commit exists
        try:
            self._run_git_command(["git", "rev-parse", "--verify", commit_sha])
        except GitNotesError:
            raise GitNotesError(f"Commit not found: {commit_sha}")

        # Build git notes add command
        cmd = ["git", "notes", "--ref", self.notes_ref, "add"]

        if force:
            cmd.append("--force")

        cmd.extend(["-m", content, commit_sha])

        try:
            self._run_git_command(cmd)
            logger.info(f"Successfully added note to {commit_sha[:7]}")
        except GitNotesError as e:
            if "already exists" in str(e) and not force:
                raise GitNotesError(f"Note already exists for {commit_sha} (use force=True to overwrite)") from e
            raise

    def get_note(self, commit_sha: str) -> Optional[str]:
        """
        Get git note for a commit.

        Args:
            commit_sha: Commit SHA

        Returns:
            Note content or None if no note exists

        Raises:
            GitNotesError: If git operation fails (except for missing note)
        """
        logger.debug(f"Getting git note for commit {commit_sha[:7]}")

        cmd = ["git", "notes", "--ref", self.notes_ref, "show", commit_sha]

        try:
            return self._run_git_command(cmd)
        except GitNotesError as e:
            # Note doesn't exist - this is expected, not an error
            if "no note found" in str(e).lower():
                logger.debug(f"No note found for {commit_sha[:7]}")
                return None
            raise

    def remove_note(self, commit_sha: str) -> None:
        """
        Remove git note from a commit.

        Args:
            commit_sha: Commit SHA

        Raises:
            GitNotesError: If removing note fails
        """
        logger.info(f"Removing git note from commit {commit_sha[:7]}")

        cmd = ["git", "notes", "--ref", self.notes_ref, "remove", commit_sha]

        try:
            self._run_git_command(cmd)
        except GitNotesError as e:
            # Git can return either "no note found" or "has no note"
            if "no note" in str(e).lower():
                logger.warning(f"No note to remove for {commit_sha[:7]}")
            else:
                raise

    def list_notes(self) -> list[tuple[str, str]]:
        """
        List all notes in the namespace.

        Returns:
            List of (commit_sha, note_sha) tuples

        Raises:
            GitNotesError: If listing fails
        """
        logger.debug(f"Listing notes in {self.notes_ref}")

        cmd = ["git", "notes", "--ref", self.notes_ref, "list"]

        try:
            output = self._run_git_command(cmd)
        except GitNotesError as e:
            # Empty notes ref is ok
            if "not found" in str(e).lower():
                return []
            raise

        if not output:
            return []

        # Parse output: "note_sha commit_sha"
        notes = []
        for line in output.split("\n"):
            if line.strip():
                parts = line.split()
                if len(parts) == 2:
                    note_sha, commit_sha = parts
                    notes.append((commit_sha, note_sha))

        return notes

    def configure_git_user(self, name: str = "github-actions[bot]", email: str = "github-actions[bot]@users.noreply.github.com") -> None:
        """
        Configure git user for commits (needed for notes).

        Args:
            name: Git user name
            email: Git user email

        Raises:
            GitNotesError: If configuration fails
        """
        logger.info(f"Configuring git user: {name} <{email}>")

        self._run_git_command(["git", "config", "user.name", name])
        self._run_git_command(["git", "config", "user.email", email])

    def fetch_notes(self, remote: str = "origin") -> None:
        """
        Fetch notes from remote.

        Args:
            remote: Remote name

        Raises:
            GitNotesError: If fetch fails
        """
        logger.info(f"Fetching notes from {remote}")

        refspec = f"{self.notes_ref}:{self.notes_ref}"
        cmd = ["git", "fetch", remote, refspec]

        try:
            self._run_git_command(cmd)
            logger.info("Successfully fetched notes")
        except GitNotesError as e:
            # Notes ref might not exist on remote yet - that's ok
            if "couldn't find remote ref" in str(e).lower():
                logger.warning(f"Notes ref {self.notes_ref} doesn't exist on {remote} yet")
            else:
                raise

    def push_notes(self, remote: str = "origin", force: bool = False) -> None:
        """
        Push notes to remote.

        Fetches existing notes first to avoid conflicts, then pushes.

        Args:
            remote: Remote name
            force: Force push

        Raises:
            GitNotesError: If push fails
        """
        logger.info(f"Pushing notes to {remote}")

        # Fetch existing notes first to avoid conflicts
        try:
            logger.debug(f"Fetching existing notes from {remote} before push")
            self.fetch_notes(remote)
        except GitNotesError as e:
            # If fetch fails, log but continue - might be first push
            logger.debug(f"Could not fetch notes (might not exist yet): {e}")

        cmd = ["git", "push"]

        if force:
            cmd.append("--force")

        cmd.extend([remote, self.notes_ref])

        try:
            self._run_git_command(cmd)
            logger.info("Successfully pushed notes")
        except GitNotesError as e:
            raise GitNotesError(f"Failed to push notes: {e}") from e

    def merge_notes(self, strategy: str = "cat_sort_uniq") -> None:
        """
        Merge notes when conflicts occur.

        Args:
            strategy: Merge strategy (cat_sort_uniq, manual, union, etc.)

        Raises:
            GitNotesError: If merge fails
        """
        logger.info(f"Merging notes with strategy: {strategy}")

        cmd = ["git", "notes", "--ref", self.notes_ref, "merge", "-s", strategy, self.notes_ref]

        try:
            self._run_git_command(cmd)
            logger.info("Successfully merged notes")
        except GitNotesError as e:
            raise GitNotesError(f"Failed to merge notes: {e}") from e

    def get_notes_ref_sha(self) -> Optional[str]:
        """
        Get SHA of the notes ref.

        Returns:
            SHA of notes ref or None if doesn't exist

        Raises:
            GitNotesError: If git operation fails
        """
        cmd = ["git", "rev-parse", "--verify", self.notes_ref]

        try:
            return self._run_git_command(cmd)
        except GitNotesError:
            return None
