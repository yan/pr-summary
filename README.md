# PR Summary GitHub Action

[![GitHub Action](https://img.shields.io/badge/action-yan%2Fpr--summary-blue?logo=github)](https://github.com/yan/pr-summary)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A GitHub Action that automatically captures comprehensive PR activity (comments, reviews, checks, commits) and embeds it into your git repository as git notes. This preserves GitHub collaboration history directly in your git repository.

**Use it in your workflow:** `yan/pr-summary@v1`

## Features

- **Complete PR History**: Captures all PR activity including:
  - Pull request metadata and description
  - All commits with authors and messages
  - Conversation comments and inline code review comments
  - Review approvals, changes requested, and comments
  - CI/CD check runs and their results
  - File changes with additions/deletions
  - Linked and closing issues
  - Participant information

- **Git Notes Storage**: Uses git notes to store summaries without modifying commit messages
- **Formatted Markdown**: Human-readable markdown summaries with organized sections
- **GitHub Actions Integration**: Runs automatically when PRs are merged

## How It Works

1. PR is merged → GitHub Action triggers
2. Script collects all PR activity via GitHub API
3. Formats data into structured markdown summary
4. Attaches summary as git note to the merge commit
5. Pushes notes to repository

## Quick Start

1. Add workflow file to `.github/workflows/pr-summary.yml`
2. Merge a PR
3. View the summary: `git notes --ref=refs/notes/commits show <merge-commit-sha>`

## Installation

Add this workflow to your repository at `.github/workflows/pr-summary.yml`:

```yaml
name: PR Summary to Git Notes

on:
  pull_request:
    types: [closed]

permissions:
  contents: write
  pull-requests: read
  checks: read

jobs:
  summarize:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: yan/pr-summary@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          pr-number: ${{ github.event.pull_request.number }}
          merge-commit-sha: ${{ github.event.pull_request.merge_commit_sha }}
```

That's it! The action will automatically run when PRs are merged.

## Usage

### Basic Usage

The action runs automatically when a PR is merged. No additional configuration is required beyond the workflow file.

### Customization

You can customize the action with input parameters:

```yaml
- uses: yan/pr-summary@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    pr-number: ${{ github.event.pull_request.number }}
    merge-commit-sha: ${{ github.event.pull_request.merge_commit_sha }}
    notes-ref: 'refs/notes/commits'  # Custom notes reference
    push-notes: 'true'                   # Whether to push notes
    log-level: 'INFO'                    # Logging level
```

### Input Parameters

**Required:**
- `github-token`: GitHub authentication token (use `${{ secrets.GITHUB_TOKEN }}`)
- `pr-number`: Pull request number

**Optional:**
- `merge-commit-sha`: Merge commit SHA (auto-detected from PR if not provided)
- `notes-ref`: Git notes reference (default: `refs/notes/commits`)
- `push-notes`: Whether to push notes to remote (default: `true`)
- `log-level`: Logging level - DEBUG, INFO, WARNING, ERROR (default: `INFO`)

## Local Development & Testing

For developers contributing to this action:

```bash
# Clone the repository
git clone https://github.com/yan/pr-summary.git
cd pr-summary

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GITHUB_TOKEN="your_github_token"
export PR_NUMBER="123"
export GITHUB_REPOSITORY="owner/repo"
export MERGE_COMMIT_SHA="abc123..."

# Run locally
python -m src.main
```

## Viewing Git Notes

### Fetch Notes from Remote

```bash
git fetch origin refs/notes/commits:refs/notes/commits
```

### View Note for a Commit

```bash
git notes --ref=refs/notes/commits show <commit-sha>
```

### View Note for Latest Merge Commit

```bash
git notes --ref=refs/notes/commits show HEAD
```

### List All Notes

```bash
git notes --ref=refs/notes/commits list
```

### Configure Git to Show Notes by Default

```bash
git config notes.displayRef refs/notes/commits
```

Now `git log` and `git show` will display notes automatically.

## Example Summary Output

```markdown
# 🟣 PR #123: Add dark mode support

## Metadata
- **Author:** @username
- **Base:** `main` ← **Head:** `feature/dark-mode`
- **Created:** 2025-10-14 10:00:00 UTC
- **Merged:** 2025-10-14 15:30:00 UTC by @maintainer
- **Labels:** `enhancement`, `ui`
- **Closes:** #45
- **Participants:** @username, @reviewer1, @reviewer2
- **URL:** https://github.com/owner/repo/pull/123

## Description
This PR adds comprehensive dark mode support to the application...

## Commits (3)
- [`abc1234`] Add dark mode CSS variables - @username
- [`def5678`] Update components for dark mode - @username
- [`ghi9012`] Add dark mode toggle - @username

## Reviews (2)
### Approved (2)
- ✅ @reviewer1 (2025-10-14 14:00:00 UTC)
- ✅ @reviewer2 (2025-10-14 14:30:00 UTC)

## Discussion (8 comments)
...

## Checks (5)
### Successful (4)
- ✅ Tests / Unit Tests (45.2s)
- ✅ Build / Production Build (120.5s)
...
```

## Architecture

### Project Structure

```
pr-summary/
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry point and orchestration
│   ├── models.py         # Type-annotated data models
│   ├── github_client.py  # GitHub API client
│   ├── collector.py      # Data collection and transformation
│   ├── formatter.py      # Markdown formatting
│   ├── git_notes.py      # Git notes operations
│   └── utils.py          # Helper functions
├── tests/
├── examples/
│   └── workflow.yml      # Example GitHub Actions workflow
├── requirements.txt
└── README.md
```

### Key Components

- **models.py**: Dataclasses for PR data (Commit, PRComment, Review, CheckRun, PRActivity)
- **github_client.py**: GitHub REST API client with retry logic and rate limiting
- **collector.py**: Fetches and transforms API data into typed models
- **formatter.py**: Generates markdown summaries from PR activity
- **git_notes.py**: Manages git notes creation and synchronization
- **main.py**: Orchestrates the complete workflow

## Development

For contributors to this project:

### Requirements

- Python 3.11+
- Git 2.6+ (for git notes support)
- GitHub personal access token for testing

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_models.py -v
```

**Test Coverage:** 80% (100 tests, all passing)

### Type Checking

The codebase uses full type annotations:

```bash
mypy --strict src/
```

## Limitations

- Only works with merged PRs
- GitHub API rate limits apply (5000 requests/hour for authenticated requests)
- Git notes must be explicitly fetched by users (`git fetch` doesn't fetch notes by default)
- Large PRs may take longer to process

## Benefits

- **Preserve History**: GitHub PR discussions are preserved in git
- **Offline Access**: View PR context without internet connection
- **Audit Trail**: Complete record of code review process
- **Integration**: Can be used by git tools and scripts
- **No Commit Pollution**: Notes don't modify commit messages or history

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with type annotations
4. Add tests if applicable
5. Submit a pull request

## Troubleshooting

### Notes Not Showing Up

```bash
# Make sure notes are fetched
git fetch origin refs/notes/commits:refs/notes/commits

# Configure git to display notes
git config --add notes.displayRef refs/notes/commits
```

### Permission Denied When Pushing

Ensure your GitHub Actions workflow has the correct permissions:

```yaml
permissions:
  contents: write  # Required for pushing notes
```

### Rate Limit Errors

The action respects GitHub API rate limits. For large repos with many PRs:
- Use `GITHUB_TOKEN` (5000 requests/hour)
- Consider running less frequently
- Monitor rate limit headers in logs

## Related Projects

- [git-notes documentation](https://git-scm.com/docs/git-notes)
- [GitHub REST API](https://docs.github.com/en/rest)
- [GitHub Actions](https://docs.github.com/en/actions)
