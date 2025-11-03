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
    Minimal Bitbucket client for Bitbucket Data Center/Server.
    Gets token from BITBUCKET_TOKEN environment variable automatically.
    """

    def __init__(self, base_url: str):
        """
        Initialize client.

        Args:
            base_url: Base API URL (e.g., https://api.bitbucket.org/2.0/repositories/workspace/repo)
        """
        # Get token from environment
        self.token = get_token_from_env()

        self.base_url = base_url.rstrip('/')

    def get_commits(self, branch: str, limit: int = 20) -> dict:
        """Get commits for a branch."""
        url = f"{self.base_url}/commits"
        params = {'until': f'refs/heads/{branch}'}
        if limit:
            params['limit'] = limit

        response = requests.get(url, params=params, headers={'Authorization': f'Bearer {self.token}'})
        response.raise_for_status()
        return response.json()

    def get_commit_changes(self, commit_id: str) -> dict:
        """Get files changed in a specific commit."""
        url = f"{self.base_url}/commits/{commit_id}/changes"
        response = requests.get(url, headers={'Authorization': f'Bearer {self.token}'})
        response.raise_for_status()
        return response.json()

    def get_file(self, path: str, ref: str) -> bytes:
        """Download file content at specific commit."""
        url = f"{self.base_url}/raw/{path}"
        response = requests.get(url, params={'at': ref}, headers={'Authorization': f'Bearer {self.token}'})
        response.raise_for_status()
        return response.content

    def get_branch_head_timestamp(self, branch: str) -> str:
        """Get latest commit timestamp for branch."""
        data = self.get_commits(branch, limit=1)
        return str(data['values'][0]['authorTimestamp'])

    def upload_files(self, branch: str, files: dict, message: str) -> dict:
        """
        Upload files to repository.

        Args:
            branch: Branch name
            files: Dict of {repo_path: content}
            message: Commit message

        Returns:
            Response JSON from last upload
        """
        result = None
        for file_path, content in files.items():
            url = f"{self.base_url}/browse/{file_path}"
            data = {
                'message': message,
                'branch': branch
            }
            files_param = {'content': content}

            response = requests.put(
                url,
                data=data,
                files=files_param,
                headers={'Authorization': f'Bearer {self.token}'}
            )
            response.raise_for_status()
            result = response.json()

        return result if result else {}
