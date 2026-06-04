from __future__ import annotations

import datetime as dt
import json
import math
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol


class ChatClient(Protocol):
    async def chat(self, messages: list[dict[str, str]], model: str | None = None, temperature: float = 0.2) -> str: ...


@dataclass(slots=True)
class MemoryChunk:
    source: str
    heading: str
    text: str
    score: float = 0.0
    kind: str = "markdown"


def _stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def _terms(text: str) -> set[str]:
    stop = {"the", "and", "for", "with", "that", "this", "from", "into", "your", "you", "are", "but", "not", "can", "will", "have", "has", "had", "game", "project", "agent", "harness", "task", "work", "make"}
    return {t for t in re.findall(r"[a-zA-Z0-9_+#.-]{3,}", text.lower()) if t not in stop}


def _tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def _split_md(path: Path, text: str, max_chars: int = 4500) -> list[MemoryChunk]:
    chunks: list[MemoryChunk] = []
    heading = "root"
    current: list[str] = []

    def flush() -> None:
        joined = "\n".join(current).strip()
        if not joined:
            return
        if len(joined) <= max_chars:
            chunks.append(MemoryChunk(path.name, heading, joined))
        else:
            for i in range(0, len(joined), max_chars):
                part = joined[i : i + max_chars].strip()
                if part:
                    chunks.append(MemoryChunk(path.name, f"{heading} part {i // max_chars + 1}", part))

    for line in text.splitlines():
        if line.startswith("#"):
            flush()
            current = [line]
            heading = line.lstrip("#").strip() or "section"
        else:
            current.append(line)
    flush()
    return chunks


