# CHIP50 MCP Bundle - Windows PowerShell Installer
# Installs Python dependencies and configures Claude Desktop automatically

#Requires -Version 5.1

# Configuration
$BundleName = "chip50-survey-mcp"
$Version = "2.0.0"
$McpbFile = "$BundleName-v$Version.mcpb"
$InstallDir = "$env:USERPROFILE\.chip50"
$ConfigFile = "$InstallDir\config.json"

# Colors
$ColorSuccess = "Green"
$ColorError = "Red"
$ColorWarning = "Yellow"
$ColorInfo = "Cyan"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "CHIP50 Survey MCP - Installation" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Helper functions
function Print-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor $ColorSuccess
}

function Print-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor $ColorError
}

function Print-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor $ColorWarning
}

function Print-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor $ColorInfo
}

# Check if command exists
function Test-CommandExists {
    param([string]$Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

# Step 1: Check prerequisites
function Check-Prerequisites {
    Write-Host ""
    Write-Host "[1/6] Checking prerequisites..." -ForegroundColor Cyan
    Write-Host ""

    # Check Python
    if (Test-CommandExists python) {
        $PythonVersion = (python --version 2>&1) -replace "Python ", ""
        Print-Success "Python found: $PythonVersion"

        # Check Python version >= 3.10
        $versionParts = $PythonVersion -split "\."
        $major = [int]$versionParts[0]
        $minor = [int]$versionParts[1]

        if (($major -gt 3) -or (($major -eq 3) -and ($minor -ge 10))) {
            Print-Success "Python version is 3.10 or higher"
        } else {
            Print-Warning "Python 3.10+ recommended (found $PythonVersion)"
        }
    } else {
        Print-Error "Python not found. Please install Python 3.10+ first."
        Write-Host ""
        Write-Host "Download from: https://www.python.org/downloads/"
        Write-Host "Or install with: winget install Python.Python.3.11"
        exit 1
    }

    # Check UV
    if (Test-CommandExists uv) {
        $UvVersion = (uv --version 2>&1)
        Print-Success "UV found: $UvVersion"
    } else {
        Print-Warning "UV not found. Installing UV..."

        # Install UV
        try {
            irm https://astral.sh/uv/install.ps1 | iex

            # Add UV to PATH for this session
            $env:Path += ";$env:USERPROFILE\.cargo\bin"

            if (Test-CommandExists uv) {
                Print-Success "UV installed successfully"
            } else {
                Print-Error "UV installation failed. Please restart PowerShell and try again."
                exit 1
            }
        } catch {
            Print-Error "Failed to install UV: $_"
            exit 1
        }
    }

    # Check gcloud
    if (Test-CommandExists gcloud) {
        Print-Success "Google Cloud SDK found"
    } else {
        Print-Warning "Google Cloud SDK not found"
        Write-Host ""
        Write-Host "You'll need to install Google Cloud SDK to use this MCP server."
        Write-Host ""
        Write-Host "Download from: https://cloud.google.com/sdk/docs/install"
        Write-Host "Or install with: choco install gcloudsdk"
        Write-Host ""
        $response = Read-Host "Continue anyway? (y/n)"
        if ($response -ne "y") {
            exit 1
        }
    }

    Print-Success "Prerequisites check complete"
}

# Step 2: Check for bundle file
function Check-Bundle {
    Write-Host ""
    Write-Host "[2/6] Checking for bundle file..." -ForegroundColor Cyan
    Write-Host ""

    if (Test-Path $McpbFile) {
        Print-Success "Bundle found: $McpbFile"
    } else {
        Print-Error "Bundle file not found: $McpbFile"
        Write-Host ""
        Write-Host "Please download the bundle from:"
        Write-Host "  https://github.com/nanocentury-ai/chip50MCP/releases/latest"
        Write-Host ""
        Write-Host "Or build it with:"
        Write-Host "  .\build_mcpb.sh (in Git Bash or WSL)"
        exit 1
    }
}

# Step 3: Install Python dependencies
function Install-Dependencies {
    Write-Host ""
    Write-Host "[3/6] Installing Python dependencies..." -ForegroundColor Cyan
    Write-Host ""

    # Create install directory
    if (-not (Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }

    # Create virtual environment with UV
    Print-Info "Creating virtual environment..."
    & uv venv "$InstallDir\venv" --python python3.10 2>&1 | Out-Null

    # Install dependencies
    Print-Info "Installing dependencies..."
    & uv pip install --quiet --python "$InstallDir\venv\Scripts\python.exe" `
        "pandas>=2.0.0" `
        "google-cloud-bigquery>=3.11.0" `
        "db-dtypes>=1.1.0" `
        "mcp>=0.9.0"

    Print-Success "Dependencies installed"
}

# Step 4: Setup Google Cloud authentication
function Setup-GcloudAuth {
    Write-Host ""
    Write-Host "[4/6] Setting up Google Cloud authentication..." -ForegroundColor Cyan
    Write-Host ""

    if (Test-CommandExists gcloud) {
        # Check if already authenticated
        $authCheck = & gcloud auth application-default print-access-token 2>&1
        if ($LASTEXITCODE -eq 0) {
            Print-Success "Already authenticated with Google Cloud"
        } else {
            Print-Warning "Not authenticated with Google Cloud"
            Write-Host ""
            $response = Read-Host "Would you like to authenticate now? (y/n)"
            if ($response -eq "y") {
                & gcloud auth application-default login
                & gcloud config set project chip50
                Print-Success "Authentication complete"
            } else {
                Print-Warning "Skipping authentication. You'll need to run:"
                Write-Host "  gcloud auth application-default login"
                Write-Host "  gcloud config set project chip50"
            }
        }
    } else {
        Print-Warning "Google Cloud SDK not installed, skipping authentication"
    }
}

# Step 5: Create configuration
function Create-Config {
    Write-Host ""
    Write-Host "[5/6] Creating configuration..." -ForegroundColor Cyan
    Write-Host ""

    # Create install directory
    if (-not (Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }

    # Extract bundle to install directory
    Print-Info "Extracting bundle..."
    $bundleDir = "$InstallDir\bundle"
    if (Test-Path $bundleDir) {
        Remove-Item -Path $bundleDir -Recurse -Force
    }
    Expand-Archive -Path $McpbFile -DestinationPath $bundleDir -Force

    # Create config file
    $configData = @{
        version = $Version
        install_date = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        bundle_path = $bundleDir
        venv_path = "$InstallDir\venv"
        api_key = "chip50_test_synthetic_data_only"
        project_id = "chip50"
        dataset_public = "public"
        min_cell_size = 10
    }

    $configData | ConvertTo-Json | Set-Content -Path $ConfigFile

    Print-Success "Configuration created at $ConfigFile"
}

# Step 6: Configure Claude Desktop
function Configure-ClaudeDesktop {
    Write-Host ""
    Write-Host "[6/6] Configuring Claude Desktop..." -ForegroundColor Cyan
    Write-Host ""

    # Claude Desktop config location
    $ClaudeConfigDir = "$env:APPDATA\Claude"
    $ClaudeConfigFile = "$ClaudeConfigDir\claude_desktop_config.json"

    # Check if Claude Desktop is installed
    if (-not (Test-Path $ClaudeConfigDir)) {
        Print-Warning "Claude Desktop config directory not found"
        Write-Host ""
        Write-Host "Claude Desktop may not be installed yet."
        Write-Host "After installing Claude Desktop, you can manually add the server configuration."
        Write-Host ""
        Write-Host "Config location: $ClaudeConfigFile"
        Write-Host ""
        Print-ManualConfig
        return
    }

    # Create config directory if needed
    if (-not (Test-Path $ClaudeConfigDir)) {
        New-Item -ItemType Directory -Path $ClaudeConfigDir -Force | Out-Null
    }

    # Check if config file exists
    if (-not (Test-Path $ClaudeConfigFile)) {
        # Create new config
        $pythonPath = "$InstallDir\venv\Scripts\python.exe" -replace "\\", "/"
        $serverPath = "$InstallDir\bundle\mcp_server\server.py" -replace "\\", "/"

        $config = @{
            mcpServers = @{
                chip50 = @{
                    command = $pythonPath
                    args = @($serverPath)
                    env = @{
                        CHIP50_API_KEY = "chip50_test_synthetic_data_only"
                        CHIP50_PROJECT_ID = "chip50"
                        CHIP50_DATASET_PUBLIC = "public"
                        CHIP50_MIN_CELL_SIZE = "10"
                    }
                }
            }
        }

        $config | ConvertTo-Json -Depth 10 | Set-Content -Path $ClaudeConfigFile
        Print-Success "Created Claude Desktop configuration"
    } else {
        Print-Warning "Claude Desktop config already exists"
        Write-Host ""
        Write-Host "Please manually add the following to your Claude Desktop config:"
        Write-Host ""
        Print-ManualConfig
    }
}

# Print manual configuration instructions
function Print-ManualConfig {
    $pythonPath = "$InstallDir\venv\Scripts\python.exe" -replace "\\", "/"
    $serverPath = "$InstallDir\bundle\mcp_server\server.py" -replace "\\", "/"

    Write-Host "Add this to your Claude Desktop config:"
    Write-Host ""
    Write-Host @"
{
  "mcpServers": {
    "chip50": {
      "command": "$pythonPath",
      "args": [
        "$serverPath"
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
"@
    Write-Host ""
}

# Main installation flow
function Main {
    Check-Prerequisites
    Check-Bundle
    Install-Dependencies
    Setup-GcloudAuth
    Create-Config
    Configure-ClaudeDesktop

    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "✓ Installation Complete!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""

    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Restart Claude Desktop (if running)"
    Write-Host "2. Verify the CHIP50 MCP server appears in Settings → MCP Servers"
    Write-Host "3. Test by asking Claude: 'What variables are available in CHIP50?'"
    Write-Host ""

    Write-Host "Configuration:" -ForegroundColor Cyan
    Write-Host "  Install directory: $InstallDir"
    Write-Host "  Config file: $ConfigFile"
    Write-Host "  Virtual environment: $InstallDir\venv"
    Write-Host ""

    Write-Host "Google Cloud:" -ForegroundColor Cyan
    if (Test-CommandExists gcloud) {
        $authCheck = & gcloud auth application-default print-access-token 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Status: ✓ Authenticated" -ForegroundColor Green
        } else {
            Write-Host "  Status: ⚠ Not authenticated" -ForegroundColor Yellow
            Write-Host "  Run: gcloud auth application-default login"
        }
    } else {
        Write-Host "  Status: ⚠ Google Cloud SDK not installed" -ForegroundColor Yellow
    }
    Write-Host ""

    Write-Host "Documentation:" -ForegroundColor Cyan
    Write-Host "  Quick Start: $InstallDir\bundle\QUICKSTART.md"
    Write-Host "  Setup Guide: $InstallDir\bundle\SETUP.md"
    Write-Host ""
    Write-Host "Need help? Check the documentation or report issues at:"
    Write-Host "  https://github.com/nanocentury-ai/chip50MCP/issues"
    Write-Host ""
}

# Run installation
try {
    Main
} catch {
    Write-Host ""
    Print-Error "Installation failed: $_"
    Write-Host ""
    Write-Host "Stack trace:" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace
    exit 1
}
