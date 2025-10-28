# Quick Start - Get Running in 2 Minutes

**Too confusing? Start here!** This is the simplest path to get the server running.

## The Absolute Simplest Way

```bash
# 1. Run the setup script (handles everything)
./scripts/setup_local.sh

# 2. Start the server
source venv/bin/activate
python -m src.api.main

# 3. Test it
curl http://localhost:8000/health
```

**That's it!** Open http://localhost:8000/docs to see the API.

---

## What Just Happened?

The setup script:
1. ✅ Checked you have Python 3.8+
2. ✅ Created a virtual environment (`venv/`)
3. ✅ Installed all Python packages
4. ✅ Created a `.env` config file
5. ✅ Set it to use simple mode (no Redis needed)

Now the server is running and ready to use!

---

## Test It Works

### Option 1: Check Health

```bash
curl http://localhost:8000/health
```

You should see: `{"status": "ok", ...}`

### Option 2: Try the Interactive Docs

Open in your browser: **http://localhost:8000/docs**

This shows all available endpoints and lets you test them!

### Option 3: Flatten a Test File

First, create a simple Excel file:

```python
# Run this to create test.xlsx
python3 << 'EOF'
from openpyxl import Workbook
wb = Workbook()
ws = wb.active
ws['A1'] = 'Hello'
ws['A2'] = 42
ws['A3'] = '=SUM(A2:A2)'
wb.save('test.xlsx')
print("✓ Created test.xlsx")
EOF
```

Then flatten it using the API:

```bash
curl -X POST -F "file=@test.xlsx" http://localhost:8000/api/v1/flatten
```

You'll get back a `job_id`. Check its status:

```bash
curl http://localhost:8000/api/v1/jobs/YOUR_JOB_ID_HERE
```

---

## Common Issues

### "Command not found" errors

Make sure you activated the virtual environment:

```bash
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### "Port 8000 already in use"

Change the port in `.env`:

```bash
echo "PORT=8080" >> .env
```

Then use `http://localhost:8080` instead.

### Script errors on setup

Run it step-by-step instead:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install packages
pip install -r requirements.txt

# Create config
cp .env.example .env

# Start server
python -m src.api.main
```

---

## What's in the `.env` File?

Open `.env` to see the configuration. The defaults work fine for testing!

**Only change these if you want git integration:**

```bash
SNAPSHOT_REPO_URL=git@github.com:yourorg/excel-snapshots.git
GIT_USER_NAME=Your Name
GIT_USER_EMAIL=your@email.com
```

Otherwise, leave it as-is!

---

## Next Steps

Now that it's running, choose your path:

### Path 1: Just Want to Use It?
- Read [API Examples](docs/API_USAGE.md) ← Not written yet, but check `/docs` in browser
- Try the interactive API docs at http://localhost:8000/docs

### Path 2: Want to Understand the Code?
- Read [CODE_WALKTHROUGH.md](docs/CODE_WALKTHROUGH.md) ← **Start here!**
- Run `python snippets/test_functions.py` to see components in action
- Open `snippets/test_functions.ipynb` in Jupyter for interactive examples

### Path 3: Want Complete Details?
- Read [GETTING_STARTED.md](GETTING_STARTED.md) - Comprehensive guide
- Read [README.md](README.md) - Full overview

---

## The 30-Second Explanation

**What does this do?**

Turns Excel files (binary, hard to diff) into text files (easy to diff).

**Why?**

So you can track Excel changes in git, just like code!

**How?**

1. You upload an Excel file via the API
2. Server extracts formulas, values, VBA, etc. → text files
3. You get back a snapshot you can commit to git

**Example:**

Before (Excel file):
- Binary file, can't see what changed

After (Flattened snapshot):
- `01.Sheet1.formulas.txt` - All formulas in plain text
- `01.Sheet1.values.txt` - All values
- `manifest.json` - Complete metadata
- `Module1.bas` - VBA code

Now you can `git diff` these files meaningfully!

---

## Still Confused?

**Try this**:

1. Start the server (steps at top)
2. Open http://localhost:8000/docs
3. Click on `/api/v1/flatten`
4. Click "Try it out"
5. Upload an Excel file
6. See what comes back!

The interactive docs make it much easier to understand.

**Or ask**: What specifically is confusing? I can explain that part!

---

## Shutting Down

Just press `Ctrl+C` in the terminal where the server is running.

To start again later:

```bash
source venv/bin/activate
python -m src.api.main
```
