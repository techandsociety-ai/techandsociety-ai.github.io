# CHIP50 Report Prompts

Self-contained prompts for reproducing the three gold-standard reports using only the CHIP50 MCP server — no external data required. Each prompt specifies a research question, the exact variables and waves to query, the analytical structure, and the expected output. Run these prompts with a Claude instance that has the CHIP50 MCP connector configured.

---

## 1. Cuba Military Force Report

**File:** `cuba_military_force_report.docx`

```
I want a Pew-style public-opinion report on American attitudes toward using U.S. military force to overthrow the Cuban government, based on Wave 38 of the CHIP50 survey. Please do the following:

1. Call introduce_mcp() to confirm which tools are available and load the schema.

2. Call get_wave_metadata() and save the Wave 38 entry (field dates, unweighted n, weighted n) — you will need it for the methodology section and the generate_pdf_report waves argument.

3. Gather data for the report using these tool calls, in order:

   a. get_ordinal_distribution(column="support_cuba", wave="38")
      → Overall distribution of the 5-point support scale (1=strongly oppose … 5=strongly support).

   b. get_ordinal_distribution_by_demographic(column="support_cuba", demographic="party7", wave="38")
      → Party breakdown (7-point scale: 1=Strong Republican … 7=Strong Democrat).

   c. get_ordinal_distribution_by_demographic(column="support_cuba", demographic="education_cat", wave="38")
      → Education breakdown.

   d. get_ordinal_distribution_by_demographic(column="support_cuba", demographic="gender", wave="38")
      → Gender breakdown.

   e. get_ordinal_distribution_by_demographic(column="support_cuba", demographic="income_cat_10", wave="38")
      → Income bracket breakdown (10 ordered brackets).

   f. get_ordinal_distribution_by_demographic(column="support_cuba", demographic="urban_type", wave="38")
      → Rurality breakdown (rural / suburban / urban).

   g. get_ordinal_distribution_by_demographic(column="support_cuba", demographic="age_cat_8", wave="38")
      → Age group breakdown (8 groups from 18–20 to 80+).

   h. get_ordinal_distribution_by_demographic(column="support_cuba", demographic="race_cat_5", wave="38")
      → Race/ethnicity breakdown (5 groups).

   i. get_ordinal_crosstab(column="support_cuba", demographic="party3", wave="38", filters={"race_hisp": ["1"]})
      → Hispanic respondents by party (3-point) — for the Hispanic × party sub-analysis.

   j. run_ols_regression(
        outcome="support_cuba",
        predictors=["party7", "education_cat", "gender", "income_cat_10", "urban_type", "age_cat_8"],
        wave="38",
        treat_as_categorical=["party7", "age_cat_8", "income_cat_10"]
      )
      → Primary multivariate model. References: Strong Republican (party7=1), HS Graduate, Male, income bracket 1, Suburban, age 18–20.

   k. run_ols_regression(
        outcome="support_cuba",
        predictors=["party7", "education_cat", "gender", "income_cat_10", "urban_type", "age_cat_8", "race_cat_5"],
        wave="38",
        treat_as_categorical=["party7", "age_cat_8", "income_cat_10", "race_cat_5"]
      )
      → Supplementary model adding race/ethnicity.

4. Build the report using generate_pdf_report with the following structure:

   Title: "Americans Lean Against Invading Cuba — but Republicans Stand Apart"
   Subtitle: "Public opinion on U.S. military force against Cuba, Wave 38"

   Sections:
   - Executive summary (bullet list of 5–6 key findings)
   - Context (1–2 paragraphs: what is the political moment; who asked the question and of whom — note this item was asked of ~3,800 of ~16,600 wave respondents)
   - Findings: Topline (Figure 1 — hbar chart of the 5-point distribution)
   - Findings: By party (Figure 2 — grouped_hbar of support/neither/oppose by party7)
   - Findings: By education (Figure 3 — grouped_hbar)
   - Findings: By gender (Figure 4 — grouped_hbar)
   - Findings: By income (Figure 5 — grouped_hbar, pair adjacent brackets)
   - Findings: By rurality (Figure 6 — grouped_hbar)
   - Findings: By age (Figure 7 — grouped_hbar)
   - Findings: By race and ethnicity (Figure 8 — grouped_hbar)
   - Further findings: Hispanic support by party (Table 9 — weighted mean on 1–5 scale)
   - Methods (describe data source, measure, estimation approach, regression references)
   - Appendix A — Analytic Memo (multivariate results in plain language, candidate storylines, consistency with prior evidence)

   Set include_methodology=True. Pass the Wave 38 metadata entry in the waves argument. Pass a log of every tool call above in the tool_calls argument.

Report conventions:
- Ordinal direction: 1 = strongly oppose, 3 = neither, 5 = strongly support (confirmed against questionnaire).
- "Support" = codes 4+5 combined; "Oppose" = codes 1+2 combined; "Neither" = code 3.
- Lead every narrative paragraph with the finding, not the statistical test.
- Call a gap "significant" only where the regression p-value < .05; where a descriptive gap does not survive controls, say so explicitly.
- Suppress cells with n < 10 (the tool does this automatically); note any combined/pooled cells.
```

