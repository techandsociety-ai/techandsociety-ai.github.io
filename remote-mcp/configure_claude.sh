#!/bin/bash
# configure_claude.sh
# Writes the MCP server URL into Claude Desktop's config.
# With OAuth, no API key is needed — mcp-remote handles the Google login flow.
#
# Usage:
#   bash configure_claude.sh                  # auto-fetch URL from Cloud Run
#   bash configure_claude.sh <SERVICE_URL>    # provide URL directly

set -e

GCP_PROJECT="${GCP_PROJECT:-chip50}"
SERVICE_NAME="social-media-demographics-mcp"
REGION="${REGION:-us-central1}"
CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
MCP_SERVER_KEY="social-media-demographics"

# ── Resolve service URL ────────────────────────────────────────────────────

if [ -n "$1" ]; then
    SERVICE_URL="$1"
    echo "Using provided URL: $SERVICE_URL"
else
    echo "Fetching service URL from Cloud Run..."
    if ! command -v gcloud &> /dev/null; then
        echo "Error: gcloud is not installed. Pass the URL as an argument:"
        echo "  bash configure_claude.sh <SERVICE_URL>"
        exit 1
    fi

    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --platform managed \
        --region "$REGION" \
        --project "$GCP_PROJECT" \
        --format 'value(status.url)' 2>/dev/null)

    if [ -z "$SERVICE_URL" ]; then
        echo "Error: Could not fetch service URL. Is the service deployed?"
        exit 1
    fi
fi

echo "  MCP endpoint: $SERVICE_URL/mcp"

# ── Back up existing config ────────────────────────────────────────────────

BACKUP="${CLAUDE_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
if [ -f "$CLAUDE_CONFIG" ]; then
    cp "$CLAUDE_CONFIG" "$BACKUP"
    echo "Backed up existing config → $BACKUP"
fi

# ── Update config via Python ───────────────────────────────────────────────

python3 - <<PYEOF
import json, os

config_path = os.path.expanduser("$CLAUDE_CONFIG")
service_url = "$SERVICE_URL"
server_key  = "$MCP_SERVER_KEY"

if os.path.exists(config_path):
    with open(config_path) as f:
        config = json.load(f)
else:
    config = {}

config.setdefault("mcpServers", {})

# OAuth flow is handled automatically by mcp-remote — no key needed
config["mcpServers"][server_key] = {
    "command": "npx",
    "args": ["mcp-remote", f"{service_url}/mcp"]
}

with open(config_path, "w") as f:
    json.dump(config, f, indent=2)

print(f"Config updated: {config_path}")
print(json.dumps(config["mcpServers"][server_key], indent=2))
PYEOF

# ── Restart Claude Desktop ─────────────────────────────────────────────────

echo ""
if pgrep -x "Claude" > /dev/null; then
    echo "Restarting Claude Desktop..."
    pkill -x "Claude" && sleep 2
    open -a Claude
    echo "Claude Desktop restarted."
else
    echo "Claude Desktop is not running — start it to pick up the new config."
fi

echo ""
echo "Done. MCP server '$MCP_SERVER_KEY' configured."
echo "First connection will open a browser window for Google login."
