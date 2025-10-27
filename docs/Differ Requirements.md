# Excel Diff Server — **Complete** Requirements & Architecture (v3 — exhaustive)

---

## 1 — What this system *is*

A server + extraction engine that flattens Excel workbooks into deterministic, human- and git-diffable text snapshots (formulas, hard-coded values, named ranges, tables, charts, pivots, connections, cell formats/styles, VBA modules, calc chain, etc.), and supports three async use-cases:

1. **Extract (hook)** — a hook/CI or client posts a file (or provides hook metadata / fetch URL). Server flattens and **commits snapshot + original** into a configured **Snapshot Repo (Repo B)**; returns a `job_id` for async status. No diffs performed by the server here.

2. **Flatten (ad-hoc)** — client uploads one file and gets back a flattened archive and manifest (async `job_id` → download link). `values_evaluated` optional.

3. **Compare (on-demand)** — client uploads two files (or two existing snapshot paths) and gets **structured JSON diff** + unified diff text (async `job_id` → result). Server compares flattened folders directly (no git required for diffing).

All results are stored temporarily for retrieval (default TTL = **10 hours**) and then cleaned up.

---

## 2 — Terminology (use these names)

* **Origin Repo (Repo A)** — where Excel files are authored/committed by users. (Optional in payload; server can receive actual file instead.)
* **Snapshot Repo (Repo B)** — where the server commits flattened snapshots + original Excel copy when `/extract` is used. Configurable; may be same as Origin Repo if you want, but usually different.
* **Flattened Snapshot** — the deterministic folder tree extracted from a workbook (text files only + manifest + original copy).
* **Job** — async task (queued → running → success|failed). Every POST returns a `job_id`.
* **CONVERTER** — path to the LibreOffice binary for `.xlsb → .xlsm` conversion (e.g. `/usr/bin/libreoffice`).
* **values_hardcoded** — values present in cells that do **not** have formulas (mandatory).
* **values_evaluated** — displayed/evaluated values (hardcoded + formula results), optional (off by default).

---

## 3 — Main API Endpoints (async only)

**Base root:** `/api/v1`

> All POSTs return `202 Accepted` with JSON `{ "status":"accepted", "job_id":"<uuid>" }` (immediate). Client polls `GET /api/v1/jobs/{job_id}` for status/result. (Callback/webhook push is an optional enhancement; explained later.)

### 3.1 `POST /api/v1/extract` — Hook-driven snapshot & commit

**Purpose:** Called by a Git hook/CI or by manual upload to commit a snapshot into Snapshot Repo (Repo B).

**Inputs (multipart/form-data or JSON hook payload):**

* `file` — binary Excel file (optional if `hook_payload.url` provided)
* `hook_payload` — optional JSON with:

  * `origin_repo` (string, e.g. `git@github.com:org/repo.git`)
  * `origin_path` (string relative path in origin repo)
  * `origin_commit` (SHA)
  * `origin_commit_message` (string) — server will use this commit message for Snapshot Repo commit if provided
  * `file_url` (URL) — the server can fetch the file (optional)
* `snapshot_repo_url` — override server default Snapshot Repo for this job (optional)
* `include_evaluated` — boolean (optional; default `false`)

**Behavior:**

* Validate size ≤ `MAX_UPLOAD_BYTES` (default 200MB). If `file` missing and `file_url` present, server fetches file.
* If input file is `.xlsb`, convert to `.xlsm` using `CONVERTER_PATH` (LibreOffice headless) before extraction.
* Run Flattener Engine → produce deterministic Flattened Snapshot and `manifest.json`.
* Commit to Snapshot Repo (Repo B) at path:
  `<origin_repo_identifier_or_default>/<origin_path_or_filename>/snapshots/<ISO8601>-<sha256>`
  Include:

  * full flattened tree under that path,
  * copy of original workbook under `originals/`
  * commit message: **use `origin_commit_message` if provided**; otherwise use template:
    `[excel-snapshot] Snapshot for <filename> @ <ISO8601>`
* Return `job_id`. Job result includes `commit_sha`, `snapshot_path`, `manifest`.

**Example curl (hook sends file):**

```bash
curl -X POST -F "file=@revenue.xlsb" \
  -F "origin_repo=git@github.com:org/repoA.git" \
  -F "origin_path=reports/revenue.xlsb" \
  -F "origin_commit=abc123" \
  -F "origin_commit_message=Add Q3 revenue" \
  https://diff-server.internal/api/v1/extract
```

