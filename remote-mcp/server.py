#!/usr/bin/env python3
"""
Remote MCP Server for CHIP50 Social Media Demographics Analysis
Deployed on Google Cloud Run with Streamable HTTP transport

Data: CHIP50 panel survey data across multiple waves
Platform usage is binary (1=uses platform, 0=does not, NULL=not asked that wave)
"""

import os
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm
from google.cloud import bigquery

from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
GCP_PROJECT  = os.getenv("GCP_PROJECT", "chip50")
DATASET_NAME = os.getenv("DATASET_NAME", "social_media_demographics")
TABLE_NAME   = os.getenv("TABLE_NAME", "panel_data_indexed")
MIN_CELL_SIZE = int(os.getenv("MIN_CELL_SIZE", "30"))

FULL_TABLE       = f"`{GCP_PROJECT}.{DATASET_NAME}.{TABLE_NAME}`"
WAVE_DATES_TABLE = f"`{GCP_PROJECT}.{DATASET_NAME}.wave_dates`"

# ── Schema constants (mirrors real CSV structure) ───────────────────────────

DEMOGRAPHIC_COLUMNS = [
    "age_cat_8",
    "education_cat",
    "income_cat_10",
    "race_cat_5",
    "gender",
    "party3",
    "party7",
    "urban_type",
    "state",
    "state_code",
]

PLATFORM_COLUMNS = [
    "use_facebook",
    "use_instagram",
    "use_youtube",
    "use_twitter",
    "use_tiktok",
    "use_snapchat",
    "use_linkedin",
    "use_reddit",
    "use_whatsapp",
    "use_messenger",
    "use_pinterest",
    "use_tumblr",
    "use_gab",
    "use_parler",
    "use_4chan",
    # Available from later waves only
    "use_truth",
    "use_mastodon",
    "use_post",
    "use_threads",
    "use_bluesky",
]

# Platforms added mid-panel (have NULLs in earlier waves)
LATE_PLATFORMS = {"use_truth", "use_mastodon", "use_post", "use_threads", "use_bluesky"}

# Attitudinal / behavioral demographics (ordinal; -99 = skipped/refused)
ATTITUDINAL_COLUMNS = [
    "ideology",
    "economy",
    "voted20",
    "voted24",
    "trump_win",
    "conspiracy_1",
    "conspiracy_2",
    "conspiracy_3",
]

# Platform usage frequency (ordinal 1–6; -99 = skipped/refused)
FREQ_COLUMNS = [
    "freq_facebook",
    "freq_instagram",
    "freq_youtube",
    "freq_twitter",
    "freq_tiktok",
    "freq_snapchat",
    "freq_linkedin",
    "freq_reddit",
    "freq_whatsapp",
    "freq_messenger",
    "freq_pinterest",
    "freq_tumblr",
    "freq_gab",
    "freq_parler",
    "freq_4chan",
    "freq_truth",
    "freq_mastodon",
    "freq_post",
    "freq_threads",
    "freq_bluesky",
]
LATE_FREQ_PLATFORMS = {"freq_truth", "freq_mastodon", "freq_post", "freq_threads", "freq_bluesky"}

# Platform trust scores (ordinal 1–4; -99 = skipped/refused)
TRUST_COLUMNS = [
    "sm_trust_youtube",
    "sm_trust_facebook",
    "sm_trust_twitter",
    "sm_trust_instagram",
    "sm_trust_reddit",
    "sm_trust_tiktok",
    "sm_trust_whatsapp",
    "sm_trust_linkedin",
    "sm_trust_truth",
    "sm_trust_parler",
    "sm_trust_mastodon",
    "sm_trust_messenger",
    "sm_trust_post",
    "sm_trust_snapchat",
    "sm_trust_4chan",
    "sm_trust_tumblr",
    "sm_trust_threads",
    "sm_trust_bluesky",
]

# Political posting frequency per platform (ordinal 1–6; -99 = skipped/refused)
POL_POST_COLUMNS = [
    "sm_post_pol_gab",
    "sm_post_pol_facebook",
    "sm_post_pol_instagram",
    "sm_post_pol_linkedin",
    "sm_post_pol_pinterest",
    "sm_post_pol_reddit",
    "sm_post_pol_tumblr",
    "sm_post_pol_tiktok",
    "sm_post_pol_twitter",
    "sm_post_pol_youtube",
    "sm_post_pol_whatsapp",
    "sm_post_pol_4chan",
    "sm_post_pol_truth",
    "sm_post_pol_parler",
    "sm_post_pol_mastodon",
    "sm_post_pol_messenger",
    "sm_post_pol_post",
    "sm_post_pol_snapchat",
    "sm_post_pol_threads",
    "sm_post_pol_bluesky",
]

# Posting behavior — binary variants 1, 2, 3 per platform (0/1)
_SM_POST_PLATFORMS = [
    "gab", "facebook", "instagram", "linkedin", "pinterest", "reddit",
    "tumblr", "tiktok", "twitter", "youtube", "whatsapp", "4chan",
    "truth", "parler", "mastodon", "messenger", "post", "snapchat",
]
SM_POST_COLUMNS = [f"sm_post_{p}_{v}" for p in _SM_POST_PLATFORMS for v in [1, 2, 3]]

# Political news sources (binary 0/1)
POL_NEWS_COLUMNS = [
    "pol_news2_2", "pol_news2_3", "pol_news2_4", "pol_news2_5",
    "pol_news2_6", "pol_news2_7", "pol_news2_8", "pol_news2_9",
    "pol_news2_10", "pol_news2_11", "pol_news2_12",
]

# Institutional trust (ordinal 1–4; -99 = skipped/refused)
POL_TRUST_COLUMNS = [
    "pol_trust_science",
    "pol_trust_trump",
    "pol_trust_twitter",
    "pol_trust_social",
    "pol_trust_google",
    "pol_trust_facebook",
]

# PHQ-9 depression screening items — SENSITIVE
# Only population-level aggregates should be returned. Cell suppression
# uses MIN_CELL_SIZE (30) to protect respondent privacy.
PHQ9_COLUMNS = [
    "phq9_1", "phq9_2", "phq9_3", "phq9_4", "phq9_5", "phq9_6",
    "phq9_7", "phq9_8", "phq9_9", "phq9_10", "phq9_11", "phq9_12",
]

# All ordinal column groups (exclude -99 sentinel in queries with col > 0)
ALL_ORDINAL_COLUMNS = (
    ATTITUDINAL_COLUMNS + FREQ_COLUMNS + TRUST_COLUMNS +
    POL_POST_COLUMNS + POL_TRUST_COLUMNS + PHQ9_COLUMNS
)

# All binary columns beyond the core use_* set
ALL_BINARY_COLUMNS = SM_POST_COLUMNS + POL_NEWS_COLUMNS

# ── Regression column sets ───────────────────────────────────────────────────

# Ordinal columns that encode -99 for skipped/refused (must filter before modelling)
_SENTINEL_COLUMNS: set[str] = set(ALL_ORDINAL_COLUMNS)

# Demographic columns treated as unordered categories → dummy-encoded in models
_CATEGORICAL_COLUMNS: set[str] = set(DEMOGRAPHIC_COLUMNS)

# Universe of columns valid as outcome or predictor in regression tools
_ALL_REGRESSION_COLUMNS: set[str] = set(
    DEMOGRAPHIC_COLUMNS
    + PLATFORM_COLUMNS
    + ATTITUDINAL_COLUMNS
    + FREQ_COLUMNS
    + TRUST_COLUMNS
    + POL_POST_COLUMNS
    + POL_TRUST_COLUMNS
    + PHQ9_COLUMNS
    + SM_POST_COLUMNS
    + POL_NEWS_COLUMNS
)

# Binary-outcome columns (valid for logistic regression)
_BINARY_COLUMNS: set[str] = set(PLATFORM_COLUMNS + SM_POST_COLUMNS + POL_NEWS_COLUMNS)

# ── Key historical events for trend annotation ───────────────────────────────
# Injected into get_platform_trends / get_freq_trends responses.
# Claude must annotate trend charts with vertical dashed lines at these waves.

