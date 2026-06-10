# CHIP50 Research MCP Server

A **remote MCP server** that gives analysts (and AI assistants acting on
their behalf) direct access to the CHIP50 panel survey, and the tools to turn
it into accessible, statistically rigorous, Pew Research–style reports on
what Americans believe and do — especially around social media, politics, and
information.

See [`AGENTS.md`](AGENTS.md) for the full mission, analytical conventions,
and report standards this server is designed to support.

## Overview

This is a **remote** Model Context Protocol (MCP) server, deployed on Google
Cloud Run, not run locally. It gives Claude (or any MCP client) direct,
privacy-protected access to the CHIP50 panel via BigQuery over HTTPS.

- ✅ **Remote**: Runs on Google Cloud Run, accessible via HTTPS — no local
  setup or BigQuery credentials needed by analysts
- ✅ **OAuth-protected**: Connect via Claude Settings → Connectors with your
  Google account
- ✅ **Privacy-protected**: Automatic cell suppression for small counts
  (n < 10)
- ✅ **Always available**: Single always-on Cloud Run instance, no cold starts

## The Data

The CHIP50 panel is a repeated-wave survey of US adults covering:

- **Platform use & frequency** for ~20 social media platforms (Facebook,
  Instagram, YouTube, Twitter/X, TikTok, Snapchat, LinkedIn, Reddit, and
  more, including later-panel platforms like Threads and Bluesky)
- **Trust** in each platform, and **political posting/news** behavior
- **Core demographics**: age, gender, race/ethnicity, education, income,
  party (3- and 7-category), urbanicity, state
- **Attitudes**: ideology, economic outlook, election-related questions,
  conspiracy beliefs, political information/discussion
- **PHQ-9** mental health screening (population-level aggregates only)

~10K respondents per wave, 38+ waves to date. All percentages and means
returned by the tools are **survey-weighted population estimates**; cells
with fewer than 10 respondents are suppressed.

## Available Tools

Call `introduce_mcp()` first — it returns the full schema, every tool, and
wave-coverage caveats, and is the source of truth for how to use this server.

### Discovery
- **`introduce_mcp`** — overview of the server, schema, and recommended
  workflow.
- **`get_available_variables`** — live dataset metadata (column groups, wave
  range).
- **`get_wave_metadata`** — per-wave respondent counts, field dates, and
  which questions/platforms were fielded.

### Single-variable distributions
- **`generate_marginals`** / **`generate_marginals_batch`** — distribution of
  one (or several, in parallel) variables.
- **`generate_marginals_by_wave`** — one variable's distribution across all
  waves, optionally stratified by a demographic.
- **`get_ordinal_distribution`** / **`get_ordinal_distribution_by_demographic`**
  — weighted % distribution for ordinal scales (frequency, trust, ideology,
  PHQ-9, etc.), overall or by demographic group.

### Cross-tabulations
- **`generate_crosstab`** — platform adoption (or any binary) by one
  demographic.
- **`generate_crosstab_filtered`** — same, restricted to a sub-population
  (e.g. Facebook use by gender among rural respondents).
- **`generate_crosstab_batch`** — one platform across multiple demographics,
  in parallel.
- **`generate_crosstab_by_wave`** — platform × demographic across all waves.
- **`generate_crosstab_multi`** — variable broken down by 2+ demographic
  dimensions at once (for heatmaps/interaction tables).
- **`get_ordinal_crosstab`** — weighted mean of an ordinal variable by
  demographic (e.g. mean Twitter trust by party).
- **`get_categorical_crosstab`** — weighted % distribution of a nominal
  categorical variable by demographic.

### Trends
- **`get_platform_trends`** — binary platform-adoption rate over time,
  optionally filtered to a demographic group.
- **`get_freq_trends`** — mean usage frequency over time.
- **`get_platform_posting_summary`** — adoption, frequency, trust, and
  political posting for one platform in a single call.

### Modeling
- **`run_ols_regression`** — survey-weighted OLS for continuous/ordinal
  outcomes, with custom reference categories.
- **`run_logistic_regression`** — survey-weighted logistic regression for
  binary outcomes.

### Reporting
- **`generate_pdf_report`** — publication-quality PDF: title page, abstract,
  auto-generated methodology section, numbered tables and Pew-style charts.
  Runs as an async job.
- **`get_report_status`** — poll a `generate_pdf_report` job for its
  download URL.

## Connecting from Claude

This server uses Google OAuth and streamable HTTP — Claude handles the
sign-in flow automatically.

1. In Claude, go to **Settings → Connectors → Add custom connector**.
2. Enter the service URL:
   ```
   https://social-media-demographics-mcp-dnbn5uv2jq-uc.a.run.app/mcp
   ```
3. Sign in with your Google account when prompted. If you're not authorized,
   request access at the auth screen.

If you're not authorized yet, request access — see the public docs at
`docs/` for end-user setup instructions and example queries.

## Privacy & Security

- **Cell suppression**: counts below 10 are suppressed at the SQL layer and
  again before being returned.
- **OAuth authentication**: Google OAuth via Claude Connectors — no API keys
  to manage.
- **No PII**: only aggregated, weighted estimates are exposed; PHQ-9 and
  other sensitive items are returned as population-level aggregates only.

## Development

### Local Testing

```bash
cd remote-mcp
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
./test_local.sh   # runs the server on localhost:8080
```

`test_regression.py` covers the OLS/logistic regression helpers — run with
`pytest` before changing those code paths.

### Project Structure

```
remote-mcp/
├── server.py           # MCP server: tools, BigQuery queries, PDF report builder
├── Dockerfile          # Container configuration
├── requirements.txt    # Python dependencies
├── deploy.sh           # Manual Cloud Run deployment (CI also deploys on push to main)
├── load_data.sh        # Load/refresh the BigQuery dataset
├── sql/                # BigQuery schema
└── chip50.png          # Logo, embedded in PDF reports
```

### Deploying

Deploys to Cloud Run happen automatically via GitHub Actions on push to
`main`. For a one-off manual deploy:

```bash
export GOOGLE_CLIENT_ID=...
export GOOGLE_CLIENT_SECRET=...
./deploy.sh
```

To refresh the BigQuery dataset from a new CSV export, run `./load_data.sh`.

### Logs

```bash
gcloud run logs read social-media-demographics-mcp --region us-central1
```

## License

MIT License — see LICENSE file for details.
