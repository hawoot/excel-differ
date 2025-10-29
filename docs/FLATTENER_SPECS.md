# Excel Workbook Flattener - Complete Specifications

**Version:** 2.0
**Date:** 2025-10-29
**Status:** Authoritative Specification

---

## 1. Purpose & Scope

The **Excel Workbook Flattener** is a standalone component that transforms binary Excel workbooks (`.xlsx`, `.xlsm`, `.xlsb`, `.xls`) into deterministic, human-readable, version-control-friendly text representations.

### What it does:
- Extracts **all** content from Excel workbooks into structured text files
- Produces **deterministic** output (same input → same output, always)
- Enables **meaningful git diffs** of Excel file changes
- Preserves **complete fidelity** of workbook structure and content
- Creates **manifests** for verification and tooling

### What it does NOT do:
- Does NOT provide diff functionality (separate component)
- Does NOT provide git integration (separate component)
- Does NOT provide API/server functionality (separate component)
- Does NOT recompute formula values (uses cached values only)

---

## 2. Core Requirements

### 2.1 Input Requirements

**Supported Input Formats:**
- `.xlsx` - Office Open XML Workbook (primary format)
- `.xlsm` - Office Open XML Macro-Enabled Workbook (primary format)
- `.xlsb` - Excel Binary Workbook (requires conversion via LibreOffice)
- `.xls` - Excel 97-2003 Workbook (requires conversion via LibreOffice)

**Input Constraints:**
- Maximum file size: Configurable (default: 200 MB)
- File must not be corrupted or invalid
- Password-protected workbooks: Extraction fails (cannot open)
- Password-protected VBA: VBA extraction fails but workbook extraction succeeds with warnings

**Input Validation:**
- File must exist and be readable
- File extension must match actual file format
- File must be a valid Excel workbook (can be opened by openpyxl or LibreOffice)

### 2.2 Output Requirements

**Output Structure:**
```
<snapshot-root>/
├── manifest.json                           # Canonical manifest
├── original/
│   └── <original-filename>                 # Original binary file
├── workbook/
│   ├── metadata.txt                        # Workbook metadata
│   ├── structure.txt                       # Sheet structure
│   ├── defined_names.txt                   # Named ranges
│   ├── calculation_chain.txt               # Calculation order
│   ├── external_links.txt                  # External references
│   ├── connections.txt                     # Data connections
│   └── addins.txt                          # Add-in references
├── sheets/
│   ├── 01.<SheetName>.metadata.json        # Per-sheet metadata
│   ├── 01.<SheetName>.formulas.txt         # Formula cells
│   ├── 01.<SheetName>.values_hardcoded.txt # Non-formula cell values
│   ├── 01.<SheetName>.values_evaluated.txt # All cell values (optional)
│   ├── 01.<SheetName>.cell_formats.txt     # Cell formatting
│   ├── 01.<SheetName>.merged_ranges.txt    # Merged cell ranges
│   ├── 01.<SheetName>.data_validations.txt # Data validation rules
│   └── 01.<SheetName>.comments.txt         # Cell comments
├── tables/
│   ├── <TableName>.definition.txt          # Table structure
│   └── <TableName>.data.csv                # Table data (optional)
├── charts/
│   ├── <ChartName>.metadata.txt            # Chart definition
│   └── <ChartName>.xml                     # Raw chart XML (fallback)
├── pivots/
│   └── <PivotName>.definition.txt          # Pivot table definition
├── vba/
│   ├── vbaProject.bin                      # Raw VBA binary (always kept)
│   ├── <ModuleName>.bas                    # Standard modules
│   ├── <ClassName>.cls                     # Class modules
│   └── <FormName>.frm                      # UserForms
├── styles/
│   ├── cell_styles.txt                     # Named cell styles
│   ├── number_formats.txt                  # Custom number formats
│   └── theme.txt                           # Theme colors/fonts
└── logs/
    └── extraction.log                      # Extraction warnings/errors
```

**Snapshot Root Naming:**
- Format: `<filename>-snapshot-<ISO8601-timestamp>-<sha256-short>`
- Example: `budget-snapshot-20251027T143022Z-a3f5c8d1`
- Timestamp: ISO8601 UTC format (YYYYMMDDTHHMMSSsZ)
- SHA256: First 8 characters of original file hash

**Output Encoding & Line Endings:**
- All text files: UTF-8 encoding
- All text files: Unix line endings (LF, `\n`)
- All text files: End with single newline character
- Binary files: Preserve original encoding (original file, vbaProject.bin)

---

## 3. Extraction Modules

### 3.1 Workbook Metadata (`workbook/metadata.txt`)

**Purpose:** Extract workbook-level properties and metadata.

**Format:** Key-value pairs, one per line
```
# Workbook Metadata
# ==================

Author: John Doe
Last Modified By: Jane Smith
Created: 2024-01-15T08:30:00Z
Modified: 2025-10-27T14:22:00Z
Title: Q4 Budget Report
Subject: Finance
Description: Annual budget projections
Keywords: budget, finance, Q4
Category: Financial Reports
Company: Acme Corp
Excel Version: 16.0
Calculation Mode: auto
Locale: en-US
```

**Required Fields:**
- `Author`: Creator name (empty string if not set)
- `Last Modified By`: Last modifier name
- `Created`: Creation timestamp (ISO8601)
- `Modified`: Last modification timestamp (ISO8601)
- `Excel Version`: Excel version or "unknown"
- `Calculation Mode`: auto, manual, or autoNoTable
- `Locale`: Workbook locale (default: en-US)

**Optional Fields:**
- `Title`, `Subject`, `Description`, `Keywords`, `Category`, `Company`

**Implementation Notes:**
- Use `openpyxl.workbook.properties` to extract properties
- Handle missing properties gracefully (empty strings)
- Format datetimes as ISO8601 UTC

---

### 3.2 Workbook Structure (`workbook/structure.txt`)

**Purpose:** Document sheet order, visibility, and identifiers.

