#!/bin/bash
set -e

# Quick test script for protected views
# Run this to verify the protected views are working correctly

echo "========================================="
echo "Testing CHIP50 Protected Views"
echo "========================================="
echo ""

PROJECT="chip50"

# Test 1: Demographics structure
echo "Test 1: Demographics Protected View Structure"
echo "----------------------------------------------"
bq query --use_legacy_sql=false --format=pretty \
  --project_id="$PROJECT" "
SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT row_hash) AS unique_row_hashes,
  COUNT(DISTINCT wave) AS num_waves,
  COUNT(DISTINCT region) AS num_regions
FROM \`chip50.public.demographics_protected\`
"
echo ""

# Test 2: Survey responses structure
echo "Test 2: Survey Responses Protected View Structure"
echo "--------------------------------------------------"
bq query --use_legacy_sql=false --format=pretty \
  --project_id="$PROJECT" "
SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT row_hash) AS unique_row_hashes,
  COUNT(DISTINCT wave) AS num_waves
FROM \`chip50.public.survey_responses_protected\`
"
echo ""

# Test 3: JOIN test
echo "Test 3: JOIN Test (Demographics + Survey)"
echo "------------------------------------------"
bq query --use_legacy_sql=false --format=pretty \
  --project_id="$PROJECT" "
SELECT
  d.wave,
  d.region,
  d.party_7,
  s.trust_congress,
  s.vote_intention
FROM \`chip50.public.demographics_protected\` d
JOIN \`chip50.public.survey_responses_protected\` s
  ON d.row_hash = s.row_hash AND d.wave = s.wave
LIMIT 5
"
echo ""

# Test 4: Regional aggregation
echo "Test 4: Verify Regional Aggregation"
echo "------------------------------------"
bq query --use_legacy_sql=false --format=pretty \
  --project_id="$PROJECT" "
SELECT
  region,
  COUNT(DISTINCT row_hash) AS unique_respondents,
  COUNT(*) AS total_observations
FROM \`chip50.public.demographics_protected\`
GROUP BY region
ORDER BY region
"
echo ""

# Test 5: Privacy check (should FAIL)
echo "Test 5: Privacy Check - Verify PII Columns Are Blocked"
echo "-------------------------------------------------------"
echo "This test should FAIL with 'Unrecognized name: id' error:"
bq query --use_legacy_sql=false \
  --project_id="$PROJECT" "
SELECT id, state_code
FROM \`chip50.public.demographics_protected\`
LIMIT 1
" 2>&1 | grep -i "error" || echo "WARNING: Privacy check did not fail as expected!"
echo ""

# Test 6: Sample crosstab
echo "Test 6: Sample Crosstab - Trust in Congress by Party"
echo "-----------------------------------------------------"
bq query --use_legacy_sql=false --format=pretty \
  --project_id="$PROJECT" "
SELECT
  d.party_7,
  COUNT(*) AS n_respondents,
  ROUND(AVG(s.trust_congress), 2) AS avg_trust_congress,
  ROUND(AVG(s.approval_pres), 2) AS avg_approval_pres
FROM \`chip50.public.demographics_protected\` d
JOIN \`chip50.public.survey_responses_protected\` s
  ON d.row_hash = s.row_hash AND d.wave = s.wave
WHERE d.party_7 IS NOT NULL
GROUP BY d.party_7
ORDER BY d.party_7
LIMIT 7
"
echo ""

echo "========================================="
echo "All Tests Complete!"
echo "========================================="
echo ""
echo "✅ If you see results above (and Test 5 failed correctly),"
echo "   then the protected views are working as expected."
echo ""
echo "Next steps:"
echo "  - Review the buildplan.md for Phase 3 (Authentication)"
echo "  - Set up API key management with Firestore"
echo "  - Build the MCP server with cell suppression"
echo ""
