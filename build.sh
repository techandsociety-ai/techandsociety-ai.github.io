#!/bin/bash
# Build script for CHIP50 Survey MCP
# Creates virtual environment and installs dependencies
#
# Usage:
#   ./build.sh         # Build or update existing venv
#   ./build.sh --clean # Remove and rebuild venv from scratch

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/mcp_server/venv"

echo "🔨 Building CHIP50 Survey MCP"
echo "=============================="
echo ""

# Parse arguments
CLEAN=0
if [ "$1" == "--clean" ]; then
    CLEAN=1
fi

# Step 1: Create virtual environment
if [ -d "$VENV_DIR" ]; then
    if [ $CLEAN -eq 1 ]; then
        echo "📦 Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
        echo "   ✓ Removed"
        echo ""
    else
        echo "📦 Virtual environment already exists"
        echo "   Using existing venv (use --clean to rebuild)"
        echo ""
        SKIP_VENV=1
    fi
fi

if [ -z "$SKIP_VENV" ]; then
    echo "📦 Creating virtual environment..."
    cd "$SCRIPT_DIR/mcp_server"
    python3 -m venv venv
    echo "   ✓ Virtual environment created"
    echo ""
fi

# Step 2: Install dependencies
echo "📥 Installing dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install pandas google-cloud-bigquery db-dtypes mcp --quiet
echo "   ✓ Dependencies installed"
echo ""

# Step 3: Verify installation
echo "🔍 Verifying installation..."
INSTALLED_PACKAGES=$("$VENV_DIR/bin/pip" list --format=freeze | grep -E "pandas|google-cloud-bigquery|db-dtypes|mcp" | wc -l)
if [ "$INSTALLED_PACKAGES" -ge 4 ]; then
    echo "   ✓ Core dependencies verified:"
    "$VENV_DIR/bin/pip" list | grep -E "pandas|google-cloud-bigquery|db-dtypes|mcp"
else
    echo "   ✗ Some dependencies missing"
    exit 1
fi
echo ""

# Step 4: Test server imports
echo "🧪 Testing server imports..."
if "$VENV_DIR/bin/python" -c "import sys; sys.path.insert(0, '$SCRIPT_DIR/mcp_server'); from server import SurveyAnalysisServer; print('✓ Server imports successfully')" 2>&1; then
    echo "   ✓ Server can be imported"
else
    echo "   ✗ Server import failed"
    exit 1
fi
echo ""

echo "✅ Build complete!"
echo ""
echo "📊 Installation summary:"
echo "   Python: $("$VENV_DIR/bin/python" --version)"
echo "   Location: $VENV_DIR"
echo "   Size: $(du -sh "$VENV_DIR" | cut -f1)"
echo ""
echo "Next steps:"
echo ""
echo "  1. Test locally:"
echo "     cd mcp_server"
echo "     ./venv/bin/python server.py"
echo ""
echo "  2. Run tests:"
echo "     python3 test_mcp_server.py"
echo ""
echo "  3. Install to Claude Desktop:"
echo "     • In Claude Desktop, go to Settings → Developer"
echo "     • Add this directory as an MCP extension"
echo "     • Restart Claude Desktop"
echo ""
echo "See INSTALLATION.md for detailed instructions."
echo ""
