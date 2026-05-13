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
import time
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm
from google.cloud import bigquery
from google.cloud import storage as gcs

from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider
from fastmcp.server.auth.oauth_proxy.models import ProxyDCRClient
from key_value.aio.stores.firestore import FirestoreStore

# reportlab — optional; required only for generate_pdf_report
try:
    from reportlab.lib import colors as _rl_colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import LETTER as _LETTER
    from reportlab.lib.styles import ParagraphStyle as _PS
    from reportlab.lib.units import inch as _inch
    from reportlab.platypus import (
        SimpleDocTemplate as _SimpleDocTemplate,
        Paragraph as _Paragraph,
        Spacer as _Spacer,
        Table as _Table,
        TableStyle as _TableStyle,
        PageBreak as _PageBreak,
        KeepTogether as _KeepTogether,
        HRFlowable as _HRFlowable,
        Image as _Image,
    )
    _REPORTLAB_AVAILABLE = True
except ImportError:
    _REPORTLAB_AVAILABLE = False

_LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chip50.png")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
GCP_PROJECT   = os.getenv("GCP_PROJECT", "chip50")
DATASET_NAME  = os.getenv("DATASET_NAME", "social_media_demographics")
TABLE_NAME    = os.getenv("TABLE_NAME", "panel_data_indexed")
MIN_CELL_SIZE = int(os.getenv("MIN_CELL_SIZE", "10"))
REPORTS_BUCKET = os.getenv("REPORTS_BUCKET", "chip50-reports")

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

# Race/ethnicity boolean flags (one-hot; 1=yes, 0=no; replaces race_cat_5)
RACE_BOOLEAN_COLUMNS = [
    "race_asian",
    "race_black",
    "race_hisp",
    "race_natam",
    "race_white",
    "race_other",
]

# Ozempic / GLP-1 questions (wave 35+; ordinal; -99 = skipped/refused)
# ozempic_wt is a subsample weight, not an analysis variable — excluded here.
OZEMPIC_COLUMNS = [
    "ozempic",         # GLP-1/Ozempic status: 1=currently taking, 2=previously took/stopped, 3=considering/interested, 4=not taking/no interest, 5=don't know/unsure
    "ozempic_why",     # reason for use: 1=weight loss, 4=diabetes, 5=other
    "ozempic_time_1",  # months using (0–10+, continuous)
    "ozempic_time_2",  # months since stopped (0–11+, continuous)
]

# Ozempic columns appropriate as OLS regression outcomes/predictors.
# ozempic and ozempic_why are excluded: their numeric codes have no linear
# interpretation (ozempic: 1=taking→5=don't know; ozempic_why: non-contiguous codes 1,4,5).
# Use ozempic_binary (derived) for logistic regression instead.
OZEMPIC_REGRESSION_COLUMNS = ["ozempic_time_1", "ozempic_time_2"]

# Categorical ordinal columns where per-category distribution (not mean) is meaningful.
# Use get_categorical_crosstab() instead of get_ordinal_crosstab() for these.
CATEGORICAL_ORDINAL_COLUMNS = ["ozempic", "ozempic_why"]

# All ordinal column groups (exclude -99 sentinel in queries with col > 0)
ALL_ORDINAL_COLUMNS = (
    ATTITUDINAL_COLUMNS + FREQ_COLUMNS + TRUST_COLUMNS +
    POL_POST_COLUMNS + POL_TRUST_COLUMNS + PHQ9_COLUMNS + OZEMPIC_COLUMNS
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
    + OZEMPIC_REGRESSION_COLUMNS
    + SM_POST_COLUMNS
    + POL_NEWS_COLUMNS
    + RACE_BOOLEAN_COLUMNS
)

# Binary-outcome columns (valid for logistic regression)
_BINARY_COLUMNS: set[str] = set(PLATFORM_COLUMNS + SM_POST_COLUMNS + POL_NEWS_COLUMNS)

# Derived columns: computed on the fly in SQL from a source column.
# Each entry: { "sql": <expression>, "source": <real column for NULL/sentinel checks> }
_DERIVED_COLUMNS: dict[str, dict] = {
    "ozempic_binary": {
        "sql": "CASE WHEN ozempic IN (1, 2) THEN 1 ELSE 0 END",
        "source": "ozempic",  # real column — used for NOT NULL + sentinel (>0) filtering
        "description": "Binary GLP-1/Ozempic use: 1 = currently taking or previously took, 0 = all other categories (wave 35 only)",
    },
}

# Register derived columns as valid regression columns and binary outcomes
_ALL_REGRESSION_COLUMNS.update(_DERIVED_COLUMNS.keys())
_BINARY_COLUMNS.update(_DERIVED_COLUMNS.keys())

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

# Compact note embedded in data responses instead of the full COLUMN_DEFINITIONS block.
# Full definitions are available via introduce_mcp() and get_available_variables().
NOTE_WEIGHTED = (
    "All rates/means/pct are WEIGHTED (population-representative). "
    "unweighted_n is raw headcount for reliability checks only — never use it to compute percentages."
)

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

OZEMPIC_SCALE_LABELS = {
    1: "Currently taking",
    2: "Previously took / stopped",
    3: "Considering / interested",
    4: "Not taking / no interest",
    5: "Don't know / unsure",
}