PLATFORM_KEY_EVENTS = {
    "use_twitter": [
        {
            "wave": 25,
            "approx_date": "2022-10-27",
            "event": "Elon Musk acquisition of Twitter/X",
            "chart_annotation": (
                "Draw a vertical dashed line at Wave 25 on ALL Twitter/X trend charts. "
                "This is a critical inflection point — never omit this annotation."
            ),
        }
    ],
    "twitter": [
        {
            "wave": 25,
            "approx_date": "2022-10-27",
            "event": "Elon Musk acquisition of Twitter/X",
            "chart_annotation": (
                "Draw a vertical dashed line at Wave 25 on ALL Twitter/X trend charts. "
                "This is a critical inflection point — never omit this annotation."
            ),
        }
    ],
}

# ── Column definitions ────────────────────────────────────────────────────────
# Included in every tool response so Claude always labels columns correctly.
# The most common user confusion: seeing unweighted_n next to a weighted %
# and assuming both are from the same weighting scheme.

COLUMN_DEFINITIONS = {
    "unweighted_n": (
        "Raw respondent count — the actual number of survey participants in this cell. "
        "Use ONLY to assess data reliability and cell suppression risk. "
        "Do NOT present as a population estimate or use to compute percentages."
    ),
    "weighted_n": (
        "Population-weighted count — adjusted for survey design weights to represent "
        "the U.S. adult population. Use for population-representative totals."
    ),
    "weighted_users": (
        "Population-weighted count of platform users (WEIGHTED — population-representative)."
    ),
    "weighted_non_users": (
        "Population-weighted count of non-users (WEIGHTED — population-representative)."
    ),
    "user_rate_pct": (
        "Platform adoption rate — WEIGHTED, population-representative percentage. "
        "Always label this as 'weighted %' or '% (weighted)' when presenting to users. "
        "Never present alongside unweighted_n without clearly distinguishing the two."
    ),
    "pct": (
        "Population-weighted percentage — WEIGHTED, population-representative. "
        "Always label as 'weighted %' when presenting to users."
    ),
    "weighted_mean": (
        "Population-weighted mean score — WEIGHTED, population-representative. "
        "Always label as 'weighted mean' when presenting to users."
    ),
    "weighted_mean_freq": (
        "Population-weighted mean usage frequency on the 1–6 ordinal scale "
        "(1=never, 2=rarely, 3=sometimes, 4=often, 5=daily, 6=almost constantly). "
        "WEIGHTED, population-representative."
    ),
    "weighted_mean_trust": (
        "Population-weighted mean trust score on the 1–4 ordinal scale "
        "(1=not at all, 2=not much, 3=somewhat, 4=a lot). "
        "WEIGHTED, population-representative."
    ),
}

FREQ_SCALE_LABELS = {
    1: "Never",
    2: "Rarely",
    3: "Sometimes",
    4: "Often",
    5: "Daily",
    6: "Almost constantly",
}

TRUST_SCALE_LABELS = {
    1: "Not at all",
    2: "Not much",
    3: "Somewhat",
    4: "A lot",
}

IDEOLOGY_SCALE_LABELS = {
    1: "Very liberal",
    2: "Liberal",
    3: "Somewhat liberal",
    4: "Moderate",
    5: "Somewhat conservative",
    6: "Conservative",
    7: "Very conservative",
}

# ── BigQuery client (lazy) ──────────────────────────────────────────────────

_bq_client: Optional[bigquery.Client] = None


def get_bq_client() -> bigquery.Client:
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(project=GCP_PROJECT)
        list(_bq_client.list_datasets(max_results=1))
        logger.info(f"Connected to BigQuery: {GCP_PROJECT}")
    return _bq_client


def run_query(sql: str) -> pd.DataFrame:
    return get_bq_client().query(sql).to_dataframe()


def wave_clause(wave: Optional[str]) -> str:
    """Build a WHERE clause fragment for wave filtering.

    Accepts integer or float wave values (e.g. '35' or '35.1').
    Uses FLOAT64 cast to handle both integer-stored and float-stored wave columns.
    """
    if not wave:
        return ""
    try:
        float(wave)  # validate numeric — prevents SQL injection
    except ValueError:
        raise ValueError(f"Invalid wave '{wave}': must be a number (e.g. '35' or '35.1').")
    return f"AND CAST(wave AS FLOAT64) = {float(wave)}"


# ── Auth (toggle with DISABLE_AUTH env var on Cloud Run) ─────────────────────

if os.getenv("DISABLE_AUTH"):
    auth = None
else:
    auth = GoogleProvider(
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        base_url=os.getenv("SERVICE_URL", "http://localhost:8080"),
        allowed_client_redirect_uris=["https://claude.ai/api/mcp/auth_callback"],
    )

# ── MCP server ──────────────────────────────────────────────────────────────

mcp = FastMCP("social-media-demographics", auth=auth)


@mcp.tool()
async def introduce_mcp() -> str:
    """Get a quick introduction to this MCP server, its tools, and how to use them.

    Call this first to understand what data is available and how to query it.
    """
    logo = (
        "            ////\n"
        "           ////\n"
        "     \\\\   ////\n"
        "      \\\\ ////\n"
        "       \\////\n"
        "        \\/\n"
        "    C H I P 5 0"
    )
    return json.dumps({
        "logo": logo,
        "name": "CHIP50 Social Media Demographics MCP",
        "description": (
            "This MCP server provides access to CHIP50 panel survey data covering social media "
            "usage, frequency, trust, and political behavior across all waves. "
            "You can analyze platform adoption rates, ordinal scales, and trends "
            "broken down by demographics, and run batch queries."
        ),
        "dataset": {
            "demographics": DEMOGRAPHIC_COLUMNS,
            "attitudinal": ATTITUDINAL_COLUMNS,
            "platforms": [c.replace("use_", "") for c in PLATFORM_COLUMNS],
            "freq_columns": FREQ_COLUMNS,
            "trust_columns": TRUST_COLUMNS,
            "pol_post_columns": POL_POST_COLUMNS,
            "pol_news_columns": POL_NEWS_COLUMNS,
            "pol_trust_columns": POL_TRUST_COLUMNS,
            "phq9_columns": PHQ9_COLUMNS,
            "notes": {
                "platform_usage": "Binary (1=uses, 0=does not). late_platforms (truth, mastodon, post, threads, bluesky) have NULLs in earlier waves.",
                "ordinal_sentinel": "All ordinal columns use -99 for skipped/refused — excluded automatically from all queries.",
                "suppression": f"Cells with n<{MIN_CELL_SIZE} are suppressed for respondent privacy.",
                "phq9_sensitivity": "PHQ-9 items are clinical mental health screening measures. Only population-level aggregates are returned.",
                "wave_coverage": "voted24 only from wave 34+; economy only waves 32/35+; sm_post_* variants only waves 27/28 and 33+.",
            },
            "problematic_waves": {
                "35.1": (
                    "Small sample wave. race_cat_5 (race/ethnicity) breakdowns are unavailable — "
                    "all cells fall below the minimum cell size threshold and are suppressed. "
                    "Use aggregate-level queries for this wave; demographic crosstabs by race may return no data."
                ),
            },
        },
        "tools": [
            {
                "name": "introduce_mcp",
                "purpose": "This tool — get an overview of the MCP and all available tools.",
                "example": "introduce_mcp()",
            },
            {
                "name": "get_available_variables",
                "purpose": "Discover all available column groups and wave range from live data.",
                "example": "get_available_variables()",
            },
            {
                "name": "generate_marginals",
                "purpose": "Distribution for a single variable. Works for demographics, platforms (binary rate), attitudinal, ordinal, and binary columns.",
                "example": 'generate_marginals(variable="age_cat_8")  # or "use_tiktok", "ideology", "freq_twitter"',
            },
            {
                "name": "generate_marginals_batch",
                "purpose": "Run generate_marginals for multiple variables in parallel.",
                "example": 'generate_marginals_batch(variables=["age_cat_8", "gender", "use_tiktok", "ideology"])',
            },
            {
                "name": "generate_crosstab",
                "purpose": "Platform adoption rate broken down by a demographic or attitudinal variable.",
                "example": 'generate_crosstab(platform="use_tiktok", demographic="ideology")',
            },
            {
                "name": "generate_crosstab_filtered",
                "purpose": "Platform adoption rate broken down by one demographic, filtered to a sub-population defined by one or more additional demographic constraints. Use this for intersection queries like 'Facebook usage by gender among rural respondents'.",
                "example": 'generate_crosstab_filtered(platform="use_facebook", demographic="gender", filters={"urban_type": "Rural"})',
            },
            {
                "name": "generate_crosstab_batch",
                "purpose": "Run generate_crosstab for one platform across multiple demographics in parallel.",
                "example": 'generate_crosstab_batch(platform="use_tiktok", demographics=["age_cat_8", "gender", "party3"])',
            },
            {
                "name": "get_platform_trends",
                "purpose": "Binary platform adoption rate across waves (time series). Optionally filter to a demographic group.",
                "example": 'get_platform_trends(platform="use_twitter", demographic="party3", demographic_value="Republican")',
            },
            {
                "name": "get_ordinal_distribution",
                "purpose": "Weighted % distribution for any ordinal variable (freq, trust, ideology, phq9, etc.).",
                "example": 'get_ordinal_distribution(column="sm_trust_twitter")',
            },
            {
                "name": "get_ordinal_crosstab",
                "purpose": "Weighted mean of an ordinal variable broken down by a demographic — e.g. mean Twitter trust by party.",
                "example": 'get_ordinal_crosstab(column="sm_trust_twitter", demographic="party3")',
            },
            {
                "name": "get_freq_trends",
                "purpose": "Mean platform usage frequency across waves (time series using ordinal freq scale).",
                "example": 'get_freq_trends(platform="twitter", demographic="party3", demographic_value="Republican")',
            },
            {
                "name": "get_platform_posting_summary",
                "purpose": "All key metrics for one platform in a single call: adoption, frequency, trust, political posting, posting variants.",
                "example": 'get_platform_posting_summary(platform="twitter")',
            },
            {
                "name": "run_ols_regression",
                "purpose": "OLS regression for a continuous/ordinal outcome. Survey-weighted by default (use_weights=True). Supports custom reference categories for categorical predictors via reference_categories. Returns coefficients, std errors, p-values, 95% CIs, R², F-stat, AIC/BIC.",
                "example": 'run_ols_regression(outcome="ideology", predictors=["use_twitter", "age_cat_8", "education_cat"], reference_categories={"party3": "Independent"})',
            },
            {
                "name": "run_logistic_regression",
                "purpose": "Logistic regression for a binary outcome (platform use, sm_post_*, pol_news_*). Survey-weighted by default (use_weights=True). Supports custom reference categories via reference_categories. Returns log-odds, odds ratios, p-values, 95% CIs, McFadden pseudo-R², AIC/BIC.",
                "example": 'run_logistic_regression(outcome="use_tiktok", predictors=["age_cat_8", "gender", "ideology", "party3"], reference_categories={"party3": "Democrat"}, use_weights=False)',
            },
        ],
        "quick_start": [
            "1. Call introduce_mcp() to get this overview.",
            "2. Call get_available_variables() to see live dataset metadata.",
            "3. Use generate_marginals() to explore a single variable.",
            "4. Use generate_crosstab() to cross a platform with a demographic. Use generate_crosstab_filtered() to add demographic sub-population filters (e.g. gender × rural).",
            "5. Use get_platform_trends() / get_freq_trends() for time series.",
            "6. Use get_ordinal_distribution() / get_ordinal_crosstab() for frequency, trust, and attitude scales.",
            "7. Use get_platform_posting_summary() for a full profile of one platform.",
            "8. Use the _batch variants to run multiple queries in parallel.",
            "9. Use run_ols_regression() or run_logistic_regression() to test whether differences are statistically meaningful while controlling for other variables.",
        ],
    }, indent=2)


