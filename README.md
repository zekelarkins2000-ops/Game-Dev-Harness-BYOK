# Game Dev Harness BYOK

A Windows 11 friendly, bring-your-own-key AI agent harness for long-form game and app development.

This repo is designed for solo creators who want to drive projects through prompts while the harness keeps durable project memory, specialist sub-agents, engine-specific setup notes, repeatable build commands, QA checkpoints, and automatic anti-hallucination memory compression.

## What it is

Game Dev Harness BYOK is a Python desktop app and CLI that talks to any OpenAI-compatible `/chat/completions` provider using your own API key and base URL. It coordinates a swarm of specialist sub-agents:

- Director
- Producer
- Game Designer
- Technical Architect
- Engine Specialist
- Gameplay Engineer
- UX/UI Artist
- QA Analyst
- Build Engineer
- Researcher
- Memory Auditor

The goal is not one giant magical prompt. The goal is to make large projects survivable by splitting work into small, validated milestones with persistent memory, retrieval, compression, and grounding audits.

## Desktop app

Launch the polished Windows UI after setup with either command:

```powershell
gdh-desktop
```

or:

```powershell
gdh ui
```

Launch the long-horizon dashboard with:

```powershell
gdh-dashboard
```

The desktop app lets you enter your API key, base URL, model, fast model, project folder, engine profile, and swarm. It includes a large mission prompt box, output panel, memory status, manual compression, project initialization, folder opening, and local UI customization.

Customizable UI options:

- Dark, Light, or System appearance
- Blue, Violet, Emerald, Orange, Rose, or Slate accent color
- 90%, 100%, 110%, or 120% font scale

UI settings are stored locally in `%APPDATA%\GameDevHarnessBYOK\desktop_settings.json`. Provider secrets are written only to the selected project’s local `.env`, which is ignored by Git.

## Package it like a normal Windows desktop app

You can build Game Dev Harness BYOK into a desktop executable folder or Windows installer.

Portable app folder:

```powershell
.\scripts\build_desktop_app.ps1
```

Installer build, if Inno Setup is installed:

```powershell
.\scripts\build_installer.ps1
```

Direct packaging commands:

```powershell
gdh-package portable
gdh-package portable --onefile
gdh-package shortcut --exe .\packaging\out\dist\GameDevHarness\GameDevHarness.exe
gdh-package installer
gdh-package all
```

See `docs/PACKAGING_WINDOWS_APP.md` for full packaging instructions.

## Advanced memory system

The harness now uses layered memory instead of simple “last N characters” context.

| Layer | Purpose |
| --- | --- |
| Anchors | never-compress project identity and hard rules |
| Pinned facts | durable user-confirmed facts |
| Compressed canonical summary | rolling source of truth for long projects |
| Markdown memory | backlog, decisions, constraints, QA, contradictions |
| Run records | recent swarm history |
| Retrieval index | prompt-relevant memory chunks |
| Memory audit | hallucination and drift checks |

Every swarm run receives a Grounded Context Bundle that separates confirmed memory, retrieved context, recent run history, assumptions, and contradictions.

Useful commands:

```powershell
gdh memory-status
gdh memory-search "combat system"
gdh memory-compress --reason "before a major milestone"
gdh memory-rebuild-index
gdh pin-fact "Combat scope" "The first playable uses turn-based combat only."
```

## Supported project profiles

| Profile | Purpose |
| --- | --- |
| `generic` | Planning and implementation help for any app/game repo |
| `gba` | GBA ROM/homebrew projects using devkitPro/devkitARM |
| `unity` | Unity projects with batch-mode build hooks |
| `unreal` | Unreal Engine projects using RunUAT/AutomationTool |
| `webapp` | Browser-based games/apps |
| `desktop` | Local Python desktop/tooling apps |

The harness can plan for any engine, but local building still requires the relevant SDK or engine installed on your Windows machine.

## Why this exists

General AI coding apps often struggle with huge solo game projects because they lose context, over-edit too much at once, or skip build validation. This harness is built around:

