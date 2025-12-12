# CHIP50 MCP Server - Quick Start Guide

Get started with the CHIP50 survey data MCP server in Claude Desktop.

## Prerequisites

1. **Google Cloud Authentication**
   ```bash
   gcloud auth application-default login
   gcloud config set project chip50
   ```

2. **UV Package Manager** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Protected Views** (should already be set up)
   - `chip50.public.demographics_protected`
   - `chip50.public.survey_responses_protected`

## Step 1: Configure Environment Variables

Create a `.env` file in your project root (optional):

```bash
# CHIP50 Configuration
export CHIP50_API_KEY="chip50_test_synthetic_data_only"
export CHIP50_PROJECT_ID="chip50"
export CHIP50_DATASET_PUBLIC="public"
export CHIP50_MIN_CELL_SIZE="10"

# Google Cloud credentials (if not using gcloud default)
# export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

## Step 2: Configure Claude Desktop

Edit your Claude Desktop MCP configuration file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Add the CHIP50 MCP server:

```json
{
  "mcpServers": {
    "chip50": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/electron/workspace/Nanocentury AI/CHIP50/chip50MCP",
        "python",
        "mcp_server/server.py"
      ],
      "env": {
        "CHIP50_API_KEY": "chip50_test_synthetic_data_only",
        "CHIP50_PROJECT_ID": "chip50",
        "CHIP50_DATASET_PUBLIC": "public"
      }
    }
  }
}
```

**Important:** Update the `--directory` path to match your local installation path!

## Step 3: Restart Claude Desktop

After updating the configuration, restart Claude Desktop completely (Quit and reopen).

## Step 4: Verify Connection

In Claude Desktop, you should see the CHIP50 MCP server tools available. Try asking:

```
What data is available in the CHIP50 dataset?
```

Claude should call the `get_available_variables` tool and show you demographic and survey variables.

## Example Usage

### 1. Discover Available Variables

**Ask Claude:**
> "What survey variables are available in the CHIP50 data?"

**Claude calls:** `get_available_variables()`

**Returns:**
- Demographic variables (region, age, education, party, etc.)
- Survey variables (trust scales, approval ratings, etc.)
- Wave information
- Privacy protections summary

### 2. Generate Simple Crosstab

**Ask Claude:**
> "Show me trust in Congress by party affiliation"

**Claude calls:** `generate_crosstab(survey_variable="trust_congress", demographic_variable="party_7")`

**Returns:**
```json
{
  "status": "success",
  "crosstab": {
    "1": {"1": {"count": 105.2, "percentage": 26.1}, ...},
    "2": {"1": {"count": 58.3, "percentage": 25.6}, ...},
    ...
  },
  "metadata": {
    "total_n": 1500,
    "cells_suppressed": 0,
    "privacy_note": "Cells with n<10 suppressed"
  }
}
```

### 3. Filter by Wave

**Ask Claude:**
> "Show me vote intention by region for wave 9 only"

**Claude calls:**
```python
generate_crosstab(
    survey_variable="vote_intention",
    demographic_variable="region",
    waves=[9]
)
```

### 4. See Cell Suppression in Action

**Ask Claude:**
> "Break down trust in media by race"

If any race category has fewer than 10 respondents for a given trust level, those cells will be suppressed:

```json
{
  "metadata": {
    "cells_suppressed": 3,
    "privacy_note": "Cells with n<10 suppressed for privacy protection"
  },
  "suppressed_cells": [
    {
      "race": "Native American",
      "trust_media": 1,
      "reason": "n<10 (privacy protection)"
    }
  ]
}
```

## Available Variables

### Demographic Variables
- `region` - Geographic region (Northeast, Mid-Atlantic, Midwest, South, West)
- `age_cat_8` - Age category (8 groups)
- `education_cat` - Education level
- `income_cat_10` - Income bracket (1-10)
- `gender` - Gender identity
- `party_7` - Party identification (1=Strong Dem, 7=Strong Rep)
- `race` - Race/ethnicity
- `urban_type` - Urban/Suburban/Rural

### Survey Variables
- `trust_congress` - Trust in Congress (1-5 scale)
- `trust_courts` - Trust in courts (1-5 scale)
- `trust_media` - Trust in media (1-5 scale)
- `trust_military` - Trust in military (1-5 scale)
- `approval_pres` - Presidential approval (1-7 scale)
- `approval_governor` - Governor approval (1-7 scale)
- `approval_senator` - Senator approval (1-7 scale)
- `issue_economy` - Economy importance (0-10 scale)
- `issue_healthcare` - Healthcare importance (0-10 scale)
- `vote_intention` - Voting intention (categorical)
- `registered_voter` - Voter registration (0/1)
- `party_thermometer` - Party feeling thermometer (0-100)

## Privacy Protections

The CHIP50 MCP server implements automatic privacy protections:

### 1. Cell Suppression (n≥10)
- Any crosstab cell with fewer than 10 observations is automatically suppressed
- Suppressed cells show `[suppressed]` instead of values
- Suppression metadata included in results

### 2. Geographic Aggregation
- State-level data aggregated to 5 regions
- Cannot access individual state codes through protected views

### 3. No User IDs
- User IDs (`id`) not accessible in protected views
- Uses non-reversible `row_hash` for internal JOINs

### 4. No Free Text
- Free-text responses excluded from protected views

## Common Questions

### Q: How do I see what variables exist?
**A:** Ask Claude: "What variables are available?" or call `get_available_variables`

### Q: What does "suppressed" mean?
**A:** Cells with fewer than 10 respondents are hidden for privacy protection (k-anonymity)

### Q: Can I see state-level data?
**A:** No, states are aggregated to 5 regions for privacy. Use `demographic_variable="region"`

### Q: Can I filter by specific conditions?
**A:** Currently, you can filter by `waves`. Additional filters planned for future versions.

### Q: Are the results weighted?
**A:** Yes, by default. Set `use_weights=false` for unweighted counts.

### Q: How many respondents are in the dataset?
**A:** 500 unique respondents, 1,500 total observations (3 waves)

## Troubleshooting

### Error: "CHIP50_API_KEY environment variable not set"
**Solution:** Add the API key to your Claude Desktop configuration:
```json
"env": {
  "CHIP50_API_KEY": "chip50_test_synthetic_data_only"
}
```

### Error: "Invalid API key"
**Solution:** For testing, use exactly: `chip50_test_synthetic_data_only"

