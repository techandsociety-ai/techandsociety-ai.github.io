# New Data Ingestion Playbook

Run these steps every time a fresh export CSV arrives from Hong (or any other source).
Each step tells you exactly which file to touch and what to change.

---

## Step 0 — Identify the new file

Put the new CSV in `data/`. Run any pre-merge scripts first (e.g. `scripts/merge_plumbing.py`
if a county-level join is needed). At the end of this step you should have one clean,
fully-merged CSV ready to load.

### Merging the county-level plumbing file

`scripts/merge_plumbing.py` joins on respondent ID, but the two files use inconsistent
ID formats: the plumbing crosswalk (`Plumbing_data_merged_with_CHIP50_respondents_v1_*.csv`)
has a mix of IDs with and without dashes (e.g. `0a0a0d02a8d02df17a34` vs
`0a0a6e5b-ab08-8441-6d4c-708d0fc71c62`), while the main CHIP50 export always uses
dashed UUIDs. **Always strip dashes from both sides before joining** — the script does
this via `strip_id()` which calls `val.replace("-", "")`. Expect a match rate of ~97%;
the ~3% unmatched rows receive empty strings for `fips`, `county`, and
`running_water_pct`. Update `CHIP50_CSV` and `OUT_CSV` in the script to point at the
new export filename before running.

---

## Step 1 — Diff the column list

```bash
# Print columns that are in the new CSV but NOT in the current indexed table
python3 - <<'EOF'
import csv, subprocess, json

NEW_CSV = "../data/<YOUR_FILE>.csv"  # ← replace

with open(NEW_CSV, newline="") as f:
    new_cols = set(csv.DictReader(f).fieldnames)

# Columns currently in create_schema.sql (proxy for what's in BQ)
import re
sql = open("sql/create_schema.sql").read()
bq_cols = set(re.findall(r'AS\s+(\w+)', sql))

added   = sorted(new_cols - bq_cols)
removed = sorted(bq_cols - new_cols)
print(f"ADDED ({len(added)}):",   added[:40], "..." if len(added) > 40 else "")
print(f"REMOVED ({len(removed)}):", removed)
EOF
```

Record the `ADDED` list — that's your work queue for steps 2–5.

---

## Step 2 — Classify each new column and update `create_schema.sql`

For each new column, determine its type by checking:
1. The survey text file (`kateto/COVID19/SURVEYS/CSP_W<N>_Survey_Text.txt`) for response codes.
2. A quick value scan: `python3 -c "import pandas as pd; print(pd.read_csv('../data/<FILE>.csv')['<COL>'].value_counts().head(20))"`

| Pattern | Type | SQL cast | Notes |
|---------|------|----------|-------|
| Only 0 and 1 (+ empty) | Binary | `CAST(col AS INT64)` | NULL = not asked this wave |
| Integer codes 1–N with -99 | Ordinal | `CAST(col AS INT64)` | -99 = skipped/refused |
| Float/continuous | Continuous | `CAST(col AS FLOAT64)` | no -99 sentinel |
| Free text | Text | `col` (no cast) | exclude from analysis lists |

Add the new columns to `sql/create_schema.sql` in the correct section, following the
existing `CAST(colname AS TYPE) as colname,` pattern. Keep related columns grouped
(e.g. all `ai_how_*` together).

---

## Step 3 — Register each column in `server.py`

Every new column must appear in **at least one** list in `server.py`, or the MCP will
silently ignore it. Use this decision tree:

```
Is it a complex SQL expression built from other columns?
  → Add to _DERIVED_COLUMNS (with "sql", "source", "description", "binary" keys)

Is it binary 0/1?
  → Add to an appropriate *_COLUMNS list (e.g. ALL_BINARY_COLUMNS or a new battery list)
  → Add to _BINARY_COLUMNS  (valid as logistic outcome)
  → Add to _ALL_REGRESSION_COLUMNS
  → Add to _ORDINAL_TOOL_COLUMNS  (so ordinal tools accept it — they skip the -99 filter for binary)

Is it ordinal with -99 sentinel?
  → Add to an appropriate *_COLUMNS list
  → Add to ALL_ORDINAL_COLUMNS (this also registers it in _SENTINEL_COLUMNS automatically)
  → Add to _ALL_REGRESSION_COLUMNS
  → If response codes are nominal/non-linear (e.g. ozempic, ozempic_why):
      also add to CATEGORICAL_ORDINAL_COLUMNS and consider get_categorical_crosstab

Is it continuous (float)?
  → Add to a named *_COLUMNS list
  → Add to _ALL_REGRESSION_COLUMNS only (NOT ALL_ORDINAL_COLUMNS — no -99 sentinel)

Is it a new platform (use_*, freq_*, sm_trust_*, sm_post_pol_*)?
  → Add to the matching *_COLUMNS list AND to LATE_PLATFORMS / LATE_FREQ_PLATFORMS if
    it has NULLs in earlier waves.
```

### Quick checklist per new column

