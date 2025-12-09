# CHIP50 Survey MCP Bundle - Installation Guide

## Bundle Information

**File:** `chip50MCP.mcpb` (21.3 KB)
**Version:** 1.0.0
**Type:** Python MCP Server (UV-based with PEP 723 inline dependencies)

## What's Included

The bundle contains only the essential files:
- `manifest.json` - Bundle metadata and configuration
- `mcp_server/server.py` - Main MCP server with inline dependencies
- `mcp_server/pyproject.toml` - Project metadata
- `README.md` - Documentation
- `chip50.png` - Extension icon

## Installation Steps

### 1. Uninstall Previous Version (If Installed)

**IMPORTANT:** If you previously installed this extension, you MUST uninstall it first to remove cached dependencies.

In Claude Desktop:
1. Go to Settings → Extensions
2. Find "CHIP50 Survey Analysis"
3. Click "Uninstall" or remove it
4. Restart Claude Desktop

### 2. Install the Bundle

1. Open Claude Desktop
2. Go to Settings → Extensions
3. Click "Install from file"
4. Select `chip50MCP.mcpb`
5. Wait for installation to complete
6. Restart Claude Desktop

### 3. Verify Installation

After restarting Claude Desktop, the extension should appear in your extensions list as "CHIP50 Survey Analysis".

To test it's working:
1. Start a new conversation
2. Ask: "What MCP tools are available?"
3. You should see two tools:
   - `upload_csv_to_bigquery`
   - `generate_bigquery_crosstab`

## How It Works

### Runtime Configuration

The bundle uses **UV** to manage Python dependencies automatically:

```json
"mcp_config": {
  "command": "python3",
  "args": ["${__dirname}/mcp_server/server.py"]
}
```

### Dependencies (PEP 723)

Dependencies are declared inline in [server.py](mcp_server/server.py) using PEP 723 format:

```python
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "pandas>=2.0.0",
#   "google-cloud-bigquery>=3.11.0",
#   "db-dtypes>=1.1.0",
#   "mcp>=0.9.0",
# ]
# ///
```

Python will automatically install these dependencies when the server first runs.

## Available Tools

### 1. upload_csv_to_bigquery

Upload CSV files (demographics or survey responses) to BigQuery tables.

**Required:**
- `csv_path` - Path to CSV file
- `project_id` - Google Cloud project ID
- `dataset_id` - BigQuery dataset ID
- `table_id` - BigQuery table ID

**Optional:**
- `write_disposition` - WRITE_TRUNCATE (default), WRITE_APPEND, or WRITE_EMPTY

### 2. generate_bigquery_crosstab

Generate weighted cross-tabulations using BigQuery.

**Required:**
- `project_id` - Google Cloud project ID
- `dataset_id` - BigQuery dataset ID
- `survey_variable` - Survey variable to analyze
- `demographic_variable` - Demographic grouping variable

**Optional:**
- `demographics_table` - Table name (default: "demographics")
- `survey_table` - Table name (default: "survey_responses")
- `waves` - Array of wave numbers to include
- `use_weights` - Use survey weights (default: true)
- `filter_conditions` - Additional SQL WHERE conditions

## Troubleshooting

### Extension Won't Start

**Error:** "ModuleNotFoundError: No module named 'pandas'"

**Solution:** This means an old venv is cached. Uninstall the extension completely:
1. Uninstall from Claude Desktop
2. Manually delete: `~/Library/Application Support/Claude/Claude Extensions/local.mcpb.stefan-wojcik.chip50mcp/`
3. Reinstall the bundle
4. Restart Claude Desktop

### Import Errors

**Error:** "ImportError: cannot import name 'bigquery' from 'google.cloud'"

**Solution:** Old dependencies cached. Follow the same uninstall procedure above.

### Server Disconnects Immediately

Check Claude Desktop logs for errors:
- macOS: `~/Library/Logs/Claude/mcp-*.log`

## Prerequisites

### System Requirements

- Python 3.8 or later
- UV package manager (will auto-install dependencies)
- Google Cloud credentials configured (for BigQuery access)

### Google Cloud Setup

To use BigQuery features:

```bash
# Install Google Cloud SDK
brew install --cask google-cloud-sdk

# Authenticate
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

## Development

To rebuild the bundle after making changes:

```bash
cd /path/to/chip50MCP
mcpb pack
```

The new bundle will be created as `chip50MCP.mcpb` in the project root.

## Support

- **Documentation:** [README.md](README.md)
- **Repository:** https://github.com/nanocentury-ai/chip50MCP
- **Issues:** Report at the GitHub repository

## License

MIT License - See LICENSE file for details
