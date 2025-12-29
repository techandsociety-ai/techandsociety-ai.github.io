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
        self._client_initialized = False

        # Cache for schema metadata to reduce BigQuery calls
        self._waves_cache = None
        self._schema_cache = {}

        # Validate API key on startup (lightweight check only)
        try:
            validate_api_key()
            print(f"✓ API key validated", file=sys.stderr)
            print(f"✓ Configuration: project={self.project_id}, dataset={self.dataset_public}", file=sys.stderr)
            print(f"✓ Cell suppression threshold: n≥{MIN_CELL_SIZE}", file=sys.stderr)
            print(f"✓ BigQuery connection will be established on first use", file=sys.stderr)
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
                        "Dynamically discovers waves and variables from BigQuery protected views. "
                        "Returns variable names, types, descriptions, and which waves each variable appears in. "
                        "Optionally filter to a specific wave. "
                        "Use this first to discover what data is available before generating crosstabs."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "wave": {
                                "type": "string",
                                "description": (
                                    "Optional wave identifier to filter results (e.g., '35', '35.1', '35_1'). "
                                    "If not specified, returns variables from all available waves with information "
                                    "about which waves contain each variable."
                                )
                            }
                        },
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
                ),
                Tool(
                    name="generate_marginals",
                    description=(
                        "Generate marginal distribution (overall frequencies) for a single survey or demographic variable. "
                        "Shows the overall distribution of responses without cross-tabulation. "
                        "Useful for understanding the baseline distribution of a variable before analyzing by demographics. "
                        "Returns weighted counts, percentages, and total sample size. "
                        "No cell suppression applied since this shows overall totals."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "variable": {
                                "type": "string",
                                "description": (
                                    "Variable to analyze (can be survey or demographic variable, e.g., 'pol_trust_congress', "
                                    "'party7', 'ai_freq_chatgpt'). Use get_available_variables to see all options."
                                )
                            },
                            "wave": {
                                "type": "string",
                                "description": (
                                    "Wave identifier to query (e.g., '35', '35_1', '36'). "
                                    "Required parameter."
                                )
                            },
                            "use_weights": {
                                "type": "boolean",
                                "description": "Whether to use survey weights for weighted tabulation (default: true)",
                                "default": True
                            }
                        },
                        "required": ["variable", "wave"]
                    }
                ),
                Tool(
                    name="generate_marginals_batch",
                    description=(
                        "Generate marginal distributions for multiple variables in a single call. "
                        "Efficiently analyzes multiple survey or demographic variables without requiring separate tool calls. "
                        "Executes queries in parallel for optimal performance. "
                        "Returns a dictionary mapping each variable to its distribution. "
                        "Use this when analyzing multiple variables (e.g., all AI-related questions) to reduce overhead."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "variables": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "List of variables to analyze (e.g., ['ai_freq_chatgpt', 'ai_freq_claude', 'party7']). "
                                    "Use get_available_variables to see all options."
                                )
                            },
                            "wave": {
                                "type": "string",
                                "description": (
                                    "Wave identifier to query (e.g., '35', '35_1', '36'). "
                                    "Required parameter."
                                )
                            },
                            "use_weights": {
                                "type": "boolean",
                                "description": "Whether to use survey weights for weighted tabulation (default: true)",
                                "default": True
                            }
                        },
                        "required": ["variables", "wave"]
                    }
                ),
                Tool(
                    name="generate_crosstab_batch",
                    description=(
                        "Generate cross-tabulations for a single survey variable across multiple demographic variables. "
                        "Efficiently analyzes how one survey question varies across different demographic breakdowns "
                        "(e.g., by party, education, age, race, region) in a single call. "
                        "Executes queries in parallel for optimal performance. "
                        "Returns a dictionary mapping each demographic variable to its crosstab. "
                        "Use this when comparing responses across multiple demographic groups."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "survey_variable": {
                                "type": "string",
                                "description": (
                                    "Survey variable to analyze (e.g., 'pol_trust_congress', 'pol_approval_pres'). "
                                    "Use get_available_variables to see all options."
                                )
                            },
                            "demographic_variables": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "List of demographic variables to group by (e.g., ['party7', 'educ', 'age_cat', 'race', 'region']). "
                                    "Use get_available_variables to see all options."
                                )
                            },
                            "wave": {
                                "type": "string",
                                "description": (
                                    "Wave identifier to query (e.g., '35', '35_1', '36'). "
                                    "Required parameter."
                                )
                            },
                            "use_weights": {
                                "type": "boolean",
                                "description": "Whether to use survey weights for weighted tabulation (default: true)",
                                "default": True
                            }
                        },
                        "required": ["survey_variable", "demographic_variables", "wave"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool calls."""
            try:
                if name == "get_available_variables":
                    result = await self.get_available_variables(
                        wave=arguments.get("wave")
                    )
                elif name == "generate_crosstab":
                    result = await self.generate_crosstab(
                        survey_variable=arguments["survey_variable"],
                        demographic_variable=arguments["demographic_variable"],
                        wave=arguments["wave"],
                        use_weights=arguments.get("use_weights", True)
                    )
                elif name == "generate_marginals":
                    result = await self.generate_marginals(
                        variable=arguments["variable"],
                        wave=arguments["wave"],
                        use_weights=arguments.get("use_weights", True)
                    )
                elif name == "generate_marginals_batch":
                    result = await self.generate_marginals_batch(
                        variables=arguments["variables"],
                        wave=arguments["wave"],
                        use_weights=arguments.get("use_weights", True)
                    )
                elif name == "generate_crosstab_batch":
                    result = await self.generate_crosstab_batch(
                        survey_variable=arguments["survey_variable"],
                        demographic_variables=arguments["demographic_variables"],
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

    def _get_bigquery_client(self) -> bigquery.Client:
        """
        Get or create BigQuery client with proper error handling.

        This is called lazily on first use to avoid blocking startup.
        """
        if self.bigquery_client is None:
            try:
                # Create client with reasonable timeout
                self.bigquery_client = bigquery.Client(
                    project=self.project_id,
                    default_query_job_config=bigquery.QueryJobConfig(
                        # Set default timeout for queries (5 minutes)
                        use_query_cache=True
                    )
                )

                # Test connection with a lightweight query
                if not self._client_initialized:
                    # Just check if we can list datasets (lightweight operation)
                    try:
                        list(self.bigquery_client.list_datasets(max_results=1))
                        self._client_initialized = True
                        print(f"✓ BigQuery connection established", file=sys.stderr)
                    except Exception as conn_err:
                        print(f"⚠ BigQuery connection warning: {conn_err}", file=sys.stderr)
                        print(f"⚠ Queries may fail until connection is established", file=sys.stderr)
                        # Don't fail here - let queries fail with proper error messages

            except Exception as e:
                print(f"✗ Failed to create BigQuery client: {e}", file=sys.stderr)
                raise RuntimeError(f"Cannot connect to BigQuery: {str(e)}")

        return self.bigquery_client

    async def _discover_available_waves(self) -> List[Dict[str, str]]:
        """
        Discover available waves by querying BigQuery dataset for protected tables.

        Returns list of wave dictionaries with wave number, table suffix, and description.
        Caches results to avoid repeated BigQuery calls.
        """
        # Return cached result if available
        if self._waves_cache is not None:
            return self._waves_cache

        try:
            client = self._get_bigquery_client()
            dataset_ref = f"{self.project_id}.{self.dataset_public}"

            # List all tables in the dataset with a limit to avoid huge responses
            # Use max_results to prevent loading thousands of tables
            tables = client.list_tables(dataset_ref, max_results=1000)

            # Find all protected tables and extract wave identifiers
            waves_found = set()
            table_count = 0
            for table in tables:
                table_count += 1
                table_name = table.table_id

                # Look for demographics_protected_w* or survey_responses_protected_w* tables
                if table_name.startswith("demographics_protected_w"):
                    wave_suffix = table_name.replace("demographics_protected_", "")
                    waves_found.add(wave_suffix)
                elif table_name.startswith("survey_responses_protected_w"):
                    wave_suffix = table_name.replace("survey_responses_protected_", "")
                    waves_found.add(wave_suffix)

                # Safety check: if we've looked at 1000 tables, stop
                if table_count >= 1000:
                    print(f"⚠ Stopped scanning after {table_count} tables", file=sys.stderr)
                    break

            # Convert to list of dictionaries with metadata
            waves_list = []
            for wave_suffix in sorted(waves_found):
                # Convert wave_suffix back to wave number: w35 -> 35, w35_1 -> 35.1
                wave_number = wave_suffix.replace('w', '').replace('_', '.')

                waves_list.append({
                    "wave": wave_number,
                    "table_suffix": wave_suffix,
                    "description": f"Wave {wave_number} data"
                })

            # Cache the result
            self._waves_cache = waves_list

            print(f"✓ Discovered {len(waves_list)} waves from {table_count} tables", file=sys.stderr)

            return waves_list

        except Exception as e:
            print(f"Warning: Could not discover waves: {e}", file=sys.stderr)
            # Return empty list if discovery fails
            return []

    async def _get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get column schema information from a BigQuery table.

        Args:
            table_name: Full table name (e.g., 'chip50.public.demographics_protected_w35')

        Returns:
            List of column dictionaries with name, type, and description
        """
        # Check cache first
        if table_name in self._schema_cache:
            return self._schema_cache[table_name]

        try:
            client = self._get_bigquery_client()
            table = client.get_table(table_name)

            columns = []
            for field in table.schema:
                # Skip internal/privacy columns
                if field.name in ['row_hash', 'weight']:
                    continue

                columns.append({
                    "name": field.name,
                    "type": field.field_type,
                    "description": field.description or f"{field.name} (no description)"
                })

            # Cache the result
            self._schema_cache[table_name] = columns

            return columns

        except Exception as e:
            print(f"Warning: Could not get schema for {table_name}: {e}", file=sys.stderr)
            return []

    async def get_available_variables(self, wave: str = None) -> Dict[str, Any]:
        """
        Get list of available survey and demographic variables.

        Dynamically queries BigQuery to discover waves and variable schemas.

        Args:
            wave: Optional wave identifier (e.g., '35', '35.1', '35_1').
                  If specified, returns variables for that wave only.
                  If None, discovers all waves and returns union of all variables.

        Returns:
            Dictionary with demographic variables, survey variables,
            available waves, and privacy notes.
        """
        try:
            # Discover all available waves
            all_waves = await self._discover_available_waves()

            if len(all_waves) == 0:
                return {
                    "status": "error",
                    "message": "No wave tables found in dataset. Check that protected views exist.",
                    "hint": f"Looking for tables in {self.project_id}.{self.dataset_public}"
                }

            # Determine which waves to query
            if wave is not None:
                # Convert wave format: '35' -> 'w35', '35.1' -> 'w35_1', '35_1' -> 'w35_1'
                wave_suffix = wave.replace('.', '_')
                if not wave_suffix.startswith('w'):
                    wave_suffix = f'w{wave_suffix}'

                # Find matching wave
                matching_waves = [w for w in all_waves if w['table_suffix'] == wave_suffix]
                if len(matching_waves) == 0:
                    return {
                        "status": "error",
                        "message": f"Wave '{wave}' not found.",
                        "available_waves": all_waves,
                        "hint": "Use one of the available waves listed above"
                    }
                waves_to_query = matching_waves
            else:
                # Query all waves
                waves_to_query = all_waves

            # Collect variables from each wave
            demographics_by_wave = {}
            survey_vars_by_wave = {}

            for wave_info in waves_to_query:
                wave_suffix = wave_info['table_suffix']
                wave_num = wave_info['wave']

                # Get demographics schema
                demo_table = f"{self.project_id}.{self.dataset_public}.demographics_protected_{wave_suffix}"
                demo_columns = await self._get_table_schema(demo_table)
                demographics_by_wave[wave_num] = demo_columns

                # Get survey responses schema
                survey_table = f"{self.project_id}.{self.dataset_public}.survey_responses_protected_{wave_suffix}"
                survey_columns = await self._get_table_schema(survey_table)
                survey_vars_by_wave[wave_num] = survey_columns

            # Aggregate variables across waves
            # Use a dict to track which waves have which variables
            all_demo_vars = {}
            all_survey_vars = {}

            for wave_num, columns in demographics_by_wave.items():
                for col in columns:
                    var_name = col['name']
                    if var_name not in all_demo_vars:
                        all_demo_vars[var_name] = {
                            "name": var_name,
                            "type": col['type'],
                            "description": col['description'],
                            "available_in_waves": []
                        }
                    all_demo_vars[var_name]['available_in_waves'].append(wave_num)

            for wave_num, columns in survey_vars_by_wave.items():
                for col in columns:
                    var_name = col['name']
                    if var_name not in all_survey_vars:
                        all_survey_vars[var_name] = {
                            "name": var_name,
                            "type": col['type'],
                            "description": col['description'],
                            "available_in_waves": []
                        }
                    all_survey_vars[var_name]['available_in_waves'].append(wave_num)

            # Convert to sorted lists
            demographic_variables = sorted(all_demo_vars.values(), key=lambda x: x['name'])
            survey_variables = sorted(all_survey_vars.values(), key=lambda x: x['name'])

            # Build response
            result = {
                "status": "success",
                "note": "Variables dynamically discovered from BigQuery protected views",
                "query_scope": f"Wave {wave}" if wave else "All waves",
                "available_waves": waves_to_query if wave else all_waves,
                "demographic_variables": demographic_variables,
                "survey_variables": survey_variables,
                "privacy_protections": {
                    "cell_suppression": f"Cells with n<{MIN_CELL_SIZE} automatically suppressed",
                    "geographic_aggregation": "State-level data aggregated to regions for privacy",
                    "user_ids": "Not accessible in protected views (row_hash used for joins)",
                    "free_text": "Excluded from protected views",
                    "wave_separation": "Each wave stored in separate tables to maintain schema flexibility"
                },
                "usage_note": "Variable availability may differ across waves. Check 'available_in_waves' for each variable."
            }

            return result

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error discovering variables: {str(e)}",
                "error_type": type(e).__name__
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
            # Get BigQuery client
            client = self._get_bigquery_client()

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

            # Execute query with timeout
            query_job = client.query(query)

            # Set a reasonable timeout (2 minutes) to prevent hanging
            try:
                results = query_job.result(timeout=120)
            except Exception as timeout_err:
                return {
                    "status": "error",
                    "message": f"Query timeout or error: {str(timeout_err)}",
                    "hint": "The query may be too complex or the dataset too large. Try a more specific query."
                }

            # Convert to list of dictionaries with size limit
            rows = []
            row_limit = 10000  # Limit to 10k rows to prevent memory issues
            for i, row in enumerate(results):
                if i >= row_limit:
                    print(f"⚠ Truncated results at {row_limit} rows to prevent memory issues", file=sys.stderr)
                    break
                rows.append(dict(row))

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
            # Use minimal memory by only keeping necessary columns
            try:
                df = pd.DataFrame(suppressed_rows)

                # Create pivot table (excluding suppressed cells for aggregates)
                non_suppressed = df[~df['suppressed']].copy()

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

                    # Get marginal totals (excluding suppressed)
                    marginal_totals = non_suppressed.groupby(demographic_variable)[count_col].sum().to_dict()
                    marginal_totals = {str(k): float(v) for k, v in marginal_totals.items()}
                else:
                    # All cells suppressed
                    pivot_counts = pd.DataFrame()
                    pivot_percentages = pd.DataFrame()
                    marginal_totals = {}

                # Clean up to free memory
                del non_suppressed

            except MemoryError as mem_err:
                return {
                    "status": "error",
                    "message": f"Out of memory processing results: {str(mem_err)}",
                    "hint": "The result set is too large. Try filtering to a smaller subset of data."
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error processing results: {str(e)}",
                    "error_type": type(e).__name__,
                    "hint": "There may be an issue with the data structure. Try a different variable combination."
                }

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

    async def generate_marginals(
        self,
        variable: str,
        wave: str,
        use_weights: bool = True
    ) -> Dict[str, Any]:
        """
        Generate marginal distribution (overall frequencies) for a single variable.

        Args:
            variable: Variable to analyze (survey or demographic)
            wave: Wave identifier (e.g., '35', '35_1')
            use_weights: Whether to use survey weights

        Returns:
            Dictionary with marginal distribution, metadata, and totals
        """
        try:
            # Get BigQuery client
            client = self._get_bigquery_client()

            # Convert wave format: '35' -> 'w35', '35.1' -> 'w35_1', '35_1' -> 'w35_1'
            wave_suffix = wave.replace('.', '_')
            if not wave_suffix.startswith('w'):
                wave_suffix = f'w{wave_suffix}'

            # Check if variable is in demographics or survey responses
            demographics_table = f"{self.project_id}.{self.dataset_public}.demographics_protected_{wave_suffix}"
            survey_table = f"{self.project_id}.{self.dataset_public}.survey_responses_protected_{wave_suffix}"

            # Try demographics first, then survey responses
            # Build query to check which table has the variable
            check_query = f"""
            SELECT
                CASE
                    WHEN EXISTS (
                        SELECT column_name
                        FROM `{self.project_id}.{self.dataset_public}.INFORMATION_SCHEMA.COLUMNS`
                        WHERE table_name = 'demographics_protected_{wave_suffix}'
                        AND column_name = '{variable}'
                    ) THEN 'demographics'
                    WHEN EXISTS (
                        SELECT column_name
                        FROM `{self.project_id}.{self.dataset_public}.INFORMATION_SCHEMA.COLUMNS`
                        WHERE table_name = 'survey_responses_protected_{wave_suffix}'
                        AND column_name = '{variable}'
                    ) THEN 'survey'
                    ELSE 'not_found'
                END as table_location
            """

            table_check = client.query(check_query).result()
            table_location = list(table_check)[0]['table_location']

            if table_location == 'not_found':
                return {
                    "status": "error",
                    "message": f"Variable '{variable}' not found in wave {wave}",
                    "hint": "Use get_available_variables to see valid variable names for this wave."
                }

            # Build marginals query
            if use_weights:
                if table_location == 'demographics':
                    query = f"""
                    SELECT
                        {variable},
                        COUNT(*) as n,
                        SUM(weight) as weighted_count
                    FROM `{demographics_table}`
                    WHERE {variable} IS NOT NULL
                    GROUP BY {variable}
                    ORDER BY {variable}
                    """
                else:
                    # Need to join with demographics for weights
                    query = f"""
                    SELECT
                        s.{variable},
                        COUNT(*) as n,
                        SUM(d.weight) as weighted_count
                    FROM `{survey_table}` s
                    INNER JOIN `{demographics_table}` d
                        ON s.row_hash = d.row_hash
                    WHERE s.{variable} IS NOT NULL
                    GROUP BY s.{variable}
                    ORDER BY s.{variable}
                    """
            else:
                # Unweighted query
                table_name = demographics_table if table_location == 'demographics' else survey_table
                query = f"""
                SELECT
                    {variable},
                    COUNT(*) as count
                FROM `{table_name}`
                WHERE {variable} IS NOT NULL
                GROUP BY {variable}
                ORDER BY {variable}
                """

            # Execute query
            query_job = client.query(query)
            results = query_job.result(timeout=120)

            # Convert to list
            rows = [dict(row) for row in results]

            if len(rows) == 0:
                return {
                    "status": "error",
                    "message": f"No data returned for variable '{variable}'",
                    "hint": "Variable may exist but have no non-null values."
                }

            # Calculate totals and percentages
            count_col = 'weighted_count' if use_weights else 'count'
            total = sum(row[count_col] for row in rows)
            total_n = sum(row.get('n', row.get('count', 0)) for row in rows)

            # Add percentages
            for row in rows:
                row['percentage'] = round((row[count_col] / total) * 100, 2)

            # Format results
            distribution = {}
            for row in rows:
                value = str(row[variable])
                distribution[value] = {
                    "count": float(row[count_col]),
                    "percentage": float(row['percentage']),
                    "n": int(row.get('n', row.get('count', 0))),
                    "display": f"{row[count_col]:.1f} ({row['percentage']:.1f}%)"
                }

            return {
                "status": "success",
                "distribution": distribution,
                "metadata": {
                    "variable": variable,
                    "wave": wave,
                    "table_suffix": wave_suffix,
                    "table_location": table_location,
                    "weighted": use_weights,
                    "total_n": total_n,
                    "total_count": float(total),
                    "unique_values": len(rows)
                },
                "message": f"Generated {'weighted' if use_weights else 'unweighted'} marginal distribution for {variable} in wave {wave}."
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generating marginals: {str(e)}",
                "error_type": type(e).__name__,
                "hint": "Use get_available_variables to see valid variable names."
            }

    async def generate_marginals_batch(
        self,
        variables: List[str],
        wave: str,
        use_weights: bool = True
    ) -> Dict[str, Any]:
        """
        Generate marginal distributions for multiple variables in parallel.

        Args:
            variables: List of variables to analyze
            wave: Wave identifier (e.g., '35', '35_1')
            use_weights: Whether to use survey weights

        Returns:
            Dictionary mapping variable names to their marginal distributions
        """
        try:
            # Execute all marginal queries in parallel using asyncio.gather
            tasks = [
                self.generate_marginals(variable=var, wave=wave, use_weights=use_weights)
                for var in variables
            ]

            results = await asyncio.gather(*tasks)

            # Create dictionary mapping variables to results
            results_dict = {}
            successful_count = 0
            failed_count = 0

            for var, result in zip(variables, results):
                results_dict[var] = result
                if result.get("status") == "success":
                    successful_count += 1
                else:
                    failed_count += 1

            return {
                "status": "success",
                "results": results_dict,
                "metadata": {
                    "total_variables": len(variables),
                    "successful": successful_count,
                    "failed": failed_count,
                    "wave": wave,
                    "weighted": use_weights
                },
                "message": f"Generated marginals for {successful_count}/{len(variables)} variables in wave {wave}."
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generating batch marginals: {str(e)}",
                "error_type": type(e).__name__,
                "hint": "Check that all variables exist in the specified wave."
            }

    async def generate_crosstab_batch(
        self,
        survey_variable: str,
        demographic_variables: List[str],
        wave: str,
        use_weights: bool = True
    ) -> Dict[str, Any]:
        """
        Generate cross-tabulations for one survey variable across multiple demographic variables.

        Args:
            survey_variable: Survey variable to analyze
            demographic_variables: List of demographic variables to group by
            wave: Wave identifier (e.g., '35', '35_1')
            use_weights: Whether to use survey weights

        Returns:
            Dictionary mapping demographic variables to their crosstabs
        """
        try:
            # Execute all crosstab queries in parallel using asyncio.gather
            tasks = [
                self.generate_crosstab(
                    survey_variable=survey_variable,
                    demographic_variable=demo_var,
                    wave=wave,
                    use_weights=use_weights
                )
                for demo_var in demographic_variables
            ]

            results = await asyncio.gather(*tasks)

            # Create dictionary mapping demographic variables to results
            results_dict = {}
            successful_count = 0
            failed_count = 0

            for demo_var, result in zip(demographic_variables, results):
                results_dict[demo_var] = result
                if result.get("status") == "success":
                    successful_count += 1
                else:
                    failed_count += 1

            return {
                "status": "success",
                "results": results_dict,
                "metadata": {
                    "survey_variable": survey_variable,
                    "total_demographics": len(demographic_variables),
                    "successful": successful_count,
                    "failed": failed_count,
                    "wave": wave,
                    "weighted": use_weights
                },
                "message": f"Generated crosstabs for {survey_variable} across {successful_count}/{len(demographic_variables)} demographic variables in wave {wave}."
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generating batch crosstabs: {str(e)}",
                "error_type": type(e).__name__,
                "hint": "Check that the survey variable and demographic variables exist in the specified wave."
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
