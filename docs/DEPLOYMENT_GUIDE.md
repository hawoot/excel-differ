# Excel Differ - Deployment Guide

**Last Updated:** 2025-11-01

---

## Table of Contents

1. [What is Excel Differ?](#what-is-excel-differ)
2. [Understanding Workflows](#understanding-workflows)
3. [Installation](#installation)
4. [Creating Your Workflow](#creating-your-workflow)
5. [Available Components](#available-components)
6. [Running Excel Differ](#running-excel-differ)
7. [Common Workflow Examples](#common-workflow-examples)
   - [Example 1: Local Development](#example-1-local-development)
   - [Example 2: Bitbucket to Local](#example-2-bitbucket-to-local)
   - [Example 3: Full Cloud Workflow](#example-3-full-cloud-workflow)
   - [Example 4: Converter-Only Workflow](#example-4-converter-only-workflow)
8. [Authentication Setup](#authentication-setup)
9. [Configuration Reference](#configuration-reference)
10. [Troubleshooting](#troubleshooting)
11. [Advanced Topics](#advanced-topics)
12. [Security Best Practices](#security-best-practices)

---

## What is Excel Differ?

Excel Differ automates the process of:
1. Getting Excel files from a source (Bitbucket, local folder)
2. Converting files if needed (.xlsb → .xlsm)
3. Flattening Excel files to text representations
4. Uploading flattened results to a destination (Bitbucket, local folder)

This makes Excel files version-control friendly and enables meaningful diffs.

---

## Understanding Workflows

Excel Differ is configured using **workflow definitions** - YAML files that describe your complete processing pipeline.

### What is a Workflow Definition?

A workflow definition tells Excel Differ exactly how to process your files:
- **Source**: Where to get Excel files
- **Destination**: Where to upload flattened results
- **Converter**: Whether/how to convert files
- **Flattener**: How to flatten Excel files

### Workflow File Structure

Every workflow YAML file has four required sections:

```yaml
source:
  implementation: <type>
  config:
    <settings>

destination:
  implementation: <type>
  config:
    <settings>

converter:
  implementation: <type>
  config:
    <settings>

flattener:
  implementation: <type>
  config:
    <settings>
```

### Example: Simple Local Workflow

```yaml
# my-workflow.yaml
source:
  implementation: local_folder
  config:
    folder_path: /data/excel
    include_patterns:
      - "**/*.xlsx"

destination:
  implementation: local_folder
  config:
    folder_path: /output

converter:
  implementation: noop
  config: {}

flattener:
  implementation: openpyxl
  config:
    include_computed: false
```

---

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git (for cloning the repository)

### Step 1: Clone Repository

```bash
cd /where/you/want/excel-differ
git clone <repository-url> excel-differ
cd excel-differ
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate        # Linux/Mac
# OR
venv\Scripts\activate           # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Creating Your Workflow

### Step 1: Choose a Template

Excel Differ provides templates for common scenarios:

```
components/workflows/workflow_definition_templates/
├── local-to-local.yaml           # Local folder → Local folder
├── local-to-bitbucket.yaml       # Local folder → Bitbucket
├── bitbucket-to-local.yaml       # Bitbucket → Local folder
├── bitbucket-to-bitbucket.yaml   # Bitbucket → Bitbucket (same repo)
├── converter-only.yaml           # Only conversion, no flattening
└── flattener-only.yaml           # Only flattening, no conversion
```

### Step 2: Copy and Customize

```bash
# Copy a template
cp components/workflows/workflow_definition_templates/local-to-local.yaml my-workflow.yaml

# Edit it
nano my-workflow.yaml
```

### Step 3: Set Up Environment Variables

If your workflow uses secrets (e.g., Bitbucket tokens), create a `.env` file:

```bash
# .env
BITBUCKET_TOKEN=your_app_password_here
```

Your workflow YAML references these with `${VAR}` syntax:

```yaml
source:
  config:
    token: ${BITBUCKET_TOKEN}  # Resolved automatically
```

---

## Available Components

### Source Implementations

| Implementation | Description | Config Keys |
|---------------|-------------|-------------|
| `local_folder` | Read from local directory | `folder_path`, `include_patterns`, `exclude_patterns` |
| `bitbucket` | Read from Bitbucket repository | `url`, `branch`, `token`, `include_patterns`, `depth` |

### Destination Implementations

| Implementation | Description | Config Keys |
|---------------|-------------|-------------|
| `local_folder` | Write to local directory | `folder_path` |
| `bitbucket` | Write to Bitbucket repository | `url`, `branch`, `token`, `output_path` |

### Converter Implementations

| Implementation | Description | Config Keys |
|---------------|-------------|-------------|
| `noop` | No conversion (most common) | None |
| `windows_excel` | Convert using Windows Excel | `timeout` |

### Flattener Implementations

| Implementation | Description | Config Keys |
|---------------|-------------|-------------|
| `openpyxl` | Full Excel flattening | `include_computed`, `include_literal`, `include_formats`, `timeout` |
| `noop` | No flattening (converter-only workflows) | None |

---

## Running Excel Differ

### Command Line

```bash
# With explicit workflow path
python main.py --workflow my-workflow.yaml

# With environment variable
export EXCEL_DIFFER_WORKFLOW=my-workflow.yaml
python main.py
```

### From Python

```python
from pathlib import Path
from components.workflows.workflow_loader import load_workflow
from components.component_registry import registry

# Load workflow
workflow = load_workflow(Path('my-workflow.yaml'))

# Create component instances
source = registry.create_source(
    workflow.source.implementation,
    workflow.source.config
)
# ... create other components and run orchestrator
```

---

## Common Workflow Examples

### Example 1: Local Development

**Scenario**: Process Excel files from local folder, output to another local folder

```yaml
# local-dev.yaml
source:
  implementation: local_folder
  config:
    folder_path: /Users/me/Documents/excel-files
    include_patterns:
      - "**/*.xlsx"
      - "**/*.xlsm"
    exclude_patterns:
      - "**/~$*"  # Temporary files

destination:
  implementation: local_folder
  config:
    folder_path: /Users/me/Documents/flattened-output

converter:
  implementation: noop
  config: {}

flattener:
  implementation: openpyxl
  config:
    include_computed: false
    include_literal: true
    include_formats: true
```

**Run it**:
```bash
python main.py --workflow local-dev.yaml
```

---

### Example 2: Bitbucket to Local

**Scenario**: Pull Excel files from Bitbucket, save flattened outputs locally

```yaml
# bitbucket-to-local.yaml
source:
  implementation: bitbucket
  config:
    url: https://bitbucket.org/myworkspace/excel-repo
    branch: main
    token: ${BITBUCKET_TOKEN}
    include_patterns:
      - "data/**/*.xlsx"
    depth: 1  # Only process latest commit

destination:
  implementation: local_folder
  config:
    folder_path: /output/flattened

converter:
  implementation: noop
  config: {}

flattener:
  implementation: openpyxl
  config:
    include_computed: false
    include_literal: true
    include_formats: true
```

**Setup**:
```bash
# Create .env file
echo "BITBUCKET_TOKEN=your_app_password" > .env

# Run
python main.py --workflow bitbucket-to-local.yaml
```

---

### Example 3: Full Cloud Workflow

**Scenario**: Automated processing within Bitbucket repository

```yaml
# cloud-workflow.yaml
source:
  implementation: bitbucket
  config:
    url: https://bitbucket.org/myworkspace/my-repo
    branch: main
    token: ${BITBUCKET_TOKEN}
    include_patterns:
      - "reports/**/*.xlsx"
      - "data/**/*.xlsm"
    exclude_patterns:
      - "**/archive/**"
    depth: 1

destination:
  implementation: bitbucket
  config:
    url: https://bitbucket.org/myworkspace/my-repo
    branch: main
    token: ${BITBUCKET_TOKEN}
    output_path: flattened/

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
```

**Setup**:
```bash
# .env
BITBUCKET_TOKEN=your_app_password

# Run
python main.py --workflow cloud-workflow.yaml
```

---

### Example 4: Converter-Only Workflow

**Scenario**: Convert .xlsb files to .xlsm, no flattening

```yaml
# converter-only.yaml
source:
  implementation: bitbucket
  config:
    url: https://bitbucket.org/myworkspace/binary-files
    branch: main
    token: ${BITBUCKET_TOKEN}
    include_patterns:
      - "**/*.xlsb"  # Only binary files
    depth: 1

destination:
  implementation: bitbucket
  config:
    url: https://bitbucket.org/myworkspace/converted-files
    branch: main
    token: ${BITBUCKET_TOKEN}
    output_path: converted/

converter:
  implementation: windows_excel
  config:
    timeout: 300

flattener:
  implementation: noop  # No flattening
  config: {}
```

---

## Authentication Setup

### Bitbucket App Password

1. Go to Bitbucket: **Settings → Personal Bitbucket settings → App passwords**
2. Click **Create app password**
3. Name: `excel-differ`
4. Permissions needed:
   - **Repositories:** Read, Write
5. Copy the generated password
6. Add to `.env`:
   ```bash
   BITBUCKET_TOKEN=your_generated_password
   ```

### Multiple Repositories

If you use different repos for source and destination:

```bash
# .env
BITBUCKET_SOURCE_TOKEN=token_for_source_repo
BITBUCKET_DEST_TOKEN=token_for_destination_repo
```

```yaml
# workflow.yaml
source:
  config:
    token: ${BITBUCKET_SOURCE_TOKEN}

destination:
  config:
    token: ${BITBUCKET_DEST_TOKEN}
```

---

## Configuration Reference

### Source: local_folder

```yaml
source:
  implementation: local_folder
  config:
    folder_path: /absolute/path/to/folder  # Required
    include_patterns:                      # Optional
      - "**/*.xlsx"
      - "**/*.xlsm"
    exclude_patterns:                      # Optional
      - "**/~$*"
      - "**/archive/**"
```

### Source: bitbucket

```yaml
source:
  implementation: bitbucket
  config:
    url: https://bitbucket.org/workspace/repo  # Required
    branch: main                                # Required
    token: ${BITBUCKET_TOKEN}                   # Required
    include_patterns:                           # Optional
      - "**/*.xlsx"
    exclude_patterns:                           # Optional
      - "**/temp/**"
    depth: 1                                    # Optional (default: 1)
    # depth = 0: process nothing
    # depth = 1: process latest commit only
    # depth = N: process last N commits
```

### Destination: local_folder

```yaml
destination:
  implementation: local_folder
  config:
    folder_path: /absolute/path/to/output  # Required
```

### Destination: bitbucket

```yaml
destination:
  implementation: bitbucket
  config:
    url: https://bitbucket.org/workspace/repo  # Required
    branch: main                                # Required
    token: ${BITBUCKET_TOKEN}                   # Required
    output_path: flattened/                     # Optional (default: /)
```

### Converter: noop

```yaml
converter:
  implementation: noop
  config: {}  # No configuration needed
```

### Converter: windows_excel

```yaml
converter:
  implementation: windows_excel
  config:
    timeout: 300  # Optional (seconds, default: 300)
```

### Flattener: openpyxl

```yaml
flattener:
  implementation: openpyxl
  config:
    include_computed: false  # Optional (default: false)
    include_literal: true    # Optional (default: true)
    include_formats: true    # Optional (default: true)
    timeout: 900            # Optional (seconds, default: 900)
```

### Flattener: noop

```yaml
flattener:
  implementation: noop
  config: {}  # No configuration needed
```

---

## Troubleshooting

### Issue: "Workflow file not found"

**Error**: `FileNotFoundError: Workflow file not found: my-workflow.yaml`

**Solution**: Provide absolute path or ensure you're in the correct directory
```bash
python main.py --workflow /absolute/path/to/my-workflow.yaml
```

---

### Issue: "Environment variable not set"

**Error**: `ValueError: Environment variable BITBUCKET_TOKEN not set`

**Solution**: Create `.env` file or set environment variable
```bash
# Option 1: Create .env file
echo "BITBUCKET_TOKEN=your_token" > .env

# Option 2: Export variable
export BITBUCKET_TOKEN=your_token
```

---

### Issue: "Unknown implementation"

**Error**: `ValueError: Unknown source implementation 'my_custom'. Available: ['local_folder', 'bitbucket']`

**Solution**: Use a registered implementation or register your custom one

---

### Issue: "Missing required section"

**Error**: `ValueError: Missing required section 'flattener' in workflow file`

**Solution**: Ensure all four sections are present (source, destination, converter, flattener)

---

## Advanced Topics

### Custom Implementations

You can add custom component implementations:

1. Create your implementation:
```python
# components/source/my_custom/my_custom_source.py
from components.interfaces import SourceInterface

class MyCustomSource(SourceInterface):
    # Implement required methods...
    pass
```

2. Register it:
```python
# components/source/my_custom/__init__.py
from components.component_registry import registry
from .my_custom_source import MyCustomSource

registry.register_source('my_custom', MyCustomSource)
```

3. Use in workflow:
```yaml
source:
  implementation: my_custom
  config:
    custom_setting: value
```

---

## Workflow Validation

Before running, you can validate your workflow:

```python
from pathlib import Path
from components.workflows.workflow_loader import load_workflow

try:
    workflow = load_workflow(Path('my-workflow.yaml'))
    print(f"✓ Workflow valid")
    print(f"  Source: {workflow.source.implementation}")
    print(f"  Destination: {workflow.destination.implementation}")
    print(f"  Converter: {workflow.converter.implementation}")
    print(f"  Flattener: {workflow.flattener.implementation}")
except Exception as e:
    print(f"✗ Workflow invalid: {e}")
```

---

## Security Best Practices

1. **Never commit `.env` file**
   ```bash
   echo ".env" >> .gitignore
   ```

2. **Use environment variables for secrets**
   ```yaml
   # Good
   token: ${BITBUCKET_TOKEN}

   # Bad
   token: "hardcoded_secret"
   ```

3. **Restrict token permissions**
   - Only grant minimum required permissions
   - Use separate tokens for source and destination if possible

4. **Protect configuration files**
   ```bash
   chmod 600 .env
   chmod 600 my-workflow.yaml
   ```

---

## Next Steps

1. **Choose a template** from `components/workflows/workflow_definition_templates/`
2. **Customize it** for your needs
3. **Set up authentication** (if using Bitbucket)
4. **Run Excel Differ** with your workflow
5. **Automate** with cron jobs or CI/CD

---

## See Also

- [components/workflows/workflow_schema.py](../components/workflows/workflow_schema.py) - Workflow structure definition
- [components/workflows/workflow_loader.py](../components/workflows/workflow_loader.py) - How workflows are loaded
- [components/workflows/workflow_definition_templates/](../components/workflows/workflow_definition_templates/) - Example workflows
- [COMPONENT_SPECIFICATIONS.md](COMPONENT_SPECIFICATIONS.md) - Full component interface specifications
- [ARCHITECTURE_V3.md](ARCHITECTURE_V3.md) - System architecture overview