class AdvancedProjectMemory:
    """Layered local memory for long-running game/app projects."""

    def __init__(self, workspace: Any):
        self.workspace = workspace
        self.root = workspace.resolve(".harness/memory")
        self.runs = workspace.resolve(".harness/runs")
        self.archive = workspace.resolve(".harness/archive")
        self.index_path = self.root / "index.jsonl"
        self.root.mkdir(parents=True, exist_ok=True)
        self.runs.mkdir(parents=True, exist_ok=True)
        self.archive.mkdir(parents=True, exist_ok=True)

    def ensure(self, project_name: str, engine_profile: str) -> None:
        defaults = {
            "anchors.md": f"# Memory Anchors\n\n- Project name: {project_name}\n- Engine profile: `{engine_profile}`\n- User may have no design or coding skills; outputs must be step-by-step.\n- Never claim tools, SDKs, files, tests, builds, or installs exist unless verified.\n- Do not copy copyrighted/proprietary assets or code.\n- Large work must be split into milestones with acceptance checks.\n",
            "pinned_facts.md": "# Pinned Facts\n\nPin durable user-confirmed facts here with `gdh pin-fact`.\n",
            "compressed_summary.md": "# Compressed Canonical Summary\n\nNo compression has been run yet.\n",
            "project_brief.md": f"# {project_name}\n\nEngine profile: `{engine_profile}`\n\n## Vision\n\nTBD\n",
            "constraints.md": "# Constraints\n\n- BYOK: secrets stay local in `.env`.\n- Prefer small validated milestones over giant rewrites.\n- All uncertain statements must be labeled as assumptions.\n",
            "backlog.md": "# Backlog\n\n## Now\n\n- Define the first playable slice.\n",
            "decisions.md": "# Architecture Decision Records\n\n",
            "qa_log.md": "# QA Log\n\n",
            "contradictions.md": "# Contradictions and Drift Watch\n\nTrack conflicts between new plans, pinned facts, prior decisions, and observed repo state.\n",
            "compression_history.md": "# Compression History\n\n",
        }
        for name, body in defaults.items():
            p = self.root / name
            if not p.exists():
                p.write_text(body, encoding="utf-8")
        if not self.index_path.exists():
            self.rebuild_index()

    def markdown_files(self) -> list[Path]:
        return sorted(p for p in self.root.glob("*.md") if p.is_file())

    def total_chars(self) -> int:
        total = sum(len(p.read_text(encoding="utf-8", errors="replace")) for p in self.markdown_files())
        total += sum(len(p.read_text(encoding="utf-8", errors="replace")) for p in self.runs.glob("*.json"))
        return total

    def needs_compression(self, trigger_chars: int) -> bool:
        return self.total_chars() >= trigger_chars

    def status(self, trigger_chars: int) -> dict[str, Any]:
        archive_runs = self.archive / "runs"
        indexed = sum(1 for _ in self.index_path.open("r", encoding="utf-8")) if self.index_path.exists() else 0
        context = self.context(max_chars=self.total_chars() + 1)
        return {
            "memory_chars": self.total_chars(),
            "estimated_tokens": _tokens(context),
            "compression_trigger_chars": trigger_chars,
            "compression_recommended": self.total_chars() >= trigger_chars,
            "markdown_files": len(self.markdown_files()),
            "active_run_records": len(list(self.runs.glob("*.json"))),
            "archived_run_records": len(list(archive_runs.glob("*.json"))) if archive_runs.exists() else 0,
            "indexed_chunks": indexed,
        }

    def append_note(self, file_name: str, heading: str, body: str) -> Path:
        if not file_name.endswith(".md"):
            file_name += ".md"
        p = self.root / file_name
        with p.open("a", encoding="utf-8") as f:
            f.write(f"\n\n## {heading}\n\n{body.strip()}\n")
        self.rebuild_index()
        return p

    def save_run(self, name: str, data: dict[str, Any]) -> Path:
        p = self.runs / f"{_stamp()}-{name}.json"
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return p

    def context(self, max_chars: int = 80000) -> str:
        priority = ["anchors.md", "pinned_facts.md", "compressed_summary.md", "constraints.md", "decisions.md", "contradictions.md", "backlog.md", "qa_log.md", "project_brief.md"]
        chunks: list[str] = []
        for name in priority:
            p = self.root / name
            if p.exists():
                chunks.append(f"\n\n--- {name} ---\n{p.read_text(encoding='utf-8', errors='replace')}")
        known = {self.root / n for n in priority}
        for p in self.markdown_files():
            if p not in known:
                chunks.append(f"\n\n--- {p.name} ---\n{p.read_text(encoding='utf-8', errors='replace')}")
        return "".join(chunks)[-max_chars:]

    def rebuild_index(self) -> int:
        chunks: list[MemoryChunk] = []
        for p in self.markdown_files():
            chunks.extend(_split_md(p, p.read_text(encoding="utf-8", errors="replace")))
        with self.index_path.open("w", encoding="utf-8") as f:
            for chunk in chunks:
                row = asdict(chunk)
                row["terms"] = sorted(_terms(chunk.heading + "\n" + chunk.text))
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return len(chunks)

    def _load_index(self) -> list[dict[str, Any]]:
        if not self.index_path.exists():
            self.rebuild_index()
        rows: list[dict[str, Any]] = []
        with self.index_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
        return rows

    def retrieve(self, query: str, limit: int = 10) -> list[MemoryChunk]:
        q_terms = _terms(query) or set(query.lower().split())
        bonus = {"anchors.md": 4.0, "pinned_facts.md": 3.5, "compressed_summary.md": 2.5, "decisions.md": 2.0, "constraints.md": 2.0, "contradictions.md": 2.0, "qa_log.md": 1.5, "backlog.md": 1.2}
        chunks: list[MemoryChunk] = []
        for row in self._load_index():
            terms = set(row.get("terms", []))
            score = len(q_terms & terms) * 2.0 + len(q_terms & _terms(row.get("heading", ""))) * 1.5 + bonus.get(row.get("source", ""), 0.0)
            if query.lower() in row.get("text", "").lower():
                score += 5.0
            if score > 0:
                chunks.append(MemoryChunk(row["source"], row["heading"], row["text"], score, row.get("kind", "markdown")))
        chunks.sort(key=lambda c: c.score, reverse=True)
        return chunks[:limit]

    def recent_runs(self, count: int = 3, max_chars_each: int = 7000) -> list[str]:
        rows: list[str] = []
        for p in sorted(self.runs.glob("*.json"), reverse=True)[:count]:
            try:
                data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            except json.JSONDecodeError:
                continue
            rows.append(f"Run: {p.name}\nPrompt: {data.get('prompt', '')}\nSynthesis excerpt:\n{str(data.get('synthesis', ''))[:max_chars_each]}\nAudit excerpt:\n{str(data.get('memory_audit', ''))[:2500]}\n")
        return rows

    def context_bundle(self, query: str, max_chars: int = 72000, retrieval_limit: int = 10, recent_run_count: int = 3) -> str:
        anchors = (self.root / "anchors.md").read_text(encoding="utf-8", errors="replace")
        pinned = (self.root / "pinned_facts.md").read_text(encoding="utf-8", errors="replace")
        summary = (self.root / "compressed_summary.md").read_text(encoding="utf-8", errors="replace")
        contradictions = (self.root / "contradictions.md").read_text(encoding="utf-8", errors="replace")
        retrieved = "\n\n".join(f"### Retrieved: {c.source} :: {c.heading} (score {c.score:.2f})\n{c.text}" for c in self.retrieve(query, retrieval_limit))
        runs = "\n\n".join(self.recent_runs(recent_run_count))
        bundle = f"""# Grounded Context Bundle

## Grounding Contract

- Treat Anchors and Pinned Facts as highest-priority project truth.
- Treat Compressed Canonical Summary as rolling state, but prefer Pinned Facts on conflict.
- Treat Retrieved Memory as relevant supporting context, not proof work is complete.
- Treat Recent Runs as historical context that may contain stale plans.
- Label unsupported details as ASSUMPTION.
- Flag contradictions and ask for verification when memory conflicts with workspace.

## Anchors

{anchors}

## Pinned Facts

{pinned}

## Compressed Canonical Summary

{summary}

## Contradictions / Drift Watch

{contradictions}

## Retrieved Memory for Current Request

{retrieved or 'No specific retrieval hits.'}

## Recent Swarm Runs

{runs or 'No recent runs.'}
"""
        return bundle if len(bundle) <= max_chars else bundle[:max_chars]

    async def compress(self, client: ChatClient, reason: str = "manual compression", keep_recent_runs: int = 8) -> str:
        self.rebuild_index()
        all_memory = self.context(max_chars=180000)
        recent = "\n\n".join(self.recent_runs(keep_recent_runs, max_chars_each=9000))
        prompt = f"""Reason for compression: {reason}

Existing memory:
{all_memory}

Recent runs:
{recent}

Create a durable, anti-hallucination compressed memory snapshot. Preserve confirmed facts, decisions, rejected directions, toolchain assumptions, unresolved questions, current milestone, known bugs, and acceptance criteria. Do not invent facts. Mark uncertain items as UNCERTAIN.
Use this exact structure:
# Compressed Canonical Summary
## Current Project Identity
## Confirmed User Intent
## Pinned Facts To Preserve
## Current Milestone
## Architecture / Engine Decisions
## Gameplay / App Design Decisions
## UI / Art Direction Decisions
## Build / Tooling State
## Known Bugs and QA Findings
## Rejected or Deprecated Directions
## Open Questions
## Retrieval Keywords
## Compression Notes
"""
        snapshot = await client.chat([
            {"role": "system", "content": "You are a memory compression specialist. Reduce context size without losing durable truth. Do not add new facts."},
            {"role": "user", "content": prompt},
        ], temperature=0.05)
        (self.root / "compressed_summary.md").write_text(snapshot.strip() + "\n", encoding="utf-8")
        with (self.root / "compression_history.md").open("a", encoding="utf-8") as f:
            f.write(f"\n\n## {_stamp()} - {reason}\n\n- Input memory chars: {len(all_memory)}\n- Recent run chars: {len(recent)}\n- Output chars: {len(snapshot)}\n")
        self._archive_old_runs(keep_recent_runs)
        self.rebuild_index()
        return snapshot

    def _archive_old_runs(self, keep_recent_runs: int) -> None:
        old = sorted(self.runs.glob("*.json"), reverse=True)[keep_recent_runs:]
        if not old:
            return
        archive_runs = self.archive / "runs"
        archive_runs.mkdir(parents=True, exist_ok=True)
        for p in old:
            shutil.move(str(p), str(archive_runs / p.name))

    async def audit_synthesis(self, client: ChatClient, prompt: str, synthesis: str, context_bundle: str) -> str:
        audit_prompt = f"""User request:
{prompt}

Grounded context:
{context_bundle}

Synthesis to audit:
{synthesis}

Audit for long-project memory drift and hallucinations. Return:
# Memory Audit
## Verdict
PASS, WARN, or FAIL.
## Unsupported Claims
## Contradictions
## Risky Assumptions
## Facts Worth Pinning
## Suggested Memory Updates
"""
        return await client.chat([
            {"role": "system", "content": "You are a strict hallucination and memory-drift auditor. Prefer 'not supported' over guessing."},
            {"role": "user", "content": audit_prompt},
        ], temperature=0.0)
