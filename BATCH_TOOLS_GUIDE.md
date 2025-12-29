# Batch Tools Guide

## Overview

The CHIP50 MCP server now includes two batch tools that allow you to analyze multiple variables or demographic groups in a single tool call, dramatically reducing overhead from multiple LLM inference passes.

## New Batch Tools

### 1. `generate_marginals_batch`

Generate marginal distributions for multiple variables at once.

**Use when:**
- Analyzing multiple survey questions (e.g., all AI-related variables)
- Comparing baseline distributions across several variables
- You need marginals for 3+ variables

**Parameters:**
- `variables` (array of strings): List of variables to analyze
- `wave` (string): Wave identifier (e.g., '35', '35_1')
- `use_weights` (boolean, optional): Use survey weights (default: true)

**Example:**
```json
{
  "variables": [
    "ai_freq_chatgpt",
    "ai_freq_claude",
    "ai_freq_gemini",
    "ai_freq_copilot",
    "ai_freq_perplexity",
    "ai_trust_info",
    "ai_concern_jobs",
    "ai_concern_privacy",
    "ai_regulate",
    "ai_future_optimism"
  ],
  "wave": "35",
  "use_weights": true
}
```

**Returns:**
```json
{
  "status": "success",
  "results": {
    "ai_freq_chatgpt": {
      "status": "success",
      "distribution": {
        "Daily": {"count": 450.2, "percentage": 15.5, ...},
        "Weekly": {"count": 820.1, "percentage": 28.2, ...},
        ...
      },
      "metadata": {...}
    },
    "ai_freq_claude": {...},
    ...
  },
  "metadata": {
    "total_variables": 10,
    "successful": 10,
    "failed": 0,
    "wave": "35",
    "weighted": true
  },
  "message": "Generated marginals for 10/10 variables in wave 35."
}
```

### 2. `generate_crosstab_batch`

Generate cross-tabulations for one survey variable across multiple demographic breakdowns.

**Use when:**
- Comparing how a survey question varies across different demographic groups
- Analyzing one question by party, education, age, race, and region
- You need crosstabs for 3+ demographic variables

**Parameters:**
- `survey_variable` (string): The survey question to analyze
- `demographic_variables` (array of strings): List of demographic groupings
- `wave` (string): Wave identifier (e.g., '35', '35_1')
- `use_weights` (boolean, optional): Use survey weights (default: true)

**Example:**
```json
{
  "survey_variable": "pol_trust_congress",
  "demographic_variables": [
    "party7",
    "educ",
    "age_cat",
    "race",
    "region",
    "gender"
  ],
  "wave": "35",
  "use_weights": true
}
```

**Returns:**
```json
{
  "status": "success",
  "results": {
    "party7": {
      "status": "success",
      "crosstab": {
        "Strong Democrat": {
          "A great deal": {"count": 45.2, "percentage": 12.3, ...},
          "A fair amount": {"count": 120.5, "percentage": 32.8, ...},
          ...
        },
        "Democrat": {...},
        ...
      },
      "metadata": {...}
    },
    "educ": {...},
    "age_cat": {...},
    ...
  },
  "metadata": {
    "survey_variable": "pol_trust_congress",
    "total_demographics": 6,
    "successful": 6,
    "failed": 0,
    "wave": "35",
    "weighted": true
  },
  "message": "Generated crosstabs for pol_trust_congress across 6/6 demographic variables in wave 35."
}
```

## Performance Comparison

### Before (Single Tools)

**Analyzing 10 AI variables:**
- 10 separate `generate_marginals` calls
- Each call = 1 LLM inference pass
- Total time: **20-40 minutes** (2-4 min per inference × 10 calls)
- BigQuery queries run sequentially

**Analyzing 1 survey question across 6 demographics:**
- 6 separate `generate_crosstab` calls
- Each call = 1 LLM inference pass
- Total time: **12-24 minutes** (2-4 min per inference × 6 calls)
- BigQuery queries run sequentially

### After (Batch Tools)

**Analyzing 10 AI variables:**
- 1 `generate_marginals_batch` call
- Single LLM inference pass
- Total time: **~3-5 minutes** (1 inference + parallel queries)
- **~5-10x faster**
- All 10 BigQuery queries run in parallel

**Analyzing 1 survey question across 6 demographics:**
- 1 `generate_crosstab_batch` call
- Single LLM inference pass
- Total time: **~3-4 minutes** (1 inference + parallel queries)
- **~4-6x faster**
- All 6 BigQuery queries run in parallel

## Implementation Details

### Parallel Execution

Both batch tools use `asyncio.gather()` to execute all queries concurrently:

```python
# generate_marginals_batch
tasks = [
    self.generate_marginals(variable=var, wave=wave, use_weights=use_weights)
    for var in variables
]
results = await asyncio.gather(*tasks)

# generate_crosstab_batch
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
```

