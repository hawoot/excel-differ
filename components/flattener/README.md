# Excel Differ - Flattener Component

This component contains multiple flattener implementations for converting Excel workbooks into text representations.

## Structure

```
flattener/
├── __init__.py            # Component-level imports
├── README.md              # This file
│
├── openpyxl_impl/         # Openpyxl-based flattener (production)
│   ├── src/               # Source code
│   ├── tests/             # Tests
│   ├── docs/              # Documentation
│   ├── venv/              # Virtual environment
│   └── README.md          # Openpyxl flattener docs
│
├── noop/                  # NoOp flattener (file copier)
│   ├── __init__.py
│   └── noop_flattener.py
│
├── scripts/               # Shared build and run scripts
│   ├── run_flattener.sh
│   ├── build_package.sh
│   └── requirements.txt
│
├── snippets/              # Shared sample files
│   └── sample.xlsx
│
└── (future implementations like pandas/, xlrd/, etc.)
```

## Available Implementations

### 1. OpenpyxlFlattener (`openpyxl_impl/`)

**Status:** ✅ Production Ready (v2.1.0)

**Purpose:** Full-featured Excel flattening using openpyxl library

**Features:**
- Extracts formulas (by row and by column)
- Extracts literal values, computed values, formats
- Extracts VBA macros
- Extracts charts, tables, named ranges
- Generates manifest with file hashes

**See:** [openpyxl_impl/README.md](openpyxl_impl/README.md) for complete documentation

---

### 2. NoOpFlattener (`noop/`)

**Status:** ✅ Available

**Purpose:** Explicit no-flattening for converter-only workflows

**Features:**
- Acts as file copier
- Creates timestamped directory
- Copies file as-is without processing

**Use cases:**
- Converter-only workflows (e.g., .xlsb → .xlsm conversion without flattening)
- Simple file copying with versioning

---

## Usage

### In Configuration

```yaml
# config/excel-differ.yaml

flattener:
  implementation: openpyxl  # or 'noop'
  config:
    # OpenpyxlFlattener config:
    include_computed: false
    include_literal: true
    include_formats: true
    timeout: 900

    # NoOpFlattener config:
    # output_dir: ./tmp/noop-flattener
```

### In Code

```python
from components.flattener import OpenpyxlFlattener, NoOpFlattener
from pathlib import Path

# Use Openpyxl flattener
flattener = OpenpyxlFlattener(config={
    'include_computed': False,
    'output_dir': './tmp/flats'
})

result = flattener.flatten(
    excel_file=Path('workbook.xlsx'),
    origin_repo='https://bitbucket.org/org/repo',
    origin_commit='abc123'
)

# Or use NoOp flattener
noop = NoOpFlattener(config={'output_dir': './tmp/copies'})
result = noop.flatten(excel_file=Path('workbook.xlsx'))
```

---

## Adding New Implementations

To add a new flattener implementation:

1. **Create subfolder:**
   ```bash
   mkdir -p components/flattener/myimpl
   ```

2. **Implement FlattenerInterface:**
   ```python
   # components/flattener/myimpl/my_flattener.py

   from components.core.interfaces import FlattenerInterface, FlattenResult

   class MyFlattener(FlattenerInterface):
       def __init__(self, config: dict):
           super().__init__(config)

       def flatten(self, excel_file, ...):
           # Implementation
           pass

       def get_name(self):
           return "MyFlattener"
   ```

3. **Register in plugin registry:**
   ```python
   # In main.py or component initialization
   from components.core.plugin_registry import registry
   from components.flattener.myimpl import MyFlattener

   registry.register_flattener('myimpl', MyFlattener)
   ```

4. **Use in config:**
   ```yaml
   flattener:
     implementation: myimpl
     config: {}
   ```

---

## References

- [openpyxl_impl/README.md](openpyxl_impl/README.md) - Complete Openpyxl flattener documentation
- [../../docs/COMPONENT_SPECIFICATIONS.md](../../docs/COMPONENT_SPECIFICATIONS.md) - FlattenerInterface specification
- [../../docs/ARCHITECTURE_V3.md](../../docs/ARCHITECTURE_V3.md) - Overall architecture

---

**See individual implementation folders for detailed documentation.**
