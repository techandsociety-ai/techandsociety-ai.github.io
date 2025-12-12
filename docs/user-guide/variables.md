---
title: Available Variables
---

# Available Variables Reference

Complete reference of all demographic and survey variables in CHIP50.

## Demographic Variables

### region
- **Type:** Categorical
- **Categories:** 5
  - Northeast
  - Mid-Atlantic  
  - Midwest
  - South
  - West
- **Note:** States are aggregated to regions for privacy

### age_cat_8
- **Type:** Categorical
- **Categories:** 8 age groups
- **Range:** 18-85+

### education_cat
- **Type:** Ordinal
- **Categories:** 5 levels
  1. Less than high school
  2. High school graduate
  3. Some college
  4. Bachelor's degree
  5. Graduate degree

### income_cat_10
- **Type:** Ordinal
- **Categories:** 10 income brackets
- **Range:** <$20k to >$200k

### gender
- **Type:** Categorical
- **Categories:** Male, Female, Other/Prefer not to say

### party_7
- **Type:** Ordinal (7-point scale)
- **Scale:**
  - 1 = Strong Democrat
  - 2 = Democrat
  - 3 = Lean Democrat
  - 4 = Independent
  - 5 = Lean Republican
  - 6 = Republican
  - 7 = Strong Republican

### race
- **Type:** Categorical
- **Categories:**
  - White
  - Black/African American
  - Hispanic/Latino
  - Asian
  - Native American
  - Other/Multiple

### urban_type
- **Type:** Categorical
- **Categories:**
  - Urban
  - Suburban
  - Rural

## Survey Variables

### Trust in Institutions (1-5 scale)

All trust variables use the same 1-5 scale:
- 1 = Not at all
- 2 = A little
- 3 = Somewhat
- 4 = Quite a bit
- 5 = A great deal

**Variables:**
- `trust_congress` - Trust in Congress
- `trust_courts` - Trust in courts
- `trust_media` - Trust in media
- `trust_military` - Trust in military

### Political Approval (1-7 scale)

All approval variables use a 1-7 scale:
- 1 = Strongly disapprove
- 2 = Disapprove
- 3 = Somewhat disapprove
- 4 = Neither approve nor disapprove
- 5 = Somewhat approve
- 6 = Approve
- 7 = Strongly approve

**Variables:**
- `approval_pres` - Presidential approval
- `approval_governor` - Governor approval
- `approval_senator` - Senator approval

### Issue Importance (0-10 scale)

- **Scale:** 0 (Not important at all) to 10 (Extremely important)

**Variables:**
- `issue_economy` - Economy importance
- `issue_healthcare` - Healthcare importance

### Other Variables

**vote_intention**
- **Type:** Categorical
- **Categories:** Democrat, Republican, Other, Undecided, Won't vote

**registered_voter**
- **Type:** Binary
- **Values:** 0 = Not registered, 1 = Registered

**party_thermometer**
- **Type:** Continuous (0-100)
- **Scale:** Feeling thermometer (0 = Very cold, 100 = Very warm)

## Wave Information

- **Available waves:** 7, 8, 9
- **Total observations:** 1,500 (500 respondents × 3 waves)
- **Unique respondents:** 500

## Usage Examples

See the [Quick Start Guide](../getting-started/quickstart.md) for usage examples.
