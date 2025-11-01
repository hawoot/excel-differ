# Excel Differ - Deployment Guide

**Version:** 3.0
**Last Updated:** 2025-11-01
**Status:** Phase 2 Design

---

## Overview

This guide explains exactly how to deploy and run Excel Differ in different scenarios. It covers both **source code** deployment (run with Python) and **standalone executable** deployment (when available).

---

## Deployment Options

### Option 1: Run from Source Code
**Best for:** Development, customisation, debugging

### Option 2: Standalone Executable (Future)
**Best for:** Production, CI/CD, distribution to non-technical users

---

## Option 1: Run from Source Code

### Minimum File Structure

```
your-deployment-location/
├── excel-differ/                    # Git repository clone
│   ├── components/
│   │   ├── core/                    # Core interfaces (Phase 2)
│   │   ├── flattener/              # ✅ Available now
│   │   ├── source/                 # Source components (Phase 2)
│   │   ├── destination/            # Destination components (Phase 2)
│   │   ├── converter/              # Converter components (Phase 2+)
│   │   └── orchestrator/           # Orchestrator (Phase 2)
│   ├── config/                      # YOUR configuration files go here
│   │   └── excel-differ.yaml       # Main config file
│   ├── docs/
│   ├── main.py                      # Main entry point (Phase 2)
│   └── requirements.txt
│
├── .env                             # YOUR secrets (tokens)
└── venv/                            # Python virtual environment (created)
```

### Step-by-Step Setup

#### 1. Clone Repository

```bash
cd /path/where/you/want/excel-differ
git clone <repository-url> excel-differ
cd excel-differ
```

#### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it (Linux/Mac)
source venv/bin/activate

# Activate it (Windows)
venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Create Configuration Files

**Create `.env` in repository root:**
```bash
# .env - Store your secrets here
BITBUCKET_TOKEN=your_bitbucket_app_password_here
```

**Create `config/excel-differ.yaml`:**
```yaml
# config/excel-differ.yaml

# Source - where to get Excel files
source:
  implementation: bitbucket
  config:
    url: https://bitbucket.org/myworkspace/my-excel-repo
    branch: main
    token: ${BITBUCKET_TOKEN}
    include_patterns:
      - "data/**/*.xlsx"
      - "reports/**/*.xlsm"
    exclude_patterns:
      - "**/archive/**"
      - "**/temp/**"
    depth: 1

# Destination - where to upload flattened outputs
destination:
  implementation: bitbucket
  config:
    url: https://bitbucket.org/myworkspace/my-excel-repo
    branch: main
    token: ${BITBUCKET_TOKEN}
    output_path: flattened/

# Sync behaviour
sync:
  depth: 1

# Components
converter:
  implementation: noop
  config: {}

flattener:
  implementation: openpyxl
  config:
    include_computed: false
    include_literal: true
    include_formats: true
    timeout: 900

git:
  implementation: bitbucket
  config: {}
```

#### 5. Run Excel Differ

**Phase 1 (Current) - Flattener Only:**
```bash
# Flatten a single file
python -m components.flattener.src flatten myfile.xlsx --output ./flats

# Show flattener info
python -m components.flattener.src info myfile.xlsx
```

**Phase 2 (Coming Soon) - Full Orchestrator:**
```bash
# Run orchestrator with config
python main.py --config config/excel-differ.yaml

# Or with environment variables
export EXCEL_DIFFER_CONFIG=config/excel-differ.yaml
python main.py
```

---

## Option 2: Standalone Executable (Future - Phase 2+)

### Minimum File Structure

```
your-deployment-location/
├── excel-differ                     # Standalone executable (or excel-differ.exe on Windows)
├── config/
│   └── excel-differ.yaml           # YOUR configuration file
└── .env                             # YOUR secrets
```

### Step-by-Step Setup

#### 1. Download Executable

```bash
# Download from releases page
curl -L https://github.com/org/excel-differ/releases/latest/download/excel-differ-linux -o excel-differ
chmod +x excel-differ

# Windows
# Download excel-differ.exe from releases page
```

#### 2. Create Configuration Files

Same as Option 1 (`.env` and `config/excel-differ.yaml`)

#### 3. Run Excel Differ

```bash
# Run with config file
./excel-differ --config config/excel-differ.yaml

# Run with environment variable
export EXCEL_DIFFER_CONFIG=config/excel-differ.yaml
./excel-differ

# Windows
excel-differ.exe --config config\excel-differ.yaml
```

---

## Configuration File Reference

### Minimal Configuration (Same Repo, Both Source and Destination)

