#!/bin/bash
# CHIP50 MCP Bundle - Cross-Platform Installer (macOS/Linux)
# Installs Python dependencies and configures Claude Desktop automatically

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BUNDLE_NAME="chip50-survey-mcp"
VERSION="2.0.0"
MCPB_FILE="${BUNDLE_NAME}-v${VERSION}.mcpb"
INSTALL_DIR="$HOME/.chip50"
CONFIG_FILE="$INSTALL_DIR/config.json"

echo -e "${BLUE}"
echo "=========================================="
echo "CHIP50 Survey MCP - Installation"
echo "=========================================="
echo -e "${NC}"
echo ""

# Helper functions
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        print_error "Unsupported OS: $OSTYPE"
        exit 1
    fi
    print_info "Detected OS: $OS"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Step 1: Check prerequisites
check_prerequisites() {
    echo ""
    echo -e "${BLUE}[1/6] Checking prerequisites...${NC}"
    echo ""

    # Check Python
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version | awk '{print $2}')
        print_success "Python 3 found: $PYTHON_VERSION"

        # Check Python version is >= 3.10
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
            print_success "Python version is 3.10 or higher"
        else
            print_warning "Python 3.10+ recommended (found $PYTHON_VERSION)"
        fi
    else
        print_error "Python 3 not found. Please install Python 3.10+ first."
        echo ""
        if [[ "$OS" == "macos" ]]; then
            echo "Install with: brew install python@3.11"
        else
            echo "Install with: sudo apt-get install python3.11"
        fi
        exit 1
    fi

    # Check UV
    if command_exists uv; then
        UV_VERSION=$(uv --version 2>&1 | head -1)
        print_success "UV found: $UV_VERSION"
    else
        print_warning "UV not found. Installing UV..."
        curl -LsSf https://astral.sh/uv/install.sh | sh

        # Add UV to PATH for this session
        export PATH="$HOME/.local/bin:$PATH"

        if command_exists uv; then
            print_success "UV installed successfully"
        else
            print_error "UV installation failed"
            exit 1
        fi
    fi

    # Check gcloud
    if command_exists gcloud; then
        GCLOUD_VERSION=$(gcloud --version | head -1)
        print_success "Google Cloud SDK found"
    else
        print_warning "Google Cloud SDK not found"
        echo ""
        echo "You'll need to install Google Cloud SDK to use this MCP server."
        echo ""
        if [[ "$OS" == "macos" ]]; then
            echo "Install with: brew install google-cloud-sdk"
        else
            echo "Install with: curl https://sdk.cloud.google.com | bash"
        fi
        echo ""
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    print_success "Prerequisites check complete"
}

# Step 2: Check for bundle file
check_bundle() {
    echo ""
    echo -e "${BLUE}[2/6] Checking for bundle file...${NC}"
    echo ""

    if [ -f "$MCPB_FILE" ]; then
        print_success "Bundle found: $MCPB_FILE"
    else
        print_error "Bundle file not found: $MCPB_FILE"
        echo ""
        echo "Please download the bundle from:"
        echo "  https://github.com/nanocentury-ai/chip50MCP/releases/latest"
        echo ""
        echo "Or build it with:"
        echo "  ./build_mcpb.sh"
        exit 1
    fi
}

# Step 3: Install Python dependencies
install_dependencies() {
    echo ""
    echo -e "${BLUE}[3/6] Installing Python dependencies...${NC}"
    echo ""

    # Create virtual environment with UV
    print_info "Creating virtual environment..."
    uv venv "$INSTALL_DIR/venv" --python python3.10 || true

    # Install dependencies
    print_info "Installing dependencies..."
    uv pip install -q --python "$INSTALL_DIR/venv/bin/python" \
        pandas>=2.0.0 \
        google-cloud-bigquery>=3.11.0 \
        db-dtypes>=1.1.0 \
        mcp>=0.9.0

    print_success "Dependencies installed"
}

# Step 4: Setup Google Cloud authentication
setup_gcloud_auth() {
    echo ""
    echo -e "${BLUE}[4/6] Setting up Google Cloud authentication...${NC}"
    echo ""

    if command_exists gcloud; then
        # Check if already authenticated
        if gcloud auth application-default print-access-token >/dev/null 2>&1; then
            print_success "Already authenticated with Google Cloud"
        else
            print_warning "Not authenticated with Google Cloud"
            echo ""
            echo "Would you like to authenticate now? (Recommended)"
            read -p "Authenticate? (y/n) " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                gcloud auth application-default login
                gcloud config set project chip50
                print_success "Authentication complete"
            else
                print_warning "Skipping authentication. You'll need to run:"
                echo "  gcloud auth application-default login"
                echo "  gcloud config set project chip50"
            fi
        fi
    else
        print_warning "Google Cloud SDK not installed, skipping authentication"
    fi
}

