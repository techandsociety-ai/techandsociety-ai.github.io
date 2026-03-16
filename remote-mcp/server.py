#!/usr/bin/env python3
"""
Remote MCP Server for Social Media Demographics Analysis
Deployed on Google Cloud Run with SSE transport
"""

import os
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import secrets

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from google.cloud import bigquery

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.sse import SseServerTransport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
GCP_PROJECT = os.getenv("GCP_PROJECT", "your-project-id")
DATASET_NAME = os.getenv("DATASET_NAME", "social_media_demographics")
MIN_CELL_SIZE = int(os.getenv("MIN_CELL_SIZE", "10"))
API_KEY = os.getenv("API_KEY", "")  # Set this in deployment

# Generate a default API key if not set (for local testing)
if not API_KEY:
    API_KEY = f"smdem_{secrets.token_urlsafe(32)}"
    logger.warning(f"No API_KEY set. Generated temporary key: {API_KEY}")

# FastAPI app
app = FastAPI(
    title="Social Media Demographics MCP Server",
    description="Remote MCP server for analyzing social media usage across demographics",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SocialMediaMCPServer:
    """MCP Server for Social Media Demographics Analysis"""

    def __init__(self):
        self.server = Server("social-media-demographics")
        self._bq_client: Optional[bigquery.Client] = None
        self._available_variables_cache: Optional[Dict] = None

        # Register MCP tools
        self._register_tools()

    def _get_bigquery_client(self) -> bigquery.Client:
        """Get or create BigQuery client"""
        if self._bq_client is None:
            try:
                self._bq_client = bigquery.Client(project=GCP_PROJECT)
                # Test connection
                list(self._bq_client.list_datasets(max_results=1))
                logger.info(f"Connected to BigQuery project: {GCP_PROJECT}")
            except Exception as e:
                logger.error(f"Failed to connect to BigQuery: {e}")
                raise
        return self._bq_client

    def _register_tools(self):
        """Register all MCP tools"""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="get_available_variables",
                    description="Get list of available demographic and platform usage variables",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="generate_crosstab",
                    description="Generate cross-tabulation of platform usage by demographic variable with privacy protection (cell suppression for n<10)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "platform": {
                                "type": "string",
                                "description": "Platform to analyze (twitter, facebook, instagram, tiktok, linkedin, youtube, reddit, snapchat)",
                                "enum": ["twitter", "facebook", "instagram", "tiktok", "linkedin", "youtube", "reddit", "snapchat"]
                            },
                            "demographic": {
                                "type": "string",
                                "description": "Demographic variable (age_group, gender, race_ethnicity, education, income, political_affiliation, region, urbanicity)"
                            },
                            "use_weights": {
                                "type": "boolean",
                                "description": "Use population weights for estimates (default: true)",
                                "default": True
                            }
                        },
                        "required": ["platform", "demographic"]
                    }
                ),
                Tool(
                    name="generate_marginals",
                    description="Get overall distribution for a single variable (platform or demographic)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "variable": {
                                "type": "string",
                                "description": "Variable to analyze"
                            },
                            "use_weights": {
                                "type": "boolean",
                                "description": "Use population weights (default: true)",
                                "default": True
                            }
                        },
                        "required": ["variable"]
                    }
                ),
                Tool(
                    name="generate_crosstab_batch",
                    description="Generate crosstabs for one platform across multiple demographics in parallel",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "platform": {
                                "type": "string",
                                "description": "Platform to analyze"
                            },
                            "demographics": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of demographic variables"
                            },
                            "use_weights": {
                                "type": "boolean",
                                "description": "Use population weights (default: true)",
                                "default": True
                            }
                        },
                        "required": ["platform", "demographics"]
                    }
                ),
                Tool(
                    name="generate_marginals_batch",
                    description="Generate marginal distributions for multiple variables in parallel",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "variables": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of variables to analyze"
                            },
                            "use_weights": {
                                "type": "boolean",
                                "description": "Use population weights (default: true)",
                                "default": True
                            }
                        },
                        "required": ["variables"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Route tool calls to appropriate handlers"""
            try:
                if name == "get_available_variables":
                    result = await self._get_available_variables()
                elif name == "generate_crosstab":
                    result = await self._generate_crosstab(**arguments)
                elif name == "generate_marginals":
                    result = await self._generate_marginals(**arguments)
                elif name == "generate_crosstab_batch":
                    result = await self._generate_crosstab_batch(**arguments)
                elif name == "generate_marginals_batch":
                    result = await self._generate_marginals_batch(**arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")

                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            except Exception as e:
                logger.error(f"Error in {name}: {e}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": str(e),
                        "tool": name,
                        "timestamp": datetime.now().isoformat()
                    }, indent=2)
                )]

    async def _get_available_variables(self) -> Dict[str, Any]:
        """Get available variables from the dataset"""
        if self._available_variables_cache:
            return self._available_variables_cache

        try:
            client = self._get_bigquery_client()

            # Get demographics columns
            demo_table = client.get_table(f"{GCP_PROJECT}.{DATASET_NAME}.demographics_indexed")
            demo_fields = [field.name for field in demo_table.schema
                          if field.name not in ['respondent_id', 'row_hash', 'survey_date', 'wave', 'weight']]

            # Get platform usage columns
            platform_table = client.get_table(f"{GCP_PROJECT}.{DATASET_NAME}.platform_usage_indexed")
            platform_fields = [field.name for field in platform_table.schema
                             if field.name not in ['row_hash', 'wave']]

            result = {
                "demographics": demo_fields,
                "platforms": platform_fields,
                "available_platforms": [
                    "twitter", "facebook", "instagram", "tiktok",
                    "linkedin", "youtube", "reddit", "snapchat"
                ],
                "total_respondents": await self._get_total_respondents()
            }

            self._available_variables_cache = result
            return result

        except Exception as e:
            logger.error(f"Error getting variables: {e}")
            raise

    async def _get_total_respondents(self) -> int:
        """Get total number of respondents"""
        try:
            client = self._get_bigquery_client()
            query = f"SELECT COUNT(*) as n FROM `{GCP_PROJECT}.{DATASET_NAME}.demographics_indexed`"
            result = client.query(query).to_dataframe()
            return int(result['n'].iloc[0])
        except Exception as e:
            logger.error(f"Error getting total respondents: {e}")
            return 0

    async def _generate_crosstab(
        self,
        platform: str,
        demographic: str,
        use_weights: bool = True
    ) -> Dict[str, Any]:
        """Generate cross-tabulation with privacy protection"""
        try:
            client = self._get_bigquery_client()

            platform_col = f"{platform}_frequency"
            weight_clause = "* d.weight" if use_weights else ""

            query = f"""
            WITH crosstab AS (
              SELECT
                d.{demographic},
                p.{platform_col} as usage,
                COUNT(*) as n,
                SUM(1 {weight_clause}) as weighted_n
              FROM `{GCP_PROJECT}.{DATASET_NAME}.demographics_indexed` d
              JOIN `{GCP_PROJECT}.{DATASET_NAME}.platform_usage_indexed` p
                ON d.row_hash = p.row_hash
              WHERE p.{platform_col} IS NOT NULL
              GROUP BY d.{demographic}, p.{platform_col}
            )
            SELECT
              {demographic},
              usage,
              n,
              weighted_n,
              CASE WHEN n < {MIN_CELL_SIZE} THEN TRUE ELSE FALSE END as suppressed
            FROM crosstab
            ORDER BY {demographic}, usage
            """

            df = client.query(query).to_dataframe()

            # Apply cell suppression
            df.loc[df['suppressed'], 'n'] = None
            df.loc[df['suppressed'], 'weighted_n'] = None

            # Calculate percentages
            if use_weights:
                total = df[~df['suppressed']]['weighted_n'].sum()
                df['percentage'] = (df['weighted_n'] / total * 100).round(2)
            else:
                total = df[~df['suppressed']]['n'].sum()
                df['percentage'] = (df['n'] / total * 100).round(2)

            df.loc[df['suppressed'], 'percentage'] = None

            return {
                "platform": platform,
                "demographic": demographic,
                "use_weights": use_weights,
                "data": df.to_dict(orient='records'),
                "suppression_note": f"Cells with n<{MIN_CELL_SIZE} are suppressed for privacy",
                "total_responses": int(total) if not use_weights else round(total, 2)
            }

        except Exception as e:
            logger.error(f"Error generating crosstab: {e}")
            raise

    async def _generate_marginals(
        self,
        variable: str,
        use_weights: bool = True
    ) -> Dict[str, Any]:
        """Generate marginal distribution for a variable"""
        try:
            client = self._get_bigquery_client()

            # Determine if platform or demographic variable
            variables = await self._get_available_variables()

            if variable in variables['platforms']:
                table = f"{GCP_PROJECT}.{DATASET_NAME}.platform_usage_indexed"
                join_clause = f"""
                JOIN `{GCP_PROJECT}.{DATASET_NAME}.demographics_indexed` d
                  ON t.row_hash = d.row_hash
                """
                weight_col = "d.weight"
            else:
                table = f"{GCP_PROJECT}.{DATASET_NAME}.demographics_indexed"
                join_clause = ""
                weight_col = "t.weight"

            weight_clause = f"* {weight_col}" if use_weights else ""

            query = f"""
            SELECT
              t.{variable} as value,
              COUNT(*) as n,
              SUM(1 {weight_clause}) as weighted_n,
              CASE WHEN COUNT(*) < {MIN_CELL_SIZE} THEN TRUE ELSE FALSE END as suppressed
            FROM `{table}` t
            {join_clause}
            WHERE t.{variable} IS NOT NULL
            GROUP BY t.{variable}
            ORDER BY t.{variable}
            """

            df = client.query(query).to_dataframe()

            # Apply suppression
            df.loc[df['suppressed'], 'n'] = None
            df.loc[df['suppressed'], 'weighted_n'] = None

            # Calculate percentages
            if use_weights:
                total = df[~df['suppressed']]['weighted_n'].sum()
                df['percentage'] = (df['weighted_n'] / total * 100).round(2)
            else:
                total = df[~df['suppressed']]['n'].sum()
                df['percentage'] = (df['n'] / total * 100).round(2)

            df.loc[df['suppressed'], 'percentage'] = None

            return {
                "variable": variable,
                "use_weights": use_weights,
                "data": df.to_dict(orient='records'),
                "total_responses": int(total) if not use_weights else round(total, 2)
            }

        except Exception as e:
            logger.error(f"Error generating marginals: {e}")
            raise

    async def _generate_crosstab_batch(
        self,
        platform: str,
        demographics: List[str],
        use_weights: bool = True
    ) -> Dict[str, Any]:
        """Generate multiple crosstabs in parallel"""
        tasks = [
            self._generate_crosstab(platform, demo, use_weights)
            for demo in demographics
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "platform": platform,
            "demographics": demographics,
            "results": {
                demo: result if not isinstance(result, Exception) else {"error": str(result)}
                for demo, result in zip(demographics, results)
            }
        }

    async def _generate_marginals_batch(
        self,
        variables: List[str],
        use_weights: bool = True
    ) -> Dict[str, Any]:
        """Generate multiple marginals in parallel"""
        tasks = [
            self._generate_marginals(var, use_weights)
            for var in variables
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "variables": variables,
            "results": {
                var: result if not isinstance(result, Exception) else {"error": str(result)}
                for var, result in zip(variables, results)
            }
        }


# Initialize MCP server
mcp_server = SocialMediaMCPServer()


def verify_api_key(authorization: Optional[str] = Header(None)) -> bool:
    """Verify API key from Authorization header"""
    if not authorization:
        return False

    # Support both "Bearer <key>" and just "<key>"
    key = authorization.replace("Bearer ", "").strip()
    return key == API_KEY


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "name": "Social Media Demographics MCP Server",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health():
    """Health check for Cloud Run"""
    try:
        # Test BigQuery connection
        client = mcp_server._get_bigquery_client()
        list(client.list_datasets(max_results=1))
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.post("/sse")
async def handle_sse(request: Request, authorization: Optional[str] = Header(None)):
    """SSE endpoint for MCP protocol"""

    # Verify API key
    if not verify_api_key(authorization):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    # Create SSE transport
    async with SseServerTransport("/messages") as transport:
        # Connect transport to server
        await mcp_server.server.connect(transport)

        # Stream events
        async def event_generator():
            async for event in transport:
                yield event

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )


@app.get("/info")
async def info(authorization: Optional[str] = Header(None)):
    """Get server information (requires auth)"""
    if not verify_api_key(authorization):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    return {
        "server": "social-media-demographics",
        "project": GCP_PROJECT,
        "dataset": DATASET_NAME,
        "min_cell_size": MIN_CELL_SIZE,
        "tools": [
            "get_available_variables",
            "generate_crosstab",
            "generate_marginals",
            "generate_crosstab_batch",
            "generate_marginals_batch"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
