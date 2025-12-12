---
title: Complete Installation Guide
---

# CHIP50 MCP Server - Installation Guide

Complete installation guide for all platforms (macOS, Linux, Windows)

---

## Quick Install (Recommended)

### macOS / Linux

```bash
# Download the bundle
curl -LO https://github.com/nanocentury-ai/chip50MCP/releases/latest/download/chip50-survey-mcp-v2.0.0.mcpb

# Run the installer
./install.sh

# Check installation
./check_install.sh
```

### Windows (PowerShell as Administrator)

```powershell
# Download the bundle
Invoke-WebRequest -Uri "https://github.com/nanocentury-ai/chip50MCP/releases/latest/download/chip50-survey-mcp-v2.0.0.mcpb" -OutFile "chip50-survey-mcp-v2.0.0.mcpb"

# Run the installer
.\install.ps1

# Check installation (in Git Bash or WSL)
.\check_install.sh
```

---

## What the Installer Does

The automated installer handles everything:

1. ✅ **Checks prerequisites** - Python 3.10+, UV, Google Cloud SDK
2. ✅ **Installs missing tools** - Automatically installs UV if needed
3. ✅ **Creates virtual environment** - Isolated Python environment in `~/.chip50/`
4. ✅ **Installs dependencies** - pandas, google-cloud-bigquery, mcp SDK
5. ✅ **Configures Google Cloud** - Prompts for authentication
6. ✅ **Extracts bundle** - Unpacks MCP server files
7. ✅ **Configures Claude Desktop** - Adds server to Claude Desktop config
8. ✅ **Verifies installation** - Tests all components

---

## Prerequisites

### Required (All Platforms)

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.10+ | Run MCP server |
| **UV** | Latest | Python package management |
| **Google Cloud SDK** | Latest | BigQuery authentication |
| **Claude Desktop** | Latest | MCP client |

### Installing Prerequisites

#### macOS

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Google Cloud SDK
brew install google-cloud-sdk

# Authenticate
gcloud auth application-default login
gcloud config set project chip50
```

#### Linux (Ubuntu/Debian)

```bash
# Install Python
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add UV to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Authenticate
gcloud auth application-default login
gcloud config set project chip50
```

#### Windows

```powershell
# Install Python (via winget)
winget install Python.Python.3.11

# Install UV
irm https://astral.sh/uv/install.ps1 | iex

# Install Google Cloud SDK
# Download from: https://cloud.google.com/sdk/docs/install
# Or via Chocolatey:
choco install gcloudsdk

# Authenticate
gcloud auth application-default login
gcloud config set project chip50
```

---

## Installation Methods

### Method 1: Automated Installation (Recommended)

**Best for:** First-time users, quick setup

**macOS/Linux:**
```bash
./install.sh
```

**Windows:**
```powershell
.\install.ps1
```

**What it does:**
- Checks all prerequisites
- Creates virtual environment
- Installs Python dependencies
- Configures Claude Desktop automatically
- Verifies installation

**Installation location:** `~/.chip50/` (macOS/Linux) or `%USERPROFILE%\.chip50\` (Windows)

---

### Method 2: Claude Desktop UI Installation

**Best for:** Users who prefer GUI installation

**Steps:**

1. **Download the bundle:**
   - Download `chip50-survey-mcp-v2.0.0.mcpb` from releases

2. **Open Claude Desktop:**
   - Launch Claude Desktop application

3. **Add MCP Server:**
   - Go to **Settings** → **MCP Servers**
   - Click **"Add Server"** or **"Install from File"**
   - Select the downloaded `.mcpb` file
   - Or drag-and-drop the file into the window

4. **Configure environment variables:**
   - Find the newly added "CHIP50 Survey Analysis" server
   - Click settings/gear icon
   - Add the following environment variables:

   ```
   CHIP50_API_KEY=chip50_test_synthetic_data_only
   CHIP50_PROJECT_ID=chip50
   CHIP50_DATASET_PUBLIC=public
   CHIP50_MIN_CELL_SIZE=10
   ```

5. **Restart Claude Desktop**

**Note:** This method still requires prerequisites (Python, UV, gcloud) to be installed separately.

---

### Method 3: Manual Installation

**Best for:** Advanced users, custom setups

**Steps:**

1. **Extract bundle:**
   ```bash
   mkdir -p ~/.chip50
   unzip chip50-survey-mcp-v2.0.0.mcpb -d ~/.chip50/bundle
   ```

2. **Create virtual environment:**
   ```bash
   uv venv ~/.chip50/venv --python python3.10
   ```

3. **Install dependencies:**
   ```bash
   uv pip install --python ~/.chip50/venv/bin/python \
     pandas>=2.0.0 \
     google-cloud-bigquery>=3.11.0 \
     db-dtypes>=1.1.0 \
     mcp>=0.9.0
   ```

4. **Edit Claude Desktop config:**

   **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

   **Linux:** `~/.config/Claude/claude_desktop_config.json`

   **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

   Add this configuration:
   ```json
   {
     "mcpServers": {
       "chip50": {
         "command": "/Users/YOUR_USERNAME/.chip50/venv/bin/python",
         "args": [
           "/Users/YOUR_USERNAME/.chip50/bundle/mcp_server/server.py"
         ],
         "env": {
           "CHIP50_API_KEY": "chip50_test_synthetic_data_only",
           "CHIP50_PROJECT_ID": "chip50",
           "CHIP50_DATASET_PUBLIC": "public",
           "CHIP50_MIN_CELL_SIZE": "10"
         }
       }
     }
   }
   ```

   **Important:** Replace `/Users/YOUR_USERNAME/` with your actual home directory path!

5. **Restart Claude Desktop**

---

## Verification

### Check Installation Status

Run the installation checker:

```bash
./check_install.sh
```

This verifies:
- ✅ Python 3.10+ installed
- ✅ UV package manager available
- ✅ Google Cloud SDK installed and authenticated
- ✅ Virtual environment created
- ✅ Python dependencies installed
- ✅ Bundle extracted correctly
- ✅ Claude Desktop configured
- ✅ BigQuery access working

### Test in Claude Desktop

1. Open Claude Desktop
2. Start a new conversation
3. Ask: **"What variables are available in CHIP50?"**

Claude should call the `get_available_variables` tool and show you:
- Demographic variables (region, age, education, party, etc.)
- Survey variables (trust scales, approval ratings, etc.)
- Privacy protection information

### Manual Test

Test the MCP server directly:

```bash
# Activate virtual environment
source ~/.chip50/venv/bin/activate  # macOS/Linux
# or
~/.chip50/venv/Scripts/activate  # Windows

