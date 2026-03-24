#!/usr/bin/env python3
"""
Remote MCP Server for CHIP50 Social Media Demographics Analysis
Deployed on Google Cloud Run with Streamable HTTP transport

Data: CHIP50 panel survey, waves 14-35, N=583,532 responses
Platform usage is binary (1=uses platform, 0=does not, NULL=not asked that wave)
"""

import os
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional

import pandas as pd
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

FULL_TABLE = f"`{GCP_PROJECT}.{DATASET_NAME}.{TABLE_NAME}`"

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
    """Build a WHERE clause fragment for wave filtering."""
    if not wave:
        return ""
    return f"AND wave = '{wave}'"


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
        ],
        "quick_start": [
            "1. Call introduce_mcp() to get this overview.",
            "2. Call get_available_variables() to see live dataset metadata.",
            "3. Use generate_marginals() to explore a single variable.",
            "4. Use generate_crosstab() to cross a platform with a demographic.",
            "5. Use get_platform_trends() / get_freq_trends() for time series.",
            "6. Use get_ordinal_distribution() / get_ordinal_crosstab() for frequency, trust, and attitude scales.",
            "7. Use get_platform_posting_summary() for a full profile of one platform.",
            "8. Use the _batch variants to run multiple queries in parallel.",
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
              STRING_AGG(DISTINCT wave ORDER BY wave) AS waves
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
                "weights": "All rates are survey-weighted using the 'weight' column.",
                "wave_coverage": "voted24 only from wave 34+; economy only waves 32/35+; sm_post_* variants only waves 27/28 and 33+.",
                "phq9_sensitivity": "PHQ-9 items are clinical mental health measures. Only aggregate statistics are returned.",
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
                "data": df.to_dict(orient="records"),
            }, indent=2, default=str)

    except Exception as e:
        logger.error(f"generate_marginals error: {e}")
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
              wave,
              COUNT(*)                                                 AS unweighted_n,
              ROUND(SUM(weight), 1)                                    AS weighted_n,
              ROUND(SUM({platform} * weight), 1)                       AS weighted_users,
              ROUND(SUM({platform} * weight) / SUM(weight) * 100, 2)  AS user_rate_pct
            FROM {FULL_TABLE}
            WHERE {platform} IS NOT NULL
              AND weight IS NOT NULL
              {demo_filter}
            GROUP BY wave
            ORDER BY CAST(wave AS FLOAT64)
        """)

        return json.dumps({
            "platform": platform,
            "demographic_filter": f"{demographic}={demographic_value}" if demographic else None,
            "data": df.to_dict(orient="records"),
        }, indent=2, default=str)

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

        return json.dumps({
            "column": column,
            "type": "ordinal_distribution",
            "wave_filter": wave or "all",
            "suppression_note": f"Cells with n<{MIN_CELL_SIZE} suppressed for privacy",
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

        return json.dumps({
            "column": column,
            "demographic": demographic,
            "wave_filter": wave or "all",
            "suppression_note": f"Cells with n<{MIN_CELL_SIZE} suppressed for privacy",
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
              wave,
              COUNT(*)                                                   AS unweighted_n,
              ROUND(SUM(weight), 1)                                      AS weighted_n,
              ROUND(SUM({freq_col} * weight) / SUM(weight), 3)          AS weighted_mean_freq
            FROM {FULL_TABLE}
            WHERE {freq_col} IS NOT NULL
              AND {freq_col} > 0
              AND weight IS NOT NULL
              {demo_filter}
            GROUP BY wave
            ORDER BY CAST(wave AS FLOAT64)
        """)

        return json.dumps({
            "platform": platform,
            "freq_column": freq_col,
            "demographic_filter": f"{demographic}={demographic_value}" if demographic else None,
            "scale_note": "Frequency scale 1–6 (1=never, 6=several times a day)",
            "data": df.to_dict(orient="records"),
        }, indent=2, default=str)

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

    results: dict = {"platform": platform, "wave_filter": wave or "all"}

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


if __name__ == "__main__":
    asyncio.run(
        mcp.run_async(
            transport="streamable-http",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8080)),
        )
    )
