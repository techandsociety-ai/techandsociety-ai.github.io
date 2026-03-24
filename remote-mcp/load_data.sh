#!/bin/bash
set -e

source ../.env

# CHIP50 Social Media Demographics MCP - Data Load Script
# Loads the panel CSV into BigQuery and rebuilds the indexed table.
# Run this manually whenever the source data file changes.
# Cloud Run deployment is handled separately via GitHub Actions (push to main).

GCP_PROJECT="${GCP_PROJECT:-chip50}"
DATASET_NAME="${DATASET_NAME:-social_media_demographics}"
DATA_FILE="${DATA_FILE:-../data/export_CHIP50_SocialMedia_vars_2026_03_20_23_57.csv}"
RAW_TABLE="${DATASET_NAME}.panel_data"

echo "==================================="
echo "CHIP50 Social Media Demographics MCP"
echo "BigQuery Data Load"
echo "==================================="
echo ""
echo "  Project:  $GCP_PROJECT"
echo "  Dataset:  $DATASET_NAME"
echo "  Data:     $DATA_FILE"
echo ""

for cmd in gcloud bq; do
    if ! command -v $cmd &> /dev/null; then
        echo "Error: $cmd CLI is not installed."
        exit 1
    fi
done

gcloud config set project "$GCP_PROJECT"

# Create dataset if needed
if ! bq show --project_id="$GCP_PROJECT" "$DATASET_NAME" &> /dev/null; then
    echo "Creating dataset $DATASET_NAME..."
    bq mk --project_id="$GCP_PROJECT" --dataset --location=US "$DATASET_NAME"
else
    echo "Dataset $DATASET_NAME already exists."
fi

# Check data file exists
if [ ! -f "$DATA_FILE" ]; then
    echo "Error: Data file not found at $DATA_FILE"
    exit 1
fi

# Load CSV into raw panel_data table (overwrite if exists)
echo "Loading CSV into $RAW_TABLE (this may take a minute)..."
bq load \
    --project_id="$GCP_PROJECT" \
    --source_format=CSV \
    --skip_leading_rows=1 \
    --replace \
    --autodetect \
    "$RAW_TABLE" \
    "$DATA_FILE"
echo "Raw data loaded."

# Rebuild clustered indexed table
echo "Rebuilding clustered indexed table..."
bq query \
    --project_id="$GCP_PROJECT" \
    --use_legacy_sql=false \
    < sql/create_schema.sql
echo "BigQuery setup complete."
echo ""
