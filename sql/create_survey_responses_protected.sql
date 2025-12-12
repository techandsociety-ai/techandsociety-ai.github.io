-- Create protected survey responses view for chip50.public dataset
-- Privacy protections:
-- 1. Remove user_id (PII)
-- 2. Use deterministic row_hash for JOIN (non-reversible)
-- 3. Exclude any free-text fields (not present in synthetic data, but good practice)

CREATE OR REPLACE VIEW `chip50.public.survey_responses_protected` AS
SELECT
  -- Matching row identifier for JOIN with demographics_protected
  FARM_FINGERPRINT(CONCAT(CAST(id AS STRING), '-', CAST(wave AS STRING))) AS row_hash,

  wave,

  -- Trust in institutions (1-5 scale)
  trust_congress,
  trust_courts,
  trust_media,
  trust_military,

  -- Political figure approval (1-7 scale)
  approval_pres,
  approval_governor,
  approval_senator,

  -- Issue importance (0-10 scale)
  issue_economy,
  issue_healthcare,

  -- Categorical responses
  vote_intention,

  -- Binary response
  registered_voter,

  -- Continuous variable (thermometer rating 0-100)
  party_thermometer

  -- NOTE: Explicitly exclude any free-text comment fields
  -- (None present in synthetic data, but important for production)

FROM `chip50.raw.survey_responses`
WHERE id IS NOT NULL  -- Data quality filter
;

-- Add view description
ALTER VIEW `chip50.public.survey_responses_protected`
SET OPTIONS (
  description = 'Privacy-protected survey responses. User IDs removed, free-text excluded. Use row_hash to join with demographics_protected.',
  labels = [('privacy_level', 'protected'), ('access_tier', 'outside_researcher')]
);
