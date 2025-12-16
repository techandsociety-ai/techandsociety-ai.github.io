# CHIP50 Real Data Processing Guide

This guide explains how to process and upload real CHIP50 survey data to BigQuery with privacy protections.

## Overview

The data processing pipeline:

1. **Load raw CSV files** from `data/` directory
2. **Split into demographics and survey responses**
3. **Remove identifying information** (PII, free-text, metadata)
4. **Upload to BigQuery** raw tables
5. **Create protected views** with additional privacy protections
6. **Test and verify** the data is ready for use

## Privacy Protections

### Automatic Removal

The processing scripts automatically remove:

- **Direct identifiers**: ZIP codes, county names, FIPS codes, IP addresses
- **Free-text responses**: Any column ending in `_TEXT`
- **Qualtrics metadata**: Display order (`_DO_`), flow (`FL_`), quality (`Q_`), timing (`timer_`)
- **Timestamps**: Exact start/end times, recorded dates
- **Supplier identifiers**: Transaction IDs, supplier response IDs

### Protected Views

BigQuery views provide additional protections:

- **Geographic aggregation**: `state_code` → `region` (e.g., "CA" → "West")
- **Row hashing**: `id` removed, replaced with non-reversible `row_hash`
- **Cell suppression**: MCP server automatically suppresses cells with n<10

## Step-by-Step Instructions

### 1. Prepare Data Files

Place your raw CHIP50 CSV files in the `data/` directory:

```bash
data/
├── CSP_W35.csv
├── CSP_W35.1.csv
└── ... (additional wave files)
```

**File naming convention**: `CSP_W{wave_number}.csv`

### 2. Process the Data

Run the processing script:

```bash
python process_real_data.py
```

This will:
- Load all `CSP_W*.csv` files from `data/`
- Split into demographics and survey responses
- Remove identifying information
- Save processed files to `data/processed/`

**Output files**:
```
data/processed/
├── chip50_demographics_20241214_123456.csv
└── chip50_survey_responses_20241214_123456.csv
```

**What gets removed**:
```python
IDENTIFYING_VARS = [
    'zip',              # Exact ZIP code
    'county',           # County name
    'fips',             # County FIPS
    'ip_state',         # IP-based location
    'ip_zip',
    'StartDate',        # Exact timestamps
    'EndDate',
    'RecordedDate',
    # ... and many more (see process_real_data.py)
]

# Also removes:
# - Columns containing '_TEXT' (free-text)
# - Columns containing '_DO_' (display order)
# - Columns starting with 'FL_' (flow)
# - Columns starting with 'Q_' (quality metrics)
# - Columns starting with 'timer_' (timing data)
```

**What gets kept**:

Demographics:
- Age categories (4, 6, and 8 categories)
- Gender and race/ethnicity variables
- Education and income categories
- Party identification
- Urbanicity (urban/suburban/rural)
- State code (for region aggregation)
- Survey weights

Survey responses:
- All substantive survey questions
- Trust in institutions
- Political attitudes and behaviors
- Health and well-being measures
- Social media usage patterns
- ... (300+ variables)

### 3. Review Processed Data

Check the processed files before uploading:

```bash
# Check row counts
wc -l data/processed/chip50_*.csv

# View demographic columns
head -1 data/processed/chip50_demographics_*.csv | tr ',' '\n' | head -20

# View survey response columns
head -1 data/processed/chip50_survey_responses_*.csv | tr ',' '\n' | head -30
```

The script prints a column summary showing:
- Which demographic variables were kept
- Which survey variables were kept
- Total row counts

### 4. Upload to BigQuery

Upload the processed data to BigQuery:

```bash
# Basic upload (auto-detects latest processed files)
python upload_real_data_to_bigquery.py --verify

# Specify project and dataset
python upload_real_data_to_bigquery.py \
  --project chip50 \
  --dataset raw \
  --verify

# Specify exact files
python upload_real_data_to_bigquery.py \
  --demographics data/processed/chip50_demographics_20241214_123456.csv \
  --survey-responses data/processed/chip50_survey_responses_20241214_123456.csv \
  --verify
```

