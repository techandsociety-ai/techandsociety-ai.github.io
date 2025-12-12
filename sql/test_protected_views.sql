-- Test queries for protected views
-- Run these after creating the protected views to validate they work correctly

-- ============================================================================
-- Test 1: Verify demographics_protected structure
-- ============================================================================
SELECT
  'Demographics Protected View - Sample' AS test_name,
  COUNT(*) AS total_rows,
  COUNT(DISTINCT row_hash) AS unique_row_hashes,
  COUNT(DISTINCT wave) AS num_waves,
  COUNT(DISTINCT region) AS num_regions
FROM `chip50.public.demographics_protected`;

-- Sample rows
SELECT *
FROM `chip50.public.demographics_protected`
LIMIT 5;

-- ============================================================================
-- Test 2: Verify survey_responses_protected structure
-- ============================================================================
SELECT
  'Survey Responses Protected View - Sample' AS test_name,
  COUNT(*) AS total_rows,
  COUNT(DISTINCT row_hash) AS unique_row_hashes,
  COUNT(DISTINCT wave) AS num_waves
FROM `chip50.public.survey_responses_protected`;

-- Sample rows
SELECT *
FROM `chip50.public.survey_responses_protected`
LIMIT 5;

-- ============================================================================
-- Test 3: Verify JOIN capability using row_hash
-- ============================================================================
SELECT
  'JOIN Test - Demographics + Survey' AS test_name,
  d.wave,
  d.region,
  d.party_7,
  d.age_cat_8,
  s.trust_congress,
  s.approval_pres,
  s.vote_intention,
  d.weight
FROM `chip50.public.demographics_protected` d
JOIN `chip50.public.survey_responses_protected` s
  ON d.row_hash = s.row_hash
  AND d.wave = s.wave
LIMIT 10;

-- ============================================================================
-- Test 4: Verify NO user_id or state_code exposure
-- ============================================================================
-- This query should FAIL (good!) since these columns shouldn't exist
-- Uncomment to test:
-- SELECT id, state_code FROM `chip50.public.demographics_protected` LIMIT 1;

-- ============================================================================
-- Test 5: Sample crosstab - Trust in Congress by Party
-- ============================================================================
SELECT
  d.party_7,
  COUNT(*) AS n_respondents,
  ROUND(AVG(s.trust_congress), 2) AS avg_trust_congress,
  ROUND(STDDEV(s.trust_congress), 2) AS sd_trust_congress
FROM `chip50.public.demographics_protected` d
JOIN `chip50.public.survey_responses_protected` s
  ON d.row_hash = s.row_hash
  AND d.wave = s.wave
WHERE d.party_7 IS NOT NULL
GROUP BY d.party_7
ORDER BY d.party_7;

-- ============================================================================
-- Test 6: Sample crosstab - Vote Intention by Region
-- ============================================================================
SELECT
  d.region,
  s.vote_intention,
  COUNT(*) AS n_respondents,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY d.region), 1) AS pct_within_region
FROM `chip50.public.demographics_protected` d
JOIN `chip50.public.survey_responses_protected` s
  ON d.row_hash = s.row_hash
  AND d.wave = s.wave
WHERE d.region IS NOT NULL AND s.vote_intention IS NOT NULL
GROUP BY d.region, s.vote_intention
ORDER BY d.region, n_respondents DESC;

-- ============================================================================
-- Test 7: Verify regions are aggregated correctly (no state codes)
-- ============================================================================
SELECT
  region,
  COUNT(DISTINCT row_hash) AS unique_respondents,
  COUNT(*) AS total_observations
FROM `chip50.public.demographics_protected`
GROUP BY region
ORDER BY region;
