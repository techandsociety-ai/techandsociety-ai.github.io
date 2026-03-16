# Quick Start Guide

Get up and running with the Social Media Demographics MCP server in 10 minutes!

## Prerequisites Check

Before you start, verify you have:

```bash
# Check gcloud CLI
gcloud --version

# Check authentication
gcloud auth list

# Check Python
python3 --version  # Should be 3.11 or higher
```

If any of these fail, see [SETUP.md](SETUP.md) for installation instructions.

## 5-Step Deployment

### 1. Set Your Project

```bash
export GCP_PROJECT="your-project-id"
# Or create a new one:
# gcloud projects create my-mcp-project
```

### 2. Authenticate

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project $GCP_PROJECT
```

### 3. Deploy

```bash
./deploy.sh
```

☕ This takes ~5-10 minutes. The script will:
- Enable Google Cloud APIs
- Create BigQuery dataset with 10,000 synthetic responses
- Build and deploy your MCP server
- Generate a secure API key

### 4. Save Your Credentials

When deployment completes, you'll see:

```
Service URL: https://social-media-demographics-mcp-xxxxx.run.app
API Key: smdem_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Save both of these!**

### 5. Configure Claude Desktop

#### macOS/Linux
```bash
# Create config directory if it doesn't exist
mkdir -p ~/.config/claude

# Edit config file
nano ~/.config/claude/claude_desktop_config.json
```

#### Windows
```powershell
# Edit this file:
notepad %APPDATA%\Claude\claude_desktop_config.json
```

#### Add This Configuration

Replace `YOUR_SERVICE_URL` and `YOUR_API_KEY` with values from step 4:

```json
{
  "mcpServers": {
    "social-media-demographics": {
      "url": "YOUR_SERVICE_URL/sse",
      "transport": {
        "type": "sse"
      },
      "env": {
        "API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

**Example**:
```json
{
  "mcpServers": {
    "social-media-demographics": {
      "url": "https://social-media-demographics-mcp-abc123.run.app/sse",
      "transport": {
        "type": "sse"
      },
      "env": {
        "API_KEY": "smdem_abc123xyz789"
      }
    }
  }
}
```

### 6. Restart Claude Desktop

Close and reopen Claude Desktop completely.

## Verify It Works

In Claude Desktop, try:

```
What variables are available in the social media demographics dataset?
```

You should see demographic variables (age_group, gender, etc.) and platform usage variables (twitter_frequency, facebook_frequency, etc.).

## Example Queries

Try these to explore the data:

### Simple Analysis
```
Show me Twitter usage by age group
```

### Cross-Platform Comparison
```
Compare TikTok and Facebook usage across age groups
```

### Multiple Demographics
```
Analyze Instagram usage across age, gender, and education level
```

### Political Analysis
```
How does Twitter usage vary by political affiliation?
```

### Batch Analysis
```
Create a comprehensive demographic profile of LinkedIn users
```

## Troubleshooting

### Can't See the MCP Server in Claude Desktop?

1. Check the config file has valid JSON: https://jsonlint.com/
2. Ensure no trailing commas
3. Check file location:
   - macOS/Linux: `~/.config/claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
4. Completely quit and restart Claude Desktop (don't just close the window)

### "Invalid API Key" Error?

1. Double-check the API key in your config matches deployment output
2. Ensure no extra spaces or quotes in the config file
3. Verify with:
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" YOUR_SERVICE_URL/info
   ```

### "Table Not Found" Error?

Check if BigQuery dataset was created:
```bash
bq ls --project_id=$GCP_PROJECT
bq ls --project_id=$GCP_PROJECT social_media_demographics
```

If missing, run:
```bash
bq query --project_id=$GCP_PROJECT --use_legacy_sql=false < sql/create_synthetic_data.sql
```

### Deployment Failed?

1. Check billing is enabled: https://console.cloud.google.com/billing
2. Verify you have Owner/Editor permissions on the project
3. Check the error message - it usually tells you what's wrong!

## What's Next?

- **Customize Data**: Edit `sql/create_synthetic_data.sql` to change the synthetic dataset
- **Add Tools**: Extend `server.py` with new analysis functions
- **Monitor Costs**: Set up billing alerts in Google Cloud Console
- **Share Access**: Give teammates the Service URL and API key

## Cost Control

Your server scales to zero when not in use, so you only pay for:
- Active requests (very cheap)
- BigQuery storage (~100MB = pennies per month)

Expected cost: **$5-15/month** for personal use with Google Cloud's free tier.

Set a budget alert:
```bash
# Visit: https://console.cloud.google.com/billing/
# Set alerts at $10, $25, $50
```

## Getting Help

- Full documentation: [SETUP.md](SETUP.md)
- View logs: `gcloud run logs read social-media-demographics-mcp --region us-central1`
- Check status: Visit your service URL in a browser
- Delete everything: See "Cleanup" section in SETUP.md

---

**Congratulations!** 🎉 You now have a fully functional remote MCP server for social media demographics analysis!
