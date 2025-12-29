#!/bin/bash
set -e

# Build CHIP50 MCP Bundle
# Creates a .mcpb file that can be installed in Claude Desktop

echo "=========================================="
echo "Building CHIP50 MCP Bundle"
echo "=========================================="
echo ""

# Configuration
BUNDLE_NAME="chip50-survey-mcp"
VERSION=$(grep '"version"' manifest.json | head -1 | sed 's/.*"version": "\(.*\)".*/\1/')
OUTPUT_FILE="${BUNDLE_NAME}-v${VERSION}.mcpb"

echo "Bundle: ${BUNDLE_NAME}"
echo "Version: ${VERSION}"
echo "Output: ${OUTPUT_FILE}"
echo ""

# Clean previous builds
echo "[1/4] Cleaning previous builds..."
rm -rf .mcpb_build
rm -f *.mcpb
echo "✓ Clean complete"
echo ""

# Create build directory
echo "[2/4] Creating bundle structure..."
mkdir -p .mcpb_build

# Copy necessary files
cp manifest.json .mcpb_build/
cp -r mcp_server .mcpb_build/
cp -r synthetic_data .mcpb_build/
cp -r sql .mcpb_build/
cp README.md .mcpb_build/
cp DATA_PROCESSING.md .mcpb_build/
cp WAVE_BASED_WORKFLOW.md .mcpb_build/
cp pyproject.toml .mcpb_build/

# Copy installation scripts
cp install.sh .mcpb_build/
cp install.ps1 .mcpb_build/
cp check_install.sh .mcpb_build/

# Make scripts executable
chmod +x .mcpb_build/install.sh
chmod +x .mcpb_build/check_install.sh

# Copy icon if it exists
if [ -f "chip50.png" ]; then
    cp chip50.png .mcpb_build/
else
    echo "Warning: chip50.png not found, bundle will use default icon"
fi

echo "✓ Files copied to .mcpb_build/"
echo ""

# Create the bundle using mcpb pack
echo "[3/4] Creating bundle with mcpb pack..."

# Check if mcpb is available
if ! command -v mcpb &> /dev/null; then
    echo "Error: mcpb command not found"
    echo "Install with: npm install -g @anthropic/mcpb"
    exit 1
fi

# Pack the bundle
mcpb pack .mcpb_build "${OUTPUT_FILE}"

echo "✓ Bundle created: ${OUTPUT_FILE}"
echo ""

# Show bundle info
echo "[4/4] Bundle information:"
BUNDLE_SIZE=$(du -h "${OUTPUT_FILE}" | cut -f1)
echo "  Size: ${BUNDLE_SIZE}"
echo "  Location: $(pwd)/${OUTPUT_FILE}"
echo ""

# Generate checksum
echo "Generating SHA-256 checksum..."
if command -v shasum &> /dev/null; then
    shasum -a 256 "${OUTPUT_FILE}" > "${OUTPUT_FILE}.sha256"
    echo "✓ Checksum saved to ${OUTPUT_FILE}.sha256"
elif command -v sha256sum &> /dev/null; then
    sha256sum "${OUTPUT_FILE}" > "${OUTPUT_FILE}.sha256"
    echo "✓ Checksum saved to ${OUTPUT_FILE}.sha256"
fi
echo ""

echo "=========================================="
echo "✓ Build Complete!"
echo "=========================================="
echo ""
echo "Installation Methods:"
echo ""
echo "Method 1: Automated Installation (Recommended)"
echo "  macOS/Linux:"
echo "    ./install.sh"
echo ""
echo "  Windows (PowerShell):"
echo "    .\\install.ps1"
echo ""
echo "Method 2: Manual Installation via Claude Desktop"
echo "  1. Open Claude Desktop"
echo "  2. Go to Settings → MCP Servers"
echo "  3. Drag-and-drop ${OUTPUT_FILE}"
echo "  4. Configure environment variables in settings"
echo ""
echo "Method 3: Extract and use directly"
echo "  unzip ${OUTPUT_FILE} -d ~/.chip50/"
echo "  Edit Claude Desktop config manually"
echo ""
echo "Check your installation:"
echo "  ./check_install.sh"
echo ""
echo "Bundle ready for distribution!"
echo ""
