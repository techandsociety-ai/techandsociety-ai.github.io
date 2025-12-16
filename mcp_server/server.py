#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pandas>=2.0.0",
#   "google-cloud-bigquery>=3.11.0",
#   "db-dtypes>=1.1.0",
#   "mcp>=0.9.0",
# ]
# ///
"""
CHIP50 Survey MCP Server - Phase 3 (MVP)

Provides privacy-preserving access to CHIP50 survey data through protected BigQuery views.
Implements cell suppression (n≥10) and uses simple test API key for validation.

Architecture:
- Wave-based table structure: Each wave has separate tables (e.g., demographics_protected_w35)
- Direct BigQuery access to wave-specific protected views (chip50.public.*_w35)
- Local cell suppression enforcement
- Simple API key validation via environment variable
- row_hash used for joining demographics and survey responses within a wave
"""

import json
import sys
import os
import asyncio
from typing import Any, Dict, List
import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

# MCP SDK imports
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio


# Simple test API key for synthetic data testing
TEST_API_KEY = "chip50_test_synthetic_data_only"

# Default configuration
DEFAULT_PROJECT_ID = os.environ.get("CHIP50_PROJECT_ID", "chip50")
DEFAULT_DATASET_PUBLIC = os.environ.get("CHIP50_DATASET_PUBLIC", "public")
MIN_CELL_SIZE = int(os.environ.get("CHIP50_MIN_CELL_SIZE", "10"))


def validate_api_key() -> bool:
    """
    Validate API key from environment variable.
    For MVP: Simple comparison to test key.

    Raises:
        ValueError: If API key is missing or invalid

    Returns:
        True if valid
    """
    api_key = os.environ.get("CHIP50_API_KEY", "")

    if not api_key:
        raise ValueError(
            "CHIP50_API_KEY environment variable not set.\n"
            f"For testing with synthetic data, set it to: {TEST_API_KEY}"
        )

    if api_key != TEST_API_KEY:
        raise ValueError(
            f"Invalid API key.\n"
            f"For testing with synthetic data, use: {TEST_API_KEY}"
        )

    return True


def suppress_small_cells(
    results: List[Dict[str, Any]],
    min_cell_size: int = MIN_CELL_SIZE
) -> tuple[List[Dict[str, Any]], int]:
    """
    Suppress cells with counts below threshold for privacy protection.

    Implements k-anonymity with minimum cell size of 10 (configurable).

    Args:
        results: List of result dictionaries from crosstab query
        min_cell_size: Minimum cell size threshold (default: 10)

    Returns:
        Tuple of (suppressed_results, count_of_suppressed_cells)
    """
    suppressed_count = 0
    suppressed_results = []

    for row in results:
        row_copy = row.copy()

        # Check count fields (handle both weighted and unweighted)
        count_field = row.get('count') or row.get('n') or row.get('weighted_count', 0)

        if count_field < min_cell_size:
            # Suppress this cell
            suppressed_count += 1
            row_copy['suppressed'] = True
            row_copy['count'] = '[suppressed]'
            row_copy['percentage'] = '[suppressed]'
            row_copy['note'] = f'n<{min_cell_size} (privacy protection)'
        else:
            row_copy['suppressed'] = False

        suppressed_results.append(row_copy)

    return suppressed_results, suppressed_count


