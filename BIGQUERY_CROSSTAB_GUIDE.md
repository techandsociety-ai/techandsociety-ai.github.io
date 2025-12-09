# BigQuery Crosstab Guide

This guide explains how to use the BigQuery-based weighted crosstabulation functionality in the CHIP50 MCP server.

## Overview

The `generate_bigquery_crosstab` tool generates weighted cross-tabulations by:
1. Joining the `demographics` and `survey_responses` tables in BigQuery
2. Using survey weights to calculate weighted proportions
3. Computing both counts and percentages for survey responses across demographic categories

## Data Structure

### Demographics Table (`nanocentury.chip50.demographics`)
Contains demographic information:
- `id` - Respondent ID
- `wave` - Survey wave number
- `age_cat_8` - Age category
- `education_cat` - Education level
- `income_cat_10` - Income category
- `gender` - Gender
- `party_7` - Party affiliation (7-point scale)
- `race` - Race/ethnicity
- `urban_type` - Urban/Suburban/Rural
- `state_code` - State code
- `weight` - Survey weight

### Survey Responses Table (`nanocentury.chip50.survey_responses`)
Contains survey responses:
- `id` - Respondent ID (joins with demographics)
- `wave` - Survey wave number (joins with demographics)
- `trust_congress` - Trust in Congress (scale 1-5)
- `trust_courts` - Trust in courts
- `trust_media` - Trust in media
- `trust_military` - Trust in military
- `approval_pres` - Presidential approval
- `approval_governor` - Governor approval
- `approval_senator` - Senator approval
- `issue_economy` - Importance of economy (0-10)
- `issue_healthcare` - Importance of healthcare (0-10)
- `vote_intention` - Voting intention
- `registered_voter` - Registered voter status (0/1)
- `party_thermometer` - Party feeling thermometer (0-100)

## Using the Tool

### Basic Weighted Crosstab

```json
{
  "project_id": "nanocentury",
  "dataset_id": "chip50",
  "survey_variable": "trust_congress",
  "demographic_variable": "party_7",
  "use_weights": true
}
```

This generates a weighted crosstab of trust in Congress by party affiliation.

### Filter by Wave

```json
{
  "project_id": "nanocentury",
  "dataset_id": "chip50",
  "survey_variable": "approval_pres",
  "demographic_variable": "race",
  "waves": [7],
  "use_weights": true
}
```

Analyzes only wave 7 data.

### Multiple Waves

```json
{
  "project_id": "nanocentury",
  "dataset_id": "chip50",
  "survey_variable": "vote_intention",
  "demographic_variable": "education_cat",
  "waves": [1, 2, 3, 7],
  "use_weights": true
}
```

### Additional Filters

```json
{
  "project_id": "nanocentury",
  "dataset_id": "chip50",
  "survey_variable": "trust_media",
  "demographic_variable": "age_cat_8",
  "filter_conditions": "state_code = 'CA' AND gender = 'Female'",
  "use_weights": true
}
```

Filters to only California females.

### Unweighted Tabulation

```json
{
  "project_id": "nanocentury",
  "dataset_id": "chip50",
  "survey_variable": "registered_voter",
  "demographic_variable": "urban_type",
  "use_weights": false
}
```

## Output Format

The tool returns:

```json
{
  "status": "success",
  "crosstab": {
    "Democrat": {
      "1": {"count": 45.2, "percentage": 12.3, "display": "45.2 (12.3%)"},
      "2": {"count": 123.5, "percentage": 33.6, "display": "123.5 (33.6%)"},
      ...
    },
    "Republican": {
      ...
    }
  },
  "marginal_totals": {
    "Democrat": 367.8,
    "Republican": 289.4,
    ...
  },
  "survey_variable": "trust_congress",
  "demographic_variable": "party_7",
  "weighted": true,
  "total_n": 1000,
  "waves_included": [7],
  "query": "SELECT ...",
  "message": "Generated weighted crosstab for trust_congress by party_7"
}
```

## SQL Query Structure

The tool generates SQL like this:

```sql
WITH joined_data AS (
    SELECT
        d.party_7,
        s.trust_congress,
        d.weight
    FROM `nanocentury.chip50.demographics` d
    INNER JOIN `nanocentury.chip50.survey_responses` s
        ON d.id = s.id AND d.wave = s.wave
    WHERE d.party_7 IS NOT NULL
        AND s.trust_congress IS NOT NULL
        AND d.wave IN (7)
)
SELECT
    party_7,
    trust_congress,
    SUM(weight) as weighted_count,
    SUM(SUM(weight)) OVER (PARTITION BY party_7) as demographic_total
FROM joined_data
GROUP BY party_7, trust_congress
ORDER BY party_7, trust_congress
```

## Common Use Cases

### 1. Trust in Institutions by Party

```json
{
  "survey_variable": "trust_congress",
  "demographic_variable": "party_7"
}
```

### 2. Presidential Approval by Demographics

```json
{
  "survey_variable": "approval_pres",
  "demographic_variable": "race"
}
```

### 3. Vote Intention by Age

```json
{
  "survey_variable": "vote_intention",
  "demographic_variable": "age_cat_8"
}
```

### 4. Issue Importance by Education

```json
{
  "survey_variable": "issue_economy",
  "demographic_variable": "education_cat"
}
```

### 5. Registration Status by Urban/Rural

```json
{
  "survey_variable": "registered_voter",
  "demographic_variable": "urban_type"
}
```

## Interpreting Results

### Weighted Counts
- These represent the estimated population counts after applying survey weights
- Weights adjust for sampling biases and make the sample representative

### Percentages
- Row percentages (percentage of each demographic group giving each response)
- Sum to 100% within each demographic category

### Marginal Totals
- Total weighted count for each demographic category
- Used to calculate percentages

## Tips

1. **Always use weights** for population estimates unless you specifically need raw sample counts
2. **Filter by wave** when analyzing trends over time
3. **Use filter_conditions** for subgroup analysis (e.g., single state, specific demographics)
4. **Check total_n** to ensure sufficient sample size for reliable estimates
5. **Review the query** field to understand exactly what SQL was executed

## Example Workflow

1. **Upload data to BigQuery:**
   ```bash
   python upload_to_bigquery.py
   ```

2. **Test the crosstab:**
   ```bash
   python test_bigquery_crosstab.py
   ```

3. **Use the MCP tool** to generate crosstabs in your application

## Troubleshooting

- **No data returned**: Check that both tables exist and have matching id/wave values
- **Permission errors**: Ensure BigQuery permissions are set correctly
- **Invalid column names**: Verify variable names match the table schemas
- **Unexpected results**: Review the generated SQL query in the output
