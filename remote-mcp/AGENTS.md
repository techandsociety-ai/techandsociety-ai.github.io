# AGENTS.md — CHIP50 Research MCP

## Mission

This MCP exists so that an analyst — or an AI assistant acting on an analyst's
behalf — can turn the CHIP50 panel survey into a **Pew Research–style report**
on what Americans believe and do, especially around social media, politics,
and information. Two things have to be true of every report this server helps
produce:

1. **Broadly accessible.** A reader with no statistics background should be
   able to skim the charts and pull out the headline finding (e.g. "62% of
   Republicans under 35 say they trust X less than they did a year ago").
2. **Statistically rigorous and reproducible.** Every number in the report
   must be traceable to a specific tool call against a specific wave (or set
   of waves), with weighting, suppression, and modeling choices documented
   well enough that another analyst could reproduce it exactly.

Pew's reports are the north star for tone and presentation: short narrative
sections built around one finding each, clean labeled charts, a methodology
section at the end that plainly describes how the sample was drawn and how
the numbers were computed, and an appendix that lets a careful reader check
the work.

## Audience & Tone for Generated Reports

- Write for a general US public audience — newspaper-explainer register, not
  academic-journal register. Avoid jargon ("odds ratio", "pseudo-R²") in the
  narrative sections; save it for the methodology/appendix.
- Lead with the finding, then the supporting numbers. "Younger adults are far
  more likely than seniors to get news from TikTok — 41% vs. 6%" beats "There
  is a statistically significant association between age category and TikTok
  news consumption (p < .001)."
- Every percentage quoted in narrative text should also appear in a table or
  chart in that section — never cite a number that isn't backed by a visible
  table/figure.
- Always state who the percentage is *of* ("of Democrats", "of all US
  adults", "of Twitter users") — this is the single most common source of
  misleading survey writing.

## Core Analytical Pattern

The MCP's job is to make the following loop fast, consistent, and hard to get
wrong:

1. **Pick a question/attitude/behavior** (an ordinal, binary, or categorical
   column — e.g. `use_tiktok`, `sm_trust_twitter`, `conspiracy_2`).
2. **Compute the share of a demographic group** that holds a given view or
   reports a given behavior — `generate_crosstab`, `get_ordinal_crosstab`,
   `get_categorical_crosstab`, `generate_crosstab_multi` for intersections.
3. **Repeat across waves** to look for movement over time —
   `generate_marginals_by_wave`, `generate_crosstab_by_wave`,
   `get_platform_trends`, `get_freq_trends` — rather than looping
   single-wave calls by hand.
4. **Test whether a pattern holds after controlling for confounders** —
   `run_ols_regression` / `run_logistic_regression`, survey-weighted by
   default.
5. **Assemble the findings into a report** — `generate_pdf_report`.

`introduce_mcp()` is the entry point and should always be called first; it
documents the full schema, every tool, wave-coverage caveats (e.g. wave 35.1's
small sample, ozempic only in wave 35), and a recommended quick-start order.
Keep that tool's docstring and JSON payload as the single source of truth for
"how to use this server" — update it whenever a tool is added, renamed, or a
new wave-coverage caveat is discovered.

### Multi-wave pattern detection

When a question spans multiple waves, the goal isn't just "here's the
number for each wave" — it's "here's whether/how this is changing, and for
whom." Prefer:

- A trend chart (line, one series per group) over a wall of per-wave tables.
- Calling out the direction and approximate magnitude of change in the
  narrative ("trust in Twitter/X among Independents fell roughly 8 points
  between wave 30 and wave 37").
- Checking whether a cross-sectional difference (e.g. by party) is stable
  across waves or only shows up in certain periods — this is what makes a
  finding a "pattern" rather than a one-wave artifact.

## Report Standards

### Plots — Pew Research style

Reports are built with `generate_pdf_report`, which renders charts via
`_render_chart` (matplotlib, CHIP50 navy/gold palette). The target look is
Pew's signature chart style:

- Minimal chrome: light gridlines, no heavy borders, muted axis colors.
- Direct value labels on bars/points so the reader doesn't have to read the
  axis.
- One clear idea per chart — a single demographic breakdown or a single
  trend line, not a dense multi-panel figure.
- Every figure gets a numbered caption ("Figure N. ...") and a "Source." line
  naming the CHIP50 wave(s) — drawn automatically from the report's `waves`
  argument — plus an optional "Note." line for caveats. This mirrors Pew's
  "Note:" / "Source:" convention at the bottom of every chart.
- Horizontal bar charts (`chart_type="hbar"` / `"grouped_hbar"`) are usually
  more readable than vertical ones when category labels are long (e.g.
  platform names, race/ethnicity categories) — prefer them for that case.

### Methodology section

`generate_pdf_report(include_methodology=True)` auto-appends a methodology
section covering: panel description, weighting, cell suppression (n < 10),
the -99 ordinal sentinel convention, and regression conventions. Treat this
section the way Pew treats its "Methodology" appendix — it should always
answer, in plain language:

- Who was surveyed, how, and when (panel description + field dates from
  `get_wave_metadata`).
- How weighting works and why unweighted *n* is shown separately.
- What's suppressed and why (privacy).
- How any model results in the report were estimated.

When a report draws on specific waves, pass them to `generate_pdf_report` via
`waves=[...]` (entries from `get_wave_metadata`) — don't leave the reader to
guess which fielding period a number comes from. The methodology section
adapts to the shape of the report:

- **Single wave → "deep dive"**: pass that wave's `get_wave_metadata` entry
  and the methodology section names the wave, its field dates, and its
  sample size, and notes explicitly that no cross-wave comparison is implied.
- **Multiple waves → "trend"**: pass each wave's entry and the methodology
  section describes the repeated cross-sectional design and adds a numbered
  table of field dates, unweighted *n*, and weighted *n* per wave.

### Reproducibility appendix

Every report should end with a supplementary section that lets a human
reviewer check and reproduce the analysis: the exact MCP tool calls (tool
name + arguments) used to produce each table/figure in the report, in order,
numbered to match the tables/figures they support. This is the
"show your work" section — a reviewer should be able to re-run those calls
verbatim against the same MCP and get the same numbers.

`generate_pdf_report` accepts a `tool_calls` parameter — a list of
`{"tool": ..., "arguments": {...}, "purpose": "..."}` dicts — and renders it
as a numbered, monospace "Appendix: Reproducibility" section at the end of
the PDF. **The calling assistant is responsible for passing this list** —
keep a running log of every MCP tool call (name + arguments + a one-line note
on what it produced) made while building a report, and pass it through to
`generate_pdf_report` so every report includes it.

## Roadmap / Known Gaps

These are the known gaps between the current implementation and the mission
above, roughly in priority order:

1. ~~**Tool-call appendix.**~~ Done — see Reproducibility appendix above.
2. ~~**Dynamic, wave-aware methodology.**~~ Done — `generate_pdf_report`
   accepts `waves=[...]` (from `get_wave_metadata`) and adapts the
   methodology section for single-wave "deep dive" vs. multi-wave "trend"
   reports (see Multi-wave pattern detection above).
3. ~~**Horizontal bar chart support.**~~ Done — `_render_chart` supports
   `chart_type="hbar"` / `"grouped_hbar"` for variables with long category
   labels (platforms, race/ethnicity, education).
4. ~~**Source/note line on every chart.**~~ Done — every chart in
   `generate_pdf_report` gets an automatic "Source." line naming the wave(s)
   from the report's `waves` argument, in addition to any caller-supplied
   "Note." text.
5. ~~**"Pattern" framing helpers.**~~ Done — `summarize_pattern_by_wave(variable,
   demographic, ordinal_value=None, flat_threshold_pp=3.0)` returns, per
   demographic group, the direction (increasing/decreasing/flat) and total
   change in percentage points from the first to last available wave, plus
   pairwise gap analysis (stable/widening/narrowing/reversed) between groups.
6. ~~**Ordinal distributions by wave x demographic.**~~ Done and verified
   (2026-06-14) — `generate_marginals_by_wave(variable, demographic)` returns
   the full per-category distribution for every wave x demographic cell with
   correct `CAST(wave AS FLOAT64)` handling (tested live with
   `support_cuba` x `race_cat_5`, no partitioning error).
   `get_ordinal_distribution_by_demographic(column, demographic, wave)` also
   confirmed working single-wave, including with `race_hisp` as the
   demographic (tested with `support_cuba` x `race_hisp`, wave 38).
7. ~~**Survey question text in source-of-truth repo.**~~ Done — W38 (and
   W35-W37.6) survey text files are live at
   `kateto/COVID19/SURVEYS/CSP_W38_Survey_Text.txt` in a clean
   `[varname] question text` + `code = label` format. This unblocks item 9
   below (variable metadata tool).
8. ~~**Intersectional subpopulation filtering.**~~ Done and verified
   (2026-06-14) — `get_ordinal_crosstab` and
   `get_ordinal_distribution_by_demographic` take an optional
   `filters: Dict[str, List[str]]` param, validated against
   `_ALL_REGRESSION_COLUMNS` and built via the existing
   `_build_filter_clauses` helper (same pattern already used by
   `run_ols_regression`/`run_logistic_regression`). Tested live:
   `get_ordinal_distribution_by_demographic(column="support_cuba",
   demographic="party3", filters={"race_hisp": ["1"]}, wave="38")` returns
   correct weighted distributions for the Hispanic subsample, broken out by
   party.
9. **Variable metadata tool (`get_variable_metadata`).** Open, now unblocked
   by item 7 — parse `CSP_W38_Survey_Text.txt` (and ideally older wave files,
   since most variables persist across waves) into a `{column: {question,
   response_labels, type, waves}}` map, expose via a new tool, and inline
   `scale_labels`/question wording into existing ordinal-tool outputs so
   Claude never has to guess what a "3" means.
10. **GLP-1 status categorization.** Mostly available now — confirmed
    `get_categorical_crosstab(column="ozempic", demographic=...)` already
    returns per-party shares for "Currently taking" / "Previously took /
    stopped" / "Considering" / "Not taking" / "Don't know" (codes 1-5) with
    labels attached. Optional follow-up: add a derived `glp1_status` column
    (same pattern as `ozempic_binary`/`ozempic_current` in
    `_DERIVED_COLUMNS`) that collapses codes 3-5 into a single "Never used"
    category for David's exact 3-bucket framing.
11. ~~**PHQ-9 composite (`phq9_total`).**~~ Done and verified (2026-06-14) —
    added `phq9_total` to `_DERIVED_COLUMNS`. CHIP50 codes each `phq9_1..9`
    item 1-4 ("Not at all" .. "Nearly every day"), so `phq9_total` sums
    `(phq9_i - 1)` across all nine items to produce the standard clinical
    0-27 scale (0-4 minimal, 5-9 mild, ..., 20-27 severe). Gated by a
    `CASE WHEN ... > 0` guard on all nine items so it's NULL (and dropped) if
    any item is -99/missing rather than silently summing a sentinel. Marked
    `binary: False` so it's only registered as a valid OLS outcome, not a
    logistic one. Also added a `.dropna(subset=cols)` safety net in
    `_fetch_regression_data` for any derived column that can evaluate to NULL
    per-row. Tested live: `run_ols_regression(outcome="phq9_total",
    predictors=["age_cat_8", "gender", "party3"], wave="38")` returns a
    plausible intercept (~9.3, "mild" band) and expected age/gender patterns
    (depression scores decline with age, men score lower than women).
12. **Height/weight ingestion.** Open — `height_1`, `height_2`,
    `weight_current`, `weight_pre_glp1` are present in
    `data/export_CHIP50_SocialMedia_vars_2026_06_06_merged.csv` and coded in
    `CSP_W38_Survey_Text.txt`, but not yet loaded into the BigQuery table or
    registered as columns in `server.py`. Needs a `load_data.sh` reload +
    column-list additions.
13. **`sm_post_mult_*` variables.** Blocked — confirmed absent from both the
    06-06 merged export and the newer `export_CHIP50_SocialMedia_vars_2026_06_06_22_09.csv`
    (284 cols, 24 `sm_post_gen_*`, 0 `sm_post_mult_*`). Needs a fresh export
    from Hong that includes these columns before any ingestion work can
    start.
14. **Subsample-specific weighting (e.g. `weight_cuba`).** Blocked on Katya —
    needs post-stratification weights generated for the `support_cuba`
    subsample, then a `weight_column` override param added to the relevant
    tools.
15. **Report-generation workflow + reliability testing.** In progress
    (2026-06-14) — the three reference `.docx` reports
    (`cuba_military_force_report.docx`, `glp1_use_report.docx`,
    `gerrymandering_amendment_report.docx`) are in `gold_standard_reports/`.
    Spot-checked `cuba_military_force_report.docx` against live tool calls:
    - `get_ordinal_distribution(column="support_cuba", wave="38")` reproduces
      Table 1 exactly (31.45/14.81/29.17/15.15/9.42 vs. reported
      31.5/14.8/29.2/15.2/9.4).
    - `get_ordinal_distribution_by_demographic(column="support_cuba",
      demographic="party7", wave="38")` reproduces Figure 2 exactly (Strong
      Republican: 50.3% support / 22.1% oppose; Lean Democrat (party7=5):
      9.4% support / 70.4% oppose — both match the report verbatim).
    - `run_ols_regression(outcome="support_cuba", predictors=["party7",
      "education_cat", "gender", "income_cat_10", "urban_type", "age_cat_8"],
      wave="38", treat_as_categorical=["party7","age_cat_8","income_cat_10"])`
      reproduces the Appendix A model exactly: n=3,807, R²=0.2125 (reported
      0.212), and every cited coefficient matches to 2 decimals (party7
      gradient -0.39/-0.27/-1.06/-1.55/-1.17/-1.35, age_cat_8 +0.37/+0.48/
      +0.40/+0.25/+0.16(p=.06), education College −0.21/Graduate −0.27/Some
      College −0.15 vs. HS-grad baseline, gender male +0.05 (p=.22),
      rural/suburban/urban gap +0.12/0/+0.03).
    Conclusion so far: the MCP's existing tools (`get_ordinal_distribution`,
    `get_ordinal_distribution_by_demographic`, `run_ols_regression`) are
    sufficient to reproduce this report's numbers exactly — no backend gaps
    found for this report. The gap, if any, is in `generate_pdf_report`'s
    narrative/appendix depth vs. these analyst-written reports (Appendix A
    "analytic memo" and Appendix B "methodological evaluation" are
    hand-authored synthesis, not auto-generated). Remaining work: spot-check
    `glp1_use_report.docx` and `gerrymandering_amendment_report.docx`
    similarly, then decide whether `generate_pdf_report`'s narrative
    generation needs a "memo/appendix" mode or whether that layer is
    intentionally left to the calling analyst/assistant.
16. **Polarization variable inventory for DDF demo.** Open — cross-check
    `ATTITUDINAL_COLUMNS`/`POL_*` against the survey text file for a first
    pass, then confirm completeness with Hong.
17. **Design decision: should "analytics-only" batteries be restricted to
    regression tools?** Open (2026-06-19) — `GEN_POST_COLUMNS`
    (`sm_post_gen_*`), `COV_BEH_COLUMNS`, `COV_TRUST_COLUMNS`,
    `ELECTION_COLUMNS` (`democ_1`, `cand24`, `vote24`, `news_elect_*`,
    `source_elect`, `media_elect`, `news_sat`), and `W38_POLITICAL_COLUMNS`
    (`state_dem`, `gerry_*`, `support_cuba`) are currently in
    `ALL_ORDINAL_COLUMNS` and therefore accessible in `get_ordinal_distribution`,
    `get_ordinal_crosstab`, and `get_ordinal_distribution_by_demographic` — even
    though the PI's tool-access matrix marks them as blank (regression-only).
    Decision needed: if the intent is truly regression-only, remove these
    batteries from `ALL_ORDINAL_COLUMNS` into a separate `_REGRESSION_ONLY_ORDINAL`
    list (still included in `_ALL_REGRESSION_COLUMNS` and `_SENTINEL_COLUMNS`).
18. **Design decision: should `ozempic` and `ozempic_why` be removed from
    `ALL_ORDINAL_COLUMNS`?** Open (2026-06-19) — both are currently in
    `ALL_ORDINAL_COLUMNS` (via `OZEMPIC_COLUMNS`), which means the ordinal
    distribution tools accept them. But their response codes are nominal/
    non-linear (`ozempic`: 1=currently taking … 5=don't know; `ozempic_why`:
    codes 1, 4, 5), so ordinal distributions are misleading. The purpose-built
    `get_categorical_crosstab` is the correct tool for these two variables.
    Consider removing them from `ALL_ORDINAL_COLUMNS` (while keeping
    `ozempic_time_1` / `ozempic_time_2` there, as those are continuous).

## Architecture

### Remote MCP on Cloud Run + BigQuery

- **Transport**: Remote MCP over HTTPS/SSE (`mcp.server.sse.SseServerTransport`
  + FastAPI), not stdio — Claude connects to a URL, not a local process.
- **Auth**: Google OAuth via Claude Settings → Connectors.
- **Data**: BigQuery project `chip50`, dataset `social_media_demographics`,
  table `panel_data_indexed` (CHIP50 panel survey: ~10K respondents/wave,
  38+ waves, 230+ variables covering ~20 social media platforms, core
  demographics, PHQ-9, and political attitudes).
- **Reports**: `generate_pdf_report` builds a PDF with ReportLab + matplotlib
  and uploads it to the `chip50-reports` GCS bucket, returning a signed URL;
  `get_report_status` polls the async job.
- **Privacy**: cells with n < 10 are suppressed at the SQL layer and again in
  Python before being returned.

### Why remote, not local

| Aspect | This project (remote) | Traditional MCP (local) |
|--------|----------------------|--------------------------|
| Deployment | Google Cloud Run | Local machine |
| Transport | SSE / HTTPS | stdio |
| Configuration | OAuth + URL | `command` + `args` |
| Access | Anywhere with internet | Only on local machine |
| Data | BigQuery (cloud) | Local files |

Running remotely keeps BigQuery credentials and query costs off individual
analysts' machines, lets multiple analysts share one always-on server, and
means the dataset and report-generation logic live in one place that can be
updated without redistributing anything to clients.

### Development workflow

```bash
./test_local.sh   # run the server on localhost:8080
gcloud run logs read social-media-demographics-mcp --region us-central1
```

Deployment is automatic: `.github/workflows/deploy.yml` builds and deploys to
Cloud Run on every push to `main` (also triggerable via
`workflow_dispatch`). `./deploy.sh` is a manual fallback for when a
local/out-of-band rebuild or restart is needed (e.g. CI is down or you need to
test an image before merging) — it is not part of the normal release path.

`test_regression.py` covers the OLS/logistic regression helpers; run it with
`pytest` before deploying changes to those code paths.
