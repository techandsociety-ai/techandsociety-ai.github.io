# Import Error Fix - Summary

## Problem

When installing the MCP server in Claude Desktop, you got this error:
```
ImportError: Unable to import required dependencies:
numpy: Error importing numpy: you should not try to import numpy from
        its source directory; please exit the numpy source tree, and relaunch
```

## Root Cause

The original implementation tried to bundle dependencies (pandas, numpy) in a `lib/` directory using:
```bash
pip install --target=lib pandas numpy
```

This **doesn't work** for packages with compiled C extensions (like numpy) because:
- They need to be properly built for your system
- They can't be simply copied to a directory
- They require proper Python environment setup

## Solution

Switched to using **`uv`** (modern Python package manager) with **inline script dependencies** (PEP 723):

### What Changed

1. **server.py** - Added dependency metadata at the top:
   ```python
   #!/usr/bin/env -S uv run
   # /// script
   # dependencies = [
   #   "pandas>=2.0.0",
   #   "numpy>=1.24.0",
   #   "google-cloud-bigquery>=3.11.0",
   #   "mcp>=0.9.0",
   # ]
   # ///
   ```

2. **mcpb.json** - Updated to use `uv run`:
   ```json
   {
     "server": {
       "command": "uv",
       "args": ["run", "server.py"]
     }
   }
   ```

3. **Removed lib/ bundling** - Dependencies are now managed by `uv` automatically

## How to Fix Your Installation

### Option 1: Quick Setup (Recommended)

Run the automated setup script:

```bash
cd "/Users/electron/workspace/Nanocentury AI/CHIP50/chip50MCP"
./setup_claude_desktop.sh
```

Then:
1. Quit Claude Desktop (Cmd+Q)
2. Restart Claude Desktop
3. Test it!

### Option 2: Manual Setup

1. **Remove old installation:**
   ```bash
   rm -rf "/Users/electron/Library/Application Support/Claude/Claude Extensions/local.mcpb.stefan-wojcik.chip50mcp"
   ```

2. **Edit Claude config:**
   ```bash
   code ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

3. **Add this configuration:**
   ```json
   {
     "mcpServers": {
       "chip50-survey-mcp": {
         "command": "uv",
         "args": [
           "run",
           "/Users/electron/workspace/Nanocentury AI/CHIP50/chip50MCP/mcp_server/server.py"
         ]
       }
     }
   }
   ```

4. **Restart Claude Desktop**

## How It Works Now

```
Claude Desktop
  ↓
  calls: uv run server.py
  ↓
  uv reads inline dependencies from server.py
  ↓
  uv creates isolated environment
  ↓
  uv installs pandas, numpy, bigquery, mcp
  ↓
  uv runs server.py with all dependencies available
  ✓ Server starts successfully
```

**Benefits:**
- ✅ Automatic dependency management
- ✅ Works with compiled packages
- ✅ Isolated environments (no conflicts)
- ✅ Cached for fast subsequent runs
- ✅ Modern Python best practice

## Testing

After setup, test in Claude Desktop:

**Ask:**
> "Can you list the available MCP tools?"

**Expected response:**
- upload_csv_to_bigquery
- generate_crosstab
- get_summary_statistics

**Then try:**
> "Using the chip50-survey-mcp server, show me summary statistics for the trust variables using the synthetic data"

## Files Modified

- ✏️ `mcp_server/server.py` - Added PEP 723 dependencies
- ✏️ `mcp_server/mcpb.json` - Changed to use `uv run`
- ➕ `mcp_server/pyproject.toml` - Added package metadata
- ➕ `setup_claude_desktop.sh` - Automated setup script
- ➕ `INSTALLATION.md` - Detailed installation guide
- ➕ `FIX_SUMMARY.md` - This file
- ✏️ `README.md` - Updated installation instructions
- ✏️ `.gitignore` - Added `lib/` (no longer needed)

## Why uv?

**uv** is Astral's modern Python package manager (same team that built Ruff):
- 10-100x faster than pip
- Supports inline script dependencies (PEP 723)
- Automatic virtual environment management
- Better dependency resolution
- Industry standard for modern Python tools

You already have it installed! (`uv 0.9.7`)

## Need Help?

See these docs:
- `INSTALLATION.md` - Detailed installation guide
- `README.md` - Full MCP server documentation
- `QUICKSTART.md` - Quick start guide

## Quick Reference

```bash
# Setup in Claude Desktop
./setup_claude_desktop.sh

# Test locally
cd mcp_server
uv run server.py

# Run tests
python3 test_mcp_server.py

# Check config
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

That's it! The import error should be completely resolved. 🎉
