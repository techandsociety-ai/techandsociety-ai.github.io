#!/bin/bash

# Test CHIP50 MCP Server with MCP Inspector
# This launches the server in the MCP Inspector for interactive testing

echo "=========================================="
echo "CHIP50 MCP Server - Inspector Test"
echo "=========================================="
echo ""

# Set environment variables
export CHIP50_API_KEY="chip50_test_synthetic_data_only"
export CHIP50_PROJECT_ID="chip50"
export CHIP50_DATASET_PUBLIC="public"
export CHIP50_MIN_CELL_SIZE="10"

# Ensure Google Cloud credentials are available
# This uses the application default credentials from gcloud
export GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS:-$HOME/.config/gcloud/application_default_credentials.json}"

# Verify the credentials file exists
if [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "Warning: Application default credentials not found at:"
    echo "  $GOOGLE_APPLICATION_CREDENTIALS"
    echo ""
    echo "Running: gcloud auth application-default login"
    gcloud auth application-default login
    echo ""
fi

echo "Environment variables set:"
echo "  CHIP50_API_KEY: $CHIP50_API_KEY"
echo "  CHIP50_PROJECT_ID: $CHIP50_PROJECT_ID"
echo "  CHIP50_DATASET_PUBLIC: $CHIP50_DATASET_PUBLIC"
echo "  CHIP50_MIN_CELL_SIZE: $CHIP50_MIN_CELL_SIZE"
echo ""

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Project directory: $PROJECT_DIR"
echo ""
echo "Launching MCP Inspector..."
echo ""
echo "Once the inspector opens in your browser:"
echo "  1. You should see two tools: get_available_variables and generate_crosstab"
echo "  2. Try 'get_available_variables' first to see what data is available"
echo "  3. Then try 'generate_crosstab' with:"
echo "     - survey_variable: trust_congress"
echo "     - demographic_variable: party_7"
echo ""
echo "Press Ctrl+C to stop the inspector when done."
echo ""

# Launch the inspector with environment variables explicitly passed
CHIP50_API_KEY="$CHIP50_API_KEY" \
CHIP50_PROJECT_ID="$CHIP50_PROJECT_ID" \
CHIP50_DATASET_PUBLIC="$CHIP50_DATASET_PUBLIC" \
CHIP50_MIN_CELL_SIZE="$CHIP50_MIN_CELL_SIZE" \
GOOGLE_APPLICATION_CREDENTIALS="$GOOGLE_APPLICATION_CREDENTIALS" \
npx @modelcontextprotocol/inspector uv run --directory "$PROJECT_DIR" python mcp_server/server.py
