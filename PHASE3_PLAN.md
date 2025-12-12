# Phase 3 Implementation Plan: Basic MCP Server

## Goal
Get core MCP functionality working for stakeholder validation using direct BigQuery access with synthetic data.

## Architecture (MVP)

```
┌─────────────────────────────────────┐
│ Claude Desktop                      │
│  └─ MCP Client                      │
└──────────┬──────────────────────────┘
           │ stdio
           ▼
┌─────────────────────────────────────┐
│ Local MCP Server (FastMCP)          │
│  - Simple API key validation        │
│  - Direct BigQuery queries          │
│  - Cell suppression (n≥10)          │
│  - Uses protected views              │
└──────────┬──────────────────────────┘
           │ Service Account Auth
           ▼
┌─────────────────────────────────────┐
│ BigQuery (chip50 project)           │
│  - chip50.public.demographics_protected   │
│  - chip50.public.survey_responses_protected │
└─────────────────────────────────────┘
```

## Changes from Original Plan

### Simplified (MVP)
- ❌ No remote FastAPI server (direct BigQuery instead)
- ❌ No Firestore (test API key hardcoded)
- ❌ No rate limiting (not needed for synthetic data testing)
- ❌ No registration system (stakeholder testing only)
- ❌ No audit logging (can be added later if needed)

### Kept
- ✅ Protected BigQuery views (already complete)
- ✅ Cell suppression (n≥10 threshold)
- ✅ Privacy protections (no PII exposure)
- ✅ MCP protocol via FastMCP
- ✅ Crosstab generation tool

## Implementation Tasks

### Task 1: Update MCP Server Configuration
**File:** `mcp_server/server.py`

**Changes needed:**
1. Keep direct BigQuery client (already present)
2. Add simple API key validation
3. Update to query protected views (`chip50.public.*` instead of `chip50.raw.*`)
4. Add cell suppression function

**New environment variables:**
```bash
CHIP50_API_KEY=chip50_test_synthetic_data_only
CHIP50_PROJECT_ID=chip50
CHIP50_DATASET_PUBLIC=public
```

### Task 2: Implement Cell Suppression
**New function in:** `mcp_server/server.py`

```python
def suppress_small_cells(
    results: list[dict],
    min_cell_size: int = 10
) -> tuple[list[dict], int]:
    """
    Suppress cells with counts below threshold.

    Args:
        results: List of result dictionaries from crosstab
        min_cell_size: Minimum cell size (default: 10)

    Returns:
        (suppressed_results, count_of_suppressed_cells)
    """
    suppressed_count = 0
    suppressed_results = []

    for row in results:
        # Check if count/n field is below threshold
        count_field = row.get('count') or row.get('n') or row.get('weighted_count')

        if count_field is not None and count_field < min_cell_size:
            # Suppress this cell
            suppressed_count += 1
            row['count'] = '[suppressed]'
            row['percentage'] = '[suppressed]'
            row['note'] = f'n<{min_cell_size}'

        suppressed_results.append(row)

    return suppressed_results, suppressed_count
```

### Task 3: Update generate_crosstab Tool
**File:** `mcp_server/server.py`

**Updates:**
1. Query `chip50.public.demographics_protected` and `chip50.public.survey_responses_protected`
2. Use `row_hash` for JOIN (not `id`)
3. Filter by `region` (not `state_code`)
4. Apply cell suppression to results
5. Add metadata about suppression

**Updated SQL template:**
```sql
WITH joined_data AS (
  SELECT
    d.{demographic_variable},
    s.{survey_variable},
    d.weight,
    d.wave
  FROM `chip50.public.demographics_protected` d
  JOIN `chip50.public.survey_responses_protected` s
    ON d.row_hash = s.row_hash AND d.wave = s.wave
  WHERE d.{demographic_variable} IS NOT NULL
    AND s.{survey_variable} IS NOT NULL
    {wave_filter}
)
SELECT
  {demographic_variable},
  COUNT(*) as n,
  SUM(weight) as weighted_count,
  ROUND(AVG(CAST({survey_variable} AS FLOAT64)), 2) as mean_value,
  ROUND(STDDEV(CAST({survey_variable} AS FLOAT64)), 2) as sd_value
FROM joined_data
GROUP BY {demographic_variable}
ORDER BY {demographic_variable}
```

### Task 4: Add get_available_variables Tool
**New tool in:** `mcp_server/server.py`

