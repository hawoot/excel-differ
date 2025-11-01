# Excel Differ - Architecture V4

**Version:** 4.0
**Date:** 2025-11-01
**Status:** Current

---

## Overview

Excel Differ V4 is a modular, plugin-based system for converting Excel workbooks into version-control-friendly text representations. The V4 architecture emphasizes clean separation, consistent naming, and scalability for future frontend development.

### Key Principles

1. **Separation of Concerns** - Backend (`src/`) ready for frontend sibling
2. **Interface-Driven Design** - All components implement defined interfaces
3. **Configuration-First** - YAML workflow definitions drive behavior
4. **Loose Coupling** - Components communicate only through interfaces
5. **CLI Separation** - All CLI logic extracted from components
6. **Consistent Naming** - Clear, specific names throughout (no vague "core", "config", etc.)

---

## Architecture Diagram

```
┌───────────────────── EXCEL DIFFER V4 ──────────────────────┐
│                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌──────────────┐ │
│  │   CLI       │────▶│ ORCHESTRATOR│────▶│   REGISTRY   │ │
│  │ (3 commands)│     │             │     │              │ │
│  └─────────────┘     └──────┬──────┘     └──────────────┘ │
│                             │                               │
│          ┌──────────────────┼──────────────────┐           │
│          │                  │                  │           │
│          ▼                  ▼                  ▼           │
│    ┌──────────┐       ┌──────────┐      ┌──────────┐     │
│    │  SOURCE  │       │CONVERTER │      │FLATTENER │     │
│    └──────────┘       └──────────┘      └──────────┘     │
│          │                  │                  │           │
│   ┌──────┴──────┐    ┌──────┴──────┐   ┌──────┴──────┐  │
│   │   Local     │    │    NoOp     │   │  Openpyxl   │  │
│   │  Bitbucket  │    │   Windows   │   │    NoOp     │  │
│   └─────────────┘    └─────────────┘   └─────────────┘  │
│                                                            │
│                         ▼                                  │
│                   ┌──────────┐                            │
│                   │DESTINATION│                           │
│                   └──────────┘                            │
│                         │                                  │
│                  ┌──────┴──────┐                          │
│                  │   Local     │                          │
│                  │  Bitbucket  │                          │
│                  └─────────────┘                          │
└────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
excel-differ/
├── src/                              # All backend code
│   ├── interfaces.py                 # Component interfaces
│   ├── registry.py                   # Component registry
│   │
│   ├── components/                   # Component implementations ONLY
│   │   ├── source/                   # Source implementations
│   │   │   ├── local_source.py       # (to be implemented)
│   │   │   └── bitbucket_source.py   # (to be implemented)
│   │   ├── destination/              # Destination implementations
│   │   │   ├── local_destination.py  # (to be implemented)
│   │   │   └── bitbucket_destination.py  # (to be implemented)
│   │   ├── converter/
│   │   │   ├── noop_converter.py
│   │   │   └── windows_converter.py  # (to be implemented)
│   │   └── flattener/
│   │       ├── openpyxl/             # Production flattener
│   │       │   ├── openpyxl_flattener.py
│   │       │   ├── flattener.py
│   │       │   ├── charts.py
│   │       │   ├── sheets.py
│   │       │   └── ... (extraction modules)
│   │       └── noop/
│   │           └── noop_flattener.py
│   │
│   ├── orchestrator/                 # Workflow coordination
│   │   └── orchestrator.py           # (to be implemented)
│   │
│   ├── workflows/                    # Workflow system
│   │   ├── schema.py                 # Workflow dataclasses
│   │   └── loader.py                 # YAML → Python loader
│   │
│   ├── differ/                       # NEW in V4: Diff functionality
│   │   ├── differ.py                 # Core diff logic
│   │   └── formatters/
│   │       ├── json_formatter.py     # JSON output
│   │       └── html_formatter.py     # (to be implemented)
│   │
│   └── cli/                          # NEW in V4: All CLI logic
│       ├── flatten_command.py        # Flatten single file
│       ├── diff_command.py           # Diff two files
│       └── workflow_command.py       # Run full workflow
│
├── workflow_definitions/             # Workflow configurations
│   ├── default.yaml                  # Default workflow
│   └── templates/                    # Example workflows
│       ├── local-to-local.yaml
│       ├── bitbucket-to-local.yaml
│       └── ... (other templates)
│
├── frontend/                         # Placeholder for future UI
├── tests/                            # Test suite
├── docs/                             # Documentation
├── main.py                           # Main entry point
├── .env.example                      # Example environment vars
└── requirements.txt                  # Python dependencies
```