```yaml
source:
  implementation: bitbucket
  config:
    url: https://bitbucket.org/workspace/repo
    branch: main
    token: ${BITBUCKET_TOKEN}
    include_patterns:
      - "**/*.xlsx"
      - "**/*.xlsm"

destination:
  implementation: bitbucket
  config:
    url: https://bitbucket.org/workspace/repo
    branch: main
    token: ${BITBUCKET_TOKEN}
    output_path: flattened/

sync:
  depth: 1

converter:
  implementation: noop

flattener:
  implementation: openpyxl
  config:
    include_computed: false
```

### Separate Repositories

```yaml
source:
  implementation: bitbucket
  config:
    url: https://bitbucket.org/workspace/excel-files
    branch: main
    token: ${BITBUCKET_SOURCE_TOKEN}
    include_patterns:
      - "**/*.xlsx"

destination:
  implementation: bitbucket
  config:
    url: https://bitbucket.org/workspace/excel-flattened
    branch: main
    token: ${BITBUCKET_DEST_TOKEN}
    output_path: /

sync:
  depth: 1

converter:
  implementation: noop

flattener:
  implementation: openpyxl
```

### Local Source, Bitbucket Destination

```yaml
source:
  implementation: local_folder
  config:
    folder_path: /path/to/excel/files
    include_patterns:
      - "**/*.xlsx"
    exclude_patterns:
      - "**/~$*"

destination:
  implementation: bitbucket
  config:
    url: https://bitbucket.org/workspace/repo
    branch: main
    token: ${BITBUCKET_TOKEN}
    output_path: flattened/

sync:
  depth: 0  # Local folder mode

converter:
  implementation: noop

flattener:
  implementation: openpyxl
```

### Bitbucket Source, Local Destination

```yaml
source:
  implementation: bitbucket
  config:
    url: https://bitbucket.org/workspace/repo
    branch: main
    token: ${BITBUCKET_TOKEN}
    include_patterns:
      - "**/*.xlsx"
    depth: 1

destination:
  implementation: local_folder
  config:
    folder_path: /output/flattened

sync:
  depth: 1

converter:
  implementation: noop

flattener:
  implementation: openpyxl
```

---

## Where to Put Configuration Files

### Recommended Location (Production)

```
/etc/excel-differ/
├── config/
│   └── excel-differ.yaml
└── .env

# Run with
excel-differ --config /etc/excel-differ/config/excel-differ.yaml
```

### Alternative: User Home Directory

```
~/.excel-differ/
├── config/
│   └── excel-differ.yaml
└── .env

# Run with
excel-differ --config ~/.excel-differ/config/excel-differ.yaml
```

### Alternative: Project Directory

```
/projects/excel-processing/
├── excel-differ/           # Executable or source
├── config/
│   └── excel-differ.yaml
└── .env

# Run with
cd /projects/excel-processing
excel-differ --config config/excel-differ.yaml
```

### Environment Variable (Recommended for CI/CD)

```bash
export EXCEL_DIFFER_CONFIG=/path/to/config/excel-differ.yaml
excel-differ
```

---

## Running in Different Environments

### Local Development

```bash
# From source
cd /path/to/excel-differ
source venv/bin/activate
python main.py --config config/excel-differ.yaml
```

### CI/CD (GitHub Actions Example)

```yaml
name: Flatten Excel Files
on:
  push:
    branches: [main]

jobs:
  flatten:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Excel Differ
        run: |
          pip install -r requirements.txt

      - name: Create config
        run: |
          mkdir -p config
          cat > config/excel-differ.yaml <<EOF
          source:
            implementation: bitbucket
            config:
              url: https://bitbucket.org/${{ github.repository }}
              branch: main
              token: \${{ secrets.BITBUCKET_TOKEN }}
              include_patterns:
                - "**/*.xlsx"
          destination:
            implementation: bitbucket
            config:
              url: https://bitbucket.org/${{ github.repository }}
              branch: main
              token: \${{ secrets.BITBUCKET_TOKEN }}
              output_path: flattened/
          sync:
            depth: 1
          converter:
            implementation: noop
          flattener:
            implementation: openpyxl
          EOF

      - name: Run Excel Differ
        env:
          BITBUCKET_TOKEN: ${{ secrets.BITBUCKET_TOKEN }}
        run: |
          python main.py --config config/excel-differ.yaml
```

### Cron Job (Linux)

```bash
# Add to crontab: crontab -e

# Run every day at 2am
0 2 * * * cd /path/to/excel-differ && source venv/bin/activate && python main.py --config config/excel-differ.yaml >> /var/log/excel-differ.log 2>&1
```

### Windows Scheduled Task

```powershell
# Create scheduled task
$action = New-ScheduledTaskAction -Execute 'C:\path\to\excel-differ.exe' -Argument '--config C:\path\to\config\excel-differ.yaml'
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "Excel Differ Daily"
```