- [ ] Listed in at least one named `*_COLUMNS` constant
- [ ] If ordinal: in `ALL_ORDINAL_COLUMNS` → auto-registers in `_SENTINEL_COLUMNS`
- [ ] If binary: in `_BINARY_COLUMNS`
- [ ] In `_ALL_REGRESSION_COLUMNS`
- [ ] If binary or derived: in `_ORDINAL_TOOL_COLUMNS`
- [ ] `wave_coverage` note in `get_available_variables` updated if wave-restricted

---

## Step 4 — Add variable descriptions

**For `_DERIVED_COLUMNS` entries** — each needs a `"description"` key. Write one sentence:
what the variable measures, its range, and any important caveats (wave restriction,
coding quirks, NULL conditions).

**For named `*_COLUMNS` lists** — descriptions appear automatically in
`get_available_variables` for batteries whose list is included in the response dict
(see Step 6). No per-column description file needed for standard columns.

**For genuinely unusual columns** — add an inline comment above the list entry in
`server.py`:
```python
"new_col",  # one-line: scale, wave coverage, or coding quirk worth knowing
```

---

## Step 5 — Update question wording in `question_wording.py`

Source: `https://github.com/kateto/COVID19/tree/master/SURVEYS`
File format: `CSP_W<N>_Survey_Text.txt`

For each new variable, find its question text in the survey file and add an entry to
`QUESTION_WORDING` in `remote-mcp/question_wording.py`:

```python
"new_col": "Exact question stem from survey text — Item label if matrix item",
```

**Matrix / multi-select items** use the pattern `"stem — item label"` (em dash, not
hyphen), matching the existing entries for `use_*`, `sm_trust_*`, `pol_news*`, etc.

**If the survey text file for the new wave isn't on GitHub yet**, ask (the repo
owner is kateto). Don't leave wording blank — at minimum note the wave number and
approximate topic so `get_question_wording` returns something useful.

---

## Step 6 — Surface new columns in `get_available_variables`

Open `server.py` and find the `get_available_variables` function (~line 1020).
The return dict lists every named battery. If you added a new battery constant
(e.g. `NEW_BATTERY_COLUMNS`), add it here:

```python
"new_battery_columns": NEW_BATTERY_COLUMNS,
```

If the battery is wave-restricted, add a note to the `"wave_coverage"` string:
```python
"wave_coverage": "... new_battery_col from wave N+.",
```

Also update the `introduce_mcp` tool docstring / JSON payload if it lists column
counts or battery names (search for `"introduce_mcp"` around line 807).

---

## Step 7 — Load data and deploy

```bash
# 1. Update load_data.sh to point at the new CSV, then:
cd remote-mcp
./load_data.sh ../data/<YOUR_FILE>.csv

# 2. Smoke-test locally
./test_local.sh
# In another terminal: curl http://localhost:8080/mcp and verify new columns appear

# 3. Run regression tests
pytest test_regression.py

# 4. Push to main → GitHub Actions deploys automatically
git add -A
git commit -m "Load <wave/date> export: add <N> new columns (<short description>)"
git push origin main
```

---

## Step 8 — Verify end-to-end in Claude

After deployment (~2 min), open Claude and run:

```
get_available_variables()
```

Confirm the new battery or column names appear in the response.

```
get_question_wording("<new_col>")
```

Confirm question text is returned (not "unknown variable").

```
get_ordinal_distribution(column="<new_col>", wave="<N>")
# or for binary:
generate_marginals(columns=["<new_col>"], wave="<N>")
```

Confirm numeric output with reasonable values and non-zero n.

---

## Common mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Column in SQL but not in server.py list | Tool returns "invalid column" error | Add to correct `*_COLUMNS` list and `_ALL_REGRESSION_COLUMNS` |
| Ordinal column missing from `ALL_ORDINAL_COLUMNS` | `-99` sentinel not filtered → biased means | Add to `ALL_ORDINAL_COLUMNS` |
| Binary column added to `ALL_ORDINAL_COLUMNS` | `-99` filter erroneously applied (0/1 values pass, but description is wrong) | Remove from `ALL_ORDINAL_COLUMNS`; add to `_BINARY_COLUMNS` and `_ORDINAL_TOOL_COLUMNS` instead |
| Nominal-coded column left in `ALL_ORDINAL_COLUMNS` | Misleading mean reported (e.g. mean of ozempic codes) | Move to `CATEGORICAL_ORDINAL_COLUMNS`; use `get_categorical_crosstab` |
| Column in server.py but missing from `create_schema.sql` | BigQuery query error: "Unrecognized name: col" | Add `CAST(col AS TYPE) as col` to `sql/create_schema.sql` and re-run `load_data.sh` |
| Wave-restricted column, no `wave_coverage` note | Claude queries all waves, gets mostly NULLs | Add note to `get_available_variables` `wave_coverage` key |
| New column list not added to `get_available_variables` return | `get_available_variables()` doesn't list it | Add `"new_battery": NEW_BATTERY_COLUMNS` to the return dict |
