#!/usr/bin/env python3
"""
PR Summary GitHub Action - Main Entry Point

Collects PR activity from GitHub API and stores it as a git note.
"""

import logging
import sys
from pathlib import Path

from .collector import PRActivityCollector
from .formatter import SummaryFormatter
from .git_notes import GitNotesError, GitNotesManager
from .github_client import AuthenticationError, GitHubAPIError, GitHubClient, RateLimitError
from .utils import (
    get_env_var,
    github_action_error,
    github_action_notice,
    github_action_output,
    parse_pr_number,
    setup_logging,
    validate_inputs,
)


logger = logging.getLogger(__name__)


def main() -> int:
    """
    Main entry point for PR summary action.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Setup logging
    log_level = get_env_var("LOG_LEVEL", required=False, default="INFO")
    setup_logging(log_level)

    logger.info("Starting PR Summary Action")

    try:
        # Get configuration from environment
        config = get_configuration()

        # Validate inputs
        validate_inputs(
            token=config["token"],
            owner=config["owner"],
            repo=config["repo"],
            pr_number=config["pr_number"],
            merge_commit_sha=config["merge_commit_sha"],
        )

        logger.info(
            f"Configuration: {config['owner']}/{config['repo']} "
            f"PR #{config['pr_number']} "
            f"Commit {config['merge_commit_sha'][:7] if config['merge_commit_sha'] else 'N/A'}"
        )

        # Initialize components
        github_client = GitHubClient(
            token=config["token"],
            owner=config["owner"],
            repo=config["repo"],
        )

        collector = PRActivityCollector(github_client)
        formatter = SummaryFormatter()
        git_notes = GitNotesManager(
            repo_path=config["repo_path"],
            notes_ref=config["notes_ref"],
        )

        # Configure git user for notes
        git_notes.configure_git_user()

        # Collect PR activity
        logger.info(f"Collecting activity for PR #{config['pr_number']}")
        activity = collector.collect_all_activity(config["pr_number"])

        if not activity.is_merged:
            logger.warning(f"PR #{config['pr_number']} is not merged, continuing anyway")
            github_action_notice(f"PR #{config['pr_number']} is not merged")

        # Format summary
        logger.info("Formatting PR summary")
        summary = formatter.format(activity)

        # Determine commit SHA to attach note to
        commit_sha = config["merge_commit_sha"] or activity.merge_commit_sha

        if not commit_sha:
            raise ValueError(
                f"No merge commit SHA available for PR #{config['pr_number']}. "
                "Ensure the PR is merged or provide MERGE_COMMIT_SHA."
            )

        logger.info(f"Attaching note to commit {commit_sha[:7]}")

        # Add git note
        git_notes.add_note(commit_sha, summary, force=True)

        # Push notes to remote if configured
        if config["push_notes"]:
            logger.info(f"Pushing notes to remote: {config['remote']}")
            try:
                git_notes.push_notes(remote=config["remote"], force=False)
                github_action_notice(f"Successfully pushed PR summary for #{config['pr_number']}")
            except GitNotesError as e:
                logger.error(f"Failed to push notes: {e}")
                github_action_error(f"Failed to push notes: {e}")
                return 1
        else:
            logger.info("Skipping push (PUSH_NOTES=false)")
            github_action_notice(
                "Git note created but not pushed. "
                f"Run: git push {config['remote']} {config['notes_ref']}"
            )

        # Output summary stats
        github_action_output("pr_number", str(config["pr_number"]))
        github_action_output("commit_sha", commit_sha)
        github_action_output("notes_ref", config["notes_ref"])
        github_action_output("summary_length", str(len(summary)))

        logger.info(
            f"Successfully created PR summary: "
            f"{len(activity.commits)} commits, "
            f"{len(activity.comments)} comments, "
            f"{len(activity.reviews)} reviews, "
            f"{len(activity.check_runs)} checks"
        )

        return 0

    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        github_action_error(f"GitHub authentication failed: {e}")
        return 1

    except RateLimitError as e:
        logger.error(f"Rate limit exceeded: {e}")
        github_action_error(f"GitHub API rate limit exceeded: {e}")
        return 1

    except GitHubAPIError as e:
        logger.error(f"GitHub API error: {e}")
        github_action_error(f"GitHub API error: {e}")
        return 1

    except GitNotesError as e:
        logger.error(f"Git notes error: {e}")
        github_action_error(f"Git operation failed: {e}")
        return 1

    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        github_action_error(f"Invalid input: {e}")
        return 1

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        github_action_error(f"Unexpected error: {e}")
        return 1


def get_configuration() -> dict[str, any]:
    """
    Get configuration from environment variables.

    Returns:
        Configuration dictionary

    Raises:
        ValueError: If required configuration is missing
    """
    # Required variables
    token = get_env_var("GITHUB_TOKEN", required=True)
    pr_number_str = get_env_var("PR_NUMBER", required=True)
    pr_number = parse_pr_number(pr_number_str)

    # Repository information
    # GitHub Actions provides GITHUB_REPOSITORY as "owner/repo"
    github_repository = get_env_var("GITHUB_REPOSITORY", required=False)

    if github_repository and "/" in github_repository:
        owner, repo = github_repository.split("/", 1)
    else:
        # Fall back to individual env vars
        owner = get_env_var("REPO_OWNER", required=True)
        repo = get_env_var("REPO_NAME", required=True)

    # Optional variables with defaults
    merge_commit_sha = get_env_var("MERGE_COMMIT_SHA", required=False, default=None)
    repo_path = get_env_var("REPO_PATH", required=False, default=".")
    notes_ref = get_env_var("NOTES_REF", required=False, default="refs/notes/pr-summary")
    remote = get_env_var("REMOTE", required=False, default="origin")

    # Boolean flags
    push_notes_str = get_env_var("PUSH_NOTES", required=False, default="true")
    push_notes = push_notes_str.lower() in ("true", "1", "yes")

    return {
        "token": token,
        "pr_number": pr_number,
        "owner": owner,
        "repo": repo,
        "merge_commit_sha": merge_commit_sha,
        "repo_path": repo_path,
        "notes_ref": notes_ref,
        "remote": remote,
        "push_notes": push_notes,
    }


if __name__ == "__main__":
    sys.exit(main())