# Run server in test mode
cd ~/.chip50/bundle
python mcp_server/server.py

# You should see:
# ✓ API key validated
# ✓ Using project: chip50
# ✓ Using dataset: chip50.public
# ✓ Cell suppression threshold: n≥10
```

---

## Troubleshooting

### Error: "Python 3.10+ required"

**Solution:**
```bash
# macOS
brew install python@3.11

# Linux
sudo apt-get install python3.11

# Windows
winget install Python.Python.3.11
```

### Error: "UV not found"

**Solution:**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Windows
irm https://astral.sh/uv/install.ps1 | iex
```

### Error: "Google Cloud SDK not found"

**Solution:**
```bash
# macOS
brew install google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash

# Windows
# Download from: https://cloud.google.com/sdk/docs/install
```

### Error: "Not authenticated with Google Cloud"

**Solution:**
```bash
gcloud auth application-default login
gcloud config set project chip50
```

### Error: "CHIP50_API_KEY environment variable not set"

**Solution:**

1. **If using automated install:** Rerun `./install.sh`
2. **If using Claude Desktop UI:** Add environment variables in settings
3. **If manual install:** Check your `claude_desktop_config.json` has the env variables

### Error: "Could not access BigQuery project 'chip50'"

**Possible causes:**
1. Not authenticated with Google Cloud
2. Project 'chip50' doesn't exist
3. No permissions to access project

**Solution:**
```bash
# Authenticate
gcloud auth application-default login

# Check current project
gcloud config get-value project

# Set correct project
gcloud config set project chip50

# Verify access
bq ls --project_id=chip50
```

### Error: "Protected views not found"

**Solution:**

Run the data setup script to create protected views:
```bash
./data_setup.sh
```

Or manually create them:
```bash
bq query --use_legacy_sql=false < sql/create_demographics_protected.sql
bq query --use_legacy_sql=false < sql/create_survey_responses_protected.sql
```

### Server not appearing in Claude Desktop

**Solutions:**

1. **Verify config file exists:**
   ```bash
   # macOS
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

   # Linux
   cat ~/.config/Claude/claude_desktop_config.json

   # Windows
   type %APPDATA%\Claude\claude_desktop_config.json
   ```

2. **Check for JSON syntax errors:**
   - Use a JSON validator (jsonlint.com)
   - Ensure commas, brackets, quotes are correct

3. **Verify paths are absolute and correct:**
   - Command path should point to Python executable
   - Args path should point to server.py

4. **Restart Claude Desktop completely:**
   - Quit (not just close window)
   - Reopen

5. **Check Claude Desktop logs:**
   - macOS: `~/Library/Logs/Claude/`
   - Linux: `~/.config/Claude/logs/`
   - Windows: `%APPDATA%\Claude\logs\`

### Permission Errors (macOS/Linux)

**Solution:**
```bash
# Make scripts executable
chmod +x install.sh check_install.sh

# Fix ownership
sudo chown -R $USER ~/.chip50/
```

### Windows Path Issues

**Solution:**

Ensure paths use forward slashes in Claude Desktop config:
```json
"command": "C:/Users/YourName/.chip50/venv/Scripts/python.exe"
```

Or use double backslashes:
```json
"command": "C:\\Users\\YourName\\.chip50\\venv\\Scripts\\python.exe"
```

---

## Uninstallation

### Complete Removal

```bash
# Remove installation directory
rm -rf ~/.chip50/