# Step 5: Create configuration
create_config() {
    echo ""
    echo -e "${BLUE}[5/6] Creating configuration...${NC}"
    echo ""

    # Create install directory
    mkdir -p "$INSTALL_DIR"

    # Extract bundle to install directory
    print_info "Extracting bundle..."
    unzip -q -o "$MCPB_FILE" -d "$INSTALL_DIR/bundle"

    # Create config file
    cat > "$CONFIG_FILE" << EOF
{
  "version": "$VERSION",
  "install_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "bundle_path": "$INSTALL_DIR/bundle",
  "venv_path": "$INSTALL_DIR/venv",
  "api_key": "chip50_test_synthetic_data_only",
  "project_id": "chip50",
  "dataset_public": "public",
  "min_cell_size": 10
}
EOF

    print_success "Configuration created at $CONFIG_FILE"
}

# Step 6: Configure Claude Desktop
configure_claude_desktop() {
    echo ""
    echo -e "${BLUE}[6/6] Configuring Claude Desktop...${NC}"
    echo ""

    # Detect Claude Desktop config location
    if [[ "$OS" == "macos" ]]; then
        CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
    else
        CLAUDE_CONFIG_DIR="$HOME/.config/Claude"
    fi

    CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"

    # Check if Claude Desktop is installed
    if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
        print_warning "Claude Desktop config directory not found"
        echo ""
        echo "Claude Desktop may not be installed yet."
        echo "After installing Claude Desktop, you can manually add the server configuration."
        echo ""
        echo "Config location: $CLAUDE_CONFIG_FILE"
        echo ""
        print_manual_config
        return
    fi

    # Create config directory if needed
    mkdir -p "$CLAUDE_CONFIG_DIR"

    # Check if config file exists
    if [ ! -f "$CLAUDE_CONFIG_FILE" ]; then
        # Create new config
        cat > "$CLAUDE_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "chip50": {
      "command": "$INSTALL_DIR/venv/bin/python",
      "args": [
        "$INSTALL_DIR/bundle/mcp_server/server.py"
      ],
      "env": {
        "CHIP50_API_KEY": "chip50_test_synthetic_data_only",
        "CHIP50_PROJECT_ID": "chip50",
        "CHIP50_DATASET_PUBLIC": "public",
        "CHIP50_MIN_CELL_SIZE": "10"
      }
    }
  }
}
EOF
        print_success "Created Claude Desktop configuration"
    else
        print_warning "Claude Desktop config already exists"
        echo ""
        echo "Please manually add the following to your Claude Desktop config:"
        echo ""
        print_manual_config
    fi
}

# Print manual configuration instructions
print_manual_config() {
    cat << EOF
Add this to $CLAUDE_CONFIG_FILE:

{
  "mcpServers": {
    "chip50": {
      "command": "$INSTALL_DIR/venv/bin/python",
      "args": [
        "$INSTALL_DIR/bundle/mcp_server/server.py"
      ],
      "env": {
        "CHIP50_API_KEY": "chip50_test_synthetic_data_only",
        "CHIP50_PROJECT_ID": "chip50",
        "CHIP50_DATASET_PUBLIC": "public",
        "CHIP50_MIN_CELL_SIZE": "10"
      }
    }
  }
}
EOF
}

# Main installation flow
main() {
    detect_os
    check_prerequisites
    check_bundle
    install_dependencies
    setup_gcloud_auth
    create_config
    configure_claude_desktop

    echo ""
    echo -e "${GREEN}"
    echo "=========================================="
    echo "✓ Installation Complete!"
    echo "=========================================="
    echo -e "${NC}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo ""
    echo "1. Restart Claude Desktop (if running)"
    echo "2. Verify the CHIP50 MCP server appears in Settings → MCP Servers"
    echo "3. Test by asking Claude: 'What variables are available in CHIP50?'"
    echo ""
    echo -e "${BLUE}Configuration:${NC}"
    echo "  Install directory: $INSTALL_DIR"
    echo "  Config file: $CONFIG_FILE"
    echo "  Virtual environment: $INSTALL_DIR/venv"
    echo ""
    echo -e "${BLUE}Google Cloud:${NC}"
    if command_exists gcloud; then
        if gcloud auth application-default print-access-token >/dev/null 2>&1; then
            echo "  Status: ✓ Authenticated"
        else
            echo "  Status: ⚠ Not authenticated"
            echo "  Run: gcloud auth application-default login"
        fi
    else
        echo "  Status: ⚠ Google Cloud SDK not installed"
    fi
    echo ""
    echo -e "${BLUE}Documentation:${NC}"
    echo "  Quick Start: $INSTALL_DIR/bundle/QUICKSTART.md"
    echo "  Setup Guide: $INSTALL_DIR/bundle/SETUP.md"
    echo ""
    echo "Need help? Check the documentation or report issues at:"
    echo "  https://github.com/nanocentury-ai/chip50MCP/issues"
    echo ""
}

# Run installation
main
