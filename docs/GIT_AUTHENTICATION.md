# Git Authentication Setup

The Excel Diff Server needs to authenticate with your git repository to commit and push flattened snapshots. There are two main authentication methods:

## 1. SSH Key Authentication (Recommended)

**Best for**: Local development, CI/CD environments

### Setup Steps

**a) Generate an SSH key** (if you don't have one):

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

**b) Add your public key to GitHub/GitLab**:

- **GitHub**: Settings → SSH and GPG keys → New SSH key
- **GitLab**: Preferences → SSH Keys
- Copy your public key:

```bash
cat ~/.ssh/id_ed25519.pub
```

**c) Configure SNAPSHOT_REPO_URL** with SSH format in `.env`:

```bash
SNAPSHOT_REPO_URL=git@github.com:yourorg/excel-snapshots.git
```

**d) Test SSH connection**:

```bash
ssh -T git@github.com
# You should see: "Hi username! You've successfully authenticated..."
```

## 2. HTTPS with Personal Access Token

**Best for**: Environments where SSH is blocked, simple setups

### Setup Steps

**a) Generate a Personal Access Token (PAT)**:

- **GitHub**: Settings → Developer settings → Personal access tokens → Tokens (classic)
  - Scopes needed: `repo` (full control)
- **GitLab**: Preferences → Access Tokens
  - Scopes needed: `write_repository`

**b) Configure SNAPSHOT_REPO_URL** with token embedded:

```bash
SNAPSHOT_REPO_URL=https://YOUR_TOKEN@github.com/yourorg/excel-snapshots.git
```

Example with GitHub token:

```bash
SNAPSHOT_REPO_URL=https://ghp_abc123xyz789@github.com/myorg/excel-snapshots.git
```

**c) Keep your token secure!**

- Don't commit `.env` files to git
- Use `.gitignore` to exclude `.env`

## 3. Troubleshooting Authentication Issues

### Error: "Permission denied (publickey)"

**Cause**: SSH key not configured or not added to GitHub/GitLab

**Solution**:
1. Check if you have an SSH key: `ls -la ~/.ssh/`
2. If not, generate one: `ssh-keygen -t ed25519`
3. Add public key to GitHub/GitLab: `cat ~/.ssh/id_ed25519.pub`
4. Test connection: `ssh -T git@github.com`

**Alternative**: Use HTTPS with a personal access token instead.

### Error: "Authentication failed" (HTTPS)

**Cause**: Token is invalid or has expired

**Solution**:
1. Generate a new token on GitHub/GitLab
2. Update `SNAPSHOT_REPO_URL` in `.env` with the new token
3. Restart the server

### Error: "Could not read from remote repository"

**Cause**: Repository doesn't exist or you don't have access

**Solution**:
1. Check `SNAPSHOT_REPO_URL` is correct
2. Verify the repository exists on GitHub/GitLab
3. Ensure you have write access to the repository

### Manual Testing

To test git authentication manually:

```bash
cd /tmp/test-clone
git clone YOUR_SNAPSHOT_REPO_URL
# If this works, the server will work too
```

## 4. Docker Considerations

### For SSH in Docker

Mount your SSH keys into the container by uncommenting in `docker-compose.yml`:

```yaml
api:
  volumes:
    - ~/.ssh:/root/.ssh:ro

worker:
  volumes:
    - ~/.ssh:/root/.ssh:ro
```

Then restart:

```bash
docker-compose down
docker-compose up -d
```

### For HTTPS in Docker

Just set `SNAPSHOT_REPO_URL` in `.env` - no additional configuration needed!

## 5. Security Best Practices

- ✅ Never commit `.env` files with tokens to version control
- ✅ Add `.env` to `.gitignore`
- ✅ Use read-only SSH keys when possible (for pull-only operations)
- ✅ Rotate access tokens periodically
- ✅ Use environment-specific tokens (dev, staging, prod)
- ✅ For CI/CD, use encrypted secrets or secret management services

## Quick Reference

| Method | SNAPSHOT_REPO_URL Format | Additional Setup |
|--------|--------------------------|------------------|
| **SSH** | `git@github.com:org/repo.git` | Add SSH key to GitHub/GitLab |
| **HTTPS** | `https://TOKEN@github.com/org/repo.git` | Generate personal access token |

## Need Help?

If you're still having issues:

1. Check the server logs for detailed error messages
2. Try manual git clone with the same URL
3. Verify your token/key has the correct permissions
4. Check if your organization has special security requirements

For more information, see the [Complete Requirements](Differ%20Requirements.md).
