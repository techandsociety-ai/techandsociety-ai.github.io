-- Create synthetic social media demographics dataset
-- This script generates realistic synthetic data matching the CHIP50 social media demographics dashboard

-- First, create the dataset
CREATE SCHEMA IF NOT EXISTS `social_media_demographics`
OPTIONS(
  description="Synthetic social media demographics data for MCP server",
  labels=[("privacy", "synthetic"), ("access", "public")]
);

-- Demographics table with 10,000 synthetic respondents
CREATE OR REPLACE TABLE `social_media_demographics.demographics` AS
WITH respondent_ids AS (
  SELECT
    GENERATE_UUID() as respondent_id,
    ROW_NUMBER() OVER () as row_num
  FROM UNNEST(GENERATE_ARRAY(1, 10000))
),
synthetic_demographics AS (
  SELECT
    respondent_id,
    FARM_FINGERPRINT(respondent_id) as row_hash,

    -- Age groups with realistic distribution
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'age'))), 100) < 15 THEN '18-24'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'age'))), 100) < 35 THEN '25-34'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'age'))), 100) < 55 THEN '35-44'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'age'))), 100) < 72 THEN '45-54'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'age'))), 100) < 87 THEN '55-64'
      ELSE '65+'
    END as age_group,

    -- Gender with diverse representation
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'gender'))), 100) < 48 THEN 'Female'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'gender'))), 100) < 95 THEN 'Male'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'gender'))), 100) < 98 THEN 'Non-binary'
      ELSE 'Prefer not to say'
    END as gender,

    -- Race/Ethnicity matching US demographics
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'race'))), 100) < 60 THEN 'White'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'race'))), 100) < 73 THEN 'Black or African American'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'race'))), 100) < 91 THEN 'Hispanic or Latino'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'race'))), 100) < 97 THEN 'Asian'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'race'))), 100) < 99 THEN 'Two or more races'
      ELSE 'Other'
    END as race_ethnicity,

    -- Education levels
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'edu'))), 100) < 28 THEN 'High school or less'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'edu'))), 100) < 58 THEN 'Some college'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'edu'))), 100) < 83 THEN 'Bachelor''s degree'
      ELSE 'Graduate degree'
    END as education,

    -- Income brackets
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'income'))), 100) < 20 THEN 'Under $25,000'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'income'))), 100) < 38 THEN '$25,000-$49,999'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'income'))), 100) < 60 THEN '$50,000-$74,999'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'income'))), 100) < 78 THEN '$75,000-$99,999'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'income'))), 100) < 90 THEN '$100,000-$149,999'
      ELSE '$150,000 or more'
    END as income,

    -- Political affiliation
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'party'))), 100) < 33 THEN 'Democrat'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'party'))), 100) < 63 THEN 'Republican'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'party'))), 100) < 93 THEN 'Independent'
      ELSE 'Other/No affiliation'
    END as political_affiliation,

    -- Geographic region
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'region'))), 100) < 18 THEN 'Northeast'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'region'))), 100) < 56 THEN 'South'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'region'))), 100) < 77 THEN 'Midwest'
      ELSE 'West'
    END as region,

    -- Urbanicity
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'urban'))), 100) < 32 THEN 'Urban'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'urban'))), 100) < 82 THEN 'Suburban'
      ELSE 'Rural'
    END as urbanicity,

    -- Weight for population adjustment (centered around 1.0)
    1.0 + (MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'weight'))), 1000) - 500) / 1000.0 as weight,

    -- Survey metadata
    CURRENT_DATE() as survey_date,
    'W1' as wave

  FROM respondent_ids
)
SELECT * FROM synthetic_demographics;

