-- CHIP50 Social Media Demographics Panel Data
-- Run AFTER `bq load` has loaded the raw CSV into panel_data
-- Creates a clustered table for query performance

-- Create clustered table for fast querying by wave and demographics
CREATE OR REPLACE TABLE `social_media_demographics.panel_data_indexed`
CLUSTER BY wave, age_cat_8, gender, party3
AS SELECT
  id,
  wave,
  state_code AS state,
  state_code,
  age_cat_8,
  education_cat,
  CAST(income_cat_10 AS INT64) as income_cat_10,
  race_cat_5,
  gender,
  party3,
  CAST(party7 AS INT64) as party7,
  urban_type,
  race,

  -- Race/ethnicity boolean flags (0/1; replaces race_cat_5)
  CAST(race_asian AS INT64) as race_asian,
  CAST(race_black AS INT64) as race_black,
  CAST(race_hisp  AS INT64) as race_hisp,
  CAST(race_natam AS INT64) as race_natam,
  CAST(race_white AS INT64) as race_white,
  CAST(race_other AS INT64) as race_other,

  -- Survey weight (from panel data)
  CAST(weight AS FLOAT64) AS weight,

  -- Attitudinal / behavioral demographics (ordinal; -99 = skipped/refused)
  CAST(ideology   AS INT64) as ideology,
  CAST(economy    AS INT64) as economy,
  CAST(voted20    AS INT64) as voted20,
  CAST(voted24    AS INT64) as voted24,
  CAST(trump_win  AS INT64) as trump_win,

  -- Conspiracy beliefs (ordinal 1–5; -99 = skipped/refused)
  CAST(conspiracy_1 AS INT64) as conspiracy_1,
  CAST(conspiracy_2 AS INT64) as conspiracy_2,
  CAST(conspiracy_3 AS INT64) as conspiracy_3,

  -- Political news sources (binary 0/1)
  CAST(pol_news2_2  AS INT64) as pol_news2_2,
  CAST(pol_news2_3  AS INT64) as pol_news2_3,
  CAST(pol_news2_4  AS INT64) as pol_news2_4,
  CAST(pol_news2_5  AS INT64) as pol_news2_5,
  CAST(pol_news2_6  AS INT64) as pol_news2_6,
  CAST(pol_news2_7  AS INT64) as pol_news2_7,
  CAST(pol_news2_8  AS INT64) as pol_news2_8,
  CAST(pol_news2_9  AS INT64) as pol_news2_9,
  CAST(pol_news2_10 AS INT64) as pol_news2_10,
  CAST(pol_news2_11 AS INT64) as pol_news2_11,
  CAST(pol_news2_12 AS INT64) as pol_news2_12,

  -- Institutional trust (ordinal 1–4; -99 = skipped/refused)
  CAST(pol_trust_science  AS INT64) as pol_trust_science,
  CAST(pol_trust_trump    AS INT64) as pol_trust_trump,
  CAST(pol_trust_twitter  AS INT64) as pol_trust_twitter,
  CAST(pol_trust_social   AS INT64) as pol_trust_social,
  CAST(pol_trust_google   AS INT64) as pol_trust_google,
  CAST(pol_trust_facebook AS INT64) as pol_trust_facebook,

  -- PHQ-9 depression screening items (SENSITIVE — ordinal 1–4; -99 = skipped/refused)
  -- Use higher suppression threshold (MIN_CELL_SIZE=30) for any queries on these columns
  CAST(phq9_1  AS INT64) as phq9_1,
  CAST(phq9_2  AS INT64) as phq9_2,
  CAST(phq9_3  AS INT64) as phq9_3,
  CAST(phq9_4  AS INT64) as phq9_4,
  CAST(phq9_5  AS INT64) as phq9_5,
  CAST(phq9_6  AS INT64) as phq9_6,
  CAST(phq9_7  AS INT64) as phq9_7,
  CAST(phq9_8  AS INT64) as phq9_8,
  CAST(phq9_9  AS INT64) as phq9_9,
  CAST(phq9_10 AS INT64) as phq9_10,
  CAST(phq9_11 AS INT64) as phq9_11,
  CAST(phq9_12 AS INT64) as phq9_12,

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
  -- Newer platforms (NULL in earlier waves)
  CAST(use_truth      AS INT64) as use_truth,
  CAST(use_mastodon   AS INT64) as use_mastodon,
  CAST(use_post       AS INT64) as use_post,
  CAST(use_threads    AS INT64) as use_threads,
  CAST(use_bluesky    AS INT64) as use_bluesky,

  -- Platform usage frequency (ordinal 1–6; -99 = skipped/refused; NULL = not asked this wave)
  CAST(freq_facebook   AS INT64) as freq_facebook,
  CAST(freq_instagram  AS INT64) as freq_instagram,
  CAST(freq_youtube    AS INT64) as freq_youtube,
  CAST(freq_twitter    AS INT64) as freq_twitter,
  CAST(freq_tiktok     AS INT64) as freq_tiktok,
  CAST(freq_snapchat   AS INT64) as freq_snapchat,
  CAST(freq_linkedin   AS INT64) as freq_linkedin,
  CAST(freq_reddit     AS INT64) as freq_reddit,
  CAST(freq_whatsapp   AS INT64) as freq_whatsapp,
  CAST(freq_messenger  AS INT64) as freq_messenger,
  CAST(freq_pinterest  AS INT64) as freq_pinterest,
  CAST(freq_tumblr     AS INT64) as freq_tumblr,
  CAST(freq_gab        AS INT64) as freq_gab,
  CAST(freq_parler     AS INT64) as freq_parler,
  CAST(freq_4chan      AS INT64) as freq_4chan,
  CAST(freq_truth      AS INT64) as freq_truth,
  CAST(freq_mastodon   AS INT64) as freq_mastodon,
  CAST(freq_post       AS INT64) as freq_post,
  CAST(freq_threads    AS INT64) as freq_threads,
  CAST(freq_bluesky    AS INT64) as freq_bluesky,

  -- Platform trust (ordinal 1–4; -99 = skipped/refused)
  CAST(sm_trust_youtube    AS INT64) as sm_trust_youtube,
  CAST(sm_trust_facebook   AS INT64) as sm_trust_facebook,
  CAST(sm_trust_twitter    AS INT64) as sm_trust_twitter,
  CAST(sm_trust_instagram  AS INT64) as sm_trust_instagram,
  CAST(sm_trust_reddit     AS INT64) as sm_trust_reddit,
  CAST(sm_trust_tiktok     AS INT64) as sm_trust_tiktok,
  CAST(sm_trust_whatsapp   AS INT64) as sm_trust_whatsapp,
  CAST(sm_trust_linkedin   AS INT64) as sm_trust_linkedin,
  CAST(sm_trust_truth      AS INT64) as sm_trust_truth,
  CAST(sm_trust_parler     AS INT64) as sm_trust_parler,
  CAST(sm_trust_mastodon   AS INT64) as sm_trust_mastodon,
  CAST(sm_trust_messenger  AS INT64) as sm_trust_messenger,
  CAST(sm_trust_post       AS INT64) as sm_trust_post,
  CAST(sm_trust_snapchat   AS INT64) as sm_trust_snapchat,
  CAST(sm_trust_4chan      AS INT64) as sm_trust_4chan,
  CAST(sm_trust_tumblr     AS INT64) as sm_trust_tumblr,
  CAST(sm_trust_threads    AS INT64) as sm_trust_threads,
  CAST(sm_trust_bluesky    AS INT64) as sm_trust_bluesky,

  -- Political posting frequency per platform (ordinal 1–6; -99 = skipped/refused)
  CAST(sm_post_pol_gab       AS INT64) as sm_post_pol_gab,
  CAST(sm_post_pol_facebook  AS INT64) as sm_post_pol_facebook,
  CAST(sm_post_pol_instagram AS INT64) as sm_post_pol_instagram,
  CAST(sm_post_pol_linkedin  AS INT64) as sm_post_pol_linkedin,
  CAST(sm_post_pol_pinterest AS INT64) as sm_post_pol_pinterest,
  CAST(sm_post_pol_reddit    AS INT64) as sm_post_pol_reddit,
  CAST(sm_post_pol_tumblr    AS INT64) as sm_post_pol_tumblr,
  CAST(sm_post_pol_tiktok    AS INT64) as sm_post_pol_tiktok,
  CAST(sm_post_pol_twitter   AS INT64) as sm_post_pol_twitter,
  CAST(sm_post_pol_youtube   AS INT64) as sm_post_pol_youtube,
  CAST(sm_post_pol_whatsapp  AS INT64) as sm_post_pol_whatsapp,
  CAST(sm_post_pol_4chan     AS INT64) as sm_post_pol_4chan,
  CAST(sm_post_pol_truth     AS INT64) as sm_post_pol_truth,
  CAST(sm_post_pol_parler    AS INT64) as sm_post_pol_parler,
  CAST(sm_post_pol_mastodon  AS INT64) as sm_post_pol_mastodon,
  CAST(sm_post_pol_messenger AS INT64) as sm_post_pol_messenger,
  CAST(sm_post_pol_post      AS INT64) as sm_post_pol_post,
  CAST(sm_post_pol_snapchat  AS INT64) as sm_post_pol_snapchat,
  CAST(sm_post_pol_threads   AS INT64) as sm_post_pol_threads,
  CAST(sm_post_pol_bluesky   AS INT64) as sm_post_pol_bluesky,

  -- Posting behavior — binary variants 1, 2, 3 per platform (0/1)
  CAST(sm_post_gab_1       AS INT64) as sm_post_gab_1,
  CAST(sm_post_gab_2       AS INT64) as sm_post_gab_2,
  CAST(sm_post_gab_3       AS INT64) as sm_post_gab_3,
  CAST(sm_post_facebook_1  AS INT64) as sm_post_facebook_1,
  CAST(sm_post_facebook_2  AS INT64) as sm_post_facebook_2,
  CAST(sm_post_facebook_3  AS INT64) as sm_post_facebook_3,
  CAST(sm_post_instagram_1 AS INT64) as sm_post_instagram_1,
  CAST(sm_post_instagram_2 AS INT64) as sm_post_instagram_2,
  CAST(sm_post_instagram_3 AS INT64) as sm_post_instagram_3,
  CAST(sm_post_linkedin_1  AS INT64) as sm_post_linkedin_1,
  CAST(sm_post_linkedin_2  AS INT64) as sm_post_linkedin_2,
  CAST(sm_post_linkedin_3  AS INT64) as sm_post_linkedin_3,
  CAST(sm_post_pinterest_1 AS INT64) as sm_post_pinterest_1,
  CAST(sm_post_pinterest_2 AS INT64) as sm_post_pinterest_2,
  CAST(sm_post_pinterest_3 AS INT64) as sm_post_pinterest_3,
  CAST(sm_post_reddit_1    AS INT64) as sm_post_reddit_1,
  CAST(sm_post_reddit_2    AS INT64) as sm_post_reddit_2,
  CAST(sm_post_reddit_3    AS INT64) as sm_post_reddit_3,
  CAST(sm_post_tumblr_1    AS INT64) as sm_post_tumblr_1,
  CAST(sm_post_tumblr_2    AS INT64) as sm_post_tumblr_2,
  CAST(sm_post_tumblr_3    AS INT64) as sm_post_tumblr_3,
  CAST(sm_post_tiktok_1    AS INT64) as sm_post_tiktok_1,
  CAST(sm_post_tiktok_2    AS INT64) as sm_post_tiktok_2,
  CAST(sm_post_tiktok_3    AS INT64) as sm_post_tiktok_3,
  CAST(sm_post_twitter_1   AS INT64) as sm_post_twitter_1,
  CAST(sm_post_twitter_2   AS INT64) as sm_post_twitter_2,
  CAST(sm_post_twitter_3   AS INT64) as sm_post_twitter_3,
  CAST(sm_post_youtube_1   AS INT64) as sm_post_youtube_1,
  CAST(sm_post_youtube_2   AS INT64) as sm_post_youtube_2,
  CAST(sm_post_youtube_3   AS INT64) as sm_post_youtube_3,
  CAST(sm_post_whatsapp_1  AS INT64) as sm_post_whatsapp_1,
  CAST(sm_post_whatsapp_2  AS INT64) as sm_post_whatsapp_2,
  CAST(sm_post_whatsapp_3  AS INT64) as sm_post_whatsapp_3,
  CAST(sm_post_4chan_1     AS INT64) as sm_post_4chan_1,
  CAST(sm_post_4chan_2     AS INT64) as sm_post_4chan_2,
  CAST(sm_post_4chan_3     AS INT64) as sm_post_4chan_3,
  CAST(sm_post_truth_1     AS INT64) as sm_post_truth_1,
  CAST(sm_post_truth_2     AS INT64) as sm_post_truth_2,
  CAST(sm_post_truth_3     AS INT64) as sm_post_truth_3,
  CAST(sm_post_parler_1    AS INT64) as sm_post_parler_1,
  CAST(sm_post_parler_2    AS INT64) as sm_post_parler_2,
  CAST(sm_post_parler_3    AS INT64) as sm_post_parler_3,
  CAST(sm_post_mastodon_1  AS INT64) as sm_post_mastodon_1,
  CAST(sm_post_mastodon_2  AS INT64) as sm_post_mastodon_2,
  CAST(sm_post_mastodon_3  AS INT64) as sm_post_mastodon_3,
  CAST(sm_post_messenger_1 AS INT64) as sm_post_messenger_1,
  CAST(sm_post_messenger_2 AS INT64) as sm_post_messenger_2,
  CAST(sm_post_messenger_3 AS INT64) as sm_post_messenger_3,
  CAST(sm_post_post_1      AS INT64) as sm_post_post_1,
  CAST(sm_post_post_2      AS INT64) as sm_post_post_2,
  CAST(sm_post_post_3      AS INT64) as sm_post_post_3,
  CAST(sm_post_snapchat_1  AS INT64) as sm_post_snapchat_1,
  CAST(sm_post_snapchat_2  AS INT64) as sm_post_snapchat_2,
  CAST(sm_post_snapchat_3  AS INT64) as sm_post_snapchat_3,

  -- Ozempic / GLP-1 questions (wave 35+; ordinal; -99 = skipped/refused; NULL = not asked)
  CAST(ozempic        AS INT64)   as ozempic,       -- 1=currently taking, 2=previously took/stopped, 3=considering/interested, 4=not taking/no interest, 5=don't know/unsure
  CAST(ozempic_why    AS INT64)   as ozempic_why,   -- 1=weight loss, 4=diabetes, 5=other
  CAST(ozempic_time_1 AS INT64)   as ozempic_time_1,-- months currently using (0–10+)
  CAST(ozempic_time_2 AS INT64)   as ozempic_time_2,-- months since stopped (0–11+)
  CAST(ozempic_wt     AS FLOAT64) as ozempic_wt     -- ozempic subsample weight (not an analysis variable)
