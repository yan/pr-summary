"""
Tests for utility functions.
"""

import os
from unittest.mock import patch

import pytest

from src.utils import (
    format_file_size,
    get_env_var,
    parse_pr_number,
    validate_inputs,
)


class TestGetEnvVar:
    """Tests for get_env_var function."""

    def test_get_existing_env_var(self, monkeypatch):
        """Test getting an existing environment variable."""
        monkeypatch.setenv("TEST_VAR", "test_value")
        assert get_env_var("TEST_VAR") == "test_value"

    def test_get_missing_required_env_var(self):
        """Test getting a missing required environment variable."""
        with pytest.raises(ValueError, match="Required environment variable not set"):
            get_env_var("NONEXISTENT_VAR", required=True)

    def test_get_missing_optional_env_var(self):
        """Test getting a missing optional environment variable."""
        result = get_env_var("NONEXISTENT_VAR", required=False)
        assert result == ""

    def test_get_env_var_with_default(self):
        """Test getting environment variable with default value."""
        result = get_env_var("NONEXISTENT_VAR", required=False, default="default_value")
        assert result == "default_value"

    def test_get_env_var_required_with_default(self, monkeypatch):
        """Test that default works even with required=True."""
        result = get_env_var("NONEXISTENT_VAR", required=True, default="default")
        assert result == "default"


class TestValidateInputs:
    """Tests for validate_inputs function."""

    def test_valid_inputs(self):
        """Test validation with valid inputs."""
        # Should not raise
        validate_inputs(
            token="ghp_1234567890abcdef",
            owner="testuser",
            repo="testrepo",
            pr_number=123,
            merge_commit_sha="abc123def456",
        )

    def test_invalid_token(self):
        """Test validation with invalid token."""
        with pytest.raises(ValueError, match="Invalid GitHub token"):
            validate_inputs(
                token="short",
                owner="testuser",
                repo="testrepo",
                pr_number=123,
            )

    def test_empty_token(self):
        """Test validation with empty token."""
        with pytest.raises(ValueError, match="Invalid GitHub token"):
            validate_inputs(
                token="",
                owner="testuser",
                repo="testrepo",
                pr_number=123,
            )

    def test_invalid_owner(self):
        """Test validation with invalid owner."""
        with pytest.raises(ValueError, match="Invalid repository owner"):
            validate_inputs(
                token="ghp_1234567890abcdef",
                owner="",
                repo="testrepo",
                pr_number=123,
            )

    def test_invalid_repo(self):
        """Test validation with invalid repo."""
        with pytest.raises(ValueError, match="Invalid repository name"):
            validate_inputs(
                token="ghp_1234567890abcdef",
                owner="testuser",
                repo="  ",
                pr_number=123,
            )

    def test_invalid_pr_number(self):
        """Test validation with invalid PR number."""
        with pytest.raises(ValueError, match="Invalid PR number"):
            validate_inputs(
                token="ghp_1234567890abcdef",
                owner="testuser",
                repo="testrepo",
                pr_number=0,
            )

        with pytest.raises(ValueError, match="Invalid PR number"):
            validate_inputs(
                token="ghp_1234567890abcdef",
                owner="testuser",
                repo="testrepo",
                pr_number=-1,
            )

    def test_invalid_merge_commit_sha(self):
        """Test validation with invalid merge commit SHA."""
        with pytest.raises(ValueError, match="Invalid merge commit SHA"):
            validate_inputs(
                token="ghp_1234567890abcdef",
                owner="testuser",
                repo="testrepo",
                pr_number=123,
                merge_commit_sha="short",
            )


class TestParsePRNumber:
    """Tests for parse_pr_number function."""

    def test_parse_valid_pr_number(self):
        """Test parsing a valid PR number."""
        assert parse_pr_number("123") == 123
        assert parse_pr_number("1") == 1
        assert parse_pr_number("999999") == 999999

    def test_parse_invalid_pr_number(self):
        """Test parsing invalid PR numbers."""
        with pytest.raises(ValueError, match="Invalid PR number"):
            parse_pr_number("abc")

        with pytest.raises(ValueError, match="Invalid PR number"):
            parse_pr_number("-1")

        with pytest.raises(ValueError, match="Invalid PR number"):
            parse_pr_number("0")

        with pytest.raises(ValueError, match="Invalid PR number"):
            parse_pr_number("")


class TestFormatFileSize:
    """Tests for format_file_size function."""

    def test_format_bytes(self):
        """Test formatting bytes."""
        assert format_file_size(500) == "500.0 B"
        assert format_file_size(1023) == "1023.0 B"

    def test_format_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(5120) == "5.0 KB"

    def test_format_megabytes(self):
        """Test formatting megabytes."""
        assert format_file_size(1048576) == "1.0 MB"
        assert format_file_size(5242880) == "5.0 MB"

    def test_format_gigabytes(self):
        """Test formatting gigabytes."""
        assert format_file_size(1073741824) == "1.0 GB"
        assert format_file_size(5368709120) == "5.0 GB"

    def test_format_terabytes(self):
        """Test formatting terabytes."""
        assert format_file_size(1099511627776) == "1.0 TB"


class TestGitHubActionHelpers:
    """Tests for GitHub Actions helper functions."""

    def test_github_action_output(self, capsys):
        """Test GitHub Actions output."""
        from src.utils import github_action_output

        github_action_output("test_name", "test_value")
        captured = capsys.readouterr()
        assert "::set-output name=test_name::test_value" in captured.out

    def test_github_action_error(self, capsys):
        """Test GitHub Actions error annotation."""
        from src.utils import github_action_error

        github_action_error("Test error message")
        captured = capsys.readouterr()
        assert "::error::Test error message" in captured.out

    def test_github_action_error_with_file(self, capsys):
        """Test GitHub Actions error with file location."""
        from src.utils import github_action_error

        github_action_error("Test error", file="test.py", line=42)
        captured = capsys.readouterr()
        assert "::error file=test.py,line=42::Test error" in captured.out

    def test_github_action_warning(self, capsys):
        """Test GitHub Actions warning annotation."""
        from src.utils import github_action_warning

        github_action_warning("Test warning")
        captured = capsys.readouterr()
        assert "::warning::Test warning" in captured.out

    def test_github_action_notice(self, capsys):
        """Test GitHub Actions notice annotation."""
        from src.utils import github_action_notice

        github_action_notice("Test notice")
        captured = capsys.readouterr()
        assert "::notice::Test notice" in captured.out
