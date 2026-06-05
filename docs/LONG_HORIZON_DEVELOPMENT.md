# Long-Horizon Game Development Toolkit

This toolkit turns Game Dev Harness BYOK into a more complete solo game/app production environment.

Launch commands with:

```powershell
gdh-long --help
```

or:

```powershell
.\scripts\run_long_horizon.bat --help
```

## What it adds

| Area | Commands / files |
| --- | --- |
| Roadmap | `.harness/roadmap.json`, `roadmap-*` commands |
| Definition of done | stored in roadmap and included in exports |
| Assets | `.harness/assets_manifest.json`, `asset-*` commands |
| Visual QA | `.harness/visual_qa`, `visual-qa-*` commands |
| Builds and tests | `.harness/build_logs`, `build-run`, `run-command` |
| Engine doctors | `doctor-profile` |
| Patch safety | `.harness/patches`, `patch-apply` |
| Snapshots | `.harness/snapshots`, `snapshot-*` commands |
| Living docs | `docs-generate` creates GDD, TDD, roadmap, QA, art, build docs |
| Plugins | `plugins/<name>/plugin.json`, `plugin-*` commands |
| Knowledge packs | `knowledge/*.md`, `knowledge-*` commands |

## Recommended loop

```powershell
gdh-long roadmap-add-epic "First Playable"
gdh-long roadmap-add-milestone "Vertical Slice"
gdh-long roadmap-add-task "Create player movement" --acceptance "Player moves; Build succeeds; QA notes recorded"
gdh start "Use the roadmap and implement the next smallest safe task." --swarm vertical-slice-swarm
gdh-long build-run
gdh-long docs-generate
```

## Roadmap commands

```powershell
gdh-long roadmap-init
gdh-long roadmap-add-epic "Core Loop"
gdh-long roadmap-add-milestone "First Playable"
gdh-long roadmap-add-task "Add inventory menu" --acceptance "Opens; Closes; Empty state works; Build succeeds"
gdh-long roadmap-next
gdh-long roadmap-update-task task-12345678 --status verified --confidence verified_by_test
gdh-long roadmap-export
```

Task statuses:

- `planned`
- `in_progress`
- `blocked`
- `implemented`
- `verified`
- `rejected`
- `deprecated`

Confidence states:

- `confirmed`
- `assumption`
- `stale`
- `deprecated`
- `contradicted`
- `needs_verification`
- `verified_by_build`
- `verified_by_test`

## Assets

```powershell
gdh-long asset-add "Player idle sprite" sprite --status placeholder --notes "Temporary 16x16 sprite"
gdh-long asset-list
gdh-long asset-update asset-12345678 --status final
```

Use this for sprites, animations, UI screens, shaders, sounds, music, characters, maps, icons, and promotional assets.

## Visual QA

```powershell
gdh-long visual-qa-add .\screenshots\bad-menu.png "Inventory menu alignment issue" --notes "Buttons overflow at 1080p" --severity high
gdh-long visual-qa-list
```

Screenshots are copied into `.harness/visual_qa/screenshots` and indexed in `.harness/visual_qa/issues.json`.

## Build and command runner

```powershell
gdh-long doctor-profile
gdh-long build-run
gdh-long run-command "pytest"
```

Logs are written to `.harness/build_logs`.

Default build commands exist for:

- Unity
- Unreal
- GBA/devkitPro
- webapp
- desktop

## Patches and snapshots

Before risky changes:

```powershell
gdh-long snapshot-create "before combat rewrite"
gdh-long snapshot-list
```

To apply a git patch safely:

```powershell
gdh-long patch-apply .\change.patch
gdh-long patch-apply .\change.patch --commit
```

Patch application first runs `git apply --check` before applying.

## Living docs

```powershell
gdh-long docs-generate
```

Generates or refreshes:

- `docs/GDD.md`
- `docs/TDD.md`
- `docs/ROADMAP.md`
- `docs/BUILD_AND_RELEASE.md`
- `docs/ART_DIRECTION.md`
- `docs/QA_PLAN.md`

## Plugins and knowledge packs

```powershell
gdh-long plugin-create godot "Godot build and validation helpers"
gdh-long plugin-list
gdh-long knowledge-list
gdh-long knowledge-show gba_homebrew.md
```

Knowledge packs are local markdown files in `knowledge/` and can be expanded per engine or release target.

## How this helps long projects

The harness no longer relies only on chat history. It has durable project state, task status, acceptance checks, asset tracking, visual QA, build logs, snapshots, and living documents that survive model context windows and session boundaries.