**Format:** Tab-delimited with header
```
# Sheet Structure
# INDEX	NAME	SHEET_ID	VISIBLE	STATE	TAB_COLOR

1	Dashboard	1	TRUE	visible	#FF5733
2	Data	2	TRUE	visible
3	Hidden	3	FALSE	hidden
4	Archive	4	FALSE	veryHidden
```

**Columns:**
- `INDEX`: 1-based sheet position (preserves tab order)
- `NAME`: Sheet name (exact, including spaces/special chars)
- `SHEET_ID`: Internal Excel sheet ID (integer)
- `VISIBLE`: TRUE or FALSE (boolean convenience)
- `STATE`: visible, hidden, or veryHidden (Excel's three visibility states)
- `TAB_COLOR`: Hex color (#RRGGBB) or theme reference (theme:N) or empty

**Sorting:** By INDEX (ascending)

**Implementation Notes:**
- Iterate `workbook.worksheets` to preserve order
- Use `sheet.sheet_state` for visibility
- Extract `sheet.sheet_properties.tabColor` for color
- Handle missing tab colors (empty string)

---

### 3.3 Defined Names (`workbook/defined_names.txt`)

**Purpose:** Extract named ranges and constants.

**Format:** Tab-delimited with header
```
# Defined Names
# NAME	SCOPE	REFERS_TO

Revenue	Workbook	Dashboard!$B$2:$B$13
TaxRate	Workbook	0.21
MonthNames	Data	Data!$A$1:$A$12
_xlnm._FilterDatabase	Data	Data!$A$1:$F$100
```

**Columns:**
- `NAME`: Name identifier (case-sensitive)
- `SCOPE`: Either "Workbook" (global) or sheet name (sheet-scoped)
- `REFERS_TO`: Reference formula (cell range, constant, or expression)

**Sorting:** By SCOPE (workbook first, then sheets alphabetically), then by NAME

**Special Names:**
- Names starting with `_xlnm.` are Excel built-in names (e.g., filter ranges, print areas)
- Include all names, even hidden/internal ones

**Implementation Notes:**
- Use `workbook.defined_names.items()`
- Handle `destinations` attribute for cell references
- For constants (no destinations), use `defn.value`
- Normalize cell references to uppercase

---

### 3.4 Calculation Chain (`workbook/calculation_chain.txt`)

**Purpose:** Document formula calculation order.

**Format:** One reference per line
```
# Calculation Chain
# (Order in which Excel evaluates formulas)

Dashboard!C2
Dashboard!C3
Dashboard!D2
Data!E5
Summary!B10
```

**Implementation Status:** **NOT YET IMPLEMENTED**
- Placeholder file created with comment: `# Calculation chain (not yet implemented)`
- Future: Parse `xl/calcChain.xml` from workbook ZIP
- Useful for debugging circular references and performance

---

### 3.5 External Links (`workbook/external_links.txt`)

**Purpose:** Document references to other workbooks.

**Format:** Tab-delimited with header
```
# External Links
# LINK_ID	TYPE	TARGET

1	external	[Budget2024.xlsx]Sheet1!$A$1:$C$10
2	external	\\server\share\data.xlsx
```

**Implementation Status:** **NOT YET IMPLEMENTED**
- Placeholder file created
- Future: Parse `xl/externalLinks/` from workbook ZIP
- Important for tracking workbook dependencies

---

### 3.6 Data Connections (`workbook/connections.txt`)

**Purpose:** Document database/web/query connections.

**Format:** Tab-delimited with header
```
# Data Connections
# NAME	TYPE	CONNECTION_STRING

SalesDB	ODBC	DRIVER={SQL Server};SERVER=sql01;DATABASE=Sales
WebData	Web	https://api.example.com/data
QueryTable	OLEDB	Provider=Microsoft.ACE.OLEDB.12.0;Data Source=C:\data.xlsx
```

**Implementation Status:** **NOT YET IMPLEMENTED**
- Placeholder file created
- Future: Parse `xl/connections.xml`
- Critical for understanding data sources

---

### 3.7 Add-ins (`workbook/addins.txt`)

**Purpose:** Document Excel add-ins referenced by workbook.

**Format:** One per line
```
# Add-ins Referenced

Analysis ToolPak (GUID: {12345678-1234-1234-1234-123456789ABC})
CustomFunctions.xlam
C:\AddIns\MyTools.xlam
```

**Implementation Status:** **NOT YET IMPLEMENTED**
- Placeholder file created
- Future: Parse workbook XML for add-in references
- Important for formula interpretation

---

## 4. Sheet-Level Extraction

### 4.1 Sheet Metadata (`sheets/01.<SheetName>.metadata.json`)

**Purpose:** Store sheet-level properties.

**Format:** JSON
```json
{
  "sheetId": 1,
  "visible": true,
  "state": "visible",
  "tab_color": "#FF5733",
  "protection": {
    "sheet_protected": true,
    "password": true
  }
}
```

**Fields:**
- `sheetId`: Internal Excel sheet ID (integer)
- `visible`: Boolean convenience flag
- `state`: "visible", "hidden", or "veryHidden"
- `tab_color`: Hex color or theme reference (optional)
- `protection`: Object describing protection (optional)
  - `sheet_protected`: Boolean
  - `password`: Boolean (true if password set, doesn't expose password)

---

### 4.2 Formulas (`sheets/01.<SheetName>.formulas.txt`)

**Purpose:** Extract all formula cells.

**Format:** Tab-delimited with header
```
# Formulas
# ADDRESS	FORMULA

A1	=SUM(B1:B10)
A2	=B2*$C$1
A3	=IF(B3>100,"High","Low")
D5	=VLOOKUP(A5,Data!$A$1:$C$100,2,FALSE)
```

**Columns:**
- `ADDRESS`: Cell address (e.g., A1, B2, AA100)
- `FORMULA`: Normalized formula (with leading =)

**Sorting:** Row-major order (A1, A2, A3, ..., B1, B2, ...)

**Formula Normalization Rules:**
1. **Preserve leading `=`**: Always include equals sign
2. **Function names uppercase**: `SUM` not `sum`, `VLOOKUP` not `vlookup`
3. **Trim whitespace**: No leading/trailing spaces
4. **Preserve structure**: Do NOT simplify or rewrite logic
5. **Preserve references**: Keep absolute ($A$1) vs relative (A1) as-is
6. **Preserve operators**: Keep spaces around operators as-is (for now)
7. **Case sensitivity**: Cell references uppercase (A1 not a1)

**Edge Cases:**
- Array formulas: Preserve `{=formula}` syntax
- Shared formulas: Expand to individual cell references
- Named ranges in formulas: Keep as-is (e.g., `=SUM(Revenue)`)
- External references: Keep as-is (e.g., `=[other.xlsx]Sheet1!A1`)

---

### 4.3 Hardcoded Values (`sheets/01.<SheetName>.values_hardcoded.txt`)

**Purpose:** Extract values from non-formula cells only.

**Format:** Tab-delimited with header
```
# Hard-coded Values (non-formula cells only)
# ADDRESS	VALUE

B1	Revenue
B2	1250000
B3	1300000
C1	Tax Rate
C2	0.21
D1	Approved
D2	TRUE
E1	2025-01-15T00:00:00Z
```

**Columns:**
- `ADDRESS`: Cell address
- `VALUE`: Normalized value (see normalization rules below)

**Sorting:** Row-major order

**MANDATORY:** This file is always created, even if empty.

**Value Normalization Rules:**

**Numbers:**
- Plain decimal notation (no commas, no currency symbols)
- Up to 15 significant digits (Excel's precision limit)
- Integers without decimal point: `100` not `100.0`
- Floats with minimal precision: `3.14159265358979` (15 sig figs max)
- Avoid scientific notation unless necessary (very large/small numbers)

**Strings:**
- Preserve exact content
- Normalize line endings to `\n` (LF)
- No escaping needed (tab-delimited format handles it)
- Empty strings: Empty value column

**Booleans:**
- `TRUE` or `FALSE` (uppercase)

**Dates:**
- ISO8601 format with timezone: `2025-01-15T00:00:00Z`
- UTC preferred
- Include time component even if midnight

**Null/Empty:**
- Empty cells: Not included in file at all (no row)

---

### 4.4 Evaluated Values (`sheets/01.<SheetName>.values_evaluated.txt`)

**Purpose:** Extract displayed values for all cells (formulas and hardcoded).

**Status:** OPTIONAL - Created only when `include_evaluated=true`

**Format:** Tab-delimited with header
```
# Evaluated Values (all cells, including formula results)
# ADDRESS	VALUE

A1	12500|cached
A2	2625|cached
B1	Revenue
B2	1250000
```

**Columns:**
- `ADDRESS`: Cell address
- `VALUE`: Displayed value, optionally with `|cached` or `|computed` suffix

**Value Source:**
- Formula cells: Cached values from workbook (Excel stores last computed result)
- Non-formula cells: Same as hardcoded values
- **NOT recomputed**: Flattener does not recalculate formulas

**Note on Volatile Functions:**
- Functions like `NOW()`, `RAND()`, `TODAY()` produce cached values
- Values may be stale if workbook hasn't been recalculated
- Manifest should note if volatile functions detected

**Implementation Limitation:**
- With `openpyxl`, loading `data_only=False` gives formulas but not cached values
- To get cached values, need to reload workbook with `data_only=True`
- Current implementation: Uses cached values if available, otherwise marks as unavailable

---

### 4.5 Cell Formats (`sheets/01.<SheetName>.cell_formats.txt`)

**Purpose:** Extract cell formatting (fonts, fills, alignment, number formats).

**Format:** Tab-delimited with header
```
# Cell Formats
# ADDRESS	FORMAT

A1	font:name=Calibri,size=11,bold,color=#000000|fill:pattern=solid,fgColor=#FFC000|align:h=center,v=center
B2	number_format:$#,##0.00|font:bold,color=#FF0000
C3	border:yes|align:wrap
```

**Columns:**
- `ADDRESS`: Cell address
- `FORMAT`: Pipe-delimited list of format components

**Format Components:**

**Number Format:**
- Syntax: `number_format:<format_code>`
- Examples:
  - `number_format:0.00` (two decimal places)
  - `number_format:$#,##0.00` (currency)
  - `number_format:yyyy-mm-dd` (date)
  - `number_format:@` (text)
- Skip if format is "General" (default)

**Font:**
- Syntax: `font:<attribute1>,<attribute2>,...`
- Attributes:
  - `name=<font-name>` (e.g., Calibri, Arial)
  - `size=<points>` (e.g., 11, 14)
  - `bold` (flag)
  - `italic` (flag)
  - `underline` (flag)
  - `color=<hex>` (e.g., #FF0000 or theme:1)
- Example: `font:name=Arial,size=12,bold,color=#FF0000`

**Fill:**
- Syntax: `fill:pattern=<pattern>,fgColor=<hex>,bgColor=<hex>`
- Patterns: solid, darkGray, lightGray, etc.
- Example: `fill:pattern=solid,fgColor=#FFC000`
- Skip if no fill (pattern=none)

**Alignment:**
- Syntax: `align:<attribute1>,<attribute2>,...`
- Attributes:
  - `h=<horizontal>` (left, center, right, justify, etc.)
  - `v=<vertical>` (top, center, bottom)
  - `wrap` (flag for wrap text)
  - `indent=<number>`
- Example: `align:h=center,v=top,wrap`

**Border:**
- Simplified: `border:yes` (if any borders present)
- Future: Detail each border side and style

**Sorting:** Row-major order

**Optimization:**
- Only include cells with non-default formatting
- Skip cells with all default values

---

### 4.6 Merged Ranges (`sheets/01.<SheetName>.merged_ranges.txt`)

**Purpose:** Document merged cell ranges.

**Format:** One range per line
```
# Merged Ranges

A1:C1
E5:E7
B10:D12
```

**Sorting:** Lexicographic (A1:C1 before B10:D12)

**Implementation Notes:**
- Use `sheet.merged_cells.ranges`
- Convert range objects to strings (e.g., "A1:C1")

---

### 4.7 Data Validations (`sheets/01.<SheetName>.data_validations.txt`)

**Purpose:** Extract data validation rules.

**Format:** Tab-delimited with header
```
# Data Validations
# RANGE	TYPE	FORMULA

A2:A100	list	Data!$A$1:$A$10
B2:B100	whole	>=0
C2:C100	date	>=TODAY()
```

**Columns:**
- `RANGE`: Cell range(s) where validation applies
- `TYPE`: Validation type (list, whole, decimal, date, time, textLength, custom)
- `FORMULA`: Validation formula or range reference

**Sorting:** By RANGE (lexicographic)

---

### 4.8 Comments (`sheets/01.<SheetName>.comments.txt`)

**Purpose:** Extract cell comments (notes).

**Format:** Tab-delimited with header
```
# Comments
# ADDRESS	AUTHOR|TEXT

A1	John Doe|This is the revenue cell. Update monthly.
B5	Jane Smith|TODO: Verify this formula
```

**Columns:**
- `ADDRESS`: Cell address
- `AUTHOR|TEXT`: Author name, pipe separator, comment text

**Text Normalization:**
- Replace `\n` (newline) with `\\n` (escaped)
- Remove `\r` (carriage return)
- Preserve exact text content

**Sorting:** Row-major order

---

## 5. Tables Extraction

### 5.1 Table Definition (`tables/<TableName>.definition.txt`)

**Purpose:** Extract Excel Table (ListObject) structure.

**Format:** Multi-section text file
```
# Table: Sales
# ============

Name: Sales
Range: Data!$A$1:$F$100
Header Row: TRUE
Totals Row: FALSE
Table Style: TableStyleMedium2

Columns:
  1. Date (type: date)
  2. Region (type: string)
  3. Product (type: string)
  4. Quantity (type: number)
  5. Price (type: currency)
  6. Total (type: formula)

Column Formulas:
  Total: =[@Quantity]*[@Price]
```

**Implementation Status:** **NOT YET IMPLEMENTED**
- Placeholder files created
- Future: Use `sheet.tables` or parse `xl/tables/` XML

---

### 5.2 Table Data (`tables/<TableName>.data.csv`)

**Purpose:** Export table data as CSV (optional).

**Status:** OPTIONAL - Only create if explicitly requested

**Format:** Standard CSV with headers
```csv
Date,Region,Product,Quantity,Price,Total
2025-01-15,West,Widget A,100,19.99,1999.00
2025-01-16,East,Widget B,50,29.99,1499.50
```

**Implementation Notes:**
- Export raw values (not formulas)
- Use standard CSV escaping for strings
- Useful for quick data inspection without Excel

---

## 6. Charts Extraction

### 6.1 Chart Metadata (`charts/<ChartName>.metadata.txt`)

**Purpose:** Document chart properties and data sources.

**Format:** Multi-section text file
```
# Chart: Revenue Trend
# ====================

Type: lineChart
Title: Monthly Revenue Trend
Source Sheet: Dashboard

Series:
  1. Revenue (Data!$B$2:$B$13)
  2. Target (Data!$C$2:$C$13)

Category Axis: Data!$A$2:$A$13 (Month names)

X-Axis: Months
Y-Axis: Revenue ($)

Legend Position: right
```

**Implementation Status:** **NOT YET IMPLEMENTED**
- Parsing chart XML is complex
- Fallback: Save raw XML (see below)

---

### 6.2 Chart XML (`charts/<ChartName>.xml`)

**Purpose:** Preserve raw chart XML for charts that can't be parsed.

**Format:** Raw XML from workbook
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart">
  ...
</c:chartSpace>
```

**Implementation:** Always extract raw XML as fallback

---

## 7. Pivot Tables Extraction

### 7.1 Pivot Definition (`pivots/<PivotName>.definition.txt`)

**Purpose:** Document pivot table structure.

**Format:** Multi-section text file
```
# Pivot: Sales Analysis
# =====================

Source Data: Data!$A$1:$F$1000
Location: Summary!$A$1

Row Fields:
  - Region
  - Product

Column Fields:
  - Quarter

Data Fields:
  - Sum of Revenue
  - Count of Orders

Filters:
  - Year = 2025
```

**Implementation Status:** **NOT YET IMPLEMENTED**
- Very complex to parse (requires understanding PivotTable cache)
- Low priority for initial implementation

---

## 8. VBA Extraction

### 8.1 VBA Project Binary (`vba/vbaProject.bin`)

**Purpose:** Preserve complete VBA project binary.

**Implementation:** ALWAYS extract and save, even if modules can't be parsed.

**Extraction Method:**
- For `.xlsm` files: Extract `xl/vbaProject.bin` from ZIP
- Use `zipfile` or `openpyxl` to access

**Rationale:**
- Complete preservation of VBA state
- Allows re-extraction if parser improves
- Can diff binary files (though not human-readable)

---

### 8.2 VBA Modules (`vba/<ModuleName>.bas`)

**Purpose:** Extract VBA source code as text.

**Format:** Plain text (VBA syntax)
```vb
Attribute VB_Name = "Module1"
Sub CalculateRevenue()
    Dim total As Double
    total = Application.WorksheetFunction.Sum(Range("B2:B10"))
    MsgBox "Total Revenue: " & Format(total, "$#,##0.00")
End Sub
```

**Module Types:**
- Standard Modules: `.bas` extension
- Class Modules: `.cls` extension
- UserForms: `.frm` extension

**Extraction Tool:** `oletools.olevba`
```python
from oletools.olevba import VBA_Parser
vba = VBA_Parser(workbook_path)
for (filename, stream_path, vba_filename, vba_code) in vba.extract_all_macros():
    # Save vba_code to file
```

**Password-Protected VBA:**
- If extraction fails with password error:
  - Create marker file: `<ModuleName>.EXTRACTION_PROTECTED`
  - Add warning to `manifest.json`
  - Keep `vbaProject.bin` intact

**Normalization:**
- **DO NOT** reformat or modify VBA code
- Preserve line endings as extracted (then normalize to LF)
- Preserve exact indentation and spacing
- Critical for accurate diffs

---

## 9. Styles Extraction

### 9.1 Cell Styles (`styles/cell_styles.txt`)

**Purpose:** Document named cell styles.

**Format:** Multi-section text file
```
# Cell Styles
# ===========

Style: Heading 1
  Font: Calibri, 14pt, bold, #1F4E78
  Fill: #D9E1F2
  Alignment: left, top

Style: Currency
  Number Format: $#,##0.00
  Font: Calibri, 11pt
  Alignment: right, center
```

**Implementation Status:** **NOT YET IMPLEMENTED**
- Use `workbook.style_names` and `workbook._named_styles`

---

### 9.2 Number Formats (`styles/number_formats.txt`)

**Purpose:** List custom number formats.

**Format:** Tab-delimited with header
```
# Custom Number Formats
# ID	FORMAT

164	"Revenue: "$#,##0.00
165	[Red]$#,##0.00;[Blue]$#,##0.00
166	yyyy-mm-dd hh:mm:ss
```

**Implementation Status:** **NOT YET IMPLEMENTED**
- Parse `workbook.style` and extract custom formats (ID >= 164)

---

### 9.3 Theme (`styles/theme.txt`)

**Purpose:** Document theme colors and fonts.

**Format:** Multi-section text file
```
# Theme
# =====

Name: Office Theme

Colors:
  theme:0 (Light 1): #FFFFFF
  theme:1 (Dark 1): #000000
  theme:2 (Light 2): #E7E6E6
  theme:3 (Dark 2): #44546A
  theme:4 (Accent 1): #4472C4
  ...

Fonts:
  Major (Headings): Calibri Light
  Minor (Body): Calibri
```

**Implementation Status:** **NOT YET IMPLEMENTED**
- Parse `xl/theme/theme1.xml` from ZIP
- Important for interpreting theme-based colors

---

## 10. Manifest (`manifest.json`)

### 10.1 Purpose

The manifest is the **single source of truth** about the extraction:
- What was extracted (file inventory)
- What warnings occurred
- What options were used
- Origin metadata (if provided)
- Verification hashes for all files

### 10.2 Schema

```json
{
  "workbook_filename": "budget.xlsb",
  "original_sha256": "a3f5c8d1e7b4f2a9c1d5e8b3f7a2c9d4e1f8b5a7c3d9e2f6b8a4c1d7e9f3b6a8",
  "extracted_at": "2025-10-27T14:30:22Z",
  "extractor_version": "2.0.0",
  "include_evaluated": false,

  "sheets": [
    {
      "index": 1,
      "name": "Dashboard",
      "sheetId": 1,
      "visible": true
    },
    {
      "index": 2,
      "name": "Data",
      "sheetId": 2,
      "visible": true
    }
  ],

  "files": [
    {
      "path": "workbook/metadata.txt",
      "sha256": "b3c7d2f9e4a1c8d5f2b9e7a4c1d8f5b2e9a6c3d1f8e5b7a2c9d6f3e1b4a7c8d2"
    },
    {
      "path": "sheets/01.Dashboard.formulas.txt",
      "sha256": "c4d8f3e2b9a7c1d6f4e9b2a8c5d1f7e3b6a9c2d8f5e1b4a7c9d3f6e2b8a5c1d7"
    }
  ],

  "warnings": [
    "VBA project is password protected, modules could not be extracted",
    "Chart 'Sales Trend' could not be parsed, saved as raw XML"
  ],

  "origin": {
    "origin_repo": "git@github.com:company/budget.git",
    "origin_path": "finance/budget.xlsb",
    "origin_commit": "abc123def456",
    "origin_commit_message": "Update Q4 budget projections"
  }
}
```

### 10.3 Required Fields

- `workbook_filename`: Original filename (string)
- `original_sha256`: SHA256 hash of original binary file (hex string)
- `extracted_at`: Extraction timestamp (ISO8601 UTC string)
- `extractor_version`: Flattener version (semver string)
- `include_evaluated`: Whether evaluated values were extracted (boolean)
- `sheets`: Array of sheet objects (see below)
- `files`: Array of file objects (see below)
- `warnings`: Array of warning strings (empty array if none)

### 10.4 Optional Fields

- `origin`: Object with origin metadata (optional)
  - `origin_repo`: Git repository URL
  - `origin_path`: File path in repository
  - `origin_commit`: Git commit SHA
  - `origin_commit_message`: Commit message

### 10.5 Sheet Object Schema

```json
{
  "index": 1,           // 1-based position
  "name": "Dashboard",  // Sheet name (exact)
  "sheetId": 1,        // Excel internal ID
  "visible": true      // Boolean
}
```

### 10.6 File Object Schema

```json
{
  "path": "sheets/01.Dashboard.formulas.txt",  // Relative to snapshot root
  "sha256": "abc123..."                        // SHA256 hex string
}
```

**File Hashing:**
- Hash computed AFTER file is written
- SHA256 algorithm
- Hex encoding (lowercase)
- Used for verification and change detection

---

## 11. Normalization Rules (Determinism)

**Critical:** These rules ensure identical input produces identical output.

### 11.1 Text Encoding
- **All text files:** UTF-8 encoding
- **BOM:** No BOM (byte order mark)
- **Line endings:** Unix (LF, `\n`) everywhere
- **File endings:** Single newline at end of file

### 11.2 Sorting
- **Cell addresses:** Row-major order (A1, A2, A3, ..., B1, B2, ...)
- **Sheet files:** Prefix with zero-padded index (01., 02., ...)
- **Named ranges:** Sort by scope, then name
- **Defined names:** Workbook scope first, then sheets alphabetically

### 11.3 Cell Address Normalization
- **Uppercase:** A1 not a1
- **Dollar signs:** Preserve in formulas (for absolute references)
- **Sorting:** Remove dollar signs before sorting

### 11.4 Formula Normalization
- **Function names:** Uppercase (SUM not sum)
- **Whitespace:** Trim leading/trailing
- **Operators:** Preserve as-is (no reformatting)
- **References:** Uppercase cell addresses
- **Logic:** NEVER change formula logic

### 11.5 Number Normalization
- **Integers:** No decimal point (100 not 100.0)
- **Decimals:** Plain notation (3.14159 not 3.14E+00)
- **Precision:** Max 15 significant digits
- **Rounding:** Use Excel's rounding rules
- **Special values:** Preserve INF, -INF, NaN if present

### 11.6 Date Normalization
- **Format:** ISO8601 with timezone
- **Timezone:** UTC (append Z)
- **Example:** 2025-10-27T14:30:00Z
- **Precision:** Seconds (no milliseconds)

### 11.7 Boolean Normalization
- **Values:** TRUE or FALSE (uppercase)
- **Never:** Yes/No, 1/0, yes/no

### 11.8 String Normalization
- **Line endings:** Convert CRLF, CR to LF
- **Trailing spaces:** Preserve (might be significant)
- **Unicode:** Preserve exact Unicode characters

### 11.9 Color Normalization
- **RGB:** Hex format #RRGGBB (uppercase)
- **Alpha:** Strip alpha channel (AARRGGBB → RRGGBB)
- **Theme colors:** Format theme:N (e.g., theme:4)
- **Indexed colors:** Format indexed:N

### 11.10 Sheet Name Sanitization
For filenames only (NOT in data):
- Replace invalid filename characters with underscore
- Invalid chars: / \ : * ? " < > |
- Collapse multiple underscores/spaces to single underscore
- Trim underscores from start/end

---

## 12. Error Handling & Edge Cases

### 12.1 Input Validation Errors
- **File doesn't exist:** Raise FileNotFoundError
- **File not readable:** Raise PermissionError
- **File too large:** Raise ValueError with size limit
- **Invalid format:** Raise ValueError with format error

### 12.2 Conversion Errors (XLSB/XLS)
- **LibreOffice not found:** Raise RuntimeError with install instructions
- **Conversion timeout:** Raise TimeoutError
- **Conversion failed:** Raise RuntimeError with LibreOffice error

### 12.3 Extraction Warnings
- **Password-protected VBA:** Add warning, continue
- **Unparseable charts:** Save raw XML, add warning
- **Missing properties:** Use empty string, no warning
- **Invalid cell values:** Convert to string, add warning

### 12.4 Workbook Errors
- **Password-protected workbook:** Cannot open, raise error
- **Corrupted file:** openpyxl error, raise with message
- **Unsupported features:** Extract what's possible, add warnings

### 12.5 Timeouts
- **Maximum extraction time:** Configurable (default: 15 minutes)
- **Action on timeout:** Raise TimeoutError, clean up temp files
- **User guidance:** Suggest splitting large workbooks

---

## 13. Configuration & Environment

### 13.1 Configuration Parameters

**File Handling:**
- `MAX_FILE_SIZE_BYTES`: Maximum input file size (default: 200MB)
- `TEMP_DIR`: Temporary directory for extraction (default: system temp)
- `OUTPUT_DIR`: Output directory for snapshots (required)

**Format Options:**
- `INCLUDE_EVALUATED`: Extract evaluated values (default: False)
- `INCLUDE_ORIGINAL`: Include original file in snapshot (default: True)
- `NUMBER_PRECISION`: Max significant digits for numbers (default: 15)

**Conversion:**
- `CONVERTER_PATH`: Path to LibreOffice binary (required for XLSB/XLS)
- `CONVERTER_TIMEOUT`: Conversion timeout in seconds (default: 300)

**Extraction:**
- `EXTRACTION_TIMEOUT`: Maximum extraction time (default: 900 seconds)
- `ENABLE_VBA_EXTRACTION`: Extract VBA modules (default: True)
- `ENABLE_CHARTS_EXTRACTION`: Extract charts (default: True)
- `ENABLE_TABLES_EXTRACTION`: Extract tables (default: True)

**Logging:**
- `LOG_LEVEL`: Logging level (default: INFO)
- `LOG_FILE`: Log file path (optional)

### 13.2 Environment Variables

All configuration can be set via environment variables:
- Prefix: `FLATTENER_`
- Example: `FLATTENER_MAX_FILE_SIZE_BYTES=104857600`
- Example: `FLATTENER_CONVERTER_PATH=/usr/bin/libreoffice`

### 13.3 Dependencies

**Required Python Libraries:**
- `openpyxl>=3.1.0`: Primary Excel library
- `lxml>=4.9.0`: XML parsing
- `oletools>=0.60`: VBA extraction

**Optional:**
- `pyxlsb>=1.0.10`: For direct XLSB reading (experimental)

**External Dependencies:**
- LibreOffice 7.x or newer (for XLSB/XLS conversion)
  - Linux: `apt install libreoffice`
  - macOS: `brew install libreoffice`
  - Windows: Download from libreoffice.org

---

## 14. Command-Line Interface

### 14.1 Basic Usage

```bash
# Flatten a workbook
excel-flattener flatten input.xlsx --output ./snapshots

# Flatten with evaluated values
excel-flattener flatten input.xlsx --output ./snapshots --include-evaluated

# Flatten XLSB (requires LibreOffice)
excel-flattener flatten input.xlsb --output ./snapshots --converter /usr/bin/libreoffice

# Show version
excel-flattener --version

# Show help
excel-flattener --help
```

### 14.2 Command: flatten

```
Usage: excel-flattener flatten [OPTIONS] INPUT_FILE

Arguments:
  INPUT_FILE                Excel file to flatten (.xlsx, .xlsm, .xlsb, .xls)

Options:
  -o, --output DIR          Output directory for snapshot [required]
  --include-evaluated       Include evaluated cell values
  --no-original            Don't include original file in snapshot
  --converter PATH         Path to LibreOffice binary
  --timeout SECONDS        Extraction timeout (default: 900)
  --config FILE            Load config from file
  -v, --verbose            Verbose output
  -q, --quiet              Quiet output
  --help                   Show this message and exit
```

### 14.3 Command: validate

```
Usage: excel-flattener validate [OPTIONS] SNAPSHOT_DIR

Validate a flattened snapshot against its manifest.

Arguments:
  SNAPSHOT_DIR              Path to snapshot directory

Options:
  --fix-hashes             Recompute and fix file hashes
  --strict                 Fail on any warnings
  --help                   Show this message and exit
```

### 14.4 Command: info

```
Usage: excel-flattener info [OPTIONS] INPUT_FILE

Show information about an Excel file without extracting.

Arguments:
  INPUT_FILE                Excel file to inspect

Options:
  --json                   Output as JSON
  --help                   Show this message and exit
```

---

## 15. Python API

### 15.1 Basic Usage

```python
from excel_flattener import Flattener
from pathlib import Path

# Create flattener
flattener = Flattener(
    include_evaluated=False,
    converter_path="/usr/bin/libreoffice"
)

# Flatten a workbook
result = flattener.flatten(
    input_file=Path("budget.xlsb"),
    output_dir=Path("./snapshots")
)

# Access results
print(f"Snapshot created at: {result['snapshot_dir']}")
print(f"Original file hash: {result['manifest'].original_sha256}")
print(f"Warnings: {result['warnings']}")
```

### 15.2 API Reference

**Class: Flattener**

```python
class Flattener:
    def __init__(
        self,
        include_evaluated: bool = False,
        converter_path: Optional[str] = None,
        extraction_timeout: int = 900,
        number_precision: int = 15,
        enable_vba: bool = True,
        enable_charts: bool = True,
        enable_tables: bool = True,
    ):
        """Initialize the flattener with options."""

    def flatten(
        self,
        input_file: Path,
        output_dir: Optional[Path] = None,
        origin_repo: Optional[str] = None,
        origin_path: Optional[str] = None,
        origin_commit: Optional[str] = None,
        origin_commit_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Flatten an Excel workbook.

        Returns:
            Dictionary with:
            - snapshot_dir: Path to snapshot directory
            - manifest: Manifest object
            - original_file: Path to original file
            - warnings: List of warnings
        """
```

**Class: Manifest**

```python
class Manifest:
    def __init__(
        self,
        workbook_filename: str,
        original_sha256: str,
        include_evaluated: bool = False,
    ):
        """Initialize manifest."""

    def add_sheet(self, index: int, name: str, sheetId: int, visible: bool):
        """Add sheet to manifest."""

    def add_file(self, file_path: Path, snapshot_root: Path):
        """Add file to manifest with hash."""

    def add_warning(self, message: str):
        """Add warning message."""

    def set_origin(
        self,
        origin_repo: Optional[str] = None,
        origin_path: Optional[str] = None,
        origin_commit: Optional[str] = None,
        origin_commit_message: Optional[str] = None,
    ):
        """Set origin metadata."""

    def save(self, path: Path):
        """Save manifest to JSON file."""

    @classmethod
    def load(cls, path: Path) -> 'Manifest':
        """Load manifest from JSON file."""
```

---

## 16. Testing Requirements

### 16.1 Test Coverage

**Must test:**
- All file formats: .xlsx, .xlsm, .xlsb, .xls
- All sheet-level features: formulas, values, formats, merges, comments
- All workbook-level features: metadata, structure, defined names
- VBA extraction: with and without password protection
- Edge cases: empty workbooks, single-sheet, many sheets (100+)
- Error handling: missing files, corrupt files, timeouts
- Normalization: deterministic output (same input → same output)
- Large files: performance testing up to max file size

### 16.2 Test Data

**Required test files:**
- `empty.xlsx`: Empty workbook
- `simple.xlsx`: Single sheet, basic formulas and values
- `complex.xlsm`: Multiple sheets, VBA, tables, charts
- `large.xlsb`: Large file (>100MB)
- `password-protected.xlsx`: Password-protected workbook
- `vba-protected.xlsm`: Workbook with password-protected VBA
- `corrupt.xlsx`: Intentionally corrupted file

### 16.3 Regression Tests

**Test determinism:**
```python
# Extract same file twice, compare outputs
result1 = flattener.flatten(input_file, output_dir1)
result2 = flattener.flatten(input_file, output_dir2)

# All files should be identical (byte-for-byte)
assert_directories_equal(result1['snapshot_dir'], result2['snapshot_dir'])
```

**Test diff-friendliness:**
```python
# Make small change to workbook, extract both versions
result_v1 = flattener.flatten(workbook_v1, output_dir1)
result_v2 = flattener.flatten(workbook_v2, output_dir2)

# Diff should only show changed cells
diff = compute_directory_diff(result_v1['snapshot_dir'], result_v2['snapshot_dir'])
assert len(diff) == expected_changes
```

---

## 17. Performance Requirements

### 17.1 Benchmarks

**Target performance:**
- Small files (<1MB): <5 seconds
- Medium files (1-10MB): <30 seconds
- Large files (10-100MB): <5 minutes
- Maximum file (200MB): <15 minutes

**Bottlenecks:**
- LibreOffice conversion (XLSB): ~10-60 seconds
- VBA extraction: ~1-5 seconds
- Large sheets (>100K cells): Memory usage

### 17.2 Optimization Strategies

**Memory:**
- Stream large files when possible
- Use `openpyxl` in read-only mode
- Clean up temp files immediately after use
- Limit cached data in memory

**Speed:**
- Skip empty rows/columns
- Only extract cells with content or formatting
- Parallel extraction of sheets (optional)
- Cache LibreOffice conversions (optional)

---

## 18. Versioning & Compatibility

### 18.1 Flattener Version

- **Current version:** 2.0.0
- **Versioning scheme:** Semantic versioning (MAJOR.MINOR.PATCH)
- **Version in manifest:** Always record extractor version
- **Backward compatibility:** Flattener 2.x can read any 2.x snapshot

### 18.2 Format Stability

**Stable (won't change):**
- Manifest JSON schema (only additions allowed)
- File naming conventions
- Core normalization rules (formulas, numbers, dates)

**Unstable (may change):**
- Exact file format details (e.g., adding new columns)
- Chart/pivot/table formats (not yet implemented)
- Warning messages

**Deprecation policy:**
- Breaking changes: Major version bump
- New features: Minor version bump
- Bug fixes: Patch version bump

---

## 19. Future Enhancements (Out of Scope for v2.0)

### 19.1 Advanced Features
- Recompute formula values (requires full calculation engine)
- Support for Excel 365 features (dynamic arrays, LAMBDA, etc.)
- Extract embedded objects (images, OLE objects)
- Extract sparklines
- Extract conditional formatting rules (detailed)

### 19.2 Performance
- Parallel sheet extraction
- Incremental extraction (only changed sheets)
- Caching of converted files

### 19.3 Formats
- Support for Google Sheets export
- Support for Numbers (Apple)
- Support for LibreOffice Calc

---

## 20. Success Criteria

**The flattener is successful if:**

1. **Deterministic:** Same input → same output, always
2. **Complete:** Extracts all relevant workbook content
3. **Diff-friendly:** Small changes in Excel → small diffs in output
4. **Fast:** Handles typical workbooks in seconds
5. **Robust:** Handles errors gracefully, never loses data
6. **Documented:** Every file format is clearly specified
7. **Testable:** Comprehensive test suite exists
8. **Maintainable:** Code is clean, modular, well-documented

---

## Appendix A: File Format Summary

| File | Purpose | Format | Mandatory | Sorting |
|------|---------|--------|-----------|---------|
| manifest.json | Inventory & metadata | JSON | YES | N/A |
| original/<file> | Original binary | Binary | YES | N/A |
| workbook/metadata.txt | Workbook properties | Key-value | YES | By key |
| workbook/structure.txt | Sheet list | Tab-delimited | YES | By index |
| workbook/defined_names.txt | Named ranges | Tab-delimited | YES | By scope, name |
| workbook/calculation_chain.txt | Calc order | List | NO | Calc order |
| workbook/external_links.txt | External refs | Tab-delimited | NO | By ID |
| workbook/connections.txt | Data connections | Tab-delimited | NO | By name |
| workbook/addins.txt | Add-in refs | List | NO | Alphabetical |
| sheets/<NN>.<Name>.metadata.json | Sheet properties | JSON | YES | N/A |
| sheets/<NN>.<Name>.formulas.txt | Formula cells | Tab-delimited | YES | Row-major |
| sheets/<NN>.<Name>.values_hardcoded.txt | Non-formula values | Tab-delimited | YES | Row-major |
| sheets/<NN>.<Name>.values_evaluated.txt | All values | Tab-delimited | NO | Row-major |
| sheets/<NN>.<Name>.cell_formats.txt | Cell formatting | Tab-delimited | YES | Row-major |
| sheets/<NN>.<Name>.merged_ranges.txt | Merged cells | List | YES | Lexicographic |
| sheets/<NN>.<Name>.data_validations.txt | Validation rules | Tab-delimited | YES | By range |
| sheets/<NN>.<Name>.comments.txt | Cell comments | Tab-delimited | YES | Row-major |
| tables/<Name>.definition.txt | Table structure | Text | NO | N/A |
| charts/<Name>.metadata.txt | Chart definition | Text | NO | N/A |
| charts/<Name>.xml | Raw chart XML | XML | NO | N/A |
| pivots/<Name>.definition.txt | Pivot structure | Text | NO | N/A |
| vba/vbaProject.bin | VBA binary | Binary | IF VBA | N/A |
| vba/<Name>.bas/cls/frm | VBA modules | VBA code | IF VBA | Alphabetical |
| styles/cell_styles.txt | Named styles | Text | NO | By name |
| styles/number_formats.txt | Custom formats | Tab-delimited | NO | By ID |
| styles/theme.txt | Theme definition | Text | NO | N/A |
| logs/extraction.log | Extraction log | Text | YES | N/A |

---

## Appendix B: Example Complete Snapshot

```
budget-snapshot-20251027T143022Z-a3f5c8d1/
├── manifest.json
├── original/
│   └── budget.xlsb
├── workbook/
│   ├── metadata.txt
│   ├── structure.txt
│   ├── defined_names.txt
│   ├── calculation_chain.txt
│   ├── external_links.txt
│   ├── connections.txt
│   └── addins.txt
├── sheets/
│   ├── 01.Dashboard.metadata.json
│   ├── 01.Dashboard.formulas.txt
│   ├── 01.Dashboard.values_hardcoded.txt
│   ├── 01.Dashboard.cell_formats.txt
│   ├── 01.Dashboard.merged_ranges.txt
│   ├── 01.Dashboard.data_validations.txt
│   ├── 01.Dashboard.comments.txt
│   ├── 02.Data.metadata.json
│   ├── 02.Data.formulas.txt
│   ├── 02.Data.values_hardcoded.txt
│   ├── 02.Data.cell_formats.txt
│   ├── 02.Data.merged_ranges.txt
│   ├── 02.Data.data_validations.txt
│   └── 02.Data.comments.txt
├── tables/
│   ├── SalesTable.definition.txt
│   └── SalesTable.data.csv
├── charts/
│   ├── RevenueTrend.metadata.txt
│   └── RevenueTrend.xml
├── pivots/
│   └── SalesAnalysis.definition.txt
├── vba/
│   ├── vbaProject.bin
│   ├── Module1.bas
│   └── ThisWorkbook.cls
├── styles/
│   ├── cell_styles.txt
│   ├── number_formats.txt
│   └── theme.txt
└── logs/
    └── extraction.log
```

---

## Document History

- **2025-10-29:** Version 2.0 - Complete rewrite for standalone flattener
- **2025-10-27:** Version 1.0 - Initial specification (integrated with API)

---

**END OF FLATTENER SPECIFICATIONS**
