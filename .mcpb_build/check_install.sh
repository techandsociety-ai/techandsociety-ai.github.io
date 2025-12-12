#!/bin/bash
# CHIP50 MCP - Installation Checker
# Verifies all dependencies and configuration are correct

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="$HOME/.chip50"
CONFIG_FILE="$INSTALL_DIR/config.json"

echo -e "${BLUE}"
echo "=========================================="
echo "CHIP50 MCP - Installation Check"
echo "=========================================="
echo -e "${NC}"
echo ""

ERRORS=0
WARNINGS=0

check() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        ((ERRORS++))
    fi
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check Python
echo -e "${BLUE}Python:${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    check 0 "Python 3 installed: $PYTHON_VERSION"

    # Check version
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
        check 0 "Python version >= 3.10"
    else
        check 1 "Python version >= 3.10 (found $PYTHON_VERSION)"
    fi
else
    check 1 "Python 3 not found"
fi
echo ""

# Check UV
echo -e "${BLUE}UV Package Manager:${NC}"
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version 2>&1 | head -1)
    check 0 "UV installed: $UV_VERSION"

    # Check if UV is in PATH
    UV_PATH=$(which uv)
    info "UV location: $UV_PATH"
else
    check 1 "UV not found - install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi
echo ""

# Check Google Cloud SDK
echo -e "${BLUE}Google Cloud SDK:${NC}"
if command -v gcloud &> /dev/null; then
    GCLOUD_VERSION=$(gcloud --version | head -1)
    check 0 "Google Cloud SDK installed"

    # Check authentication
    if gcloud auth application-default print-access-token &>/dev/null; then
        check 0 "Authenticated with Google Cloud"

        # Check project
        PROJECT=$(gcloud config get-value project 2>/dev/null)
        if [ "$PROJECT" == "chip50" ]; then
            check 0 "Project set to 'chip50'"
        else
            warn "Project is '$PROJECT' (expected 'chip50')"
            info "Run: gcloud config set project chip50"
        fi
    else
        check 1 "Not authenticated with Google Cloud"
        info "Run: gcloud auth application-default login"
    fi
else
    check 1 "Google Cloud SDK not found"
fi
echo ""

# Check installation directory
echo -e "${BLUE}Installation:${NC}"
if [ -d "$INSTALL_DIR" ]; then
    check 0 "Install directory exists: $INSTALL_DIR"

    # Check config file
    if [ -f "$CONFIG_FILE" ]; then
        check 0 "Config file exists"

        # Parse config
        if command -v jq &> /dev/null; then
            VERSION=$(jq -r '.version' "$CONFIG_FILE" 2>/dev/null || echo "unknown")
            info "Installed version: $VERSION"
        fi
    else
        check 1 "Config file not found"
    fi

    # Check virtual environment
    if [ -d "$INSTALL_DIR/venv" ]; then
        check 0 "Virtual environment exists"

        # Check if Python in venv works
        if [ -f "$INSTALL_DIR/venv/bin/python" ]; then
            check 0 "Python in virtual environment"

            # Check dependencies
            if "$INSTALL_DIR/venv/bin/python" -c "import pandas, google.cloud.bigquery, mcp" 2>/dev/null; then
                check 0 "Required Python packages installed"
            else
                check 1 "Some required packages missing"
                info "Reinstall with: ./install.sh"
            fi
        else
            check 1 "Python not found in virtual environment"
        fi
    else
        check 1 "Virtual environment not found"
    fi

    # Check bundle
    if [ -d "$INSTALL_DIR/bundle" ]; then
        check 0 "Bundle extracted"

        # Check server file
        if [ -f "$INSTALL_DIR/bundle/mcp_server/server.py" ]; then
            check 0 "MCP server file exists"
        else
            check 1 "MCP server file not found"
        fi
    else
        check 1 "Bundle not extracted"
    fi
else
    check 1 "Installation directory not found"
    info "Run: ./install.sh"
fi
echo ""

# Check Claude Desktop config
echo -e "${BLUE}Claude Desktop:${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    CLAUDE_CONFIG="$HOME/.config/Claude/claude_desktop_config.json"
else
    CLAUDE_CONFIG="unknown"
fi

if [ -f "$CLAUDE_CONFIG" ]; then
    check 0 "Claude Desktop config exists"

    # Check if chip50 server is configured
    if command -v jq &> /dev/null; then
        if jq -e '.mcpServers.chip50' "$CLAUDE_CONFIG" &>/dev/null; then
            check 0 "CHIP50 MCP server configured"

            # Check command path
            CMD=$(jq -r '.mcpServers.chip50.command' "$CLAUDE_CONFIG" 2>/dev/null)
            info "Server command: $CMD"

            # Check if command exists
            if [ -f "$CMD" ]; then
                check 0 "Server command file exists"
            else
                warn "Server command file not found: $CMD"
            fi

            # Check environment variables
            API_KEY=$(jq -r '.mcpServers.chip50.env.CHIP50_API_KEY // empty' "$CLAUDE_CONFIG" 2>/dev/null)
            if [ -n "$API_KEY" ]; then
                check 0 "API key configured"
            else
                warn "API key not set in Claude Desktop config"
            fi
        else
            check 1 "CHIP50 MCP server not configured in Claude Desktop"
            info "Run: ./install.sh"
        fi
    else
        warn "jq not installed - cannot verify Claude Desktop config details"
        info "Install jq with: brew install jq (macOS) or apt-get install jq (Linux)"
    fi
else
    warn "Claude Desktop config not found"
    info "Claude Desktop may not be installed"
    info "Expected location: $CLAUDE_CONFIG"
fi
echo ""

# Check BigQuery access
echo -e "${BLUE}BigQuery Access:${NC}"
if command -v bq &> /dev/null && gcloud auth application-default print-access-token &>/dev/null; then
    # Test query to check access
    if bq ls --project_id=chip50 &>/dev/null; then
        check 0 "Can access BigQuery project 'chip50'"

        # Check for datasets
        if bq ls --project_id=chip50 | grep -q "public"; then
            check 0 "Public dataset exists"

            # Check for protected views
            if bq ls chip50:public 2>/dev/null | grep -q "demographics_protected"; then
                check 0 "Protected views exist"
            else
                warn "Protected views not found"
                info "Run: ./data_setup.sh"
            fi
        else
            warn "Public dataset not found"
            info "Run: ./data_setup.sh"
        fi
    else
        check 1 "Cannot access BigQuery project 'chip50'"
        info "Check permissions or create project"
    fi
else
    warn "Cannot check BigQuery access (gcloud or bq not available)"
fi
echo ""

# Summary
echo -e "${BLUE}"
echo "=========================================="
echo "Summary"
echo "=========================================="
echo -e "${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Your CHIP50 MCP installation is ready to use."
    echo ""
    echo "Next steps:"
    echo "  1. Restart Claude Desktop"
    echo "  2. Ask Claude: 'What variables are available in CHIP50?'"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ Installation complete with $WARNINGS warning(s)${NC}"
    echo ""
    echo "Your installation should work, but review warnings above."
else
    echo -e "${RED}✗ Found $ERRORS error(s) and $WARNINGS warning(s)${NC}"
    echo ""
    echo "Please fix errors above before using CHIP50 MCP."
    echo ""
    echo "Common fixes:"
    echo "  - Install missing dependencies"
    echo "  - Run: ./install.sh"
    echo "  - Authenticate: gcloud auth application-default login"
fi
echo ""

exit $ERRORS
