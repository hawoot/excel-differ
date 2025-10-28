#!/bin/bash
# Setup script for local development (without Docker)
# This script is safe to run multiple times

echo "========================================="
echo "Excel Diff Server - Local Setup"
echo "========================================="
echo ""

# Don't exit on error - we'll handle them ourselves
set +e

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ ERROR: requirements.txt not found"
    echo "Please run this script from the project root directory:"
    echo "  cd /path/to/excel-differ"
    echo "  ./scripts/setup_local.sh"
    exit 1
fi

echo "✓ Running from project root"
echo ""

# 1. Check Python
echo "Step 1: Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "  Found: Python $PYTHON_VERSION"

    # Check if version is 3.8+
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
        echo "  ✓ Python version OK"
    else
        echo "  ⚠️  Python 3.8+ recommended (you have $PYTHON_VERSION)"
        echo "  Some features may not work. Consider upgrading."
    fi
else
    echo "  ❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi
echo ""

# 2. Check Git
echo "Step 2: Checking Git..."
if command -v git &> /dev/null; then
    echo "  ✓ Git found: $(git --version)"
else
    echo "  ❌ Git not found. Install with:"
    echo "     Ubuntu: sudo apt-get install git"
    echo "     macOS:  brew install git"
    exit 1
fi
echo ""

# 3. Check LibreOffice (optional but recommended)
echo "Step 3: Checking LibreOffice..."
if command -v libreoffice &> /dev/null; then
    echo "  ✓ LibreOffice found"
elif command -v soffice &> /dev/null; then
    echo "  ✓ LibreOffice found (soffice)"
else
    echo "  ⚠️  LibreOffice not found"
    echo "  XLSB files won't work without LibreOffice"
    echo ""
    echo "  Install with:"
    echo "    Ubuntu: sudo apt-get install libreoffice"
    echo "    macOS:  brew install libreoffice"
    echo ""
    echo "  You can continue without it (XLSX/XLSM will still work)"
fi
echo ""

# 4. Check Redis (optional)
echo "Step 4: Checking Redis..."
REDIS_AVAILABLE=false
if command -v redis-server &> /dev/null; then
    echo "  ✓ Redis found"
    REDIS_AVAILABLE=true
else
    echo "  ⚠️  Redis not found"
    echo "  Will use QUEUE_BACKEND=multiprocessing (simpler mode)"
    echo ""
    echo "  To install Redis later:"
    echo "    Ubuntu: sudo apt-get install redis-server"
    echo "    macOS:  brew install redis"
fi
echo ""

# 5. Create virtual environment
echo "Step 5: Setting up virtual environment..."
if [ -d "venv" ]; then
    echo "  ✓ Virtual environment already exists"
else
    echo "  Creating virtual environment..."
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        echo "  ✓ Virtual environment created"
    else
        echo "  ❌ Failed to create virtual environment"
        exit 1
    fi
fi
echo ""

# 6. Activate and install dependencies
echo "Step 6: Installing Python dependencies..."
echo "  (This may take a minute...)"

# Activate venv
source venv/bin/activate

# Upgrade pip quietly
pip install --upgrade pip --quiet

# Install requirements
pip install -r requirements.txt --quiet

if [ $? -eq 0 ]; then
    echo "  ✓ Dependencies installed"
else
    echo "  ❌ Failed to install dependencies"
    echo "  Try manually: source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi
echo ""

# 7. Create .env file
echo "Step 7: Setting up configuration..."
if [ -f ".env" ]; then
    echo "  ✓ .env file already exists (not overwriting)"
else
    if [ -f ".env.example" ]; then
        cp .env.example .env

        # Update QUEUE_BACKEND if no Redis
        if [ "$REDIS_AVAILABLE" = false ]; then
            # Works on both Linux and macOS
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' 's/QUEUE_BACKEND=celery/QUEUE_BACKEND=multiprocessing/' .env
            else
                sed -i 's/QUEUE_BACKEND=celery/QUEUE_BACKEND=multiprocessing/' .env
            fi
        fi

        echo "  ✓ Created .env file from .env.example"
    else
        echo "  ⚠️  .env.example not found, creating minimal .env"
        cat > .env << 'EOF'
# Minimal configuration
SNAPSHOT_REPO_URL=
QUEUE_BACKEND=multiprocessing
CONVERTER_PATH=/usr/bin/libreoffice
LOG_LEVEL=INFO
EOF
        echo "  ✓ Created minimal .env file"
    fi
fi
echo ""

# 8. Create directories
echo "Step 8: Creating directories..."
mkdir -p /tmp/excel-differ /tmp/snapshot-repo 2>/dev/null
echo "  ✓ Created /tmp/excel-differ and /tmp/snapshot-repo"
echo ""

# Summary
echo "========================================="
echo "✅ Setup Complete!"
echo "========================================="
echo ""

# Show next steps based on what's available
echo "🚀 To start the server:"
echo ""
echo "  1. Activate virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Start the server:"
echo "     python -m src.api.main"
echo ""

if [ "$REDIS_AVAILABLE" = true ]; then
    echo "  3. Optional - Use Celery (better for production):"
    echo "     Terminal 1: redis-server"
    echo "     Terminal 2: celery -A src.workers.celery_app worker --loglevel=info"
    echo ""
    echo "     (Make sure QUEUE_BACKEND=celery in .env)"
    echo ""
fi

echo "  Test it:"
echo "     curl http://localhost:8000/health"
echo ""

echo "📝 Important: Edit .env file to configure:"
echo "   - SNAPSHOT_REPO_URL (git repo for snapshots)"
echo "   - GIT_USER_NAME and GIT_USER_EMAIL"
echo ""

echo "📚 Documentation:"
echo "   - Getting Started: GETTING_STARTED.md"
echo "   - Code Walkthrough: docs/CODE_WALKTHROUGH.md"
echo "   - API Docs: http://localhost:8000/docs (after starting)"
echo ""

echo "🧪 Try examples:"
echo "   python snippets/test_functions.py"
echo ""

# Show warnings if any
if [ "$REDIS_AVAILABLE" = false ]; then
    echo "⚠️  Note: Using multiprocessing backend (no Redis)"
    echo "   This is fine for testing and development!"
    echo ""
fi

echo "Need help? Read docs/SETUP_WITHOUT_DOCKER.md"
echo "========================================="
echo ""
