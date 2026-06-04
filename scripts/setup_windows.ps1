$ErrorActionPreference = "Stop"

Write-Host "Creating virtual environment..."
python -m venv .venv

Write-Host "Activating virtual environment..."
. .\.venv\Scripts\Activate.ps1

Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

Write-Host "Installing Game Dev Harness BYOK..."
pip install -e .[dev]

Write-Host ""
Write-Host "Setup complete."
Write-Host "Next:"
Write-Host "  copy .env.example .env"
Write-Host "  notepad .env"
Write-Host "  gdh doctor"