**What happens**:
1. BigQuery schema is auto-detected from CSV headers
2. Data is uploaded to `chip50.raw.demographics` and `chip50.raw.survey_responses`
3. If `--verify` flag is used, runs verification queries:
   - Total row counts
   - Unique respondent IDs
   - Rows per wave

**Expected output**:
```
Uploading chip50_demographics_20241214_123456.csv to chip50.raw.demographics...
  File size: 12.34 MB
  Uploading... (this may take a few minutes)
✓ Successfully loaded 31,892 rows into chip50.raw.demographics
  Schema: 38 columns

Uploading chip50_survey_responses_20241214_123456.csv to chip50.raw.survey_responses...
  File size: 45.67 MB
  Uploading... (this may take a few minutes)
✓ Successfully loaded 31,892 rows into chip50.raw.survey_responses
  Schema: 312 columns

Verifying chip50.raw.demographics...
  Total rows: 31,892
  Unique IDs: 30,234
  Rows by wave:
    Wave 35: 15,946 rows
    Wave 35.1: 15,946 rows
```

### 5. Create Protected Views

Create the privacy-protected BigQuery views:

```bash
./test_views.sh
```

This script:
1. Executes `sql/create_demographics_protected.sql`
2. Executes `sql/create_survey_responses_protected.sql`
3. Creates views in `chip50.public` dataset

**Protected views**:

**`chip50.public.demographics_protected`**:
- Removes `id` column, replaces with `row_hash`
- Aggregates `state_code` → `region`
- Keeps safe demographic categories
- Includes survey weights

**`chip50.public.survey_responses_protected`**:
- Removes `id` column, replaces with `row_hash`
- Includes all substantive survey questions
- Excludes free-text, metadata columns

**Testing the views**:
```sql
-- Test demographics view
SELECT
  region,
  COUNT(*) as respondents
FROM `chip50.public.demographics_protected`
GROUP BY region
ORDER BY respondents DESC;

-- Test survey responses view
SELECT
  wave,
  COUNT(*) as responses,
  AVG(CAST(pol_trust_congress AS FLOAT64)) as avg_trust_congress
FROM `chip50.public.survey_responses_protected`
GROUP BY wave
ORDER BY wave;

-- Test JOIN between views
SELECT
  d.region,
  d.party7,
  AVG(CAST(s.pol_trust_congress AS FLOAT64)) as avg_trust
FROM `chip50.public.demographics_protected` d
JOIN `chip50.public.survey_responses_protected` s
  ON d.row_hash = s.row_hash
WHERE d.party7 IS NOT NULL
  AND s.pol_trust_congress IS NOT NULL
GROUP BY d.region, d.party7
ORDER BY d.region, d.party7;
```

### 6. Test the MCP Server

Test crosstab generation with real data:

```bash
python test_bigquery_crosstab.py
```

This runs test queries using the protected views and validates:
- Data can be retrieved
- JOINs work correctly
- Cell suppression applies (n≥10)
- Weighted analysis produces correct results

## Data Schema

### Demographics Table (`chip50.raw.demographics`)

**Key columns**:
- `id` (STRING): Unique respondent ID (UUID)
- `wave` (STRING): Survey wave number
- `age_cat_8` (STRING): Age category (8 levels)
- `education_cat` (STRING): Education level
- `income_cat_10` (STRING): Income category (10 levels)
- `gender` (STRING): Gender identity
- `party7` (STRING): Party identification (7-point scale)
- `race_*` (STRING): Race/ethnicity indicators
- `state_code` (STRING): Two-letter state code
- `region` (STRING): Census region
- `urban_type` (STRING): Urban/Suburban/Rural
- `weight` (FLOAT64): Survey weight

### Survey Responses Table (`chip50.raw.survey_responses`)

**Key variable groups**:

1. **Trust in institutions** (23 variables)
   - `pol_trust_congress`, `pol_trust_court`, `pol_trust_media`, etc.

2. **Political attitudes** (50+ variables)
   - `ideology`, `vote24_post`, `support24`, etc.

3. **Political news** (17 variables)
   - `pol_news1_1` through `pol_news2_8`

4. **Thermometers** (30+ variables)
   - Political figures: `therm1_1` through `therm1_21`
   - Countries: `therm_country_*`
   - Companies: `therm_company_*`