class SurveyAnalysisServer:
    """MCP server for CHIP50 survey data analysis with privacy protections."""

    def __init__(self):
        self.server = Server("chip50-survey-mcp")
        self.bigquery_client = None
        self.project_id = DEFAULT_PROJECT_ID
        self.dataset_public = DEFAULT_DATASET_PUBLIC

        # Validate API key on startup
        try:
            validate_api_key()
            print(f"✓ API key validated", file=sys.stderr)
            print(f"✓ Using project: {self.project_id}", file=sys.stderr)
            print(f"✓ Using dataset: {self.project_id}.{self.dataset_public}", file=sys.stderr)
            print(f"✓ Cell suppression threshold: n≥{MIN_CELL_SIZE}", file=sys.stderr)
        except ValueError as e:
            print(f"✗ API key validation failed: {e}", file=sys.stderr)
            sys.exit(1)

        # Register tool handlers
        self.setup_handlers()

    def setup_handlers(self):
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="get_available_variables",
                    description=(
                        "Get list of available survey and demographic variables in the CHIP50 dataset. "
                        "Returns variable names, descriptions, scale information, and available waves. "
                        "Use this first to discover what data is available before generating crosstabs."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="generate_crosstab",
                    description=(
                        "Generate privacy-protected cross-tabulation of CHIP50 survey data. "
                        "Analyzes survey responses across demographic categories with automatic "
                        "cell suppression (n≥10) for privacy protection. Uses protected views with "
                        "geographic aggregation (regions, not states) and no user IDs exposed. "
                        "Returns weighted counts, percentages, and suppression metadata. "
                        "Each wave has separate tables (e.g., demographics_protected_w35)."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "survey_variable": {
                                "type": "string",
                                "description": (
                                    "Survey variable to analyze (e.g., 'pol_trust_congress', 'pol_approval_pres', "
                                    "'pol_vote_intention'). Use get_available_variables to see all options."
                                )
                            },
                            "demographic_variable": {
                                "type": "string",
                                "description": (
                                    "Demographic variable to group by (e.g., 'party7', 'region', "
                                    "'educ', 'age_cat', 'race', 'gender'). "
                                    "Note: 'region' used instead of 'state_code' for privacy. "
                                    "Use get_available_variables to see all options."
                                )
                            },
                            "wave": {
                                "type": "string",
                                "description": (
                                    "Wave identifier to query (e.g., '35', '35_1', '36'). "
                                    "Each wave has separate tables. Use get_available_variables to see available waves. "
                                    "Required parameter."
                                )
                            },
                            "use_weights": {
                                "type": "boolean",
                                "description": "Whether to use survey weights for weighted tabulation (default: true)",
                                "default": True
                            }
                        },
                        "required": ["survey_variable", "demographic_variable", "wave"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool calls."""
            try:
                if name == "get_available_variables":
                    result = await self.get_available_variables()
                elif name == "generate_crosstab":
                    result = await self.generate_crosstab(
                        survey_variable=arguments["survey_variable"],
                        demographic_variable=arguments["demographic_variable"],
                        wave=arguments["wave"],
                        use_weights=arguments.get("use_weights", True)
                    )
                else:
                    raise ValueError(f"Unknown tool: {name}")

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            except Exception as e:
                error_msg = {
                    "status": "error",
                    "message": str(e),
                    "error_type": type(e).__name__
                }
                return [TextContent(type="text", text=json.dumps(error_msg, indent=2))]

    async def get_available_variables(self) -> Dict[str, Any]:
        """
        Get list of available survey and demographic variables.

        Returns dictionary with demographic variables, survey variables,
        available waves, and privacy notes.
        """
        return {
            "status": "success",
            "note": "Each wave has separate tables (e.g., demographics_protected_w35, demographics_protected_w35_1)",
            "available_waves": [
                {
                    "wave": "35",
                    "table_suffix": "w35",
                    "description": "Wave 35 data"
                },
                {
                    "wave": "35.1",
                    "table_suffix": "w35_1",
                    "description": "Wave 35.1 data"
                }
            ],
            "demographic_variables": [
                {
                    "name": "region",
                    "description": "Geographic region (5 categories)",
                    "categories": ["Northeast", "Mid-Atlantic", "Midwest", "South", "West"],
                    "note": "State-level data aggregated to regions for privacy"
                },
                {
                    "name": "age_cat",
                    "description": "Age category",
                    "note": "Categories may vary by wave"
                },
                {
                    "name": "educ",
                    "description": "Education level",
                    "note": "Categories may vary by wave"
                },
                {
                    "name": "income_cat",
                    "description": "Income bracket",
                    "note": "Categories may vary by wave"
                },
                {
                    "name": "gender",
                    "description": "Gender identity",
                    "categories": ["Male", "Female", "Non-binary", "Prefer not to say"]
                },
                {
                    "name": "party7",
                    "description": "Party identification (7-point scale)",
                    "scale": "1=Strong Democrat, 7=Strong Republican, 4=Independent",
                    "categories": "1-7"
                },
                {
                    "name": "race",
                    "description": "Race/ethnicity",
                    "note": "Categories may vary by wave"
                },
                {
                    "name": "urban_type",
                    "description": "Urban/suburban/rural classification",
                    "categories": ["Urban", "Suburban", "Rural"]
                }
            ],
            "survey_variables": [
                {
                    "name": "pol_trust_congress",
                    "description": "Trust in Congress",
                    "scale": "1-5 (1=Strongly distrust, 5=Strongly trust)"
                },
                {
                    "name": "pol_trust_courts",
                    "description": "Trust in courts",
                    "scale": "1-5 (1=Strongly distrust, 5=Strongly trust)"
                },
                {
                    "name": "pol_trust_media",
                    "description": "Trust in media",
                    "scale": "1-5 (1=Strongly distrust, 5=Strongly trust)"
                },
                {
                    "name": "pol_trust_military",
                    "description": "Trust in military",
                    "scale": "1-5 (1=Strongly distrust, 5=Strongly trust)"
                },
                {
                    "name": "pol_approval_pres",
                    "description": "Presidential approval",
                    "scale": "1-7 (1=Strongly disapprove, 7=Strongly approve)"
                },
                {
                    "name": "pol_approval_governor",
                    "description": "Governor approval",
                    "scale": "1-7 (1=Strongly disapprove, 7=Strongly approve)"
                },
                {
                    "name": "pol_approval_senator",
                    "description": "Senator approval",
                    "scale": "1-7 (1=Strongly disapprove, 7=Strongly approve)"
                },
                {
                    "name": "pol_issue_economy",
                    "description": "Economy issue importance",
                    "scale": "0-10 (0=Not important, 10=Extremely important)"
                },
                {
                    "name": "pol_issue_healthcare",
                    "description": "Healthcare issue importance",
                    "scale": "0-10 (0=Not important, 10=Extremely important)"
                },
                {
                    "name": "pol_vote_intention",
                    "description": "Voting intention",
                    "type": "categorical",
                    "note": "Categories may vary by wave"
                },
                {
                    "name": "pol_registered_voter",
                    "description": "Voter registration status",
                    "scale": "0-1 (0=Not registered, 1=Registered)",
                    "type": "binary"
                },
                {
                    "name": "pol_party_thermometer",
                    "description": "Party feeling thermometer",
                    "scale": "0-100 (0=Very cold, 100=Very warm)",
                    "type": "continuous"
                }
            ],
            "privacy_protections": {
                "cell_suppression": f"Cells with n<{MIN_CELL_SIZE} automatically suppressed",
                "geographic_aggregation": "State-level data aggregated to 5 regions",
                "user_ids": "Not accessible in protected views (row_hash used for joins)",
                "free_text": "Excluded from protected views",
                "wave_separation": "Each wave stored in separate tables to maintain schema flexibility"
            },
            "usage_note": "Variable names and categories may differ across waves. Check specific wave documentation for exact column names."
        }

    async def generate_crosstab(
        self,
        survey_variable: str,
        demographic_variable: str,
        wave: str,
        use_weights: bool = True
    ) -> Dict[str, Any]:
        """
        Generate privacy-protected cross-tabulation using BigQuery protected views.

        Args:
            survey_variable: Survey variable to analyze
            demographic_variable: Demographic variable to group by
            wave: Wave identifier (e.g., '35', '35_1')
            use_weights: Whether to use survey weights

        Returns:
            Dictionary with crosstab results, metadata, and suppression info
        """
        try:
            # Initialize BigQuery client
            client = bigquery.Client(project=self.project_id)

            # Convert wave format: '35' -> 'w35', '35.1' -> 'w35_1', '35_1' -> 'w35_1'
            wave_suffix = wave.replace('.', '_')
            if not wave_suffix.startswith('w'):
                wave_suffix = f'w{wave_suffix}'

            # Use wave-specific protected views (chip50.public.*_w35)
            demographics_table = f"{self.project_id}.{self.dataset_public}.demographics_protected_{wave_suffix}"
            survey_table = f"{self.project_id}.{self.dataset_public}.survey_responses_protected_{wave_suffix}"

            # Build the base query with JOIN using row_hash (not id)
            base_join = f"""
            SELECT
                d.{demographic_variable},
                s.{survey_variable},
                d.weight
            FROM `{demographics_table}` d
            INNER JOIN `{survey_table}` s
                ON d.row_hash = s.row_hash
            WHERE d.{demographic_variable} IS NOT NULL
                AND s.{survey_variable} IS NOT NULL
            """

            # Build weighted or unweighted crosstab query
            if use_weights:
                query = f"""
                WITH joined_data AS ({base_join})
                SELECT
                    {demographic_variable},
                    {survey_variable},
                    COUNT(*) as n,
                    SUM(weight) as weighted_count,
                    SUM(SUM(weight)) OVER (PARTITION BY {demographic_variable}) as demographic_total
                FROM joined_data
                GROUP BY {demographic_variable}, {survey_variable}
                ORDER BY {demographic_variable}, {survey_variable}
                """
            else:
                query = f"""
                WITH joined_data AS ({base_join})
                SELECT
                    {demographic_variable},
                    {survey_variable},
                    COUNT(*) as count,
                    SUM(COUNT(*)) OVER (PARTITION BY {demographic_variable}) as demographic_total
                FROM joined_data
                GROUP BY {demographic_variable}, {survey_variable}
                ORDER BY {demographic_variable}, {survey_variable}
                """

            # Execute query
            query_job = client.query(query)
            results = query_job.result()

            # Convert to list of dictionaries
            rows = [dict(row) for row in results]

            if len(rows) == 0:
                return {
                    "status": "error",
                    "message": "No data returned. Check that variables exist and have non-null values."
                }

            # Calculate percentages
            count_col = 'weighted_count' if use_weights else 'count'
            for row in rows:
                row['percentage'] = round((row[count_col] / row['demographic_total']) * 100, 2)

            # Apply cell suppression for privacy
            suppressed_rows, suppressed_count = suppress_small_cells(rows, MIN_CELL_SIZE)

            # Convert to pandas DataFrame for pivot table
            df = pd.DataFrame(suppressed_rows)

            # Create pivot table (excluding suppressed cells for aggregates)
            non_suppressed = df[~df['suppressed']]

            if len(non_suppressed) > 0:
                pivot_counts = non_suppressed.pivot_table(
                    index=demographic_variable,
                    columns=survey_variable,
                    values=count_col,
                    aggfunc='sum',
                    fill_value=0
                )

                pivot_percentages = non_suppressed.pivot_table(
                    index=demographic_variable,
                    columns=survey_variable,
                    values='percentage',
                    aggfunc='mean',
                    fill_value=0
                )
            else:
                pivot_counts = pd.DataFrame()
                pivot_percentages = pd.DataFrame()

            # Format combined table
            combined_table = {}
            for demo_cat in pivot_counts.index:
                combined_table[str(demo_cat)] = {}
                for survey_cat in pivot_counts.columns:
                    count_val = pivot_counts.loc[demo_cat, survey_cat]
                    pct_val = pivot_percentages.loc[demo_cat, survey_cat]
                    combined_table[str(demo_cat)][str(survey_cat)] = {
                        "count": float(count_val),
                        "percentage": float(pct_val),
                        "display": f"{count_val:.1f} ({pct_val:.1f}%)"
                    }

            # Get marginal totals (excluding suppressed)
            marginal_totals = non_suppressed.groupby(demographic_variable)[count_col].sum().to_dict()
            marginal_totals = {str(k): float(v) for k, v in marginal_totals.items()}

            # Calculate total sample size
            total_n = int(df['n'].sum()) if 'n' in df.columns else len(df)

            return {
                "status": "success",
                "crosstab": combined_table,
                "marginal_totals": marginal_totals,
                "metadata": {
                    "survey_variable": survey_variable,
                    "demographic_variable": demographic_variable,
                    "wave": wave,
                    "table_suffix": wave_suffix,
                    "weighted": use_weights,
                    "total_n": total_n,
                    "cells_suppressed": suppressed_count,
                    "min_cell_size": MIN_CELL_SIZE,
                    "privacy_note": f"Cells with n<{MIN_CELL_SIZE} suppressed for privacy protection"
                },
                "suppressed_cells": [
                    {
                        demographic_variable: row[demographic_variable],
                        survey_variable: row[survey_variable],
                        "reason": row.get('note', '')
                    }
                    for row in suppressed_rows if row.get('suppressed', False)
                ] if suppressed_count > 0 else [],
                "message": (
                    f"Generated {'weighted' if use_weights else 'unweighted'} crosstab for wave {wave}. "
                    f"{suppressed_count} cell(s) suppressed for privacy (n<{MIN_CELL_SIZE})."
                )
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generating crosstab: {str(e)}",
                "error_type": type(e).__name__,
                "hint": "Use get_available_variables to see valid variable names."
            }

    async def run(self):
        """Run the MCP server."""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Main entry point."""
    server = SurveyAnalysisServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