---

## Authentication Setup

### Bitbucket App Password

1. Go to Bitbucket: **Settings → Personal Bitbucket settings → App passwords**
2. Click **Create app password**
3. Name: `excel-differ`
4. Permissions needed:
   - **Repositories:** Read, Write
   - **Pull requests:** Read (optional)
5. Copy the generated password
6. Add to `.env`:
   ```
   BITBUCKET_TOKEN=your_app_password_here
   ```

### Multiple Repositories (Different Tokens)

```bash
# .env
BITBUCKET_SOURCE_TOKEN=token_for_source_repo
BITBUCKET_DEST_TOKEN=token_for_dest_repo
```

```yaml
# config/excel-differ.yaml
source:
  config:
    token: ${BITBUCKET_SOURCE_TOKEN}

destination:
  config:
    token: ${BITBUCKET_DEST_TOKEN}
```

---

## Troubleshooting

### Issue: "Environment variable not set"

**Cause:** `.env` file not found or not loaded

**Solution:**
```bash
# Make sure .env is in the same directory as excel-differ
ls -la .env

# Or specify explicitly
export BITBUCKET_TOKEN=your_token
```

### Issue: "Cannot connect to repository"

**Cause:** Invalid token or URL

**Solution:**
```bash
# Test token manually
curl -u username:token https://api.bitbucket.org/2.0/user

# Verify URL format
# Correct: https://bitbucket.org/workspace/repo
# Wrong: https://bitbucket.org/workspace/repo.git
```

### Issue: "No files found to process"

**Cause:** Patterns don't match any files, or all files already processed

**Solution:**
```yaml
# Check patterns are correct
include_patterns:
  - "**/*.xlsx"  # Recursive
  - "*.xlsx"     # Only root directory

# Verify depth setting
sync:
  depth: 1  # Only last commit
```

### Issue: "Permission denied"

**Cause:** Missing write permissions on destination

**Solution:**
- Verify token has write permissions
- Check repository settings allow pushes
- Verify branch is not protected

---

## Performance Considerations

### Large Repositories

If source repository has many Excel files:

```yaml
source:
  config:
    include_patterns:
      - "reports/2024/**/*.xlsx"  # Narrow scope
    exclude_patterns:
      - "**/archive/**"           # Exclude old files
    depth: 1                       # Only recent changes
```

### Large Files

If Excel files are very large (>50MB):

```yaml
flattener:
  config:
    timeout: 1800  # Increase timeout to 30 minutes
```

### API Rate Limits

If hitting Bitbucket API rate limits:

- Use `depth: 1` to minimize API calls
- Consider switching to local git implementation (GitPython)
- Add delays between operations (future feature)

---

## Security Best Practices

### 1. Never Commit Secrets

```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo "config/excel-differ.yaml" >> .gitignore  # If it contains secrets
```

### 2. Use Environment Variables

```yaml
# Good
token: ${BITBUCKET_TOKEN}

# Bad
token: "your_actual_token_here"
```

### 3. Restrict Token Permissions

- Only grant minimum required permissions
- Use separate tokens for source and destination
- Rotate tokens regularly

### 4. Protect Config Files

```bash
# Restrict permissions
chmod 600 .env
chmod 600 config/excel-differ.yaml
```

---

## Upgrade Guide

### Upgrading from Source

```bash
cd /path/to/excel-differ

# Pull latest changes
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Check for config changes
git diff config/excel-differ.yaml.example

# Run
python main.py --config config/excel-differ.yaml
```

### Upgrading Standalone Executable

```bash
# Download new version
curl -L https://github.com/org/excel-differ/releases/latest/download/excel-differ-linux -o excel-differ-new

# Backup old version
mv excel-differ excel-differ-old

# Replace
mv excel-differ-new excel-differ
chmod +x excel-differ

# Test
./excel-differ --version

# Clean up if successful
rm excel-differ-old
```

---

## Next Steps

After deployment:

1. **Verify Configuration:** Run with `--dry-run` (future feature) to verify config
2. **Test Small Batch:** Start with `depth: 1` to process only recent changes
3. **Monitor Logs:** Check output for warnings or errors
4. **Review Results:** Verify flattened outputs are correct
5. **Automate:** Set up cron job or CI/CD integration
6. **Monitor:** Set up alerts for failures (future feature)

---

## References

- [PROJECT_PLAN.md](PROJECT_PLAN.md) - Current project status
- [ARCHITECTURE_V3.md](ARCHITECTURE_V3.md) - System architecture
- [COMPONENT_SPECIFICATIONS.md](COMPONENT_SPECIFICATIONS.md) - Component details

---

**END OF DEPLOYMENT GUIDE**
