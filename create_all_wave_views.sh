#!/bin/bash
# Create protected BigQuery views for all waves
#
# This script creates privacy-protected views for each wave:
# - demographics_protected_w35 from demographics_w35
# - survey_responses_protected_w35 from survey_responses_w35
# - demographics_protected_w35_1 from demographics_w35_1
# - survey_responses_protected_w35_1 from survey_responses_w35_1

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Default project
PROJECT=${PROJECT:-chip50}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --project)
      PROJECT="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --project PROJECT    GCP project ID (default: chip50)"
      echo "  -h, --help          Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}Creating Protected BigQuery Views for All Waves${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""
echo "Project: $PROJECT"
echo ""

# Find all view SQL files
VIEW_FILES=$(find sql -name "create_*_protected_w*.sql" | sort)

if [ -z "$VIEW_FILES" ]; then
  echo -e "${RED}✗ Error: No view SQL files found in sql/ directory${NC}"
  exit 1
fi

echo "Found view SQL files:"
echo "$VIEW_FILES" | while read -r file; do
  echo "  - $file"
done
echo ""

# Create each view
SUCCESS_COUNT=0
TOTAL_COUNT=0

echo "$VIEW_FILES" | while read -r sql_file; do
  TOTAL_COUNT=$((TOTAL_COUNT + 1))

  view_name=$(basename "$sql_file" .sql | sed 's/create_//')

  echo -e "${YELLOW}Creating view: $view_name${NC}"

  if bq query --project_id="$PROJECT" --use_legacy_sql=false < "$sql_file"; then
    echo -e "${GREEN}✓ Successfully created $view_name${NC}"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
  else
    echo -e "${RED}✗ Failed to create $view_name${NC}"
  fi

  echo ""
done

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}VIEWS CREATED${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""
echo "View your protected views at:"
echo "https://console.cloud.google.com/bigquery?project=$PROJECT&d=public"
echo ""
echo "Test a query:"
echo "  SELECT region, COUNT(*) as n"
echo "  FROM \`$PROJECT.public.demographics_protected_w35\`"
echo "  GROUP BY region"
echo "  ORDER BY n DESC;"
echo ""
