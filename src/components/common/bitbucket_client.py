"""Reusable Bitbucket API client for interacting with Bitbucket Cloud API v2.0."""

import base64
import logging
from typing import Dict, List, Optional, Any, BinaryIO
from urllib.parse import urljoin
import requests


logger = logging.getLogger(__name__)


class BitbucketError(Exception):
    """Base exception for Bitbucket API errors."""
    pass


class BitbucketAuthError(BitbucketError):
    """Raised when authentication fails."""
    pass


class BitbucketNotFoundError(BitbucketError):
    """Raised when a resource is not found."""
    pass


class BitbucketClient:
    """
    A clean, reusable client for Bitbucket Cloud API v2.0.

    Example usage:
        client = BitbucketClient('myworkspace', 'myrepo', 'my_app_password')

        # Get file content
        content = client.get_file('path/to/file.xlsx', 'main')

        # List commits
        commits = client.list_commits('main', limit=10)

        # Upload files
        client.upload_files('main', {'path/to/file.txt': b'content'}, 'Update file')
    """

    def __init__(
        self,
        workspace: str,
        repo_slug: str,
        token: str,
        username: str = 'x-token-auth',
        base_url: str = 'https://api.bitbucket.org/2.0'
    ):
        """
        Initialize Bitbucket API client.

        Args:
            workspace: Bitbucket workspace ID
            repo_slug: Repository slug/name
            token: App password or access token
            username: Username for Basic Auth (default: 'x-token-auth' for app passwords)
            base_url: Base URL for Bitbucket API (default: https://api.bitbucket.org/2.0)
        """
        self.workspace = workspace
        self.repo_slug = repo_slug
        self.base_url = base_url.rstrip('/')
        self.auth = (username, token)
        self.session = requests.Session()
        self.session.auth = self.auth

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        data: Optional[Any] = None,
        files: Optional[Dict] = None
    ) -> requests.Response:
        """
        Make an HTTP request to the Bitbucket API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json: JSON body
            data: Form data
            files: Files to upload

        Returns:
            Response object

        Raises:
            BitbucketAuthError: If authentication fails
            BitbucketNotFoundError: If resource not found
            BitbucketError: For other API errors
        """
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                data=data,
                files=files
            )

            # Handle specific status codes
            if response.status_code == 401:
                raise BitbucketAuthError(f"Authentication failed: {response.text}")
            elif response.status_code == 404:
                raise BitbucketNotFoundError(f"Resource not found: {endpoint}")
            elif response.status_code >= 400:
                raise BitbucketError(
                    f"API request failed with status {response.status_code}: {response.text}"
                )

            return response

        except requests.exceptions.RequestException as e:
            raise BitbucketError(f"Request failed: {str(e)}") from e

    def _paginate(self, endpoint: str, params: Optional[Dict] = None, limit: Optional[int] = None) -> List[Dict]:
        """
        Fetch all pages of a paginated API response.

        Args:
            endpoint: API endpoint
            params: Query parameters
            limit: Maximum number of items to return (None for all)

        Returns:
            List of all items from all pages
        """
        all_items = []
        params = params or {}
        page = 1

        while True:
            params['page'] = page
            response = self._make_request('GET', endpoint, params=params)
            data = response.json()

            # Bitbucket uses 'values' array for paginated results
            items = data.get('values', [])
            all_items.extend(items)

            # Check if we've hit the limit
            if limit and len(all_items) >= limit:
                return all_items[:limit]

            # Check if there's a next page
            if 'next' not in data:
                break

            page += 1

        return all_items

    def get_file(self, path: str, ref: str = 'main') -> bytes:
        """
        Download file content at a specific commit or branch.

        Args:
            path: File path in repository
            ref: Commit SHA or branch name (default: 'main')

        Returns:
            File content as bytes
        """
        endpoint = f'/repositories/{self.workspace}/{self.repo_slug}/src/{ref}/{path}'
        response = self._make_request('GET', endpoint)
        return response.content

    def list_commits(
        self,
        branch: str = 'main',
        since: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        List commits on a branch.

        Args:
            branch: Branch name (default: 'main')
            since: Only return commits after this commit SHA
            limit: Maximum number of commits to return

        Returns:
            List of commit objects with keys: hash, date, message, author, etc.
        """
        endpoint = f'/repositories/{self.workspace}/{self.repo_slug}/commits/{branch}'
        params = {}

        if since:
            params['exclude'] = since

        commits = self._paginate(endpoint, params=params, limit=limit)
        return commits

    def get_commit(self, commit_sha: str) -> Dict:
        """
        Get details of a specific commit.

        Args:
            commit_sha: Commit SHA

        Returns:
            Commit object with details
        """
        endpoint = f'/repositories/{self.workspace}/{self.repo_slug}/commit/{commit_sha}'
        response = self._make_request('GET', endpoint)
        return response.json()

    def get_commit_diff(self, commit_sha: str) -> Dict:
        """
        Get the diff/changes for a specific commit.

        Args:
            commit_sha: Commit SHA

        Returns:
            Diff object showing files changed
        """
        endpoint = f'/repositories/{self.workspace}/{self.repo_slug}/diff/{commit_sha}'
        response = self._make_request('GET', endpoint)
        return response.json()

    def get_branch_head(self, branch: str = 'main') -> str:
        """
        Get the latest commit SHA for a branch.

        Args:
            branch: Branch name (default: 'main')

        Returns:
            Commit SHA of the branch head
        """
        endpoint = f'/repositories/{self.workspace}/{self.repo_slug}/refs/branches/{branch}'
        response = self._make_request('GET', endpoint)
        data = response.json()
        return data['target']['hash']

    def upload_files(
        self,
        branch: str,
        files: Dict[str, bytes],
        message: str,
        author: Optional[str] = None
    ) -> Dict:
        """
        Upload one or more files in a single commit.

        Args:
            branch: Target branch name
            files: Dict mapping file paths to their content (as bytes)
            message: Commit message
            author: Optional commit author (format: "Name <email>")

        Returns:
            Response data from the API

        Example:
            client.upload_files(
                'main',
                {'path/file1.txt': b'content1', 'path/file2.txt': b'content2'},
                'Update files'
            )
        """
        endpoint = f'/repositories/{self.workspace}/{self.repo_slug}/src'

        # Prepare multipart form data
        form_data = {
            'message': message,
            'branch': branch
        }

        if author:
            form_data['author'] = author

        # Add files to the form (Bitbucket expects file fields)
        files_dict = {}
        for path, content in files.items():
            # Each file needs a unique field name, we use the path
            files_dict[path] = (path, content)

        response = self._make_request('POST', endpoint, data=form_data, files=files_dict)
        return response.json()

    def list_directory(self, path: str = '', ref: str = 'main') -> List[Dict]:
        """
        List contents of a directory in the repository.

        Args:
            path: Directory path (empty string for root)
            ref: Commit SHA or branch name (default: 'main')

        Returns:
            List of file/directory objects
        """
        endpoint = f'/repositories/{self.workspace}/{self.repo_slug}/src/{ref}/{path}'
        params = {'format': 'meta'}  # Get metadata instead of file content
        response = self._make_request('GET', endpoint, params=params)
        data = response.json()
        return data.get('values', [])

    def get_repository_info(self) -> Dict:
        """
        Get repository information.

        Returns:
            Repository metadata
        """
        endpoint = f'/repositories/{self.workspace}/{self.repo_slug}'
        response = self._make_request('GET', endpoint)
        return response.json()
