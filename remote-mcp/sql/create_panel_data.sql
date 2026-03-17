-- Create synthetic social media demographics PANEL dataset
-- Time series: Quarterly waves from Q4 2020 (Dec 2020) to Q1 2026 (Mar 2026)
-- Total: 22 quarters
-- Panel structure: 15,000 initial respondents with realistic attrition over time

-- First, create the dataset
CREATE SCHEMA IF NOT EXISTS `social_media_demographics`
OPTIONS(
  description="Synthetic social media demographics panel data for MCP server - Quarterly 2020-2026",
  labels=[("privacy", "synthetic"), ("access", "public"), ("type", "panel")]
);

-- Create wave/quarter reference table
CREATE OR REPLACE TABLE `social_media_demographics.waves` AS
SELECT
  wave_number,
  wave_date,
  EXTRACT(YEAR FROM wave_date) as year,
  EXTRACT(QUARTER FROM wave_date) as quarter,
  FORMAT_DATE('%Y-Q%Q', wave_date) as wave_label
FROM (
  SELECT
    ROW_NUMBER() OVER (ORDER BY wave_date) as wave_number,
    wave_date
  FROM UNNEST([
    DATE('2020-12-15'),  -- Q4 2020
    DATE('2021-03-15'),  -- Q1 2021
    DATE('2021-06-15'),  -- Q2 2021
    DATE('2021-09-15'),  -- Q3 2021
    DATE('2021-12-15'),  -- Q4 2021
    DATE('2022-03-15'),  -- Q1 2022
    DATE('2022-06-15'),  -- Q2 2022
    DATE('2022-09-15'),  -- Q3 2022
    DATE('2022-12-15'),  -- Q4 2022
    DATE('2023-03-15'),  -- Q1 2023
    DATE('2023-06-15'),  -- Q2 2023
    DATE('2023-09-15'),  -- Q3 2023
    DATE('2023-12-15'),  -- Q4 2023
    DATE('2024-03-15'),  -- Q1 2024
    DATE('2024-06-15'),  -- Q2 2024
    DATE('2024-09-15'),  -- Q3 2024
    DATE('2024-12-15'),  -- Q4 2024
    DATE('2025-03-15'),  -- Q1 2025
    DATE('2025-06-15'),  -- Q2 2025
    DATE('2025-09-15'),  -- Q3 2025
    DATE('2025-12-15'),  -- Q4 2025
    DATE('2026-03-15')   -- Q1 2026
  ]) as wave_date
);

