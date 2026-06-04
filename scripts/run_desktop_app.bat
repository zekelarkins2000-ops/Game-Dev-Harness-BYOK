@echo off
setlocal
if not exist .venv\Scripts\activate.bat (
  echo Missing .venv. Run scripts\setup_windows.ps1 first.
  exit /b 1
)
call .venv\Scripts\activate.bat
gdh-desktop