### Error: "No data returned"
**Solution:** Check variable names with `get_available_variables` - names are case-sensitive

### Server not appearing in Claude Desktop
1. Check that the `--directory` path is correct in your config
2. Verify UV is installed: `uv --version`
3. Check Claude Desktop logs (Help → View Logs)
4. Restart Claude Desktop completely

### BigQuery Authentication Errors
**Solution:**
```bash
# Re-authenticate
gcloud auth application-default login

# Verify project
gcloud config get-value project

# Should return: chip50
```

## Example Analyses

### 1. Political Polarization
> "Compare trust in Congress between strong Democrats (party_7=1) and strong Republicans (party_7=7)"

### 2. Regional Differences
> "How does presidential approval vary across regions?"

### 3. Demographic Patterns
> "Show me vote intention by education level"

### 4. Issue Salience
> "What is the average importance of economy vs healthcare issues by party?"

### 5. Multi-Variable Analysis
> "Show trust in courts by region, and tell me if there are any patterns"

## Next Steps

- **Explore the data:** Ask Claude to generate various crosstabs
- **Test privacy protections:** Try small demographic groups to see cell suppression
- **Provide feedback:** Report any issues or suggestions
- **Read the documentation:** See [buildplan.md](buildplan.md) for technical details

## Getting Help

- **Technical docs:** [buildplan.md](buildplan.md)
- **Setup guide:** [SETUP.md](SETUP.md)
- **Project status:** [PROJECT_STATUS.md](PROJECT_STATUS.md)
- **Phase 3 plan:** [PHASE3_PLAN.md](PHASE3_PLAN.md)

---

**Note:** This is a testing version using synthetic data. Production authentication with Firestore and registration will be added in Phase 4.
