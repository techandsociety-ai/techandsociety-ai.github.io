#!/usr/bin/env bash
# CHIP50 MCP Installer
# Adds the CHIP50 social media demographics connector to Claude Desktop.
#
# Usage:
#   bash install.sh
#
# Supported: macOS, Linux, Windows (via Git Bash or WSL)

set -e

MCP_SERVER_KEY="chip50-social-media-demographics"
MCP_ENDPOINT="https://social-media-demographics-mcp-dnbn5uv2jq-uc.a.run.app/mcp"

# ── Detect OS and config path ─────────────────────────────────────────────────

detect_config_path() {
    case "$(uname -s)" in
        Darwin)
            echo "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
            ;;
        Linux)
            echo "$HOME/.config/Claude/claude_desktop_config.json"
            ;;
        MINGW*|MSYS*|CYGWIN*)
            # Git Bash / WSL on Windows
            echo "$APPDATA/Claude/claude_desktop_config.json"
            ;;
        *)
            echo ""
            ;;
    esac
}

CLAUDE_CONFIG="$(detect_config_path)"

if [ -z "$CLAUDE_CONFIG" ]; then
    echo "Unsupported OS: $(uname -s)"
    echo "Manually add the following to your Claude Desktop config:"
    echo ""
    echo "  \"$MCP_SERVER_KEY\": {"
    echo "    \"command\": \"npx\","
    echo "    \"args\": [\"mcp-remote\", \"$MCP_ENDPOINT\"]"
    echo "  }"
    exit 1
fi

echo "CHIP50 MCP Installer"
echo "OS     : $(uname -s)"
echo "Config : $CLAUDE_CONFIG"
echo ""

# ── Check npx is available ────────────────────────────────────────────────────

if ! command -v npx &> /dev/null; then
    echo "npx is required but not installed."
    echo ""
    echo "Install Node.js from https://nodejs.org (LTS version), then re-run this script."
    exit 1
fi

# ── Back up existing config ───────────────────────────────────────────────────

mkdir -p "$(dirname "$CLAUDE_CONFIG")"

if [ -f "$CLAUDE_CONFIG" ]; then
    BACKUP="${CLAUDE_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$CLAUDE_CONFIG" "$BACKUP"
    echo "Backed up config → $(basename "$BACKUP")"
fi

# ── Update config ─────────────────────────────────────────────────────────────

python3 - <<PYEOF
import json, os, sys

config_path = """$CLAUDE_CONFIG"""
server_key  = "$MCP_SERVER_KEY"
endpoint    = "$MCP_ENDPOINT"

try:
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {}

    config.setdefault("mcpServers", {})
    config["mcpServers"][server_key] = {
        "command": "npx",
        "args": ["mcp-remote", endpoint]
    }

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"Added '{server_key}' to mcpServers.")

except Exception as e:
    print(f"Failed to update config: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF

# ── Restart Claude Desktop ────────────────────────────────────────────────────

restart_claude() {
    case "$(uname -s)" in
        Darwin)
            if pgrep -x "Claude" > /dev/null 2>&1; then
                pkill -x "Claude" && sleep 2
                open -a Claude
                echo "Claude Desktop restarted."
            else
                open -a Claude 2>/dev/null || true
                echo "Claude Desktop launched."
            fi
            ;;
        Linux)
            if pgrep -x "claude" > /dev/null 2>&1; then
                pkill -x "claude" && sleep 2
            fi
            nohup claude > /dev/null 2>&1 &
            echo "Claude Desktop restarted."
            ;;
        MINGW*|MSYS*|CYGWIN*)
            taskkill //IM Claude.exe //F > /dev/null 2>&1 || true
            sleep 2
            start Claude 2>/dev/null || true
            echo "Claude Desktop restarted."
            ;;
    esac
}

echo ""
restart_claude

echo ""
echo "Done! CHIP50 tools will appear in Claude Desktop after restart."
echo ""
echo "First use will open a browser window for Google login."
echo "After that, no login is needed."