### Error Handling

- Each variable/demographic is processed independently
- If one fails, others continue processing
- Results include both successful and failed operations
- Metadata shows success/failure counts

### Return Format

Results are organized as a dictionary:
- **Keys**: Variable names or demographic variable names
- **Values**: Individual tool results (same format as single tools)
- **Metadata**: Summary statistics about the batch operation

## When to Use Which Tool

### Use Single Tools When:
- Analyzing 1-2 variables
- Exploratory analysis where you're deciding what to query next
- Quick one-off lookups
- Testing variable names

### Use Batch Tools When:
- Analyzing 3+ variables or demographics
- You know exactly what you want to analyze
- Comparing across multiple dimensions
- Time is a constraint
- You want to minimize LLM inference overhead

## Common Usage Patterns

### Pattern 1: Comprehensive AI Analysis
```json
{
  "tool": "generate_marginals_batch",
  "variables": [
    "ai_freq_chatgpt", "ai_freq_claude", "ai_freq_gemini",
    "ai_freq_copilot", "ai_freq_perplexity", "ai_trust_info",
    "ai_concern_jobs", "ai_concern_privacy", "ai_regulate",
    "ai_future_optimism"
  ],
  "wave": "35"
}
```

### Pattern 2: Key Demographics Breakdown
```json
{
  "tool": "generate_crosstab_batch",
  "survey_variable": "pol_approval_pres",
  "demographic_variables": ["party7", "educ", "age_cat", "race", "region"],
  "wave": "35"
}
```

### Pattern 3: Full Demographic Profile
```json
{
  "tool": "generate_crosstab_batch",
  "survey_variable": "ai_future_optimism",
  "demographic_variables": [
    "party7", "party3", "ideology5",
    "educ", "age_cat", "gender", "race", "region",
    "income", "religion"
  ],
  "wave": "35"
}
```

### Pattern 4: Political Attitudes Battery
```json
{
  "tool": "generate_marginals_batch",
  "variables": [
    "pol_trust_congress", "pol_trust_courts", "pol_trust_media",
    "pol_approval_pres", "pol_vote_intention", "pol_ideology_self"
  ],
  "wave": "35"
}
```

## Limitations

1. **All variables must be from the same wave**
   - Cannot mix variables from different waves in one batch
   - For cross-wave analysis, use multiple batch calls (one per wave)

2. **Crosstab batch only supports one survey variable**
   - If you need multiple survey variables × multiple demographics, use multiple calls
   - Or combine `generate_marginals_batch` for survey vars + `generate_crosstab_batch` for detailed breakdown

3. **Memory constraints**
   - Very large batches (50+ variables) may hit memory limits
   - Recommended batch size: 10-20 variables at a time

## Privacy Protections

Batch tools maintain all privacy protections:
- ✅ Cell suppression (n≥10) still enforced in crosstabs
- ✅ Geographic aggregation (region, not state)
- ✅ No PII access
- ✅ row_hash used instead of user IDs
- ✅ Protected views queried

## Upgrading from Single Tools

**Before:**
```
Call generate_marginals for ai_freq_chatgpt → Wait 3 min
Call generate_marginals for ai_freq_claude → Wait 3 min
Call generate_marginals for ai_freq_gemini → Wait 3 min
...
Total: 30 minutes for 10 variables
```

**After:**
```
Call generate_marginals_batch with all 10 variables → Wait 4 min
Total: 4 minutes for 10 variables
```

**Migration is simple:**
1. Identify places where you make multiple `generate_marginals` calls for the same wave
2. Collect all variable names into an array
3. Replace with single `generate_marginals_batch` call
4. Adjust code to parse the batch result format

## Example Workflow

### Discovering and Analyzing AI Attitudes

```
Step 1: Discover AI variables
→ Call get_available_variables(wave="35")
→ Filter for variables starting with "ai_"
→ Find 10 AI-related variables

Step 2: Get baseline distributions
→ Call generate_marginals_batch(
    variables=["ai_freq_chatgpt", "ai_freq_claude", ...],
    wave="35"
  )
→ Review overall distributions (3 min instead of 30 min)

Step 3: Analyze by demographics
→ Call generate_crosstab_batch(
    survey_variable="ai_future_optimism",
    demographic_variables=["party7", "educ", "age_cat", "race", "region"],
    wave="35"
  )
→ See how optimism varies across groups (3 min instead of 15 min)

Total time: ~6 minutes (vs 45+ minutes with single tools)
```

## Conclusion

Batch tools provide significant performance improvements when analyzing multiple variables or demographic groups. They reduce LLM inference overhead while executing BigQuery queries in parallel, making large-scale analysis practical and efficient.

**Key takeaway:** Use batch tools when you need 3+ variables or demographics analyzed in the same wave. You'll save 5-10x in time and reduce context window usage.
