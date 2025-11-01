# Excel Differ - Configuration Examples

This folder contains example configurations for common use cases.

## Available Examples

### 1. [local-to-bitbucket.yaml](local-to-bitbucket.yaml)
**Scenario:** Local Folder → Bitbucket

Process Excel files from a local folder and upload flattened outputs to Bitbucket.

**Use cases:**
- One-time migration of Excel files to version control
- Processing files from network share or local backup
- Manual processing before automating

**Components:**
- Source: `local_folder`
- Destination: `bitbucket`
- Converter: `noop` (no conversion)
- Flattener: `openpyxl`

---

### 2. [bitbucket-to-bitbucket.yaml](bitbucket-to-bitbucket.yaml)
**Scenario:** Bitbucket → Bitbucket (same repo)

Automated flattening within the same repository.

**Use cases:**
- CI/CD workflow that flattens on every push
- Keep flats alongside source files in same repo
- Single repository for both Excel files and flattened outputs

**Components:**
- Source: `bitbucket`
- Destination: `bitbucket` (same repo, different path)
- Converter: `noop`
- Flattener: `openpyxl`

---

### 3. [flattener-only.yaml](flattener-only.yaml)
**Scenario:** Flattening Workflow (No Conversion)

Only flatten Excel files without any format conversion.

**Use cases:**
- Files are already in .xlsx or .xlsm format
- No binary Excel files (.xlsb) to process
- Pure flattening workflow

**Components:**
- Source: `bitbucket`
- Destination: `bitbucket` (different repo)
- Converter: `noop` (explicitly no conversion)
- Flattener: `openpyxl`

---

### 4. [converter-only.yaml](converter-only.yaml)
**Scenario:** Conversion Workflow (No Flattening)

Only convert Excel file formats without flattening.

**Use cases:**
- Converting .xlsb → .xlsm for compatibility
- Migrating from binary format to modern OOXML
- Format standardization without text representation

**Components:**
- Source: `bitbucket`
- Destination: `bitbucket`
- Converter: `windows_excel` or `libreoffice`
- Flattener: `noop` (acts as file copier)

**Result:** Converted Excel files (.xlsm) uploaded as-is, no text flattening.

---

## How to Use

1. **Copy example to your config directory:**
   ```bash
   cp config/examples/bitbucket-to-bitbucket.yaml config/excel-differ.yaml
   ```

2. **Edit configuration:**
   - Replace repository URLs
   - Update file patterns
   - Adjust flattener options

3. **Set environment variables:**
   ```bash
   # .env file
   BITBUCKET_TOKEN=your_app_password_here
   BITBUCKET_SOURCE_TOKEN=source_token  # If different
   BITBUCKET_DEST_TOKEN=dest_token      # If different
   ```

4. **Run Excel Differ:**
   ```bash
   python main.py --config config/excel-differ.yaml
   ```

---

## Configuration Reference

### Source Configuration

```yaml
source:
  implementation: bitbucket | local_folder | github | gitpython
  config:
    # Bitbucket/GitHub/GitPython:
    url: https://bitbucket.org/workspace/repo
    branch: main
    token: ${BITBUCKET_TOKEN}
    depth: 1  # How many commits back if no state

    # Local folder:
    folder_path: /path/to/files

    # Common (all implementations):
    include_patterns:
      - "**/*.xlsx"
    exclude_patterns:
      - "**/archive/**"
```

### Destination Configuration

```yaml
destination:
  implementation: bitbucket | local_folder | github | gitpython
  config:
    # Bitbucket/GitHub/GitPython:
    url: https://bitbucket.org/workspace/repo
    branch: main
    token: ${BITBUCKET_TOKEN}
    output_path: flattened/

    # Local folder:
    folder_path: /output/path
```

### Converter Configuration

```yaml
converter:
  implementation: noop | windows_excel | libreoffice
  config:
    # NoOp: no config needed

    # Windows Excel / LibreOffice:
    timeout: 300
```

### Flattener Configuration

```yaml
flattener:
  implementation: openpyxl | noop
  config:
    # Openpyxl:
    include_computed: false
    include_literal: true
    include_formats: true
    timeout: 900

    # NoOp: no config needed
```

---

## Common Scenarios

### Scenario: CI/CD Automated Flattening

Use [bitbucket-to-bitbucket.yaml](bitbucket-to-bitbucket.yaml) with depth=1 to only process latest changes.

### Scenario: Bulk Migration

Use [local-to-bitbucket.yaml](local-to-bitbucket.yaml) with depth=0 (or omit sync state file) to process all files.

### Scenario: Format Conversion Only

Use [converter-only.yaml](converter-only.yaml) to convert .xlsb to .xlsm without flattening.

### Scenario: Separate Repos for Source and Output

Use [flattener-only.yaml](flattener-only.yaml) as template, with different URLs for source and destination.

---

## Troubleshooting

**Issue:** "No files found to process"
- Check `include_patterns` match your files
- Verify `exclude_patterns` aren't too broad
- Check `depth` setting (0 = do nothing)

**Issue:** "Cannot convert .xlsb files"
- Using `NoOpConverter` with .xlsb files
- Change converter to `windows_excel` or `libreoffice`

**Issue:** "Authentication failed"
- Verify token in `.env` file
- Check token has correct permissions (read + write)
- Ensure token isn't expired

---

## Next Steps

After configuring:
1. Test with `depth: 1` to process only recent changes
2. Review uploaded outputs
3. Adjust patterns and options as needed
4. Automate with CI/CD or cron

See [DEPLOYMENT_GUIDE.md](../../docs/DEPLOYMENT_GUIDE.md) for complete deployment instructions.
