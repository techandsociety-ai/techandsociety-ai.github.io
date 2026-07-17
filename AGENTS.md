# AGENTS.md — techandsociety.ai website

Repo-wide guidance for people and agents working in this repository. For what
the site is and how it deploys, see [`README.md`](README.md). For the docs
pages' own visual-design conventions, see [`docs/AGENTS.md`](docs/AGENTS.md).

## What this repo is (in one line)

The GitHub Pages website for **techandsociety.ai**. Only `docs/` is deployed
(via `.github/workflows/pages.yml`); everything else is repo support. The MCP
server lives separately in
[`techandsociety-ai/mcp-server`](https://github.com/techandsociety-ai/mcp-server).

## Branch & PR scoping

Scope work one concern at a time:

- **Each branch/PR maps to a single ticket**, or a small bundle of closely
  related tickets that share **one theme**.
- **Keep PRs tightly scoped** — touch only what the change needs. Orthogonal or
  unrelated work gets its own branch/PR, even when you spot it mid-change; open
  a ticket for it instead of folding it in.
- **When in doubt, split.** A reviewer should be able to hold the whole change
  in their head and name the single thing it does.

Examples from this repo:

- **A themed bundle is fine.** PR #9 combined a README rewrite, several file
  deletions, and a `.gitignore` trim — one theme: *remove the leftover
  MCP-server files and make this a website-only repo*.
- **Split out orthogonal work.** The Python live-reload dev server (#10) and the
  stale-link fix (#13) were deliberately kept **out** of #9 — a new dev feature
  and a live-site content change are separate concerns from a file cleanup, so
  each got its own branch, ticket, and PR.

A quick tell: if the PR title needs an "and" joining unrelated things, it's
probably two PRs.

## Local development

The site is static — no build step. For a live-reloading preview, use the
bundled dev server with [uv](https://docs.astral.sh/uv/) (details in
[`README.md`](README.md#working-on-the-site-locally)):

```bash
uv run serve.py         # serves docs/ at http://localhost:8000, reloads on edit
```

`serve.py` declares its `livereload` dependency inline (PEP 723), so `uv run`
handles it — no venv or install step. Zero-dependency fallback:
`cd docs && python3 -m http.server 8000`.

## Deploying

Merging a change that touches `docs/**` triggers `pages.yml`, which publishes
`docs/` to GitHub Pages (custom domain `techandsociety.ai`). Changes to
repo-support files (this file, `README.md`, `serve.py`, …) don't redeploy the
site.
