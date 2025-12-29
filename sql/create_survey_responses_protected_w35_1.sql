-- Create protected survey responses view for Wave 35.1
-- Privacy protections:
-- 1. Remove user_id (PII) - exclude 'id' column
-- 2. Use deterministic row_hash for JOIN (non-reversible)
-- 3. Exclude free-text fields that may contain PII (columns ending in _TEXT)
-- 4. Exclude Qualtrics metadata (Progress, Status, Finished, etc.)
--
-- Note: Wave 35.1 has different survey questions than Wave 35
--
-- Strategy: Use SELECT * EXCEPT to include all survey questions by default,
-- only excluding columns that pose privacy risks. This ensures new survey
-- questions are automatically included.

CREATE OR REPLACE VIEW `chip50.public.survey_responses_protected_w35_1` AS
SELECT
  -- Generate row_hash for JOIN (replaces id)
  FARM_FINGERPRINT(CONCAT(CAST(id AS STRING), '-', CAST(wave AS STRING))) AS row_hash,

  -- Include all survey response columns EXCEPT privacy-sensitive ones
  * EXCEPT (
    -- PII and identifiers
    id,

    -- Qualtrics metadata (platform-generated, not survey data)
    Progress,
    Status,
    Finished,

    -- Free-text fields that may contain identifying information
    -- University and school names (potentially identifying)
    grad_name,
    undergrad_name,
    val_uni_name,

    -- Open-ended text responses (may contain PII)
    grad_type_6_TEXT,
    undergrad_type_6_TEXT
  )

FROM `chip50.raw.survey_responses_w35_1`
WHERE id IS NOT NULL  -- Data quality filter
;

-- Add view description
ALTER VIEW `chip50.public.survey_responses_protected_w35_1`
SET OPTIONS (
  description = 'Privacy-protected survey responses for Wave 35.1. User IDs removed, free-text excluded.',
  labels = [('privacy_level', 'protected'), ('access_tier', 'outside_researcher'), ('wave', '35_1')]
);
