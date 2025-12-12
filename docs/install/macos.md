---
title: macOS Installation
---

# Installing CHIP50 MCP on macOS

Complete installation guide for macOS (Intel and Apple Silicon).

## Prerequisites

### 1. Homebrew (Recommended)

If you don't have Homebrew:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. UV Package Manager

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Add to your PATH (usually done automatically):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

Verify:
```bash
uv --version
```

### 3. Google Cloud SDK

**Option A: Homebrew (Recommended)**
```bash
brew install google-cloud-sdk
```

**Option B: Direct Install**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

Verify:
```bash
gcloud --version
```

### 4. Authenticate with Google Cloud

```bash
# Authenticate
gcloud auth application-default login

# Set project
gcloud config set project chip50
```

## Installation Methods

### Method 1: Automated Installer (Recommended)

```bash
# Download the installation script
curl -LO https://github.com/nanocentury-ai/chip50MCP/releases/latest/download/install.sh

# Make it executable
chmod +x install.sh

# Run the installer
./install.sh
```

The installer will:
1. ✓ Check for UV and Google Cloud SDK
2. ✓ Download the CHIP50 MCP bundle
3. ✓ Install the bundle to Claude Desktop
4. ✓ Configure environment variables
5. ✓ Verify the installation

**Restart Claude Desktop** to activate.

### Method 2: Manual Bundle Installation

1. **Download the bundle:**
```bash
curl -LO https://github.com/nanocentury-ai/chip50MCP/releases/latest/download/chip50-survey-mcp-v2.0.0.mcpb
```

2. **Install in Claude Desktop:**
   - Open Claude Desktop
   - Go to Settings → MCP Servers
   - Drag `chip50-survey-mcp-v2.0.0.mcpb` into the window
   - Or click "Add Server" and select the file

3. **Configure environment variables in Claude Desktop UI:**
   - `CHIP50_API_KEY`: `chip50_test_synthetic_data_only`
   - `CHIP50_PROJECT_ID`: `chip50`
   - `CHIP50_DATASET_PUBLIC`: `public`

4. **Restart Claude Desktop**

### Method 3: Development Installation

For local development:

1. **Clone the repository:**
```bash
git clone https://github.com/nanocentury-ai/chip50MCP.git
cd chip50MCP
```

2. **Edit Claude Desktop config:**
```bash
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Add:
```json
{
  "mcpServers": {
    "chip50": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/YOUR_USERNAME/path/to/chip50MCP",
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

**Important:** Update the `--directory` path to your actual path!

3. **Restart Claude Desktop**

## Verification

### Run the Installation Checker

```bash
./check_install.sh
```

Expected output:
```
✓ UV is installed (v0.x.x)
✓ Google Cloud SDK is installed
✓ Authenticated with Google Cloud
✓ Project set to: chip50
✓ Can access BigQuery
✓ Protected views exist
✓ Claude Desktop config exists
✓ MCP server configured

Installation complete! ✓
```

### Test in Claude Desktop

Open Claude Desktop and ask:
```
What variables are available in CHIP50?
```

Claude should call `get_available_variables` and show demographic and survey variables.

## macOS-Specific Notes

### Apple Silicon (M1/M2/M3) vs Intel

UV and Google Cloud SDK work on both architectures. No special configuration needed.

### File Locations

- **UV:** `~/.local/bin/uv`
- **Google Cloud config:** `~/.config/gcloud/`
- **Claude Desktop config:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Claude Desktop logs:** `~/Library/Logs/Claude/`

### Permissions

If you get "permission denied" errors:
```bash
# Make script executable
chmod +x install.sh

# Or for the check script
chmod +x check_install.sh
```

### Homebrew Paths

If Homebrew is installed in a custom location:
```bash
# Check Homebrew prefix
brew --prefix

# Add to PATH if needed
export PATH="$(brew --prefix)/bin:$PATH"
```

## Troubleshooting

### UV Not Found

```bash
# Check if UV is installed
which uv

# If not found, add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Google Cloud Authentication Issues

```bash
# Re-authenticate
gcloud auth application-default login

# Check project
gcloud config get-value project

# Should show: chip50
```

### Claude Desktop Not Finding Server

1. **Check config file exists:**
```bash
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

2. **Verify JSON syntax:**
Use [jsonlint.com](https://jsonlint.com) to validate

3. **Check Claude Desktop logs:**
```bash
tail -f ~/Library/Logs/Claude/mcp*.log
```

4. **Restart Claude Desktop completely:**
   - Quit Claude Desktop (Cmd+Q)
   - Wait 5 seconds
   - Reopen Claude Desktop

### BigQuery Access Denied

```bash
# Verify you have access to the project
gcloud projects list

# Should show chip50 in the list

# Check IAM permissions
gcloud projects get-iam-policy chip50 --flatten="bindings[].members" --filter="bindings.members:user:$(gcloud config get-value account)"
```

## Next Steps

- [Quick Start Guide](../getting-started/quickstart.md)
- [First Steps](../getting-started/first-steps.md)
- [Troubleshooting Guide](troubleshooting.md)