### 3.2 `POST /api/v1/flatten` — Flatten a single workbook (archive + manifest)

**Purpose:** Produce flattened snapshot for one workbook and return an archive + manifest.

**Inputs:**

* `file` (required) — binary Excel
* `format` — `zip` (default) or `tar.gz`
* `include_evaluated` (optional boolean; default `false`)

**Behavior:**

* Convert `.xlsb` if needed, run Flattener Engine -> snapshot folder.
* Create archive (`zip`), store temporarily in result storage.
* Return `job_id`. Job result includes download URL, archive size and `manifest.json`.

**Example curl:**

```bash
curl -X POST -F "file=@report.xlsm" https://diff-server.internal/api/v1/flatten
```

### 3.3 `POST /api/v1/compare` — Compare two workbooks (on-demand)

**Purpose:** Diff two workbooks and return structured JSON + unified diff text.

**Inputs (either):**

* `file_a` + `file_b` (upload both), OR
* `snapshot_path_a` + `snapshot_path_b` (refer to existing flattened snapshots in Snapshot Repo) — server will fetch or read
* `output` — `both` (default) / `json` / `text`
* `include_evaluated` — boolean (default false)
* `diff_context` — integer lines for unified diff context (default 3)

**Behavior:**

* Ensure both inputs available (upload or read snapshot paths).
* Flatten both (if files provided).
* Run folder→folder Diff Engine (file-by-file compare), produce:

  * `diff_json` — typed list of changes (details below).
  * `diff_unified` — unified patch text (if requested).
* Store results temporarily (TTL), return `job_id`. Job result contains `diff_json`, `diff_unified` (or download link if large).

**Example curl:**

```bash
curl -X POST -F "file_a=@old.xlsb" -F "file_b=@new.xlsb" https://diff-server.internal/api/v1/compare
```

### 3.4 `GET /api/v1/jobs/{job_id}` — Poll for job status & results

**Returns:**

* `job_id`, `status` (`queued|running|success|failed`), `type` (`extract|flatten|compare`), timestamps, progress, and `result` payload when `success`.
* `result` differs by type:

  * **extract:** `{ commit_sha, snapshot_path, manifest }`
  * **flatten:** `{ archive_url, manifest, size_bytes }`
  * **compare:** `{ diff_json, diff_unified, summary }`

Example response (compare):

```json
{
  "job_id":"uuid-123",
  "status":"success",
  "type":"compare",
  "started_at":"2025-10-27T10:00:00Z",
  "completed_at":"2025-10-27T10:04:12Z",
  "result":{
    "diff_json":[ ... ],
    "diff_unified":"@@ -1,3 +1,3 @@ ..."
  }
}
```

### 3.5 `GET /api/v1/snapshots/download?path=<snapshot_path>` — Download committed snapshot

**Purpose:** Download the flattened snapshot and original workbook committed to Snapshot Repo. (Admin or automation use.)

**Inputs:**

* `path` — path returned in `extract` job result.

**Behavior:**

* Server reads Snapshot Repo (local clone path `SNAPSHOT_REPO_LOCAL_PATH`) and streams a zip of the snapshot folder.

---

## 4 — Job lifecycle & worker model

* **Client POST → server returns `job_id` immediately.**
* **Worker queue** (e.g., Celery, RQ, or simple process pool) picks job, runs extraction/diff.
* **Job time limit:** `EXTRACTION_TIMEOUT_SECONDS = 900` (15 minutes). Workers should enforce this.
* **Result TTL:** `RESULT_TTL_SECONDS = 36000` (10 hours) — job output stored for retrieval; server cleans older entries via scheduled job.
* **Concurrency:** configurable (e.g., `WORKER_CONCURRENCY=4`).
* **Temp storage path:** `TEMP_STORAGE_PATH` (cleaned on success/failure per TTL).

---

## 5 — Configuration (env/config keys)

