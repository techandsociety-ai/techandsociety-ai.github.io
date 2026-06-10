# Quick Start — Connect to the CHIP50 Research MCP

The CHIP50 MCP server is already deployed and running on Google Cloud Run.
Most users just need to connect Claude to it — no deployment, gcloud, or API
keys required.

## 1. Add the Connector

In Claude:

1. Go to **Settings → Connectors → Add custom connector**.
2. Enter the service URL:
   ```
   https://social-media-demographics-mcp-dnbn5uv2jq-uc.a.run.app/mcp
   ```
3. Sign in with your Google account when prompted.

If your account isn't authorized yet, request access at the auth screen and
ping the CHIP50 team.

## 2. Verify It Works

Ask Claude:

```
Call introduce_mcp and tell me what's in the CHIP50 dataset.
```

You should see the dataset schema (demographics, platforms, attitudinal
scales, wave coverage) and a list of available tools.

## 3. Try a Few Queries

### A single percentage
```
What share of Republicans say they trust Twitter/X "a great deal" or "a lot"?
```

### A demographic breakdown
```
Show me TikTok adoption by age group.
```

### A trend across waves
```
How has trust in Facebook changed across waves, broken down by party?
```

### A controlled comparison
```
Does TikTok use predict more conspiracy belief, after controlling for age,
education, and party?
```

### A full report
```
Build a short report on how Gen Z and Boomers differ in social media trust,
with charts, a methodology section, and the underlying tool calls listed at
the end.
```

## What's Next

- See [`AGENTS.md`](AGENTS.md) for the analytical conventions and report
  standards this server is built around — useful context if you're asking
  Claude to produce a report.
- See [`README.md`](README.md) for the full tool list and dataset coverage.
- If you're developing or self-hosting this server, see
  [`README.md`](README.md#development) and `SETUP.md`.
