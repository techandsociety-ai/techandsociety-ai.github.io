# Setup Guide - Social Media Demographics MCP Server

This guide walks you through deploying the Social Media Demographics MCP server to Google Cloud Run and configuring it with Claude Desktop.

## Prerequisites

Before you begin, ensure you have:

1. **Google Cloud Account** with billing enabled
   - Create one at: https://cloud.google.com/
   - You'll get $300 in free credits for new accounts

2. **gcloud CLI** installed and configured
   - Install: https://cloud.google.com/sdk/docs/install
   - Verify: `gcloud --version`

3. **Claude Desktop** installed
   - Download from: https://claude.ai/download

4. **Git** (to clone this repository)

## Step-by-Step Deployment

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd remote-mcp
```

### 2. Authenticate with Google Cloud

```bash
# Login to your Google account
gcloud auth login

# Set up application default credentials (for BigQuery access)
gcloud auth application-default login
```

### 3. Create or Select a Google Cloud Project

```bash
# Create a new project (replace PROJECT_ID with your desired ID)
gcloud projects create PROJECT_ID --name="Social Media Demographics MCP"

# Or list existing projects
gcloud projects list

# Set the project
export GCP_PROJECT="your-project-id"
gcloud config set project $GCP_PROJECT
```

### 4. Enable Billing

Visit the [Google Cloud Console](https://console.cloud.google.com/billing) and:
- Select your project
- Link a billing account
- Billing is required for Cloud Run and BigQuery

### 5. Run the Deployment Script

```bash
./deploy.sh
```

The script will:
1. Enable required APIs (Cloud Run, BigQuery, Cloud Build)
2. Create a BigQuery dataset with 10,000 synthetic survey responses
3. Build a Docker container with your MCP server
4. Deploy it to Cloud Run
5. Generate an API key for secure access

**IMPORTANT**: Save the API key shown at the end - you'll need it for Claude Desktop!

### 6. Verify Deployment

After deployment completes, test your server:

```bash
# Get your service URL from the deployment output, then:
export SERVICE_URL="https://your-service-url.run.app"
export API_KEY="your-generated-api-key"

# Test health endpoint (no auth required)
curl $SERVICE_URL/health

