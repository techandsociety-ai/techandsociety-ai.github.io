# CHIP50 Research MCP

A remote [Model Context Protocol](https://modelcontextprotocol.io/) server that gives Claude direct, privacy-protected access to the CHIP50 panel survey — enabling natural-language research queries against 38+ waves of nationally representative data on social media use, political attitudes, and mental health.

## What It Is

CHIP50 is a large-scale, nationally representative repeated-wave survey tracking how Americans use social media and how that connects to political attitudes and mental health. Each wave includes ~10,000 respondents with survey weights calibrated to match the U.S. adult population.

This MCP server lets an analyst (or an AI assistant) query that data in plain English instead of writing SQL or running statistical software. Claude selects the appropriate analysis tools, runs population-weighted queries against the CHIP50 BigQuery database, and returns tables, trend analyses, regression output, and publication-quality PDF reports.

## Quick Start

The server is already deployed. To connect:

1. In Claude, go to **Settings → Connectors → Add custom connector**
2. Enter the server URL:
   ```
   https://social-media-demographics-mcp-dnbn5uv2jq-uc.a.run.app/mcp
   ```
3. Sign in with your Google account when prompted. Request access if your account isn't yet authorized.

Then ask Claude anything about the data:

```
Call introduce_mcp and tell me what's in the CHIP50 dataset.
```

See [`remote-mcp/QUICKSTART.md`](remote-mcp/QUICKSTART.md) for more example queries.

## What's in the Dataset

- **20 social media platforms**: Facebook, Instagram, X/Twitter, TikTok, YouTube, Snapchat, LinkedIn, Reddit, WhatsApp, Pinterest, Messenger, Tumblr, Truth Social, Gab, Parler, Mastodon, Bluesky, Threads, 4chan, and more
- **Usage, frequency, trust, and political posting** per platform
- **Core demographics**: age, gender, race/ethnicity, education, income, party ID (3- and 7-category), urbanicity, state
- **Political attitudes**: ideology, institutional trust, voting behavior, conspiracy beliefs, political information
- **PHQ-9 mental health screening**: all 9 items, returned as population-level aggregates only
- **38+ waves**, 2020–present, ~10K respondents per wave, survey-weighted

## Tools (24)

| Category | Tools |
|----------|-------|
| Discovery | `introduce_mcp`, `get_available_variables`, `get_question_wording`, `get_wave_metadata` |
| Distributions | `generate_marginals`, `generate_marginals_batch`, `generate_marginals_by_wave`, `get_ordinal_distribution`, `get_ordinal_distribution_by_demographic` |
| Crosstabs | `generate_crosstab`, `generate_crosstab_filtered`, `generate_crosstab_batch`, `generate_crosstab_by_wave`, `generate_crosstab_multi`, `get_ordinal_crosstab`, `get_categorical_crosstab` |
| Trends | `get_platform_trends`, `get_freq_trends`, `get_platform_posting_summary`, `summarize_pattern_by_wave` |
| Modeling | `run_ols_regression`, `run_logistic_regression` |
| Reporting | `generate_pdf_report`, `get_report_status` |

Call `introduce_mcp()` first — it returns the full schema, all tool descriptions, and wave-coverage caveats.

## Privacy & Security

- **Cell suppression**: counts below 10 are suppressed at the SQL layer and again in Python before returning
- **OAuth authentication**: Google OAuth via Claude Connectors — no API keys
- **No PII**: only aggregated, survey-weighted estimates are returned; PHQ-9 and other sensitive items are population-level aggregates only

## Repository Layout

```
remote-mcp/         MCP server (deployed to Google Cloud Run)
├── server.py       All 24 tools + BigQuery queries + PDF report builder
├── Dockerfile      Container configuration
├── deploy.sh       Manual deploy fallback (CI deploys automatically on push to main)
├── load_data.sh    Load/refresh the BigQuery dataset from a new CSV export
├── sql/            BigQuery schema
├── QUICKSTART.md   End-user connection guide
├── README.md       Full tool list and dataset documentation
└── AGENTS.md       Analytical conventions, report standards, roadmap

docs/               Public documentation site (GitHub Pages)
└── index.html      Single-file docs page at chip50.org/CHIP50-MCP-Docs

gold_standard_reports/   Reference .docx reports for MCP validation
```

## Development

```bash
cd remote-mcp
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
./test_local.sh          # run server on localhost:8080
pytest test_regression.py   # regression helper unit tests
```

Deployment to Cloud Run happens automatically via GitHub Actions on push to `main`. See [`remote-mcp/README.md`](remote-mcp/README.md#development) for details.

## License

MIT License — see `remote-mcp/` directory.