@mcp.tool()
async def get_available_variables() -> str:
    """Return available demographic variables, platforms, and wave range from the dataset."""
    try:
        result = run_query(f"""
            SELECT
              COUNT(*)           AS total_rows,
              COUNT(DISTINCT id) AS unique_respondents,
              COUNT(DISTINCT wave) AS wave_count,
              ARRAY_TO_STRING(
                ARRAY(
                  SELECT FORMAT('%g', wave_f)
                  FROM (SELECT DISTINCT CAST(wave AS FLOAT64) AS wave_f FROM {FULL_TABLE})
                  ORDER BY wave_f
                ), ', '
              ) AS waves
            FROM {FULL_TABLE}
        """)
        row = result.iloc[0]

        return json.dumps({
            "demographics": DEMOGRAPHIC_COLUMNS,
            "attitudinal": ATTITUDINAL_COLUMNS,
            "platforms": PLATFORM_COLUMNS,
            "late_platforms": list(LATE_PLATFORMS),
            "freq_columns": FREQ_COLUMNS,
            "late_freq_platforms": list(LATE_FREQ_PLATFORMS),
            "trust_columns": TRUST_COLUMNS,
            "pol_post_columns": POL_POST_COLUMNS,
            "pol_news_columns": POL_NEWS_COLUMNS,
            "pol_trust_columns": POL_TRUST_COLUMNS,
            "phq9_columns": PHQ9_COLUMNS,
            "total_rows": int(row["total_rows"]),
            "unique_respondents": int(row["unique_respondents"]),
            "wave_count": int(row["wave_count"]),
            "waves": row["waves"],
            "notes": {
                "platform_usage": "Binary (1=uses, 0=does not). late_platforms have NULL in earlier waves.",
                "ordinal_sentinel": "All ordinal columns use -99 for skipped/refused responses — excluded automatically.",
                "weights": (
                    "All rates, percentages, and means are WEIGHTED using the survey 'weight' column. "
                    "unweighted_n fields are raw respondent headcounts for reliability checks only — "
                    "never use unweighted_n to compute percentages or present as population estimates."
                ),
                "wave_coverage": "voted24 only from wave 34+; economy only waves 32/35+; sm_post_* variants only waves 27/28 and 33+.",
                "phq9_sensitivity": "PHQ-9 items are clinical mental health measures. Only aggregate statistics are returned.",
                "missing_platform_waves": (
                    "Some waves exist in the panel but platform questions were not asked. "
                    "get_platform_trends and get_freq_trends will return a 'missing_waves' field "
                    "listing these gaps. Do NOT interpolate across missing waves in trend charts — "
                    "show explicit breaks."
                ),
                "key_events": (
                    "get_platform_trends and get_freq_trends include a 'key_events' field for platforms "
                    "with major historical inflection points (e.g., Twitter Wave 25 = Musk acquisition Oct 2022). "
                    "Always annotate trend charts with vertical dashed lines at these events."
                ),
            },
            "problematic_waves": {
                "35.1": (
                    "Small sample wave. race_cat_5 (race/ethnicity) breakdowns are unavailable — "
                    "all cells fall below the minimum cell size threshold and are suppressed. "
                    "Use aggregate-level queries for this wave; demographic crosstabs by race may return no data."
                ),
            },
        }, indent=2)

    except Exception as e:
        logger.error(f"get_available_variables error: {e}")
        raise


@mcp.tool()
async def generate_crosstab(
    platform: str,
    demographic: str,
    wave: Optional[str] = None,
) -> str:
    """Platform adoption rate broken down by a demographic variable.

    Returns survey-weighted user_rate_pct (population-representative % using the platform)
    per demographic group, with cell suppression for groups with unweighted n < MIN_CELL_SIZE.
    All rates and counts use the respondent survey weight for population-representative estimates.

    Args:
        platform:    Column name, e.g. "use_twitter", "use_tiktok"
        demographic: Column name, e.g. "age_cat_8", "party3", "gender"
        wave:        Optional wave number to filter to (e.g. "35"). Omit for all waves.
    """
    if platform not in PLATFORM_COLUMNS:
        raise ValueError(f"Unknown platform '{platform}'. Choose from: {PLATFORM_COLUMNS}")
    valid_demographics = DEMOGRAPHIC_COLUMNS + ATTITUDINAL_COLUMNS
    if demographic not in valid_demographics:
        raise ValueError(f"Unknown demographic '{demographic}'. Choose from: {valid_demographics}")

    try:
        df = run_query(f"""
            SELECT
              {demographic}                                               AS demographic_value,
              COUNT(*)                                                    AS unweighted_n,
              ROUND(SUM(weight), 1)                                       AS weighted_n,
              ROUND(SUM({platform} * weight), 1)                          AS weighted_users,
              ROUND((SUM(weight) - SUM({platform} * weight)), 1)          AS weighted_non_users,
              ROUND(SUM({platform} * weight) / SUM(weight) * 100, 2)      AS user_rate_pct,
              CASE WHEN COUNT(*) < {MIN_CELL_SIZE} THEN TRUE ELSE FALSE END AS suppressed
            FROM {FULL_TABLE}
            WHERE {platform} IS NOT NULL
              AND {demographic} IS NOT NULL
              AND weight IS NOT NULL
              {"AND " + demographic + " > 0" if demographic in ALL_ORDINAL_COLUMNS else ""}
              {wave_clause(wave)}
            GROUP BY {demographic}
            ORDER BY {demographic}
        """)

        # Apply suppression (based on unweighted_n to protect actual respondent privacy)
        df.loc[df["suppressed"], ["weighted_n", "weighted_users", "weighted_non_users", "user_rate_pct"]] = None

        return json.dumps({
            "platform": platform,
            "demographic": demographic,
            "wave_filter": wave or "all",
            "suppression_note": f"Cells with n<{MIN_CELL_SIZE} suppressed for privacy",
            "column_definitions": COLUMN_DEFINITIONS,
            "interpretation_note": (
                "unweighted_n = raw respondent headcount — for reliability checks only, NOT a population estimate. "
                "user_rate_pct = WEIGHTED adoption rate — population-representative. "
                "When presenting a table, label the N column as 'Unweighted N' and the rate column as '% (weighted)'."
            ),
            "data": df.to_dict(orient="records"),
        }, indent=2, default=str)

    except Exception as e:
        logger.error(f"generate_crosstab error: {e}")
        raise


