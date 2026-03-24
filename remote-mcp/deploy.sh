#!/bin/bash
set -e

source ../.env

# CHIP50 Social Media Demographics MCP - Manual Deployment Script
# Deploys the remote MCP server to Google Cloud Run.
# NOTE: Deployment also runs automatically via GitHub Actions on push to main.
# Use this script for one-off manual deploys only.
# To load/refresh BigQuery data, run load_data.sh instead.

GCP_PROJECT="chip50"

echo "==================================="
echo "CHIP50 Social Media Demographics MCP"
echo "Cloud Run Deployment Script"
echo "==================================="
echo ""

# Check required tools
for cmd in gcloud bq; do
    if ! command -v $cmd &> /dev/null; then
        echo "Error: $cmd CLI is not installed."
        exit 1
    fi
done

if [ -z "$GCP_PROJECT" ]; then
    echo "Enter your Google Cloud Project ID:"
    read -r GCP_PROJECT
fi

echo "Using project: $GCP_PROJECT"
gcloud config set project "$GCP_PROJECT"

# Configuration
SERVICE_NAME="social-media-demographics-mcp"
REGION="${REGION:-us-central1}"
DATASET_NAME="social_media_demographics"

echo ""
echo "Configuration:"
echo "  Service:  $SERVICE_NAME"
echo "  Region:   $REGION"
echo "  Dataset:  $DATASET_NAME"
echo ""

# Check required Google OAuth credentials
if [ -z "$GOOGLE_CLIENT_ID" ] || [ -z "$GOOGLE_CLIENT_SECRET" ]; then
    echo "Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set."
    echo ""
    echo "Get these from Google Cloud Console:"
    echo "  1. Go to APIs & Services → Credentials"
    echo "  2. Create OAuth 2.0 Client ID (Web application)"
    echo "  3. Export before running this script:"
    echo "     export GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com"
    echo "     export GOOGLE_CLIENT_SECRET=your-secret"
    echo ""
    exit 1
fi

# Step 1: Enable required APIs
echo "Step 1/4: Enabling required Google Cloud APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    bigquery.googleapis.com \
    --project="$GCP_PROJECT"
echo "APIs enabled."
echo ""

# Step 2: Build container
echo "Step 2/4: Building container image..."
gcloud builds submit \
    --tag "gcr.io/$GCP_PROJECT/$SERVICE_NAME" \
    --project="$GCP_PROJECT" \
    .
echo "Container built."
echo ""

# Step 3: Deploy to Cloud Run
echo "Step 3/4: Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --image "gcr.io/$GCP_PROJECT/$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --set-env-vars "GCP_PROJECT=$GCP_PROJECT,DATASET_NAME=$DATASET_NAME,MIN_CELL_SIZE=30,GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET=$GOOGLE_CLIENT_SECRET" \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 1 \
    --project="$GCP_PROJECT"
echo "Deployment complete."
echo ""

# Get service URL and update SERVICE_URL env var so OAuth redirects work
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --project="$GCP_PROJECT" \
    --format 'value(status.url)')

echo "Setting SERVICE_URL=$SERVICE_URL on the service..."
gcloud run services update "$SERVICE_NAME" \
    --region "$REGION" \
    --project="$GCP_PROJECT" \
    --update-env-vars "SERVICE_URL=$SERVICE_URL"

echo "==================================="
echo "Deployment Complete!"
echo "==================================="
echo ""
echo "Service URL: $SERVICE_URL"
echo ""
echo "IMPORTANT — Add this redirect URI to your Google OAuth app:"
echo "  $SERVICE_URL/auth/callback"
echo "(APIs & Services → Credentials → your OAuth client → Authorized redirect URIs)"
echo ""

# Step 4: Auto-configure Claude Desktop
echo "Step 4/4: Configuring Claude Desktop..."
bash "$(dirname "$0")/configure_claude.sh" "$SERVICE_URL"

echo ""
echo "Test (browser will prompt Google login):"
echo "  open $SERVICE_URL/mcp"
echo ""
echo "Logs:"
echo "  gcloud run logs read $SERVICE_NAME --region $REGION --project $GCP_PROJECT"
echo ""
