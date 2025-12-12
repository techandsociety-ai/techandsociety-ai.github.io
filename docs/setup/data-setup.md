---
title: Data Setup Guide
---

# CHIP50 Data Setup Guide

This guide walks through setting up the CHIP50 survey data pipeline with privacy-preserving BigQuery views.

## Architecture Overview

```
Synthetic Data Generation
         ↓
BigQuery Raw Tables (chip50.raw.*)
         ↓
Protected Public Views (chip50.public.*)
         ↓
MCP Server Access (with cell suppression)
```

## Prerequisites

1. **UV Package Manager**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Google Cloud SDK**
   ```bash
   # macOS
   brew install google-cloud-sdk

   # Or download from: https://cloud.google.com/sdk/docs/install
   ```

3. **Google Cloud Project**
   - Project ID: `chip50`
   - BigQuery API enabled
   - Appropriate permissions (BigQuery Admin or Editor)

## Quick Start

### One-Command Setup

Run the complete data pipeline:

```bash
./data_setup.sh
```

This script will:
1. ✓ Check for UV installation
2. ✓ Authenticate with Google Cloud
3. ✓ Create BigQuery datasets (raw and public)
4. ✓ Generate synthetic survey data (if not exists)
5. ✓ Upload data to `chip50.raw.*` tables
6. ✓ Create protected views in `chip50.public.*`

### Manual Step-by-Step Setup

If you prefer to run steps individually:

#### 1. Authenticate with Google Cloud

```bash
# Login to your Google account
gcloud auth login

# Set application default credentials
gcloud auth application-default login

# Set the project
gcloud config set project chip50
```

#### 2. Install Dependencies with UV

```bash
# UV will automatically create a virtual environment and install dependencies
uv sync
```

#### 3. Generate Synthetic Data

```bash
uv run python synthetic_data/generate_synthetic_data.py
```

This creates:
- `synthetic_data/synthetic_demographics.csv` (500 respondents × 3 waves = 1,500 rows)
- `synthetic_data/synthetic_survey_responses.csv` (1,500 rows)

#### 4. Create BigQuery Datasets

```bash
# Create raw dataset (restricted access)
bq mk --dataset --location=US \
  --description="Raw survey data (restricted access)" \
  chip50:raw

# Create public dataset (for protected views)
bq mk --dataset --location=US \
  --description="Public-facing protected views (privacy-preserving)" \
  chip50:public
```

#### 5. Upload Data to BigQuery

```bash
uv run python upload_to_bigquery.py
```

This uploads to:
- `chip50.raw.demographics`
- `chip50.raw.survey_responses`

#### 6. Create Protected Views

```bash
# Create demographics protected view
bq query --use_legacy_sql=false < sql/create_demographics_protected.sql

# Create survey responses protected view
bq query --use_legacy_sql=false < sql/create_survey_responses_protected.sql
```

## Data Structure

### Raw Tables (chip50.raw.*)

**Restricted access - Core researchers only**

#### `demographics`
- `id` (STRING): Unique respondent identifier (UUID)
- `wave` (INTEGER): Survey wave number
- `age_cat_8` (STRING): 8-category age groups
- `education_cat` (STRING): Education level
- `income_cat_10` (INTEGER): Income decile (1-10)
- `gender` (STRING): Gender identity
- `party_7` (INTEGER): 7-point party identification scale
- `race` (STRING): Race/ethnicity
- `urban_type` (STRING): Urban/Suburban/Rural
- `state_code` (STRING): Two-letter state code
- `weight` (FLOAT): Survey weight

#### `survey_responses`
- `id` (STRING): Respondent identifier (links to demographics)
- `wave` (INTEGER): Survey wave number
- Trust variables (1-5 scale): `trust_congress`, `trust_courts`, `trust_media`, `trust_military`
- Approval variables (1-7 scale): `approval_pres`, `approval_governor`, `approval_senator`
- Issue importance (0-10 scale): `issue_economy`, `issue_healthcare`
- `vote_intention` (STRING): Categorical voting intention
- `registered_voter` (INTEGER): Binary voter registration status
- `party_thermometer` (FLOAT): Party feeling thermometer (0-100)

### Protected Views (chip50.public.*)

**Public access - All researchers**

#### `demographics_protected`

Privacy protections:
- ✅ `id` removed → replaced with `row_hash` (FARM_FINGERPRINT, non-reversible)
- ✅ `state_code` removed → aggregated to `region` (Northeast, South, etc.)
- ✅ All other demographic variables preserved

#### `survey_responses_protected`

Privacy protections:
- ✅ `id` removed → replaced with `row_hash` (matches demographics_protected)
- ✅ All substantive survey variables preserved
- ✅ Free-text fields excluded (none in synthetic data)

**JOIN capability:**
```sql
SELECT d.*, s.*
FROM `chip50.public.demographics_protected` d
JOIN `chip50.public.survey_responses_protected` s
  ON d.row_hash = s.row_hash AND d.wave = s.wave
```

## Testing

### Run Test Queries

```bash
# Test all protected views
bq query --use_legacy_sql=false < sql/test_protected_views.sql
```

### Verify Privacy Protections

1. **No PII exposure**: `id` column should not exist in protected views
2. **Geographic aggregation**: Only `region` should be available, not `state_code`
3. **JOIN functionality**: `row_hash` should successfully link demographics and survey data
4. **Data quality**: Row counts should match raw tables

### Expected Results

- **Total rows**: 1,500 (500 respondents × 3 waves)
- **Unique respondents**: 500
- **Waves**: 7, 8, 9
- **Regions**: 5 (Northeast, Mid-Atlantic, Midwest, South, West)

## Privacy Features

### Current Implementation (Phase 2)

- ✅ User ID removal (PII protection)
- ✅ Geographic aggregation (state → region)
- ✅ Deterministic JOIN keys (non-reversible hashing)
- ✅ Free-text exclusion

### Future Implementation (Phase 3-4)

- ⏳ Cell size suppression (n ≥ 10)
- ⏳ Tiered access control (API keys)
- ⏳ Rate limiting (100 queries/day)
- ⏳ Audit logging

## Troubleshooting

### Authentication Issues

```bash
# Re-authenticate
gcloud auth login
gcloud auth application-default login

# Verify credentials
gcloud auth list
```

### BigQuery Permissions

Ensure your account has:
- `roles/bigquery.admin` or
- `roles/bigquery.dataEditor` + `roles/bigquery.jobUser`

```bash
# Check permissions
gcloud projects get-iam-policy chip50 --flatten="bindings[].members" \
  --filter="bindings.members:user:YOUR_EMAIL"
```

### Dataset Not Found

If datasets don't exist, create them manually:

```bash
bq mk --dataset chip50:raw
bq mk --dataset chip50:public
```

### View Creation Errors

If views fail to create, check:
1. Raw tables exist: `bq ls chip50:raw`
2. SQL syntax: Review error message for specific issues
3. Permissions: Ensure you can create views in the public dataset

## Next Steps

After completing this setup:

1. **Test queries** against protected views
2. **Set up IAM roles** for tiered access (core vs. outside researchers)
3. **Implement MCP server** with cell suppression logic
4. **Deploy remote server** with authentication

See [buildplan.md](buildplan.md) for complete implementation roadmap.

## Resources

- [BigQuery Documentation](https://cloud.google.com/bigquery/docs)
- [UV Package Manager](https://github.com/astral-sh/uv)
- [CHIP50 Build Plan](buildplan.md)
