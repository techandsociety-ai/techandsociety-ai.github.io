---
title: Installation Guide
---

# Complete Installation Guide

This guide covers all installation methods for the CHIP50 MCP server across different platforms.

## Automated Installation (Recommended)

The automated installer handles all dependencies and configuration for you.

### macOS / Linux

```bash
# Download the bundle
curl -LO https://github.com/nanocentury-ai/chip50MCP/releases/latest/download/chip50-survey-mcp-v2.0.0.mcpb

# Make installer executable
chmod +x install.sh

# Run the installer
./install.sh

# Restart Claude Desktop
```

### Windows

```powershell
# Download the bundle
Invoke-WebRequest -Uri "https://github.com/nanocentury-ai/chip50MCP/releases/latest/download/chip50-survey-mcp-v2.0.0.mcpb" -OutFile "chip50-survey-mcp-v2.0.0.mcpb"

# Run the installer
.\install.ps1

# Restart Claude Desktop
```

## Manual Installation

### Prerequisites

#### 1. UV Package Manager

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

Verify installation:
```bash
uv --version
```

#### 2. Google Cloud SDK

**macOS:**
```bash
brew install google-cloud-sdk
```

**Linux:**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

**Windows:**
Download from [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)

Or via Chocolatey:
```powershell
choco install gcloudsdk
```

Verify installation:
```bash
gcloud --version
```

#### 3. Google Cloud Authentication

```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Set the CHIP50 project
gcloud config set project chip50
```

### Manual Bundle Installation

1. Download the `.mcpb` file from releases
2. Open Claude Desktop
3. Go to Settings → MCP Servers
4. Click "Add Server" or drag the `.mcpb` file
5. Configure environment variables:
   - `CHIP50_API_KEY`: `chip50_test_synthetic_data_only`
   - `CHIP50_PROJECT_ID`: `chip50`
   - `CHIP50_DATASET_PUBLIC`: `public`

### Development Installation

For local development from source:

**1. Clone the repository:**
```bash
git clone https://github.com/nanocentury-ai/chip50MCP.git
cd chip50MCP
```

**2. Configure Claude Desktop:**

Edit your configuration file:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Add:
```json
{
  "mcpServers": {
    "chip50": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/ABSOLUTE/PATH/TO/chip50MCP",
        "python",
        "mcp_server/server.py"
      ],
      "env": {
        "CHIP50_API_KEY": "chip50_test_synthetic_data_only",
        "CHIP50_PROJECT_ID": "chip50",
        "CHIP50_DATASET_PUBLIC": "public"
      }
    }
  }
}
```

**Important:** Replace `/ABSOLUTE/PATH/TO/chip50MCP` with your actual path!

**3. Restart Claude Desktop**

## Verification

### Check Installation

Run the installation checker:

```bash
./check_install.sh
```

This verifies:
- ✓ UV is installed and in PATH
- ✓ Google Cloud SDK is installed
- ✓ Google Cloud authentication is configured
- ✓ Access to CHIP50 BigQuery project
- ✓ Protected views exist
- ✓ Claude Desktop can connect to the MCP server

### Manual Verification

**1. Check UV:**
```bash
uv --version
# Should show: uv 0.x.x or higher
```

**2. Check Google Cloud:**
```bash
gcloud config get-value project
# Should show: chip50

gcloud auth application-default print-access-token
# Should show a valid access token
```

**3. Test BigQuery Access:**
```bash
bq query --use_legacy_sql=false \
  'SELECT COUNT(*) as n FROM `chip50.public.demographics_protected`'
# Should return a count (e.g., 1500)
```

**4. Check Claude Desktop:**

Open Claude Desktop and ask:
```
What variables are available in CHIP50?
```

Claude should call `get_available_variables` and return demographic and survey variables.

## Troubleshooting

See the [Troubleshooting Guide](../install/troubleshooting.md) for common issues and solutions.

## Next Steps

- [Quick Start Guide](quickstart.md) - Try your first queries
- [First Steps](first-steps.md) - Learn basic usage
- [User Guide](../user-guide/usage.md) - Detailed usage instructions
