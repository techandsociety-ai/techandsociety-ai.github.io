-- Create protected demographics view for Wave 35
-- Privacy protections:
-- 1. Remove user_id (PII)
-- 2. Aggregate state -> region (reduce geographic precision)
-- 3. Use deterministic row_hash for JOIN (non-reversible)
-- 4. Remove exact geographic identifiers (zip, county, fips)

CREATE OR REPLACE VIEW `chip50.public.demographics_protected_w35` AS
SELECT
  -- Row identifier for JOIN (replaces user_id, non-reversible)
  FARM_FINGERPRINT(CONCAT(CAST(id AS STRING), '-', CAST(wave AS STRING))) AS row_hash,

  wave,

  -- Geographic aggregation: state_code -> region (privacy protection)
  CASE
    -- Northeast
    WHEN state_code IN ('ME', 'NH', 'VT', 'MA', 'RI', 'CT') THEN 'Northeast'
    -- Mid-Atlantic
    WHEN state_code IN ('NY', 'NJ', 'PA') THEN 'Mid-Atlantic'
    -- Midwest
    WHEN state_code IN ('OH', 'IN', 'IL', 'MI', 'WI', 'MN', 'IA', 'MO', 'ND', 'SD', 'NE', 'KS') THEN 'Midwest'
    -- South
    WHEN state_code IN ('DE', 'MD', 'VA', 'WV', 'NC', 'SC', 'GA', 'FL', 'KY', 'TN', 'AL', 'MS', 'AR', 'LA', 'OK', 'TX') THEN 'South'
    -- West
    WHEN state_code IN ('MT', 'ID', 'WY', 'CO', 'NM', 'AZ', 'UT', 'NV', 'WA', 'OR', 'CA', 'AK', 'HI') THEN 'West'
    ELSE 'Unknown'
  END AS region,

  -- Age categories (keep all variants for flexibility)
  age_cat_4,
  age_cat_6,
  age_cat_8,

  -- Gender variables
  gender,
  gender_full,
  female,
  male,

  -- Race/ethnicity variables
  race_asian,
  race_black,
  race_natam,
  race_pac,
  race_white,
  race_other,
  race_hisp,
  race_cat_4,

  -- Education
  education,
  education_cat,

  -- Income categories
  income_cat_10,
  income_cat_5,
  income_cat_4,

  -- Family structure
  relation,
  kids_n,
  parent,

  -- Party identification
  party7,
  party3,
  democrat,
  republican,
  independent,

  -- Urbanicity
  urbanicity,
  urban_type,

  -- Time variables
  year,
  month,

  -- Survey weights (for weighted analysis)
  weight,
  weight_state,
  weight_vote,
  weight_vote_state

FROM `chip50.raw.demographics_w35`
WHERE id IS NOT NULL  -- Data quality filter
;

-- Add view description
ALTER VIEW `chip50.public.demographics_protected_w35`
SET OPTIONS (
  description = 'Privacy-protected demographic data for Wave 35. User IDs removed, geography aggregated to regions.',
  labels = [('privacy_level', 'protected'), ('access_tier', 'outside_researcher'), ('wave', '35')]
);
