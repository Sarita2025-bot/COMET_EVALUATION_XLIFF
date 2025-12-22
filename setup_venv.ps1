# PowerShell script to set up Python 3.11 virtual environment
# This script creates a virtual environment and installs all required dependencies

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setting up Python 3.11 Virtual Environment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python 3.11 is available
# Try different methods to find Python 3.11
$pythonCmd = $null

# Method 1: Try py launcher with version
try {
    $version = & py -3.11 --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $pythonCmd = "py -3.11"
        Write-Host "Found Python 3.11 via py launcher" -ForegroundColor Green
    }
} catch {}

# Method 2: Try python3.11 directly
if (-not $pythonCmd) {
    try {
        $version = & python3.11 --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pythonCmd = "python3.11"
            Write-Host "Found Python 3.11 via python3.11" -ForegroundColor Green
        }
    } catch {}
}

# Method 3: Check common installation paths
if (-not $pythonCmd) {
    $commonPaths = @(
        "C:\Python311\python.exe",
        "C:\Program Files\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
    )
    
    foreach ($path in $commonPaths) {
        if (Test-Path $path) {
            $pythonCmd = "`"$path`""
            Write-Host "Found Python 3.11 at: $path" -ForegroundColor Green
            break
        }
    }
}

# If Python 3.11 is not found, provide instructions
if (-not $pythonCmd) {
    Write-Host "ERROR: Python 3.11 not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python 3.11 first:" -ForegroundColor Yellow
    Write-Host "1. Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "2. During installation, check 'Add Python to PATH'" -ForegroundColor Yellow
    Write-Host "3. Restart PowerShell after installation" -ForegroundColor Yellow
    Write-Host "4. Run this script again" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Display Python version
Write-Host "Python version:" -ForegroundColor Cyan
& $pythonCmd --version
Write-Host ""

# Remove existing virtual environment if it exists
if (Test-Path ".venv") {
    Write-Host "Removing existing virtual environment..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force .venv
}

# Create virtual environment
Write-Host "Creating virtual environment (.venv)..." -ForegroundColor Cyan
& $pythonCmd -m venv .venv

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor Red
    exit 1
}

Write-Host "Virtual environment created successfully!" -ForegroundColor Green
Write-Host ""

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Could not activate virtual environment automatically" -ForegroundColor Yellow
    Write-Host "You may need to run: .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host ""
}

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Install requirements
Write-Host ""
Write-Host "Installing required packages..." -ForegroundColor Cyan
Write-Host "This may take several minutes (COMET model will be downloaded on first use)..." -ForegroundColor Yellow
python -m pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Setup Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "To activate the virtual environment in the future, run:" -ForegroundColor Cyan
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "Then run the evaluation script:" -ForegroundColor Cyan
    Write-Host "  python run_comet_evaluation.py" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "ERROR: Failed to install requirements" -ForegroundColor Red
    exit 1
}

