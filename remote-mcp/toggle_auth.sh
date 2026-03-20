#!/usr/bin/env bash
# toggle_auth.sh — Enable or disable Google OAuth on the Cloud Run MCP server.
#
# Usage:
#   bash toggle_auth.sh off   # disable auth (anyone with URL can connect)
#   bash toggle_auth.sh on    # re-enable auth (Google login required)
#   bash toggle_auth.sh       # show current state

set -e

SERVICE_NAME="social-media-demographics-mcp"
REGION="${REGION:-us-central1}"
GCP_PROJECT="${GCP_PROJECT:-chip50}"

# ── Current state ─────────────────────────────────────────────────────────────

current_state() {
    local val
    val=$(gcloud run services describe "$SERVICE_NAME" \
        --region "$REGION" \
        --project "$GCP_PROJECT" \
        --format "value(spec.template.spec.containers[0].env[DISABLE_AUTH].value)" \
        2>/dev/null)
    if [ "$val" = "true" ]; then
        echo "off (auth disabled — no login required)"
    else
        echo "on (auth enabled — Google login required)"
    fi
}

# ── Toggle ────────────────────────────────────────────────────────────────────

case "${1:-status}" in
    off)
        echo "Disabling auth on $SERVICE_NAME..."
        gcloud run services update "$SERVICE_NAME" \
            --region "$REGION" \
            --project "$GCP_PROJECT" \
            --update-env-vars DISABLE_AUTH=true
        echo ""
        echo "Auth is OFF. Anyone with the URL can connect — turn it back on when done testing:"
        echo "  bash toggle_auth.sh on"
        ;;
    on)
        echo "Enabling auth on $SERVICE_NAME..."
        gcloud run services update "$SERVICE_NAME" \
            --region "$REGION" \
            --project "$GCP_PROJECT" \
            --remove-env-vars DISABLE_AUTH
        echo ""
        echo "Auth is ON. Google login required."
        ;;
    status)
        echo "Auth is currently: $(current_state)"
        ;;
    *)
        echo "Usage: bash toggle_auth.sh [on|off|status]"
        exit 1
        ;;
esac
