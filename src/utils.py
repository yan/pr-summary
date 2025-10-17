"""
Utility functions for PR summary action.

Helper functions for environment variables, logging, and validation.
"""

import logging
import os
import sys
from typing import Optional


def setup_logging(level: str = "INFO") -> None:
    """
    Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Reduce noise from requests library
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def get_env_var(name: str, required: bool = True, default: Optional[str] = None) -> str:
    """
    Get environment variable with validation.

    Args:
        name: Environment variable name
        required: Whether the variable is required
        default: Default value if not set

    Returns:
        Environment variable value

    Raises:
        ValueError: If required variable is not set
    """
    value = os.getenv(name, default)

    if required and not value:
        raise ValueError(f"Required environment variable not set: {name}")

    return value or ""


def validate_inputs(
    token: str,
    owner: str,
    repo: str,
    pr_number: int,
    merge_commit_sha: Optional[str] = None,
) -> None:
    """
    Validate input parameters.

    Args:
        token: GitHub token
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        merge_commit_sha: Merge commit SHA

    Raises:
        ValueError: If any inputs are invalid
    """
    if not token or len(token) < 10:
        raise ValueError("Invalid GitHub token")

    if not owner or not owner.strip():
        raise ValueError("Invalid repository owner")

    if not repo or not repo.strip():
        raise ValueError("Invalid repository name")

    if pr_number <= 0:
        raise ValueError(f"Invalid PR number: {pr_number}")

    if merge_commit_sha is not None and len(merge_commit_sha) < 7:
        raise ValueError(f"Invalid merge commit SHA: {merge_commit_sha}")


def parse_pr_number(pr_number_str: str) -> int:
    """
    Parse PR number from string.

    Args:
        pr_number_str: PR number as string

    Returns:
        PR number as integer

    Raises:
        ValueError: If PR number is invalid
    """
    try:
        pr_number = int(pr_number_str)
        if pr_number <= 0:
            raise ValueError("PR number must be positive")
        return pr_number
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid PR number: {pr_number_str}") from e


def github_action_output(name: str, value: str) -> None:
    """
    Set GitHub Actions output variable.

    Args:
        name: Output variable name
        value: Output variable value
    """
    # GitHub Actions output format
    print(f"::set-output name={name}::{value}")


def github_action_error(message: str, file: Optional[str] = None, line: Optional[int] = None) -> None:
    """
    Create GitHub Actions error annotation.

    Args:
        message: Error message
        file: File path (optional)
        line: Line number (optional)
    """
    annotation = "::error"

    if file:
        annotation += f" file={file}"
    if line:
        annotation += f",line={line}"

    annotation += f"::{message}"
    print(annotation)


def github_action_warning(message: str, file: Optional[str] = None, line: Optional[int] = None) -> None:
    """
    Create GitHub Actions warning annotation.

    Args:
        message: Warning message
        file: File path (optional)
        line: Line number (optional)
    """
    annotation = "::warning"

    if file:
        annotation += f" file={file}"
    if line:
        annotation += f",line={line}"

    annotation += f"::{message}"
    print(annotation)


def github_action_notice(message: str, file: Optional[str] = None, line: Optional[int] = None) -> None:
    """
    Create GitHub Actions notice annotation.

    Args:
        message: Notice message
        file: File path (optional)
        line: Line number (optional)
    """
    annotation = "::notice"

    if file:
        annotation += f" file={file}"
    if line:
        annotation += f",line={line}"

    annotation += f"::{message}"
    print(annotation)


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0

    return f"{size_bytes:.1f} TB"