@mcp.tool()
async def generate_marginals(
    variable: str,
    wave: Optional[str] = None,
) -> str:
    """Distribution for a single variable (demographic or platform).

    For demographics: count and % per category.
    For platforms: overall adoption rate (% using the platform).

    Args:
        variable: Demographic column (e.g. "age_cat_8") or platform column (e.g. "use_twitter")
        wave:     Optional wave number to filter to. Omit for all waves.
    """
    all_valid = (
        DEMOGRAPHIC_COLUMNS + ATTITUDINAL_COLUMNS + PLATFORM_COLUMNS +
        ALL_ORDINAL_COLUMNS + ALL_BINARY_COLUMNS
    )
    if variable not in all_valid:
        raise ValueError(
            f"Unknown variable '{variable}'. "
            f"Choose from demographics: {DEMOGRAPHIC_COLUMNS}, "
            f"attitudinal: {ATTITUDINAL_COLUMNS}, "
            f"platforms: {PLATFORM_COLUMNS}, "
            f"ordinal: {ALL_ORDINAL_COLUMNS}, "
            f"or binary: {ALL_BINARY_COLUMNS}"
        )

    # Binary columns: use_* and sm_post_*/pol_news2_* — compute adoption rate
    is_binary = variable in PLATFORM_COLUMNS or variable in ALL_BINARY_COLUMNS

    try:
        if is_binary:
            # Platform: return overall adoption rate
            df = run_query(f"""
                SELECT
                  '{variable}'                                              AS platform,
                  COUNT(*)                                                  AS unweighted_n,
                  ROUND(SUM(weight), 1)                                     AS weighted_n,
                  ROUND(SUM({variable} * weight), 1)                        AS weighted_users,
                  ROUND(SUM(weight) - SUM({variable} * weight), 1)          AS weighted_non_users,
                  ROUND(SUM({variable} * weight) / SUM(weight) * 100, 2)    AS user_rate_pct
                FROM {FULL_TABLE}
                WHERE {variable} IS NOT NULL
                  AND weight IS NOT NULL
                  {wave_clause(wave)}
            """)
            return json.dumps({
                "variable": variable,
                "type": "platform",
                "wave_filter": wave or "all",
                "column_definitions": COLUMN_DEFINITIONS,
                "interpretation_note": (
                    "unweighted_n = raw respondent headcount (reliability check only). "
                    "user_rate_pct = WEIGHTED, population-representative adoption rate."
                ),
                "data": df.to_dict(orient="records"),
            }, indent=2, default=str)

        else:
            # Demographic / attitudinal / ordinal: category distribution
            # For ordinal columns, also exclude -99 (skipped/refused sentinel)
            sentinel_filter = f"AND {variable} > 0" if variable in ALL_ORDINAL_COLUMNS else ""
            df = run_query(f"""
                SELECT
                  {variable}                                                   AS value,
                  COUNT(*)                                                      AS unweighted_n,
                  ROUND(SUM(weight), 1)                                         AS weighted_n,
                  ROUND(SUM(weight) * 100.0 / SUM(SUM(weight)) OVER(), 2)      AS pct,
                  CASE WHEN COUNT(*) < {MIN_CELL_SIZE} THEN TRUE ELSE FALSE END AS suppressed
                FROM {FULL_TABLE}
                WHERE {variable} IS NOT NULL
                  AND weight IS NOT NULL
                  {sentinel_filter}
                  {wave_clause(wave)}
                GROUP BY {variable}
                ORDER BY {variable}
            """)

            df.loc[df["suppressed"], ["weighted_n", "pct"]] = None

            return json.dumps({
                "variable": variable,
                "type": "demographic",
                "wave_filter": wave or "all",
                "suppression_note": f"Cells with n<{MIN_CELL_SIZE} suppressed for privacy",
                "column_definitions": COLUMN_DEFINITIONS,
                "interpretation_note": (
                    "unweighted_n = raw respondent headcount (reliability check only). "
                    "pct = WEIGHTED, population-representative percentage. "
                    "Label clearly when presenting to users."
                ),
                "data": df.to_dict(orient="records"),
            }, indent=2, default=str)

    except Exception as e:
        logger.error(f"generate_marginals error: {e}")
        raise


@mcp.tool()
async def generate_crosstab_filtered(
    platform: str,
    demographic: str,
    filters: Dict[str, str],
    wave: Optional[str] = None,
) -> str:
    """Platform adoption rate broken down by a demographic, with additional demographic filters.

    Use this to answer intersection queries like "Facebook usage by gender among rural respondents"
    or "TikTok adoption by age among college-educated Republicans."

    Returns survey-weighted user_rate_pct per demographic group for the filtered sub-population,
    with cell suppression for groups with unweighted n < MIN_CELL_SIZE.

    Args:
        platform:    Platform column, e.g. "use_facebook"
        demographic: Column to group results by, e.g. "gender"
        filters:     Dict of {column: value} to restrict the sub-population,
                     e.g. {"urban_type": "Rural"} or {"urban_type": "Rural", "party3": "Democrat"}
        wave:        Optional wave number to filter to (e.g. "35"). Omit for all waves.

    Example:
        generate_crosstab_filtered(
            platform="use_facebook",
            demographic="gender",
            filters={"urban_type": "Rural"}
        )
        → Facebook usage by gender, restricted to rural respondents only.
    """
    if platform not in PLATFORM_COLUMNS:
        raise ValueError(f"Unknown platform '{platform}'. Choose from: {PLATFORM_COLUMNS}")

    valid_demographics = DEMOGRAPHIC_COLUMNS + ATTITUDINAL_COLUMNS
    if demographic not in valid_demographics:
        raise ValueError(f"Unknown demographic '{demographic}'. Choose from: {valid_demographics}")

    if not filters:
        raise ValueError("filters must contain at least one {column: value} pair. "
                         "Use generate_crosstab() if no filtering is needed.")

    # Validate each filter column and build safe SQL clauses
    filter_clauses = []
    for col, val in filters.items():
        if col not in valid_demographics:
            raise ValueError(
                f"Unknown filter column '{col}'. Choose from: {valid_demographics}"
            )
        if col == demographic:
            raise ValueError(
                f"Filter column '{col}' cannot be the same as the breakdown demographic. "
                "Use filters to restrict the sub-population, not to select a single group."
            )
        # Safe: col is validated against allowlist; val is parameterized via f-string
        # but BigQuery parameterized queries are not available here — rely on column allowlist
        # and treat val as a string literal (same pattern used in get_platform_trends).
        filter_clauses.append(f"AND {col} = '{val}'")

    filter_sql = "\n              ".join(filter_clauses)

    try:
        df = run_query(f"""
            SELECT
              {demographic}                                               AS demographic_value,
              COUNT(*)                                                    AS unweighted_n,
              ROUND(SUM(weight), 1)                                       AS weighted_n,
              ROUND(SUM({platform} * weight), 1)                          AS weighted_users,
              ROUND((SUM(weight) - SUM({platform} * weight)), 1)          AS weighted_non_users,
              ROUND(SUM({platform} * weight) / SUM(weight) * 100, 2)      AS user_rate_pct,
              CASE WHEN COUNT(*) < {MIN_CELL_SIZE} THEN TRUE ELSE FALSE END AS suppressed
            FROM {FULL_TABLE}
            WHERE {platform} IS NOT NULL
              AND {demographic} IS NOT NULL
              AND weight IS NOT NULL
              {"AND " + demographic + " > 0" if demographic in ALL_ORDINAL_COLUMNS else ""}
              {filter_sql}
              {wave_clause(wave)}
            GROUP BY {demographic}
            ORDER BY {demographic}
        """)

        df.loc[df["suppressed"], ["weighted_n", "weighted_users", "weighted_non_users", "user_rate_pct"]] = None

        return json.dumps({
            "platform": platform,
            "demographic": demographic,
            "filters": filters,
            "wave_filter": wave or "all",
            "suppression_note": f"Cells with n<{MIN_CELL_SIZE} suppressed for privacy",
            "column_definitions": COLUMN_DEFINITIONS,
            "interpretation_note": (
                "unweighted_n = raw respondent headcount (reliability check only). "
                "user_rate_pct = WEIGHTED, population-representative adoption rate for the filtered sub-population. "
                "Label clearly when presenting to users."
            ),
            "data": df.to_dict(orient="records"),
        }, indent=2, default=str)

    except Exception as e:
        logger.error(f"generate_crosstab_filtered error: {e}")
        raise


