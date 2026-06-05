# Packaging as a Windows Desktop App

Game Dev Harness BYOK can be packaged like a normal Windows desktop app, similar in spirit to desktop coding tools such as Claude Code/Codex-style launchers.

The repo supports three packaging modes:

1. Portable app folder
2. Single-file executable
3. Windows installer with Start Menu/Desktop shortcuts

## Recommended: portable app folder

From PowerShell:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\scripts\build_desktop_app.ps1
```

Output:

```text
packaging\out\dist\GameDevHarness\GameDevHarness.exe
packaging\out\dist\GameDevHarnessDashboard\GameDevHarnessDashboard.exe
```

You can copy those folders anywhere and run the `.exe` files.

## Create shortcuts

After building:

```powershell
gdh-package shortcut --exe .\packaging\out\dist\GameDevHarness\GameDevHarness.exe
```

This creates Start Menu and Desktop shortcuts by default.

## Build a single executable

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e .[desktop-build]
gdh-package portable --onefile
```

Single-file builds are convenient, but app-folder builds usually start faster and are easier to debug.

## Build a Windows installer

Install Inno Setup first, then run:

```powershell
.\scripts\build_installer.ps1
```

Output:

```text
packaging\out\installer\GameDevHarnessBYOK-Setup.exe
```

The installer includes:

- Game Dev Harness BYOK desktop app
- Game Dev Harness Dashboard
- Start Menu shortcuts
- optional desktop shortcut
- uninstall entry in Windows Apps

## Packaging commands

```powershell
gdh-package portable
gdh-package portable --onefile
gdh-package shortcut --exe .\packaging\out\dist\GameDevHarness\GameDevHarness.exe
gdh-package installer
gdh-package all
```

## Notes

- Your API keys are not bundled into the app.
- The packaged app still stores BYOK provider settings in the selected project’s local `.env` file.
- `.env`, build artifacts, installer outputs, and generated icons are ignored by Git.
- The dashboard can also be launched directly from `GameDevHarnessDashboard.exe`.

## Troubleshooting

If PyInstaller is missing:

```powershell
pip install -e .[desktop-build]
```

If the installer step fails with `ISCC not found`, install Inno Setup or use the portable folder instead.

If Windows SmartScreen warns you, that is expected for an unsigned app. Code signing would require a signing certificate and release signing workflow.