---

## Core Components

### 1. **Interfaces** (`src/interfaces.py`)

Defines contracts for all components:

- **SourceInterface** - Get files from somewhere
- **DestinationInterface** - Upload results somewhere
- **ConverterInterface** - Convert Excel formats
- **FlattenerInterface** - Flatten Excel to text

All implementations must conform to these interfaces.

### 2. **Registry** (`src/registry.py`)

Central registration system for components:

```python
# Register components at startup
def register_all_components():
    registry.register_converter('noop', NoOpConverter)
    registry.register_flattener('openpyxl', OpenpyxlFlattener)
    registry.register_flattener('noop', NoOpFlattener)
    # ... more registrations

# Create instances on demand
flattener = registry.create_flattener('openpyxl', config)
```

### 3. **Workflows** (`src/workflows/`)

YAML-driven workflow system:

- **schema.py** - Workflow dataclass definitions
- **loader.py** - Loads and validates YAML workflows

### 4. **CLI** (`src/cli/`)

Three command-line interfaces:

- **flatten** - Flatten single Excel file
- **diff** - Compare two Excel files
- **workflow** - Run complete workflow (main use case)

All accessed via: `python main.py [command]`

### 5. **Differ** (`src/differ/`) - NEW in V4

On-demand diffing of two Excel files:

1. Flattens both files
2. Compares flattened outputs
3. Returns structured diff (JSON/HTML)

---

## Component Interaction Flow

### Workflow Execution

```
1. main.py
   ├─▶ register_all_components()
   └─▶ CLI command

2. workflow command
   ├─▶ Load YAML (workflow_definitions/default.yaml)
   ├─▶ Create components via registry
   │   ├─▶ Source
   │   ├─▶ Destination
   │   ├─▶ Converter
   │   └─▶ Flattener
   └─▶ Run Orchestrator

3. Orchestrator
   ├─▶ Get sync state (from destination)
   ├─▶ Get changed files (from source)
   └─▶ For each file:
       ├─▶ Download (source)
       ├─▶ Convert (if needed)
       ├─▶ Flatten
       ├─▶ Upload (destination)
       └─▶ Update sync state
```

---

## Configuration System

### YAML Workflow Structure

```yaml
source:
  implementation: <implementation_name>
  config:
    <implementation-specific settings>

destination:
  implementation: <implementation_name>
  config:
    <implementation-specific settings>

converter:
  implementation: <implementation_name>
  config:
    <implementation-specific settings>

flattener:
  implementation: <implementation_name>
  config:
    <implementation-specific settings>
```

### Default Workflow

Located at `workflow_definitions/default.yaml`:

```yaml
source:
  implementation: local_folder
  config:
    folder_path: ./input

destination:
  implementation: local_folder
  config:
    folder_path: ./output

converter:
  implementation: noop
  config: {}

flattener:
  implementation: openpyxl
  config:
    include_computed: false
    include_literal: true
```

---

## CLI Commands

### 1. Flatten Command

Flatten a single Excel file:

```bash
python main.py flatten workbook.xlsx
python main.py flatten workbook.xlsx -o ./output/
```

### 2. Diff Command - NEW in V4

Compare two Excel files:

```bash
python main.py diff file1.xlsx file2.xlsx
python main.py diff file1.xlsx file2.xlsx -o diff-result.json
```

### 3. Workflow Command

Run full workflow:

```bash
python main.py workflow                    # Uses default.yaml
python main.py workflow my-workflow.yaml   # Custom workflow
```

---

## V4 Improvements

### From V3 to V4

1. **Restructured to `src/`**
   - Clear backend/frontend separation
   - Backend code under `src/`
   - Frontend placeholder created