---

## 2. GLP-1 Use Report

**File:** `glp1_use_report.docx`

```
I want a Pew-style trend report on who is taking GLP-1 drugs (e.g., Ozempic, Wegovy) and how that changed across two 2025 survey waves of the CHIP50 panel. Please do the following:

1. Call introduce_mcp() to confirm available tools and load the schema.

2. Call get_wave_metadata() and save the Wave 35 and Wave 38 entries (field dates, unweighted n, weighted n) — you will need them for the methodology section and the generate_pdf_report waves argument.

3. Gather data using these tool calls, in order:

   a. generate_marginals_by_wave(variable="ozempic", waves=["35", "38"])
      → Full 5-category distribution of ozempic status in each wave.
      Categories: 1=Currently taking, 2=Previously took/stopped, 3=Considering/interested, 4=Not taking/no interest, 5=Prefer not to answer.

   b. get_categorical_crosstab(column="ozempic", demographic="party3", waves=["35", "38"])
      → GLP-1 status by party (3-point: Republican / Independent-Other / Democrat) in each wave.

   c. get_categorical_crosstab(column="ozempic", demographic="education_cat", waves=["35", "38"])
      → By education level.

   d. get_categorical_crosstab(column="ozempic", demographic="gender", waves=["35", "38"])
      → By gender.

   e. get_categorical_crosstab(column="ozempic", demographic="income_cat_10", waves=["35", "38"])
      → By income bracket (1–10). Pair adjacent brackets for display (1+2, 3+4, 5+6, 7+8, 9+10).

   f. get_categorical_crosstab(column="ozempic", demographic="urban_type", waves=["35", "38"])
      → By rurality.

   g. get_categorical_crosstab(column="ozempic", demographic="age_cat_8", waves=["35", "38"])
      → By age group. Combine "18–20" and "21–30" into "30 and under"; combine "71–80" and "80+" into "71 and over."

   h. run_logistic_regression(
        outcome="ozempic_current",
        predictors=["party3", "education_cat", "gender", "income_cat_10", "urban_type", "age_cat_8"],
        wave="35",
        treat_as_categorical=["party3", "age_cat_8", "income_cat_10"]
      )
      → Logistic regression of current use (1/0) on demographics, Wave 35.
      References: Independent/Other, HS Graduate, Male, income bracket 1, Rural, age 31–40.

   i. run_logistic_regression(
        outcome="ozempic_current",
        predictors=["party3", "education_cat", "gender", "income_cat_10", "urban_type", "age_cat_8"],
        wave="38",
        treat_as_categorical=["party3", "age_cat_8", "income_cat_10"]
      )
      → Same model in Wave 38.

   j. generate_marginals_by_wave(variable="ozempic_reason", waves=["35", "38"])
      → Stated reason for taking (Diabetes / Weight loss / Both) among current/former users.

   k. generate_marginals_by_wave(variable="ozempic_duration", waves=["35", "38"])
      → Duration of use among current/former users.

   l. get_categorical_crosstab(column="ozempic", demographic="education_cat", waves=["35", "38"])
      Already done at step c — use for "previously took" sub-table (Table 11: former users by demographic).
      Repeat for each relevant demographic as needed to build Table 11.

4. Build the report using generate_pdf_report with this structure:

   Title: "Who Is Taking GLP-1 Drugs — and How That Changed Across 2025"
   Subtitle: "A two-wave trend analysis, CHIP50 Waves 35 and 38"

   Sections:
   - Executive summary (6 bullets: overall rise, income gradient, age gap narrowing, gender gap widening, stable structure elsewhere, discontinuation share)
   - Context (2–3 paragraphs: GLP-1 policy backdrop in 2025; clinical need — obesity ~40%, diabetes ~12% of adults, both concentrated in lower-income/less-educated groups)
   - Findings: Topline and trend (Figure 1 — grouped_hbar or stacked bar comparing W35 and W38 distributions; include "ever used" = currently + previously as a derived row)
   - Findings: By party (Figure 2 — current use and consideration by party3, both waves)
   - Findings: By education (Figure 3 — grouped bar; note "HS or less" combined)
   - Findings: By gender (Figure 4 — bar comparing current use and consideration by gender, both waves)
   - Findings: By income (Figure 5 — paired brackets, both waves)
   - Findings: By rurality (Figure 6 — both waves)
   - Findings: By age (Figure 7 — age groups, both waves; note "30 and under" and "71 and over" combined ends)
   - Findings: Multivariate model (Figure 8 — forest plot style: odds ratios ± 95% CI for both waves side by side)
   - Further findings: Why users take GLP-1s (Figure 9 — reason by wave, current/former users only)
   - Further findings: Duration of use (Figure 10 — duration by wave)
   - Further findings: Former users (Table 11 — "previously took" % by demographic, both waves)
   - Methods (source, outcome coding, regression design, income coding, suppression, labels, inference caveats)
   - Data appendix (full-precision tables for all figures)

   Set include_methodology=True. Pass both wave metadata entries in the waves argument. Pass a full tool_calls log.

Report conventions:
- Always state which ozempic category each percentage refers to (currently taking / previously took / considering / not taking).
- In trend comparisons, lead with the direction and magnitude of change, not just the levels.
- For the income figure, combine adjacent brackets by summing weighted population counts, not averaging percentages.
- In the model section, report odds ratios (not log-odds) with 95% CIs; note that pseudo-R² is modest (~0.05) and expected for an adoption model.
- Suppress cells with n < 10; mark lower-bound pooled estimates with "+".
```