-- Panel respondents table (demographics - mostly stable over time)
CREATE OR REPLACE TABLE `social_media_demographics.panel_respondents` AS
WITH base_respondents AS (
  SELECT
    GENERATE_UUID() as respondent_id,
    ROW_NUMBER() OVER () as panel_id
  FROM UNNEST(GENERATE_ARRAY(1, 15000))  -- 15k panel members
),
demographics AS (
  SELECT
    respondent_id,
    panel_id,
    FARM_FINGERPRINT(respondent_id) as row_hash,

    -- Age groups (starting age in 2020)
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'age'))), 100) < 15 THEN '18-24'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'age'))), 100) < 35 THEN '25-34'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'age'))), 100) < 55 THEN '35-44'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'age'))), 100) < 72 THEN '45-54'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'age'))), 100) < 87 THEN '55-64'
      ELSE '65+'
    END as age_group_2020,

    -- Gender (stable)
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'gender'))), 100) < 48 THEN 'Female'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'gender'))), 100) < 95 THEN 'Male'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'gender'))), 100) < 98 THEN 'Non-binary'
      ELSE 'Prefer not to say'
    END as gender,

    -- Race/Ethnicity (stable)
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'race'))), 100) < 60 THEN 'White'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'race'))), 100) < 73 THEN 'Black or African American'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'race'))), 100) < 91 THEN 'Hispanic or Latino'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'race'))), 100) < 97 THEN 'Asian'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'race'))), 100) < 99 THEN 'Two or more races'
      ELSE 'Other'
    END as race_ethnicity,

    -- Education (can change - starting level)
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'edu'))), 100) < 28 THEN 'High school or less'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'edu'))), 100) < 58 THEN 'Some college'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'edu'))), 100) < 83 THEN 'Bachelor''s degree'
      ELSE 'Graduate degree'
    END as education_2020,

    -- Income (can change - starting level)
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'income'))), 100) < 20 THEN 'Under $25,000'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'income'))), 100) < 38 THEN '$25,000-$49,999'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'income'))), 100) < 60 THEN '$50,000-$74,999'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'income'))), 100) < 78 THEN '$75,000-$99,999'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'income'))), 100) < 90 THEN '$100,000-$149,999'
      ELSE '$150,000 or more'
    END as income_2020,

    -- Political affiliation (can change)
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'party'))), 100) < 33 THEN 'Democrat'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'party'))), 100) < 63 THEN 'Republican'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'party'))), 100) < 93 THEN 'Independent'
      ELSE 'Other/No affiliation'
    END as political_affiliation_2020,

    -- Geographic region (mostly stable, some migration)
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'region'))), 100) < 18 THEN 'Northeast'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'region'))), 100) < 56 THEN 'South'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'region'))), 100) < 77 THEN 'Midwest'
      ELSE 'West'
    END as region_2020,

    -- Urbanicity (mostly stable)
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'urban'))), 100) < 32 THEN 'Urban'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'urban'))), 100) < 82 THEN 'Suburban'
      ELSE 'Rural'
    END as urbanicity,

    -- Attrition probability (some demographics more likely to drop out)
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'age'))), 100) < 15 THEN 0.08  -- 18-24: higher attrition
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(respondent_id, 'age'))), 100) < 35 THEN 0.05  -- 25-34
      ELSE 0.02  -- Older: lower attrition
    END as quarterly_attrition_rate

  FROM base_respondents
)
SELECT * FROM demographics;

