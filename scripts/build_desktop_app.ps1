$ErrorActionPreference = "Stop"

if (!(Test-Path .venv\Scripts\Activate.ps1)) {
  Write-Host "Missing .venv. Running setup first..."
  .\scripts\setup_windows.ps1
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[desktop-build]

gdh-package portable

Write-Host ""
Write-Host "Portable desktop app built at: packaging\out\dist\GameDevHarness"
Write-Host "Dashboard built at: packaging\out\dist\GameDevHarnessDashboard"