# Remove Claude Desktop config (manual)
# Edit claude_desktop_config.json and remove "chip50" entry

# Uninstall UV (optional)
rm -rf ~/.cargo/bin/uv
```

### Keep Dependencies, Remove Server

```bash
# Just remove the bundle
rm -rf ~/.chip50/bundle

# Keep virtual environment and config for reinstall
```

---

## Updating

### Update to New Version

1. **Download new bundle:**
   ```bash
   curl -LO https://github.com/nanocentury-ai/chip50MCP/releases/latest/download/chip50-survey-mcp-v2.1.0.mcpb
   ```

2. **Run installer again:**
   ```bash
   ./install.sh
   ```

   The installer will:
   - Detect existing installation
   - Update bundle files
   - Preserve configuration
   - Update dependencies if needed

3. **Restart Claude Desktop**

### Update Dependencies Only

```bash
uv pip install --python ~/.chip50/venv/bin/python --upgrade \
  pandas \
  google-cloud-bigquery \
  mcp
```

---

## Configuration Files

### Installation Config

**Location:** `~/.chip50/config.json`

```json
{
  "version": "2.0.0",
  "install_date": "2025-12-11T12:00:00Z",
  "bundle_path": "/Users/name/.chip50/bundle",
  "venv_path": "/Users/name/.chip50/venv",
  "api_key": "chip50_test_synthetic_data_only",
  "project_id": "chip50",
  "dataset_public": "public",
  "min_cell_size": 10
}
```

### Claude Desktop Config

**Location (macOS):** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Location (Linux):** `~/.config/Claude/claude_desktop_config.json`

**Location (Windows):** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "chip50": {
      "command": "/path/to/.chip50/venv/bin/python",
      "args": ["/path/to/.chip50/bundle/mcp_server/server.py"],
      "env": {
        "CHIP50_API_KEY": "chip50_test_synthetic_data_only",
        "CHIP50_PROJECT_ID": "chip50",
        "CHIP50_DATASET_PUBLIC": "public",
        "CHIP50_MIN_CELL_SIZE": "10"
      }
    }
  }
}
```

---

## Platform-Specific Notes

### macOS

- **Architecture:** Bundle works on both Intel (x86_64) and Apple Silicon (arm64)
- **Security:** First run may prompt for permission - allow in System Preferences
- **Python:** Prefer Homebrew Python over system Python

### Linux

- **Distributions:** Tested on Ubuntu 20.04+, Debian 11+, Fedora 35+
- **Dependencies:** May need `python3-venv` package
- **Permissions:** Ensure user has write access to `~/.chip50/`

### Windows

- **PowerShell:** Use PowerShell 5.1+ or PowerShell Core 7+
- **Execution Policy:** May need to run: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
- **Paths:** Use forward slashes or escaped backslashes in config
- **WSL:** Can also install in WSL2 using Linux instructions

---

## Advanced Configuration

### Custom Installation Directory

```bash
# Set custom directory
export CHIP50_INSTALL_DIR="/custom/path"
./install.sh
```

### Multiple Versions

Install different versions side-by-side:

```bash
# Version 2.0.0
unzip chip50-survey-mcp-v2.0.0.mcpb -d ~/.chip50/v2.0.0

# Version 2.1.0
unzip chip50-survey-mcp-v2.1.0.mcpb -d ~/.chip50/v2.1.0

# Configure different servers in Claude Desktop
```

### Development Install

For developers working on the MCP server:

```bash
# Clone repository
git clone https://github.com/nanocentury-ai/chip50MCP.git
cd chip50MCP

# Create virtual environment
uv venv .venv
source .venv/bin/activate

# Install in editable mode
uv pip install -e .

# Point Claude Desktop to development version
# Update command path to: /path/to/chip50MCP/.venv/bin/python
# Update args path to: /path/to/chip50MCP/mcp_server/server.py
```

---

## Getting Help

### Documentation

- **Quick Start:** [QUICKSTART.md](QUICKSTART.md)
- **Setup Guide:** [SETUP.md](SETUP.md)
- **Build Plan:** [buildplan.md](buildplan.md)
- **Cross-Platform:** [CROSS_PLATFORM_GUIDE.md](CROSS_PLATFORM_GUIDE.md)

### Support Channels

- **Issues:** https://github.com/nanocentury-ai/chip50MCP/issues
- **Discussions:** https://github.com/nanocentury-ai/chip50MCP/discussions

### Before Reporting Issues

1. Run `./check_install.sh` and include output
2. Check Claude Desktop logs
3. Verify all prerequisites are installed
4. Try manual installation to isolate the problem

---

## Summary

**Easiest Method:**
```bash
./install.sh && ./check_install.sh
```

**After Installation:**
1. Restart Claude Desktop
2. Ask Claude: "What variables are available in CHIP50?"
3. Start analyzing survey data with privacy protections!

**Need Help?** Run `./check_install.sh` to diagnose issues.

---

**Version:** 2.0.0
**Last Updated:** December 2025
**License:** MIT
