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
- Every figure gets a numbered caption ("Figure N. ...") and, where relevant,
  a source/note line describing the population and wave(s) (this mirrors
  Pew's "Note:" / "Source:" convention at the bottom of every chart).
- Horizontal bar charts are usually more readable than vertical ones when
  category labels are long (e.g. platform names, race/ethnicity categories) —
  prefer them for that case even though `_render_chart` currently only does
  vertical bars (see Roadmap).

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
3. **Horizontal bar chart support** in `_render_chart`, for variables with
   long category labels (platforms, race/ethnicity, education).
4. **Source/note line on every chart** by default (population description +
   wave(s)), not just when the caller remembers to pass `notes`.
5. **"Pattern" framing helpers.** Consider a tool that, given a column and a
   demographic, returns a structured summary across waves (direction, total
   change, whether the cross-sectional gap is stable) to make the
   trend-narrative step in "Multi-wave pattern detection" above less manual.

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
./deploy.sh       # build + deploy to Cloud Run
gcloud run logs read social-media-demographics-mcp --region us-central1
```

`test_regression.py` covers the OLS/logistic regression helpers; run it with
`pytest` before deploying changes to those code paths.
