---
title: Troubleshooting
---

# Troubleshooting Guide

Common issues and solutions for CHIP50 MCP installation and usage.

## Installation Issues

### UV Not Found

**Symptoms:**
- `command not found: uv` (macOS/Linux)
- `'uv' is not recognized` (Windows)

**Solutions:**

**macOS/Linux:**
```bash
# Check if UV is installed
which uv

# If not found, install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Windows:**
```powershell
# Check if UV is in PATH
where.exe uv

# If not found, reinstall
irm https://astral.sh/uv/install.ps1 | iex

# Restart terminal
```

### Google Cloud SDK Not Found

**Symptoms:**
- `command not found: gcloud`
- Cannot authenticate with BigQuery

**Solutions:**

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
- Download from: [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)
- Or: `choco install gcloudsdk`

### Installation Script Fails

**Symptoms:**
- `Permission denied` errors
- Script won't run

**Solutions:**

**macOS/Linux:**
```bash
# Make script executable
chmod +x install.sh
./install.sh

# If still fails, run with bash explicitly
bash install.sh
```

**Windows:**
```powershell
# Set execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run script
.\install.ps1
```

## Authentication Issues

### Google Cloud Authentication Failed

**Symptoms:**
- `Could not automatically determine credentials`
- `Error 401: Unauthorized`
- BigQuery access denied

**Solutions:**

```bash
# Re-authenticate
gcloud auth application-default login

# Verify project is set
gcloud config set project chip50
gcloud config get-value project

# Check credentials file exists
# macOS/Linux:
ls -la ~/.config/gcloud/application_default_credentials.json

# Windows:
dir $env:APPDATA\gcloud\application_default_credentials.json
```

### Wrong Google Account

**Symptoms:**
- Authentication succeeds but BigQuery access denied
- "Project chip50 not found"

**Solutions:**

```bash
# Check current account
gcloud auth list

# Switch accounts
gcloud config set account YOUR_CORRECT_EMAIL@example.com

# Re-authenticate
gcloud auth application-default login
```

### Missing BigQuery Permissions

**Symptoms:**
- `Access Denied: Project chip50: User does not have permission`

**Solutions:**

Contact the CHIP50 team to grant you access. You need:
- `roles/bigquery.dataViewer` on the `chip50` project
- Or `roles/bigquery.user` with view access to `public` dataset

## Claude Desktop Issues

### MCP Server Not Appearing

**Symptoms:**
- CHIP50 tools not available in Claude Desktop
- No error messages

**Solutions:**

1. **Check config file location:**

**macOS:**
```bash
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Linux:**
```bash
cat ~/.config/Claude/claude_desktop_config.json
```

**Windows:**
```powershell
Get-Content "$env:APPDATA\Claude\claude_desktop_config.json"
```