FROM `social_media_demographics.panel_data`
-- Exclude national sub-sample waves (Size != 'full' per Wave to Dates.xlsx).
-- Waves 4, 6, 8 = small; 11, 12 = medium; 15 = small.
-- All analyses should use full-size waves only.
WHERE CAST(wave AS STRING) NOT IN ('4', '6', '8', '11', '12', '15');

-- Validation summary
SELECT
  COUNT(*)               AS total_rows,
  COUNT(DISTINCT id)     AS unique_respondents,
  COUNT(DISTINCT wave)   AS waves,
  MIN(CAST(wave AS FLOAT64)) AS first_wave,
  MAX(CAST(wave AS FLOAT64)) AS last_wave,
  ROUND(SUM(use_facebook * weight) / SUM(weight) * 100, 1)  AS facebook_use_pct,
  ROUND(SUM(use_twitter  * weight) / SUM(weight) * 100, 1)  AS twitter_use_pct,
  ROUND(SUM(use_youtube  * weight) / SUM(weight) * 100, 1)  AS youtube_use_pct,
  ROUND(SUM(use_tiktok   * weight) / SUM(weight) * 100, 1)  AS tiktok_use_pct,
  ROUND(AVG(CASE WHEN freq_facebook > 0 THEN freq_facebook END), 2) AS avg_freq_facebook,
  ROUND(AVG(CASE WHEN sm_trust_twitter > 0 THEN sm_trust_twitter END), 2) AS avg_trust_twitter,
  ROUND(AVG(CASE WHEN ideology > 0 THEN ideology END), 2)   AS avg_ideology
FROM `social_media_demographics.panel_data_indexed`;
