---
title: Linux Installation
---

# Installing CHIP50 MCP on Linux

Complete installation guide for Linux distributions (Ubuntu, Debian, Fedora, Arch, etc.).

## Prerequisites

### 1. UV Package Manager

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Add to PATH (if not automatic):
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Verify:
```bash
uv --version
```

### 2. Google Cloud SDK

**Ubuntu/Debian:**
```bash
# Add the Cloud SDK distribution URI as a package source
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list

# Import the Google Cloud public key
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -

# Update and install
sudo apt-get update && sudo apt-get install google-cloud-sdk
```

**Fedora/RHEL:**
```bash
sudo tee -a /etc/yum.repos.d/google-cloud-sdk.repo << EOM
[google-cloud-sdk]
name=Google Cloud SDK
baseurl=https://packages.cloud.google.com/yum/repos/cloud-sdk-el8-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=0
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg
       https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
EOM

sudo dnf install google-cloud-sdk
```

**Arch Linux:**
```bash
yay -S google-cloud-sdk
```

**Universal Method:**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

Verify:
```bash
gcloud --version
```

### 3. Authenticate with Google Cloud

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
```bash
git clone https://github.com/nanocentury-ai/chip50MCP.git
cd chip50MCP
```

2. **Edit Claude Desktop config:**
```bash
nano ~/.config/Claude/claude_desktop_config.json
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
        "/home/YOUR_USERNAME/path/to/chip50MCP",
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

## Linux-Specific Notes

### File Locations

- **UV:** `~/.local/bin/uv`
- **Google Cloud config:** `~/.config/gcloud/`
- **Claude Desktop config:** `~/.config/Claude/claude_desktop_config.json`
- **Claude Desktop logs:** `~/.local/share/Claude/logs/`

### Permissions

If you get "permission denied" errors:
```bash
# Make scripts executable
chmod +x install.sh
chmod +x check_install.sh

# Check UV is executable
chmod +x ~/.local/bin/uv
```

### PATH Configuration

Different shells use different config files:

**Bash:**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Zsh:**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Fish:**
```fish
set -Ua fish_user_paths $HOME/.local/bin
```

### SELinux (Fedora/RHEL)

If SELinux is blocking Claude Desktop:
```bash
# Check for denials
sudo ausearch -m avc -ts recent

# If needed, set permissive mode for testing
sudo setenforce 0

# For permanent fix, create a policy module
```

## Troubleshooting

### UV Not Found

```bash
# Check if UV is installed
which uv

# If not found, reinstall
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

### Google Cloud Authentication Issues

```bash
# Re-authenticate
gcloud auth application-default login

# Check project
gcloud config get-value project

# Should show: chip50

# Check credentials file exists
ls -la ~/.config/gcloud/application_default_credentials.json
```

### Claude Desktop Not Starting

```bash
# Check if Claude is installed
which claude

# Check logs for errors
cat ~/.local/share/Claude/logs/main.log

# Try running from terminal to see errors
claude
```

### Claude Desktop Not Finding Server

1. **Check config file exists:**
```bash
cat ~/.config/Claude/claude_desktop_config.json
```

2. **Verify JSON syntax:**
```bash
python3 -m json.tool ~/.config/Claude/claude_desktop_config.json
```

3. **Check permissions:**
```bash
chmod 644 ~/.config/Claude/claude_desktop_config.json
```

4. **Restart Claude Desktop completely:**
```bash
pkill -f claude
claude &
```

### BigQuery Access Denied

```bash
# Verify you have access to the project
gcloud projects list | grep chip50

# Check IAM permissions
gcloud projects get-iam-policy chip50 --flatten="bindings[].members" --filter="bindings.members:user:$(gcloud config get-value account)"

# Test BigQuery access
bq query --use_legacy_sql=false \
  'SELECT COUNT(*) FROM `chip50.public.demographics_protected`'
```

### AppArmor Issues (Ubuntu)

If AppArmor is blocking Claude Desktop:
```bash
# Check for denials
sudo dmesg | grep DENIED

# If needed, disable AppArmor for Claude
sudo aa-complain /path/to/claude
```

## Distribution-Specific Notes

### Ubuntu/Debian
- Claude Desktop may need `libgbm1` and `libasound2`
- Install with: `sudo apt-get install libgbm1 libasound2`

### Fedora/RHEL
- May need `alsa-lib` and `mesa-libgbm`
- Install with: `sudo dnf install alsa-lib mesa-libgbm`

### Arch Linux
- Use AUR for Claude Desktop: `yay -S claude-desktop`
- UV available in AUR: `yay -S uv`

## Next Steps

- [Quick Start Guide](../getting-started/quickstart.md)
- [First Steps](../getting-started/first-steps.md)
- [Troubleshooting Guide](troubleshooting.md)
