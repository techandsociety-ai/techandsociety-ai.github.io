#!/bin/bash
set -e

# Social Media Demographics MCP - Deployment Script
# Deploys the remote MCP server to Google Cloud Run

echo "==================================="
echo "Social Media Demographics MCP"
echo "Cloud Run Deployment Script"
echo "==================================="
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed."
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get or prompt for project ID
if [ -z "$GCP_PROJECT" ]; then
    echo "Enter your Google Cloud Project ID:"
    read -r GCP_PROJECT
fi

if [ -z "$GCP_PROJECT" ]; then
    echo "Error: GCP_PROJECT is required"
    exit 1
fi

echo "Using project: $GCP_PROJECT"
gcloud config set project "$GCP_PROJECT"

# Configuration
SERVICE_NAME="social-media-demographics-mcp"
REGION="${REGION:-us-central1}"
DATASET_NAME="social_media_demographics"

echo ""
echo "Configuration:"
echo "  Service: $SERVICE_NAME"
echo "  Region: $REGION"
echo "  Dataset: $DATASET_NAME"
echo ""

# Generate API key if not set
if [ -z "$API_KEY" ]; then
    API_KEY="smdem_$(openssl rand -base64 32 | tr -d '/+=' | cut -c1-43)"
    echo "Generated API Key: $API_KEY"
    echo "IMPORTANT: Save this API key - you'll need it to configure Claude Desktop"
    echo ""
fi

# Step 1: Enable required APIs
echo "Step 1/5: Enabling required Google Cloud APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    bigquery.googleapis.com \
    --project="$GCP_PROJECT"

echo "APIs enabled successfully"
echo ""

# Step 2: Create BigQuery dataset and load synthetic data
echo "Step 2/5: Creating BigQuery dataset with synthetic data..."

# Check if dataset exists
if bq ls -d --project_id="$GCP_PROJECT" "$DATASET_NAME" &> /dev/null; then
    echo "Dataset $DATASET_NAME already exists"
    echo "Do you want to recreate it? (y/N)"
    read -r RECREATE
    if [ "$RECREATE" = "y" ] || [ "$RECREATE" = "Y" ]; then
        bq rm -r -f -d "$GCP_PROJECT:$DATASET_NAME"
        echo "Existing dataset deleted"
    else
        echo "Using existing dataset"
    fi
fi

# Create dataset if it doesn't exist
if ! bq ls -d --project_id="$GCP_PROJECT" "$DATASET_NAME" &> /dev/null; then
    echo "Creating dataset..."
    bq mk --project_id="$GCP_PROJECT" --dataset --location=US "$DATASET_NAME"

    echo "Loading synthetic data..."
    bq query --project_id="$GCP_PROJECT" --use_legacy_sql=false < sql/create_synthetic_data.sql

    echo "Dataset created and populated successfully"
else
    echo "Dataset already exists, skipping creation"
fi

echo ""

# Step 3: Build and push container
echo "Step 3/5: Building container image..."

gcloud builds submit \
    --tag "gcr.io/$GCP_PROJECT/$SERVICE_NAME" \
    --project="$GCP_PROJECT" \
    .

echo "Container built successfully"
echo ""

# Step 4: Deploy to Cloud Run
echo "Step 4/5: Deploying to Cloud Run..."

gcloud run deploy "$SERVICE_NAME" \
    --image "gcr.io/$GCP_PROJECT/$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --set-env-vars "GCP_PROJECT=$GCP_PROJECT,DATASET_NAME=$DATASET_NAME,API_KEY=$API_KEY,MIN_CELL_SIZE=10" \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0 \
    --project="$GCP_PROJECT"

echo "Deployment successful"
echo ""

# Step 5: Get service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --project="$GCP_PROJECT" \
    --format 'value(status.url)')

echo "==================================="
echo "Deployment Complete!"
echo "==================================="
echo ""
echo "Service URL: $SERVICE_URL"
echo "API Key: $API_KEY"
echo ""
echo "Add this to your Claude Desktop config (~/.config/claude/claude_desktop_config.json):"
echo ""
cat << EOF
{
  "mcpServers": {
    "social-media-demographics": {
      "url": "$SERVICE_URL/sse",
      "transport": {
        "type": "sse"
      },
      "env": {
        "API_KEY": "$API_KEY"
      }
    }
  }
}
EOF
echo ""
echo "Test the deployment:"
echo "  curl -H \"Authorization: Bearer $API_KEY\" $SERVICE_URL/info"
echo ""
echo "View logs:"
echo "  gcloud run logs read $SERVICE_NAME --region $REGION --project $GCP_PROJECT"
echo ""
