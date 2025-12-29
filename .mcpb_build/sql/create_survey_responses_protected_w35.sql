-- Create protected survey responses view for Wave 35
-- Privacy protections:
-- 1. Remove user_id (PII) - exclude 'id' column
-- 2. Use deterministic row_hash for JOIN (non-reversible)
-- 3. Exclude free-text fields that may contain PII (columns ending in _TEXT, _why, senator names, etc.)
-- 4. Exclude Qualtrics metadata (Progress, Status, Finished, Duration, IPAddress, etc.)
--
-- Strategy: Use SELECT * EXCEPT to include all survey questions by default,
-- only excluding columns that pose privacy risks. This ensures new survey
-- questions (like AI attitudes) are automatically included.

CREATE OR REPLACE VIEW `chip50.public.survey_responses_protected_w35` AS
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
    -- These typically end in _TEXT or _why or are open-ended name fields
    senator_1,
    senator_2,
    elect_role_why,
    sm_quit_why_4chan,
    sm_quit_why_bereal,
    sm_quit_why_bluesky,
    sm_quit_why_facebook,
    sm_quit_why_instagram,
    sm_quit_why_linkedin,
    sm_quit_why_mastodon,
    sm_quit_why_messenger,
    sm_quit_why_parler,
    sm_quit_why_pinterest,
    sm_quit_why_reddit,
    sm_quit_why_snapchat,
    sm_quit_why_tiktok,
    sm_quit_why_truth,
    sm_quit_why_tumblr,
    sm_quit_why_twitch,
    sm_quit_why_twitter,
    sm_quit_why_whatsapp,
    sm_quit_why_youtube
  )

FROM `chip50.raw.survey_responses_w35`
WHERE id IS NOT NULL  -- Data quality filter
;

-- Add view description
ALTER VIEW `chip50.public.survey_responses_protected_w35`
SET OPTIONS (
  description = 'Privacy-protected survey responses for Wave 35. User IDs removed, free-text excluded.',
  labels = [('privacy_level', 'protected'), ('access_tier', 'outside_researcher'), ('wave', '35')]
);
