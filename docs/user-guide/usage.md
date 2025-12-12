---
title: Usage Guide
---

# Using the CHIP50 MCP Server

Complete guide to using CHIP50 MCP with Claude Desktop.

## Available Tools

The CHIP50 MCP server provides two main tools:

### 1. get_available_variables

Discover what demographic and survey variables are available.

**Usage:**
```
Ask Claude: "What variables are available in CHIP50?"
```

**Returns:**
- List of demographic variables with descriptions
- List of survey variables with scales
- Wave information
- Privacy protection summary

### 2. generate_crosstab

Generate privacy-protected cross-tabulations.

**Parameters:**
- `survey_variable` (required): Survey question to analyze
- `demographic_variable` (required): Demographic to group by
- `waves` (optional): Filter to specific survey waves
- `use_weights` (optional): Use survey weights (default: true)

**Usage:**
```
Ask Claude: "Show me trust in Congress by party affiliation"
```

## Natural Language Queries

You don't need to remember exact variable names. Claude will match your natural language to the correct variables:

| You Say | Claude Uses |
|---------|-------------|
| "party affiliation" | `party_7` |
| "trust in Congress" | `trust_congress` |
| "age groups" | `age_cat_8` |
| "education level" | `education_cat` |

## Privacy Protections

All results include automatic privacy protections:

- **Cell Suppression:** Cells with n<10 are suppressed
- **No PII:** No access to user IDs or identifying information
- **Geographic Aggregation:** States grouped into 5 regions
- **Metadata:** Every result includes privacy information

See [Privacy Protections](privacy.md) for details.

## Next Steps

- [Available Variables](variables.md) - Full variable reference
- [Cross-Tabulation Guide](crosstabs.md) - Detailed crosstab usage
- [Privacy Protections](privacy.md) - Understanding privacy features
