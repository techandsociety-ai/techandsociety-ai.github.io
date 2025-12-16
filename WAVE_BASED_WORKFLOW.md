# Wave-Based Data Workflow

This guide explains the wave-specific data processing workflow where **each wave gets its own separate BigQuery tables and views**.

## Overview

Instead of combining all waves into single tables, this workflow creates:

```
Wave 35:
  ├── chip50.raw.demographics_w35
  ├── chip50.raw.survey_responses_w35
  ├── chip50.public.demographics_protected_w35
  └── chip50.public.survey_responses_protected_w35

Wave 35.1:
  ├── chip50.raw.demographics_w35_1
  ├── chip50.raw.survey_responses_w35_1
  ├── chip50.public.demographics_protected_w35_1
  └── chip50.public.survey_responses_protected_w35_1
```

## Why Separate Tables Per Wave?

**Advantages:**
- **Schema flexibility**: Each wave can have different columns without NULLs
- **Performance**: Queries on single waves are faster
- **Clear versioning**: Easy to see which wave data comes from
- **Incremental updates**: Add new waves without touching existing data
- **Testing**: Test new waves independently

## Quick Start

### 1. Process Data by Wave

```bash
python process_real_data_by_wave.py
```

**What it does:**
- Reads each `CSP_W*.csv` file separately
- Splits into demographics and survey responses
- Removes PII and metadata
- Outputs wave-specific files:
  - `chip50_demographics_w35_TIMESTAMP.csv`
  - `chip50_survey_responses_w35_TIMESTAMP.csv`
  - `chip50_demographics_w35_1_TIMESTAMP.csv`
  - `chip50_survey_responses_w35_1_TIMESTAMP.csv`

**Output location:** `data/processed/`

### 2. Upload to BigQuery

```bash
python upload_real_data_by_wave.py
```

**What it does:**
- Finds processed files for each wave
- Uploads to wave-specific tables:
  - `chip50.raw.demographics_w35`
  - `chip50.raw.survey_responses_w35`
  - `chip50.raw.demographics_w35_1`
  - `chip50.raw.survey_responses_w35_1`

**Options:**
```bash
# Upload specific waves only
python upload_real_data_by_wave.py --waves 35 35.1

# Different project
python upload_real_data_by_wave.py --project my-project --dataset raw
```

### 3. Create Protected Views

```bash
./create_all_wave_views.sh
```

**What it does:**
- Executes all `sql/create_*_protected_w*.sql` files
- Creates protected views in `chip50.public.*`
- Applies privacy protections:
  - Removes `id` column
  - Aggregates state → region
  - Creates non-reversible `row_hash`

**Views created:**
- `chip50.public.demographics_protected_w35`
- `chip50.public.survey_responses_protected_w35`
- `chip50.public.demographics_protected_w35_1`
- `chip50.public.survey_responses_protected_w35_1`

## File Structure

### SQL Scripts (per wave)

```
sql/
├── create_demographics_protected_w35.sql
├── create_survey_responses_protected_w35.sql
├── create_demographics_protected_w35_1.sql
└── create_survey_responses_protected_w35_1.sql
```

Each SQL file:
- References the correct raw table (`demographics_w35`)
- Creates the correct view (`demographics_protected_w35`)
- Includes wave label in metadata

### Processed Data Files

```
data/processed/
├── chip50_demographics_w35_20241214_123456.csv
├── chip50_survey_responses_w35_20241214_123456.csv
├── chip50_demographics_w35_1_20241214_123456.csv
└── chip50_survey_responses_w35_1_20241214_123456.csv
```

File naming: `chip50_{table_type}_w{wave}_{timestamp}.csv`

Wave numbers with decimals use underscores: `35.1` → `w35_1`

## Querying Wave-Specific Tables

### Query a Single Wave

```sql
-- Demographics for Wave 35
SELECT
  region,
  party7,
  COUNT(*) as n
FROM `chip50.public.demographics_protected_w35`
GROUP BY region, party7
ORDER BY region, party7;
```

### Compare Across Waves

```sql
-- Compare trust in Congress across waves
SELECT
  '35' as wave,
  AVG(CAST(pol_trust_congress AS FLOAT64)) as avg_trust
FROM `chip50.public.survey_responses_protected_w35`

UNION ALL

SELECT
  '35.1' as wave,
  AVG(CAST(pol_trust_congress AS FLOAT64)) as avg_trust
FROM `chip50.public.survey_responses_protected_w35_1`;
```

### Join Demographics and Survey Responses

```sql
-- Within a single wave (using row_hash)
SELECT
  d.region,
  d.party7,
  AVG(CAST(s.pol_trust_congress AS FLOAT64)) as avg_trust,
  COUNT(*) as n
FROM `chip50.public.demographics_protected_w35` d
JOIN `chip50.public.survey_responses_protected_w35` s
  ON d.row_hash = s.row_hash
WHERE d.party7 IS NOT NULL
  AND s.pol_trust_congress IS NOT NULL
GROUP BY d.region, d.party7
HAVING n >= 10  -- Cell suppression
ORDER BY d.region, d.party7;
```

## Adding New Waves

When you get a new wave (e.g., Wave 36):

### 1. Add the CSV file

```bash
# Place new file in data/
data/CSP_W36.csv
```

### 2. Process the new wave

```bash
python process_real_data_by_wave.py
```

This automatically detects and processes all `CSP_W*.csv` files.

### 3. Create SQL scripts for the new wave

Copy and modify existing scripts:

```bash
# Copy templates
cp sql/create_demographics_protected_w35.sql \
   sql/create_demographics_protected_w36.sql

cp sql/create_survey_responses_protected_w35.sql \
   sql/create_survey_responses_protected_w36.sql

# Update table references
# In each file, replace:
#   demographics_w35 → demographics_w36
#   demographics_protected_w35 → demographics_protected_w36
#   'wave', '35' → 'wave', '36'
```

