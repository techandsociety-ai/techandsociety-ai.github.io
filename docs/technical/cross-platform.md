---
title: Cross-Platform Support
---

# Cross-Platform Support Guide

## How CHIP50 MCP Bundle Works Across Different Operating Systems

### Platform Detection (Automatic)

The MCPB bundle uses `"command": "uv"` which Claude Desktop resolves automatically:

| Platform | UV Location (Examples) | How It's Found |
|----------|----------------------|----------------|
| **macOS** | `~/.local/bin/uv` or `/usr/local/bin/uv` | System PATH |
| **Linux** | `~/.local/bin/uv` or `/usr/bin/uv` | System PATH |
| **Windows** | `%USERPROFILE%\.cargo\bin\uv.exe` | System PATH |

Claude Desktop uses the system's PATH environment variable to find `uv`, so no hardcoded paths needed!

---

## Installation per Platform

### macOS

**Prerequisites:**
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Google Cloud SDK
brew install google-cloud-sdk

# Authenticate
gcloud auth application-default login
gcloud config set project chip50
```

**Install Bundle:**
1. Download `chip50-survey-mcp-v2.0.0.mcpb`
2. Drag into Claude Desktop Settings → MCP Servers
3. Configure API key in settings UI

---

### Linux (Ubuntu/Debian)

**Prerequisites:**
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add UV to PATH (if not automatic)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Authenticate
gcloud auth application-default login
gcloud config set project chip50
```

**Install Bundle:**
1. Download `chip50-survey-mcp-v2.0.0.mcpb`
2. Open Claude Desktop
3. Settings → MCP Servers → Add Server
4. Select the `.mcpb` file
5. Configure API key in settings UI

---

### Windows

**Prerequisites:**
```powershell
# Install UV (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# Or via Scoop
scoop install uv

# Install Google Cloud SDK
# Download from: https://cloud.google.com/sdk/docs/install
# Or via Chocolatey:
choco install gcloudsdk

# Authenticate
gcloud auth application-default login
gcloud config set project chip50
```

**Install Bundle:**
1. Download `chip50-survey-mcp-v2.0.0.mcpb`
2. Open Claude Desktop
3. Settings → MCP Servers → Add Server
4. Select the `.mcpb` file
5. Configure API key in settings UI

**Windows-Specific Notes:**
- UV installs to `%USERPROFILE%\.cargo\bin\uv.exe`
- Ensure this directory is in your PATH
- Google Cloud credentials stored in: `%APPDATA%\gcloud\`

---

## Path Resolution

### How `"command": "uv"` Works

When Claude Desktop sees:
```json
{
  "command": "uv",
  "args": ["run", "--no-project", "..."]
}
```

It searches for `uv` in:
1. **System PATH** (primary method)
2. **Common installation locations** (fallback)

### Platform-Specific Paths

**macOS/Linux:**
- `~/.local/bin/uv`
- `/usr/local/bin/uv`
- `/usr/bin/uv`

**Windows:**
- `%USERPROFILE%\.cargo\bin\uv.exe`
- `%LOCALAPPDATA%\Programs\uv\uv.exe`
- `C:\Program Files\uv\uv.exe`

### Verification

To verify UV is in PATH:

**macOS/Linux:**
```bash
which uv
uv --version
```

**Windows (PowerShell):**
```powershell
where.exe uv
uv --version
```

---

## File Paths (Handled Automatically)

### Python Script Paths

The manifest uses:
```json
"${__dirname}/mcp_server/server.py"
```

**What happens:**
- `${__dirname}` → Replaced with bundle installation directory
- Works on all platforms (Claude Desktop handles path separators)

**Platform Translations:**
- **macOS/Linux:** `/path/to/bundle/mcp_server/server.py`
- **Windows:** `C:\path\to\bundle\mcp_server\server.py`

### Google Cloud Credentials

**macOS/Linux:**
- Default: `~/.config/gcloud/application_default_credentials.json`

**Windows:**
- Default: `%APPDATA%\gcloud\application_default_credentials.json`

Claude Desktop's BigQuery client detects these automatically via:
```python
from google.cloud import bigquery
client = bigquery.Client()  # Auto-detects credentials
```

---

## Platform Compatibility Declaration

The manifest declares:
```json
"compatibility": {
  "platforms": ["darwin", "linux", "win32"]
}
```

This tells Claude Desktop the bundle works on:
- **`darwin`** → macOS
- **`linux`** → Linux (all distros)
- **`win32`** → Windows (all versions)

---

## Testing Per Platform

### Automated Tests (Future)

Create platform-specific test scripts:

**`test_macos.sh`:**
```bash
#!/bin/bash
uv --version || exit 1
gcloud --version || exit 1
echo "✓ macOS prerequisites OK"
```

**`test_linux.sh`:**
```bash
#!/bin/bash
uv --version || exit 1
gcloud --version || exit 1
echo "✓ Linux prerequisites OK"
```

**`test_windows.ps1`:**
```powershell
uv --version
if ($LASTEXITCODE -ne 0) { exit 1 }
gcloud --version
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "✓ Windows prerequisites OK"
```

---

## Common Cross-Platform Issues

### Issue 1: UV Not Found

**Error:** `'uv' is not recognized as an internal or external command`

**Solution:**
```bash
# Verify UV is installed
uv --version