@mcp.tool()
async def generate_crosstab_batch(
    platform: str,
    demographics: List[str],
    wave: Optional[str] = None,
) -> str:
    """Run generate_crosstab for one platform across multiple demographics in parallel.

    Args:
        platform:     Platform column, e.g. "use_twitter"
        demographics: List of demographic columns
        wave:         Optional wave filter
    """
    tasks = [generate_crosstab(platform, d, wave) for d in demographics]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return json.dumps({
        "platform": platform,
        "wave_filter": wave or "all",
        "results": {
            d: json.loads(r) if not isinstance(r, Exception) else {"error": str(r)}
            for d, r in zip(demographics, results)
        }
    }, indent=2)


@mcp.tool()
async def generate_marginals_batch(
    variables: List[str],
    wave: Optional[str] = None,
) -> str:
    """Run generate_marginals for multiple variables in parallel.

    Args:
        variables: List of demographic or platform column names
        wave:      Optional wave filter
    """
    tasks = [generate_marginals(v, wave) for v in variables]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return json.dumps({
        "wave_filter": wave or "all",
        "results": {
            v: json.loads(r) if not isinstance(r, Exception) else {"error": str(r)}
            for v, r in zip(variables, results)
        }
    }, indent=2)


@mcp.tool()
async def get_platform_trends(
    platform: str,
    demographic: Optional[str] = None,
    demographic_value: Optional[str] = None,
) -> str:
    """Platform adoption rate across waves (time series).

    Use this to track how platform usage has changed over the panel.
    Optionally filter to a specific demographic group.

    Args:
        platform:          Platform column, e.g. "use_twitter"
        demographic:       Optional demographic column to filter by, e.g. "party3"
        demographic_value: Required if demographic is set, e.g. "Republican"
    """
    if platform not in PLATFORM_COLUMNS:
        raise ValueError(f"Unknown platform '{platform}'. Choose from: {PLATFORM_COLUMNS}")

    demo_filter = ""
    if demographic and demographic_value:
        if demographic not in DEMOGRAPHIC_COLUMNS:
            raise ValueError(f"Unknown demographic '{demographic}'")
        demo_filter = f"AND {demographic} = '{demographic_value}'"

    try:
        df = run_query(f"""
            SELECT
              t.wave,
              wd.midpoint_date,
              COUNT(*)                                                   AS unweighted_n,
              ROUND(SUM(t.weight), 1)                                    AS weighted_n,
              ROUND(SUM(t.{platform} * t.weight), 1)                     AS weighted_users,
              ROUND(SUM(t.{platform} * t.weight) / SUM(t.weight) * 100, 2) AS user_rate_pct
            FROM {FULL_TABLE} t
            LEFT JOIN {WAVE_DATES_TABLE} wd ON CAST(t.wave AS FLOAT64) = wd.wave_num
            WHERE t.{platform} IS NOT NULL
              AND t.weight IS NOT NULL
              {demo_filter}
            GROUP BY t.wave, wd.midpoint_date
            ORDER BY CAST(t.wave AS FLOAT64)
        """)

        # Detect waves that exist in the panel but are absent for this platform.
        # These are genuine data gaps (question not asked that wave) — not missing rows.
        all_waves_df = run_query(f"""
            SELECT DISTINCT CAST(wave AS FLOAT64) AS wave_num
            FROM {FULL_TABLE}
            ORDER BY wave_num
        """)
        all_wave_set  = {int(w) for w in all_waves_df["wave_num"].tolist()}
        data_wave_set = {int(float(r["wave"])) for r in df.to_dict(orient="records")}
        missing_waves = sorted(all_wave_set - data_wave_set)

        response: dict = {
            "platform": platform,
            "demographic_filter": f"{demographic}={demographic_value}" if demographic else None,
            "column_definitions": COLUMN_DEFINITIONS,
            "interpretation_note": (
                "unweighted_n = raw respondent headcount (reliability check only). "
                "user_rate_pct = WEIGHTED, population-representative adoption rate. "
                "Always label these distinctly when presenting results to users."
            ),
            "data": df.to_dict(orient="records"),
        }

        if missing_waves:
            response["missing_waves"] = missing_waves
            response["gap_warning"] = (
                f"Waves {missing_waves} exist in the CHIP50 panel but have no data for "
                f"'{platform}' — the question was likely not fielded those waves. "
                "Do NOT interpolate or connect data points across these gaps in charts. "
                "Show them as explicit breaks or missing markers."
            )

        key_events = PLATFORM_KEY_EVENTS.get(platform, [])
        if key_events:
            response["key_events"] = key_events
            response["annotation_instruction"] = (
                "REQUIRED: Annotate trend charts for this platform with vertical dashed lines "
                "at every wave listed in 'key_events'. Do not skip these annotations."
            )

        return json.dumps(response, indent=2, default=str)

    except Exception as e:
        logger.error(f"get_platform_trends error: {e}")
        raise


@mcp.tool()
async def get_ordinal_distribution(
    column: str,
    wave: Optional[str] = None,
) -> str:
    """Weighted distribution of any ordinal variable (frequency, trust, ideology, etc.).

    Returns the weighted % of respondents at each response category,
    excluding -99 (skipped/refused) values.

    Args:
        column: Any ordinal column — e.g. "freq_twitter", "sm_trust_facebook",
                "ideology", "economy", "phq9_1", "pol_trust_science"
        wave:   Optional wave filter. Omit for all waves.

    Note: PHQ-9 columns (phq9_1–phq9_12) are clinical mental health screening
    items. Only population-level aggregate distributions are returned.
    """
    valid = ALL_ORDINAL_COLUMNS
    if column not in valid:
        raise ValueError(
            f"Unknown ordinal column '{column}'. "
            f"Choose from: {valid}"
        )

    try:
        df = run_query(f"""
            SELECT
              {column}                                                        AS value,
              COUNT(*)                                                        AS unweighted_n,
              ROUND(SUM(weight), 1)                                           AS weighted_n,
              ROUND(SUM(weight) * 100.0 / SUM(SUM(weight)) OVER(), 2)        AS pct,
              CASE WHEN COUNT(*) < {MIN_CELL_SIZE} THEN TRUE ELSE FALSE END   AS suppressed
            FROM {FULL_TABLE}
            WHERE {column} IS NOT NULL
              AND {column} > 0
              AND weight IS NOT NULL
              {wave_clause(wave)}
            GROUP BY {column}
            ORDER BY {column}
        """)

        df.loc[df["suppressed"], ["weighted_n", "pct"]] = None

        # Attach scale labels if applicable
        scale_labels = None
        if column.startswith("freq_"):
            scale_labels = FREQ_SCALE_LABELS
        elif column.startswith("sm_trust_") or column.startswith("pol_trust_"):
            scale_labels = TRUST_SCALE_LABELS
        elif column == "ideology":
            scale_labels = IDEOLOGY_SCALE_LABELS

        return json.dumps({
            "column": column,
            "type": "ordinal_distribution",
            "wave_filter": wave or "all",
            "suppression_note": f"Cells with n<{MIN_CELL_SIZE} suppressed for privacy",
            "scale_labels": scale_labels,
            "column_definitions": COLUMN_DEFINITIONS,
            "interpretation_note": (
                "unweighted_n = raw respondent headcount (reliability check only). "
                "pct = WEIGHTED, population-representative percentage. "
                "Always label as 'weighted %' when presenting to users."
            ),
            "data": df.to_dict(orient="records"),
        }, indent=2, default=str)

    except Exception as e:
        logger.error(f"get_ordinal_distribution error: {e}")
        raise


