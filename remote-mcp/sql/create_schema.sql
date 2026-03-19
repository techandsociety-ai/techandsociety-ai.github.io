-- CHIP50 Social Media Demographics Panel Data
-- Run AFTER `bq load` has loaded the raw CSV into panel_data
-- Creates a clustered table for query performance

-- Create clustered table for fast querying by wave and demographics
CREATE OR REPLACE TABLE `social_media_demographics.panel_data_indexed`
CLUSTER BY wave, age_cat_8, gender, party3
AS SELECT
  id,
  wave,
  state,
  state_code,
  age_cat_8,
  education_cat,
  CAST(income_cat_10 AS INT64) as income_cat_10,
  race_cat_5,
  gender,
  party3,
  CAST(party7 AS INT64) as party7,
  urban_type,
  -- Platform usage (binary: 1 = uses platform, 0 = does not, NULL = not asked this wave)
  CAST(use_facebook   AS INT64) as use_facebook,
  CAST(use_instagram  AS INT64) as use_instagram,
  CAST(use_youtube    AS INT64) as use_youtube,
  CAST(use_twitter    AS INT64) as use_twitter,
  CAST(use_tiktok     AS INT64) as use_tiktok,
  CAST(use_snapchat   AS INT64) as use_snapchat,
  CAST(use_linkedin   AS INT64) as use_linkedin,
  CAST(use_reddit     AS INT64) as use_reddit,
  CAST(use_whatsapp   AS INT64) as use_whatsapp,
  CAST(use_messenger  AS INT64) as use_messenger,
  CAST(use_pinterest  AS INT64) as use_pinterest,
  CAST(use_tumblr     AS INT64) as use_tumblr,
  CAST(use_gab        AS INT64) as use_gab,
  CAST(use_parler     AS INT64) as use_parler,
  CAST(use_4chan      AS INT64) as use_4chan,
  -- Newer platforms (NULL in earlier waves — only asked from certain waves onward)
  CAST(use_truth      AS INT64) as use_truth,
  CAST(use_mastodon   AS INT64) as use_mastodon,
  CAST(use_post       AS INT64) as use_post,
  CAST(use_threads    AS INT64) as use_threads,
  CAST(use_bluesky    AS INT64) as use_bluesky
FROM `social_media_demographics.panel_data`;

-- Validation summary
SELECT
  COUNT(*)          AS total_rows,
  COUNT(DISTINCT id)    AS unique_respondents,
  COUNT(DISTINCT wave)  AS waves,
  MIN(CAST(wave AS FLOAT64)) AS first_wave,
  MAX(CAST(wave AS FLOAT64)) AS last_wave,
  ROUND(AVG(use_facebook) * 100, 1)  AS facebook_use_pct,
  ROUND(AVG(use_twitter)  * 100, 1)  AS twitter_use_pct,
  ROUND(AVG(use_youtube)  * 100, 1)  AS youtube_use_pct,
  ROUND(AVG(use_tiktok)   * 100, 1)  AS tiktok_use_pct
FROM `social_media_demographics.panel_data_indexed`;
