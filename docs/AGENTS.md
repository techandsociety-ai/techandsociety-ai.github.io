# AGENTS.md — CHIP50 MCP Docs

## What this repo is

A static GitHub Pages documentation site for the CHIP50 Social Media Survey MCP server. It lives at `https://nanocentury-ai.github.io/CHIP50-MCP-Docs/` and is a single self-contained file: `docs/index.html`.

The MCP server itself lives in a separate private repo (`nanocentury-ai/DDFchip50`, path `remote-mcp/`). This repo is only the public-facing docs.

## The MCP server

- **Live URL**: `https://social-media-demographics-mcp-dnbn5uv2jq-uc.a.run.app/mcp`
- **Transport**: Remote MCP over HTTPS (not stdio)
- **Auth**: Google OAuth — users connect via Settings → Connectors → Add custom connector in Claude
- **Backend**: Google Cloud Run + BigQuery (`chip50` GCP project, dataset `social_media_demographics`)

## What the MCP server does

Provides AI-accessible tools for analyzing the CHIP50 panel survey — ~10K respondents/wave, 38+ waves, 232 variables covering 20 social media platforms, 9 demographic variables, PHQ-9 mental health items, and political attitudes. All queries return population-weighted estimates with cell suppression (n < 10).

24 tools: `introduce_mcp`, `get_available_variables`, `get_question_wording`, `get_wave_metadata`, `generate_marginals`, `generate_marginals_by_wave`, `generate_marginals_batch`, `generate_crosstab`, `generate_crosstab_by_wave`, `generate_crosstab_filtered`, `generate_crosstab_batch`, `generate_crosstab_multi`, `summarize_pattern_by_wave`, `get_platform_trends`, `get_freq_trends`, `get_ordinal_distribution`, `get_ordinal_distribution_by_demographic`, `get_ordinal_crosstab`, `get_categorical_crosstab`, `get_platform_posting_summary`, `run_ols_regression`, `run_logistic_regression`, `generate_pdf_report`, `get_report_status`.

## Docs site design

- **Single file**: everything is in `index.html` — no build step, no framework, no dependencies except Google Fonts
- **Fonts**: Montserrat (headings), Barlow (body), Barlow Condensed (labels/tags) — matches chip50.org
- **Colors**: Navy `#1c3461` primary, `#2d5fa6` accent blue, white/off-white backgrounds — matches chip50.org
- **Style target**: looks like it belongs to the chip50.org family but is clearly a docs page, not a knock-off of the main site
- **Logo**: `chip50.png` — navy US map with checkmark icon

## Deployment

Push to `main` → GitHub Pages auto-deploys (no workflow needed, Pages is configured to serve from root of `main`). Changes are live within ~30 seconds.

```bash
cd docs/
git add -A && git commit -m "..." && git push
```

## What's on the page

1. **Hero** — tagline, key stats (38+ waves, ~10K respondents, 20 platforms, 232 variables, 24 tools)
2. **Overview** — plain-English explanation of CHIP50 + how the MCP works (4-step flow)
3. **Data** — coverage cards: platforms, demographics, mental health, political attitudes, waves, privacy
4. **Sample Queries** — tabbed section with Quick / Medium / Complex query examples with prompts and expected outputs
5. **Tools Reference** — all 18 MCP tools with plain-English descriptions
6. **Setup** — 4-step end-user connection guide (Settings → Connectors → Add custom connector)

## Key decisions / things to preserve

- The setup section is oriented toward **end users connecting to the existing server**, not self-hosting. Do not revert it to deployment instructions.
- The server URL in the setup section is the live production URL — do not treat it as a placeholder.
- Access to the server is managed (Google OAuth). Users who aren't authorized should request access at the auth screen.
- A JS password gate is implemented — the password is stored as a SHA-256 hash checked client-side, with the session stored in `sessionStorage`.
