# PR Summary GitHub Action

A GitHub Action that automatically captures comprehensive PR activity (comments, reviews, checks, commits) and embeds it into your git repository as git notes. This preserves GitHub collaboration history directly in your git repository.

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

## Installation

### Option 1: Copy to Your Repository

1. Copy the `src/` directory to your repository
2. Copy `requirements.txt` to your repository root
3. Create `.github/workflows/pr-summary.yml` with the example workflow
4. Commit and push

### Option 2: As a Submodule

```bash
git submodule add https://github.com/yourusername/pr-summary
```

## Usage

### Basic GitHub Actions Workflow

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

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Generate PR Summary
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          MERGE_COMMIT_SHA: ${{ github.event.pull_request.merge_commit_sha }}
        run: python -m src.main
```

### Environment Variables

Required:
- `GITHUB_TOKEN`: GitHub authentication token (automatically provided in Actions)
- `PR_NUMBER`: Pull request number
- `GITHUB_REPOSITORY`: Repository in format "owner/repo" (or use `REPO_OWNER` and `REPO_NAME`)

Optional:
- `MERGE_COMMIT_SHA`: Merge commit SHA (auto-detected if not provided)
- `REPO_PATH`: Path to git repository (default: ".")
- `NOTES_REF`: Git notes reference (default: "refs/notes/pr-summary")
- `REMOTE`: Git remote name (default: "origin")
- `PUSH_NOTES`: Whether to push notes (default: "true")
- `LOG_LEVEL`: Logging level (default: "INFO")

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GITHUB_TOKEN="your_github_token"
export PR_NUMBER="123"
export REPO_OWNER="username"
export REPO_NAME="repository"
export MERGE_COMMIT_SHA="abc123..."

# Run
python -m src.main
```

## Viewing Git Notes

### Fetch Notes from Remote

```bash
git fetch origin refs/notes/pr-summary:refs/notes/pr-summary
```

### View Note for a Commit

```bash
git notes --ref=refs/notes/pr-summary show <commit-sha>
```

### View Note for Latest Merge Commit

```bash
git notes --ref=refs/notes/pr-summary show HEAD
```

### List All Notes

```bash
git notes --ref=refs/notes/pr-summary list
```

### Configure Git to Show Notes by Default

```bash
git config notes.displayRef refs/notes/pr-summary
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

### Requirements

- Python 3.11+
- Git 2.6+ (for git notes support)
- GitHub personal access token or GITHUB_TOKEN

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements.txt pytest mypy

# Run type checking
mypy src/

# Run tests (when implemented)
pytest tests/
```

### Type Checking

The codebase uses full type annotations and can be checked with mypy:

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
git fetch origin refs/notes/pr-summary:refs/notes/pr-summary

# Configure git to display notes
git config --add notes.displayRef refs/notes/pr-summary
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
