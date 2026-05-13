# Convenience launcher for Windows PowerShell.
# Usage:  .\run.ps1
$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
pip install --upgrade pip | Out-Null
pip install -r requirements.txt
streamlit run app.py
