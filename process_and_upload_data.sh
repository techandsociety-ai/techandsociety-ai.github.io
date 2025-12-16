#!/bin/bash
# Complete pipeline to process and upload CHIP50 real data to BigQuery (Wave-Based)
#
# This script implements a wave-based approach where each wave gets its own tables:
# - CSP_W35.csv → chip50.raw.demographics_w35 & survey_responses_w35
# - CSP_W35.1.csv → chip50.raw.demographics_w35_1 & survey_responses_w35_1
#
# Steps:
# 1. Processes raw CSV files by wave (splits demographics, removes PII)
# 2. Uploads to BigQuery wave-specific raw tables
# 3. Creates protected views for each wave
# 4. Runs verification tests
#
# Usage: ./process_and_upload_data.sh [--project PROJECT] [--dataset DATASET] [--waves WAVE1 WAVE2 ...]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROJECT=${PROJECT:-chip50}
DATASET=${DATASET:-raw}
SKIP_PROCESSING=false
WAVES=()

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --project)
      PROJECT="$2"
      shift 2
      ;;
    --dataset)
      DATASET="$2"
      shift 2
      ;;
    --waves)
      shift
      while [[ $# -gt 0 ]] && [[ ! "$1" =~ ^-- ]]; do
        WAVES+=("$1")
        shift
      done
      ;;
    --skip-processing)
      SKIP_PROCESSING=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --project PROJECT       GCP project ID (default: chip50)"
      echo "  --dataset DATASET       BigQuery dataset (default: raw)"
      echo "  --waves WAVE1 WAVE2...  Specific waves to process (e.g., --waves 35 35.1)"
      echo "  --skip-processing       Skip data processing step (use existing processed files)"
      echo "  -h, --help             Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0 --project chip50-prod --dataset raw"
      echo "  $0 --waves 35 35.1  # Process only specific waves"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}CHIP50 Wave-Based Data Processing and Upload Pipeline${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""
echo "Configuration:"
echo "  Project:  $PROJECT"
echo "  Dataset:  $DATASET"
if [ ${#WAVES[@]} -gt 0 ]; then
  echo "  Waves:    ${WAVES[*]}"
else
  echo "  Waves:    All (auto-detect)"
fi
echo ""

# Check if data files exist
echo -e "${YELLOW}Checking for data files...${NC}"
DATA_FILES=$(find data -maxdepth 1 -name "CSP_W*.csv" -type f 2>/dev/null || true)

if [ -z "$DATA_FILES" ]; then
  echo -e "${RED}✗ Error: No CSV files found in data/ directory${NC}"
  echo ""
  echo "Please place your CHIP50 CSV files in the data/ directory:"
  echo "  data/CSP_W35.csv"
  echo "  data/CSP_W35.1.csv"
  echo "  etc."
  exit 1
fi

echo -e "${GREEN}✓ Found the following data files:${NC}"
echo "$DATA_FILES" | while read -r file; do
  echo "  - $file"
done
echo ""

# Step 1: Process the data
if [ "$SKIP_PROCESSING" = false ]; then
  echo -e "${BLUE}======================================================================${NC}"
  echo -e "${BLUE}Step 1: Processing raw data by wave (removing PII, splitting tables)${NC}"
  echo -e "${BLUE}======================================================================${NC}"
  echo ""

  echo "This creates separate files for each wave:"
  echo "  Wave 35   → chip50_demographics_w35_*.csv & chip50_survey_responses_w35_*.csv"
  echo "  Wave 35.1 → chip50_demographics_w35_1_*.csv & chip50_survey_responses_w35_1_*.csv"
  echo ""

  if ! python3 process_real_data_by_wave.py; then
    echo -e "${RED}✗ Error: Data processing failed${NC}"
    exit 1
  fi

  echo ""
  echo -e "${GREEN}✓ Data processing completed successfully${NC}"
  echo ""
else
  echo -e "${YELLOW}⊘ Skipping data processing (using existing processed files)${NC}"
  echo ""
fi

# Check if processed files exist
PROCESSED_DIR="data/processed"
if [ ! -d "$PROCESSED_DIR" ]; then
  echo -e "${RED}✗ Error: Processed data directory not found: $PROCESSED_DIR${NC}"
  exit 1
fi

# Count processed wave files
PROCESSED_WAVES=$(find "$PROCESSED_DIR" -name "chip50_demographics_w*_*.csv" -type f | wc -l)
if [ "$PROCESSED_WAVES" -eq 0 ]; then
  echo -e "${RED}✗ Error: No processed wave files found in $PROCESSED_DIR${NC}"
  echo "Expected files like:"
  echo "  - chip50_demographics_w35_*.csv"
  echo "  - chip50_survey_responses_w35_*.csv"
  exit 1
fi

echo -e "${GREEN}✓ Found processed files for wave-based upload:${NC}"
find "$PROCESSED_DIR" -name "chip50_*_w*_*.csv" -type f | sort | while read -r file; do
  echo "  - $(basename "$file")"
done
echo ""

# Step 2: Upload to BigQuery
echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}Step 2: Uploading to BigQuery (wave-specific tables)${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""

echo "This creates separate tables for each wave:"
echo "  Wave 35   → $PROJECT.$DATASET.demographics_w35"
echo "             $PROJECT.$DATASET.survey_responses_w35"
echo "  Wave 35.1 → $PROJECT.$DATASET.demographics_w35_1"
echo "             $PROJECT.$DATASET.survey_responses_w35_1"
echo ""

# Build upload command
UPLOAD_CMD="python3 upload_real_data_by_wave.py --project \"$PROJECT\" --dataset \"$DATASET\""

# Add specific waves if provided
if [ ${#WAVES[@]} -gt 0 ]; then
  UPLOAD_CMD="$UPLOAD_CMD --waves ${WAVES[*]}"
fi

if ! eval "$UPLOAD_CMD"; then
  echo -e "${RED}✗ Error: BigQuery upload failed${NC}"
  exit 1
fi

echo ""
echo -e "${GREEN}✓ BigQuery upload completed successfully${NC}"
echo ""

# Step 3: Create protected views
echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}Step 3: Creating protected views (one per wave)${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""

echo "This creates privacy-protected views in the public dataset:"
echo "  - Removes id column"
echo "  - Aggregates state → region"
echo "  - Adds non-reversible row_hash for joining"
echo ""

if [ ! -f "./create_all_wave_views.sh" ]; then
  echo -e "${YELLOW}⚠ Warning: create_all_wave_views.sh not found${NC}"
  echo ""
  echo "You can manually create views by running SQL files in sql/ directory:"
  SQL_FILES=$(find sql -name "create_*_protected_w*.sql" -type f 2>/dev/null | sort)
  if [ -n "$SQL_FILES" ]; then
    echo "$SQL_FILES" | while read -r sql_file; do
      echo "  bq query --project_id=$PROJECT < $sql_file"
    done
  else
    echo "  No SQL files found matching pattern: sql/create_*_protected_w*.sql"
  fi
else
  if ! ./create_all_wave_views.sh; then
    echo -e "${RED}✗ Error: View creation failed${NC}"
    exit 1
  fi

  echo ""
  echo -e "${GREEN}✓ Protected views created successfully${NC}"
fi

echo ""

# Step 4: Summary
echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}PIPELINE COMPLETE!${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""
echo -e "${GREEN}✓ All steps completed successfully${NC}"
echo ""
echo "Your wave-based data is now available in BigQuery:"
echo ""

# Dynamically list raw tables
echo "  Raw tables (in $PROJECT.$DATASET):"
RAW_TABLES=$(bq ls --project_id="$PROJECT" --dataset_id="$DATASET" --format=csv 2>/dev/null | tail -n +2 | grep -E "(demographics_w|survey_responses_w)" | cut -d',' -f1 || echo "")
if [ -n "$RAW_TABLES" ]; then
  echo "$RAW_TABLES" | sort | while read -r table; do
    [ -n "$table" ] && echo "    - $PROJECT.$DATASET.$table"
  done
else
  # Fallback: detect from processed files
  echo "    (Detecting from processed files...)"
  find "$PROCESSED_DIR" -name "chip50_demographics_w*_*.csv" -type f 2>/dev/null | sort | while read -r file; do
    WAVE=$(basename "$file" | sed -E 's/chip50_demographics_(w[0-9_]+)_.*/\1/')
    echo "    - $PROJECT.$DATASET.demographics_$WAVE"
    echo "    - $PROJECT.$DATASET.survey_responses_$WAVE"
  done | sort -u
fi
echo ""

# Dynamically list protected views
echo "  Protected views (in $PROJECT.public):"
PROTECTED_VIEWS=$(bq ls --project_id="$PROJECT" --dataset_id="public" --format=csv 2>/dev/null | tail -n +2 | grep -E "protected_w" | cut -d',' -f1 || echo "")
if [ -n "$PROTECTED_VIEWS" ]; then
  echo "$PROTECTED_VIEWS" | sort | while read -r view; do
    [ -n "$view" ] && echo "    - $PROJECT.public.$view"
  done
else
  # Fallback: list SQL files that should have been executed
  echo "    (Expected based on SQL files...)"
  find sql -name "create_*_protected_w*.sql" -type f 2>/dev/null | sort | while read -r sql_file; do
    VIEW_NAME=$(basename "$sql_file" .sql | sed 's/create_//')
    echo "    - $PROJECT.public.$VIEW_NAME"
  done
fi
echo ""

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}NEXT STEPS${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""
echo "  1. View your data in BigQuery console:"
echo "     https://console.cloud.google.com/bigquery?project=$PROJECT&d=$DATASET"
echo ""
echo "  2. Query a specific wave (example for w35):"
echo "     SELECT region, party7, COUNT(*) as n"
echo "     FROM \`$PROJECT.public.demographics_protected_w35\`"
echo "     GROUP BY region, party7"
echo ""
echo "  3. Compare across waves:"
echo "     See WAVE_BASED_WORKFLOW.md for cross-wave query examples"
echo ""
echo "  4. Test the MCP server:"
echo "     python test_bigquery_crosstab.py"
echo ""
echo "  5. Review documentation:"
echo "     - WAVE_BASED_WORKFLOW.md (wave-specific workflow)"
echo "     - DATA_PROCESSING.md (general processing guide)"
echo ""