@mcp.tool()
async def get_ordinal_crosstab(
    column: str,
    demographic: str,
    wave: Optional[str] = None,
) -> str:
    """Weighted mean of an ordinal variable broken down by a demographic group.

    Use this to answer questions like "How much do Republicans trust Twitter vs Democrats?"
    or "Does TikTok usage frequency vary by age group?"

    Returns the weighted mean of the ordinal column per demographic category,
    excluding -99 (skipped/refused) values.

    Args:
        column:      Any ordinal column — e.g. "sm_trust_twitter", "freq_tiktok", "ideology"
        demographic: Demographic or attitudinal column — e.g. "party3", "age_cat_8", "gender"
        wave:        Optional wave filter. Omit for all waves.
    """
    if column not in ALL_ORDINAL_COLUMNS:
        raise ValueError(f"Unknown ordinal column '{column}'. Choose from: {ALL_ORDINAL_COLUMNS}")
    valid_demographics = DEMOGRAPHIC_COLUMNS + ATTITUDINAL_COLUMNS
    if demographic not in valid_demographics:
        raise ValueError(f"Unknown demographic '{demographic}'. Choose from: {valid_demographics}")

    demo_sentinel = f"AND {demographic} > 0" if demographic in ALL_ORDINAL_COLUMNS else ""

    try:
        df = run_query(f"""
            SELECT
              {demographic}                                                        AS demographic_value,
              COUNT(*)                                                             AS unweighted_n,
              ROUND(SUM(weight), 1)                                                AS weighted_n,
              ROUND(SUM({column} * weight) / SUM(weight), 3)                      AS weighted_mean,
              CASE WHEN COUNT(*) < {MIN_CELL_SIZE} THEN TRUE ELSE FALSE END        AS suppressed
            FROM {FULL_TABLE}
            WHERE {column} IS NOT NULL
              AND {column} > 0
              AND {demographic} IS NOT NULL
              AND weight IS NOT NULL
              {demo_sentinel}
              {wave_clause(wave)}
            GROUP BY {demographic}
            ORDER BY {demographic}
        """)

        df.loc[df["suppressed"], ["weighted_n", "weighted_mean"]] = None

        scale_labels = None
        if column.startswith("freq_"):
            scale_labels = FREQ_SCALE_LABELS
        elif column.startswith("sm_trust_") or column.startswith("pol_trust_"):
            scale_labels = TRUST_SCALE_LABELS
        elif column == "ideology":
            scale_labels = IDEOLOGY_SCALE_LABELS

        return json.dumps({
            "column": column,
            "demographic": demographic,
            "wave_filter": wave or "all",
            "suppression_note": f"Cells with n<{MIN_CELL_SIZE} suppressed for privacy",
            "scale_labels": scale_labels,
            "column_definitions": COLUMN_DEFINITIONS,
            "interpretation_note": (
                "unweighted_n = raw respondent headcount (reliability check only). "
                "weighted_mean = WEIGHTED, population-representative mean. "
                "Always label as 'weighted mean' when presenting to users."
            ),
            "data": df.to_dict(orient="records"),
        }, indent=2, default=str)

    except Exception as e:
        logger.error(f"get_ordinal_crosstab error: {e}")
        raise


@mcp.tool()
async def get_freq_trends(
    platform: str,
    demographic: Optional[str] = None,
    demographic_value: Optional[str] = None,
) -> str:
    """Mean platform usage frequency across waves (time series).

    Tracks how often respondents use a platform over time using the ordinal
    frequency scale (1–6), excluding -99 (skipped/refused) values.
    Optionally filter to a specific demographic group.

    Args:
        platform:          Platform name without prefix, e.g. "twitter", "tiktok", "facebook"
        demographic:       Optional demographic column to filter by, e.g. "party3"
        demographic_value: Required if demographic is set, e.g. "Republican"
    """
    freq_col = f"freq_{platform}"
    if freq_col not in FREQ_COLUMNS:
        raise ValueError(
            f"Unknown platform '{platform}'. "
            f"Choose from: {[c.replace('freq_', '') for c in FREQ_COLUMNS]}"
        )

    demo_filter = ""
    if demographic and demographic_value:
        if demographic not in DEMOGRAPHIC_COLUMNS + ATTITUDINAL_COLUMNS:
            raise ValueError(f"Unknown demographic '{demographic}'")
        demo_filter = f"AND {demographic} = '{demographic_value}'"

    try:
        df = run_query(f"""
            SELECT
              t.wave,
              wd.midpoint_date,
              COUNT(*)                                                     AS unweighted_n,
              ROUND(SUM(t.weight), 1)                                      AS weighted_n,
              ROUND(SUM(t.{freq_col} * t.weight) / SUM(t.weight), 3)      AS weighted_mean_freq
            FROM {FULL_TABLE} t
            LEFT JOIN {WAVE_DATES_TABLE} wd ON CAST(t.wave AS FLOAT64) = wd.wave_num
            WHERE t.{freq_col} IS NOT NULL
              AND t.{freq_col} > 0
              AND t.weight IS NOT NULL
              {demo_filter}
            GROUP BY t.wave, wd.midpoint_date
            ORDER BY CAST(t.wave AS FLOAT64)
        """)

        all_waves_df = run_query(f"""
            SELECT DISTINCT CAST(wave AS FLOAT64) AS wave_num
            FROM {FULL_TABLE}
            ORDER BY wave_num
        """)
        all_wave_set  = {int(w) for w in all_waves_df["wave_num"].tolist()}
        data_wave_set = {int(float(r["wave"])) for r in df.to_dict(orient="records")}
        missing_waves = sorted(all_wave_set - data_wave_set)

        response: dict = {
            "platform": platform,
            "freq_column": freq_col,
            "demographic_filter": f"{demographic}={demographic_value}" if demographic else None,
            "scale_note": "Frequency scale 1–6 (1=never, 6=several times a day)",
            "scale_labels": FREQ_SCALE_LABELS,
            "column_definitions": COLUMN_DEFINITIONS,
            "interpretation_note": (
                "unweighted_n = raw respondent headcount (reliability check only). "
                "weighted_mean_freq = WEIGHTED, population-representative mean frequency. "
                "Always label these distinctly when presenting results to users."
            ),
            "data": df.to_dict(orient="records"),
        }

        if missing_waves:
            response["missing_waves"] = missing_waves
            response["gap_warning"] = (
                f"Waves {missing_waves} exist in the CHIP50 panel but have no frequency data for "
                f"'{platform}' — the question was likely not fielded those waves. "
                "Do NOT interpolate across these gaps. Show as explicit breaks in charts."
            )

        key_events = PLATFORM_KEY_EVENTS.get(platform, [])
        if key_events:
            response["key_events"] = key_events
            response["annotation_instruction"] = (
                "REQUIRED: Annotate trend charts for this platform with vertical dashed lines "
                "at every wave listed in 'key_events'. Do not skip these annotations."
            )

        return json.dumps(response, indent=2, default=str)

    except Exception as e:
        logger.error(f"get_freq_trends error: {e}")
        raise