-- Panel responses table (one row per respondent per wave they responded to)
CREATE OR REPLACE TABLE `social_media_demographics.panel_responses` AS
WITH wave_participation AS (
  SELECT
    r.respondent_id,
    r.panel_id,
    r.row_hash,
    w.wave_number,
    w.wave_date,
    w.wave_label,
    w.year,
    w.quarter,

    -- Determine if respondent participated in this wave (attrition model)
    CASE
      -- Always participate in wave 1
      WHEN w.wave_number = 1 THEN TRUE
      -- Cumulative attrition: higher probability of dropping out as waves progress
      WHEN RAND() > POW(1 - r.quarterly_attrition_rate, w.wave_number - 1) THEN FALSE
      ELSE TRUE
    END as participated,

    -- Demographics at this wave (some can change over time)
    r.gender,
    r.race_ethnicity,
    r.urbanicity,

    -- Age group evolves (simple aging model - group changes every ~10 years)
    CASE
      WHEN r.age_group_2020 = '18-24' AND w.wave_number >= 17 THEN '25-34'  -- After ~4 years
      WHEN r.age_group_2020 = '25-34' AND w.wave_number >= 17 THEN '35-44'
      WHEN r.age_group_2020 = '35-44' AND w.wave_number >= 17 THEN '45-54'
      WHEN r.age_group_2020 = '45-54' AND w.wave_number >= 17 THEN '55-64'
      WHEN r.age_group_2020 = '55-64' AND w.wave_number >= 17 THEN '65+'
      ELSE r.age_group_2020
    END as age_group,

    -- Education can improve (5% chance per year to move up one level)
    CASE
      WHEN r.education_2020 = 'High school or less' AND MOD(ABS(FARM_FINGERPRINT(CONCAT(r.respondent_id, 'edu_change', CAST(w.wave_number AS STRING)))), 100) < (w.wave_number * 1.25) THEN 'Some college'
      WHEN r.education_2020 = 'Some college' AND MOD(ABS(FARM_FINGERPRINT(CONCAT(r.respondent_id, 'edu_change', CAST(w.wave_number AS STRING)))), 100) < (w.wave_number * 1.25) THEN 'Bachelor''s degree'
      WHEN r.education_2020 = 'Bachelor''s degree' AND MOD(ABS(FARM_FINGERPRINT(CONCAT(r.respondent_id, 'edu_change', CAST(w.wave_number AS STRING)))), 100) < (w.wave_number * 1.0) THEN 'Graduate degree'
      ELSE r.education_2020
    END as education,

    -- Income changes over time (can go up or down)
    CASE
      -- Slight income growth trend over time, but with variation
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(r.respondent_id, 'income_change', CAST(w.wave_number AS STRING)))), 100) < 10 THEN
        CASE r.income_2020
          WHEN 'Under $25,000' THEN '$25,000-$49,999'
          WHEN '$25,000-$49,999' THEN '$50,000-$74,999'
          WHEN '$50,000-$74,999' THEN '$75,000-$99,999'
          WHEN '$75,000-$99,999' THEN '$100,000-$149,999'
          WHEN '$100,000-$149,999' THEN '$150,000 or more'
          ELSE r.income_2020
        END
      ELSE r.income_2020
    END as income,

    -- Political affiliation (can shift slightly)
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(r.respondent_id, 'party_change', CAST(w.wave_number AS STRING)))), 100) < 5 THEN
        CASE
          WHEN r.political_affiliation_2020 = 'Democrat' THEN 'Independent'
          WHEN r.political_affiliation_2020 = 'Republican' THEN 'Independent'
          WHEN r.political_affiliation_2020 = 'Independent' AND MOD(ABS(FARM_FINGERPRINT(CONCAT(r.respondent_id, 'party_dir'))), 2) = 0 THEN 'Democrat'
          WHEN r.political_affiliation_2020 = 'Independent' THEN 'Republican'
          ELSE r.political_affiliation_2020
        END
      ELSE r.political_affiliation_2020
    END as political_affiliation,

    -- Region (2% migration per year)
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(r.respondent_id, 'migration', CAST(w.wave_number AS STRING)))), 100) < 2 THEN
        CASE MOD(ABS(FARM_FINGERPRINT(CONCAT(r.respondent_id, 'new_region'))), 4)
          WHEN 0 THEN 'Northeast'
          WHEN 1 THEN 'South'
          WHEN 2 THEN 'Midwest'
          ELSE 'West'
        END
      ELSE r.region_2020
    END as region,

    -- Weight (varies slightly by wave for survey adjustments)
    1.0 + (MOD(ABS(FARM_FINGERPRINT(CONCAT(r.respondent_id, 'weight', CAST(w.wave_number AS STRING)))), 1000) - 500) / 1000.0 as weight

  FROM `social_media_demographics.panel_respondents` r
  CROSS JOIN `social_media_demographics.waves` w
)
SELECT * EXCEPT(participated)
FROM wave_participation
WHERE participated = TRUE;

