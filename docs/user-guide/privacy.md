---
title: Privacy Protections
---

# Privacy Protections

CHIP50 MCP implements multiple layers of privacy protection.

## Cell Suppression (n≥10)

Any crosstab cell with fewer than 10 observations is automatically suppressed.

**Why:** Prevents identification of individuals in small groups (k-anonymity).

**How it works:**
- Before returning results, count observations in each cell
- If n<10, replace with `[suppressed]`
- Include suppression metadata in results

**Example:**
```
Party 7 (Strong Rep) × Trust=5: [suppressed - n<10]
```

## Geographic Aggregation

States are aggregated into 5 regions to prevent identification by location.

**Regions:**
- Northeast
- Mid-Atlantic
- Midwest
- South
- West

**Why:** State-level data could identify respondents in small states.

**Impact:** You cannot filter or group by individual states.

## No User IDs

Protected views do not include user IDs.

**Instead:**
- Demographics and responses joined via non-reversible `row_hash`
- Cannot trace back to individual respondents
- Cannot link across surveys (besides CHIP50 waves)

## No Free Text

Free-text responses are excluded from protected views.

**Why:** Free text can contain identifying information.

**Impact:** Only structured, categorical/numeric variables available.

## Protected BigQuery Views

All data access goes through BigQuery protected views:
- `chip50.public.demographics_protected`
- `chip50.public.survey_responses_protected`

**Benefits:**
- Privacy enforced at database level
- Cannot bypass protections
- Consistent rules for all users

## Privacy Metadata

Every result includes privacy information:

```json
{
  "metadata": {
    "total_n": 1500,
    "cells_suppressed": 2,
    "privacy_note": "Cells with n<10 suppressed for privacy protection",
    "suppression_threshold": 10
  }
}
```

## Limitations

Privacy protections impose some limitations:

- ❌ Cannot see cells with n<10
- ❌ Cannot access state-level data
- ❌ Cannot access user IDs
- ❌ Cannot see free-text responses
- ❌ Cannot filter to very small subgroups

These limitations are intentional and protect respondent privacy.

## Technical Details

See [Privacy Implementation](../technical/privacy-implementation.md) for technical details.
