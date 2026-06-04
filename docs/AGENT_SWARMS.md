# Sub-Agent Swarms

A swarm is a coordinated set of specialist prompts. Each sub-agent sees the same user request, current memory, and workspace file list, but responds from a specific professional role.

## Built-in swarms

### `studio`

Full game/app team:

- Director
- Producer
- Game Designer
- Technical Architect
- Engine Specialist
- Gameplay Engineer
- UX/UI Artist
- QA Analyst
- Build Engineer

### `minimal`

Small focused code tasks:

- Director
- Technical Architect
- Gameplay Engineer
- QA Analyst

### `gba`

Homebrew/ROM-scale project planning:

- Director
- Producer
- Game Designer
- Technical Architect
- Engine Specialist
- Gameplay Engineer
- QA Analyst
- Build Engineer

### `research-heavy`

Used before risky engine/API work:

- Director
- Researcher
- Producer
- Technical Architect
- Engine Specialist
- QA Analyst

## Why swarms matter

Large solo game development requires different kinds of thinking. The Designer protects fun, the Architect protects maintainability, the Engineer implements, the QA Analyst catches regressions, the Build Engineer keeps the project runnable, and the Director prevents scope explosion.
