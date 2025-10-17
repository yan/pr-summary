"""
GitHub API client for fetching PR data.

Handles authentication, pagination, rate limiting, and retries.
"""

import logging
import time
from typing import Any, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class RateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded."""

    pass


class AuthenticationError(GitHubAPIError):
    """Raised when authentication fails."""

    pass


class GitHubClient:
    """Client for interacting with the GitHub REST API."""

    BASE_URL = "https://api.github.com"
    API_VERSION = "2022-11-28"

    def __init__(self, token: str, owner: str, repo: str, timeout: int = 30):
        """
        Initialize GitHub API client.

        Args:
            token: GitHub authentication token (PAT or GITHUB_TOKEN)
            owner: Repository owner (username or organization)
            repo: Repository name
            timeout: Request timeout in seconds
        """
        self.token = token
        self.owner = owner
        self.repo = repo
        self.timeout = timeout

        # Create session with retry strategy
        self.session = self._create_session()

        # Validate authentication on initialization
        self._validate_auth()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()

        # Retry strategy: retry on connection errors and 5xx server errors
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Set default headers
        session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": self.API_VERSION,
            }
        )

        return session

    def _validate_auth(self) -> None:
        """Validate authentication by making a test request to the repository."""
        try:
            # Use repository endpoint instead of /user since GitHub Actions tokens
            # don't have access to user scope
            response = self._make_request(f"/repos/{self.owner}/{self.repo}")
            logger.info(f"Authenticated for repository: {response.get('full_name', 'unknown')}")
        except GitHubAPIError as e:
            if e.status_code == 401:
                raise AuthenticationError("Invalid GitHub token") from e
            if e.status_code == 404:
                raise AuthenticationError(f"Repository not found or token lacks access: {self.owner}/{self.repo}") from e
            raise

    def _make_request(
        self, endpoint: str, params: Optional[dict[str, Any]] = None, method: str = "GET"
    ) -> dict[str, Any]:
        """
        Make a request to the GitHub API.

        Args:
            endpoint: API endpoint (e.g., '/repos/{owner}/{repo}/pulls/{number}')
            params: Query parameters
            method: HTTP method

        Returns:
            Response JSON data

        Raises:
            RateLimitError: If rate limit is exceeded
            AuthenticationError: If authentication fails
            GitHubAPIError: For other API errors
        """
        url = urljoin(self.BASE_URL, endpoint)

        logger.debug(f"{method} {url} with params: {params}")

        try:
            response = self.session.request(method, url, params=params, timeout=self.timeout)

            # Check rate limit
            remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
            if remaining < 10:
                reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                logger.warning(
                    f"API rate limit low: {remaining} requests remaining. "
                    f"Resets at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(reset_time))}"
                )

            # Handle rate limiting
            if response.status_code == 403 and remaining == 0:
                reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                wait_time = max(0, reset_time - time.time())
                raise RateLimitError(
                    f"Rate limit exceeded. Resets in {wait_time:.0f} seconds",
                    status_code=403,
                    response=response.json() if response.content else None,
                )

            # Handle authentication errors
            if response.status_code == 401:
                raise AuthenticationError("Authentication failed", status_code=401)

            # Handle other errors
            response.raise_for_status()

            return response.json()

        except requests.exceptions.Timeout as e:
            raise GitHubAPIError(f"Request timeout after {self.timeout}s") from e
        except requests.exceptions.RequestException as e:
            raise GitHubAPIError(f"Request failed: {str(e)}") from e

    def _paginate(
        self, endpoint: str, params: Optional[dict[str, Any]] = None, per_page: int = 100
    ) -> list[dict[str, Any]]:
        """
        Fetch all pages of a paginated endpoint.

        Args:
            endpoint: API endpoint
            params: Query parameters
            per_page: Results per page (max 100)

        Returns:
            List of all results across all pages
        """
        params = params or {}
        params["per_page"] = min(per_page, 100)
        params["page"] = 1

        all_results: list[dict[str, Any]] = []

        while True:
            logger.debug(f"Fetching page {params['page']} of {endpoint}")
            results = self._make_request(endpoint, params)

            if not results:
                break

            all_results.extend(results)

            # Check if there are more pages
            if len(results) < params["per_page"]:
                break

            params["page"] += 1

        logger.info(f"Fetched {len(all_results)} total items from {endpoint}")
        return all_results

    # PR endpoints

    def get_pull_request(self, pr_number: int) -> dict[str, Any]:
        """
        Get PR metadata.

        Args:
            pr_number: Pull request number

        Returns:
            PR data
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}"
        return self._make_request(endpoint)

    def get_pr_commits(self, pr_number: int) -> list[dict[str, Any]]:
        """
        Get all commits in a PR.

        Args:
            pr_number: Pull request number

        Returns:
            List of commits
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}/commits"
        return self._paginate(endpoint)

    def get_pr_files(self, pr_number: int) -> list[dict[str, Any]]:
        """
        Get all file changes in a PR.

        Args:
            pr_number: Pull request number

        Returns:
            List of file changes
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}/files"
        return self._paginate(endpoint)

    def get_pr_comments(self, pr_number: int) -> list[dict[str, Any]]:
        """
        Get review comments (inline code comments) on a PR.

        Args:
            pr_number: Pull request number

        Returns:
            List of review comments
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}/comments"
        return self._paginate(endpoint)

    def get_issue_comments(self, pr_number: int) -> list[dict[str, Any]]:
        """
        Get conversation comments on a PR.

        Note: PRs are issues, so we use the issues endpoint.

        Args:
            pr_number: Pull request number

        Returns:
            List of conversation comments
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/issues/{pr_number}/comments"
        return self._paginate(endpoint)

    def get_pr_reviews(self, pr_number: int) -> list[dict[str, Any]]:
        """
        Get PR reviews (approvals, change requests, etc.).

        Args:
            pr_number: Pull request number

        Returns:
            List of reviews
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}/reviews"
        return self._paginate(endpoint)

    def get_check_runs(self, ref: str) -> list[dict[str, Any]]:
        """
        Get check runs for a commit SHA or ref.

        Args:
            ref: Commit SHA or git ref

        Returns:
            List of check runs
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/commits/{ref}/check-runs"
        response = self._make_request(endpoint)
        return response.get("check_runs", [])

    def get_commit_status(self, ref: str) -> dict[str, Any]:
        """
        Get combined status for a commit.

        Args:
            ref: Commit SHA or git ref

        Returns:
            Combined status data
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/commits/{ref}/status"
        return self._make_request(endpoint)

    def get_repository(self) -> dict[str, Any]:
        """
        Get repository metadata.

        Returns:
            Repository data
        """
        endpoint = f"/repos/{self.owner}/{self.repo}"
        return self._make_request(endpoint)

    def get_user(self, username: str) -> dict[str, Any]:
        """
        Get user information.

        Args:
            username: GitHub username

        Returns:
            User data
        """
        endpoint = f"/users/{username}"
        return self._make_request(endpoint)
