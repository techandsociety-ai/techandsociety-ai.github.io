#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "pandas>=2.0.0",
#   "google-cloud-bigquery>=3.11.0",
#   "db-dtypes>=1.1.0",
#   "mcp>=0.9.0",
# ]
# ///
"""
CHIP50 Survey MCP Server

Provides tools for uploading survey data to BigQuery and generating
cross-tabulations of survey responses across demographic categories.
"""

import json
import sys
import asyncio
from typing import Any, Dict, List, Optional
import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

# MCP SDK imports
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
import mcp.server.stdio


class SurveyAnalysisServer:
    """MCP server for survey data analysis."""

    def __init__(self):
        self.server = Server("chip50-survey-mcp")
        self.bigquery_client = None
        self.project_id = None

        # Register tool handlers
        self.setup_handlers()

    def setup_handlers(self):
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="upload_csv_to_bigquery",
                    description=(
                        "Upload a CSV file to a BigQuery table. Creates the table if it doesn't exist. "
                        "Supports both demographic and substantive survey data."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "csv_path": {
                                "type": "string",
                                "description": "Path to the CSV file to upload"
                            },
                            "project_id": {
                                "type": "string",
                                "description": "Google Cloud project ID"
                            },
                            "dataset_id": {
                                "type": "string",
                                "description": "BigQuery dataset ID"
                            },
                            "table_id": {
                                "type": "string",
                                "description": "BigQuery table ID"
                            },
                            "write_disposition": {
                                "type": "string",
                                "enum": ["WRITE_TRUNCATE", "WRITE_APPEND", "WRITE_EMPTY"],
                                "description": "Write disposition: WRITE_TRUNCATE (overwrite), WRITE_APPEND (append), or WRITE_EMPTY (fail if exists)",
                                "default": "WRITE_TRUNCATE"
                            }
                        },
                        "required": ["csv_path", "project_id", "dataset_id", "table_id"]
                    }
                ),
                Tool(
                    name="generate_bigquery_crosstab",
                    description=(
                        "Generate weighted cross-tabulation using BigQuery. Joins demographics and survey "
                        "response tables and calculates weighted proportions for survey responses across "
                        "demographic categories. Returns both counts and percentages."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_id": {
                                "type": "string",
                                "description": "Google Cloud project ID"
                            },
                            "dataset_id": {
                                "type": "string",
                                "description": "BigQuery dataset ID"
                            },
                            "demographics_table": {
                                "type": "string",
                                "description": "Demographics table name (default: demographics)",
                                "default": "demographics"
                            },
                            "survey_table": {
                                "type": "string",
                                "description": "Survey responses table name (default: survey_responses)",
                                "default": "survey_responses"
                            },
                            "survey_variable": {
                                "type": "string",
                                "description": "Survey variable to analyze (e.g., 'trust_congress', 'approval_pres', 'vote_intention')"
                            },
                            "demographic_variable": {
                                "type": "string",
                                "description": "Demographic variable to group by (e.g., 'party_7', 'education_cat', 'age_cat_8', 'race', 'gender')"
                            },
                            "waves": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Wave numbers to include (optional, defaults to all waves)"
                            },
                            "use_weights": {
                                "type": "boolean",
                                "description": "Whether to use survey weights for weighted tabulation",
                                "default": True
                            },
                            "filter_conditions": {
                                "type": "string",
                                "description": "Additional SQL WHERE conditions (optional, e.g., 'state_code = \"CA\"')"
                            }
                        },
                        "required": ["project_id", "dataset_id", "survey_variable", "demographic_variable"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool calls."""
            try:
                if name == "upload_csv_to_bigquery":
                    result = await self.upload_csv_to_bigquery(
                        csv_path=arguments["csv_path"],
                        project_id=arguments["project_id"],
                        dataset_id=arguments["dataset_id"],
                        table_id=arguments["table_id"],
                        write_disposition=arguments.get("write_disposition", "WRITE_TRUNCATE")
                    )
                elif name == "generate_bigquery_crosstab":
                    result = await self.generate_bigquery_crosstab(
                        project_id=arguments["project_id"],
                        dataset_id=arguments["dataset_id"],
                        demographics_table=arguments.get("demographics_table", "demographics"),
                        survey_table=arguments.get("survey_table", "survey_responses"),
                        survey_variable=arguments["survey_variable"],
                        demographic_variable=arguments["demographic_variable"],
                        waves=arguments.get("waves"),
                        use_weights=arguments.get("use_weights", True),
                        filter_conditions=arguments.get("filter_conditions")
                    )
                else:
                    raise ValueError(f"Unknown tool: {name}")

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            except Exception as e:
                error_msg = f"Error executing {name}: {str(e)}"
                return [TextContent(type="text", text=error_msg)]

    async def upload_csv_to_bigquery(
        self,
        csv_path: str,
        project_id: str,
        dataset_id: str,
        table_id: str,
        write_disposition: str = "WRITE_TRUNCATE"
    ) -> Dict[str, Any]:
        """Upload CSV file to BigQuery."""
        try:
            # Initialize BigQuery client
            client = bigquery.Client(project=project_id)

            # Read CSV
            df = pd.read_csv(csv_path)

            # Create dataset if it doesn't exist
            dataset_ref = client.dataset(dataset_id)
            try:
                client.get_dataset(dataset_ref)
            except NotFound:
                dataset = bigquery.Dataset(dataset_ref)
                dataset.location = "US"
                client.create_dataset(dataset)

            # Define table reference
            table_ref = dataset_ref.table(table_id)

            # Configure load job
            job_config = bigquery.LoadJobConfig(
                write_disposition=write_disposition,
                autodetect=True,
            )

            # Load data
            job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
            job.result()  # Wait for job to complete

            # Get table info
            table = client.get_table(table_ref)

            return {
                "status": "success",
                "message": f"Uploaded {table.num_rows} rows to {project_id}.{dataset_id}.{table_id}",
                "rows": table.num_rows,
                "columns": len(table.schema),
                "table_path": f"{project_id}.{dataset_id}.{table_id}"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    async def generate_bigquery_crosstab(
        self,
        project_id: str,
        dataset_id: str,
        demographics_table: str,
        survey_table: str,
        survey_variable: str,
        demographic_variable: str,
        waves: Optional[List[int]] = None,
        use_weights: bool = True,
        filter_conditions: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate weighted cross-tabulation using BigQuery."""
        try:
            # Initialize BigQuery client
            client = bigquery.Client(project=project_id)

            # Build the base query with JOIN
            base_join = f"""
            SELECT
                d.{demographic_variable},
                s.{survey_variable},
                d.weight
            FROM `{project_id}.{dataset_id}.{demographics_table}` d
            INNER JOIN `{project_id}.{dataset_id}.{survey_table}` s
                ON d.id = s.id AND d.wave = s.wave
            WHERE d.{demographic_variable} IS NOT NULL
                AND s.{survey_variable} IS NOT NULL
            """

            # Add wave filter if specified
            if waves:
                wave_list = ','.join(map(str, waves))
                base_join += f" AND d.wave IN ({wave_list})"

            # Add additional filter conditions if specified
            if filter_conditions:
                base_join += f" AND {filter_conditions}"

            # Build weighted or unweighted crosstab query
            if use_weights:
                query = f"""
                WITH joined_data AS ({base_join})
                SELECT
                    {demographic_variable},
                    {survey_variable},
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

            # Convert to pandas DataFrame for easier processing
            df = results.to_dataframe()

            if len(df) == 0:
                return {
                    "status": "error",
                    "message": "No data returned from query. Check that tables exist and have matching data."
                }

            # Calculate percentages
            count_col = 'weighted_count' if use_weights else 'count'
            df['percentage'] = (df[count_col] / df['demographic_total'] * 100).round(2)

            # Create pivot table for display
            pivot_counts = df.pivot(
                index=demographic_variable,
                columns=survey_variable,
                values=count_col
            ).fillna(0)

            pivot_percentages = df.pivot(
                index=demographic_variable,
                columns=survey_variable,
                values='percentage'
            ).fillna(0)

            # Format combined table with counts and percentages
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
            total_n_query = f"""
            WITH joined_data AS ({base_join})
            SELECT COUNT(*) as total_n
            FROM joined_data
            """
            total_n_job = client.query(total_n_query)
            total_n_result = list(total_n_job.result())[0]
            total_n = total_n_result['total_n']

            # Get marginal totals by demographic category
            marginal_totals = df.groupby(demographic_variable)[count_col].sum().to_dict()
            marginal_totals = {str(k): float(v) for k, v in marginal_totals.items()}

            return {
                "status": "success",
                "crosstab": combined_table,
                "marginal_totals": marginal_totals,
                "survey_variable": survey_variable,
                "demographic_variable": demographic_variable,
                "weighted": use_weights,
                "total_n": total_n,
                "waves_included": waves if waves else "all",
                "query": query,
                "message": f"Generated {'weighted' if use_weights else 'unweighted'} crosstab for {survey_variable} by {demographic_variable}"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"BigQuery error: {str(e)}",
                "error_type": type(e).__name__
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
