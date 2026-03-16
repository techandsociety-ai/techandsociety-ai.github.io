#!/bin/bash
# Test the MCP server locally before deployment

set -e

echo "====================================="
echo "Local MCP Server Test"
echo "====================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Set environment variables for local testing
export GCP_PROJECT="${GCP_PROJECT:-your-project-id}"
export DATASET_NAME="${DATASET_NAME:-social_media_demographics}"
export MIN_CELL_SIZE="10"
export API_KEY="${API_KEY:-test_key_123}"
export PORT="8080"

echo ""
echo "Configuration:"
echo "  Project: $GCP_PROJECT"
echo "  Dataset: $DATASET_NAME"
echo "  Port: $PORT"
echo "  API Key: $API_KEY"
echo ""

# Check if user wants to create test data
echo "Do you want to create the BigQuery dataset with synthetic data? (y/N)"
read -r CREATE_DATA

if [ "$CREATE_DATA" = "y" ] || [ "$CREATE_DATA" = "Y" ]; then
    echo "Creating BigQuery dataset..."
    if command -v bq &> /dev/null; then
        bq query --project_id="$GCP_PROJECT" --use_legacy_sql=false < sql/create_synthetic_data.sql
        echo "Dataset created successfully"
    else
        echo "Warning: bq command not found. Skipping dataset creation."
        echo "Install the gcloud CLI to create the dataset: https://cloud.google.com/sdk/docs/install"
    fi
    echo ""
fi

echo "Starting MCP server..."
echo "Press Ctrl+C to stop"
echo ""
echo "Test endpoints:"
echo "  Health: http://localhost:$PORT/health"
echo "  Info: http://localhost:$PORT/info (requires API key)"
echo ""
echo "Test with curl:"
echo "  curl -H \"Authorization: Bearer $API_KEY\" http://localhost:$PORT/info"
echo ""

# Run the server
python server.py