2. **Verify JSON syntax:**
   - No trailing commas
   - All quotes matched
   - Valid JSON structure
   - Use [jsonlint.com](https://jsonlint.com) to validate

3. **Check path is absolute:**
```json
{
  "mcpServers": {
    "chip50": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/ABSOLUTE/PATH/TO/chip50MCP",  // Must be absolute!
        "python",
        "mcp_server/server.py"
      ]
    }
  }
}
```

4. **Restart Claude Desktop completely:**
   - Quit (don't just close the window)
   - Wait 5 seconds
   - Reopen

### MCP Server Crashes

**Symptoms:**
- Tools appear but calls fail
- "Server disconnected" errors

**Solutions:**

1. **Check Claude Desktop logs:**

**macOS:**
```bash
tail -f ~/Library/Logs/Claude/mcp*.log
```

**Linux:**
```bash
tail -f ~/.local/share/Claude/logs/mcp*.log
```

**Windows:**
```powershell
Get-Content "$env:APPDATA\Claude\logs\mcp*.log" -Tail 50 -Wait
```

2. **Common log errors and fixes:**

**Error:** `ModuleNotFoundError: No module named 'google'`
```bash
# UV should handle this automatically, but try:
uv pip install google-cloud-bigquery
```

**Error:** `FileNotFoundError: server.py`
```bash
# Check the --directory path is correct
# Use absolute path, not relative
```

**Error:** `PermissionError`
```bash
# Make sure Python script is readable
chmod +r mcp_server/server.py
```

### Environment Variables Not Set

**Symptoms:**
- "CHIP50_API_KEY not set" error
- "Missing required environment variable"

**Solutions:**

Ensure environment variables are in Claude Desktop config:

```json
{
  "mcpServers": {
    "chip50": {
      "command": "uv",
      "args": [...],
      "env": {
        "CHIP50_API_KEY": "chip50_test_synthetic_data_only",
        "CHIP50_PROJECT_ID": "chip50",
        "CHIP50_DATASET_PUBLIC": "public"
      }
    }
  }
}
```

## Usage Issues

### "Invalid API Key" Error

**Symptoms:**
- API key validation fails
- Access denied despite correct credentials

**Solutions:**

For testing, use exactly:
```
chip50_test_synthetic_data_only
```

Check there are no:
- Extra spaces
- Quote marks
- Invisible characters

### No Data Returned

**Symptoms:**
- Crosstab generates successfully but shows empty results
- Zero observations

**Possible causes:**

1. **Variable names are case-sensitive:**
```
✗ trust_Congress
✗ Trust_Congress
✓ trust_congress
```

2. **Wave filter excludes all data:**
```python
# Check what waves exist first
get_available_variables()  # Shows: waves [7, 8, 9]

# Don't use waves that don't exist
generate_crosstab(..., waves=[1, 2, 3])  # Returns empty
```

3. **Invalid variable combination:**
```bash
# Check available variables first
get_available_variables()
```

### Too Many Suppressed Cells

**Symptoms:**
- Most cells show `[suppressed]`
- Not enough data to analyze

**Solutions:**

1. **Use broader categories:**
   - Instead of `race` (many categories), try `region` (5 categories)
   - Instead of `age_cat_8` (8 groups), try grouping into fewer buckets

2. **Don't filter to single wave:**
```python
# More data = fewer suppressions
generate_crosstab(..., waves=[7, 8, 9])  # Better

# vs
generate_crosstab(..., waves=[9])  # More suppressions
```

3. **Remember:** Suppression protects privacy. It means the group is too small (<10) to report safely.

### Slow Query Performance

**Symptoms:**
- Queries take >10 seconds
- Claude times out

**Possible causes:**

1. **BigQuery cold start:** First query may be slower
2. **Network latency:** Check internet connection
3. **Large crosstabs:** Many categories = more computation

**Solutions:**

- First query is always slower (warming up)
- Subsequent queries should be faster
- If persistent, check BigQuery quota limits

## Data Issues

### "Protected View Not Found"

**Symptoms:**
- `Table not found: chip50.public.demographics_protected`
- Access denied to protected views

**Solutions:**

1. **Verify views exist:**
```bash
bq ls chip50:public
```

Should show:
- `demographics_protected`
- `survey_responses_protected`

2. **Check permissions:**
```bash
bq show chip50:public.demographics_protected
```

3. **Contact CHIP50 team** if views are missing

### Unexpected Results

**Symptoms:**
- Numbers don't match expectations
- Percentages seem wrong

**Checks:**

1. **Weighted vs unweighted:**
   - By default, results are survey-weighted
   - For raw counts, use `use_weights=false`

2. **Wave filtering:**
   - Check which waves are included
   - Different waves may have different sample compositions

3. **Cell suppression:**
   - Suppressed cells affect totals
   - Percentages calculated from visible cells only

## Platform-Specific Issues

### macOS: Permission Denied

**Symptoms:**
- Can't run scripts
- Can't access files

**Solutions:**

```bash
# Make scripts executable
chmod +x install.sh
chmod +x check_install.sh

# Check file ownership
ls -la

# If needed, fix ownership
chown -R $(whoami) .
```

### Linux: SELinux or AppArmor Blocking

**Symptoms:**
- Claude Desktop won't start
- MCP server crashes
- "Permission denied" in logs

**Solutions:**

**SELinux (Fedora/RHEL):**
```bash
# Check for denials
sudo ausearch -m avc -ts recent

# Temporary: Set permissive
sudo setenforce 0

# Permanent: Create policy module
```

**AppArmor (Ubuntu):**
```bash
# Check for denials
sudo dmesg | grep DENIED

# Temporary: Complain mode
sudo aa-complain /path/to/claude
```

### Windows: Path Issues

**Symptoms:**
- "File not found" errors
- Path with spaces not working

**Solutions:**

1. **Use forward slashes or double backslashes:**
```json
// Good
"C:/Users/John Smith/chip50MCP"
"C:\\Users\\John Smith\\chip50MCP"

// Bad
"C:\Users\John Smith\chip50MCP"
```

2. **Avoid spaces in paths if possible:**
   - Install to `C:/chip50MCP` instead of `C:/My Documents/chip50MCP`

3. **Use quotes in PowerShell:**
```powershell
cd "C:\Users\John Smith\chip50MCP"
```

## Getting More Help

### Check Installation

Run the installation checker:
```bash
./check_install.sh  # macOS/Linux
.\check_install.ps1  # Windows
```

### View Logs

**Claude Desktop logs:**

**macOS:**
```bash
tail -f ~/Library/Logs/Claude/mcp*.log
```

**Linux:**
```bash
tail -f ~/.local/share/Claude/logs/mcp*.log
```

**Windows:**
```powershell
Get-Content "$env:APPDATA\Claude\logs\mcp*.log" -Tail 50 -Wait
```

### Test MCP Server Directly

Test the server outside Claude Desktop:

```bash
cd chip50MCP
uv run mcp_server/server.py

# Should start without errors
# Press Ctrl+C to stop
```

### Contact Support

If none of the above helps:

1. **Check existing issues:** [GitHub Issues](https://github.com/nanocentury-ai/chip50MCP/issues)
2. **Open a new issue:** Include:
   - Operating system and version
   - UV version: `uv --version`
   - Google Cloud SDK version: `gcloud --version`
   - Error messages from logs
   - Steps to reproduce the problem
3. **Discussions:** [GitHub Discussions](https://github.com/nanocentury-ai/chip50MCP/discussions)

## Diagnostic Checklist

Use this checklist to diagnose issues:

- [ ] UV is installed: `uv --version`
- [ ] Google Cloud SDK is installed: `gcloud --version`
- [ ] Authenticated with Google Cloud: `gcloud auth list`
- [ ] Project is set to chip50: `gcloud config get-value project`
- [ ] Can access BigQuery: `bq query "SELECT 1"`
- [ ] Protected views exist: `bq ls chip50:public`
- [ ] Claude Desktop config file exists
- [ ] JSON syntax is valid
- [ ] Path to server.py is absolute
- [ ] Environment variables are set
- [ ] Claude Desktop has been restarted
- [ ] No errors in Claude Desktop logs

If all items are checked and it still doesn't work, [open an issue](https://github.com/nanocentury-ai/chip50MCP/issues/new).
