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
MIN_CELL_SIZE = int(os.getenv("MIN_CELL_SIZE", "10"))

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
    )

# ── MCP server ──────────────────────────────────────────────────────────────

mcp = FastMCP("social-media-demographics", auth=auth)


@mcp.tool()
async def introduce_mcp() -> str:
    """Get a quick introduction to this MCP server, its tools, and how to use them.

    Call this first to understand what data is available and how to query it.
    """
    return json.dumps({
        "name": "CHIP50 Social Media Demographics MCP",
        "description": (
            "This MCP server provides access to CHIP50 panel survey data covering social media "
            "usage across waves 14–35 (583,532 responses). You can analyze platform adoption "
            "rates broken down by demographics, track trends over time, and run batch queries."
        ),
        "dataset": {
            "waves": "14–35",
            "total_responses": 583532,
            "demographics": DEMOGRAPHIC_COLUMNS,
            "platforms": [c.replace("use_", "") for c in PLATFORM_COLUMNS],
            "note": (
                "Platform usage is binary (1=uses, 0=does not). "
                "Cells with n<10 are suppressed for privacy. "
                "Some platforms (truth, mastodon, post, threads, bluesky) were added mid-panel "
                "and have NULLs in earlier waves."
            ),
        },
        "tools": [
            {
                "name": "introduce_mcp",
                "purpose": "This tool — get an overview of the MCP and all available tools.",
                "example": "introduce_mcp()",
            },
            {
                "name": "get_available_variables",
                "purpose": "Discover available demographics, platforms, and wave range from live data.",
                "example": "get_available_variables()",
            },
            {
                "name": "generate_marginals",
                "purpose": "Distribution for a single variable. Demographics return count/% per category; platforms return overall adoption rate.",
                "example": 'generate_marginals(variable="age_cat_8")  # or variable="use_tiktok"',
            },
            {
                "name": "generate_marginals_batch",
                "purpose": "Run generate_marginals for multiple variables in parallel — efficient for profiling several variables at once.",
                "example": 'generate_marginals_batch(variables=["age_cat_8", "gender", "use_tiktok"])',
            },
            {
                "name": "generate_crosstab",
                "purpose": "Platform adoption rate broken down by one demographic — e.g. TikTok usage by age group.",
                "example": 'generate_crosstab(platform="use_tiktok", demographic="age_cat_8")',
            },
            {
                "name": "generate_crosstab_batch",
                "purpose": "Run generate_crosstab for one platform across multiple demographics in parallel.",
                "example": 'generate_crosstab_batch(platform="use_tiktok", demographics=["age_cat_8", "gender", "party3"])',
            },
            {
                "name": "get_platform_trends",
                "purpose": "Platform adoption rate across waves (time series). Optionally filter to a specific demographic group.",
                "example": 'get_platform_trends(platform="use_twitter")  # or add demographic="party3", demographic_value="Republican"',
            },
        ],
        "quick_start": [
            "1. Call introduce_mcp() to get this overview.",
            "2. Call get_available_variables() to see live dataset metadata.",
            "3. Use generate_marginals() to explore a single variable.",
            "4. Use generate_crosstab() to cross a platform with a demographic.",
            "5. Use get_platform_trends() to see how usage changed over time.",
            "6. Use the _batch variants to run multiple queries in parallel.",
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
            "platforms": PLATFORM_COLUMNS,
            "late_platforms": list(LATE_PLATFORMS),
            "total_rows": int(row["total_rows"]),
            "unique_respondents": int(row["unique_respondents"]),
            "wave_count": int(row["wave_count"]),
            "waves": row["waves"],
            "note": (
                "Platform usage is binary (1=uses, 0=does not). "
                "late_platforms have NULL in earlier waves."
            )
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

    Returns user_rate_pct (% of respondents using the platform) per demographic group,
    with cell suppression for groups with n < MIN_CELL_SIZE.

    Args:
        platform:    Column name, e.g. "use_twitter", "use_tiktok"
        demographic: Column name, e.g. "age_cat_8", "party3", "gender"
        wave:        Optional wave number to filter to (e.g. "35"). Omit for all waves.
    """
    if platform not in PLATFORM_COLUMNS:
        raise ValueError(f"Unknown platform '{platform}'. Choose from: {PLATFORM_COLUMNS}")
    if demographic not in DEMOGRAPHIC_COLUMNS:
        raise ValueError(f"Unknown demographic '{demographic}'. Choose from: {DEMOGRAPHIC_COLUMNS}")

    try:
        df = run_query(f"""
            SELECT
              {demographic}                  AS demographic_value,
              COUNT(*)                       AS total,
              SUM({platform})                AS users,
              COUNT(*) - SUM({platform})     AS non_users,
              ROUND(SUM({platform}) / COUNT(*) * 100, 2) AS user_rate_pct,
              CASE WHEN COUNT(*) < {MIN_CELL_SIZE} THEN TRUE ELSE FALSE END AS suppressed
            FROM {FULL_TABLE}
            WHERE {platform} IS NOT NULL
              AND {demographic} IS NOT NULL
              {wave_clause(wave)}
            GROUP BY {demographic}
            ORDER BY {demographic}
        """)

        # Apply suppression
        df.loc[df["suppressed"], ["total", "users", "non_users", "user_rate_pct"]] = None

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
    if variable not in DEMOGRAPHIC_COLUMNS and variable not in PLATFORM_COLUMNS:
        raise ValueError(
            f"Unknown variable '{variable}'. "
            f"Choose from demographics: {DEMOGRAPHIC_COLUMNS} "
            f"or platforms: {PLATFORM_COLUMNS}"
        )

    try:
        if variable in PLATFORM_COLUMNS:
            # Platform: return overall adoption rate
            df = run_query(f"""
                SELECT
                  '{variable}'                              AS platform,
                  COUNT(*)                                  AS total_responses,
                  SUM({variable})                           AS users,
                  COUNT(*) - SUM({variable})                AS non_users,
                  ROUND(SUM({variable}) / COUNT(*) * 100, 2) AS user_rate_pct
                FROM {FULL_TABLE}
                WHERE {variable} IS NOT NULL
                  {wave_clause(wave)}
            """)
            return json.dumps({
                "variable": variable,
                "type": "platform",
                "wave_filter": wave or "all",
                "data": df.to_dict(orient="records"),
            }, indent=2, default=str)

        else:
            # Demographic: category distribution
            df = run_query(f"""
                SELECT
                  {variable}  AS value,
                  COUNT(*)    AS n,
                  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS pct,
                  CASE WHEN COUNT(*) < {MIN_CELL_SIZE} THEN TRUE ELSE FALSE END AS suppressed
                FROM {FULL_TABLE}
                WHERE {variable} IS NOT NULL
                  {wave_clause(wave)}
                GROUP BY {variable}
                ORDER BY {variable}
            """)

            df.loc[df["suppressed"], ["n", "pct"]] = None

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
              COUNT(*)   AS total_responses,
              SUM({platform})  AS users,
              ROUND(SUM({platform}) / COUNT(*) * 100, 2) AS user_rate_pct
            FROM {FULL_TABLE}
            WHERE {platform} IS NOT NULL
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


if __name__ == "__main__":
    asyncio.run(
        mcp.run_async(
            transport="streamable-http",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8080)),
        )
    )
