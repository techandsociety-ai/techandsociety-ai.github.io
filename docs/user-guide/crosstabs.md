---
title: Cross-Tabulation Guide
---

# Cross-Tabulation Guide

Learn how to generate and interpret cross-tabulations with CHIP50 MCP.

## What is a Crosstab?

A cross-tabulation (crosstab) shows how responses to one variable vary across categories of another variable.

**Example:** Trust in Congress by Party Affiliation

| Party | Trust=1 | Trust=2 | Trust=3 | Trust=4 | Trust=5 |
|-------|---------|---------|---------|---------|---------|
| Strong Dem | 26.1% | 24.3% | 28.5% | 15.2% | 5.9% |
| Independent | 35.7% | 28.4% | 25.2% | 8.3% | 2.4% |
| Strong Rep | 45.2% | 30.1% | 18.7% | [sup] | [sup] |

## Generating Crosstabs

Ask Claude in natural language:

```
Show me trust in Congress by party affiliation
```

Claude will:
1. Match "trust in Congress" → `trust_congress`
2. Match "party affiliation" → `party_7`
3. Call `generate_crosstab(survey_variable="trust_congress", demographic_variable="party_7")`
4. Apply privacy protections
5. Return results with interpretation

## Reading Results

### Counts and Percentages

Results show both weighted counts and percentages:
- **Count:** Survey-weighted number of respondents
- **Percentage:** Proportion within each demographic group

### Privacy Metadata

Every result includes:
- `total_n`: Total observations
- `cells_suppressed`: Number of suppressed cells
- `privacy_note`: Privacy protection explanation

### Suppressed Cells

Cells with n<10 show `[suppressed]` for privacy protection.

## Advanced Features

### Filter by Wave

```
Show trust in Congress by party for wave 9 only
```

### Unweighted Results

```
Show me unweighted counts of vote intention by education
```

### Multiple Comparisons

Ask Claude to compare multiple crosstabs:
```
Compare trust in Congress vs trust in media by party affiliation
```

## Best Practices

1. **Start with available variables:** Ask "What variables exist?" first
2. **Use natural language:** Claude will match to correct variable names
3. **Watch for suppression:** Many suppressed cells may indicate small sample sizes
4. **Ask for interpretation:** Have Claude explain patterns in the data
5. **Consider weights:** Weighted results represent population estimates

## Common Patterns

See [First Steps](../getting-started/first-steps.md) for example analyses.
