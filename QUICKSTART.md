# CHIP50 Survey MCP - Quick Start Guide

## What Was Built

A complete Model Context Protocol (MCP) server for survey data analysis with:

✅ **Synthetic Data Generation** - 500 respondents across 3 waves (7, 8, 9) with realistic demographic and survey response distributions
✅ **BigQuery Upload Tool** - Upload CSV files to Google Cloud BigQuery
✅ **Cross-Tabulation Tool** - Generate weighted/unweighted crosstabs of survey responses by demographics
✅ **Summary Statistics Tool** - Calculate weighted means, medians, and distributions
✅ **MCPB Package** - Installable MCP server with bundled dependencies

## Project Structure

```
chip50MCP/
├── mcp_server/
│   ├── server.py          # MCP server with 3 tools
│   ├── mcpb.json          # Package configuration
│   └── lib/               # Bundled dependencies (pandas, numpy, bigquery, mcp)
│
├── synthetic_data/
│   ├── generate_synthetic_data.py
│   ├── synthetic_demographics.csv     # 1,500 rows (500 respondents × 3 waves)
│   └── synthetic_survey_responses.csv # 1,500 rows with 12 survey variables
│
├── test_mcp_server.py     # Test suite
├── README.md              # Full documentation
└── requirements.txt       # Dependencies list
```

## Installation & Testing

### 1. Verify Synthetic Data

```bash
python3 test_mcp_server.py
```

Expected output: All tests pass ✓

### 2. Install as MCPB Package

To make this MCP server available to Claude Code:

```bash
# Option A: Install locally (for development)
cd mcp_server
# Add to your MCP settings manually

# Option B: Create mcpb package (for distribution)
# Package the mcp_server directory as chip50-survey-mcp.mcpb
# Then: mcp install chip50-survey-mcp.mcpb
```

## Using the MCP Server

Once installed, you can use these tools in Claude Code:

### Tool 1: Upload to BigQuery

```
Upload the synthetic demographics to BigQuery:
- Project: my-gcp-project
- Dataset: chip50_surveys
- Table: demographics
```

### Tool 2: Generate Cross-Tabulations

```
Create a weighted cross-tab of trust in Congress by party affiliation using all waves
```

```
Show me vote intention by education level for wave 9 only
```

### Tool 3: Summary Statistics

```
Calculate weighted summary statistics for all trust variables across waves 7-9
```

## Synthetic Data Details

### Demographics (11 variables, 1,500 rows)
- `id` - UUID for respondent
- `wave` - Survey wave (7, 8, or 9)
- `age_cat_8` - 8 age categories
- `education_cat` - 5 education levels
- `income_cat_10` - Income deciles (1-10)
- `gender` - Male, Female, Non-binary, Prefer not to say
- `party_7` - 7-point party scale (1=Strong Dem to 7=Strong Rep)
- `race` - 7 racial/ethnic categories
- `urban_type` - Urban, Suburban, Rural
- `state_code` - US state abbreviation
- `weight` - Survey weight (0.2 to 3.0)

### Survey Questions (12 variables, 1,500 rows)
- **Trust in institutions** (1-5 scale): congress, courts, media, military
- **Political approval** (1-7 scale): president, governor, senator
- **Issue importance** (0-10 scale): economy, healthcare
- **Vote intention** (categorical): "Definitely will vote", "Probably will vote", etc.
- **Registered voter** (binary): 0 or 1
- **Party thermometer** (0-100 continuous)

## Example Outputs

### Cross-Tab Example
```json
{
  "crosstab": {
    "1": {
      "1": "93.2 (23.3%)",
      "2": "54.0 (23.5%)",
      ...
    }
  },
  "summary": {"mean": 2.43, "n": 1500},
  "weight_note": "weighted"
}
```

Rows = demographic variable (e.g., party_7)
Columns = survey response (e.g., trust level 1-5)
Values = weighted count (percentage within row)

### Summary Stats Example
```json
{
  "trust_congress": {
    "mean": 2.431,
    "min": 1.0,
    "max": 5.0,
    "n": 1500,
    "weighted": true
  }
}
```

## Next Steps

### For Real Data

1. **Never commit real data** - See `.gitignore`
2. **Replace synthetic data** - Place real CSVs in `data/` directory
3. **Use same column names** - Match the schema from synthetic data
4. **Set up BigQuery**
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

### Customization

- **Add more survey questions**: Modify `generate_synthetic_data.py`
- **Change sample size**: Edit `n_respondents` parameter
- **Add more waves**: Modify `waves=[7,8,9]` list
- **Add new MCP tools**: Edit `mcp_server/server.py`

## Troubleshooting

**"ModuleNotFoundError"**
→ Dependencies not in lib/. Run: `python3 -m pip install --target=mcp_server/lib pandas numpy google-cloud-bigquery mcp`

**"Weights sum to zero"**
→ IDs don't match between demographics and survey CSVs. Regenerate synthetic data.

**"Table not found" in BigQuery**
→ Authenticate: `gcloud auth application-default login`

## Testing Checklist

- [x] Synthetic data generated (1,500 rows each)
- [x] IDs match between demographics and survey data
- [x] Cross-tabs work for numeric variables (trust, approval)
- [x] Cross-tabs work for categorical variables (vote_intention)
- [x] Summary stats calculate weighted means
- [x] Handles missing waves parameter (uses all waves)
- [ ] BigQuery upload (requires GCP credentials)

## Support

For questions about this MCP server, refer to:
- `README.md` - Full documentation
- `test_mcp_server.py` - Example usage
- MCP docs: https://modelcontextprotocol.io