2. **CLI Extraction**
   - All CLI logic moved from components to `src/cli/`
   - Three clear commands: flatten, diff, workflow
   - One entry point: `main.py`

3. **Consistent Naming**
   - No more vague names ("core", "config.py")
   - `openpyxl_flattener.py` instead of `flattener_plugin.py`
   - Specific file names throughout

4. **Differ Module**
   - NEW on-demand diff capability
   - JSON output (HTML coming soon)
   - Standalone feature for comparing files

5. **Default Workflow**
   - `workflow_definitions/default.yaml`
   - Just run `python main.py workflow` - it works!

6. **Auto-Registration**
   - Components registered at startup
   - Single `register_all_components()` function
   - No manual registration in component files

7. **Simplified .env**
   - Only Bitbucket token
   - Everything else in YAML workflows

---

## Implementation Status

### ✅ Completed

- Core interfaces defined
- Component registry system
- Workflow loader and schema
- NoOp converter
- Openpyxl flattener (full implementation)
- NoOp flattener
- Differ module (JSON output)
- All three CLIs (flatten, diff, workflow)
- Default workflow configuration
- Auto-registration system

### ⏳ To Be Implemented

- Orchestrator core logic
- LocalSource component
- LocalDestination component
- BitbucketSource component
- BitbucketDestination component
- HTML differ formatter
- Windows Excel converter

---

## Extension Points

### Adding a New Component

1. **Create implementation:**
   ```python
   # src/components/source/github_source.py
   from src.interfaces import SourceInterface

   class GitHubSource(SourceInterface):
       def __init__(self, config: dict):
           super().__init__(config)

       # Implement interface methods...
   ```

2. **Register in `src/registry.py`:**
   ```python
   def register_all_components():
       # ... existing registrations
       from src.components.source.github_source import GitHubSource
       registry.register_source('github', GitHubSource)
   ```

3. **Use in workflow:**
   ```yaml
   source:
     implementation: github
     config:
       repo: owner/repo
       token: ${GITHUB_TOKEN}
   ```

---

## Security

### Environment Variables

Secrets in `.env` file (git-ignored):

```bash
BITBUCKET_TOKEN=your_app_password
```

Referenced in YAML with `${VAR_NAME}` syntax:

```yaml
source:
  config:
    token: ${BITBUCKET_TOKEN}
```

### Best Practices

1. Never commit `.env` file
2. Use separate tokens for source/destination
3. Restrict token permissions to minimum required
4. Regularly rotate tokens

---

## Testing

### Component Tests

```python
# Test interface compliance
from src.components.flattener.noop.noop_flattener import NoOpFlattener

flattener = NoOpFlattener({'output_dir': './test'})
assert hasattr(flattener, 'flatten')
assert hasattr(flattener, 'get_name')
```

### Integration Tests

```python
# Test workflow loading
from pathlib import Path
from src.workflows.loader import load_workflow

workflow = load_workflow(Path('workflow_definitions/default.yaml'))
assert workflow.flattener.implementation == 'openpyxl'
```

---

## Future Enhancements

1. **Frontend** - Web UI for configuration and visualization
2. **Orchestrator** - Complete implementation
3. **More Sources** - GitHub, GitLab, S3, HTTP
4. **More Destinations** - GitHub, GitLab, S3, Azure Blob
5. **HTML Differ** - Rich visual diff output
6. **Parallel Processing** - Process multiple files concurrently
7. **Dry Run Mode** - Simulate without uploading
8. **Webhooks** - Trigger on repository changes

---

## References

- [COMPONENT_SPECIFICATIONS.md](COMPONENT_SPECIFICATIONS.md) - Interface specifications
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - How to deploy and use
- [PROJECT_PLAN.md](PROJECT_PLAN.md) - Project roadmap and status
- [src/interfaces.py](../src/interfaces.py) - Component interface definitions
- [src/registry.py](../src/registry.py) - Component registration system
- [workflow_definitions/templates/](../workflow_definitions/templates/) - Example workflows

---

**END OF ARCHITECTURE V4 DOCUMENT**