-- Platform usage table with realistic correlations to demographics
CREATE OR REPLACE TABLE `social_media_demographics.platform_usage` AS
WITH demographics AS (
  SELECT * FROM `social_media_demographics.demographics`
),
platform_data AS (
  SELECT
    row_hash,
    wave,

    -- Twitter/X usage (higher among younger, educated, political)
    CASE
      WHEN age_group IN ('18-24', '25-34') AND education IN ('Bachelor''s degree', 'Graduate degree')
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'twitter'))), 100) < 55 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'twitter'))), 100) < 75 THEN 'Often'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'twitter'))), 100) < 88 THEN 'Sometimes'
                  ELSE 'Rarely' END
      WHEN age_group IN ('18-24', '25-34')
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'twitter'))), 100) < 35 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'twitter'))), 100) < 60 THEN 'Often'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'twitter'))), 100) < 78 THEN 'Sometimes'
                  ELSE 'Rarely' END
      ELSE CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'twitter'))), 100) < 15 THEN 'Daily'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'twitter'))), 100) < 32 THEN 'Often'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'twitter'))), 100) < 55 THEN 'Sometimes'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'twitter'))), 100) < 75 THEN 'Rarely'
                ELSE 'Never' END
    END as twitter_frequency,

    -- Facebook usage (higher among older demographics)
    CASE
      WHEN age_group IN ('45-54', '55-64', '65+')
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'facebook'))), 100) < 65 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'facebook'))), 100) < 85 THEN 'Often'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'facebook'))), 100) < 93 THEN 'Sometimes'
                  ELSE 'Rarely' END
      WHEN age_group IN ('25-34', '35-44')
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'facebook'))), 100) < 45 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'facebook'))), 100) < 72 THEN 'Often'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'facebook'))), 100) < 88 THEN 'Sometimes'
                  ELSE 'Rarely' END
      ELSE CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'facebook'))), 100) < 25 THEN 'Daily'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'facebook'))), 100) < 45 THEN 'Often'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'facebook'))), 100) < 68 THEN 'Sometimes'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'facebook'))), 100) < 82 THEN 'Rarely'
                ELSE 'Never' END
    END as facebook_frequency,

    -- Instagram usage (strongly skewed young)
    CASE
      WHEN age_group = '18-24'
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'instagram'))), 100) < 72 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'instagram'))), 100) < 90 THEN 'Often'
                  ELSE 'Sometimes' END
      WHEN age_group = '25-34'
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'instagram'))), 100) < 58 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'instagram'))), 100) < 80 THEN 'Often'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'instagram'))), 100) < 92 THEN 'Sometimes'
                  ELSE 'Rarely' END
      WHEN age_group IN ('35-44', '45-54')
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'instagram'))), 100) < 30 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'instagram'))), 100) < 55 THEN 'Often'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'instagram'))), 100) < 75 THEN 'Sometimes'
                  ELSE 'Rarely' END
      ELSE CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'instagram'))), 100) < 15 THEN 'Daily'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'instagram'))), 100) < 30 THEN 'Often'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'instagram'))), 100) < 50 THEN 'Sometimes'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'instagram'))), 100) < 65 THEN 'Rarely'
                ELSE 'Never' END
    END as instagram_frequency,

    -- TikTok usage (extremely young-skewed)
    CASE
      WHEN age_group = '18-24'
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'tiktok'))), 100) < 68 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'tiktok'))), 100) < 85 THEN 'Often'
                  ELSE 'Sometimes' END
      WHEN age_group = '25-34'
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'tiktok'))), 100) < 42 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'tiktok'))), 100) < 68 THEN 'Often'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'tiktok'))), 100) < 83 THEN 'Sometimes'
                  ELSE 'Rarely' END
      WHEN age_group IN ('35-44', '45-54')
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'tiktok'))), 100) < 18 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'tiktok'))), 100) < 38 THEN 'Often'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'tiktok'))), 100) < 60 THEN 'Sometimes'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'tiktok'))), 100) < 75 THEN 'Rarely'
                  ELSE 'Never' END
      ELSE CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'tiktok'))), 100) < 8 THEN 'Daily'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'tiktok'))), 100) < 18 THEN 'Often'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'tiktok'))), 100) < 32 THEN 'Sometimes'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'tiktok'))), 100) < 48 THEN 'Rarely'
                ELSE 'Never' END
    END as tiktok_frequency,

    -- LinkedIn usage (professional, educated demographics)
    CASE
      WHEN education IN ('Bachelor''s degree', 'Graduate degree') AND age_group IN ('25-34', '35-44', '45-54')
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'linkedin'))), 100) < 35 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'linkedin'))), 100) < 60 THEN 'Often'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'linkedin'))), 100) < 82 THEN 'Sometimes'
                  ELSE 'Rarely' END
      WHEN education IN ('Bachelor''s degree', 'Graduate degree')
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'linkedin'))), 100) < 22 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'linkedin'))), 100) < 48 THEN 'Often'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'linkedin'))), 100) < 72 THEN 'Sometimes'
                  ELSE 'Rarely' END
      ELSE CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'linkedin'))), 100) < 8 THEN 'Daily'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'linkedin'))), 100) < 20 THEN 'Often'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'linkedin'))), 100) < 38 THEN 'Sometimes'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'linkedin'))), 100) < 55 THEN 'Rarely'
                ELSE 'Never' END
    END as linkedin_frequency,

    -- YouTube usage (nearly universal, slight age variation)
    CASE
      WHEN age_group IN ('18-24', '25-34', '35-44')
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'youtube'))), 100) < 75 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'youtube'))), 100) < 92 THEN 'Often'
                  ELSE 'Sometimes' END
      ELSE CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'youtube'))), 100) < 58 THEN 'Daily'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'youtube'))), 100) < 82 THEN 'Often'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'youtube'))), 100) < 93 THEN 'Sometimes'
                ELSE 'Rarely' END
    END as youtube_frequency,

    -- Reddit usage (young, male-skewed, educated)
    CASE
      WHEN age_group IN ('18-24', '25-34') AND gender = 'Male' AND education IN ('Bachelor''s degree', 'Graduate degree')
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'reddit'))), 100) < 48 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'reddit'))), 100) < 72 THEN 'Often'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'reddit'))), 100) < 88 THEN 'Sometimes'
                  ELSE 'Rarely' END
      WHEN age_group IN ('18-24', '25-34')
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'reddit'))), 100) < 28 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'reddit'))), 100) < 52 THEN 'Often'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'reddit'))), 100) < 72 THEN 'Sometimes'
                  ELSE 'Rarely' END
      ELSE CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'reddit'))), 100) < 12 THEN 'Daily'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'reddit'))), 100) < 28 THEN 'Often'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'reddit'))), 100) < 48 THEN 'Sometimes'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'reddit'))), 100) < 65 THEN 'Rarely'
                ELSE 'Never' END
    END as reddit_frequency,

    -- Snapchat usage (very young-skewed)
    CASE
      WHEN age_group = '18-24'
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'snapchat'))), 100) < 65 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'snapchat'))), 100) < 82 THEN 'Often'
                  ELSE 'Sometimes' END
      WHEN age_group = '25-34'
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'snapchat'))), 100) < 35 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'snapchat'))), 100) < 58 THEN 'Often'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'snapchat'))), 100) < 75 THEN 'Sometimes'
                  ELSE 'Rarely' END
      ELSE CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'snapchat'))), 100) < 8 THEN 'Daily'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'snapchat'))), 100) < 18 THEN 'Often'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'snapchat'))), 100) < 32 THEN 'Sometimes'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(row_hash AS STRING), 'snapchat'))), 100) < 48 THEN 'Rarely'
                ELSE 'Never' END
    END as snapchat_frequency

  FROM demographics
)
SELECT * FROM platform_data;

-- Create indexes for performance
CREATE OR REPLACE TABLE `social_media_demographics.demographics_indexed`
CLUSTER BY row_hash
AS SELECT * FROM `social_media_demographics.demographics`;

CREATE OR REPLACE TABLE `social_media_demographics.platform_usage_indexed`
CLUSTER BY row_hash
AS SELECT * FROM `social_media_demographics.platform_usage`;

-- Summary stats for validation
SELECT
  'Total Respondents' as metric,
  COUNT(*) as value
FROM `social_media_demographics.demographics`
UNION ALL
SELECT
  'Age Groups',
  COUNT(DISTINCT age_group)
FROM `social_media_demographics.demographics`
UNION ALL
SELECT
  'Platforms Tracked',
  8 -- Twitter, Facebook, Instagram, TikTok, LinkedIn, YouTube, Reddit, Snapchat
;
