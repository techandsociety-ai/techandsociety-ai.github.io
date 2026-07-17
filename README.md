# techandsociety.ai — website

The public website for **Tech & Society**, served via GitHub Pages at
[techandsociety.ai](https://techandsociety.ai).

The site is a small set of self-contained, static HTML pages: a landing page,
an MCP information page, and a handful of published research reports built from
the CHIP50 panel survey.

> Looking for the MCP server itself (the tools, BigQuery queries, and Cloud Run
> deployment)? That lives in a separate repo:
> **[techandsociety-ai/mcp-server](https://github.com/techandsociety-ai/mcp-server)**.
> This repo is only the website.

## What gets deployed

**Only the `docs/` directory is published.** GitHub Pages serves it as-is (no
Jekyll theme — see `docs/_config.yml`), and `docs/CNAME` binds it to the
`techandsociety.ai` custom domain.

```
docs/                         ← the deployed site (and nothing outside it)
├── index.html                Landing page
├── mcp.html                  MCP information / access page
├── report-america-meets-ai.html
├── report-depression.html
├── report-depression-heatmap.html
├── report-social-media-trust.html
├── report-who-posts-politics.html
├── chip50.png                Logo
├── _config.yml               Pages config (serve HTML as-is, no theme)
├── CNAME                     Custom domain: techandsociety.ai
└── AGENTS.md                 Notes for agents working on the site
```

Anything outside `docs/` (this README, `MIGRATION_PLAN.md`, etc.) is repo
support and is **not** part of the published site.

> **Editing note:** `website/index.html` is an earlier, unpublished draft of the
> landing page. It is not deployed — edit the copies in `docs/`, which are the
> source of truth for the live site.

## How it deploys

`.github/workflows/pages.yml` builds and publishes the site. It runs on:

- a push to `main` that touches `docs/**`, or
- a manual `workflow_dispatch` run.

The workflow uploads `docs/` as the Pages artifact and deploys it. Because the
trigger is scoped to `docs/**`, changes to repo-support files (like this README)
don't redeploy the site.

## Working on the site locally

The pages are plain static HTML with no build step. To preview:

```bash
cd docs
python3 -m http.server 8000
# open http://localhost:8000
```

Then edit the relevant `.html` file and reload.

## Deploying a change

1. Edit files under `docs/`.
2. Commit and open a PR against `main`.
3. On merge, `pages.yml` publishes automatically — the live site updates within
   a minute or so.