* `SNAPSHOT_REPO_URL` — default Snapshot Repo (Repo B) URL (string)
* `SNAPSHOT_REPO_LOCAL_PATH` — local checked-out mirror path for Repo B (string)
* `CONVERTER_PATH` — path to LibreOffice binary (e.g., `/usr/bin/libreoffice`)
* `MAX_UPLOAD_BYTES` — default `200 * 1024 * 1024` (200 MB)
* `EXTRACTION_TIMEOUT_SECONDS` — default `900` (15 minutes)
* `RESULT_TTL_SECONDS` — default `36000` (10 hours)
* `WORKER_CONCURRENCY` — default `4`
* `TEMP_STORAGE_PATH` — path for job temp artifacts
* `INCLUDE_EVALUATED_DEFAULT` — default `false`
* `LOG_LEVEL` — e.g., `INFO`
* `CALLBACKS_ENABLED` — default `false` (enhance later)

> Note: Snapshot Repo and Origin Repo are configurable; the server does not assume the same repo for both.

---

## 6 — Flattened snapshot — exact folder schema (authoritative)

Snapshot root name:
`<workbook_filename>-snapshot-<ISO8601>-<sha256_of_original>`

All files utf-8, LF; numeric/date formatting normalized (rules below).

```
<snapshot_root>/
  manifest.json                # canonical manifest (see schema)
  original/
    workbook.xlsb              # original uploaded/converted binary
  workbook/
    structure.txt              # sheet order, sheetId, visibility, tab_color
    defined_names.txt          # NAME<TAB>SCOPE<TAB>REFERS_TO
    calculation_chain.txt      # list of sheet!cell in calc order (if present)
    external_links.txt         # list of external links & resovled targets
    connections.txt            # connection name + connection string / query
    addins.txt                 # list add-ins used (xlam/xla or COM GUID)
    metadata.txt               # author, created, modified, excel_version, locale
  sheets/
    01.SheetName.metadata.json # {sheetId, visible:boolean, tab_color, protection}
    01.SheetName.formulas.txt  # lines: ADDRESS<TAB>NORMALIZED_FORMULA (ALL FORMULA CELLS)
    01.SheetName.values_hardcoded.txt # lines: ADDRESS<TAB>RAW_LITERAL_VALUE (ONLY non-formula)
    01.SheetName.values_evaluated.txt # (optional) lines: ADDRESS<TAB>DISPLAYED_VALUE (ALL CELLS)
    01.SheetName.cell_formats.txt # lines: ADDRESS<TAB>number_format<TAB>font:..|fill:..|align:..
    01.SheetName.merged_ranges.txt # list of merged ranges
    01.SheetName.data_validations.txt # cell/range validation rules
    01.SheetName.comments.txt   # cell -> comment text & author (if any)
  tables/
    Table_<name>.definition.txt # table name, range, columns, column types, table style
    Table_<name>.rows.csv       # optional CSV of table rows (raw text)
  charts/
    Chart_<name>.metadata.txt  # chart type, source ranges, axes, series
    Chart_<name>.xml           # raw chart xml if parsing not practical
  pivots/
    Pivot_<name>.definition.txt
  vba/
    ThisWorkbook.bas
    Module_<name>.bas
    Class_<name>.cls
    UserForm_<name>.frm
    vbaProject.bin             # raw binary (always keep)
  styles/
    cell_styles.txt            # style name -> style definition
    number_formats.txt
    theme.txt
  logs/
    extraction.log             # extractor warnings/errors for this workbook
```

**Key naming rules**

* Prefix sheet files with zero-padded index `01.`, `02.` to preserve tab order.
* `values_hardcoded` is always present (mandatory).
* `values_evaluated` only created if `include_evaluated=true` (off by default).
* Keep raw `vbaProject.bin` always. If module extraction fails (password protected) include marker file `Module_X.EXTRACTION_PROTECTED` and put warning in `manifest.json`.

---

## 7 — Manifest (`manifest.json`) — required fields

Example manifest JSON:

```json
{
  "workbook_filename":"revenue.xlsb",
  "original_sha256":"abcd1234...",
  "extracted_at":"2025-10-27T12:34:56Z",
  "extractor_version":"0.1.0",
  "include_evaluated": false,
  "sheets":[
    {"index":1,"name":"Sheet1","sheetId":1,"visible":true},
    {"index":2,"name":"Sheet2","sheetId":2,"visible":false}
  ],
  "files":[
    {"path":"sheets/01.Sheet1.formulas.txt","sha256":"..."},
    {"path":"sheets/01.Sheet1.values_hardcoded.txt","sha256":"..."}
  ],
  "warnings":[ "VBA module ModuleFoo protected" ],
  "origin": {
    "origin_repo":"git@github.com:org/repoA.git",
    "origin_path":"reports/revenue.xlsb",
    "origin_commit":"abc123",
    "origin_commit_message":"Add Q3 revenue"
  }
}
```

