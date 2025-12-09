# CHIP50 Survey MCP - Installation Guide

## Overview

This MCP server uses a **bundled virtual environment** approach (following the official Anthropic pattern) to ensure all Python dependencies work correctly, including compiled packages like numpy and pandas.

## Quick Start

### 1. Clone and Build

```bash
# Clone the repository
git clone <repository-url>
cd chip50MCP

# Run the build script to create the venv and install dependencies
./build.sh
```

The build script will:
- Create a Python virtual environment in `mcp_server/venv/`
- Install pandas, numpy, google-cloud-bigquery, and mcp
- Verify all dependencies are working
- Take ~2-3 minutes and create ~220MB of files

### 2. Install to Claude Desktop

**Option A: Via Claude Desktop UI (Recommended)**

1. Open Claude Desktop
2. Go to **Settings → Developer → MCP Extensions**
3. Click **Add Extension**
4. Point to the `chip50MCP` directory
5. Restart Claude Desktop

**Option B: Via Config File**

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "chip50-survey-mcp": {
      "command": "/ABSOLUTE/PATH/TO/chip50MCP/mcp_server/venv/bin/python",
      "args": [
        "/ABSOLUTE/PATH/TO/chip50MCP/mcp_server/server.py"
      ]
    }
  }
}
```

Replace `/ABSOLUTE/PATH/TO/` with your actual path.

Then restart Claude Desktop.

### 3. Verify Installation

In Claude Desktop, ask:
```
Can you list the available MCP tools?
```

You should see:
- `upload_csv_to_bigquery`
- `generate_crosstab`
- `get_summary_statistics`

## Build Script Usage

```bash
# Build with existing venv (fast, updates dependencies)
./build.sh

# Clean rebuild (removes and recreates venv)
./build.sh --clean
```

## How It Works

The installation uses the **official Anthropic pattern** from their file-manager-python example:

1. **`manifest.json`** - Tells Claude Desktop how to run the extension
2. **`mcp_server/venv/`** - Bundled virtual environment with all dependencies
3. **`mcp_server/server.py`** - The MCP server code

Key part of `manifest.json`:
```json
{
  "server": {
    "type": "python",
    "entry_point": "mcp_server/server.py",
    "mcp_config": {
      "command": "${__dirname}/mcp_server/venv/bin/python",
      "args": ["${__dirname}/mcp_server/server.py"]
    }
  }
}
```

This ensures the bundled Python interpreter (with all dependencies) is used.

## Why This Approach?

**Previous approach (failed):** Bundle deps to `lib/` using `pip install --target`
- ❌ Doesn't work with compiled packages (numpy, pandas)
- ❌ ImportError on numpy

**Current approach:** Bundle complete virtual environment
- ✅ Works with all packages including compiled ones
- ✅ Official Anthropic pattern
- ✅ Isolated from system Python
- ✅ Reproducible builds

## Troubleshooting

### Build fails with "python3: command not found"

Install Python 3.8 or later:
```bash
# macOS
brew install python3

# Check version
python3 --version
```

### "No module named 'pandas'" error

The venv wasn't created or dependencies weren't installed. Run:
```bash
./build.sh --clean
```

### Claude Desktop doesn't see the extension

1. Check the `manifest.json` is in the root directory
2. Verify the venv exists: `ls -la mcp_server/venv/bin/python`
3. Check Claude Desktop logs:
   ```bash
   tail -f ~/Library/Logs/Claude/mcp*.log
   ```

### Extension installs but tools don't work

Test the server directly:
```bash
cd mcp_server
./venv/bin/python server.py
```

It should wait for stdio input (that's correct). Press Ctrl+C to exit.

If you see import errors, rebuild:
```bash
./build.sh --clean
```

## For Developers

### Project Structure

```
chip50MCP/
├── manifest.json          # Claude Desktop extension manifest
├── build.sh              # Build script (creates venv)
├── mcp_server/
│   ├── server.py         # MCP server implementation
│   ├── venv/             # Bundled virtual environment (gitignored)
│   │   ├── bin/
│   │   │   └── python    # Python interpreter with deps
│   │   └── lib/
│   │       └── python3.X/
│   │           └── site-packages/  # pandas, numpy, etc.
│   └── pyproject.toml    # Python package metadata
├── synthetic_data/       # Test data
└── test_mcp_server.py   # Test suite
```

### Adding Dependencies

1. Edit `build.sh` and add to the pip install line:
   ```bash
   "$VENV_DIR/bin/pip" install pandas numpy google-cloud-bigquery mcp YOUR_PACKAGE --quiet
   ```

2. Rebuild:
   ```bash
   ./build.sh --clean
   ```

3. Test:
   ```bash
   ./mcp_server/venv/bin/python -c "import YOUR_PACKAGE"
   ```

### Testing Changes

```bash
# Test server imports
./mcp_server/venv/bin/python mcp_server/server.py

# Run test suite
python3 test_mcp_server.py

# Test in Claude Desktop
# (just restart Claude Desktop after making changes)
```

## Git and Version Control

The `venv/` directory is **gitignored** (it's ~220MB and platform-specific).

**When sharing/deploying:**
1. Clone the repo
2. Run `./build.sh`
3. The venv will be created locally

**When updating from git:**
```bash
git pull
./build.sh  # Update dependencies if needed
```

## Reference

- [Official Anthropic MCP example](https://github.com/modelcontextprotocol/mcpb/tree/main/examples/file-manager-python)
- [MCP Documentation](https://modelcontextprotocol.io)
- See `QUICKSTART.md` for usage examples
- See `README.md` for tool documentation
