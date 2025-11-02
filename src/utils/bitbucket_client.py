"""Minimal Bitbucket HTTP client - inserts token into URL for authentication."""

import os
import requests


def get_token_from_env(env_var: str = 'BITBUCKET_TOKEN') -> str:
    """
    Get Bitbucket token from environment variable.

    Args:
        env_var: Environment variable name (default: BITBUCKET_TOKEN)

    Returns:
        Token value

    Raises:
        ValueError: If env var not set
    """
    token = os.getenv(env_var)
    if not token:
        raise ValueError(f"Environment variable {env_var} not set")
    return token


class BitbucketClient:
    """
    Minimal Bitbucket client - inserts token into URL for auth.
    Gets token from BITBUCKET_TOKEN environment variable automatically.
    """

    def __init__(self, base_url: str):
        """
        Initialize client.

        Args:
            base_url: Base API URL (e.g., https://api.bitbucket.org/2.0/repositories/workspace/repo)
        """
        # Get token from environment
        token = get_token_from_env()

        # Insert token into URL: https://... -> https://{token}@...
        self.base_url = base_url.rstrip('/')

        # Create URL with embedded token
        if '://' in self.base_url:
            protocol, rest = self.base_url.split('://', 1)
            self.base_url_with_token = f"{protocol}://{token}@{rest}"
        else:
            self.base_url_with_token = self.base_url

    def get_commits(self, branch: str, exclude: str = None, pagelen: int = None) -> dict:
        """Get commits for a branch."""
        url = f"{self.base_url_with_token}/commits/{branch}"
        params = {}
        if exclude:
            params['exclude'] = exclude
        if pagelen:
            params['pagelen'] = pagelen

        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_file(self, path: str, ref: str) -> bytes:
        """Download file content at specific commit."""
        url = f"{self.base_url_with_token}/src/{ref}/{path}"
        response = requests.get(url)
        response.raise_for_status()
        return response.content

    def get_branch_head(self, branch: str) -> str:
        """Get latest commit SHA for branch."""
        url = f"{self.base_url_with_token}/refs/branches/{branch}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data['target']['hash']

    def upload_files(self, branch: str, files: dict, message: str) -> dict:
        """
        Upload files to repository.

        Args:
            branch: Branch name
            files: Dict of {repo_path: (filename, content)}
            message: Commit message

        Returns:
            Response JSON
        """
        url = f"{self.base_url_with_token}/src"
        data = {
            'message': message,
            'branch': branch
        }
        response = requests.post(url, data=data, files=files)
        response.raise_for_status()
        return response.json()