---

## 3. Gerrymandering Amendment Report

**File:** `gerrymandering_amendment_report.docx`

```
I want a Pew-style public-opinion report on American attitudes toward a constitutional amendment to stop gerrymandering, based on Wave 38 of the CHIP50 survey. Please do the following:

1. Call introduce_mcp() to confirm available tools and load the schema.

2. Call get_wave_metadata() and save the Wave 38 entry (field dates, unweighted n, weighted n).

3. Gather data using these tool calls, in order:

   a. get_ordinal_distribution(column="gerry_amend", wave="38")
      → Full 6-category distribution.
      Scale: 1=strongly support, 2=somewhat support, 3=neither support nor oppose, 4=somewhat oppose, 5=strongly oppose, 6=not sure.
      Note: this is the opposite direction from support_cuba (here 1=support, 5=oppose).

   b. get_ordinal_distribution_by_demographic(column="gerry_amend", demographic="party7", wave="38")
      → By 7-point party identification.

   c. get_ordinal_distribution_by_demographic(column="gerry_amend", demographic="race_cat_5", wave="38")
      → By race/ethnicity (5 groups).

   d. get_ordinal_distribution_by_demographic(column="gerry_amend", demographic="education_cat", wave="38")
      → By education.

   e. get_ordinal_distribution_by_demographic(column="gerry_amend", demographic="gender", wave="38")
      → By gender.

   f. get_ordinal_distribution_by_demographic(column="gerry_amend", demographic="income_cat_10", wave="38")
      → By income bracket.

   g. get_ordinal_distribution_by_demographic(column="gerry_amend", demographic="urban_type", wave="38")
      → By rurality.

   h. get_ordinal_distribution_by_demographic(column="gerry_amend", demographic="age_cat_8", wave="38")
      → By age group.

   i. get_ordinal_distribution_by_demographic(column="gerry_amend", demographic="state", wave="38")
      → By state (for geographic analysis). Aggregate to Census regions (Northeast, South, Midwest, West) by summing weighted counts; note that per-state n is too small for reliable estimates in most states.

   j. run_ols_regression(
        outcome="gerry_amend",
        predictors=["party7", "race_cat_5", "education_cat", "gender", "income_cat_10", "urban_type", "age_cat_8"],
        wave="38",
        treat_as_categorical=["party7", "race_cat_5", "age_cat_8", "income_cat_10"],
        filters={"gerry_amend": ["1","2","3","4","5"]}
      )
      → OLS regression on 1–5 scale excluding "not sure" (6). References: Strong Republican (party7=1), White, HS Graduate, Male, income bracket 1, Suburban, age 18–20.
      Note: "not sure" (6) must be excluded from the regression — it is not a scale point.

4. Build the report using generate_pdf_report with this structure:

   Title: "Broad, Bipartisan Support for a Constitutional Amendment to Stop Gerrymandering — but a Big Undecided Middle"
   Subtitle: "Public opinion on anti-gerrymandering amendment, CHIP50 Wave 38"

   Sections:
   - Executive summary (5 bullets: 3-to-1 support overall; bipartisan with independents as the low point; education gradient; White respondents most supportive; the through-line is engagement not polarization)
   - Context (2 paragraphs: the redistricting/gerrymandering policy backdrop; survey question wording — "Would you support or oppose a constitutional amendment that would prohibit states from redrawing congressional district boundaries to help one political party over another?")
   - Findings: Topline (Figure 1 — hbar of 6-category distribution; describe "not sure" separately from the 1–5 scale)
   - Findings: By party (Figure 2 — grouped_hbar of support/neither/oppose/not-sure by party7)
   - Findings: By race and ethnicity (Figure 3 — grouped_hbar)
   - Findings: By education (Figure 4 — grouped_hbar; note the ~39-point spread from HS-or-less to graduate)
   - Findings: By gender (Figure 5 — grouped_hbar; note women more likely to be "not sure")
   - Findings: By income (Figure 6 — grouped_hbar)
   - Findings: By community type (Figure 7 — grouped_hbar)
   - Findings: By age (Figure 8 — grouped_hbar)
   - Further findings: Geographic variation (Table 9 — Census-region aggregates; note state-level estimates are noisy)
   - Methods (data, measure, scale direction confirmation, estimation, regression design, multiple-comparison discipline)
   - Appendix A — Analytic Memo (multivariate findings in full; candidate storylines; consistency with prior redistricting polling)
   - Appendix B — Methodological Evaluation (candid assessment: value-label verification, the large middle, non-probability panel, model-based SEs, multiple comparisons, state-level noise, provenance gaps)

   Set include_methodology=True. Pass the Wave 38 metadata entry in the waves argument. Pass a full tool_calls log.

Report conventions:
- Scale direction: 1=strongly support → 5=strongly oppose (confirmed against questionnaire). "Support" = codes 1+2; "Oppose" = codes 4+5; "Neither" = code 3; "Not sure" = code 6.
- The key narrative frame: gaps across demographics are mostly gaps in certainty (not-sure rate), not in opposition.
- Low R² (~0.06) is itself a headline finding — this is not a polarized issue.
- Call a gap "significant" only where regression p < .05; note where descriptive gaps wash out under controls (community type washes out; gender survives).
- Suppress cells with n < 10; note that "somewhat oppose" cells for 3 small states were suppressed.
- State-level estimates are for the 50-state national panel — not state-representative polls; communicate that limitation clearly.
```
