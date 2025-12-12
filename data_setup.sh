#!/bin/bash
set -e  # Exit on error

# CHIP50 Data Setup Script
# This script sets up the complete data pipeline:
# 1. Authenticates with Google Cloud
# 2. Generates synthetic data
# 3. Uploads to BigQuery raw tables (chip50.raw.*)
# 4. Creates protected public views (chip50.public.*)

echo "========================================"
echo "CHIP50 Data Setup Pipeline"
echo "========================================"
echo ""

# Configuration
PROJECT_ID="chip50"
RAW_DATASET="raw"
PUBLIC_DATASET="public"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check for UV
echo -e "${BLUE}[1/6] Checking for UV package manager...${NC}"
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: UV not found. Please install it first:${NC}"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
echo -e "${GREEN}✓ UV found${NC}"
echo ""

# Step 2: Authenticate with Google Cloud
echo -e "${BLUE}[2/6] Authenticating with Google Cloud...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo -e "${YELLOW}No active Google Cloud authentication found.${NC}"
    echo "Please authenticate with gcloud:"
    gcloud auth login
    gcloud auth application-default login
else
    echo -e "${GREEN}✓ Already authenticated with Google Cloud${NC}"
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
    echo -e "  Active account: ${ACTIVE_ACCOUNT}"
fi

# Set the project
echo "Setting project to: ${PROJECT_ID}"
gcloud config set project ${PROJECT_ID}
echo ""

# Step 3: Ensure BigQuery datasets exist
echo -e "${BLUE}[3/6] Checking BigQuery datasets...${NC}"

# Check/create raw dataset
if ! bq ls -d ${PROJECT_ID}:${RAW_DATASET} &> /dev/null; then
    echo "Creating dataset: ${PROJECT_ID}.${RAW_DATASET}"
    bq mk --dataset \
        --location=US \
        --description="Raw survey data (restricted access)" \
        ${PROJECT_ID}:${RAW_DATASET}
else
    echo -e "${GREEN}✓ Dataset exists: ${PROJECT_ID}.${RAW_DATASET}${NC}"
fi

# Check/create public dataset
if ! bq ls -d ${PROJECT_ID}:${PUBLIC_DATASET} &> /dev/null; then
    echo "Creating dataset: ${PROJECT_ID}.${PUBLIC_DATASET}"
    bq mk --dataset \
        --location=US \
        --description="Public-facing protected views (privacy-preserving)" \
        ${PROJECT_ID}:${PUBLIC_DATASET}
else
    echo -e "${GREEN}✓ Dataset exists: ${PROJECT_ID}.${PUBLIC_DATASET}${NC}"
fi
echo ""

# Step 4: Generate synthetic data
echo -e "${BLUE}[4/6] Generating synthetic data...${NC}"
if [ ! -f "synthetic_data/synthetic_demographics.csv" ] || [ ! -f "synthetic_data/synthetic_survey_responses.csv" ]; then
    echo "Running synthetic data generator..."
    uv run python synthetic_data/generate_synthetic_data.py
    echo -e "${GREEN}✓ Synthetic data generated${NC}"
else
    echo -e "${YELLOW}Synthetic data files already exist. Skipping generation.${NC}"
    echo "To regenerate, delete the files in synthetic_data/ and run again."
fi
echo ""

# Step 5: Upload data to BigQuery
echo -e "${BLUE}[5/6] Uploading data to BigQuery...${NC}"
echo "This will upload synthetic data to:"
echo "  - ${PROJECT_ID}.${RAW_DATASET}.demographics"
echo "  - ${PROJECT_ID}.${RAW_DATASET}.survey_responses"
echo ""

uv run python upload_to_bigquery.py

echo -e "${GREEN}✓ Data uploaded successfully${NC}"
echo ""

# Step 6: Create protected public views
echo -e "${BLUE}[6/6] Creating protected public views...${NC}"
echo "Creating privacy-preserving views in ${PROJECT_ID}.${PUBLIC_DATASET}"
echo ""

# Create demographics_protected view
echo "Creating demographics_protected view..."
bq query --use_legacy_sql=false < sql/create_demographics_protected.sql

# Create survey_responses_protected view
echo "Creating survey_responses_protected view..."
bq query --use_legacy_sql=false < sql/create_survey_responses_protected.sql

echo -e "${GREEN}✓ Protected views created${NC}"
echo ""

# Final summary
echo "========================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================"
echo ""
echo "Raw data tables (restricted access):"
echo "  - ${PROJECT_ID}.${RAW_DATASET}.demographics"
echo "  - ${PROJECT_ID}.${RAW_DATASET}.survey_responses"
echo ""
echo "Public views (privacy-preserving):"
echo "  - ${PROJECT_ID}.${PUBLIC_DATASET}.demographics_protected"
echo "  - ${PROJECT_ID}.${PUBLIC_DATASET}.survey_responses_protected"
echo ""
echo "View your data at:"
echo "  https://console.cloud.google.com/bigquery?project=${PROJECT_ID}"
echo ""
echo "Next steps:"
echo "  1. Test the protected views with sample queries"
echo "  2. Set up IAM permissions for tiered access"
echo "  3. Deploy the MCP server"
echo ""
