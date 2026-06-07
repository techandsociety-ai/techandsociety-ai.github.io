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

  -- General posting frequency per platform (ordinal 1–7; -99 = skipped/refused; NULL = not asked this wave)
  -- Follow-up to sm_post_pol_*; asked of all users regardless of political posting
  CAST(sm_post_gen_4chan      AS INT64) as sm_post_gen_4chan,
  CAST(sm_post_gen_facebook   AS INT64) as sm_post_gen_facebook,
  CAST(sm_post_gen_gab        AS INT64) as sm_post_gen_gab,
  CAST(sm_post_gen_instagram  AS INT64) as sm_post_gen_instagram,
  CAST(sm_post_gen_linkedin   AS INT64) as sm_post_gen_linkedin,
  CAST(sm_post_gen_mastodon   AS INT64) as sm_post_gen_mastodon,
  CAST(sm_post_gen_messenger  AS INT64) as sm_post_gen_messenger,
  CAST(sm_post_gen_parler     AS INT64) as sm_post_gen_parler,
  CAST(sm_post_gen_pinterest  AS INT64) as sm_post_gen_pinterest,
  CAST(sm_post_gen_post       AS INT64) as sm_post_gen_post,
  CAST(sm_post_gen_reddit     AS INT64) as sm_post_gen_reddit,
  CAST(sm_post_gen_snapchat   AS INT64) as sm_post_gen_snapchat,
  CAST(sm_post_gen_tiktok     AS INT64) as sm_post_gen_tiktok,
  CAST(sm_post_gen_truth      AS INT64) as sm_post_gen_truth,
  CAST(sm_post_gen_tumblr     AS INT64) as sm_post_gen_tumblr,
  CAST(sm_post_gen_twitter    AS INT64) as sm_post_gen_twitter,
  CAST(sm_post_gen_whatsapp   AS INT64) as sm_post_gen_whatsapp,
  CAST(sm_post_gen_youtube    AS INT64) as sm_post_gen_youtube,
  CAST(sm_post_gen_bluesky    AS INT64) as sm_post_gen_bluesky,
  CAST(sm_post_gen_threads    AS INT64) as sm_post_gen_threads,
  CAST(sm_post_gen_bereal     AS INT64) as sm_post_gen_bereal,
  CAST(sm_post_gen_lemon8     AS INT64) as sm_post_gen_lemon8,
  CAST(sm_post_gen_rednote    AS INT64) as sm_post_gen_rednote,
  CAST(sm_post_gen_twitch     AS INT64) as sm_post_gen_twitch,

  -- COVID behavior (ordinal 1–4; -99 = skipped/refused; NULL = not asked this wave)
  CAST(cov_beh_1 AS INT64) as cov_beh_1,
  CAST(cov_beh_2 AS INT64) as cov_beh_2,
  CAST(cov_beh_3 AS INT64) as cov_beh_3,
  CAST(cov_beh_4 AS INT64) as cov_beh_4,
  CAST(cov_beh_5 AS INT64) as cov_beh_5,

  -- Democracy / 2024 election attitudes (NULL = not asked this wave)
  CAST(democ_1     AS INT64) as democ_1,      -- democratic norms scale 0–100; -99 = skipped/refused
  CAST(cand24      AS INT64) as cand24,        -- 2024 candidate preference (ordinal 1–6); -99 = skipped/refused
  CAST(vote24      AS INT64) as vote24,        -- 2024 vote (ordinal 1–4); -99 = skipped/refused

  -- Election news consumption (NULL = not asked this wave; -99 = skipped/refused)
  CAST(news_elect_1 AS INT64) as news_elect_1, -- ordinal 1–5
  CAST(news_elect_2 AS INT64) as news_elect_2, -- ordinal 1–5
  CAST(news_elect_3 AS INT64) as news_elect_3, -- ordinal 1–5
  CAST(source_elect AS INT64) as source_elect,  -- primary election news source (ordinal 1–10)
  CAST(media_elect  AS INT64) as media_elect,   -- election media type (ordinal 1–9)
  CAST(news_sat     AS INT64) as news_sat,      -- news satisfaction (ordinal 1–5)

  -- Ozempic / GLP-1 questions (wave 35+; ordinal; -99 = skipped/refused; NULL = not asked)
  CAST(ozempic        AS INT64)   as ozempic,       -- 1=currently taking, 2=previously took/stopped, 3=considering/interested, 4=not taking/no interest, 5=don't know/unsure
  CAST(ozempic_why    AS INT64)   as ozempic_why,   -- 1=weight loss, 4=diabetes, 5=other
  CAST(ozempic_time_1 AS INT64)   as ozempic_time_1,-- months currently using (0–10+)
  CAST(ozempic_time_2 AS INT64)   as ozempic_time_2,-- months since stopped (0–11+)
  CAST(ozempic_wt     AS FLOAT64) as ozempic_wt,    -- ozempic subsample weight (not an analysis variable)

  -- ── New SM platforms (wave 38+; NULL in earlier waves) ─────────────────────
  -- Platform usage (binary 0/1)
  CAST(use_discord   AS INT64) as use_discord,
  CAST(use_telegram  AS INT64) as use_telegram,
  CAST(use_twitch    AS INT64) as use_twitch,

  -- Platform usage frequency (ordinal 1–6; -99 = skipped/refused)
  CAST(freq_discord  AS INT64) as freq_discord,
  CAST(freq_telegram AS INT64) as freq_telegram,
  CAST(freq_twitch   AS INT64) as freq_twitch,

  -- General posting frequency (ordinal 1–7; -99 = skipped/refused)
  CAST(sm_post_gen_discord  AS INT64) as sm_post_gen_discord,
  CAST(sm_post_gen_telegram AS INT64) as sm_post_gen_telegram,

  -- Political posting frequency (ordinal 1–6; -99 = skipped/refused)
  CAST(sm_post_pol_discord  AS INT64) as sm_post_pol_discord,
  CAST(sm_post_pol_telegram AS INT64) as sm_post_pol_telegram,
  CAST(sm_post_pol_twitch   AS INT64) as sm_post_pol_twitch,

  -- Platform trust (ordinal 1–4; -99 = skipped/refused)
  CAST(sm_trust_discord   AS INT64) as sm_trust_discord,
  CAST(sm_trust_telegram  AS INT64) as sm_trust_telegram,
  CAST(sm_trust_twitch    AS INT64) as sm_trust_twitch,
  CAST(sm_trust_gab       AS INT64) as sm_trust_gab,
  CAST(sm_trust_pinterest AS INT64) as sm_trust_pinterest,

  -- Platform quit intention (wave 38+; ordinal 1=already quit, 2=considering, 3=not planning; -99 = refused)
  CAST(sm_quit_bluesky   AS INT64) as sm_quit_bluesky,
  CAST(sm_quit_discord   AS INT64) as sm_quit_discord,
  CAST(sm_quit_gab       AS INT64) as sm_quit_gab,
  CAST(sm_quit_facebook  AS INT64) as sm_quit_facebook,
  CAST(sm_quit_messenger AS INT64) as sm_quit_messenger,
  CAST(sm_quit_instagram AS INT64) as sm_quit_instagram,
  CAST(sm_quit_linkedin  AS INT64) as sm_quit_linkedin,
  CAST(sm_quit_mastodon  AS INT64) as sm_quit_mastodon,
  CAST(sm_quit_parler    AS INT64) as sm_quit_parler,
  CAST(sm_quit_pinterest AS INT64) as sm_quit_pinterest,
  CAST(sm_quit_post      AS INT64) as sm_quit_post,
  CAST(sm_quit_reddit    AS INT64) as sm_quit_reddit,
  CAST(sm_quit_tiktok    AS INT64) as sm_quit_tiktok,
  CAST(sm_quit_threads   AS INT64) as sm_quit_threads,
  CAST(sm_quit_truth     AS INT64) as sm_quit_truth,
  CAST(sm_quit_tumblr    AS INT64) as sm_quit_tumblr,
  CAST(sm_quit_telegram  AS INT64) as sm_quit_telegram,
  CAST(sm_quit_twitch    AS INT64) as sm_quit_twitch,
  CAST(sm_quit_twitter   AS INT64) as sm_quit_twitter,
  CAST(sm_quit_snapchat  AS INT64) as sm_quit_snapchat,
  CAST(sm_quit_youtube   AS INT64) as sm_quit_youtube,
  CAST(sm_quit_whatsapp  AS INT64) as sm_quit_whatsapp,
  CAST(sm_quit_4chan     AS INT64) as sm_quit_4chan,

  -- ── Extended institutional trust (wave 38+; ordinal 1–4; -99 = refused) ───
  CAST(pol_trust_city        AS INT64) as pol_trust_city,
  CAST(pol_trust_state       AS INT64) as pol_trust_state,
  CAST(pol_trust_congress    AS INT64) as pol_trust_congress,
  CAST(pol_trust_white_house AS INT64) as pol_trust_white_house,
  CAST(pol_trust_court       AS INT64) as pol_trust_court,
  CAST(pol_trust_election    AS INT64) as pol_trust_election,
  CAST(pol_trust_fbi         AS INT64) as pol_trust_fbi,
  CAST(pol_trust_fda         AS INT64) as pol_trust_fda,
  CAST(pol_trust_cdc         AS INT64) as pol_trust_cdc,
  CAST(pol_trust_biden       AS INT64) as pol_trust_biden,
  CAST(pol_trust_harris      AS INT64) as pol_trust_harris,
  CAST(pol_trust_doctors     AS INT64) as pol_trust_doctors,
  CAST(pol_trust_pharma      AS INT64) as pol_trust_pharma,
  CAST(pol_trust_education   AS INT64) as pol_trust_education,
  CAST(pol_trust_police      AS INT64) as pol_trust_police,
  CAST(pol_trust_military    AS INT64) as pol_trust_military,
  CAST(pol_trust_justice     AS INT64) as pol_trust_justice,
  CAST(pol_trust_religion    AS INT64) as pol_trust_religion,
  CAST(pol_trust_banks       AS INT64) as pol_trust_banks,
  CAST(pol_trust_media       AS INT64) as pol_trust_media,
  CAST(pol_trust_ai          AS INT64) as pol_trust_ai,

  -- ── Wave-38 political / electoral content ─────────────────────────────────
  -- Political interest and party strength (ordinal; -99 = refused)
  -- Note: raw `party` column excluded — contains text labels; use party3/party7 instead
  CAST(interest AS INT64) as interest,
  CAST(indep    AS INT64) as indep,
  CAST(dem_str  AS INT64) as dem_str,
  CAST(rep_str  AS INT64) as rep_str,

  -- 2024 election follow-up
  CAST(vote24_post    AS INT64) as vote24_post,
  CAST(vote24_certain AS INT64) as vote24_certain,
  CAST(support24      AS INT64) as support24,

  -- 2026 election outlook (ordinal; -99 = refused)
  CAST(vote_26    AS INT64) as vote_26,
  CAST(rep_26     AS INT64) as rep_26,
  CAST(sen_26     AS INT64) as sen_26,
  CAST(el_conf_26 AS INT64) as el_conf_26,

  -- Partisan attitudes (ordinal; -99 = refused)
  CAST(pol_par_1 AS INT64) as pol_par_1,
  CAST(pol_par_2 AS INT64) as pol_par_2,
  CAST(pol_par_3 AS INT64) as pol_par_3,
  CAST(pol_par_4 AS INT64) as pol_par_4,
  CAST(pol_par_5 AS INT64) as pol_par_5,
  CAST(pol_par_6 AS INT64) as pol_par_6,
  CAST(pol_par_7 AS INT64) as pol_par_7,

  -- Government approval (ordinal; -99 = refused)
  CAST(gov_gen   AS INT64) as gov_gen,
  CAST(mayor_gen AS INT64) as mayor_gen,

  -- Democracy evaluations (0–100 slider; -99 = refused)
  CAST(us_dem_1          AS INT64) as us_dem_1,
  CAST(state_dem_1       AS INT64) as state_dem_1,
  CAST(gerry_eval        AS INT64) as gerry_eval,
  CAST(gerry_amend       AS INT64) as gerry_amend,
  CAST(gerry_state_aware AS INT64) as gerry_state_aware,

  -- Policy attitudes (ordinal; -99 = refused)
  CAST(gas_affected  AS INT64) as gas_affected,
  CAST(support_cuba  AS INT64) as support_cuba,

  -- Feeling thermometers — domestic groups (0–100; -99 = refused)
  CAST(therm1_1  AS INT64) as therm1_1,
  CAST(therm1_2  AS INT64) as therm1_2,
  CAST(therm1_3  AS INT64) as therm1_3,
  CAST(therm1_4  AS INT64) as therm1_4,
  CAST(therm1_5  AS INT64) as therm1_5,
  CAST(therm1_6  AS INT64) as therm1_6,
  CAST(therm1_7  AS INT64) as therm1_7,
  CAST(therm1_11 AS INT64) as therm1_11,
  CAST(therm1_12 AS INT64) as therm1_12,
  CAST(therm1_13 AS INT64) as therm1_13,
  CAST(therm1_14 AS INT64) as therm1_14,
  CAST(therm1_15 AS INT64) as therm1_15,
  CAST(therm1_16 AS INT64) as therm1_16,

  -- Feeling thermometers — countries (0–100; -99 = refused)
  CAST(therm_country_1  AS INT64) as therm_country_1,
  CAST(therm_country_2  AS INT64) as therm_country_2,
  CAST(therm_country_3  AS INT64) as therm_country_3,
  CAST(therm_country_4  AS INT64) as therm_country_4,
  CAST(therm_country_11 AS INT64) as therm_country_11,
  CAST(therm_country_12 AS INT64) as therm_country_12,
  CAST(therm_country_15 AS INT64) as therm_country_15,

  -- Party comfort (ordinal 1–5; -99 = refused)
  CAST(comfort_party_1 AS INT64) as comfort_party_1,
  CAST(comfort_party_2 AS INT64) as comfort_party_2,
  CAST(comfort_party_3 AS INT64) as comfort_party_3,

  -- ── Wave-38 protest / social unrest content ────────────────────────────────
  -- Support for protest (ordinal; -99 = refused)
  CAST(prot_prior_1  AS INT64) as prot_prior_1,
  CAST(prot_prior_2  AS INT64) as prot_prior_2,
  CAST(prot_prior_3  AS INT64) as prot_prior_3,
  CAST(prot_prior_4  AS INT64) as prot_prior_4,
  CAST(prot_prior_5  AS INT64) as prot_prior_5,
  CAST(prot_prior_6  AS INT64) as prot_prior_6,
  CAST(prot_prior_7  AS INT64) as prot_prior_7,
  CAST(prot_prior_8  AS INT64) as prot_prior_8,
  CAST(prot_prior_9  AS INT64) as prot_prior_9,
  CAST(prot_prior_10 AS INT64) as prot_prior_10,
  CAST(prot_prior_11 AS INT64) as prot_prior_11,
  CAST(prot_prior_12 AS INT64) as prot_prior_12,
  CAST(prot_prior_13 AS INT64) as prot_prior_13,
  CAST(trump_protest AS INT64) as trump_protest,
  -- Anti-Trump protest causes / feelings (binary 0/1 check-all)
  CAST(prot_causes_1  AS INT64) as prot_causes_1,
  CAST(prot_causes_2  AS INT64) as prot_causes_2,
  CAST(prot_causes_3  AS INT64) as prot_causes_3,
  CAST(prot_causes_4  AS INT64) as prot_causes_4,
  CAST(prot_causes_5  AS INT64) as prot_causes_5,
  CAST(prot_causes_6  AS INT64) as prot_causes_6,
  CAST(prot_causes_7  AS INT64) as prot_causes_7,
  CAST(prot_causes_8  AS INT64) as prot_causes_8,
  CAST(prot_causes_9  AS INT64) as prot_causes_9,
  CAST(prot_causes_10 AS INT64) as prot_causes_10,
  CAST(prot_causes_11 AS INT64) as prot_causes_11,
  CAST(prot_causes_12 AS INT64) as prot_causes_12,
  CAST(prot_feel_1    AS INT64) as prot_feel_1,
  CAST(prot_feel_2    AS INT64) as prot_feel_2,
  CAST(prot_feel_3    AS INT64) as prot_feel_3,
  CAST(prot_feel_4    AS INT64) as prot_feel_4,
  CAST(prot_feel_5    AS INT64) as prot_feel_5,
  CAST(prot_feel_6    AS INT64) as prot_feel_6,
  CAST(prot_feel_7    AS INT64) as prot_feel_7,
  CAST(prot_feel_8    AS INT64) as prot_feel_8,
  CAST(prot_feel_9    AS INT64) as prot_feel_9,
  -- Protest encouragement / contagion (ordinal; -99 = refused)
  CAST(prot_enc_trump_1       AS INT64) as prot_enc_trump_1,
  CAST(prot_enc_trump_2       AS INT64) as prot_enc_trump_2,
  CAST(prot_enc_trump_3       AS INT64) as prot_enc_trump_3,
  CAST(prot_enc_trump_4       AS INT64) as prot_enc_trump_4,
  CAST(prot_enc_trump_5       AS INT64) as prot_enc_trump_5,
  CAST(prot_contagion_trump_1 AS INT64) as prot_contagion_trump_1,
  CAST(prot_contagion_trump_2 AS INT64) as prot_contagion_trump_2,
  CAST(prot_contagion_trump_3 AS INT64) as prot_contagion_trump_3,
  CAST(prot_contagion_trump_4 AS INT64) as prot_contagion_trump_4,
  CAST(prot_contagion_trump_5 AS INT64) as prot_contagion_trump_5,
  CAST(prot_contagion_trump_6 AS INT64) as prot_contagion_trump_6,
  CAST(prot_contagion_trump_7 AS INT64) as prot_contagion_trump_7,
  CAST(trump_prot_fut         AS INT64) as trump_prot_fut,
  CAST(trump_prot_symp        AS INT64) as trump_prot_symp,
  -- Reasons for not protesting (binary 0/1 check-all)
  CAST(trump_prot_notwhy_1  AS INT64) as trump_prot_notwhy_1,
  CAST(trump_prot_notwhy_2  AS INT64) as trump_prot_notwhy_2,
  CAST(trump_prot_notwhy_3  AS INT64) as trump_prot_notwhy_3,
  CAST(trump_prot_notwhy_4  AS INT64) as trump_prot_notwhy_4,
  CAST(trump_prot_notwhy_5  AS INT64) as trump_prot_notwhy_5,
  CAST(trump_prot_notwhy_6  AS INT64) as trump_prot_notwhy_6,
  CAST(trump_prot_notwhy_7  AS INT64) as trump_prot_notwhy_7,
  CAST(trump_prot_notwhy_8  AS INT64) as trump_prot_notwhy_8,
  CAST(trump_prot_notwhy_9  AS INT64) as trump_prot_notwhy_9,
  CAST(trump_prot_notwhy_10 AS INT64) as trump_prot_notwhy_10,
  CAST(trump_prot_notwhy_11 AS INT64) as trump_prot_notwhy_11,

  -- ── Wave-38 Iran foreign policy content ────────────────────────────────────
  CAST(iran_foll           AS INT64) as iran_foll,
  CAST(iran_decision       AS INT64) as iran_decision,
  CAST(iran_trump_app      AS INT64) as iran_trump_app,
  CAST(iran_threat_belief  AS INT64) as iran_threat_belief,
  CAST(iran_posture        AS INT64) as iran_posture,
  CAST(iran_action_outcome AS INT64) as iran_action_outcome,

  -- ── Wave-38 health / disability content ────────────────────────────────────
  -- Health attitudes (ordinal; -99 = refused)
  CAST(vac_gen_child AS INT64) as vac_gen_child,
  CAST(mmr_risk      AS INT64) as mmr_risk,
  -- Disability / functioning (ordinal; -99 = refused)
  CAST(dis_work    AS INT64) as dis_work,
  CAST(dis_wg_vis  AS INT64) as dis_wg_vis,
  CAST(dis_wg_hear AS INT64) as dis_wg_hear,
  CAST(dis_wg_mob  AS INT64) as dis_wg_mob,
  CAST(dis_wg_cog  AS INT64) as dis_wg_cog,
  CAST(dis_wg_sc   AS INT64) as dis_wg_sc,
  CAST(dis_wg_com  AS INT64) as dis_wg_com,
  -- Extended GLP-1/Ozempic module (subsample ~2500; -99 = refused)
  CAST(ozempic_dm      AS INT64) as ozempic_dm,
  CAST(ozempic_pay     AS INT64) as ozempic_pay,
  CAST(ozempic_stop_1  AS INT64) as ozempic_stop_1,   -- reasons for stopping (binary 0/1)
  CAST(ozempic_stop_2  AS INT64) as ozempic_stop_2,
  CAST(ozempic_stop_3  AS INT64) as ozempic_stop_3,
  CAST(ozempic_stop_4  AS INT64) as ozempic_stop_4,
  CAST(ozempic_stop_5  AS INT64) as ozempic_stop_5,
  CAST(ozempic_stop_6  AS INT64) as ozempic_stop_6,
  CAST(ozempic_stop_7  AS INT64) as ozempic_stop_7,
  CAST(ozempic_stop_8  AS INT64) as ozempic_stop_8,
  CAST(ozempic_stop_9  AS INT64) as ozempic_stop_9,
  CAST(ozempic_stop_10 AS INT64) as ozempic_stop_10,
  CAST(ozempic_stop_11 AS INT64) as ozempic_stop_11,
  CAST(ozempic_stop_12 AS INT64) as ozempic_stop_12,
  CAST(ozempic_stop_13 AS INT64) as ozempic_stop_13,
  CAST(ozempic_stop_14 AS INT64) as ozempic_stop_14,
  CAST(ozempic_stop_15 AS INT64) as ozempic_stop_15,
  CAST(ozempic_stop_16 AS INT64) as ozempic_stop_16,
  CAST(height_1        AS INT64) as height_1,          -- height feet (coded category)
  CAST(height_2        AS INT64) as height_2,          -- height inches (coded category)
  CAST(weight_current  AS INT64) as weight_current,    -- current weight (coded category)
  CAST(weight_pre_glp1 AS INT64) as weight_pre_glp1,   -- weight before GLP-1 (coded category)
  -- Healthcare coverage (ordinal / binary; -99 = refused)
  CAST(med_policy_approve_1 AS INT64) as med_policy_approve_1,
  CAST(med_policy_approve_2 AS INT64) as med_policy_approve_2,
  CAST(med_policy_approve_3 AS INT64) as med_policy_approve_3,
  CAST(insured              AS INT64) as insured,
  CAST(insured_lost         AS INT64) as insured_lost,
  CAST(insured_lost_why_1   AS INT64) as insured_lost_why_1,   -- reasons (binary 0/1)
  CAST(insured_lost_why_2   AS INT64) as insured_lost_why_2,
  CAST(insured_lost_why_3   AS INT64) as insured_lost_why_3,
  CAST(insured_lost_why_4   AS INT64) as insured_lost_why_4,
  CAST(insured_lost_why_5   AS INT64) as insured_lost_why_5,
  CAST(insured_lost_why_6   AS INT64) as insured_lost_why_6,
  CAST(insured_lost_why_7   AS INT64) as insured_lost_why_7,
  CAST(insured_lost_why_8   AS INT64) as insured_lost_why_8,
  CAST(insured_lost_why_9   AS INT64) as insured_lost_why_9,
  CAST(insured_lost_why_10  AS INT64) as insured_lost_why_10,
  CAST(insured_lost_why_11  AS INT64) as insured_lost_why_11,
  CAST(insured_lost_why_12  AS INT64) as insured_lost_why_12,
  CAST(insured_lost_why_13  AS INT64) as insured_lost_why_13,
  CAST(insured_lost_why_14  AS INT64) as insured_lost_why_14,
  CAST(insured_lost_why_15  AS INT64) as insured_lost_why_15,
  CAST(insured_lost_why_16  AS INT64) as insured_lost_why_16,
  CAST(insured_lost_why_17  AS INT64) as insured_lost_why_17,
  CAST(insured_lost_why_18  AS INT64) as insured_lost_why_18,
  CAST(insured_lost_why_19  AS INT64) as insured_lost_why_19,
  CAST(insurance_type_1     AS INT64) as insurance_type_1,     -- type (binary 0/1)
  CAST(insurance_type_2     AS INT64) as insurance_type_2,
  CAST(insurance_type_3     AS INT64) as insurance_type_3,
  CAST(insurance_type_4     AS INT64) as insurance_type_4,
  CAST(insurance_type_5     AS INT64) as insurance_type_5,
  CAST(insurance_type_6     AS INT64) as insurance_type_6,
  CAST(insurance_type_7     AS INT64) as insurance_type_7,
  CAST(insurance_type_8     AS INT64) as insurance_type_8,
  CAST(insured_gap          AS INT64) as insured_gap,
  CAST(med_ever_1           AS INT64) as med_ever_1,           -- Medicaid/Medicare ever (binary 0/1)
  CAST(med_ever_2           AS INT64) as med_ever_2,
  CAST(med_ever_3           AS INT64) as med_ever_3,
  CAST(medicaid_last        AS INT64) as medicaid_last,
  CAST(medicare_last        AS INT64) as medicare_last,

  -- ── Wave-38 mental health / social support extended ────────────────────────
  CAST(soc_sup_1 AS INT64) as soc_sup_1,
  CAST(soc_sup_2 AS INT64) as soc_sup_2,
  CAST(soc_sup_3 AS INT64) as soc_sup_3,
  CAST(soc_sup_4 AS INT64) as soc_sup_4,
  CAST(soc_sup_5 AS INT64) as soc_sup_5,
  CAST(phq9_13   AS INT64) as phq9_13,
  CAST(stress_1  AS INT64) as stress_1,
  CAST(lonely1   AS INT64) as lonely1,
  CAST(lonely2   AS INT64) as lonely2,
  CAST(lonely3   AS INT64) as lonely3,

  -- ── Wave-38 university / research funding content ──────────────────────────
  CAST(uni_funding_1           AS INT64) as uni_funding_1,
  CAST(uni_funding_2           AS INT64) as uni_funding_2,
  CAST(uni_funding_3           AS INT64) as uni_funding_3,
  CAST(uni_sources_1           AS INT64) as uni_sources_1,
  CAST(uni_sources_2           AS INT64) as uni_sources_2,
  CAST(uni_sources_3           AS INT64) as uni_sources_3,
  CAST(program_inv_1           AS INT64) as program_inv_1,
  CAST(program_inv_2           AS INT64) as program_inv_2,
  CAST(program_inv_3           AS INT64) as program_inv_3,
  CAST(program_inv_4           AS INT64) as program_inv_4,
  CAST(ec_benefit_1            AS INT64) as ec_benefit_1,
  CAST(ec_benefit_2            AS INT64) as ec_benefit_2,
  CAST(ec_benefit_3            AS INT64) as ec_benefit_3,
  CAST(non_economic_benefits_1 AS INT64) as non_economic_benefits_1,
  CAST(non_economic_benefits_2 AS INT64) as non_economic_benefits_2,
  CAST(non_economic_benefits_3 AS INT64) as non_economic_benefits_3,
  CAST(public_funds_1          AS INT64) as public_funds_1,
  CAST(public_funds_2          AS INT64) as public_funds_2,
  CAST(public_funds_3          AS INT64) as public_funds_3,
  CAST(public_funds_order_1    AS INT64) as public_funds_order_1,
  CAST(public_funds_order_2    AS INT64) as public_funds_order_2,
  CAST(public_funds_order_3    AS INT64) as public_funds_order_3,

  -- ── Wave-38 LLM / AI attitudes ─────────────────────────────────────────────
  CAST(llm_psych AS INT64) as llm_psych,
  CAST(llm_help  AS INT64) as llm_help

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
