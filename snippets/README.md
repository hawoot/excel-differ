# Learning Notebooks

Three hands-on notebooks to learn the Excel Diff Server step-by-step.

## 📓 Notebooks

### 1️⃣ Check Setup (`01_check_setup.ipynb`)
**Run this first!**

Verifies your environment is set up correctly:
- ✅ Python version
- ✅ Required packages installed
- ✅ Project structure
- ✅ Configuration
- ✅ LibreOffice (optional)
- ✅ Redis (optional)

**No coding required** - just run each cell and see green checkmarks!

### 2️⃣ Test Features (`02_test_features.ipynb`)
**The main learning notebook!**

Hands-on tutorial covering:
1. Create a test Excel file
2. Test formula normalization
3. Test number normalization
4. **Flatten an Excel file** (the core operation!)
5. Explore the output files
6. Look at extracted formulas
7. Look at extracted values
8. Modify the Excel file
9. Flatten version 2
10. **Compare the two versions**
11. Get structured diff output

**This is where you understand how it all works!**

### 3️⃣ Test API (`03_test_api.ipynb`)
**Test the REST API**

**Requires**: Server must be running (`python -m src.api.main`)

Tests all API endpoints:
- Health check
- POST /api/v1/flatten
- GET /api/v1/jobs/{job_id}
- POST /api/v1/compare
- Error handling
- Interactive docs

## 🚀 How to Use

### Option 1: Jupyter Notebook (Recommended)

```bash
# Install Jupyter
pip install jupyter

# Start Jupyter
jupyter notebook

# Open the notebooks in order:
# 1. 01_check_setup.ipynb
# 2. 02_test_features.ipynb
# 3. 03_test_api.ipynb
```

### Option 2: VS Code

If you have VS Code with Python extension:
1. Open a `.ipynb` file
2. Click "Run All" or run cells one-by-one
3. Output appears inline

### Option 3: JupyterLab

```bash
pip install jupyterlab
jupyter lab
```

## 📋 Prerequisites

Before running the notebooks:

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Install packages (if not already done)
pip install -r requirements.txt

# 3. Install Jupyter
pip install jupyter

# 4. For notebook 3, start the API server in another terminal
python -m src.api.main
```

## 🎯 Learning Path

**Complete beginner?** Follow this order:

1. Read [QUICKSTART.md](../QUICKSTART.md) (5 min)
2. Run `01_check_setup.ipynb` (check everything works)
3. Run `02_test_features.ipynb` (understand the core concepts)
4. Start API server: `python -m src.api.main`
5. Run `03_test_api.ipynb` (see the REST API in action)
6. Read [docs/CODE_WALKTHROUGH.md](../docs/CODE_WALKTHROUGH.md) (deep dive)

**Want to understand the code?** After the notebooks:
- Read [docs/KEY_FILES_EXPLAINED.md](../docs/KEY_FILES_EXPLAINED.md)
- Browse `src/engine/flattener/` files
- Read function docstrings

## 💡 Tips

**Notebooks keep failing?**
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt`
- Run `01_check_setup.ipynb` to diagnose issues

**Want to modify and experiment?**
- Copy a notebook: `cp 02_test_features.ipynb my_experiments.ipynb`
- Change values, add cells, break things!
- Learning by doing is the best way

**Cells run out of order?**
- Restart kernel: Kernel → Restart & Clear Output
- Run all cells in order: Cell → Run All

## 🔍 What Each Notebook Teaches

| Notebook | You Learn | Key Concepts |
|----------|-----------|--------------|
| **01_check_setup** | Environment is ready | Dependencies, configuration |
| **02_test_features** | How flattening works | Normalization, extraction, comparison |
| **03_test_api** | How to use the API | REST endpoints, async jobs |

## 🎓 After the Notebooks

Once you've completed all three notebooks, you'll understand:
- ✅ How Excel files are converted to text
- ✅ How normalization makes output deterministic
- ✅ What files are created in snapshots
- ✅ How to compare two Excel versions
- ✅ How to use the REST API
- ✅ Where to look in the code for specific features

**Ready to code?** You can now:
- Customize normalization logic
- Add new extraction features
- Integrate with your CI/CD pipeline
- Build UIs on top of the API

## 🐛 Troubleshooting

**Import errors**:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Can't find modules**:
The notebooks automatically add project root to Python path. If this fails, check you're in the `snippets/` folder.

**API connection refused**:
Server not running! Start it:
```bash
python -m src.api.main
```

**Kernel died**:
- Restart kernel
- Check if you have enough RAM (flattening large files needs memory)
- Try smaller test files

## 📚 Next Steps

After completing the notebooks:
1. Read [CODE_WALKTHROUGH.md](../docs/CODE_WALKTHROUGH.md)
2. Try modifying the code
3. Test with real Excel files from your work
4. Integrate with your workflow

**Questions?** Check the docs folder or read the code - it's well commented!