### 4. Upload and create views

```bash
# Upload new wave
python upload_real_data_by_wave.py --waves 36

# Create views
./create_all_wave_views.sh
```

## Naming Conventions

### Wave Numbers to Table Names

| Wave | Raw Table Suffix | View Suffix | Filename Suffix |
|------|-----------------|-------------|-----------------|
| 35 | `_w35` | `_w35` | `_w35` |
| 35.1 | `_w35_1` | `_w35_1` | `_w35_1` |
| 36 | `_w36` | `_w36` | `_w36` |

**Rule:** Dots (`.`) in wave numbers become underscores (`_`) in table/file names.

### Full Table Names

```
Raw tables:      chip50.raw.{table_type}_w{wave}
Protected views: chip50.public.{table_type}_protected_w{wave}

Examples:
  chip50.raw.demographics_w35
  chip50.public.demographics_protected_w35_1
```

## Verification

After uploading and creating views, verify the data:

### Check Row Counts

```sql
-- Raw tables
SELECT 'demographics_w35' as table, COUNT(*) as rows
FROM `chip50.raw.demographics_w35`
UNION ALL
SELECT 'demographics_w35_1', COUNT(*)
FROM `chip50.raw.demographics_w35_1`;
```

### Check Views Exist

```sql
-- List all protected views
SELECT table_name
FROM `chip50.public.INFORMATION_SCHEMA.TABLES`
WHERE table_name LIKE '%protected%'
ORDER BY table_name;
```

### Test row_hash JOIN

```sql
-- Ensure demographics and survey responses match
SELECT
  'w35' as wave,
  d.rows as demo_rows,
  s.rows as survey_rows,
  j.matching_rows as joined_rows
FROM
  (SELECT COUNT(*) as rows FROM `chip50.public.demographics_protected_w35`) d,
  (SELECT COUNT(*) as rows FROM `chip50.public.survey_responses_protected_w35`) s,
  (SELECT COUNT(*) as matching_rows
   FROM `chip50.public.demographics_protected_w35` d
   JOIN `chip50.public.survey_responses_protected_w35` s
   ON d.row_hash = s.row_hash) j;
```

Expected: `demo_rows = survey_rows = joined_rows`

## Troubleshooting

### Issue: Processed files not found

**Symptom:**
```
⚠ Warning: Processed files not found for wave 35
```

**Solution:**
```bash
# Make sure you ran the processing step first
python process_real_data_by_wave.py

# Check processed files exist
ls -la data/processed/
```

### Issue: Table already exists

**Symptom:**
```
Already Exists: Table chip50:raw.demographics_w35
```

**Solution:**

The upload script uses `WRITE_TRUNCATE` by default, which should replace existing tables. If you get this error, manually delete the table:

```bash
bq rm -f chip50:raw.demographics_w35
```

Then re-run the upload.

### Issue: Column not found in view

**Symptom:**
```
Unrecognized name: pol_trust_congress at [28:3]
```

**Cause:** The SQL view references a column that doesn't exist in the raw table.

**Solution:**

1. Check which columns exist:
   ```sql
   SELECT column_name
   FROM `chip50.raw.INFORMATION_SCHEMA.COLUMNS`
   WHERE table_name = 'survey_responses_w35'
   ORDER BY column_name;
   ```

2. Edit the SQL view to remove or add columns as needed:
   ```bash
   vim sql/create_survey_responses_protected_w35.sql
   ```

3. Recreate the view:
   ```bash
   ./create_all_wave_views.sh
   ```

### Issue: Different columns across waves

**Symptom:** Wave 35 has column X but Wave 35.1 doesn't.

**Solution:** This is expected! Each wave can have different columns. When querying across waves, use:

```sql
-- Use COALESCE for columns that might not exist in all waves
SELECT
  wave,
  COALESCE(pol_trust_congress, NULL) as trust_congress
FROM `chip50.public.survey_responses_protected_w35`

UNION ALL

SELECT
  wave,
  COALESCE(pol_trust_congress, NULL) as trust_congress
FROM `chip50.public.survey_responses_protected_w35_1`;
```

Or only select columns that exist in both waves.

## Best Practices

1. **Process all waves at once** - Run `process_real_data_by_wave.py` without arguments to process all waves

2. **Consistent naming** - Always use the wave number exactly as it appears in the filename

3. **Version control SQL** - Keep SQL view scripts in git so you can recreate views

4. **Document wave changes** - Track which variables were added/removed in each wave

5. **Test before production** - Always verify row counts and JOINs after upload

6. **Backup raw data** - Keep original CSV files backed up before processing

## Comparison: Wave-Based vs. Combined

| Aspect | Wave-Based (This Workflow) | Combined (Alternative) |
|--------|---------------------------|----------------------|
| **Tables** | One per wave | Single table for all |
| **Schemas** | Can differ per wave | Must be uniform |
| **Queries** | Must specify wave | Filter by wave column |
| **Updates** | Add new tables | Append to existing |
| **Performance** | Fast for single wave | Fast for all waves |
| **Complexity** | More tables to manage | Simpler structure |

**When to use wave-based:**
- Schemas change across waves
- Often query single waves
- Want clear version separation
- Add waves incrementally

**When to use combined:**
- Consistent schema
- Usually query all waves
- Prefer simpler structure
- Cross-wave analysis primary use

## Additional Resources

- [Data Processing Guide](DATA_PROCESSING.md) - General data processing concepts
- [BigQuery Views Documentation](https://cloud.google.com/bigquery/docs/views)
- [SQL Scripts Directory](sql/) - All view creation scripts
