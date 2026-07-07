#!/bin/bash
set -e

source ../.env

# CHIP50 Social Media Demographics MCP - Data Load Script
# Loads the panel CSV into BigQuery and rebuilds the indexed table.
# Run this manually whenever the source data file changes.
# Cloud Run deployment is handled separately via GitHub Actions (push to main).

GCP_PROJECT="${GCP_PROJECT:-chip50}"
DATASET_NAME="${DATASET_NAME:-social_media_demographics}"
# Accept path as first positional arg, then DATA_FILE env var, then default
DATA_FILE="${1:-${DATA_FILE:-../data/export_CHIP50_SocialMedia_vars_2026_06_27_plumbing.csv}}"
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

# Generate explicit schema JSON so wave is FLOAT64 (handles fractional waves 33.5, 35.1).
# --autodetect infers INT64 from the first rows (all wave=1) and then fails on fractional values.
SCHEMA_FILE=$(mktemp /tmp/chip50_schema_XXXXXX.json)
python3 - "$DATA_FILE" "$SCHEMA_FILE" <<'PYEOF'
import csv, json, sys

# Columns that must be STRING (categorical, identifier, or free-text)
STRING_COLS = {
    'id', 'state_code', 'race_cat_5', 'gender', 'party3', 'urban_type',
    'age_cat_8', 'education_cat', 'race', 'county', 'survey_ai_tools',
    'StartDate', 'EndDate',
}

csv_file, out_file = sys.argv[1], sys.argv[2]
with open(csv_file, newline='') as f:
    cols = csv.DictReader(f).fieldnames

def col_type(col):
    # Free-text open-ended fields
    if col.endswith('_TEXT') or col in STRING_COLS:
        return 'STRING'
    return 'FLOAT64'

schema = [{'name': col, 'type': col_type(col), 'mode': 'NULLABLE'} for col in cols]
with open(out_file, 'w') as f:
    json.dump(schema, f)
print(f"Schema written: {len(schema)} columns")
PYEOF

# Load CSV into raw panel_data table (overwrite if exists)
echo "Loading CSV into $RAW_TABLE (this may take a minute)..."
bq load \
    --project_id="$GCP_PROJECT" \
    --source_format=CSV \
    --skip_leading_rows=1 \
    --replace \
    --schema="$SCHEMA_FILE" \
    "$RAW_TABLE" \
    "$DATA_FILE"
rm -f "$SCHEMA_FILE"
echo "Raw data loaded."

# Rebuild clustered indexed table
echo "Rebuilding clustered indexed table..."
bq query \
    --project_id="$GCP_PROJECT" \
    --use_legacy_sql=false \
    < sql/create_schema.sql
echo "BigQuery setup complete."
echo ""
