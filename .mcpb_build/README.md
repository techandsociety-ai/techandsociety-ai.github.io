# CHIP50 Survey MCP Server

A Model Context Protocol (MCP) server for analyzing CHIP50 survey data using BigQuery. This package enables AI assistants to perform weighted cross-tabulations and statistical analysis of survey responses across demographic categories.

## Features

- **BigQuery Upload**: Upload CSV files (demographic and survey data) to BigQuery tables
- **BigQuery Cross-tabulation**: Generate weighted cross-tabs of survey responses by demographics directly in BigQuery
- **Synthetic Data**: Includes tools for generating realistic synthetic survey data for testing

## Installation

### Option 1: Install as MCPB Package (Recommended)

1. Download the `chip50MCP.mcpb` file from the releases
2. In Claude Desktop, go to Extensions → Install from file
3. Select the downloaded `.mcpb` file
4. The extension will install with all dependencies

### Option 2: Manual Installation for Development

**Prerequisites:**
- **uv** (Python package manager): https://docs.astral.sh/uv/
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "chip50-survey-mcp": {
      "command": "uv",
      "args": [
        "run",
        "/ABSOLUTE/PATH/TO/chip50MCP/mcp_server/server.py"
      ]
    }
  }
}
```

Replace `/ABSOLUTE/PATH/TO/` with your actual path.

See [INSTALLATION.md](INSTALLATION.md) for detailed setup instructions.

## Project Structure

```
chip50MCP/
├── mcp_server/
│   ├── server.py          # Main MCP server (with inline dependencies)
│   ├── mcpb.json          # MCPB package configuration
│   └── pyproject.toml     # Python package metadata
├── synthetic_data/
│   ├── generate_synthetic_data.py  # Synthetic data generator
│   ├── synthetic_demographics.csv  # Sample demographic data (1,500 rows)
│   └── synthetic_survey_responses.csv  # Sample survey responses (1,500 rows)
├── data/
│   └── [real survey data - gitignored]
├── INSTALLATION.md        # Detailed installation guide
├── QUICKSTART.md          # Quick start guide
└── requirements.txt       # Dependencies list
```

## Available Tools

### 1. upload_csv_to_bigquery

Upload CSV files to BigQuery tables.

**Parameters:**
- `csv_path` (string, required): Path to CSV file
- `project_id` (string, required): Google Cloud project ID
- `dataset_id` (string, required): BigQuery dataset ID
- `table_id` (string, required): BigQuery table ID
- `write_disposition` (string, optional): Write mode - `WRITE_TRUNCATE` (default), `WRITE_APPEND`, or `WRITE_EMPTY`

**Example:**
```json
{
  "csv_path": "synthetic_data/synthetic_demographics.csv",
  "project_id": "my-gcp-project",
  "dataset_id": "chip50_survey",
  "table_id": "demographics",
  "write_disposition": "WRITE_TRUNCATE"
}
```

### 2. generate_bigquery_crosstab

Generate weighted cross-tabulations using BigQuery. Joins demographics and survey response tables and calculates weighted proportions for survey responses across demographic categories.

**Parameters:**
- `project_id` (string, required): Google Cloud project ID
- `dataset_id` (string, required): BigQuery dataset ID
- `demographics_table` (string, optional): Demographics table name (default: `demographics`)
- `survey_table` (string, optional): Survey responses table name (default: `survey_responses`)
- `survey_variable` (string, required): Survey variable to analyze (e.g., `trust_congress`, `approval_pres`, `vote_intention`)
- `demographic_variable` (string, required): Demographic variable to group by (e.g., `party_7`, `education_cat`, `age_cat_8`, `race`, `gender`)
- `waves` (array of integers, optional): Wave numbers to include (optional, defaults to all waves)
- `use_weights` (boolean, optional): Use survey weights for weighted tabulation (default: true)
- `filter_conditions` (string, optional): Additional SQL WHERE conditions (e.g., `state_code = "CA"`)

**Example:**
```json
{
  "project_id": "my-gcp-project",
  "dataset_id": "chip50_survey",
  "survey_variable": "trust_congress",
  "demographic_variable": "party_7",
  "waves": [7, 8, 9],
  "use_weights": true
}
```

## Synthetic Data

### Demographic Variables

The synthetic dataset includes:
- `id`: Unique respondent UUID
- `wave`: Survey wave number (7, 8, 9)
- `age_cat_8`: 8-category age groups
- `education_cat`: Education level
- `income_cat_10`: 10-category income brackets
- `gender`: Gender identity
- `party_7`: 7-point party affiliation scale
- `race`: Racial/ethnic identity
- `urban_type`: Urban/Suburban/Rural
- `state_code`: US state code
- `weight`: Survey weight for population adjustment

### Survey Variables

The synthetic survey includes:
- Trust in institutions (1-5 scale): `trust_congress`, `trust_courts`, `trust_media`, `trust_military`
- Political approval (1-7 scale): `approval_pres`, `approval_governor`, `approval_senator`
- Issue importance (0-10 scale): `issue_economy`, `issue_healthcare`
- Categorical: `vote_intention`, `registered_voter`
- Thermometer rating (0-100): `party_thermometer`

### Generating New Synthetic Data

```bash
cd synthetic_data
python3 generate_synthetic_data.py
```

Modify the parameters in the script to adjust:
- Number of respondents (default: 500)
- Wave numbers (default: [7, 8, 9])
- Random seed for reproducibility

## Usage with Claude Desktop

Once installed, the MCP server will be available in Claude Desktop. You can use it to:

1. **Upload survey data to BigQuery** for cloud-based analysis
2. **Generate cross-tabs** to understand how responses vary across demographics using BigQuery's processing power

Example queries to Claude:
- "Upload the synthetic demographics file to BigQuery project 'my-project', dataset 'surveys', table 'demographics'"
- "Generate a weighted cross-tab of trust in Congress by party affiliation from BigQuery"
- "Show me how approval ratings vary by education level across waves 7, 8, and 9"

## BigQuery Setup

To use the BigQuery upload feature:

1. Install Google Cloud SDK
2. Authenticate: `gcloud auth application-default login`
3. Set project: `gcloud config set project YOUR_PROJECT_ID`
4. Ensure you have BigQuery Data Editor permissions

## Security & Privacy

- Synthetic data is safe for testing and development
- Real survey data contains PII and should NEVER be committed to version control
- When uploading to BigQuery, ensure proper IAM permissions and data governance
- Use separate GCP projects for dev/staging/production environments

## Development

### Running the Server Locally

The server uses `uv` with inline script dependencies (PEP 723):

```bash
cd mcp_server
uv run server.py
```

Dependencies are automatically installed and cached by `uv` on first run.

### Testing Tools

```bash
# Test the MCP server functionality
python3 test_mcp_server.py

# Or with uv's Python environment
uv run test_mcp_server.py
```

See `test_mcp_server.py` for example tool calls and expected outputs.

## License

MIT License - See LICENSE file for details

## Support

For issues and questions, please contact the CHIP50 team.
