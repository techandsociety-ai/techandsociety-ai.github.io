-- Create protected demographics view for chip50.public dataset
-- Privacy protections:
-- 1. Remove user_id (PII)
-- 2. Aggregate state -> region (reduce geographic precision)
-- 3. Use deterministic row_hash for JOIN (non-reversible)

CREATE OR REPLACE VIEW `chip50.public.demographics_protected` AS
SELECT
  -- Row identifier for JOIN (replaces user_id, non-reversible)
  FARM_FINGERPRINT(CONCAT(CAST(id AS STRING), '-', CAST(wave AS STRING))) AS row_hash,

  wave,

  -- Geographic aggregation: state -> region
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

  -- Safe demographic variables (categorical, non-identifying)
  age_cat_8,
  education_cat,
  income_cat_10,
  gender,
  party_7,
  race,
  urban_type,

  -- Survey weight (for weighted analysis)
  weight

FROM `chip50.raw.demographics`
WHERE id IS NOT NULL  -- Data quality filter
;

-- Add view description
ALTER VIEW `chip50.public.demographics_protected`
SET OPTIONS (
  description = 'Privacy-protected demographic data. User IDs removed, geography aggregated to regions. Safe for public analysis.',
  labels = [('privacy_level', 'protected'), ('access_tier', 'outside_researcher')]
);
