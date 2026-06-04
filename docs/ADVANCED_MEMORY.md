# Advanced Memory and Anti-Hallucination System

Long game projects fail when the assistant forgets old decisions, treats stale plans as current truth, or compresses away critical details. Game Dev Harness BYOK uses layered local memory to reduce those failures.

## Memory layers

| Layer | File/location | Purpose |
| --- | --- | --- |
| Anchors | `.harness/memory/anchors.md` | Never-compress project identity, hard rules, and safety constraints |
| Pinned facts | `.harness/memory/pinned_facts.md` | User-confirmed facts that should survive every compression |
| Canonical summary | `.harness/memory/compressed_summary.md` | Rolling compressed source of truth |
| Decisions | `.harness/memory/decisions.md` | Architecture and design decisions |
| Backlog | `.harness/memory/backlog.md` | Current and future work |
| QA log | `.harness/memory/qa_log.md` | Bugs, tests, acceptance checks, memory audits |
| Contradictions | `.harness/memory/contradictions.md` | Drift and conflict watch |
| Index | `.harness/memory/index.jsonl` | Local lexical retrieval index |
| Runs | `.harness/runs/*.json` | Recent swarm records |
| Archive | `.harness/archive/runs/*.json` | Older runs moved out of active context |

## How automatic compression works

Before each swarm, the harness checks active memory size. When the configured threshold is exceeded, it asks the selected BYOK model to rewrite the memory into a structured canonical summary.

The compression prompt preserves confirmed user intent, pinned facts, current milestone, architecture and engine decisions, gameplay/app design decisions, UI/art direction decisions, build/tooling state, known bugs, rejected directions, open questions, and retrieval keywords.

Older run logs are archived after compression so they remain available locally without bloating every future context bundle.

## Retrieval

The harness builds a local markdown chunk index and scores chunks against the current prompt. High-priority files such as anchors, pinned facts, decisions, constraints, contradictions, and compressed summaries receive extra weight.

This is intentionally simple, transparent, and local. It does not require a vector database or a second embedding provider.

## Grounded Context Bundle

Every swarm receives a Grounded Context Bundle that tells agents what is confirmed, what is historical, and what must be labeled as an assumption.

The bundle includes:

- grounding contract
- anchors
- pinned facts
- compressed canonical summary
- contradictions/drift watch
- retrieved relevant memory
- recent swarm runs

## Hallucination audit

After the Director synthesis, the harness can run a memory audit. The audit checks for unsupported claims, contradictions, risky assumptions, facts worth pinning, and suggested memory updates.

The audit is saved to `qa_log.md` and included in the desktop output.

## Commands

```powershell
gdh memory-status
gdh memory-search "combat system"
gdh memory-compress --reason "before vertical slice implementation"
gdh memory-rebuild-index
gdh pin-fact "Engine choice" "The project uses Unity for the first playable."
```

## Best practice for huge projects

Pin anything that must not be forgotten:

```powershell
gdh pin-fact "Scope limit" "The first playable has one map, one player character, one enemy, and one win condition."
```

Run compression before major shifts:

```powershell
gdh memory-compress --reason "before switching from prototype to production milestone"
```

Review status often:

```powershell
gdh memory-status
```