@mcp.tool()
async def get_platform_posting_summary(
    platform: str,
    wave: Optional[str] = None,
) -> str:
    """All key metrics for one platform in a single call.

    Returns adoption rate, mean usage frequency, mean platform trust,
    mean political posting frequency, and posting behavior rates (variants 1–3).

    Args:
        platform: Platform name without prefix, e.g. "twitter", "tiktok", "facebook"
        wave:     Optional wave filter. Omit for all waves.
    """
    use_col      = f"use_{platform}"
    freq_col     = f"freq_{platform}"
    trust_col    = f"sm_trust_{platform}"
    pol_post_col = f"sm_post_pol_{platform}"
    post_cols    = [f"sm_post_{platform}_{v}" for v in [1, 2, 3]]

    if use_col not in PLATFORM_COLUMNS:
        raise ValueError(
            f"Unknown platform '{platform}'. "
            f"Choose from: {[c.replace('use_', '') for c in PLATFORM_COLUMNS]}"
        )

    results: dict = {
        "platform": platform,
        "wave_filter": wave or "all",
        "column_definitions": COLUMN_DEFINITIONS,
        "interpretation_note": (
            "All rates and means are WEIGHTED, population-representative estimates. "
            "unweighted_n fields are raw respondent headcounts for reliability checks only."
        ),
    }

    async def _query(label: str, sql: str):
        try:
            df = run_query(sql)
            results[label] = df.to_dict(orient="records")
        except Exception as e:
            results[label] = {"error": str(e)}

    wc = wave_clause(wave)

    tasks = [
        _query("adoption_rate", f"""
            SELECT
              COUNT(*) AS unweighted_n,
              ROUND(SUM({use_col} * weight) / SUM(weight) * 100, 2) AS user_rate_pct
            FROM {FULL_TABLE}
            WHERE {use_col} IS NOT NULL AND weight IS NOT NULL {wc}
        """),
        _query("mean_frequency", f"""
            SELECT
              COUNT(*) AS unweighted_n,
              ROUND(SUM({freq_col} * weight) / SUM(weight), 3) AS weighted_mean_freq
            FROM {FULL_TABLE}
            WHERE {freq_col} IS NOT NULL AND {freq_col} > 0 AND weight IS NOT NULL {wc}
        """ if freq_col in FREQ_COLUMNS else "SELECT 'not available' AS note"),
        _query("mean_trust", f"""
            SELECT
              COUNT(*) AS unweighted_n,
              ROUND(SUM({trust_col} * weight) / SUM(weight), 3) AS weighted_mean_trust
            FROM {FULL_TABLE}
            WHERE {trust_col} IS NOT NULL AND {trust_col} > 0 AND weight IS NOT NULL {wc}
        """ if trust_col in TRUST_COLUMNS else "SELECT 'not available' AS note"),
        _query("mean_pol_posting", f"""
            SELECT
              COUNT(*) AS unweighted_n,
              ROUND(SUM({pol_post_col} * weight) / SUM(weight), 3) AS weighted_mean_pol_post
            FROM {FULL_TABLE}
            WHERE {pol_post_col} IS NOT NULL AND {pol_post_col} > 0 AND weight IS NOT NULL {wc}
        """ if pol_post_col in POL_POST_COLUMNS else "SELECT 'not available' AS note"),
    ]

    for v, col in enumerate(post_cols, 1):
        if col in SM_POST_COLUMNS:
            tasks.append(_query(f"posting_variant_{v}_rate", f"""
                SELECT
                  COUNT(*) AS unweighted_n,
                  ROUND(SUM({col} * weight) / SUM(weight) * 100, 2) AS rate_pct
                FROM {FULL_TABLE}
                WHERE {col} IS NOT NULL AND weight IS NOT NULL {wc}
            """))

    await asyncio.gather(*tasks)

    return json.dumps(results, indent=2, default=str)


# ── Regression helpers ───────────────────────────────────────────────────────

def _fetch_regression_data(
    outcome: str,
    predictors: List[str],
    wave: Optional[str],
) -> pd.DataFrame:
    """Pull individual-level rows needed for a regression from BigQuery."""
    cols = [outcome] + predictors
    select_cols = ", ".join(cols) + ", weight"

    not_null = " AND ".join(f"{c} IS NOT NULL" for c in cols + ["weight"])

    sentinel_clauses = " ".join(
        f"AND {c} > 0" for c in cols if c in _SENTINEL_COLUMNS
    )

    sql = f"""
        SELECT {select_cols}
        FROM {FULL_TABLE}
        WHERE {not_null}
          {sentinel_clauses}
          {wave_clause(wave)}
    """
    return run_query(sql)


def _resolve_reference_level(col: str, available: List[str], requested: Optional[str]) -> str:
    """Return the reference level to use for a categorical column.

    If *requested* is provided and exists in *available*, use it.
    Otherwise fall back to the alphabetically first category and emit a warning
    when the requested level was not found.
    """
    if requested is not None:
        if requested in available:
            return requested
        logger.warning(
            f"Requested reference level '{requested}' not found in '{col}' "
            f"(available: {available}). Falling back to alphabetically first."
        )
    return available[0] if available else "first"


def _encode_predictors(
    df: pd.DataFrame,
    predictors: List[str],
    reference_levels: Optional[Dict[str, str]] = None,
) -> tuple[pd.DataFrame, List[str], List[str]]:
    """Dummy-encode categorical predictors; pass numeric ones through.

    Args:
        df: Data frame with all predictor columns present.
        predictors: Ordered list of predictor column names.
        reference_levels: Optional mapping of {column_name: reference_category}.
            When provided for a categorical column the specified category is used
            as the dropped (reference) level.  Unknown categories fall back to
            the alphabetically first value with a logged warning.

    Returns:
        (X DataFrame, encoding notes, warning messages)
    """
    if reference_levels is None:
        reference_levels = {}
    notes: List[str] = []
    warnings: List[str] = []
    frames: List[pd.DataFrame] = []
    for col in predictors:
        if col in _CATEGORICAL_COLUMNS:
            sorted_cats = sorted(df[col].dropna().unique())
            requested_ref = reference_levels.get(col)
            ref = _resolve_reference_level(col, sorted_cats, requested_ref)

            if requested_ref is not None and requested_ref not in sorted_cats:
                warnings.append(
                    f"Reference level '{requested_ref}' not found for '{col}'. "
                    f"Available categories: {sorted_cats}. "
                    f"Falling back to '{ref}'."
                )

            # Put the reference level first so drop_first=True always drops it.
            other_cats = [c for c in sorted_cats if c != ref]
            ordered_cats = [ref] + other_cats
            cat_series = pd.Categorical(df[col], categories=ordered_cats)
            dummies = pd.get_dummies(cat_series, prefix=col, drop_first=True, dtype=float)
            dummies.index = df.index

            notes.append(f"'{col}' dummy-encoded (reference category: '{ref}')")
            frames.append(dummies)
        else:
            frames.append(df[[col]].astype(float))
    return pd.concat(frames, axis=1), notes, warnings


@mcp.tool()
async def run_ols_regression(
    outcome: str,
    predictors: List[str],
    wave: Optional[str] = None,
    reference_levels: Optional[Dict[str, str]] = None,
    use_weights: bool = True,
) -> str:
    """Run an OLS regression of a continuous/ordinal outcome on one or more predictors.

    Fits outcome ~ predictor1 + predictor2 + ... using Weighted Least Squares
    (WLS) with survey weights by default, so estimates are population-representative.
    Categorical demographic predictors are automatically dummy-encoded.

    Args:
        outcome: Dependent variable — any ordinal or continuous column
            (attitudinal, freq, trust, phq9, pol_trust, etc.).
            For binary outcomes (platform use) use run_logistic_regression().
        predictors: One or more independent variables. Demographics are
            dummy-encoded automatically; ordinal columns enter as numeric.
        wave: Optional — restrict to a single survey wave.
        reference_levels: Optional mapping of {column_name: reference_category}
            for categorical predictors. Specifies which category to use as the
            baseline (dropped) level in dummy encoding. For example,
            {"gender": "Male", "race_cat_5": "White"} makes Male and White the
            reference categories. When omitted, the alphabetically first
            category is used. Unknown category values fall back to the
            alphabetically first with a warning in the response.
        use_weights: If True (default), applies survey weights via WLS for
            population-representative estimates. Set to False for unweighted OLS.

    Returns:
        JSON with: coefficients, std errors, t-stats, p-values,
        95% CIs, R², adjusted R², F-statistic, AIC, BIC.
        Any reference-level warnings are included in the 'notes' field.
    """
    all_cols = [outcome] + predictors
    invalid = [c for c in all_cols if c not in _ALL_REGRESSION_COLUMNS]
    if invalid:
        return json.dumps({
            "error": f"Unknown columns: {invalid}. Call get_available_variables() to see valid column names."
        })
    if outcome in _CATEGORICAL_COLUMNS:
        return json.dumps({
            "error": (
                f"'{outcome}' is a nominal categorical variable and is not appropriate as an OLS outcome. "
                "Use a continuous or ordinal outcome, or run_logistic_regression() for binary outcomes."
            )
        })

    try:
        df = await asyncio.get_event_loop().run_in_executor(
            None, _fetch_regression_data, outcome, predictors, wave
        )
    except Exception as e:
        logger.error(f"run_ols_regression data fetch error: {e}")
        return json.dumps({"error": str(e)})

    if len(df) < 50:
        return json.dumps({"error": f"Too few observations ({len(df)}) after filters — cannot fit model."})

    y = df[outcome].astype(float)
    weights = df["weight"].astype(float)
    X_df, enc_notes, ref_warnings = _encode_predictors(df, predictors, reference_levels)
    X = sm.add_constant(X_df, has_constant="add")

    try:
        if use_weights:
            model = sm.WLS(y, X, weights=weights).fit()
        else:
            model = sm.OLS(y, X).fit()
    except Exception as e:
        logger.error(f"run_ols_regression fit error: {e}")
        return json.dumps({"error": f"Model fitting failed: {e}"})

    ci = model.conf_int(alpha=0.05)
    coefficients = []
    for term in model.params.index:
        p = float(model.pvalues[term])
        coefficients.append({
            "term": term,
            "estimate": round(float(model.params[term]), 6),
            "std_error": round(float(model.bse[term]), 6),
            "t_stat": round(float(model.tvalues[term]), 4),
            "p_value": round(p, 6),
            "ci_lower_95": round(float(ci.loc[term, 0]), 6),
            "ci_upper_95": round(float(ci.loc[term, 1]), 6),
            "significant_05": p < 0.05,
        })

    weight_note = (
        "Survey weights applied via Weighted Least Squares (WLS)."
        if use_weights else
        "Unweighted OLS — estimates are NOT survey-weighted and may not be population-representative."
    )
    notes = enc_notes + ref_warnings + [
        weight_note,
        "Standard errors are model-based (not design-based); interpret accordingly.",
    ]
    if any(c in _SENTINEL_COLUMNS for c in all_cols):
        notes.append("Rows with -99 (skipped/refused) excluded from all ordinal columns.")

    model_type = "OLS (Weighted Least Squares)" if use_weights else "OLS (Unweighted)"
    return json.dumps({
        "model_type": model_type,
        "outcome": outcome,
        "predictors_specified": predictors,
        "reference_levels_requested": reference_levels,
        "wave": wave,
        "n_observations": int(len(df)),
        "weighted_n": round(float(weights.sum()), 1),
        "model_fit": {
            "r_squared": round(float(model.rsquared), 6),
            "adj_r_squared": round(float(model.rsquared_adj), 6),
            "f_statistic": round(float(model.fvalue), 4) if model.fvalue is not None else None,
            "f_pvalue": round(float(model.f_pvalue), 6) if model.f_pvalue is not None else None,
            "aic": round(float(model.aic), 2),
            "bic": round(float(model.bic), 2),
        },
        "coefficients": coefficients,
        "notes": notes,
    }, indent=2, default=str)


