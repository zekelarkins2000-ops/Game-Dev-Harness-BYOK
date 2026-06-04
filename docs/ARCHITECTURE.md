# Architecture

Game Dev Harness BYOK has five core layers.

## 1. CLI

`game_dev_harness.cli` exposes:

- `gdh init`
- `gdh doctor`
- `gdh start`
- `gdh resume`
- `gdh add-note`

## 2. Provider layer

The harness calls an OpenAI-compatible `/chat/completions` endpoint with:

- `GDH_API_KEY`
- `GDH_BASE_URL`
- `GDH_MODEL`
- optional `GDH_FAST_MODEL`

The harness does not require a specific vendor.

## 3. Durable memory

`.harness/memory` stores:

- `project_brief.md`
- `constraints.md`
- `backlog.md`
- `decisions.md`
- `qa_log.md`

`.harness/runs` stores JSON records for every swarm run.

## 4. Swarm orchestration

`SwarmRunner` loads project memory and current files, runs specialist roles concurrently, then asks the Director to synthesize a single plan.

## 5. Workspace safety

The workspace wrapper keeps file operations rooted in the selected project directory and avoids path traversal.

## Long project strategy

The harness is intentionally milestone-first:

1. Understand.
2. Design.
3. Technical plan.
4. Implementation plan.
5. QA plan.
6. Director synthesis.
7. Save memory.
8. Repeat.
