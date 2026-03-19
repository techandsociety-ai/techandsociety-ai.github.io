#!/bin/bash
set -e

source ../.env

# CHIP50 Social Media Demographics MCP - Deployment Script
# Deploys the remote MCP server to Google Cloud Run
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
DATA_FILE="../data/CHIP50_social_media_usage_posting_waves14-35_1-Aug.csv"
RAW_TABLE="${DATASET_NAME}.panel_data"

echo ""
echo "Configuration:"
echo "  Service:  $SERVICE_NAME"
echo "  Region:   $REGION"
echo "  Dataset:  $DATASET_NAME"
echo "  Data:     $DATA_FILE"
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
echo "Step 1/5: Enabling required Google Cloud APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    bigquery.googleapis.com \
    --project="$GCP_PROJECT"
echo "APIs enabled."
echo ""

# Step 2: Load real panel data into BigQuery
echo "Step 2/5: Loading panel data into BigQuery..."

# Check data file exists
if [ ! -f "$DATA_FILE" ]; then
    echo "Error: Data file not found at $DATA_FILE"
    echo "Expected: CHIP50_social_media_usage_posting_waves14-35_1-Aug.csv in the data/ folder"
    exit 1
fi

# Create dataset if needed
if ! bq show --project_id="$GCP_PROJECT" "$DATASET_NAME" &> /dev/null; then
    echo "Creating dataset $DATASET_NAME..."
    bq mk --project_id="$GCP_PROJECT" --dataset --location=US "$DATASET_NAME"
else
    echo "Dataset $DATASET_NAME already exists."
fi

# Load CSV into raw panel_data table (overwrite if exists)
echo "Loading CSV into $RAW_TABLE (this may take a minute)..."
bq load \
    --project_id="$GCP_PROJECT" \
    --source_format=CSV \
    --skip_leading_rows=1 \
    --replace \
    --autodetect \
    "$RAW_TABLE" \
    "$DATA_FILE" \
    "id:STRING,wave:STRING,state:STRING,age_cat_8:STRING,education_cat:STRING,income_cat_10:STRING,race_cat_5:STRING,gender:STRING,party3:STRING,party7:STRING,urban_type:STRING,race:STRING,state_code:STRING,use_gab:STRING,use_facebook:STRING,use_instagram:STRING,use_linkedin:STRING,use_pinterest:STRING,use_reddit:STRING,use_tumblr:STRING,use_tiktok:STRING,use_twitter:STRING,use_youtube:STRING,use_whatsapp:STRING,use_4chan:STRING,use_parler:STRING,use_snapchat:STRING,use_messenger:STRING,use_truth:STRING,use_mastodon:STRING,use_post:STRING,use_threads:STRING,use_bluesky:STRING"

echo "Raw data loaded."

# Create clustered indexed table for performance
echo "Creating clustered indexed table..."
bq query \
    --project_id="$GCP_PROJECT" \
    --use_legacy_sql=false \
    < sql/create_schema.sql

echo "BigQuery setup complete."
echo ""

# Step 3: Build container
echo "Step 3/5: Building container image..."
gcloud builds submit \
    --tag "gcr.io/$GCP_PROJECT/$SERVICE_NAME" \
    --project="$GCP_PROJECT" \
    .
echo "Container built."
echo ""

# Step 4: Deploy to Cloud Run
echo "Step 4/5: Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --image "gcr.io/$GCP_PROJECT/$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --set-env-vars "GCP_PROJECT=$GCP_PROJECT,DATASET_NAME=$DATASET_NAME,MIN_CELL_SIZE=10,GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET=$GOOGLE_CLIENT_SECRET" \
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

# Step 5: Auto-configure Claude Desktop
echo "Step 5/5: Configuring Claude Desktop..."
bash "$(dirname "$0")/configure_claude.sh" "$SERVICE_URL"

echo ""
echo "Test (browser will prompt Google login):"
echo "  open $SERVICE_URL/mcp"
echo ""
echo "Logs:"
echo "  gcloud run logs read $SERVICE_NAME --region $REGION --project $GCP_PROJECT"
echo ""
