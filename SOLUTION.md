# Solution: ImportError Fixed ✅

## Problem Summary

When installing the CHIP50 MCP extension to Claude Desktop, you encountered:
```
ImportError: Unable to import required dependencies:
numpy: Error importing numpy: you should not try to import numpy from
        its source directory
```

## Root Cause

The original implementation tried to bundle dependencies using:
```bash
pip install --target=mcp_server/lib pandas numpy google-cloud-bigquery mcp
```

**This doesn't work** for packages with compiled C extensions (numpy, pandas) because:
- They need proper platform-specific compilation
- They can't be simply copied between directories
- The `--target` approach breaks their internal structure

## Solution: Bundled Virtual Environment

Following the **official Anthropic pattern** from their [file-manager-python example](https://github.com/modelcontextprotocol/mcpb/tree/main/examples/file-manager-python), we switched to bundling a complete virtual environment.

### Key Changes

1. **Created `build.sh`** - Builds a venv with all dependencies
2. **Updated `manifest.json`** - Points to the bundled Python interpreter:
   ```json
   {
     "server": {
       "mcp_config": {
         "command": "${__dirname}/mcp_server/venv/bin/python",
         "args": ["${__dirname}/mcp_server/server.py"]
       }
     }
   }
   ```
3. **Removed `lib/` bundling** - Now gitignored
4. **Updated `.gitignore`** - Excludes `venv/` (users build it locally)

### How It Works

```
User clones repo
     ↓
Runs ./build.sh
     ↓
Creates mcp_server/venv/
     ↓
Installs pandas, numpy, bigquery, mcp
     ↓
Installs extension in Claude Desktop
     ↓
Claude Desktop uses bundled venv/bin/python
     ↓
All dependencies available ✅
```

## Installation Steps (For You Right Now)

Since you already have the venv built, you can install directly:

### Remove Old Extension

The old broken extension is still installed:
```bash
rm -rf "/Users/electron/Library/Application Support/Claude/Claude Extensions/local.mcpb.stefan-wojcik.chip50mcp"
```

### Install via Claude Desktop

**Option 1: UI (Easiest)**
1. Open Claude Desktop
2. Settings → Developer → MCP Extensions
3. Add Extension → Point to `/Users/electron/workspace/Nanocentury AI/CHIP50/chip50MCP`
4. Restart Claude Desktop

**Option 2: Config File**
Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "chip50-survey-mcp": {
      "command": "/Users/electron/workspace/Nanocentury AI/CHIP50/chip50MCP/mcp_server/venv/bin/python",
      "args": [
        "/Users/electron/workspace/Nanocentury AI/CHIP50/chip50MCP/mcp_server/server.py"
      ]
    }
  }
}
```

Restart Claude Desktop.

### Verify

Ask Claude:
```
Can you list the available MCP tools?
```

Expected:
- ✅ upload_csv_to_bigquery
- ✅ generate_crosstab
- ✅ get_summary_statistics

## For Future Users (GitHub Clone)

```bash
# Clone
git clone <repo-url>
cd chip50MCP

# Build (creates venv with dependencies)
./build.sh

# Install to Claude Desktop
# (via Settings → Developer → MCP Extensions)

# Or manually edit claude_desktop_config.json
```

## Why This Is Better

| Approach | Result |
|----------|--------|
| `pip install --target=lib` | ❌ Breaks numpy/pandas |
| Bundle complete `venv/` | ✅ Works perfectly |
| Use `uv` with inline deps | ⚠️ Requires uv installed globally |
| **Bundled venv** (our solution) | ✅ Official pattern, self-contained |

## Files Changed

- ✅ `build.sh` - New build script
- ✅ `manifest.json` - Updated to use venv Python
- ✅ `server.py` - Removed uv inline deps, back to simple imports
- ✅ `.gitignore` - Ignores venv/ (built locally)
- ✅ `INSTALLATION.md` - Complete installation guide
- ✅ `SOLUTION.md` - This file

## Testing

The venv is already built and verified:
```bash
✓ Python 3.13.9
✓ pandas 2.3.3
✓ numpy 2.3.5
✓ google-cloud-bigquery 3.38.0
✓ mcp 1.22.0
✓ Server imports successfully
```

## Next Steps

1. **Remove old extension** (see above)
2. **Install via Claude Desktop UI** or config file
3. **Restart Claude Desktop**
4. **Test the tools!**

The ImportError should be completely resolved. 🎉