`manifest.json` is canonical and used by diff engine to detect presence/absence of files.

---

## 8 — Normalization & determinism rules (must follow)

To ensure diffs are meaningful and repeatable:

### Formulas

* Trim leading/trailing whitespace.
* Function names UPPERCASED (e.g., `SUM` not `sum`) — **only case normalization**, do not change semantics.
* Do not rewrite formula logic (no simplification).
* Use `,` as canonical argument separator in serialized forms (record original locale in `metadata.txt`).

### Values

* **Hardcoded values**: write raw value as in XML (strings, booleans, numbers). Numbers in plain decimal with up to 15 significant digits (avoid scientific unless needed).
* **Dates**: write ISO8601 plus original Excel serial and original number format id.
* **Strings**: preserve exact content; normalize line endings to `\n`.
* **Evaluated values**: if included, note whether it is `cached` from workbook or `recomputed`. Default: **cached only**.

### Cell addresses / ordering

* All sheet files sorted by sheet index; within each file list rows sorted by row-major order (A1, A2, B1, B2...).

### Styles / Formats

* Color values in hex `#RRGGBB` or theme token with mapping included in `theme.txt`.
* Number format strings as given; custom formats listed in `number_formats.txt`.

### VBA

* Dump module code **exactly** as extracted (preserve lines, do not reformat).
* If module protected, include `ModuleX.EXTRACTION_PROTECTED` marker and raw `vbaProject.bin`.

---

## 9 — Diff JSON schema (for `/compare` results)

`diff_json` is an array of typed objects. Each object is one of:

### Sheet-level

```json
{ "category":"sheet", "action":"added|removed|renamed", "old_name": "...", "new_name": "...", "details": {...} }
```

### Formula change

```json
{
  "category":"formula",
  "sheet":"Sheet1",
  "cell":"C5",
  "old":"=SUM(A1:A4)",
  "new":"=SUM(A1:A5)"
}
```

### Hard-coded value change

```json
{
  "category":"value_hardcoded",
  "sheet":"Sheet1",
  "cell":"A2",
  "old":"100",
  "new":"120"
}
```

### Evaluated value change (if requested)

```json
{
  "category":"value_evaluated",
  "sheet":"Sheet1",
  "cell":"B3",
  "old":"$10.00",
  "new":"$11.00",
  "note":"cached"
}
```

### VBA change

```json
{
  "category":"vba",
  "action":"modified|added|removed",
  "module":"Module1",
  "diff":"unified-diff-string"
}
```

### Table/Chart/Pivot/Connection/Format changes

```json
{
  "category":"table",
  "action":"modified",
  "table":"Sales",
  "details":"columns added: Region"
}
```

### Generic file-level change (if structure changed)

```json
{
  "category":"file",
  "path":"sheets/01.Sheet1.formulas.txt",
  "action":"modified",
  "diff":"unified-diff-string"
}
```

Also include `summary` object:

```json
{
  "summary":{
    "sheets_added": 1,
    "sheets_removed": 0,
    "formulas_changed": 3,
    "values_hardcoded_changed": 5,
    "vba_modules_changed":1
  }
}
```

**Unified diff**: also return a git-style unified text diff (if `output` includes `text`).

---

## 10 — Errors, statuses & HTTP semantics

* **All POSTs**: 202 Accepted + `{status:accepted, job_id}`.
* **Invalid payload / validation errors**: 400 Bad Request + JSON `{error: "..."}`
* **File too large**: 413 Payload Too Large
* **Server internal error**: 500 Internal Server Error + job marked `failed` with `error` message
* **GET /jobs/{job_id}**: 200 OK with job status JSON; 404 if `job_id` unknown.
* **GET /snapshots/download?path=...**: 200 stream (zip) on success; 404 if snapshot not found.

---

## 11 — Edge cases & handling rules (explicit)

* **Password-protected workbook or VBA project**

  * Extraction: note `warning` in `manifest.json`, include raw `vbaProject.bin`, include `ModuleX.EXTRACTION_PROTECTED` marker files. Job succeeds with `warnings` unless extraction completely fails.

* **Unsupported or unparseable charts/pivots**

  * Save raw chart/pivot xml under `charts/ChartX.xml` or `pivots/PivotX.xml` and add warning.

