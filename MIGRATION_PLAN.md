# Tech and Society — Migration Plan

**Goal:** Move the CHIP50 MCP project from its current home (Nanocentury AI / GCP project `chip50`) to a new public-facing organization under the `techandsociety.ai` brand, with a website showcasing the work.

**Current state:**
- Repo: private, under Nanocentury AI GitHub org
- GCP project: `chip50` (Cloud Run + BigQuery)
- Cloud Run URL: `https://social-media-demographics-mcp-dnbn5uv2jq-uc.a.run.app/mcp`
- Docs site: `docs/` folder served via GitHub Pages

---

## Phase 1 — GitHub Org Setup
**Status: Ready to start**

- [ ] Create GitHub org `tech-and-society` (check availability; fallback: `tech-and-society-lab` or `techandsociety`)
- [ ] Set org profile: description ("Tech and Society Research Lab"), link to `techandsociety.ai`, avatar/logo (blocked on Jason's deck — placeholder ok for now)
- [ ] Configure org settings: visibility defaults (public), member roles, billing plan (Team or free-tier)
- [ ] Create initial teams: `admins`, `contributors`, `external-collaborators`
- [ ] Add initial members with roles (Stefan = owner)
- [ ] Set up default branch protection for new repos: require PR reviews, require status checks, disallow force-push to `main`

**Notes:** GitHub org slug must be all-lowercase, no spaces. `tech-and-society` is the closest clean match.

---

## Phase 2 — Domain & Website Infra
**Status: Ready (if DNS access confirmed)**

- [ ] Confirm DNS access for `techandsociety.ai` (who controls the registrar?)
- [ ] Decide hosting: **Recommendation = Vercel** (free tier, easy custom domain, supports password protection via Edge Middleware or Vercel Password Protection add-on)
  - Alternative: GitHub Pages (free, simpler, but no native password protection)
  - Alternative: Netlify (similar to Vercel)
- [ ] Once hosting chosen, point DNS: add CNAME/A records for `techandsociety.ai` → hosting provider
- [ ] Set up HTTPS (automatic with Vercel/Netlify/Pages)

**Decision needed:** Who holds the DNS for `techandsociety.ai`? And is password protection a hard requirement or nice-to-have?

---

## Phase 3 — Migrate MCP Code
**Status: Ready to start**

Steps (in order):

1. [ ] Create repo `chip50-mcp` under the new `tech-and-society` org (public repo, MIT license)
2. [ ] Mirror git history from this repo's `remote-mcp/` subfolder using `git filter-repo --subdirectory-filter remote-mcp` into a clean new repo (preserves full commit history)
3. [ ] Update hardcoded references in the migrated repo:
   - GCP project ID: `chip50` → new project ID (set in Phase 4)
   - Cloud Run service name and region (if changed)
   - GitHub Actions workflow: update `GCP_PROJECT`, `WIF_PROVIDER`, `SERVICE_ACCOUNT` secrets
   - README: update Cloud Run URL once redeployed
4. [ ] Add to new repo: `LICENSE` (MIT), `CONTRIBUTING.md`, attribution note (Doris Duke Foundation support) in README
5. [ ] Re-register new MCP endpoint URL with Claude Connectors once Cloud Run is redeployed
6. [ ] Share new connector URL with authorized users
7. [ ] End-to-end test: crosstab, marginal, regression, PDF report

**Blocked on:** Phase 4 (need new GCP project ID before updating config)

---

## Phase 4 — Data Migration (BigQuery / GCP)
**Status: Ready to start (requires Google org creation)**

1. [ ] Create new Google Cloud org under `techandsociety.ai` domain (requires Google Workspace or Cloud Identity on that domain)
2. [ ] Create GCP project: `tech-and-society` (or `tas-chip50` — project ID must be globally unique)
3. [ ] Enable billing account; attach to new project
4. [ ] Set up IAM: owner (Stefan), CI service account for Cloud Run deploy, viewer role for collaborators
5. [ ] Enable APIs: BigQuery, Cloud Run, Cloud Build, Artifact Registry, IAM, Secret Manager
6. [ ] Copy BigQuery dataset from `chip50` project to new project:
   ```bash
   bq cp chip50:chip50_data.survey_data tas-chip50:chip50_data.survey_data
   ```
   Or for full dataset:
   ```bash
   bq mk --transfer_config ...  # use BQ Data Transfer Service for cross-project copy
   ```
7. [ ] Validate: row counts and spot-check 3–5 queries match between old and new project
8. [ ] Update MCP server `BQ_PROJECT` env var in Cloud Run to point to new project
9. [ ] Archive old `chip50` GCP project (do not delete — keep for 90 days as rollback)

**Prereq:** Google org creation requires DNS verification on `techandsociety.ai` — do Phase 2 DNS first.

---

## Phase 5 — Website
**Status: BLOCKED on Jason's deck (logo + color palette)**

Once unblocked:

1. [ ] Scaffold site framework (Recommendation: **Astro** — static by default, fast, easy to deploy to Vercel/Pages; or plain HTML if minimal)
2. [ ] Build landing page for `techandsociety.ai`:
   - Hero: project name, mission statement
   - CHIP50 section: what it is, who it's for, how to request access
   - Team section
   - Doris Duke Foundation acknowledgment
3. [ ] Password protection: implement via Vercel's built-in password protection (Pro plan) or a simple Netlify Identity gate
4. [ ] Wire up deployment: GitHub Actions → Vercel/Netlify on push to `main`

**Blocked on:** Logo, color palette, typography from Jason's slide deck.

---

## Phase 6 — Demo Video
**Status: BLOCKED on Jason's deck (branding/intro slides)**

Once unblocked:

1. [ ] Script a 5–8 min workflow walkthrough:
   - Connect MCP in Claude
   - `introduce_mcp` → explore the dataset
   - Pull a crosstab (e.g., platform use by party ID)
   - Run a logistic regression
   - Generate a PDF report
2. [ ] Record screen capture (QuickTime or Loom)
3. [ ] Edit with branded intro/outro slides (from Jason's deck)
4. [ ] Publish: embed on `techandsociety.ai` and link from `chip50-mcp` repo README

---

## Dependency Map

```
Phase 2 (DNS) ──────────────────────────────> Phase 4 (GCP org creation requires DNS verification)
                                                    │
Phase 1 (GitHub org) ──> Phase 3 (repo migrate) ──> Phase 4 (update BQ config)
                                                    │
Jason's deck ──────────────────────────────> Phase 5 (website) ──> Phase 6 (video)
```

**Can start immediately (no blockers):** Phase 1, Phase 3 (steps 1–4 only)
**Unblock next:** DNS verification (Phase 2) → GCP org (Phase 4)
**Waiting on external:** Jason's deck (Phases 5 and 6)

---

## Open Questions / Decisions Needed

| # | Question | Who decides | Notes |
|---|----------|-------------|-------|
| 1 | GitHub org slug: `tech-and-society` or something else? | Stefan | Check availability first |
| 2 | Hosting for website: Vercel vs GitHub Pages vs Netlify? | Stefan | Vercel recommended for password protection |
| 3 | Is password protection a hard requirement for the site? | Stefan | Changes hosting choice |
| 4 | Who controls DNS for `techandsociety.ai`? | Stefan/Jason | Needed for GCP org creation |
| 5 | New GCP project ID (globally unique string) | Stefan | Suggestion: `tech-and-society-lab` |
| 6 | Keep old `chip50` GCP project how long after migration? | Stefan | Recommend 90-day archive period |
| 7 | Who else gets added as GitHub org members at launch? | Stefan/Jason | |
