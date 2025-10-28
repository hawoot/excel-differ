"""
Git authentication helpers and documentation.
"""

# This module provides documentation for git authentication setup.
# The actual authentication is handled by GitPython using system git credentials.

GIT_AUTH_HELP = """
Git Authentication Setup for Excel Diff Server
================================================

The Excel Diff Server needs to authenticate with your git repository to commit
and push flattened snapshots. There are two main authentication methods:

1. SSH Key Authentication (Recommended)
----------------------------------------
   Best for: Local development, CI/CD environments

   Setup steps:

   a) Generate an SSH key (if you don't have one):
      $ ssh-keygen -t ed25519 -C "your_email@example.com"

   b) Add your public key to GitHub/GitLab/etc:
      - GitHub: Settings → SSH and GPG keys → New SSH key
      - GitLab: Preferences → SSH Keys
      - Copy your public key: $ cat ~/.ssh/id_ed25519.pub

   c) Configure SNAPSHOT_REPO_URL with SSH format:
      SNAPSHOT_REPO_URL=git@github.com:yourorg/excel-snapshots.git

   d) Test SSH connection:
      $ ssh -T git@github.com
      # You should see: "Hi username! You've successfully authenticated..."

2. HTTPS with Personal Access Token
------------------------------------
   Best for: Environments where SSH is blocked, simple setups

   Setup steps:

   a) Generate a Personal Access Token (PAT):
      - GitHub: Settings → Developer settings → Personal access tokens → Tokens (classic)
        - Scopes needed: repo (full control)
      - GitLab: Preferences → Access Tokens
        - Scopes needed: write_repository

   b) Configure SNAPSHOT_REPO_URL with token embedded:
      SNAPSHOT_REPO_URL=https://YOUR_TOKEN@github.com/yourorg/excel-snapshots.git

      Example with GitHub token:
      SNAPSHOT_REPO_URL=https://ghp_abc123xyz789@github.com/myorg/excel-snapshots.git

   c) Keep your token secure! Don't commit .env files to git.

3. Troubleshooting Authentication Issues
-----------------------------------------

   Error: "Permission denied (publickey)"
   → SSH key not configured or not added to GitHub/GitLab
   → Solution: Follow SSH setup steps above

   Error: "Authentication failed" (HTTPS)
   → Token is invalid or has expired
   → Solution: Generate a new token and update SNAPSHOT_REPO_URL

   Error: "Could not read from remote repository"
   → Repository doesn't exist or you don't have access
   → Solution: Check repository exists and you have write access

   To test git authentication manually:
   $ cd /tmp/test-clone
   $ git clone YOUR_SNAPSHOT_REPO_URL
   # If this works, the server will work too

4. Docker Considerations
------------------------

   For SSH in Docker:
   - Mount your SSH keys into the container:
     volumes:
       - ~/.ssh:/root/.ssh:ro

   For HTTPS in Docker:
   - Just set SNAPSHOT_REPO_URL in environment variables
   - No additional configuration needed

5. Security Best Practices
---------------------------

   - Never commit .env files with tokens to version control
   - Add .env to .gitignore
   - Use read-only SSH keys when possible (for pull-only operations)
   - Rotate access tokens periodically
   - Use environment-specific tokens (dev, staging, prod)
   - For CI/CD, use encrypted secrets or secret management services

For more help, see: docs/GIT_AUTHENTICATION.md
"""


def print_auth_help():
    """Print git authentication help to console."""
    print(GIT_AUTH_HELP)


def get_auth_instructions(error_message: str = "") -> str:
    """
    Get authentication instructions based on error message.

    Args:
        error_message: Git error message

    Returns:
        Helpful instructions for fixing the auth issue
    """
    error_lower = error_message.lower()

    if "permission denied" in error_lower or "publickey" in error_lower:
        return """
SSH Authentication Failed
-------------------------
Your SSH key is not configured or not recognized by the git server.

Quick fix:
1. Check if you have an SSH key: ls -la ~/.ssh/
2. If not, generate one: ssh-keygen -t ed25519
3. Add public key to GitHub/GitLab: cat ~/.ssh/id_ed25519.pub
4. Test connection: ssh -T git@github.com

Alternative: Use HTTPS with a personal access token instead.
See docs/GIT_AUTHENTICATION.md for details.
"""

    elif "authentication failed" in error_lower or "401" in error_lower:
        return """
HTTPS Authentication Failed
---------------------------
Your personal access token is invalid or expired.

Quick fix:
1. Generate a new token on GitHub/GitLab
2. Update SNAPSHOT_REPO_URL with the new token:
   SNAPSHOT_REPO_URL=https://YOUR_NEW_TOKEN@github.com/yourorg/repo.git
3. Restart the server

See docs/GIT_AUTHENTICATION.md for details.
"""

    elif "not found" in error_lower or "404" in error_lower:
        return """
Repository Not Found
--------------------
The repository URL is incorrect or you don't have access to it.

Quick fix:
1. Check SNAPSHOT_REPO_URL is correct
2. Verify the repository exists on GitHub/GitLab
3. Ensure you have write access to the repository
4. Try cloning manually to test: git clone YOUR_SNAPSHOT_REPO_URL
"""

    else:
        return f"""
Git Error
---------
An error occurred during git operation: {error_message}

General troubleshooting:
1. Test git connection manually: git clone YOUR_SNAPSHOT_REPO_URL
2. Check authentication setup (SSH keys or HTTPS token)
3. Verify repository exists and you have write access
4. See docs/GIT_AUTHENTICATION.md for detailed setup instructions
"""