* **Locale function separators**

  * Record workbook locale in `metadata.txt`. Normalize serialized formulas to canonical `,` separator; record original separator in metadata if different.

* **Volatile functions (NOW(), RAND())**

  * Evaluated values are `cached` by default; manifest notes volatility; do not attempt recompute.

* **Add-ins / external functions**

  * Record add-in references under `addins.txt`. If formula uses add-in function, treat formula text as-is; warn if add-in missing.

* **Large workbooks / long tasks**

  * Timeout = 15 minutes by default. If extraction exceeds timeout, job marked `failed` with message. Consider increasing `EXTRACTION_TIMEOUT_SECONDS` per environment.

* **Network fetch failure for `file_url` in hook payload**

  * Mark job failed; include error message.

* **Concurrent commits to Snapshot Repo**

  * Use git operations with retry/backoff. If commit fails, job marked `failed` with reason.

---

## 12 — Operational & security notes

* **No auth by default** (you requested this). For production, add token/OAuth/mTLS soon.
* **Max upload** is configurable; default = 200MB.
* **Job result TTL** = 10 hours; server cleans older artifacts.
* **Audit logs**: log uploader IP, origin repo, origin commit, job_id, extractor_version.
* **Sandboxing**: run extraction inside worker with isolated temp dir and limited permissions.
* **Backups & storage**: Snapshot Repo size may grow; plan for retention/archival.

---

## 13 — Implementation guidance (tools & hints — non-prescriptive)

* **Flattening engine**: Python is recommended (openpyxl, lxml) + `oletools.olevba` for VBA extraction. For `.xlsb` conversion use LibreOffice headless (`CONVERTER_PATH`).
* **Async queue**: Celery/RQ/async workers; whatever your infra uses; keep job IDs opaque and idempotent.
* **Diff engine**: folder→folder file compare (hash files, diff changed files with unified diff; produce typed JSON).
* **Snapshot Repo operations**: keep a local checked-out clone at `SNAPSHOT_REPO_LOCAL_PATH`, perform `git add`/`commit`/`push` with proper error handling and retries.
* **Archive format**: ZIP for downloads; use streaming response to avoid memory pressure.

---

## 14 — Examples & flows

### Hook-triggered extract (recommended CI setup)

1. Developer pushes to Repo A.
2. CI job runs `git diff` to list changed Excel files and POSTs each to server:

```bash
curl -X POST -F "file=@reports/rev.xlsb" \
  -F "origin_repo=git@github.com:org/repoA.git" \
  -F "origin_path=reports/rev.xlsb" \
  -F "origin_commit=abc123" \
  -F "origin_commit_message='Add Q3 revenue'" \
  https://diff-server.internal/api/v1/extract
```

3. Server returns `job_id`. CI may poll `GET /jobs/{job_id}` or rely on callback later (enhancement).
4. Once job completes, server committed flattened files + original under Snapshot Repo path and returns `commit_sha` in job result.

### On-demand compare

```bash
curl -X POST -F "file_a=@old.xlsb" -F "file_b=@new.xlsb" \
  https://diff-server.internal/api/v1/compare
# returns job_id
# poll GET /api/v1/jobs/{job_id} for result
```

### Get flattened archive

```bash
curl -X POST -F "file=@file.xlsm" https://diff-server.internal/api/v1/flatten
# returns job_id, poll /jobs/{job_id} for archive_url
```

---

## 15 — Callback URL (enhancement, optional; short explanation)

**What it is:** a URL you expose where the server will POST job results when finished. Instead of polling, you get a push.

**How it works (in practice):**

* You pass `callback_url` in POST (e.g., `https://ci.mycompany/callbacks/excel-diff`) or configure it in caller.
* When job is done the server calls `POST callback_url` with JSON payload (`job_id`, `status`, `result`).
* Your service receives it and can display/store results.

**Who posts what and where:** server posts job results to your `callback_url`. You must provide an endpoint that accepts POST. This requires your environment to be reachable from server (or use webhook relay). Because you said you're not very familiar, we left this **optional** for later.

---

## 16 — Other defaults

* `MAX_UPLOAD_BYTES` = 200 MB
* `EXTRACTION_TIMEOUT_SECONDS` = 900 s (15 min)
* `RESULT_TTL_SECONDS` = 36,000 s (10 hours)
* `CONVERTER_PATH` exists and should point to LibreOffice
* `values_evaluated` off by default