# Test info endpoint (requires auth)
curl -H "Authorization: Bearer $API_KEY" $SERVICE_URL/info
```

Expected response from `/info`:
```json
{
  "server": "social-media-demographics",
  "project": "your-project-id",
  "dataset": "social_media_demographics",
  "min_cell_size": 10,
  "tools": [
    "get_available_variables",
    "generate_crosstab",
    "generate_marginals",
    "generate_crosstab_batch",
    "generate_marginals_batch"
  ]
}
```

### 7. Configure Claude Desktop

#### macOS/Linux

Edit `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "social-media-demographics": {
      "url": "https://your-service-url.run.app/sse",
      "transport": {
        "type": "sse"
      },
      "env": {
        "API_KEY": "your-generated-api-key"
      }
    }
  }
}
```

#### Windows

Edit `%APPDATA%\Claude\claude_desktop_config.json` with the same content.

### 8. Restart Claude Desktop

Close and reopen Claude Desktop. You should now see the Social Media Demographics MCP server available with its logo!

## Using the MCP Server

Try these example queries in Claude Desktop:

```
Show me the available variables in the social media demographics dataset
```

```
Create a crosstab of Twitter usage by age group
```

```
Show me Instagram usage patterns across different education levels
```

```
Compare TikTok usage across all demographic categories
```

```
What are the marginal distributions for political affiliation?
```

## Local Testing (Optional)

To test the server locally before deployment:

```bash
./test_local.sh
```

This will:
- Set up a Python virtual environment
- Install dependencies
- Start the server on `localhost:8080`
- Optionally create the BigQuery dataset

## Cost Management

### Expected Costs (Moderate Use)

- **Cloud Run**: $5-10/month
  - First 2 million requests free
  - Pay only when requests are being processed
  - Scales to zero when not in use

- **BigQuery**: $1-5/month
  - First 1 TB of queries per month free
  - 10 GB of storage free
  - Our synthetic dataset is ~100 MB

- **Container Registry**: $0-1/month
  - First 0.5 GB free

**Total: ~$6-15/month for personal use**

### Cost Optimization Tips

1. **Set Max Instances**: Prevent runaway costs
   ```bash
   gcloud run services update social-media-demographics-mcp \
     --max-instances 10 \
     --region us-central1
   ```

2. **Monitor Usage**: Set up billing alerts
   - Visit [Cloud Console Billing](https://console.cloud.google.com/billing)
   - Set alerts at $10, $25, $50

3. **Delete When Not Needed**:
   ```bash
   # Delete the Cloud Run service
   gcloud run services delete social-media-demographics-mcp --region us-central1

   # Delete the BigQuery dataset
   bq rm -r -f -d $GCP_PROJECT:social_media_demographics
   ```

## Troubleshooting

### Issue: "Permission Denied" during deployment

**Solution**: Ensure you've enabled billing and have Owner/Editor role on the project:
```bash
gcloud projects get-iam-policy $GCP_PROJECT --flatten="bindings[].members" --filter="bindings.members:user:YOUR_EMAIL"
```

### Issue: "Table not found" errors in Claude Desktop

**Solution**: Verify BigQuery dataset was created:
```bash
bq ls --project_id=$GCP_PROJECT
bq ls --project_id=$GCP_PROJECT social_media_demographics
```

### Issue: "Invalid API key" errors

**Solution**: Double-check your `claude_desktop_config.json`:
- Ensure API_KEY matches the one from deployment
- No extra spaces or quotes
- File is valid JSON (use https://jsonlint.com/)

### Issue: Cloud Run service timing out

**Solution**: Increase timeout:
```bash
gcloud run services update social-media-demographics-mcp \
  --timeout 300 \
  --region us-central1
```

### Issue: "Out of memory" errors

**Solution**: Increase memory allocation:
```bash
gcloud run services update social-media-demographics-mcp \
  --memory 2Gi \
  --region us-central1
```

## Viewing Logs

```bash
# Recent logs
gcloud run logs read social-media-demographics-mcp --region us-central1 --limit 50

# Tail logs in real-time
gcloud run logs tail social-media-demographics-mcp --region us-central1
```

## Updating the Server

After making code changes:

```bash
# Rebuild and redeploy
./deploy.sh

# Or manually:
gcloud builds submit --tag gcr.io/$GCP_PROJECT/social-media-demographics-mcp
gcloud run deploy social-media-demographics-mcp \
  --image gcr.io/$GCP_PROJECT/social-media-demographics-mcp \
  --region us-central1
```

## Security Best Practices

1. **Rotate API Keys Regularly**:
   - Generate a new key: `openssl rand -base64 32`
   - Update Cloud Run environment variable
   - Update Claude Desktop config

2. **Use VPC Connector** (for production):
   - Create a VPC network
   - Connect Cloud Run service to VPC
   - Restrict BigQuery access to VPC

3. **Enable Cloud Armor** (for production):
   - Add DDoS protection
   - Rate limiting
   - Geographic restrictions

## Next Steps

- **Customize Data**: Modify `sql/create_synthetic_data.sql` to generate different synthetic data
- **Add Features**: Extend `server.py` with new analysis tools
- **Scale Up**: Add more respondents or demographic variables
- **Share**: Deploy for your team with shared access

## Support

For issues or questions:
- Check the [troubleshooting section](#troubleshooting)
- Review [Cloud Run documentation](https://cloud.google.com/run/docs)
- Review [BigQuery documentation](https://cloud.google.com/bigquery/docs)
- Open an issue on GitHub

## License

MIT License - see LICENSE file