-- Platform usage table with TIME-VARYING patterns
CREATE OR REPLACE TABLE `social_media_demographics.platform_usage_panel` AS
WITH responses AS (
  SELECT * FROM `social_media_demographics.panel_responses`
),
platform_usage AS (
  SELECT
    r.respondent_id,
    r.row_hash,
    r.wave_number,
    r.wave_date,
    r.wave_label,
    r.year,
    r.quarter,
    r.age_group,
    r.gender,
    r.education,

    -- Calculate time trend factors (0-1, where 0 = Dec 2020, 1 = Mar 2026)
    (r.wave_number - 1) / 21.0 as time_progress,

    -- TWITTER/X - Declining over time, especially after Musk acquisition (Q4 2022 = wave 9)
    CASE
      WHEN r.wave_number >= 9 THEN  -- Post-Musk era
        CASE
          WHEN r.age_group IN ('18-24', '25-34') AND r.education IN ('Bachelor''s degree', 'Graduate degree')
            THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'twitter', CAST(r.wave_number AS STRING)))), 100) < GREATEST(20, 55 - (r.wave_number - 9) * 3) THEN 'Daily'
                      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'twitter', CAST(r.wave_number AS STRING)))), 100) < GREATEST(35, 75 - (r.wave_number - 9) * 3) THEN 'Often'
                      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'twitter', CAST(r.wave_number AS STRING)))), 100) < 65 THEN 'Sometimes'
                      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'twitter', CAST(r.wave_number AS STRING)))), 100) < 80 THEN 'Rarely'
                      ELSE 'Never' END
          ELSE CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'twitter', CAST(r.wave_number AS STRING)))), 100) < GREATEST(10, 25 - (r.wave_number - 9) * 2) THEN 'Daily'
                    WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'twitter', CAST(r.wave_number AS STRING)))), 100) < 35 THEN 'Sometimes'
                    WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'twitter', CAST(r.wave_number AS STRING)))), 100) < 60 THEN 'Rarely'
                    ELSE 'Never' END
        END
      ELSE  -- Pre-Musk era
        CASE
          WHEN r.age_group IN ('18-24', '25-34') AND r.education IN ('Bachelor''s degree', 'Graduate degree')
            THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'twitter', CAST(r.wave_number AS STRING)))), 100) < 50 THEN 'Daily'
                      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'twitter', CAST(r.wave_number AS STRING)))), 100) < 75 THEN 'Often'
                      ELSE 'Sometimes' END
          ELSE CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'twitter', CAST(r.wave_number AS STRING)))), 100) < 20 THEN 'Daily'
                    WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'twitter', CAST(r.wave_number AS STRING)))), 100) < 45 THEN 'Sometimes'
                    ELSE 'Rarely' END
        END
    END as twitter_frequency,

    -- TIKTOK - Explosive growth from 2020-2023, then plateaus
    CASE
      WHEN r.age_group = '18-24'
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'tiktok', CAST(r.wave_number AS STRING)))), 100) < LEAST(40 + r.wave_number * 2, 75) THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'tiktok', CAST(r.wave_number AS STRING)))), 100) < LEAST(55 + r.wave_number * 2, 90) THEN 'Often'
                  ELSE 'Sometimes' END
      WHEN r.age_group = '25-34'
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'tiktok', CAST(r.wave_number AS STRING)))), 100) < LEAST(20 + r.wave_number * 2, 50) THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'tiktok', CAST(r.wave_number AS STRING)))), 100) < LEAST(40 + r.wave_number * 2, 70) THEN 'Often'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'tiktok', CAST(r.wave_number AS STRING)))), 100) < 85 THEN 'Sometimes'
                  ELSE 'Rarely' END
      ELSE CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'tiktok', CAST(r.wave_number AS STRING)))), 100) < LEAST(5 + r.wave_number, 25) THEN 'Daily'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'tiktok', CAST(r.wave_number AS STRING)))), 100) < LEAST(15 + r.wave_number, 40) THEN 'Sometimes'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'tiktok', CAST(r.wave_number AS STRING)))), 100) < 60 THEN 'Rarely'
                ELSE 'Never' END
    END as tiktok_frequency,

    -- FACEBOOK - Declining, especially among young
    CASE
      WHEN r.age_group IN ('45-54', '55-64', '65+')
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'facebook', CAST(r.wave_number AS STRING)))), 100) < GREATEST(50, 70 - r.wave_number) THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'facebook', CAST(r.wave_number AS STRING)))), 100) < 85 THEN 'Often'
                  ELSE 'Sometimes' END
      WHEN r.age_group IN ('18-24')
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'facebook', CAST(r.wave_number AS STRING)))), 100) < GREATEST(5, 30 - r.wave_number * 1.5) THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'facebook', CAST(r.wave_number AS STRING)))), 100) < 40 THEN 'Sometimes'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'facebook', CAST(r.wave_number AS STRING)))), 100) < 65 THEN 'Rarely'
                  ELSE 'Never' END
      ELSE CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'facebook', CAST(r.wave_number AS STRING)))), 100) < GREATEST(30, 50 - r.wave_number * 0.5) THEN 'Daily'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'facebook', CAST(r.wave_number AS STRING)))), 100) < 72 THEN 'Often'
                ELSE 'Sometimes' END
    END as facebook_frequency,

    -- INSTAGRAM - Steady with slight growth
    CASE
      WHEN r.age_group = '18-24'
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'instagram', CAST(r.wave_number AS STRING)))), 100) < 72 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'instagram', CAST(r.wave_number AS STRING)))), 100) < 90 THEN 'Often'
                  ELSE 'Sometimes' END
      WHEN r.age_group = '25-34'
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'instagram', CAST(r.wave_number AS STRING)))), 100) < 58 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'instagram', CAST(r.wave_number AS STRING)))), 100) < 82 THEN 'Often'
                  ELSE 'Sometimes' END
      ELSE CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'instagram', CAST(r.wave_number AS STRING)))), 100) < 25 THEN 'Daily'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'instagram', CAST(r.wave_number AS STRING)))), 100) < 50 THEN 'Often'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'instagram', CAST(r.wave_number AS STRING)))), 100) < 70 THEN 'Sometimes'
                ELSE 'Rarely' END
    END as instagram_frequency,

    -- LINKEDIN - Steady growth among professionals
    CASE
      WHEN r.education IN ('Bachelor''s degree', 'Graduate degree') AND r.age_group IN ('25-34', '35-44', '45-54')
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'linkedin', CAST(r.wave_number AS STRING)))), 100) < LEAST(30 + r.wave_number * 0.5, 45) THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'linkedin', CAST(r.wave_number AS STRING)))), 100) < 65 THEN 'Often'
                  ELSE 'Sometimes' END
      ELSE CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'linkedin', CAST(r.wave_number AS STRING)))), 100) < 15 THEN 'Sometimes'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'linkedin', CAST(r.wave_number AS STRING)))), 100) < 40 THEN 'Rarely'
                ELSE 'Never' END
    END as linkedin_frequency,

    -- YOUTUBE - Universally high and steady
    CASE
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'youtube', CAST(r.wave_number AS STRING)))), 100) < 70 THEN 'Daily'
      WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'youtube', CAST(r.wave_number AS STRING)))), 100) < 90 THEN 'Often'
      ELSE 'Sometimes'
    END as youtube_frequency,

    -- REDDIT - Slight growth among younger educated
    CASE
      WHEN r.age_group IN ('18-24', '25-34') AND r.gender = 'Male' AND r.education IN ('Bachelor''s degree', 'Graduate degree')
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'reddit', CAST(r.wave_number AS STRING)))), 100) < 45 THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'reddit', CAST(r.wave_number AS STRING)))), 100) < 72 THEN 'Often'
                  ELSE 'Sometimes' END
      ELSE CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'reddit', CAST(r.wave_number AS STRING)))), 100) < 20 THEN 'Sometimes'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'reddit', CAST(r.wave_number AS STRING)))), 100) < 50 THEN 'Rarely'
                ELSE 'Never' END
    END as reddit_frequency,

    -- SNAPCHAT - Declining among all but youngest
    CASE
      WHEN r.age_group = '18-24'
        THEN CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'snapchat', CAST(r.wave_number AS STRING)))), 100) < GREATEST(50, 70 - r.wave_number * 0.5) THEN 'Daily'
                  WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'snapchat', CAST(r.wave_number AS STRING)))), 100) < 82 THEN 'Often'
                  ELSE 'Sometimes' END
      ELSE CASE WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'snapchat', CAST(r.wave_number AS STRING)))), 100) < GREATEST(10, 25 - r.wave_number * 0.5) THEN 'Sometimes'
                WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(r.row_hash AS STRING), 'snapchat', CAST(r.wave_number AS STRING)))), 100) < 40 THEN 'Rarely'
                ELSE 'Never' END
    END as snapchat_frequency

  FROM responses r
)
SELECT * EXCEPT(time_progress) FROM platform_usage;

-- Create summary statistics table
CREATE OR REPLACE TABLE `social_media_demographics.panel_summary` AS
SELECT
  wave_number,
  wave_label,
  wave_date,
  COUNT(DISTINCT respondent_id) as respondents,
  COUNT(DISTINCT CASE WHEN wave_number = 1 THEN respondent_id END) OVER () as initial_panel_size,
  ROUND(COUNT(DISTINCT respondent_id) * 100.0 / COUNT(DISTINCT CASE WHEN wave_number = 1 THEN respondent_id END) OVER (), 1) as retention_rate
FROM `social_media_demographics.panel_responses`
GROUP BY wave_number, wave_label, wave_date
ORDER BY wave_number;

-- Display summary
SELECT * FROM `social_media_demographics.panel_summary`;
