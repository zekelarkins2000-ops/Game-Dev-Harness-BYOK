# Desktop App

Game Dev Harness BYOK includes a Windows-friendly desktop UI built with CustomTkinter.

## Launch

After setup:

```powershell
gdh-desktop
```

or:

```powershell
gdh ui
```

or:

```powershell
.\scripts\run_desktop_app.bat
```

## What the UI does

The desktop app provides a simple control center for people who do not want to live in the terminal.

It includes:

- project folder picker
- project name field
- engine profile dropdown
- base URL field
- model and fast model fields
- API key field
- swarm selector
- large mission prompt box
- output panel
- save settings button
- initialize/update workspace button
- doctor button
- run swarm button
- compress memory button
- memory status button
- open folder button

## Customization

The UI supports Dark, Light, and System modes; Blue, Violet, Emerald, Orange, Rose, and Slate accents; and 90%, 100%, 110%, and 120% font scale.

UI settings are stored locally in `%APPDATA%\GameDevHarnessBYOK\desktop_settings.json`.

## Recommended workflow

1. Launch `gdh-desktop`.
2. Pick a project folder.
3. Enter your provider details.
4. Choose a profile such as `unity`, `unreal`, `gba`, or `desktop`.
5. Click **Save BYOK Settings**.
6. Click **Initialize / Update Workspace**.
7. Enter a milestone-sized prompt.
8. Click **Run Swarm**.
9. Review the Director synthesis and Memory Audit.
10. Pin durable facts and compress memory when needed.
