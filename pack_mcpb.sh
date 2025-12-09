#!/bin/bash
# MCPB Packaging Script for CHIP50 Survey MCP Server
# Creates a proper .mcpb bundle following the MCPB v0.4 specification
#
# Usage:
#   ./pack_mcpb.sh         # Create chip50-survey-mcp.mcpb
#   ./pack_mcpb.sh --clean # Remove build artifacts and rebuild

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="chip50-survey-mcp.mcpb"
BUILD_DIR="$SCRIPT_DIR/.mcpb_build"

echo "📦 CHIP50 Survey MCP - MCPB Packaging"
echo "======================================"
echo ""

# Parse arguments
CLEAN=0
if [ "$1" == "--clean" ]; then
    CLEAN=1
fi

# Step 1: Clean build directory if requested
if [ -d "$BUILD_DIR" ] && [ $CLEAN -eq 1 ]; then
    echo "🧹 Cleaning build directory..."
    rm -rf "$BUILD_DIR"
    echo "   ✓ Cleaned"
    echo ""
fi

# Step 2: Create build directory
echo "📁 Creating build directory..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
echo "   ✓ Build directory created"
echo ""

# Step 3: Copy required files
echo "📋 Copying bundle files..."

# Copy manifest.json (required)
cp "$SCRIPT_DIR/manifest.json" "$BUILD_DIR/"
echo "   ✓ manifest.json"

# Copy icon (optional but recommended)
if [ -f "$SCRIPT_DIR/chip50.png" ]; then
    cp "$SCRIPT_DIR/chip50.png" "$BUILD_DIR/"
    echo "   ✓ chip50.png"
fi

# Copy server directory
mkdir -p "$BUILD_DIR/mcp_server"
cp "$SCRIPT_DIR/mcp_server/server.py" "$BUILD_DIR/mcp_server/"
echo "   ✓ mcp_server/server.py"

# Copy pyproject.toml for reference (optional)
if [ -f "$SCRIPT_DIR/mcp_server/pyproject.toml" ]; then
    cp "$SCRIPT_DIR/mcp_server/pyproject.toml" "$BUILD_DIR/mcp_server/"
    echo "   ✓ mcp_server/pyproject.toml"
fi

# Copy README for documentation (optional)
if [ -f "$SCRIPT_DIR/README.md" ]; then
    cp "$SCRIPT_DIR/README.md" "$BUILD_DIR/"
    echo "   ✓ README.md"
fi

echo ""

# Step 4: Validate manifest
echo "🔍 Validating manifest.json..."
# Set default entry point
ENTRY_POINT="mcp_server/server.py"

if command -v jq &> /dev/null; then
    if jq empty "$BUILD_DIR/manifest.json" 2>/dev/null; then
        echo "   ✓ Valid JSON"

        # Check required fields
        MANIFEST_VERSION=$(jq -r '.manifest_version' "$BUILD_DIR/manifest.json")
        NAME=$(jq -r '.name' "$BUILD_DIR/manifest.json")
        VERSION=$(jq -r '.version' "$BUILD_DIR/manifest.json")
        SERVER_TYPE=$(jq -r '.server.type' "$BUILD_DIR/manifest.json")
        ENTRY_POINT=$(jq -r '.server.entry_point' "$BUILD_DIR/manifest.json")

        echo "   📋 Manifest details:"
        echo "      - Name: $NAME"
        echo "      - Version: $VERSION"
        echo "      - Manifest version: $MANIFEST_VERSION"
        echo "      - Server type: $SERVER_TYPE"
        echo "      - Entry point: $ENTRY_POINT"
    else
        echo "   ✗ Invalid JSON in manifest.json"
        exit 1
    fi
else
    echo "   ⚠ jq not found, using default entry point"
    echo "   📋 Entry point: $ENTRY_POINT"
fi
echo ""

# Step 5: Verify entry point exists
echo "🔍 Verifying entry point..."
if [ -f "$BUILD_DIR/$ENTRY_POINT" ]; then
    echo "   ✓ Entry point exists: $ENTRY_POINT"
else
    echo "   ✗ Entry point not found: $ENTRY_POINT"
    exit 1
fi
echo ""

# Step 6: Test UV can read dependencies
echo "🧪 Testing UV dependency resolution..."
if command -v uv &> /dev/null; then
    cd "$BUILD_DIR"
    if uv run --no-project "$ENTRY_POINT" --help &>/dev/null; then
        echo "   ✓ UV can resolve dependencies from PEP 723 metadata"
    else
        # Try just importing to test dependencies
        if uv run --no-project python -c "import sys; sys.path.insert(0, 'mcp_server'); import server" 2>&1 | grep -q "Installed"; then
            echo "   ✓ UV installed dependencies successfully"
        fi
    fi
    cd "$SCRIPT_DIR"
else
    echo "   ⚠ UV not found, skipping dependency test"
fi
echo ""

# Step 7: Create the .mcpb file (ZIP archive)
echo "🗜️  Creating .mcpb bundle..."
cd "$BUILD_DIR"
rm -f "$SCRIPT_DIR/$OUTPUT_FILE"
zip -r "$SCRIPT_DIR/$OUTPUT_FILE" . -x "*.DS_Store" -x "__pycache__/*" -x "*.pyc" >/dev/null
cd "$SCRIPT_DIR"
echo "   ✓ Bundle created"
echo ""

# Step 8: Verify the bundle
echo "🔍 Verifying bundle..."
if unzip -l "$OUTPUT_FILE" | grep -q "manifest.json"; then
    echo "   ✓ manifest.json present in bundle"
else
    echo "   ✗ manifest.json missing from bundle"
    exit 1
fi

if unzip -l "$OUTPUT_FILE" | grep -q "$ENTRY_POINT"; then
    echo "   ✓ Entry point present in bundle"
else
    echo "   ✗ Entry point missing from bundle"
    exit 1
fi

BUNDLE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
FILE_COUNT=$(unzip -l "$OUTPUT_FILE" | tail -1 | awk '{print $2}')
echo "   ✓ Bundle size: $BUNDLE_SIZE"
echo "   ✓ Total files: $FILE_COUNT"
echo ""

# Step 9: Cleanup
if [ $CLEAN -eq 1 ]; then
    echo "🧹 Cleaning up build directory..."
    rm -rf "$BUILD_DIR"
    echo "   ✓ Cleaned"
    echo ""
fi

# Success!
echo "✅ MCPB bundle created successfully!"
echo ""
echo "📦 Output: $OUTPUT_FILE"
echo ""
echo "Next steps:"
echo "  1. Test the bundle locally:"
echo "     unzip -l $OUTPUT_FILE"
echo ""
echo "  2. Install in Claude Desktop:"
echo "     • Open Claude Desktop"
echo "     • Go to Settings → Extensions"
echo "     • Click 'Install from file'"
echo "     • Select $OUTPUT_FILE"
echo ""
echo "  3. Verify installation:"
echo "     • Restart Claude Desktop"
echo "     • Check that 'CHIP50 Survey Analysis' appears in extensions"
echo "     • Test with: 'List available MCP tools'"
echo ""