OZEMPIC_WHY_SCALE_LABELS = {
    1: "Weight loss",
    4: "Diabetes / blood sugar",
    5: "Other reason",
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


class AutoRegisteringGoogleProvider(GoogleProvider):
    """GoogleProvider that auto-registers unknown client IDs instead of erroring.

    When a client presents a cached client_id that isn't in storage (e.g. after
    a server migration from MemoryStore to Firestore, or after any future incident
    that wipes OAuth state), the client is silently re-registered and the flow
    completes normally. The registration is persisted to Firestore so it only
    happens once per client.
    """

    async def get_client(self, client_id: str):
        client = await super().get_client(client_id)
        if client is None:
            logger.info("Auto-registering unknown client_id=%s", client_id)
            proxy_client = ProxyDCRClient(
                client_id=client_id,
                redirect_uris=[],
                grant_types=["authorization_code", "refresh_token"],
                response_types=["code"],
                token_endpoint_auth_method="none",
                scope="openid",
                allowed_redirect_uri_patterns=self._allowed_client_redirect_uris,
            )
            await self._client_store.put(key=client_id, value=proxy_client)
            return proxy_client
        return client


# ── Auth (toggle with DISABLE_AUTH env var on Cloud Run) ─────────────────────

if os.getenv("DISABLE_AUTH"):
    auth = None
else:
    auth = AutoRegisteringGoogleProvider(
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        base_url=os.getenv("SERVICE_URL", "http://localhost:8080"),
        allowed_client_redirect_uris=[
            "https://claude.ai/api/mcp/auth_callback",
            "http://localhost:*",
            "http://127.0.0.1:*",
        ],
        client_storage=FirestoreStore(project=GCP_PROJECT, default_collection="mcp_oauth"),
        require_authorization_consent=False,
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
            "ozempic_columns": OZEMPIC_COLUMNS,
            "race_boolean_columns": RACE_BOOLEAN_COLUMNS,
            "notes": {
                "platform_usage": "Binary (1=uses, 0=does not). late_platforms (truth, mastodon, post, threads, bluesky) have NULLs in earlier waves.",
                "ordinal_sentinel": "All ordinal columns use -99 for skipped/refused — excluded automatically from all queries.",
                "suppression": f"Cells with n<{MIN_CELL_SIZE} are suppressed for respondent privacy.",
                "phq9_sensitivity": "PHQ-9 items are clinical mental health screening measures. Only population-level aggregates are returned.",
                "ozempic_coverage": "Ozempic columns only available in wave 35 (not fielded in later waves). Always specify wave='35' when querying ozempic variables.",
                "ozempic_regression": "ozempic, ozempic_why, ozempic_time_1, ozempic_time_2 are valid regression outcomes/predictors.",
                "race_booleans": "race_asian/black/hisp/natam/white/other are binary (0/1) flags replacing race_cat_5. Valid as regression predictors and marginals (returns adoption rate, like platform columns).",
                "wave_coverage": "voted24 only from wave 34+; economy only waves 32/35+; sm_post_* variants only waves 27/28 and 33+; ozempic only wave 35.",
            },
            "problematic_waves": {
                "35.1": (
                    "Small sample wave. race_cat_5 (race/ethnicity) breakdowns are unavailable — "
                    "all cells fall below the minimum cell size threshold and are suppressed. "
                    "Use aggregate-level queries for this wave; demographic crosstabs by race may return no data."
                ),
            },
            "column_definitions": COLUMN_DEFINITIONS,
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
                "purpose": "Platform adoption rate broken down by ONE demographic or attitudinal variable. Use this for any question like 'TikTok use by race' or 'Facebook adoption by age'. This is the primary single-demographic breakdown tool.",
                "example": 'generate_crosstab(platform="use_tiktok", demographic="race_cat_5")',
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
                "name": "generate_crosstab_multi",
                "purpose": (
                    "Variable broken down by the intersection of 2+ demographic dimensions — "
                    "returns one row per unique cell for 2D heatmaps and interaction tables. "
                    "Binary variables (platform use, race booleans) → adoption rate per cell. "
                    "Ordinal variables (freq_*, trust_*, ideology, etc.) → weighted mean per cell. "
                    "Use instead of running a regression just to get subgroup cell estimates."
                ),
                "example": 'generate_crosstab_multi(variable="use_tiktok", demographics=["gender", "party3"])',
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
                "name": "get_categorical_crosstab",
                "purpose": (
                    "Weighted % distribution of a categorical variable broken down by a demographic. "
                    "Use for 'ozempic' and 'ozempic_why' — columns where response categories are nominal "
                    "and a mean is not meaningful. Returns pct_within_demo for every response category "
                    "within each demographic group. Example: share currently taking Ozempic by party."
                ),
                "example": 'get_categorical_crosstab(column="ozempic", demographic="party3", wave="35")',
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
                "name": "generate_marginals_by_wave",
                "purpose": (
                    "Distribution of ONE variable across ALL waves in a single query. "
                    "Use instead of calling generate_marginals() 37 times. "
                    "Works for demographics, platforms, ordinal columns, and binary columns."
                ),
                "example": 'generate_marginals_by_wave(variable="race_cat_5")',
            },
            {
                "name": "generate_crosstab_by_wave",
                "purpose": (
                    "Platform adoption rate by demographic group across ALL waves in a single query. "
                    "Use instead of calling generate_crosstab() once per wave. "
                    "Returns the full wave × demographic matrix."
                ),
                "example": 'generate_crosstab_by_wave(platform="use_twitter", demographic="party3")',
            },
            {
                "name": "get_wave_metadata",
                "purpose": (
                    "Wave-level metadata: respondent counts, field dates, field-period length, "
                    "wave size category, and per-wave flags showing which platforms and variable "
                    "groups (PHQ-9, institutional trust, ideology, etc.) were actually fielded. "
                    "Call without arguments for a panel-wide coverage overview, or pass a wave "
                    "number to inspect a specific wave before querying it."
                ),
                "example": (
                    'get_wave_metadata()            # all waves\n'
                    'get_wave_metadata(wave="37")   # single wave detail'
                ),
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
            {
                "name": "generate_pdf_report",
                "purpose": (
                    "Generate a publication-quality PDF report from CHIP50 analysis results. "
                    "Produces a title page, optional abstract, auto-generated methodology section "
                    "(weighting, cell suppression, regression conventions), and user-defined sections "
                    "with numbered tables following academic style. "
                    "Returns the PDF as a base64-encoded string for local saving."
                ),
                "example": (
                    'generate_pdf_report(\n'
                    '  title="Social Media Platform Adoption: Wave 37",\n'
                    '  subtitle="Demographic Breakdowns and Trends",\n'
                    '  authors="CHIP50 Research Team",\n'
                    '  abstract="This report summarizes platform adoption rates...\\n\\nKey findings...",\n'
                    '  sections=[\n'
                    '    {\n'
                    '      "heading": "Facebook Adoption by Party",\n'
                    '      "content": "Adoption rates vary substantially by party affiliation.",\n'
                    '      "tables": [\n'
                    '        {\n'
                    '          "title": "Facebook Adoption Rate by Party Affiliation",\n'
                    '          "column_headers": ["Party", "Adoption Rate (%)", "n (unweighted)"],\n'
                    '          "rows": [["Democrat","72.3","1245"],["Republican","68.1","1102"]],\n'
                    '          "notes": "Rates are population-weighted. Cells with n<10 are suppressed."\n'
                    '        }\n'
                    '      ]\n'
                    '    }\n'
                    '  ]\n'
                    ')'
                ),
            },
        ],
        "quick_start": [
            "1. Call introduce_mcp() to get this overview.",
            "2. Call get_available_variables() to see live dataset metadata.",
            "3. Use generate_marginals() to explore a single variable.",
            "4. Use generate_crosstab() to cross a platform with a demographic. Use generate_crosstab_filtered() to add demographic sub-population filters (e.g. gender × rural).",
            "5. Use get_wave_metadata() to see respondent counts, field dates, and which questions were asked per wave.",
            "5b. Use get_platform_trends() / get_freq_trends() for platform adoption/frequency time series.",
            "5c. Use generate_marginals_by_wave() to get a variable's distribution across ALL waves in one call (e.g. race_cat_5 per wave). Use generate_crosstab_by_wave() for platform × demographic across all waves. Both replace looping through 37 waves.",
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
            "ozempic_columns": OZEMPIC_COLUMNS,
            "race_boolean_columns": RACE_BOOLEAN_COLUMNS,
            "derived_columns": {k: v["description"] for k, v in _DERIVED_COLUMNS.items()},
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
                "wave_coverage": "voted24 only from wave 34+; economy only waves 32/35+; sm_post_* variants only waves 27/28 and 33+; ozempic only wave 35.",
                "race_booleans": "race_asian/black/hisp/natam/white/other are binary (0/1) flags replacing race_cat_5. Valid as regression predictors and in marginals/marginals_by_wave (returns adoption rate, like platform columns).",
                "ozempic_regression": "ozempic_binary (derived: currently taking or previously took vs. all others) is valid for logistic regression (wave 35 only). ozempic/ozempic_why/ozempic_time_* are valid OLS outcomes. Always use wave='35'.",
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


async def _generate_crosstab_impl(
    platform: str,
    demographic: str,
    wave: Optional[str] = None,
) -> str:
    if platform not in PLATFORM_COLUMNS:
        raise ValueError(f"Unknown platform '{platform}'. Choose from: {PLATFORM_COLUMNS}")
    if demographic not in _ALL_REGRESSION_COLUMNS:
        raise ValueError(f"Unknown column '{demographic}'. Call get_available_variables() to see valid names.")

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
            "note": NOTE_WEIGHTED,
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
async def generate_crosstab(
    platform: str,
    demographic: str,
    wave: Optional[str] = None,
) -> str:
    """Platform adoption rate broken down by ONE demographic variable. Use this for any
    single-demographic breakdown: 'TikTok use by race', 'Facebook by age', 'Twitter by party', etc.
    This is the primary tool for platform × demographic analysis.

    Returns survey-weighted user_rate_pct (population-representative % using the platform)
    per demographic group, with cell suppression for groups with unweighted n < MIN_CELL_SIZE.
    All rates and counts use the respondent survey weight for population-representative estimates.

    Args:
        platform:    Column name, e.g. "use_twitter", "use_tiktok"
        demographic: Column name, e.g. "age_cat_8", "party3", "gender", "race_cat_5"
        wave:        Optional wave number to filter to (e.g. "35"). Omit for all waves.
    """
    return await _generate_crosstab_impl(platform, demographic, wave)


async def _generate_marginals_impl(
    variable: str,
    wave: Optional[str] = None,
) -> str:
    all_valid = (
        DEMOGRAPHIC_COLUMNS + ATTITUDINAL_COLUMNS + PLATFORM_COLUMNS +
        ALL_ORDINAL_COLUMNS + ALL_BINARY_COLUMNS + RACE_BOOLEAN_COLUMNS
    )
    if variable not in all_valid:
        raise ValueError(
            f"Unknown variable '{variable}'. "
            f"Choose from demographics: {DEMOGRAPHIC_COLUMNS}, "
            f"attitudinal: {ATTITUDINAL_COLUMNS}, "
            f"platforms: {PLATFORM_COLUMNS}, "
            f"ordinal: {ALL_ORDINAL_COLUMNS}, "
            f"binary: {ALL_BINARY_COLUMNS}, "
            f"or race booleans: {RACE_BOOLEAN_COLUMNS}"
        )

    # Binary columns: use_* and sm_post_*/pol_news2_* and race booleans — compute adoption rate
    is_binary = variable in PLATFORM_COLUMNS or variable in ALL_BINARY_COLUMNS or variable in RACE_BOOLEAN_COLUMNS

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
                "note": NOTE_WEIGHTED,
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
                "note": NOTE_WEIGHTED,
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
    return await _generate_marginals_impl(variable, wave)


@mcp.tool()
async def generate_marginals_by_wave(variable: str) -> str:
    """Distribution of a single variable broken down by wave — one query, all waves.

    Use this instead of calling generate_marginals() 37 times.
    Returns the weighted distribution of the variable for every wave in a single call.

    For demographic/categorical variables: weighted % per category per wave.
    For platform (binary) variables: weighted adoption rate per wave.

    Args:
        variable: Any demographic, platform, or ordinal column —
                  e.g. "race_cat_5", "use_tiktok", "ideology", "phq9_1"
    """
    all_valid = (
        DEMOGRAPHIC_COLUMNS + ATTITUDINAL_COLUMNS + PLATFORM_COLUMNS +
        ALL_ORDINAL_COLUMNS + ALL_BINARY_COLUMNS + RACE_BOOLEAN_COLUMNS
    )
    if variable not in all_valid:
        raise ValueError(
            f"Unknown variable '{variable}'. Call get_available_variables() to see valid names."
        )

    is_binary = variable in PLATFORM_COLUMNS or variable in ALL_BINARY_COLUMNS or variable in RACE_BOOLEAN_COLUMNS

    try:
        if is_binary:
            df = run_query(f"""
                SELECT
                  CAST(t.wave AS FLOAT64)                                       AS wave,
                  wd.midpoint_date,
                  COUNT(*)                                                       AS unweighted_n,
                  ROUND(SUM(t.{variable} * t.weight) / SUM(t.weight) * 100, 2)   AS user_rate_pct
                FROM {FULL_TABLE} t
                LEFT JOIN {WAVE_DATES_TABLE} wd ON CAST(t.wave AS FLOAT64) = wd.wave_num
                WHERE t.{variable} IS NOT NULL
                  AND t.weight IS NOT NULL
                GROUP BY CAST(t.wave AS FLOAT64), wd.midpoint_date
                ORDER BY CAST(t.wave AS FLOAT64)
            """)

            return json.dumps({
                "variable": variable,
                "type": "platform_by_wave",
                "note": NOTE_WEIGHTED,
                "interpretation_note": (
                    "unweighted_n = raw respondent headcount per wave (reliability check only). "
                    "user_rate_pct = WEIGHTED, population-representative adoption rate per wave."
                ),
                "data": df.to_dict(orient="records"),
            }, indent=2, default=str)

        else:
            sentinel_filter = f"AND t.{variable} > 0" if variable in ALL_ORDINAL_COLUMNS else ""
            df = run_query(f"""
                WITH agg AS (
                  SELECT
                    CAST(t.wave AS FLOAT64)                                          AS wave,
                    wd.midpoint_date,
                    t.{variable}                                                      AS value,
                    COUNT(*)                                                          AS unweighted_n,
                    ROUND(SUM(t.weight), 1)                                           AS weighted_n,
                    CASE WHEN COUNT(*) < {MIN_CELL_SIZE} THEN TRUE ELSE FALSE END     AS suppressed
                  FROM {FULL_TABLE} t
                  LEFT JOIN {WAVE_DATES_TABLE} wd ON CAST(t.wave AS FLOAT64) = wd.wave_num
                  WHERE t.{variable} IS NOT NULL
                    AND t.weight IS NOT NULL
                    {sentinel_filter}
                  GROUP BY CAST(t.wave AS FLOAT64), wd.midpoint_date, t.{variable}
                )
                SELECT
                  wave,
                  midpoint_date,
                  value,
                  unweighted_n,
                  weighted_n,
                  ROUND(weighted_n * 100.0 / SUM(weighted_n) OVER (PARTITION BY CAST(wave AS STRING)), 2) AS pct,
                  suppressed
                FROM agg
                ORDER BY wave, value
            """)

            df.loc[df["suppressed"], ["weighted_n", "pct"]] = None

            scale_labels = None
            if variable.startswith("freq_"):
                scale_labels = FREQ_SCALE_LABELS
            elif variable.startswith("sm_trust_") or variable.startswith("pol_trust_"):
                scale_labels = TRUST_SCALE_LABELS
            elif variable == "ideology":
                scale_labels = IDEOLOGY_SCALE_LABELS

            return json.dumps({
                "variable": variable,
                "type": "demographic_by_wave",
                "suppression_note": f"Cells with n<{MIN_CELL_SIZE} suppressed for privacy",
                "scale_labels": scale_labels,
                "note": NOTE_WEIGHTED,
                "interpretation_note": (
                    "unweighted_n = raw respondent headcount per wave/category (reliability check only). "
                    "pct = WEIGHTED, population-representative percentage within each wave. "
                    "pct sums to 100 within each wave, not across waves."
                ),
                "data": df.to_dict(orient="records"),
            }, indent=2, default=str)

    except Exception as e:
        logger.error(f"generate_marginals_by_wave error: {e}")
        raise


@mcp.tool()
async def generate_crosstab_by_wave(
    platform: str,
    demographic: str,
) -> str:
    """Platform adoption rate by demographic group, across all waves — one query.

    Use this instead of calling generate_crosstab() once per wave.
    Returns the full wave × demographic breakdown in a single BigQuery call,
    enabling trend analysis broken down by demographic group.

    Args:
        platform:    Platform column, e.g. "use_twitter", "use_tiktok"
        demographic: Demographic column, e.g. "race_cat_5", "party3", "age_cat_8"
    """
    if platform not in PLATFORM_COLUMNS:
        raise ValueError(f"Unknown platform '{platform}'. Choose from: {PLATFORM_COLUMNS}")
    if demographic not in _ALL_REGRESSION_COLUMNS:
        raise ValueError(f"Unknown column '{demographic}'. Call get_available_variables() to see valid names.")

    try:
        df = run_query(f"""
            SELECT
              CAST(t.wave AS FLOAT64)                                                AS wave,
              wd.midpoint_date,
              t.{demographic}                                                         AS demographic_value,
              COUNT(*)                                                               AS unweighted_n,
              ROUND(SUM(t.{platform} * t.weight) / SUM(t.weight) * 100, 2)           AS user_rate_pct,
              CASE WHEN COUNT(*) < {MIN_CELL_SIZE} THEN TRUE ELSE FALSE END           AS suppressed
            FROM {FULL_TABLE} t
            LEFT JOIN {WAVE_DATES_TABLE} wd ON CAST(t.wave AS FLOAT64) = wd.wave_num
            WHERE t.{platform} IS NOT NULL
              AND t.{demographic} IS NOT NULL
              AND t.weight IS NOT NULL
              {"AND t." + demographic + " > 0" if demographic in ALL_ORDINAL_COLUMNS else ""}
            GROUP BY CAST(t.wave AS FLOAT64), wd.midpoint_date, t.{demographic}
            ORDER BY CAST(t.wave AS FLOAT64), t.{demographic}
        """)

        df.loc[df["suppressed"], ["user_rate_pct"]] = None

        # Detect wave gaps (same logic as get_platform_trends)
        all_waves_df = run_query(f"""
            SELECT DISTINCT CAST(wave AS FLOAT64) AS wave_num FROM {FULL_TABLE} ORDER BY wave_num
        """)
        all_wave_set  = {int(w) for w in all_waves_df["wave_num"].tolist()}
        data_wave_set = {int(float(r["wave"])) for r in df.to_dict(orient="records")}
        missing_waves = sorted(all_wave_set - data_wave_set)

        response: dict = {
            "platform": platform,
            "demographic": demographic,
            "suppression_note": f"Cells with n<{MIN_CELL_SIZE} suppressed for privacy",
            "note": NOTE_WEIGHTED,
            "interpretation_note": (
                "unweighted_n = raw respondent headcount per wave/group (reliability check only). "
                "user_rate_pct = WEIGHTED, population-representative adoption rate. "
                "Each row is one wave × demographic_value combination."
            ),
            "data": df.to_dict(orient="records"),
        }
        if missing_waves:
            response["missing_waves"] = missing_waves
            response["gap_warning"] = (
                f"Waves {missing_waves} exist in the panel but have no data for '{platform}'. "
                "Do NOT interpolate across these gaps."
            )
        key_events = PLATFORM_KEY_EVENTS.get(platform, [])
        if key_events:
            response["key_events"] = key_events
            response["annotation_instruction"] = (
                "REQUIRED: annotate trend charts with vertical dashed lines at waves in 'key_events'."
            )

        return json.dumps(response, indent=2, default=str)

    except Exception as e:
        logger.error(f"generate_crosstab_by_wave error: {e}")
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

    if demographic not in _ALL_REGRESSION_COLUMNS:
        raise ValueError(f"Unknown column '{demographic}'. Call get_available_variables() to see valid names.")

    if not filters:
        raise ValueError("filters must contain at least one {column: value} pair. "
                         "Use generate_crosstab() if no filtering is needed.")

    # Validate each filter column and build safe SQL clauses
    filter_clauses = []
    for col, val in filters.items():
        if col not in _ALL_REGRESSION_COLUMNS:
            raise ValueError(
                f"Unknown filter column '{col}'. Call get_available_variables() to see valid names."
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
            "note": NOTE_WEIGHTED,
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
    tasks = [_generate_crosstab_impl(platform, d, wave) for d in demographics]
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
async def generate_crosstab_multi(
    variable: str,
    demographics: List[str],
    wave: Optional[str] = None,
) -> str:
    """Variable broken down by the intersection of multiple demographic dimensions.

    Returns one row per unique combination of all demographics. Use this for 2D
    heatmaps and interaction tables that require more than one grouping variable.

    For binary variables (platform use, race booleans): returns weighted adoption
    rate per cell. For ordinal variables (freq_*, trust_*, ideology, etc.): returns
    weighted mean per cell. This replaces running a regression just to get cell estimates.

    Examples:
        generate_crosstab_multi(variable="use_tiktok", demographics=["gender", "party3"])
        → TikTok adoption rate for each gender × party combination.

        generate_crosstab_multi(variable="freq_facebook", demographics=["age_cat_8", "gender"])
        → Mean Facebook usage frequency for each age × gender cell.

    Cell counts fall quickly with more dimensions. Keep to 2–3 demographics to avoid
    excessive suppression. Cells with unweighted n < MIN_CELL_SIZE are suppressed.

    Args:
        variable:     The column to measure. Binary platform/race columns → adoption
                      rate. Ordinal columns → weighted mean.
        demographics: Two or more grouping columns, e.g. ["gender", "party3"].
        wave:         Optional wave number to filter to. Omit for all waves.
    """
    valid_variables = set(PLATFORM_COLUMNS + RACE_BOOLEAN_COLUMNS + ALL_ORDINAL_COLUMNS)
    if variable not in valid_variables:
        raise ValueError(
            f"Unknown variable '{variable}'. Must be a platform (use_*), race boolean, "
            f"or ordinal column. Call get_available_variables() to see valid names."
        )
    if len(demographics) < 2:
        raise ValueError(
            "demographics must contain at least 2 columns. "
            "Use generate_crosstab() or get_ordinal_crosstab() for a single grouping variable."
        )
    invalid = [d for d in demographics if d not in _ALL_REGRESSION_COLUMNS]
    if invalid:
        raise ValueError(f"Unknown columns: {invalid}. Call get_available_variables() to see valid names.")
    if variable in demographics:
        raise ValueError(f"variable '{variable}' cannot also appear in demographics.")

    is_binary = variable in PLATFORM_COLUMNS or variable in RACE_BOOLEAN_COLUMNS
    is_ordinal = variable in ALL_ORDINAL_COLUMNS

    group_cols = ", ".join(demographics)
    select_cols = ",\n              ".join(demographics)
    null_filters = "\n              ".join(f"AND {d} IS NOT NULL" for d in demographics)
    sentinel_filters = "\n              ".join(
        f"AND {d} > 0" for d in demographics if d in _SENTINEL_COLUMNS
    )
    variable_sentinel = f"AND {variable} > 0" if is_ordinal else ""

    if is_binary:
        metric_select = (
            f"ROUND(SUM({variable} * weight), 1)                          AS weighted_users,\n"
            f"              ROUND((SUM(weight) - SUM({variable} * weight)), 1)          AS weighted_non_users,\n"
            f"              ROUND(SUM({variable} * weight) / SUM(weight) * 100, 2)      AS user_rate_pct,"
        )
        suppress_cols = ["weighted_n", "weighted_users", "weighted_non_users", "user_rate_pct"]
        result_type = "adoption_rate"
    else:  # ordinal → weighted mean
        metric_select = (
            f"ROUND(SUM({variable} * weight) / SUM(weight), 3)            AS weighted_mean,"
        )
        suppress_cols = ["weighted_n", "weighted_mean"]
        result_type = "weighted_mean"

    scale_labels = None
    if variable.startswith("freq_"):
        scale_labels = FREQ_SCALE_LABELS
    elif variable.startswith("sm_trust_") or variable.startswith("pol_trust_"):
        scale_labels = TRUST_SCALE_LABELS
    elif variable == "ideology":
        scale_labels = IDEOLOGY_SCALE_LABELS

    try:
        df = run_query(f"""
            SELECT
              {select_cols},
              COUNT(*)                                                    AS unweighted_n,
              ROUND(SUM(weight), 1)                                       AS weighted_n,
              {metric_select}
              CASE WHEN COUNT(*) < {MIN_CELL_SIZE} THEN TRUE ELSE FALSE END AS suppressed
            FROM {FULL_TABLE}
            WHERE {variable} IS NOT NULL
              AND weight IS NOT NULL
              {variable_sentinel}
              {null_filters}
              {sentinel_filters}
              {wave_clause(wave)}
            GROUP BY {group_cols}
            ORDER BY {group_cols}
        """)

        df.loc[df["suppressed"], suppress_cols] = None

        return json.dumps({
            "variable": variable,
            "result_type": result_type,
            "demographics": demographics,
            "wave_filter": wave or "all",
            "n_cells": int(len(df)),
            "n_suppressed": int(df["suppressed"].sum()),
            "suppression_note": f"Cells with n<{MIN_CELL_SIZE} suppressed for privacy",
            "scale_labels": scale_labels,
            "note": NOTE_WEIGHTED,
            "interpretation_note": (
                "Each row is one unique combination of all demographic variables. "
                + (
                    "user_rate_pct = WEIGHTED adoption rate for that subgroup intersection."
                    if is_binary else
                    "weighted_mean = WEIGHTED mean of the variable for that subgroup intersection."
                ) +
                " unweighted_n = raw respondent headcount (reliability check only)."
            ),
            "data": df.to_dict(orient="records"),
        }, indent=2, default=str)

    except Exception as e:
        logger.error(f"generate_crosstab_multi error: {e}")
        raise


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
    tasks = [_generate_marginals_impl(v, wave) for v in variables]
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
        if demographic not in _ALL_REGRESSION_COLUMNS:
            raise ValueError(f"Unknown column '{demographic}'. Call get_available_variables() to see valid names.")
        demo_filter = f"AND {demographic} = '{demographic_value}'"

    try:
        df = run_query(f"""
            SELECT
              t.wave,
              wd.midpoint_date,
              COUNT(*)                                                   AS unweighted_n,
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
            "note": NOTE_WEIGHTED,
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
            "note": NOTE_WEIGHTED,
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
    if demographic not in _ALL_REGRESSION_COLUMNS:
        raise ValueError(f"Unknown column '{demographic}'. Call get_available_variables() to see valid names.")

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
            "note": NOTE_WEIGHTED,
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
async def get_categorical_crosstab(
    column: str,
    demographic: str,
    wave: Optional[str] = None,
) -> str:
    """Weighted % distribution of a categorical variable broken down by a demographic group.

    Use this for columns where response categories are nominal/categorical rather than
    a true ordinal scale — specifically the ozempic status and ozempic_why columns.
    Returns the share of each response category within every demographic group,
    so you can answer questions like "What share of Republicans are currently taking Ozempic?"
    or "How does Ozempic consideration vary by age group?"

    Unlike get_ordinal_crosstab() (which returns a single weighted mean per group),
    this returns a full distribution: one row per demographic × response-category combination.

    Valid columns:
        "ozempic"      — GLP-1/Ozempic status (1–5 scale; available wave 35+)
        "ozempic_why"  — Primary reason for use (codes 1, 4, 5; available wave 35+,
                         only among current/past users)

    Args:
        column:      "ozempic" or "ozempic_why"
        demographic: Demographic or attitudinal column — e.g. "party3", "age_cat_8", "gender"
        wave:        Optional wave filter (e.g. "35"). Omit for all waves.
                     Note: ozempic data is only available from wave 35 onward.
    """
    if column not in CATEGORICAL_ORDINAL_COLUMNS:
        raise ValueError(
            f"Column '{column}' is not supported by get_categorical_crosstab(). "
            f"Valid columns: {CATEGORICAL_ORDINAL_COLUMNS}. "
            f"For other ordinal columns use get_ordinal_crosstab()."
        )
    if demographic not in _ALL_REGRESSION_COLUMNS:
        raise ValueError(f"Unknown column '{demographic}'. Call get_available_variables() to see valid names.")

    demo_sentinel = f"AND {demographic} > 0" if demographic in ALL_ORDINAL_COLUMNS else ""

    scale_labels = OZEMPIC_SCALE_LABELS if column == "ozempic" else OZEMPIC_WHY_SCALE_LABELS

    try:
        df = run_query(f"""
            SELECT
              {demographic}                                                             AS demographic_value,
              {column}                                                                  AS response_value,
              COUNT(*)                                                                  AS unweighted_n,
              ROUND(SUM(weight), 1)                                                     AS weighted_n,
              ROUND(
                SUM(weight) * 100.0
                / SUM(SUM(weight)) OVER (PARTITION BY {demographic}),
                2
              )                                                                         AS pct_within_demo,
              CASE WHEN COUNT(*) < {MIN_CELL_SIZE} THEN TRUE ELSE FALSE END            AS suppressed
            FROM {FULL_TABLE}
            WHERE {column} IS NOT NULL
              AND {column} > 0
              AND {demographic} IS NOT NULL
              AND weight IS NOT NULL
              {demo_sentinel}
              {wave_clause(wave)}
            GROUP BY {demographic}, {column}
            ORDER BY {demographic}, {column}
        """)

        df.loc[df["suppressed"], ["weighted_n", "pct_within_demo"]] = None

        # Attach human-readable response labels
        df["response_label"] = df["response_value"].map(scale_labels)

        return json.dumps({
            "column": column,
            "demographic": demographic,
            "wave_filter": wave or "all",
            "suppression_note": f"Cells with n<{MIN_CELL_SIZE} suppressed for privacy",
            "ozempic_coverage_note": "ozempic columns are only available from wave 35 onward.",
            "scale_labels": scale_labels,
            "note": NOTE_WEIGHTED,
            "interpretation_note": (
                "Each row is one demographic_value × response_value combination. "
                "pct_within_demo = WEIGHTED % of that demographic group giving this response — "
                "rows sum to ~100% within each demographic_value. "
                "unweighted_n = raw respondent headcount (reliability check only). "
                "Always label pct_within_demo as 'weighted %' when presenting to users."
            ),
            "data": df.to_dict(orient="records"),
        }, indent=2, default=str)

    except Exception as e:
        logger.error(f"get_categorical_crosstab error: {e}")
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
        if demographic not in _ALL_REGRESSION_COLUMNS:
            raise ValueError(f"Unknown column '{demographic}'. Call get_available_variables() to see valid names.")
        demo_filter = f"AND {demographic} = '{demographic_value}'"

    try:
        df = run_query(f"""
            SELECT
              t.wave,
              wd.midpoint_date,
              COUNT(*)                                                     AS unweighted_n,
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
            "note": NOTE_WEIGHTED,
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
        "note": NOTE_WEIGHTED,
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


@mcp.tool()
async def get_wave_metadata(wave: Optional[str] = None) -> str:
    """Wave-level metadata: respondent counts, field dates, and which questions were asked.

    Use this before querying a specific wave to understand what data is available,
    or call without arguments to get a panel-wide coverage overview.

    Returns per wave:
      - Unweighted and weighted respondent counts
      - Field start/end dates, midpoint date, and field-period length
      - Wave size category (full / medium / small)
      - Which of the 20 platforms were asked
      - Which variable groups were fielded (PHQ-9, institutional trust, ideology, etc.)

    Args:
        wave: Optional wave number (e.g. "37"). Omit to get all waves.
    """
    # Build WHERE — validate wave to prevent SQL injection
    where_parts = ["1=1"]
    if wave:
        try:
            float(wave)
        except ValueError:
            raise ValueError(f"Invalid wave '{wave}': must be numeric.")
        where_parts.append(f"CAST(t.wave AS FLOAT64) = {float(wave)}")
    where_sql = "WHERE " + " AND ".join(where_parts)

    try:
        df = run_query(f"""
            SELECT
              CAST(t.wave AS FLOAT64)              AS wave,
              wd.start_date,
              wd.end_date,
              wd.midpoint_date,
              wd.size                              AS wave_size_category,
              wd.n                                 AS official_n,
              COUNT(*)                             AS unweighted_n,
              ROUND(SUM(t.weight), 0)              AS weighted_n,

              -- ── Platform questions asked (NULL = not fielded this wave) ──
              COUNTIF(t.use_facebook  IS NOT NULL) AS n_facebook,
              COUNTIF(t.use_instagram IS NOT NULL) AS n_instagram,
              COUNTIF(t.use_youtube   IS NOT NULL) AS n_youtube,
              COUNTIF(t.use_twitter   IS NOT NULL) AS n_twitter,
              COUNTIF(t.use_tiktok    IS NOT NULL) AS n_tiktok,
              COUNTIF(t.use_snapchat  IS NOT NULL) AS n_snapchat,
              COUNTIF(t.use_linkedin  IS NOT NULL) AS n_linkedin,
              COUNTIF(t.use_reddit    IS NOT NULL) AS n_reddit,
              COUNTIF(t.use_whatsapp  IS NOT NULL) AS n_whatsapp,
              COUNTIF(t.use_messenger IS NOT NULL) AS n_messenger,
              COUNTIF(t.use_pinterest IS NOT NULL) AS n_pinterest,
              COUNTIF(t.use_tumblr    IS NOT NULL) AS n_tumblr,
              COUNTIF(t.use_gab       IS NOT NULL) AS n_gab,
              COUNTIF(t.use_parler    IS NOT NULL) AS n_parler,
              COUNTIF(t.use_4chan     IS NOT NULL) AS n_4chan,
              COUNTIF(t.use_truth     IS NOT NULL) AS n_truth,
              COUNTIF(t.use_mastodon  IS NOT NULL) AS n_mastodon,
              COUNTIF(t.use_threads   IS NOT NULL) AS n_threads,
              COUNTIF(t.use_bluesky   IS NOT NULL) AS n_bluesky,
              COUNTIF(t.use_post      IS NOT NULL) AS n_post,

              -- ── Variable group coverage (representative column per group) ──
              COUNTIF(t.freq_facebook IS NOT NULL
                AND t.freq_facebook > 0)                     AS n_freq,
              COUNTIF(t.sm_trust_facebook IS NOT NULL
                AND t.sm_trust_facebook > 0)                 AS n_trust,
              COUNTIF(t.sm_post_pol_facebook IS NOT NULL
                AND t.sm_post_pol_facebook > 0)              AS n_pol_post,
              COUNTIF(t.sm_post_facebook_1 IS NOT NULL)      AS n_posting_variants,
              COUNTIF(t.pol_news2_2 IS NOT NULL)             AS n_pol_news,
              COUNTIF(t.phq9_1 IS NOT NULL
                AND t.phq9_1 > 0)                            AS n_phq9,
              COUNTIF(t.pol_trust_science IS NOT NULL
                AND t.pol_trust_science > 0)                 AS n_pol_trust,
              COUNTIF(t.ideology IS NOT NULL
                AND t.ideology > 0)                          AS n_ideology,
              COUNTIF(t.economy IS NOT NULL
                AND t.economy > 0)                           AS n_economy,
              COUNTIF(t.voted20 IS NOT NULL
                AND t.voted20 > 0)                           AS n_voted20,
              COUNTIF(t.voted24 IS NOT NULL
                AND t.voted24 > 0)                           AS n_voted24,
              COUNTIF(t.trump_win IS NOT NULL
                AND t.trump_win > 0)                         AS n_trump_win,
              COUNTIF(t.conspiracy_1 IS NOT NULL
                AND t.conspiracy_1 > 0)                      AS n_conspiracy,
              COUNTIF(t.ozempic IS NOT NULL
                AND t.ozempic > 0)                           AS n_ozempic

            FROM {FULL_TABLE} t
            LEFT JOIN {WAVE_DATES_TABLE} wd
              ON CAST(t.wave AS FLOAT64) = wd.wave_num
            {where_sql}
            GROUP BY
              CAST(t.wave AS FLOAT64),
              wd.start_date, wd.end_date, wd.midpoint_date,
              wd.size, wd.n
            ORDER BY CAST(t.wave AS FLOAT64)
        """)

        # Map coverage count columns → readable platform names
        platform_cols = [
            "facebook", "instagram", "youtube", "twitter", "tiktok",
            "snapchat", "linkedin", "reddit", "whatsapp", "messenger",
            "pinterest", "tumblr", "gab", "parler", "4chan",
            "truth", "mastodon", "threads", "bluesky", "post",
        ]
        variable_group_cols = {
            "usage_frequency":        "n_freq",
            "platform_trust":         "n_trust",
            "political_posting_freq": "n_pol_post",
            "posting_variants":       "n_posting_variants",
            "political_news_sources": "n_pol_news",
            "phq9_mental_health":     "n_phq9",
            "institutional_trust":    "n_pol_trust",
            "ideology":               "n_ideology",
            "economy_sentiment":      "n_economy",
            "voted_2020":             "n_voted20",
            "voted_2024":             "n_voted24",
            "trump_win_expectation":  "n_trump_win",
            "conspiracy_beliefs":     "n_conspiracy",
            "ozempic":                "n_ozempic",
        }

        waves_out = []
        for _, row in df.iterrows():
            platforms_asked = [p for p in platform_cols if (row.get(f"n_{p}") or 0) > 0]

            variable_groups_fielded = [
                label for label, col in variable_group_cols.items()
                if (row.get(col) or 0) > 0
            ]

            # Field period length
            field_days = None
            if pd.notna(row.get("start_date")) and pd.notna(row.get("end_date")):
                try:
                    field_days = (
                        pd.to_datetime(row["end_date"]) -
                        pd.to_datetime(row["start_date"])
                    ).days
                except Exception:
                    pass

            waves_out.append({
                "wave":               row["wave"],
                "start_date":         str(row["start_date"])   if pd.notna(row.get("start_date"))   else None,
                "end_date":           str(row["end_date"])     if pd.notna(row.get("end_date"))     else None,
                "midpoint_date":      str(row["midpoint_date"])if pd.notna(row.get("midpoint_date"))else None,
                "field_period_days":  field_days,
                "wave_size_category": row.get("wave_size_category"),
                "unweighted_n":       int(row["unweighted_n"]),
                "weighted_n":         int(row["weighted_n"]),
                "official_n":         int(row["official_n"]) if pd.notna(row.get("official_n")) else None,
                "platforms_asked":       platforms_asked,
                "n_platforms_asked":     len(platforms_asked),
                "attitudes_only_wave":   len(platforms_asked) == 0,
                "variable_groups_fielded": variable_groups_fielded,
            })

        return json.dumps({
            "wave_filter": wave or "all",
            "n_waves_returned": len(waves_out),
            "interpretation_note": (
                "unweighted_n = raw respondent count from the main data table. "
                "official_n = sample size from the wave tracking spreadsheet (authoritative). "
                "weighted_n = sum of survey weights (population-representative total). "
                "variable_groups_asked = True if the question group was fielded that wave."
            ),
            "waves": waves_out,
        }, indent=2, default=str)

    except Exception as e:
        logger.error(f"get_wave_metadata error: {e}")
        raise


# ── Regression helpers ───────────────────────────────────────────────────────

def _build_filter_clauses(filters: Dict[str, List]) -> str:
    """Convert a {column: [values]} dict into SQL AND … IN (…) clauses.

    String values are single-quoted; values that parse as numbers are unquoted.
    Single-quotes inside string values are escaped.
    """
    clauses = []
    for col, values in filters.items():
        quoted = []
        for v in values:
            try:
                float(v)
                quoted.append(str(v))
            except (TypeError, ValueError):
                safe = str(v).replace("'", "\\'")
                quoted.append(f"'{safe}'")
        clauses.append(f"{col} IN ({', '.join(quoted)})")
    return "AND " + " AND ".join(clauses)


def _fetch_regression_data(
    outcome: str,
    predictors: List[str],
    wave: Optional[str],
    filters: Optional[Dict[str, List]] = None,
) -> pd.DataFrame:
    """Pull individual-level rows needed for a regression from BigQuery."""
    cols = [outcome] + predictors

    # Resolve derived columns: substitute SQL expressions in SELECT;
    # use source column for NOT NULL and sentinel (>0) checks.
    def _real_col(c: str) -> str:
        return _DERIVED_COLUMNS[c]["source"] if c in _DERIVED_COLUMNS else c

    def _select_expr(c: str) -> str:
        if c in _DERIVED_COLUMNS:
            return f"{_DERIVED_COLUMNS[c]['sql']} AS {c}"
        return c

    real_cols = [_real_col(c) for c in cols]
    select_cols = ", ".join(_select_expr(c) for c in cols) + ", weight"

    not_null = " AND ".join(f"{c} IS NOT NULL" for c in real_cols + ["weight"])

    sentinel_clauses = " ".join(
        f"AND {c} > 0" for c in real_cols if c in _SENTINEL_COLUMNS
    )

    filter_clauses = _build_filter_clauses(filters) if filters else ""

    sql = f"""
        SELECT {select_cols}
        FROM {FULL_TABLE}
        WHERE {not_null}
          {sentinel_clauses}
          {wave_clause(wave)}
          {filter_clauses}
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
    treat_as_categorical: Optional[List[str]] = None,
) -> tuple[pd.DataFrame, List[str], List[str]]:
    """Dummy-encode categorical predictors; pass numeric ones through.

    Args:
        df: Data frame with all predictor columns present.
        predictors: Ordered list of predictor column names.
        reference_levels: Optional mapping of {column_name: reference_category}.
            When provided for a categorical column the specified category is used
            as the dropped (reference) level.  Unknown categories fall back to
            the alphabetically first value with a logged warning.
        treat_as_categorical: Optional list of ordinal column names to dummy-encode
            rather than treat as continuous. Useful for freq_* or trust_* columns
            where the numeric scale should not be assumed linear.

    Returns:
        (X DataFrame, encoding notes, warning messages)
    """
    if reference_levels is None:
        reference_levels = {}
    _extra_categorical: set[str] = set(treat_as_categorical) if treat_as_categorical else set()
    notes: List[str] = []
    warnings: List[str] = []
    frames: List[pd.DataFrame] = []
    for col in predictors:
        if col in _CATEGORICAL_COLUMNS or col in _extra_categorical:
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


def _fit_ols(
    df: pd.DataFrame,
    outcome: str,
    predictors: List[str],
    reference_levels: Optional[Dict[str, str]],
    use_weights: bool,
    treat_as_categorical: Optional[List[str]] = None,
):
    """Encode predictors and fit OLS/WLS. Runs in a thread executor."""
    y = df[outcome].astype(float)
    weights = df["weight"].astype(float)
    X_df, enc_notes, ref_warnings = _encode_predictors(df, predictors, reference_levels, treat_as_categorical)
    X = sm.add_constant(X_df, has_constant="add")
    model = sm.WLS(y, X, weights=weights).fit() if use_weights else sm.OLS(y, X).fit()
    return model, y, weights, enc_notes, ref_warnings


def _fit_logistic(
    df: pd.DataFrame,
    outcome: str,
    predictors: List[str],
    reference_levels: Optional[Dict[str, str]],
    use_weights: bool,
    treat_as_categorical: Optional[List[str]] = None,
):
    """Encode predictors and fit logistic GLM. Runs in a thread executor."""
    y = df[outcome].astype(float)
    weights = df["weight"].astype(float)
    X_df, enc_notes, ref_warnings = _encode_predictors(df, predictors, reference_levels, treat_as_categorical)
    X = sm.add_constant(X_df, has_constant="add")
    if use_weights:
        model = sm.GLM(y, X, family=sm.families.Binomial(), freq_weights=weights).fit()
    else:
        model = sm.GLM(y, X, family=sm.families.Binomial()).fit()
    return model, y, weights, enc_notes, ref_warnings


@mcp.tool()
async def run_ols_regression(
    outcome: str,
    predictors: List[str],
    wave: Optional[str] = None,
    reference_levels: Optional[Dict[str, str]] = None,
    use_weights: bool = True,
    filters: Optional[Dict[str, List[str]]] = None,
    treat_as_categorical: Optional[List[str]] = None,
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
        filters: Optional subgroup filter applied before fitting. A mapping of
            {column_name: [allowed_values]}. Rows where the column value is NOT
            in the list are dropped before the model is fit. Example:
            {"age_cat_8": ["18-24", "25-34"]} restricts to the two youngest
            age groups. {"gender": ["Female"], "party3": ["Democrat"]} restricts
            to female Democrats. Filter columns do not need to appear in predictors.
            Call get_available_variables() to see valid column names and values.
        treat_as_categorical: Optional list of ordinal predictor columns to
            dummy-encode rather than treat as continuous. Use this when the
            ordinal scale should not be assumed linear — e.g. freq_* columns
            (1=Never … 6=Almost constantly) or trust_* columns (1–4 scale).
            Example: ["freq_facebook", "freq_instagram"] produces dummies for
            each observed frequency value, with the lowest (reference) level
            dropped unless overridden via reference_levels.

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
    if filters:
        invalid_filters = [c for c in filters if c not in _ALL_REGRESSION_COLUMNS]
        if invalid_filters:
            return json.dumps({
                "error": f"Unknown filter columns: {invalid_filters}. Call get_available_variables() to see valid column names."
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
            None, _fetch_regression_data, outcome, predictors, wave, filters
        )
    except Exception as e:
        logger.error(f"run_ols_regression data fetch error: {e}")
        return json.dumps({"error": str(e)})

    if len(df) < 50:
        return json.dumps({"error": f"Too few observations ({len(df)}) after filters — cannot fit model."})

    try:
        model, y, weights, enc_notes, ref_warnings = await asyncio.get_event_loop().run_in_executor(
            None, _fit_ols, df, outcome, predictors, reference_levels, use_weights, treat_as_categorical
        )
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
        "treat_as_categorical": treat_as_categorical,
        "subgroup_filters": filters,
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
    filters: Optional[Dict[str, List[str]]] = None,
    treat_as_categorical: Optional[List[str]] = None,
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
        filters: Optional subgroup filter applied before fitting. A mapping of
            {column_name: [allowed_values]}. Rows where the column value is NOT
            in the list are dropped before the model is fit. Example:
            {"age_cat_8": ["18-24", "25-34"]} restricts to the two youngest
            age groups. {"gender": ["Female"], "party3": ["Democrat"]} restricts
            to female Democrats. Filter columns do not need to appear in predictors.
            Call get_available_variables() to see valid column names and values.
        treat_as_categorical: Optional list of ordinal predictor columns to
            dummy-encode rather than treat as continuous. Use this when the
            ordinal scale should not be assumed linear — e.g. freq_* columns
            (1=Never … 6=Almost constantly) or trust_* columns (1–4 scale).
            Example: ["freq_facebook"] produces dummies for each observed frequency
            value, with the lowest (reference) level dropped unless overridden via
            reference_levels.

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
    if filters:
        invalid_filters = [c for c in filters if c not in _ALL_REGRESSION_COLUMNS]
        if invalid_filters:
            return json.dumps({
                "error": f"Unknown filter columns: {invalid_filters}. Call get_available_variables() to see valid column names."
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
            None, _fetch_regression_data, outcome, predictors, wave, filters
        )
    except Exception as e:
        logger.error(f"run_logistic_regression data fetch error: {e}")
        return json.dumps({"error": str(e)})

    if len(df) < 50:
        return json.dumps({"error": f"Too few observations ({len(df)}) after filters — cannot fit model."})

    # Binary check before handing off to executor
    unique_vals = set(df[outcome].dropna().unique())
    if not unique_vals.issubset({0.0, 1.0, 0, 1}):
        return json.dumps({"error": f"Outcome '{outcome}' has non-binary values: {sorted(unique_vals)[:10]}."})

    try:
        model, y, weights, enc_notes, ref_warnings = await asyncio.get_event_loop().run_in_executor(
            None, _fit_logistic, df, outcome, predictors, reference_levels, use_weights, treat_as_categorical
        )
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
        "treat_as_categorical": treat_as_categorical,
        "subgroup_filters": filters,
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


# ── PDF Report Generator ─────────────────────────────────────────────────────

def _build_chip50_pdf(
    title: str,
    subtitle: Optional[str],
    authors: Optional[str],
    abstract: Optional[str],
    sections: List[Dict[str, Any]],
    include_methodology: bool,
    buf: BytesIO,
) -> int:
    """Render the report into *buf* and return the number of tables produced."""

    # ── Palette ───────────────────────────────────────────────────────────────
    NAVY    = _rl_colors.Color(0.13, 0.24, 0.44)
    NAVY_LT = _rl_colors.Color(0.22, 0.38, 0.62)
    ROW_ALT = _rl_colors.Color(0.94, 0.96, 0.99)
    RULE    = _rl_colors.Color(0.50, 0.50, 0.50)
    WHITE   = _rl_colors.white
    BLACK   = _rl_colors.black

    PAGE_W, PAGE_H = _LETTER
    MARGIN    = 1.15 * _inch
    CONTENT_W = PAGE_W - 2 * MARGIN

    # ── Running header / footer ───────────────────────────────────────────────
    short_title = (title[:58] + "\u2026") if len(title) > 60 else title

    def _on_first_page(canvas, doc):
        pass  # title page — no header/footer chrome

    def _on_later_pages(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(NAVY)
        canvas.setLineWidth(0.5)
        # header rule + text
        canvas.line(MARGIN, PAGE_H - 0.65 * _inch,
                    PAGE_W - MARGIN, PAGE_H - 0.65 * _inch)
        canvas.setFont("Times-Roman", 8)
        canvas.setFillColor(NAVY)
        canvas.drawString(MARGIN, PAGE_H - 0.54 * _inch,
                          "CHIP50 Social Media Demographics Panel")
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.54 * _inch, short_title)
        # footer rule + text
        canvas.line(MARGIN, 0.65 * _inch, PAGE_W - MARGIN, 0.65 * _inch)
        canvas.setFont("Times-Roman", 8)
        canvas.setFillColor(RULE)
        canvas.drawString(MARGIN, 0.46 * _inch, "CHIP50 \u2022 Nanocentury AI")
        canvas.drawRightString(PAGE_W - MARGIN, 0.46 * _inch, f"Page {doc.page}")
        canvas.restoreState()

    doc = _SimpleDocTemplate(
        buf,
        pagesize=_LETTER,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
        title=title,
        author=authors or "CHIP50 Panel",
        subject="CHIP50 Social Media Demographics Report",
        creator="CHIP50 MCP PDF Generator",
    )

    # ── Paragraph styles ──────────────────────────────────────────────────────
    def _ps(name, **kw):
        return _PS(name, **kw)

    s_title = _ps("ChipTitle",
        fontName="Times-Bold", fontSize=22, leading=28,
        textColor=NAVY, alignment=TA_CENTER, spaceAfter=10)
    s_subtitle = _ps("ChipSubtitle",
        fontName="Times-Italic", fontSize=14, leading=18,
        textColor=NAVY_LT, alignment=TA_CENTER, spaceAfter=6)
    s_authors = _ps("ChipAuthors",
        fontName="Times-Roman", fontSize=11, leading=14,
        textColor=BLACK, alignment=TA_CENTER, spaceAfter=4)
    s_date = _ps("ChipDate",
        fontName="Times-Roman", fontSize=10, leading=13,
        textColor=RULE, alignment=TA_CENTER, spaceAfter=20)
    s_h1 = _ps("ChipH1",
        fontName="Times-Bold", fontSize=14, leading=18,
        textColor=NAVY, spaceBefore=18, spaceAfter=6)
    s_body = _ps("ChipBody",
        fontName="Times-Roman", fontSize=10.5, leading=15,
        textColor=BLACK, alignment=TA_JUSTIFY, spaceAfter=8)
    s_abstract = _ps("ChipAbstract",
        fontName="Times-Italic", fontSize=10, leading=14,
        textColor=BLACK, alignment=TA_JUSTIFY,
        leftIndent=24, rightIndent=24, spaceAfter=10)
    s_tbl_title = _ps("ChipTblTitle",
        fontName="Times-Bold", fontSize=9.5, leading=12,
        textColor=BLACK, spaceBefore=14, spaceAfter=3)
    s_tbl_note = _ps("ChipTblNote",
        fontName="Times-Italic", fontSize=8.5, leading=11,
        textColor=RULE, spaceAfter=12)
    # ── Table style factory ───────────────────────────────────────────────────
    def _tbl_style(n_rows: int) -> _TableStyle:
        cmds = [
            ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
            ("FONTNAME",      (0, 0), (-1, 0),  "Times-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0),  9),
            ("TOPPADDING",    (0, 0), (-1, 0),  6),
            ("BOTTOMPADDING", (0, 0), (-1, 0),  6),
            ("FONTNAME",      (0, 1), (-1, -1), "Times-Roman"),
            ("FONTSIZE",      (0, 1), (-1, -1), 9),
            ("TOPPADDING",    (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            *[("BACKGROUND",  (0, r), (-1, r),  ROW_ALT)
              for r in range(2, n_rows, 2)],
            ("GRID",          (0, 0), (-1, -1), 0.3, RULE),
            ("LINEBELOW",     (0, 0), (-1, 0),  0.8, NAVY),
            ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 7),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
        ]
        return _TableStyle(cmds)

    # ── Helper: cell paragraph styles ─────────────────────────────────────────
    _s_th = _ps("TH", fontName="Times-Bold",   fontSize=9, textColor=WHITE, leading=11)
    _s_td = _ps("TD", fontName="Times-Roman",  fontSize=9, textColor=BLACK, leading=11)

    # ── Story ─────────────────────────────────────────────────────────────────
    story: List[Any] = []
    table_counter = [0]

    # Title page
    story.append(_Spacer(1, 1.4 * _inch))
    if os.path.exists(_LOGO_PATH):
        # 175×153 px source — render at 1.2 × 1.047 in (preserves aspect ratio)
        logo_img = _Image(_LOGO_PATH, width=1.2 * _inch, height=round(1.2 * 153 / 175, 3) * _inch)
        logo_img.hAlign = "CENTER"
        story.append(logo_img)
        story.append(_Spacer(1, 0.18 * _inch))
    story.append(_HRFlowable(width="75%", color=NAVY, thickness=1.5, spaceAfter=22))
    story.append(_Paragraph(title, s_title))
    if subtitle:
        story.append(_Paragraph(subtitle, s_subtitle))
    if authors:
        story.append(_Paragraph(authors, s_authors))
    report_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
    story.append(_Paragraph(report_date, s_date))
    story.append(_Spacer(1, 0.3 * _inch))
    story.append(_HRFlowable(width="35%", color=NAVY_LT, thickness=0.5))
    story.append(_Spacer(1, 0.18 * _inch))
    story.append(_Paragraph(
        "CHIP50 Social Media Demographics Panel<br/>"
        "<font size='9' color='#888888'>Nanocentury AI</font>",
        s_date,
    ))
    story.append(_PageBreak())

    # Abstract
    if abstract:
        story.append(_Paragraph("Abstract", s_h1))
        story.append(_HRFlowable(width="100%", color=NAVY, thickness=0.5, spaceAfter=10))
        for para in abstract.strip().split("\n\n"):
            if para.strip():
                story.append(_Paragraph(para.strip(), s_abstract))
        story.append(_Spacer(1, 0.15 * _inch))

    # Methodology section
    if include_methodology:
        story.append(_Paragraph("Data &amp; Methodology", s_h1))
        story.append(_HRFlowable(width="100%", color=NAVY, thickness=0.5, spaceAfter=10))
        methodology_text = [
            (
                "The data presented in this report are drawn from the CHIP50 Social Media "
                "Demographics Panel, a nationally representative online survey panel of U.S. "
                "adults conducted by Nanocentury AI across multiple fielding waves."
            ),
            (
                "Survey weights are applied throughout to adjust for design effects and ensure "
                "population representativeness. All percentages and means reported in this "
                "document are weighted population estimates unless otherwise indicated. "
                "Unweighted respondent counts (<i>n</i>) are provided solely as an indicator "
                "of statistical reliability and must not be interpreted as population estimates "
                "or used to compute percentages."
            ),
            (
                "Cells with fewer than 10 respondents are suppressed and reported as \u201c\u2014\u201d "
                "to protect respondent privacy. Platform usage is measured as a binary indicator "
                "(1\u202f=\u202fuses platform; 0\u202f=\u202fdoes not use platform). Ordinal "
                "response scales encode \u221299 for skipped or refused responses; these values "
                "are automatically excluded from all distributional and regression analyses."
            ),
            (
                "Regression models employ survey-weighted estimation. OLS models report "
                "coefficients with heteroskedasticity-consistent standard errors, "
                "<i>R</i>\u00b2, <i>F</i>-statistic, and AIC/BIC. Logistic regression models "
                "report log-odds coefficients, odds ratios, McFadden\u2019s pseudo-<i>R</i>\u00b2, "
                "and AIC/BIC. Statistical significance is assessed at \u03b1\u202f=\u202f0.05."
            ),
        ]
        for para in methodology_text:
            story.append(_Paragraph(para, s_body))
        story.append(_Spacer(1, 0.1 * _inch))

    # User sections
    for section in sections:
        heading = section.get("heading", "")
        content = section.get("content", "")
        tables  = section.get("tables") or []

        if heading:
            story.append(_Paragraph(heading, s_h1))
            story.append(_HRFlowable(width="100%", color=NAVY, thickness=0.5, spaceAfter=10))

        if content:
            for para in content.strip().split("\n\n"):
                if para.strip():
                    story.append(_Paragraph(para.strip(), s_body))

        for tbl_def in tables:
            col_headers = tbl_def.get("column_headers") or []
            rows        = tbl_def.get("rows") or []
            notes       = tbl_def.get("notes")
            tbl_ttl     = tbl_def.get("title", "")

            if not col_headers and not rows:
                continue

            table_counter[0] += 1
            label = f"Table {table_counter[0]}."
            if tbl_ttl:
                label += f" {tbl_ttl}"

            # Build cell data
            data: List[List[Any]] = []
            if col_headers:
                data.append([_Paragraph(str(h), _s_th) for h in col_headers])
            for row in rows:
                data.append([_Paragraph(str(cell), _s_td) for cell in row])

            if not data:
                continue

            n_cols = len(data[0])
            # Column widths: first col ~30% wider than rest
            if n_cols == 1:
                col_widths = [CONTENT_W]
            elif n_cols == 2:
                col_widths = [CONTENT_W * 0.44, CONTENT_W * 0.56]
            else:
                first = CONTENT_W * 0.30
                rest  = (CONTENT_W - first) / (n_cols - 1)
                col_widths = [first] + [rest] * (n_cols - 1)

            tbl = _Table(data, colWidths=col_widths, repeatRows=1)
            tbl.setStyle(_tbl_style(len(data)))

            block: List[Any] = [_Paragraph(label, s_tbl_title), tbl]
            if notes:
                block.append(_Paragraph(f"<i>Note.</i> {notes}", s_tbl_note))
            story.append(_KeepTogether(block))

        story.append(_Spacer(1, 0.08 * _inch))

    doc.build(story, onFirstPage=_on_first_page, onLaterPages=_on_later_pages)
    return table_counter[0]


@mcp.tool()
async def generate_pdf_report(
    title: str,
    sections: List[Dict[str, Any]],
    subtitle: Optional[str] = None,
    authors: Optional[str] = None,
    abstract: Optional[str] = None,
    include_methodology: bool = True,
) -> str:
    """Generate a formatted PDF report from CHIP50 analysis results.

    Produces a publication-quality PDF following academic methodology reporting
    standards: title page, abstract, auto-generated methodology section,
    numbered tables with captions and footnotes, running page header/footer.

    The PDF is uploaded to GCS and a signed download URL (valid 1 hour) is
    returned. Download it with: curl -L "<download_url>" -o report.pdf

    Parameters
    ----------
    title : str
        Main report title (appears on title page and in the running header).
    sections : list[dict]
        Report body sections, in order. Each section dict supports:

        - "heading" (str): Section heading displayed in bold navy.
        - "content" (str): Narrative text. Separate paragraphs with \\n\\n.
          Basic HTML tags (<i>, <b>) are supported.
        - "tables" (list[dict]): Tables to embed after the section text.
          Each table dict:
            - "title" (str): Caption; auto-prefixed "Table N. <title>".
            - "column_headers" (list[str]): Header row.
            - "rows" (list[list[str]]): Data rows; all cells as strings.
            - "notes" (str, optional): Footnote rendered below the table in
              italic per APA style ("Note. ...").

    subtitle : str, optional
        Subtitle under the main title on the title page.
    authors : str, optional
        Author name(s) for the title page.
    abstract : str, optional
        Abstract / executive summary (paragraphs separated by \\n\\n).
    include_methodology : bool, default True
        Auto-include the CHIP50 methodology section (weighting, cell
        suppression, ordinal sentinel, regression conventions).

    Returns
    -------
    JSON with:
    - download_url      : Signed GCS URL valid for 1 hour. Pass directly to
                          curl or a browser to download the PDF.
    - filename          : Suggested local filename for saving.
    - tables_generated  : Count of numbered tables in the report.
    - size_bytes        : PDF file size in bytes.
    - expires_in        : Human-readable URL expiry ("1 hour").
    """
    if not _REPORTLAB_AVAILABLE:
        raise RuntimeError(
            "reportlab is not installed. Add 'reportlab>=4.2.0' to requirements.txt "
            "and redeploy the service."
        )

    # Build PDF in memory
    buf = BytesIO()
    n_tables = _build_chip50_pdf(
        title=title,
        subtitle=subtitle,
        authors=authors,
        abstract=abstract,
        sections=sections,
        include_methodology=include_methodology,
        buf=buf,
    )
    pdf_bytes = buf.getvalue()

    # Derive a clean filename
    date_stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() else "_" for c in title)[:40].strip("_")
    filename   = f"chip50_{safe_title}_{date_stamp}.pdf"
    gcs_key    = f"reports/{filename}"

    # Upload to GCS
    gcs_client = gcs.Client(project=GCP_PROJECT)
    bucket     = gcs_client.bucket(REPORTS_BUCKET)
    blob       = bucket.blob(gcs_key)
    blob.upload_from_string(pdf_bytes, content_type="application/pdf")

    # Public URL (bucket is publicly readable)
    public_url = f"https://storage.googleapis.com/{REPORTS_BUCKET}/{gcs_key}"

    return json.dumps({
        "download_url": public_url,
        "filename": filename,
        "tables_generated": n_tables,
        "size_bytes": len(pdf_bytes),
    }, indent=2)


if __name__ == "__main__":
    asyncio.run(
        mcp.run_async(
            transport="streamable-http",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8080)),
        )
    )
