# Game Dev Harness BYOK

A Windows 11 friendly, bring-your-own-key AI agent harness for long-form game and app development.

This repo is designed for solo creators who want to drive projects through prompts while the harness keeps durable project memory, specialist sub-agents, engine-specific setup notes, repeatable build commands, and QA checkpoints.

## What it is

Game Dev Harness BYOK is a Python CLI that talks to any OpenAI-compatible `/chat/completions` provider using your own API key and base URL. It coordinates a swarm of specialist sub-agents:

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

The goal is not one giant magical prompt. The goal is to make large projects survivable by splitting work into small, validated milestones with persistent memory.

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

1. Durable memory in `.harness/memory`.
2. Sub-agent swarms for design, architecture, engineering, QA, build, and UX.
3. Milestone-based execution instead of endless one-shot code generation.
4. BYOK provider config so you can choose your model, key, and base URL.
5. Windows-first setup with PowerShell scripts and engine doctor checks.

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

### 4. Add your key and provider

Copy `.env.example` to `.env`:

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

### 5. Check your machine

```powershell
gdh doctor
```

### 6. Initialize a game/app workspace

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

### 7. Run the agent swarm

```powershell
gdh start "Create the first playable milestone for a tactical 4v4 esports manager game with a simulated live match viewer." --swarm studio
```

For a GBA-focused swarm:

```powershell
gdh start "Make a top-down monster catching RPG first playable for GBA with original region, original characters, and placeholder sprites." --swarm gba
```

## How to use it for very large projects

Use this loop:

1. Prompt for a milestone, not the whole game.
2. Let the swarm create a plan and acceptance checks.
3. Ask it to implement only the next work package.
4. Run the build/test command.
5. Paste failures back into `gdh start`.
6. Keep going.

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
game_dev_harness/       Python package
docs/                   Architecture and usage documentation
scripts/                Windows helpers
examples/prompts/       Starter prompts
```

## Safety and legality

This project does not include Nintendo, Unity, Unreal, Activision, Pokémon, or other third-party copyrighted assets. It is meant to generate original projects or work on projects you have rights to modify.

For ROM development, use homebrew tooling and original assets/code. Do not use this harness to distribute copyrighted ROMs or proprietary game data.

## License

MIT. See [LICENSE](LICENSE).