```python
@mcp.tool()
def get_available_variables() -> dict:
    """
    Get list of available survey and demographic variables.

    Returns dictionary with:
    - demographic_variables: List of demographic breakdown options
    - survey_variables: List of survey question variables
    - waves: Available wave numbers
    """
    return {
        "demographic_variables": [
            {"name": "region", "description": "Geographic region (Northeast, South, etc.)"},
            {"name": "age_cat_8", "description": "Age category (8 groups)"},
            {"name": "education_cat", "description": "Education level"},
            {"name": "income_cat_10", "description": "Income bracket (1-10)"},
            {"name": "gender", "description": "Gender identity"},
            {"name": "party_7", "description": "Party identification (7-point scale)"},
            {"name": "race", "description": "Race/ethnicity"},
            {"name": "urban_type", "description": "Urban/Suburban/Rural"}
        ],
        "survey_variables": [
            {"name": "trust_congress", "description": "Trust in Congress (1-5 scale)", "scale": "1=Strongly distrust, 5=Strongly trust"},
            {"name": "trust_courts", "description": "Trust in courts (1-5 scale)", "scale": "1=Strongly distrust, 5=Strongly trust"},
            {"name": "trust_media", "description": "Trust in media (1-5 scale)", "scale": "1=Strongly distrust, 5=Strongly trust"},
            {"name": "trust_military", "description": "Trust in military (1-5 scale)", "scale": "1=Strongly distrust, 5=Strongly trust"},
            {"name": "approval_pres", "description": "Presidential approval (1-7 scale)", "scale": "1=Strongly disapprove, 7=Strongly approve"},
            {"name": "approval_governor", "description": "Governor approval (1-7 scale)", "scale": "1=Strongly disapprove, 7=Strongly approve"},
            {"name": "approval_senator", "description": "Senator approval (1-7 scale)", "scale": "1=Strongly disapprove, 7=Strongly approve"},
            {"name": "issue_economy", "description": "Economy issue importance (0-10 scale)", "scale": "0=Not important, 10=Extremely important"},
            {"name": "issue_healthcare", "description": "Healthcare issue importance (0-10 scale)", "scale": "0=Not important, 10=Extremely important"},
            {"name": "vote_intention", "description": "Voting intention (categorical)", "scale": "Definitely/Probably will vote, Unsure, etc."},
            {"name": "registered_voter", "description": "Voter registration status (binary)", "scale": "1=Registered, 0=Not registered"},
            {"name": "party_thermometer", "description": "Party feeling thermometer (0-100)", "scale": "0=Very cold, 100=Very warm"}
        ],
        "waves": [7, 8, 9],
        "privacy_note": "Data accessed through protected views with cell suppression (n≥10). User IDs removed, geography aggregated to regions."
    }
```

### Task 5: Add Simple API Key Validation
**New function in:** `mcp_server/server.py`

```python
import os

# Simple test API key for synthetic data
TEST_API_KEY = "chip50_test_synthetic_data_only"

def validate_api_key() -> bool:
    """
    Validate API key from environment variable.
    For MVP: Simple comparison to test key.
    """
    api_key = os.environ.get("CHIP50_API_KEY", "")

    if not api_key:
        raise ValueError(
            "CHIP50_API_KEY environment variable not set. "
            "Set it to: chip50_test_synthetic_data_only"
        )

    if api_key != TEST_API_KEY:
        raise ValueError(
            f"Invalid API key. For testing, use: {TEST_API_KEY}"
        )

    return True

# Call on server startup
validate_api_key()
```

### Task 6: Update Claude Desktop Configuration
**File:** `~/.config/claude/config.json` (or equivalent)

```json
{
  "mcpServers": {
    "chip50": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/chip50MCP",
        "python",
        "mcp_server/server.py"
      ],
      "env": {
        "CHIP50_API_KEY": "chip50_test_synthetic_data_only",
        "CHIP50_PROJECT_ID": "chip50",
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service-account-key.json"
      }
    }
  }
}
```

### Task 7: Create Setup Documentation
**New file:** `QUICKSTART.md`

Document:
1. How to set up the API key environment variable
2. How to configure Claude Desktop
3. Example queries to test
4. How to interpret results with cell suppression

## Testing Checklist

- [ ] MCP server starts without errors
- [ ] API key validation works (rejects invalid keys)
- [ ] `get_available_variables` returns complete list
- [ ] `generate_crosstab` queries protected views successfully
- [ ] Cell suppression applied correctly (n<10 cells suppressed)
- [ ] Results include suppression metadata
- [ ] JOIN between demographics and survey data works
- [ ] Claude Desktop can call all tools
- [ ] Error messages are helpful

## Example Usage (Claude Desktop)

**User:** "What variables are available in the CHIP50 data?"

**Claude calls:** `get_available_variables()`

**Response:** List of demographic and survey variables with descriptions

---

**User:** "Show me trust in Congress by party affiliation"

**Claude calls:** `generate_crosstab(survey_variable="trust_congress", demographic_variable="party_7")`

**Response:**
```
Party 1: avg=2.47, n=403
Party 2: avg=2.46, n=228
Party 3: avg=2.32, n=190
...
Note: 0 cells suppressed (all n≥10)
```

---

**User:** "Break down vote intention by region"

**Claude calls:** `generate_crosstab(survey_variable="vote_intention", demographic_variable="region")`

**Response:**
```
Northeast:
  - Definitely will vote: 35%, n=11 [suppressed]
  - Probably will vote: 30%, n=9 [suppressed]
  ...

Note: 2 cells suppressed due to small sample size (n<10)
```

## Success Criteria

1. ✅ Stakeholders can use Claude Desktop to explore CHIP50 data
2. ✅ Privacy protections enforced (no PII, cell suppression)
3. ✅ Results are accurate and interpretable
4. ✅ Tool is discoverable (Claude understands what data is available)
5. ✅ Error messages guide users to correct usage

## After Phase 3

Once stakeholders validate the basic functionality:
- **Phase 4:** Add production authentication (Firestore, registration)
- **Phase 5:** Consider remote server architecture (if needed for scaling)
- **Phase 6:** Add distribution/installation scripts
- **Phase 7:** Complete user documentation

## Time Estimate

Phase 3 implementation: **4-6 hours**
- Update MCP server: 2 hours
- Add cell suppression: 1 hour
- Testing with Claude Desktop: 1-2 hours
- Documentation: 1 hour
