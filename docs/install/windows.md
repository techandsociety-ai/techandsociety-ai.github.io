---
title: Windows Installation
---

# Installing CHIP50 MCP on Windows

Complete installation guide for Windows 10 and Windows 11.

## Prerequisites

### 1. UV Package Manager

**PowerShell (Recommended):**
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

**Or via Scoop:**
```powershell
scoop install uv
```

**Or via pip:**
```powershell
pip install uv
```

Verify:
```powershell
uv --version
```

### 2. Google Cloud SDK

**Option A: Interactive Installer (Recommended)**
1. Download from: [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)
2. Run the installer
3. Follow the prompts
4. Restart your terminal

**Option B: Chocolatey**
```powershell
choco install gcloudsdk
```

Verify:
```powershell
gcloud --version
```

### 3. Authenticate with Google Cloud

```powershell
# Authenticate
gcloud auth application-default login

# Set project
gcloud config set project chip50
```

## Installation Methods

### Method 1: Automated Installer (Recommended)

```powershell
# Download the installation script
Invoke-WebRequest -Uri "https://github.com/nanocentury-ai/chip50MCP/releases/latest/download/install.ps1" -OutFile "install.ps1"

# Run the installer
.\install.ps1
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
```powershell
Invoke-WebRequest -Uri "https://github.com/nanocentury-ai/chip50MCP/releases/latest/download/chip50-survey-mcp-v2.0.0.mcpb" -OutFile "chip50-survey-mcp-v2.0.0.mcpb"
```

2. **Install in Claude Desktop:**
   - Open Claude Desktop
   - Go to Settings → MCP Servers
   - Click "Add Server" and select the `.mcpb` file
   - Or drag the file into the MCP Servers window

3. **Configure environment variables in Claude Desktop UI:**
   - `CHIP50_API_KEY`: `chip50_test_synthetic_data_only`
   - `CHIP50_PROJECT_ID`: `chip50`
   - `CHIP50_DATASET_PUBLIC`: `public`

4. **Restart Claude Desktop**

### Method 3: Development Installation

For local development:

1. **Clone the repository:**
```powershell
git clone https://github.com/nanocentury-ai/chip50MCP.git
cd chip50MCP
```

2. **Edit Claude Desktop config:**
```powershell
notepad "$env:APPDATA\Claude\claude_desktop_config.json"
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
        "C:\\Users\\YOUR_USERNAME\\path\\to\\chip50MCP",
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

**Important:** Update the `--directory` path to your actual path! Use double backslashes (`\\`) or forward slashes (`/`).

3. **Restart Claude Desktop**

## Verification

### Run the Installation Checker

```powershell
.\check_install.ps1
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

## Windows-Specific Notes

### File Locations

- **UV:** `%USERPROFILE%\.cargo\bin\uv.exe`
- **Google Cloud config:** `%APPDATA%\gcloud\`
- **Claude Desktop config:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Claude Desktop logs:** `%APPDATA%\Claude\logs\`

### PATH Configuration

UV should be added to PATH automatically. If not:

1. Open System Properties (Win+Pause/Break)
2. Click "Advanced system settings"
3. Click "Environment Variables"
4. Under "User variables", select "Path" and click "Edit"
5. Click "New" and add: `%USERPROFILE%\.cargo\bin`
6. Click OK on all dialogs
7. **Restart your terminal**

### PowerShell Execution Policy

If you get "script execution disabled" errors:

```powershell
# Check current policy
Get-ExecutionPolicy

# Allow scripts (as Administrator)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Windows Defender

Windows Defender may flag UV or the installation script. This is a false positive. You can:
1. Click "More info" → "Run anyway"
2. Or add an exception for the file

## Troubleshooting

### UV Not Found

```powershell
# Check if UV is in PATH
where.exe uv

# If not found, add to PATH manually (see above)

# Or reinstall
irm https://astral.sh/uv/install.ps1 | iex
```

### Google Cloud Authentication Issues

```powershell
# Re-authenticate
gcloud auth application-default login

# Check project
gcloud config get-value project

# Should show: chip50

# Check credentials file exists
Test-Path "$env:APPDATA\gcloud\application_default_credentials.json"
```

### Claude Desktop Not Finding Server

1. **Check config file exists:**
```powershell
Get-Content "$env:APPDATA\Claude\claude_desktop_config.json"
```

2. **Verify JSON syntax:**
Use [jsonlint.com](https://jsonlint.com) to validate

3. **Check path format:**
   - Use forward slashes: `"C:/Users/..."`
   - Or double backslashes: `"C:\\Users\\..."`
   - Do NOT use single backslashes

4. **Check Claude Desktop logs:**
```powershell
Get-Content "$env:APPDATA\Claude\logs\mcp*.log" -Tail 50
```

5. **Restart Claude Desktop completely:**
   - Quit Claude Desktop (File → Exit)
   - Wait 5 seconds
   - Reopen Claude Desktop

### BigQuery Access Denied

```powershell
# Verify you have access to the project
gcloud projects list

# Should show chip50 in the list

# Test BigQuery access
bq query --use_legacy_sql=false "SELECT COUNT(*) FROM `chip50.public.demographics_protected`"
```

### Line Ending Issues

If you get errors about line endings when running scripts:

```powershell
# Convert line endings (requires dos2unix)
dos2unix install.sh

# Or use Git to checkout with correct line endings
git config --global core.autocrlf input
```

### Antivirus Blocking Installation

Some antivirus software may block UV or the MCP server:

1. **Temporarily disable antivirus** during installation
2. **Add exceptions** for:
   - `%USERPROFILE%\.cargo\bin\uv.exe`
   - The chip50MCP installation directory
   - Claude Desktop executable

### WSL (Windows Subsystem for Linux)

If using WSL, follow the [Linux installation guide](linux.md) instead. The Windows guide is for native Windows installation.

## PowerShell Tips

### Check System Information

```powershell
# Windows version
[System.Environment]::OSVersion.Version

# PowerShell version
$PSVersionTable.PSVersion

# Check if UV is in PATH
$env:Path -split ';' | Select-String "uv"
```

### Environment Variables

```powershell
# View environment variable
echo $env:CHIP50_API_KEY

# Set environment variable (current session)
$env:CHIP50_API_KEY = "chip50_test_synthetic_data_only"

# Set permanently (requires restart)
[System.Environment]::SetEnvironmentVariable("CHIP50_API_KEY", "chip50_test_synthetic_data_only", "User")
```

## Next Steps

- [Quick Start Guide](../getting-started/quickstart.md)
- [First Steps](../getting-started/first-steps.md)
- [Troubleshooting Guide](troubleshooting.md)