5. **Health and well-being** (40+ variables)
   - COVID: `covid`, `vaccine_get`, `cov_test`
   - Mental health: `phq9_*`, `stress_1`, `lonely*`
   - Healthcare: `medicaid`, `medicare`, `ozempic`

6. **Social media** (100+ variables)
   - Usage: `use_facebook`, `use_twitter`, etc.
   - Frequency: `freq_*`
   - Trust: `sm_trust_*`
   - Political posting: `sm_post_pol_*`

7. **AI usage** (66+ variables)
   - Knowledge: `ai_know_*`
   - Frequency: `ai_freq_*`
   - Reasons: `ai_why_*`
   - How used: `ai_how_*`

## Troubleshooting

### Issue: "No files matching pattern found"

**Cause**: CSV files not in `data/` directory or wrong naming.

**Solution**:
```bash
# Check files exist
ls -la data/CSP_W*.csv

# Ensure files match pattern: CSP_W{number}.csv
```

### Issue: "Column not found" in protected views

**Cause**: SQL view references a column that doesn't exist in processed data.

**Solution**:
1. Check which columns are in the uploaded table:
   ```sql
   SELECT column_name
   FROM `chip50.raw.INFORMATION_SCHEMA.COLUMNS`
   WHERE table_name = 'demographics'
   ORDER BY column_name;
   ```

2. Update SQL view to use available columns:
   ```bash
   # Edit the view SQL
   vim sql/create_demographics_protected.sql

   # Recreate the view
   ./test_views.sh
   ```

### Issue: Upload fails with "Quota exceeded"

**Cause**: BigQuery has daily quotas for data loading.

**Solution**:
- Wait 24 hours for quota reset
- Or use `--write-disposition WRITE_APPEND` to add incrementally
- Or request quota increase in GCP console

### Issue: Different wave files have different columns

**Cause**: Survey instruments evolve across waves.

**Solution**: The scripts handle this automatically:
- `pd.concat(..., sort=False)` preserves all columns
- Missing columns filled with NULL/None
- BigQuery auto-detect handles varying schemas

## Best Practices

### 1. Version Control for Processed Data

Keep track of when data was processed:

```bash
# Output files include timestamp
chip50_demographics_20241214_123456.csv

# Git tag after successful upload
git tag -a data-upload-20241214 -m "Uploaded waves 35, 35.1"
git push --tags
```

### 2. Backup Raw Data

Before processing, backup the original CSV files:

```bash
# Create backup
tar -czf data_backup_$(date +%Y%m%d).tar.gz data/*.csv

# Store in safe location
mv data_backup_*.tar.gz ~/backups/
```

### 3. Verify Data Quality

After upload, run quality checks:

```sql
-- Check for duplicates
SELECT id, wave, COUNT(*) as n
FROM `chip50.raw.demographics`
GROUP BY id, wave
HAVING n > 1;

-- Check wave distribution
SELECT wave, COUNT(*) as n
FROM `chip50.raw.demographics`
GROUP BY wave
ORDER BY wave;

-- Check missing values in key variables
SELECT
  COUNTIF(age_cat_8 IS NULL) as missing_age,
  COUNTIF(gender IS NULL) as missing_gender,
  COUNTIF(party7 IS NULL) as missing_party,
  COUNT(*) as total
FROM `chip50.raw.demographics`;
```

### 4. Document Variable Definitions

Create a data dictionary for reference:

```bash
# Generate column list
head -1 data/processed/chip50_survey_responses_*.csv | tr ',' '\n' > variables.txt

# Add descriptions (manual process)
# Share with team
```

## Next Steps

After successful data processing and upload:

1. **Update MCP server configuration** to use `chip50.public.*` views
2. **Test crosstab generation** with various variable combinations
3. **Document available variables** for end users
4. **Set up automated data pipeline** for future waves
5. **Monitor query performance** and optimize as needed

## Additional Resources

- [BigQuery Best Practices](https://cloud.google.com/bigquery/docs/best-practices)
- [CHIP50 MCP Server Documentation](README.md)
- [Protected Views SQL](sql/)
- [Privacy Protection Details](buildplan.md#phase-2-database-security--privacy-layer)
