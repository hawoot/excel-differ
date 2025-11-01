# Excel Differ - Workflow Definition Templates

This folder contains example workflow definitions for common scenarios.

## What is a Workflow Definition?

A workflow definition is a YAML file that tells Excel Differ:
- **Where** to get Excel files (source)
- **Where** to upload flattened results (destination)
- **Whether** to convert files (converter)
- **How** to flatten files (flattener)

## Available Templates

### 1. local-to-local.yaml
**Scenario:** Process files from one local folder, output to another
**Use case:** Local development, testing, or standalone processing

```yaml
source: local_folder
destination: local_folder
```

### 2. local-to-bitbucket.yaml
**Scenario:** Process files from local folder, upload to Bitbucket
**Use case:** Local source of truth, cloud backup of flattened outputs

```yaml
source: local_folder
destination: bitbucket
```

### 3. bitbucket-to-local.yaml
**Scenario:** Pull files from Bitbucket, save outputs locally
**Use case:** Work with cloud files, keep flattened outputs local

```yaml
source: bitbucket
destination: local_folder
```

### 4. bitbucket-to-bitbucket.yaml
**Scenario:** Pull files from Bitbucket, upload outputs back to same repo
**Use case:** Fully automated cloud workflow, everything in one place

```yaml
source: bitbucket (same repo)
destination: bitbucket (same repo)
```

### 5. converter-only.yaml
**Scenario:** Only convert .xlsb → .xlsm, no flattening
**Use case:** Format conversion workflow without flattening

```yaml
converter: windows_excel
flattener: noop
```

### 6. flattener-only.yaml
**Scenario:** Only flatten Excel files, no conversion
**Use case:** Standard flattening workflow for .xlsx and .xlsm files

```yaml
converter: noop
flattener: openpyxl
```

## Using These Templates

### Option 1: Copy and Customize
```bash
# Copy template to your own workflow file
cp components/workflows/workflow_definition_templates/local-to-local.yaml my-workflow.yaml

# Edit your workflow file
nano my-workflow.yaml

# Run Excel Differ with your workflow
python main.py --workflow my-workflow.yaml
```

### Option 2: Use Directly
```bash
# Use template directly
python main.py --workflow components/workflows/workflow_definition_templates/local-to-local.yaml
```

## Environment Variables

Templates use `${VAR}` syntax for secrets. Create a `.env` file:

```bash
# .env
BITBUCKET_TOKEN=your_app_password
BITBUCKET_SOURCE_TOKEN=source_token
BITBUCKET_DEST_TOKEN=dest_token
```

Then the workflow loader automatically resolves these references.

## Customization

Each template can be customized:
- Change URLs and paths
- Add/remove file patterns
- Adjust flattener settings
- Change component implementations

See [workflow_schema.py](../workflow_schema.py) for all available options.

## See Also

- [../workflow_schema.py](../workflow_schema.py) - Workflow structure definition
- [../workflow_loader.py](../workflow_loader.py) - How workflows are loaded
- [../../component_registry.py](../../component_registry.py) - Available components
- [../../../docs/DEPLOYMENT_GUIDE.md](../../../docs/DEPLOYMENT_GUIDE.md) - Full deployment guide
