$ErrorActionPreference = "Stop"

if (!(Test-Path .venv\Scripts\Activate.ps1)) {
  Write-Host "Missing .venv. Running setup first..."
  .\scripts\setup_windows.ps1
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[desktop-build]

gdh-package all

Write-Host ""
Write-Host "If Inno Setup is installed, installer output is in: packaging\out\installer"
Write-Host "If not, use the portable app folder in: packaging\out\dist"