# If not found, add to PATH
# macOS/Linux:
export PATH="$HOME/.local/bin:$PATH"

# Windows (PowerShell as Admin):
$env:Path += ";$env:USERPROFILE\.cargo\bin"
[Environment]::SetEnvironmentVariable("Path", $env:Path, "User")
```

### Issue 2: Python Version

**Error:** `Python 3.10 or higher required`

**Solution:**
UV automatically downloads the correct Python version! Just ensure UV itself is installed.

### Issue 3: Google Cloud Auth

**Error:** `Could not automatically determine credentials`

**Solution (All Platforms):**
```bash
gcloud auth application-default login
```

This creates credentials in the platform-specific location automatically.

### Issue 4: Line Endings (Windows)

**Potential Issue:** Git may checkout with CRLF line endings

**Prevention:** Already handled in `.gitignore`:
```
# .gitattributes (create if needed)
*.py text eol=lf
*.sh text eol=lf
*.json text eol=lf
```

UV handles this automatically when running Python scripts.

---

## Build Process (Cross-Platform)

The `build_mcpb.sh` script creates a platform-agnostic bundle:

```bash
./build_mcpb.sh
# Creates: chip50-survey-mcp-v2.0.0.mcpb
# Works on: macOS, Linux, Windows
```

**Single bundle works everywhere** because:
1. Python code is cross-platform
2. UV handles Python version detection
3. Paths use platform-agnostic variables
4. Dependencies installed per-platform by UV

---

## Distribution

### One Bundle, All Platforms

You only need to distribute:
- ✅ `chip50-survey-mcp-v2.0.0.mcpb` (single file)
- ✅ Platform-specific installation docs (UV + gcloud setup)

### Download Page Example

```
chip50.org/download

CHIP50 MCP Bundle
-----------------
Version: 2.0.0
File: chip50-survey-mcp-v2.0.0.mcpb (160KB)

[Download Bundle]

Prerequisites by Platform:
- macOS: [Instructions]
- Linux: [Instructions]
- Windows: [Instructions]
```

---

## Summary

### What Claude Desktop Handles Automatically
- ✅ Finding `uv` in system PATH
- ✅ Path separator translation (`/` vs `\`)
- ✅ Environment variable expansion (`${__dirname}`)
- ✅ Platform detection
- ✅ Google Cloud credential location

### What Users Must Install (Per-Platform)
- ✅ UV package manager
- ✅ Google Cloud SDK
- ✅ Authentication (`gcloud auth`)

### What's the Same Everywhere
- ✅ Bundle file (`.mcpb`)
- ✅ Configuration UI
- ✅ API key setup
- ✅ Tool functionality

**Result:** One bundle, works everywhere, minimal platform-specific setup! 🎉