@mcp.tool()
async def run_logistic_regression(
    outcome: str,
    predictors: List[str],
    wave: Optional[str] = None,
    reference_levels: Optional[Dict[str, str]] = None,
    use_weights: bool = True,
) -> str:
    """Run a logistic regression of a binary outcome on one or more predictors.

    Fits outcome ~ predictor1 + predictor2 + ... using a survey-weighted GLM
    (Binomial family, logit link) by default so estimates are population-representative.
    Categorical demographic predictors are automatically dummy-encoded.
    Returns both log-odds coefficients and odds ratios.

    Args:
        outcome: Binary dependent variable (0/1). Platform use columns
            (use_facebook, use_tiktok, etc.) and sm_post_* / pol_news_* columns.
            For ordinal/continuous outcomes use run_ols_regression().
        predictors: One or more independent variables. Demographics are
            dummy-encoded automatically; ordinal columns enter as numeric.
        wave: Optional — restrict to a single survey wave.
        reference_levels: Optional mapping of {column_name: reference_category}
            for categorical predictors. Specifies which category to use as the
            baseline (dropped) level in dummy encoding. For example,
            {"gender": "Male", "race_cat_5": "White"} makes Male and White the
            reference categories. When omitted, the alphabetically first
            category is used. Unknown category values fall back to the
            alphabetically first with a warning in the response.
        use_weights: If True (default), applies survey weights via GLM freq_weights
            for population-representative estimates. Set to False for unweighted logit.

    Returns:
        JSON with: log-odds, odds ratios, std errors, z-stats, p-values,
        95% CIs (log-odds and OR scale), McFadden pseudo-R², AIC, BIC.
        Any reference-level warnings are included in the 'notes' field.
    """
    all_cols = [outcome] + predictors
    invalid = [c for c in all_cols if c not in _ALL_REGRESSION_COLUMNS]
    if invalid:
        return json.dumps({
            "error": f"Unknown columns: {invalid}. Call get_available_variables() to see valid column names."
        })
    if outcome not in _BINARY_COLUMNS:
        return json.dumps({
            "error": (
                f"'{outcome}' is not a recognised binary (0/1) column. "
                "Logistic regression requires a binary outcome (platform use, sm_post_*, pol_news_*). "
                "For ordinal/continuous outcomes use run_ols_regression()."
            )
        })

    try:
        df = await asyncio.get_event_loop().run_in_executor(
            None, _fetch_regression_data, outcome, predictors, wave
        )
    except Exception as e:
        logger.error(f"run_logistic_regression data fetch error: {e}")
        return json.dumps({"error": str(e)})

    if len(df) < 50:
        return json.dumps({"error": f"Too few observations ({len(df)}) after filters — cannot fit model."})

    y = df[outcome].astype(float)
    weights = df["weight"].astype(float)

    unique_vals = set(y.dropna().unique())
    if not unique_vals.issubset({0.0, 1.0}):
        return json.dumps({"error": f"Outcome '{outcome}' has non-binary values: {sorted(unique_vals)[:10]}."})

    X_df, enc_notes, ref_warnings = _encode_predictors(df, predictors, reference_levels)
    X = sm.add_constant(X_df, has_constant="add")

    try:
        if use_weights:
            model = sm.GLM(
                y, X,
                family=sm.families.Binomial(),
                freq_weights=weights,
            ).fit()
        else:
            model = sm.GLM(
                y, X,
                family=sm.families.Binomial(),
            ).fit()
    except Exception as e:
        logger.error(f"run_logistic_regression fit error: {e}")
        return json.dumps({"error": f"Model fitting failed: {e}"})

    ci = model.conf_int(alpha=0.05)
    coefficients = []
    for term in model.params.index:
        p = float(model.pvalues[term])
        lo = float(model.params[term])
        ci_lo = float(ci.loc[term, 0])
        ci_hi = float(ci.loc[term, 1])
        coefficients.append({
            "term": term,
            "log_odds": round(lo, 6),
            "odds_ratio": round(float(np.exp(lo)), 6),
            "std_error": round(float(model.bse[term]), 6),
            "z_stat": round(float(model.tvalues[term]), 4),
            "p_value": round(p, 6),
            "ci_lower_95_log_odds": round(ci_lo, 6),
            "ci_upper_95_log_odds": round(ci_hi, 6),
            "ci_lower_95_OR": round(float(np.exp(ci_lo)), 6),
            "ci_upper_95_OR": round(float(np.exp(ci_hi)), 6),
            "significant_05": p < 0.05,
        })

    llf = float(model.llf)
    llnull = float(model.llnull)
    pseudo_r2 = round(1.0 - (llf / llnull), 6) if llnull != 0 else None

    weight_note = (
        "Survey weights applied via GLM freq_weights (analytic/aweights)."
        if use_weights else
        "Unweighted logit — estimates are NOT survey-weighted and may not be population-representative."
    )
    notes = enc_notes + ref_warnings + [
        weight_note,
        "Odds ratio interpretation: OR > 1 = higher odds, OR < 1 = lower odds vs reference.",
        "Standard errors are model-based (not design-based); interpret accordingly.",
    ]
    if any(c in _SENTINEL_COLUMNS for c in all_cols):
        notes.append("Rows with -99 (skipped/refused) excluded from all ordinal columns.")

    model_type = (
        "Logistic Regression (Weighted GLM, Binomial/logit)"
        if use_weights else
        "Logistic Regression (Unweighted GLM, Binomial/logit)"
    )
    return json.dumps({
        "model_type": model_type,
        "outcome": outcome,
        "predictors_specified": predictors,
        "reference_levels_requested": reference_levels,
        "wave": wave,
        "n_observations": int(len(df)),
        "weighted_n": round(float(weights.sum()), 1),
        "model_fit": {
            "pseudo_r_squared_mcfadden": pseudo_r2,
            "log_likelihood": round(llf, 4),
            "null_log_likelihood": round(llnull, 4),
            "aic": round(float(model.aic), 2),
            "bic": round(float(model.bic), 2),
        },
        "coefficients": coefficients,
        "notes": notes,
    }, indent=2, default=str)


if __name__ == "__main__":
    asyncio.run(
        mcp.run_async(
            transport="streamable-http",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8080)),
        )
    )