1. Durable layered memory in `.harness/memory`.
2. Automatic compression with pinned facts and anchors.
3. Retrieval-scored context bundles.
4. Sub-agent swarms for design, architecture, engineering, QA, build, UX, and memory auditing.
5. Milestone-based execution instead of endless one-shot code generation.
6. BYOK provider config so you can choose your model, key, and base URL.
7. Windows-first setup with PowerShell scripts, desktop UI, dashboard, and engine doctor checks.

## Windows 11 setup

### 1. Install prerequisites

Install:

- Python 3.11 or newer
- Git for Windows
- Optional for GBA: devkitPro/devkitARM
- Optional for Unity: Unity Hub + the Unity Editor version for your project
- Optional for Unreal: Unreal Engine 5.x

### 2. Clone the repo

```powershell
git clone https://github.com/zekelarkins2000-ops/Game-Dev-Harness-BYOK.git
cd Game-Dev-Harness-BYOK
```

### 3. Run the setup script

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\scripts\setup_windows.ps1
```

Manual equivalent:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev]
```

### 4. Launch the desktop app

```powershell
gdh-desktop
```

or:

```powershell
.\scripts\run_desktop_app.bat
```

### 5. Add your key and provider

You can do this in the desktop app, or manually copy `.env.example` to `.env`:

```powershell
copy .env.example .env
notepad .env
```

Set:

```text
GDH_API_KEY=your-key
GDH_BASE_URL=https://your-provider.example/v1
GDH_MODEL=your-model
GDH_FAST_MODEL=your-cheaper-model-if-any
```

`.env` is ignored by Git.

### 6. Check your machine

```powershell
gdh doctor
```

### 7. Initialize a game/app workspace

```powershell
gdh init --name "My Dream Game" --profile unity --base-url "https://api.openai.com/v1" --model "gpt-5.5"
```

For GBA:

```powershell
gdh init --name "Pocket Quest" --profile gba
```

For Unreal:

```powershell
gdh init --name "Large Scale Shooter" --profile unreal
```

### 8. Run the agent swarm

```powershell
gdh start "Create the first playable milestone for a tactical 4v4 esports manager game with a simulated live match viewer." --swarm studio
```

For a GBA-focused swarm:

```powershell
gdh start "Make a top-down monster catching RPG first playable for GBA with original region, original characters, and placeholder sprites." --swarm gba
```

## Long-horizon toolkit

```powershell
gdh-long roadmap-add-epic "First Playable"
gdh-long roadmap-add-milestone "Vertical Slice"
gdh-long roadmap-add-task "Add player movement" --acceptance "Player moves; Build succeeds; QA notes recorded"
gdh-long build-run
gdh-long docs-generate
```

See `docs/LONG_HORIZON_DEVELOPMENT.md` for the full workflow.

## How to use it for very large projects

Use this loop:

1. Prompt for a milestone, not the whole game.
2. Let the swarm create a plan and acceptance checks.
3. Pin durable facts with `gdh pin-fact`.
4. Ask it to implement only the next work package.
5. Run the build/test command.
6. Paste failures back into `gdh start`.
7. Compress memory before major shifts or when `gdh memory-status` recommends it.
8. Keep going.

Useful commands:

```powershell
gdh resume
gdh add-note decisions.md "Combat scope" "The first playable uses turn-based combat only."
gdh start "Continue from memory. Implement the next smallest task and include exact files to change."
```

## Swarm modes

| Swarm | Best for |
| --- | --- |
| `studio` | Full game/app milestones |
| `minimal` | Smaller code tasks |
| `gba` | ROM/homebrew projects |
| `research-heavy` | Engine/API research before risky work |

## Repository structure

```text
game_dev_harness/       Python package, CLI, memory system, desktop UI, dashboard, packaging
docs/                   Architecture and usage documentation
scripts/                Windows helpers and build scripts
packaging/              Installer, shortcut, and PyInstaller helper files
examples/prompts/       Starter prompts
```

## Safety and legality

This project does not include Nintendo, Unity, Unreal, Activision, Pokémon, or other third-party copyrighted assets. It is meant to generate original projects or work on projects you have rights to modify.

For ROM development, use homebrew tooling and original assets/code. Do not use this harness to distribute copyrighted ROMs or proprietary game data.

## License

MIT. See [LICENSE](LICENSE).
