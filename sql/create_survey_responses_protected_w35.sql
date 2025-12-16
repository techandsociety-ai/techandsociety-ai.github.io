-- Create protected survey responses view for Wave 35
-- Privacy protections:
-- 1. Remove user_id (PII)
-- 2. Use deterministic row_hash for JOIN (non-reversible)
-- 3. Exclude any free-text fields (TEXT columns)
-- 4. Exclude Qualtrics metadata (DO_, FL_, Q_, timer_ columns)

CREATE OR REPLACE VIEW `chip50.public.survey_responses_protected_w35` AS
SELECT
  -- Matching row identifier for JOIN with demographics_protected_w35
  FARM_FINGERPRINT(CONCAT(CAST(id AS STRING), '-', CAST(wave AS STRING))) AS row_hash,

  wave,

  -- Trust in institutions
  pol_trust_city,
  pol_trust_state,
  pol_trust_congress,
  pol_trust_white_house,
  pol_trust_court,
  pol_trust_election,
  pol_trust_fbi,
  pol_trust_fda,
  pol_trust_cdc,
  pol_trust_trump,
  pol_trust_musk,
  pol_trust_rfk,
  pol_trust_doctors,
  pol_trust_pharma,
  pol_trust_science,
  pol_trust_education,
  pol_trust_police,
  pol_trust_military,
  pol_trust_justice,
  pol_trust_religion,
  pol_trust_banks,
  pol_trust_media,
  pol_trust_social,

  -- General trust
  trust,

  -- Voting and elections
  vote24_post,
  vote24_certain,
  voted24,
  support24,
  vote20_post,
  voted20,
  support20,

  -- Economy
  economy,

  -- Household composition
  house_0_6,
  house_6_12,
  house_13_17,
  house_18_59,
  house_60,

  -- Political interest and discussion
  pol_info,
  pol_disc,

  -- Political news sources
  pol_news1_1,
  pol_news1_2,
  pol_news1_3,
  pol_news1_4,
  pol_news1_5,
  pol_news1_6,
  pol_news1_7,
  pol_news1_8,
  pol_news1_9,
  pol_news2_1,
  pol_news2_2,
  pol_news2_3,
  pol_news2_4,
  pol_news2_5,
  pol_news2_6,
  pol_news2_7,
  pol_news2_8,

  -- Conspiracies
  conspiracy_1,
  conspiracy_2,
  conspiracy_3,
  conspiracy_4,

  -- Ideology
  ideology,

  -- Political participation
  pol_par_1,
  pol_par_2,
  pol_par_3,
  pol_par_4,
  pol_par_5,
  pol_par_6,
  pol_par_7,
  pol_par_9,

  -- Government evaluations
  trump_gen,
  gov_gen,
  rep_gen,
  sen_gen_1,
  sen_gen_2,
  mayor_gen,

  -- Violence attitudes
  violence_ever,
  violence_now,
  violence_gov_1,
  violence_gov_2,
  violence_gov_3,
  violence_gov_4,

  -- Thermometers (political figures)
  therm1_1,
  therm1_2,
  therm1_3,
  therm1_4,
  therm1_5,
  therm1_6,
  therm1_7,
  therm1_11,
  therm1_13,
  therm1_14,
  therm1_15,
  therm1_19,
  therm1_20,
  therm1_21,

  -- Thermometers (countries)
  therm_country_1,
  therm_country_2,
  therm_country_3,
  therm_country_4,
  therm_country_11,
  therm_country_12,
  therm_country_15,
  therm_country_16,
  therm_country_17,
  therm_country_18,
  therm_country_19,

  -- Thermometers (companies)
  therm_company_1,
  therm_company_2,
  therm_company_3,
  therm_company_4,
  therm_company_5,
  therm_company_6,

  -- Thermometers (candidates/voters)
  therm_cand_1,
  therm_cand_2,
  therm_voters_1,
  therm_voters_2,

  -- DOGE and Trump policies
  doge_heard,
  doge_approve,
  trump_policy_1_1,
  trump_policy_1_2,
  trump_policy_1_3,
  trump_policy_1_4,
  trump_policy_1_5,
  trump_policy_1_6,
  trump_policy_1_7,
  trump_policy_1_8,
  trump_policy_1_9,
  trump_policy_1_10,
  trump_policy_1_11,
  trump_policy_2_1,
  trump_policy_2_2,
  trump_policy_2_3,
  trump_policy_2_4,
  trump_policy_2_5,
  trump_policy_2_6,
  trump_policy_2_7,
  trump_policy_2_8,
  trump_policy_2_9,
  trump_policy_2_10,

  -- Science policy
  science_policy_1_1,
  science_policy_1_2,
  science_policy_1_3,
  science_policy_1_4,
  science_policy_2_1,
  science_policy_2_2,
  science_policy_2_3,
  science_policy_2_4,

  -- Stock market
  tariffs,
  stocks,
  stock_change,
  trump_market,

  -- Protests
  trump_protest,
  trump_prot_sm_1,
  trump_prot_sm_2,
  trump_prot_sm_3,
  trump_prot_sm_4,
  trump_prot_sm_5,
  trump_prot_fut,
  blm_protest,

  -- Campus issues
  columbia,
  columbia_agree,
  harvard,
  harvard_agree,
  columbia_stance_1,
  columbia_stance_2,

  -- Discussion and disagreement
  fam_disc,
  fam_disc_agree,
  fr_disc,
  fr_disc_agree,
  comfort_party_1,
  comfort_party_2,
  comfort_party_3,
  dif_views,

  -- Social support
  soc_sup_1,
  soc_sup_2,
  soc_sup_3,
  soc_sup_4,

  -- Investment
  invest_sci,
  invest_med,

  -- Social media use
  soc_med_use,
  soc_med_news,
  soc_med_com,
  soc_med_source_1,
  soc_med_source_2,
  soc_med_source_3,
  soc_med_source_4,
  soc_med_source_5,

  -- COVID-19
  covid,
  cov_test,
  test_recent,
  test_positive_1,
  test_positive_2,
  test_positive_3,
  test_positive_4,
  vaccine_get,
  vac_boost,

  -- Healthcare
  medicaid,
  medicare,
  med_on_1,
  med_on_2,
  med_on_3,
  vac_mmr,
  fluoride,
  ozempic,
  ozempic_why,
  ozempic_time_1,
  ozempic_time_2,
  ozempic_wt,

  -- Mental health (PHQ-9)
  phq9_1,
  phq9_2,
  phq9_3,
  phq9_4,
  phq9_5,
  phq9_6,
  phq9_7,
  phq9_8,
  phq9_9,
  phq9_10,
  phq9_11,
  phq9_12,
  phq9_13,

  -- Stress and loneliness
  stress_1,
  lonely1,
  lonely2,
  lonely3,

  -- BITE-5
  bite5_1,
  bite5_2,
  bite5_3,
  bite5_4,
  bite5_5,

  -- Mental health treatment
  therapy,
  antidepress,
  antidep_approve,

  -- General health
  gen_health,

  -- Sleep
  awake_hour,
  awake_minutes,
  asleep_hour,
  asleep_minutes,
  fall_asleep_hour,
  fall_asleep_minutes,
  restless,
  unrest

FROM `chip50.raw.survey_responses_w35`
WHERE id IS NOT NULL  -- Data quality filter
;

-- Add view description
ALTER VIEW `chip50.public.survey_responses_protected_w35`
SET OPTIONS (
  description = 'Privacy-protected survey responses for Wave 35. User IDs removed, free-text excluded.',
  labels = [('privacy_level', 'protected'), ('access_tier', 'outside_researcher'), ('wave', '35')]
);
