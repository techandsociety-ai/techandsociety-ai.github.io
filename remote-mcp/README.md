# Social Media Demographics MCP Server

A remote Model Context Protocol (MCP) server for analyzing social media demographics data, deployed on Google Cloud Run.

## Overview

This MCP server provides privacy-protected access to synthetic social media demographics data through BigQuery. It enables analysis of platform usage across demographic segments including age, gender, race/ethnicity, education, income, and political affiliation.

## Features

- **Remote Access**: Deployed on Google Cloud Run, accessible from anywhere
- **Privacy Protected**: Automatic cell suppression for small counts (n<10)
- **Multiple Platforms**: Coverage of major social media platforms (Twitter/X, Facebook, Instagram, TikTok, LinkedIn, YouTube, Reddit, Snapchat)
- **Rich Demographics**: Age, gender, race/ethnicity, education, income, political affiliation, geography
- **Batch Operations**: Efficient parallel queries for multiple analyses
- **Weighted Analysis**: Support for population-weighted estimates

## Available Tools

### 1. `get_available_variables`
Discover available demographic and platform usage variables.

### 2. `generate_crosstab`
Generate cross-tabulations of platform usage by demographic variables.

### 3. `generate_marginals`
Get overall distribution for a single variable.

### 4. `generate_crosstab_batch`
Generate multiple crosstabs in parallel (efficient for analyzing one platform across multiple demographics).

### 5. `generate_marginals_batch`
Generate marginal distributions for multiple variables in parallel.

## Quick Start

### Prerequisites

1. Google Cloud account with billing enabled
2. `gcloud` CLI installed and configured
3. Claude Desktop installed

### Deployment

1. Clone this repository
2. Set your Google Cloud project:
   ```bash
   export GCP_PROJECT="your-project-id"
   ```

3. Run the deployment script:
   ```bash
   ./deploy.sh
   ```

4. The script will:
   - Create BigQuery dataset with synthetic data
   - Build and deploy the MCP server to Cloud Run
   - Output the service URL and API key

### Configure Claude Desktop

Add this to your Claude Desktop MCP configuration:

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

## Data Structure

### Demographics Table
- Age groups (18-24, 25-34, 35-44, 45-54, 55-64, 65+)
- Gender (Male, Female, Non-binary, Prefer not to say)
- Race/Ethnicity (White, Black, Hispanic, Asian, Other, Multiple)
- Education (High School or less, Some College, Bachelor's, Graduate degree)
- Income brackets
- Political affiliation (Democrat, Republican, Independent, Other)
- Geographic region (Northeast, South, Midwest, West)
- Urban/Suburban/Rural classification

### Platform Usage Table
- Platform: Twitter/X, Facebook, Instagram, TikTok, LinkedIn, YouTube, Reddit, Snapchat
- Frequency: Never, Rarely, Sometimes, Often, Daily
- Account status: Active, Inactive, No account
- Years using platform
- Content creation behavior

## Privacy & Security

- **Cell Suppression**: Counts below 10 are automatically suppressed
- **API Key Authentication**: Prevents unauthorized access
- **No PII Storage**: Only aggregated demographic categories
- **Rate Limiting**: Prevents abuse
- **Audit Logging**: All queries logged for compliance

## Development

### Local Testing

```bash
cd remote-mcp
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python server.py
```

### Project Structure

```
remote-mcp/
├── server.py           # Main MCP server with FastAPI
├── Dockerfile          # Container configuration
├── requirements.txt    # Python dependencies
├── deploy.sh          # Deployment automation
├── cloud-run.yaml     # Cloud Run configuration
├── sql/               # BigQuery table creation scripts
│   ├── create_demographics.sql
│   └── create_platform_usage.sql
└── logo.svg           # MCP server logo
```

## Cost Estimation

Typical monthly costs for moderate use:
- Cloud Run: ~$5-10 (with generous free tier)
- BigQuery: ~$1-5 (first 1TB queries free monthly)
- Total: ~$6-15/month for personal use

## Support

For issues or questions, please open an issue on GitHub.

## License

MIT License - see LICENSE file for details.
