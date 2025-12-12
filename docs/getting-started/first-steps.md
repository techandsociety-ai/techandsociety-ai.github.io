---
title: First Steps
---

# First Steps with CHIP50 MCP

After installing the CHIP50 MCP server, follow this guide to start exploring the data.

## Verify Connection

First, verify that Claude Desktop can see the CHIP50 MCP server.

**Ask Claude:**
```
What tools do you have available from CHIP50?
```

Claude should list:
- `get_available_variables` - Discover what data is available
- `generate_crosstab` - Generate cross-tabulations

## Step 1: Discover Available Variables

Before analyzing data, see what's available.

**Ask Claude:**
```
What variables are available in CHIP50?
```

Claude will call `get_available_variables()` and show:

### Demographic Variables
- `region` - Geographic region (5 categories)
- `age_cat_8` - Age groups (8 categories)
- `education_cat` - Education level (5 levels)
- `income_cat_10` - Income bracket (10 levels)
- `gender` - Gender identity
- `party_7` - Party ID (7-point scale: 1=Strong Dem, 7=Strong Rep)
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
- `party_thermometer` - Party thermometer (0-100)

## Step 2: Generate Your First Crosstab

Try a simple cross-tabulation.

**Ask Claude:**
```
Show me trust in Congress by party affiliation
```

Claude will generate a weighted cross-tabulation showing:
- Counts and percentages for each combination
- Total sample size
- Any suppressed cells (n<10)
- Privacy metadata

### Example Output

```
Trust in Congress by Party ID (7-point scale)

Party 1 (Strong Dem):
  Trust=1 (Not at all): 26.1% (n=105)
  Trust=2: 24.3% (n=98)
  Trust=3 (Somewhat): 28.5% (n=115)
  Trust=4: 15.2% (n=61)
  Trust=5 (A great deal): 5.9% (n=24)

Party 7 (Strong Rep):
  Trust=1 (Not at all): 45.2% (n=87)
  Trust=2: 30.1% (n=58)
  Trust=3 (Somewhat): 18.7% (n=36)
  Trust=4: 4.8% (n=9) [suppressed - n<10]
  Trust=5 (A great deal): [suppressed - n<10]

Total: 1,500 observations
Cells suppressed: 2 (privacy protection: n<10)
```

## Step 3: Filter by Wave

Survey data includes multiple waves. You can filter to specific waves.

**Ask Claude:**
```
Show vote intention by region for wave 9 only
```

Claude will filter the data to only wave 9 observations.

## Step 4: Try Different Combinations

Explore different demographic breakdowns:

### Political Analysis
```
Compare presidential approval between Democrats and Republicans
```

### Regional Differences
```
How does trust in media vary across regions?
```

### Demographic Patterns
```
Show me vote intention by education level
```

### Issue Salience
```
What's the average importance of healthcare by party affiliation?
```

## Understanding Privacy Protections

As you explore, you'll see privacy protections in action:

### Cell Suppression (n≥10)

When a crosstab cell has fewer than 10 respondents, it's automatically suppressed:

```
Trust=4: [suppressed - n<10]
```

This prevents identification of small groups.

### No State-Level Data

States are aggregated into 5 regions:
- Northeast
- Mid-Atlantic
- Midwest
- South
- West

You cannot access individual state codes.

### No User IDs

The protected views don't include user IDs. Demographics and responses are joined using non-reversible hashes.

### Metadata Included

Every result includes privacy metadata:
```json
{
  "metadata": {
    "total_n": 1500,
    "cells_suppressed": 2,
    "privacy_note": "Cells with n<10 suppressed for privacy protection"
  }
}
```

## Common Patterns

### Ask for Interpretations

Don't just generate crosstabs—ask Claude to interpret them:

```
Show trust in Congress by party and explain any patterns you see
```

### Compare Multiple Variables

```
Compare trust in Congress vs trust in courts across party affiliation
```

### Ask "Why" Questions

```
Why might trust in media differ between rural and urban respondents?
```

Claude can use the crosstab data to provide contextual analysis.

## Tips for Effective Analysis

1. **Start broad, then narrow**
   - First: "What variables exist?"
   - Then: "Show me X by Y"
   - Finally: "Show me X by Y for wave 9 only"

2. **Ask for interpretations**
   - Claude can analyze patterns in the crosstabs
   - Request context and explanations

3. **Watch for suppression**
   - Suppressed cells indicate small sample sizes
   - Consider broader categories if too many cells are suppressed

4. **Use natural language**
   - You don't need to know exact variable names
   - Claude will find the closest match
   - Example: "party affiliation" → `party_7`

5. **Combine with other knowledge**
   - Ask Claude to compare results to published research
   - Request historical context
   - Get methodological advice

## Example Analysis Session

Here's a complete analysis session:

**You:** "What demographic and survey variables are available?"

**Claude:** [Lists all variables with descriptions]

**You:** "Show me trust in Congress by party affiliation"

**Claude:** [Generates crosstab showing strong partisanship in trust]

**You:** "That's interesting. How does this compare to trust in the military?"

**Claude:** [Generates second crosstab showing less partisan divide]

**You:** "Why might trust in the military be less partisan than trust in Congress?"

**Claude:** [Provides analysis using the crosstab data and general knowledge about institutional trust]

## Next Steps

Now that you're familiar with the basics:

- **Explore more:** Try different variable combinations
- **Learn advanced features:** See the [User Guide](../user-guide/usage.md)
- **Understand the data:** Read about [Available Variables](../user-guide/variables.md)
- **Deep dive on privacy:** Check out [Privacy Protections](../user-guide/privacy.md)

## Getting Help

If you encounter issues:
- Check the [Troubleshooting Guide](../install/troubleshooting.md)
- Review the [User Guide](../user-guide/usage.md)
- Ask Claude: "What can I do with CHIP50 data?"
