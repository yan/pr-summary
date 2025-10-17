"""
Tests for git notes manager.
"""

import subprocess
from unittest.mock import Mock, patch

import pytest

from src.git_notes import GitNotesError, GitNotesManager


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    (repo_path / "test.txt").write_text("test")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


class TestGitNotesManagerInit:
    """Tests for GitNotesManager initialization."""

    def test_init_valid_repo(self, temp_git_repo):
        """Test initialization with valid git repository."""
        manager = GitNotesManager(repo_path=str(temp_git_repo))
        assert manager.repo_path == temp_git_repo
        assert manager.notes_ref == "refs/notes/pr-summary"

    def test_init_custom_notes_ref(self, temp_git_repo):
        """Test initialization with custom notes ref."""
        manager = GitNotesManager(
            repo_path=str(temp_git_repo),
            notes_ref="refs/notes/custom",
        )
        assert manager.notes_ref == "refs/notes/custom"

    def test_init_invalid_repo(self, tmp_path):
        """Test initialization with invalid repository."""
        non_repo = tmp_path / "not_a_repo"
        non_repo.mkdir()

        with pytest.raises(GitNotesError, match="Not a git repository"):
            GitNotesManager(repo_path=str(non_repo))


class TestAddNote:
    """Tests for adding git notes."""

    def test_add_note_success(self, temp_git_repo):
        """Test successfully adding a note."""
        manager = GitNotesManager(repo_path=str(temp_git_repo))

        # Get the commit SHA
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        commit_sha = result.stdout.strip()

        # Add note
        manager.add_note(commit_sha, "Test note content")

        # Verify note was added
        result = subprocess.run(
            ["git", "notes", "--ref", "refs/notes/pr-summary", "show", commit_sha],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        assert "Test note content" in result.stdout

    def test_add_note_force_overwrite(self, temp_git_repo):
        """Test overwriting existing note with force=True."""
        manager = GitNotesManager(repo_path=str(temp_git_repo))

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        commit_sha = result.stdout.strip()

        # Add initial note
        manager.add_note(commit_sha, "First note")

        # Overwrite with force
        manager.add_note(commit_sha, "Second note", force=True)

        # Verify note was overwritten
        result = subprocess.run(
            ["git", "notes", "--ref", "refs/notes/pr-summary", "show", commit_sha],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        assert "Second note" in result.stdout
        assert "First note" not in result.stdout

    def test_add_note_invalid_commit(self, temp_git_repo):
        """Test adding note to invalid commit SHA."""
        manager = GitNotesManager(repo_path=str(temp_git_repo))

        with pytest.raises(GitNotesError, match="Commit not found"):
            manager.add_note("invalid_sha", "Test note")


class TestGetNote:
    """Tests for getting git notes."""

    def test_get_existing_note(self, temp_git_repo):
        """Test getting an existing note."""
        manager = GitNotesManager(repo_path=str(temp_git_repo))

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        commit_sha = result.stdout.strip()

        manager.add_note(commit_sha, "Test note")

        note = manager.get_note(commit_sha)
        assert note == "Test note"

    def test_get_nonexistent_note(self, temp_git_repo):
        """Test getting a note that doesn't exist."""
        manager = GitNotesManager(repo_path=str(temp_git_repo))

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        commit_sha = result.stdout.strip()

        note = manager.get_note(commit_sha)
        assert note is None


class TestRemoveNote:
    """Tests for removing git notes."""

    def test_remove_existing_note(self, temp_git_repo):
        """Test removing an existing note."""
        manager = GitNotesManager(repo_path=str(temp_git_repo))

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        commit_sha = result.stdout.strip()

        # Add and then remove note
        manager.add_note(commit_sha, "Test note")
        manager.remove_note(commit_sha)

        # Verify note was removed
        note = manager.get_note(commit_sha)
        assert note is None

    def test_remove_nonexistent_note(self, temp_git_repo):
        """Test removing a note that doesn't exist."""
        manager = GitNotesManager(repo_path=str(temp_git_repo))

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        commit_sha = result.stdout.strip()

        # Should not raise error
        manager.remove_note(commit_sha)


class TestListNotes:
    """Tests for listing git notes."""

    def test_list_notes_empty(self, temp_git_repo):
        """Test listing notes when none exist."""
        manager = GitNotesManager(repo_path=str(temp_git_repo))

        notes = manager.list_notes()
        assert notes == []

    def test_list_notes_with_notes(self, temp_git_repo):
        """Test listing notes when they exist."""
        manager = GitNotesManager(repo_path=str(temp_git_repo))

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        commit_sha = result.stdout.strip()

        manager.add_note(commit_sha, "Test note")

        notes = manager.list_notes()
        assert len(notes) == 1
        assert notes[0][0] == commit_sha


class TestConfigureGitUser:
    """Tests for configuring git user."""

    def test_configure_git_user(self, temp_git_repo):
        """Test configuring git user."""
        manager = GitNotesManager(repo_path=str(temp_git_repo))

        manager.configure_git_user(name="Test Bot", email="bot@example.com")

        # Verify configuration
        result = subprocess.run(
            ["git", "config", "user.name"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "Test Bot"

        result = subprocess.run(
            ["git", "config", "user.email"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "bot@example.com"


class TestPushNotes:
    """Tests for pushing notes (mocked)."""

    def test_push_notes_mocked(self, temp_git_repo):
        """Test pushing notes with mocked git command."""
        manager = GitNotesManager(repo_path=str(temp_git_repo))

        with patch.object(manager, "_run_git_command") as mock_run:
            mock_run.return_value = ""
            manager.push_notes(remote="origin")

            # Verify git push command was called
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "push" in args
            assert "origin" in args
            assert "refs/notes/pr-summary" in args


class TestFetchNotes:
    """Tests for fetching notes (mocked)."""

    def test_fetch_notes_mocked(self, temp_git_repo):
        """Test fetching notes with mocked git command."""
        manager = GitNotesManager(repo_path=str(temp_git_repo))

        with patch.object(manager, "_run_git_command") as mock_run:
            mock_run.return_value = ""
            manager.fetch_notes(remote="origin")

            # Verify git fetch command was called
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "fetch" in args
            assert "origin" in args


class TestErrorHandling:
    """Tests for error handling in git operations."""

    def test_timeout_error(self, temp_git_repo):
        """Test handling of command timeout."""
        manager = GitNotesManager(repo_path=str(temp_git_repo))

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30)):
            with pytest.raises(GitNotesError, match="timeout"):
                manager._run_git_command(["git", "status"])

    def test_command_error(self, temp_git_repo):
        """Test handling of command failure."""
        manager = GitNotesManager(repo_path=str(temp_git_repo))

        with pytest.raises(GitNotesError):
            manager._run_git_command(["git", "invalid-command"])
