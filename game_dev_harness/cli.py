from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import httpx
import typer
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

from .memory import AdvancedProjectMemory

app = typer.Typer(help="Game Dev Harness BYOK: long-form AI agent harness for game/app projects.")
console = Console()
ENGINE_PROFILES = {"generic", "gba", "unity", "unreal", "webapp", "desktop"}


class ProviderConfig(BaseModel):
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-5.5"
    fast_model: str | None = None
    api_key_env: str = "GDH_API_KEY"
    timeout_seconds: int = 120
    max_retries: int = 2


class HarnessConfig(BaseModel):
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    default_swarm: str = "studio"
    max_parallel_agents: int = 4
    require_confirm_before_shell: bool = True
    project_name: str = "Untitled Game"
    engine_profile: str = "generic"
    memory_token_budget: int = 18000
    auto_compress_memory: bool = True
    compression_trigger_chars: int = 140000
    compression_keep_recent_runs: int = 8
    retrieval_max_chunks: int = 10
    recent_run_context_count: int = 3
    hallucination_audit: bool = True
    strict_grounding: bool = True


@dataclass(slots=True)
class AgentRole:
    name: str
    mission: str
    responsibilities: list[str]
    model_hint: str = "default"


CORE_ROLES: dict[str, AgentRole] = {
    "director": AgentRole("Director", "Own product vision and align the swarm.", ["Convert vague prompts into milestones.", "Reject scope that breaks the milestone.", "Separate confirmed memory from assumptions."]),
    "producer": AgentRole("Producer", "Break long projects into safe work packages.", ["Maintain milestone plan and acceptance criteria.", "Detect blockers early.", "Keep stale tasks from resurfacing."]),
    "designer": AgentRole("Game Designer", "Design mechanics, loops, economy, onboarding, progression, and player experience.", ["Write implementable design specs.", "Prefer prototype-first design.", "Mark canon, placeholders, and experiments separately."]),
    "architect": AgentRole("Technical Architect", "Choose structure, data models, engine patterns, and maintainability rules.", ["Prevent fragile one-off scripts.", "Define module boundaries.", "Detect contradictions against prior decisions."]),
    "engineer": AgentRole("Gameplay Engineer", "Implement gameplay, tools, UI, and automation in small tested increments.", ["Write rollback-aware patches.", "Respect engine conventions.", "Never claim files changed unless the plan changes them."]),
    "engine-specialist": AgentRole("Engine Specialist", "Handle GBA/devkitPro, Unity, Unreal, web, or desktop workflows.", ["Map tasks to build commands.", "Warn when installs are required.", "Separate installed-tool facts from assumptions."]),
    "qa": AgentRole("QA Analyst", "Find defects before they grow into project debt.", ["Write test plans.", "Define acceptance tests.", "Call out hallucinated success and unverifiable claims."]),
    "build": AgentRole("Build Engineer", "Make local builds repeatable on Windows 11.", ["Manage scripts and artifacts.", "Document prerequisites.", "Do not assume SDKs exist unless doctor/memory confirms them."]),
    "ux": AgentRole("UX/UI Artist", "Create usable interfaces and production-friendly art direction prompts.", ["Define screens and HUD rules.", "Create asset briefs.", "Track placeholder versus final art."]),
    "researcher": AgentRole("Researcher", "Collect project-specific facts before risky implementation.", ["Summarize engine docs.", "Avoid copying licensed content.", "Label every uncertain claim."]),
    "memory-auditor": AgentRole("Memory Auditor", "Protect the project from context-loss, contradictions, and hallucinations.", ["Compare output against anchors, pinned facts, decisions, and constraints.", "Identify unsupported claims.", "Suggest durable memory updates."]),
}


def roles_for_swarm(name: str) -> list[AgentRole]:
    swarms = {
        "minimal": ["director", "architect", "engineer", "qa"],
        "gba": ["director", "producer", "designer", "architect", "engine-specialist", "engineer", "qa", "build", "memory-auditor"],
        "research-heavy": ["director", "researcher", "producer", "architect", "engine-specialist", "qa", "memory-auditor"],
        "studio": ["director", "producer", "designer", "architect", "engine-specialist", "engineer", "ux", "qa", "build", "memory-auditor"],
    }
    return [CORE_ROLES[k] for k in swarms.get(name, swarms["studio"])]


def role_prompt(role: AgentRole, engine_profile: str, strict: bool = True) -> str:
    rules = "\n".join(f"- {r}" for r in role.responsibilities)
    grounding = """- Use the Grounded Context Bundle as the source of truth.
- Label anything not present in the user request, workspace files, or memory as ASSUMPTION.
- Do not invent completed work, installed tools, file contents, assets, APIs, or user preferences.
- Flag contradictions against anchors, pinned facts, decisions, and constraints.""" if strict else "- Prefer grounded answers and clearly label uncertainty."
    return f"""You are the {role.name} in Game Dev Harness BYOK.
Mission: {role.mission}
Engine profile: {engine_profile}
Responsibilities:
{rules}

Hard rules:
- Assume the user may have no design or coding skills.
- Make outputs actionable for Windows 11.
- Split huge projects into durable milestones, acceptance criteria, and checkpoints.
- Never pretend external tools are installed.
- Do not copy copyrighted assets, game content, or proprietary code.

Grounding rules:
{grounding}
"""


def load_config(project_dir: Path) -> HarnessConfig:
    load_dotenv()
    load_dotenv(project_dir / ".env")
    path = project_dir / ".harness" / "config.json"
    cfg = HarnessConfig.model_validate(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else HarnessConfig()
    cfg.provider.base_url = os.getenv("GDH_BASE_URL", cfg.provider.base_url).rstrip("/")
    cfg.provider.model = os.getenv("GDH_MODEL", cfg.provider.model)
    cfg.provider.fast_model = os.getenv("GDH_FAST_MODEL", cfg.provider.fast_model or "") or None
    return cfg


def save_config(project_dir: Path, cfg: HarnessConfig) -> Path:
    path = project_dir / ".harness" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg.model_dump(), indent=2), encoding="utf-8")
    return path


def api_key(provider: ProviderConfig) -> str:
    key = os.getenv(provider.api_key_env)
    if not key:
        raise RuntimeError(f"Missing API key. Set {provider.api_key_env} in .env or your environment.")
    return key


class LLMClient:
    def __init__(self, provider: ProviderConfig):
        self.provider = provider
        self.key = api_key(provider)
        self.base_url = provider.base_url.rstrip("/")

    async def chat(self, messages: list[dict[str, str]], model: str | None = None, temperature: float = 0.2) -> str:
        endpoint = self.base_url if self.base_url.endswith("/chat/completions") else f"{self.base_url}/chat/completions"
        payload = {"model": model or self.provider.model, "messages": messages, "temperature": temperature}
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        last: Exception | None = None
        for attempt in range(self.provider.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.provider.timeout_seconds) as client:
                    r = await client.post(endpoint, headers=headers, json=payload)
                    r.raise_for_status()
                    return r.json()["choices"][0]["message"]["content"]
            except Exception as exc:
                last = exc
                if attempt < self.provider.max_retries:
                    await asyncio.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"LLM request failed: {last}")


class Workspace:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, rel: str | Path) -> Path:
        path = (self.root / rel).resolve()
        if path != self.root and self.root not in path.parents:
            raise ValueError(f"Refusing to access path outside workspace: {rel}")
        return path

    def write(self, rel: str, content: str) -> Path:
        path = self.resolve(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def list_files(self, max_files: int = 250) -> list[str]:
        excluded = {".git", ".venv", "__pycache__", "Library", "Temp", "Builds", "Saved", "Intermediate", "Binaries", "node_modules", "archive"}
        found: list[str] = []
        for p in self.root.rglob("*"):
            if len(found) >= max_files:
                break
            if not p.is_file() or any(part in excluded for part in p.parts):
                continue
            found.append(p.relative_to(self.root).as_posix())
        return sorted(found)


class SwarmRunner:
    def __init__(self, workspace: Workspace, cfg: HarnessConfig):
        self.workspace = workspace
        self.cfg = cfg
        self.memory = AdvancedProjectMemory(workspace)
        self.client = LLMClient(cfg.provider)

    async def run(self, prompt: str, swarm: str) -> dict[str, Any]:
        self.memory.ensure(self.cfg.project_name, self.cfg.engine_profile)
        if self.cfg.auto_compress_memory and self.memory.needs_compression(self.cfg.compression_trigger_chars):
            console.print("[yellow]Memory is large; running automatic compression before the swarm...[/]")
            await self.memory.compress(self.client, "automatic pre-swarm compression", self.cfg.compression_keep_recent_runs)
        context = self.memory.context_bundle(prompt, self.cfg.memory_token_budget * 4, self.cfg.retrieval_max_chunks, self.cfg.recent_run_context_count)
        files = "\n".join(self.workspace.list_files())
        roles = roles_for_swarm(swarm)
        console.print(f"Agents: {', '.join(r.name for r in roles)}")
        sem = asyncio.Semaphore(max(1, self.cfg.max_parallel_agents))

        async def run_role(role: AgentRole) -> tuple[str, str]:
            async with sem:
                console.print(f"[cyan]Running {role.name}...[/]")
                text = await self.client.chat([
                    {"role": "system", "content": role_prompt(role, self.cfg.engine_profile, self.cfg.strict_grounding)},
                    {"role": "user", "content": f"User request:\n{prompt}\n\n{context}\n\nWorkspace files:\n{files}\n\nReturn key decisions, confirmed facts, assumptions, risks, next actions, acceptance checks, and memory updates that should be pinned."},
                ], temperature=0.25)
                return role.name, text

        outputs = dict(await asyncio.gather(*(run_role(r) for r in roles)))
        packed = "\n\n".join(f"## {k}\n{v}" for k, v in outputs.items())
        synthesis = await self.client.chat([
            {"role": "system", "content": "You are the Director synthesizing a multi-agent game-development swarm. Create one cohesive milestone plan for a non-programmer. Separate confirmed memory from assumptions."},
            {"role": "user", "content": f"Original request:\n{prompt}\n\n{context}\n\nWorkspace files:\n{files}\n\nSub-agent outputs:\n{packed}\n\nSynthesize a grounded plan. Do not claim implementation happened unless this run actually wrote files."},
        ], temperature=0.2)
        audit = await self.memory.audit_synthesis(self.client, prompt, synthesis, context) if self.cfg.hallucination_audit else ""
        record = {"prompt": prompt, "swarm": swarm, "roles": [asdict(r) for r in roles], "context_chars": len(context), "role_outputs": outputs, "synthesis": synthesis, "memory_audit": audit}
        self.memory.save_run("swarm", record)
        self.memory.append_note("backlog.md", "Swarm synthesis", synthesis)
        if audit:
            self.memory.append_note("qa_log.md", "Memory audit summary", audit)
        return record


def scaffold_profile(ws: Workspace, profile: str, project_name: str) -> list[Path]:
    created = [ws.write("DESIGN_BRIEF.md", f"# {project_name} Design Brief\n\nEngine profile: `{profile}`\n\n## First playable\n\nTBD\n")]
    if profile == "gba":
        created.append(ws.write("source/main.c", '#include <gba.h>\n#include <stdio.h>\nint main(void){ irqInit(); irqEnable(IRQ_VBLANK); consoleDemoInit(); iprintf("Game Dev Harness\\n"); while(1){ VBlankIntrWait(); } }\n'))
        created.append(ws.write("Makefile", "# Requires devkitPro/devkitARM. Replace with a full devkitARM Makefile as the project grows.\n"))
    elif profile == "unity":
        created.append(ws.write("Assets/Scripts/GameBootstrap.cs", 'using UnityEngine;\npublic class GameBootstrap : MonoBehaviour { void Start(){ Debug.Log("Harness bootstrap loaded"); } }\n'))
        created.append(ws.write("Assets/Editor/BuildCommand.cs", '#if UNITY_EDITOR\nusing UnityEditor;\npublic static class BuildCommand { public static void BuildWindows(){ BuildPipeline.BuildPlayer(new[]{"Assets/Scenes/Main.unity"}, "Builds/Windows/Game.exe", BuildTarget.StandaloneWindows64, BuildOptions.None); } }\n#endif\n'))
    elif profile == "unreal":
        safe = "".join(c for c in project_name if c.isalnum()) or "HarnessGame"
        created.append(ws.write(f"{safe}.uproject", '{\n  "FileVersion": 3,\n  "EngineAssociation": "5.0",\n  "Category": "Games",\n  "Description": "Generated by Game Dev Harness BYOK"\n}\n'))
    elif profile == "webapp":
        created.append(ws.write("app/index.html", "<!doctype html><title>Harness App</title><div id='app'></div><script src='main.js'></script>\n"))
        created.append(ws.write("app/main.js", "document.getElementById('app').textContent = 'First playable placeholder';\n"))
    elif profile == "desktop":
        created.append(ws.write("app.py", "print('Desktop app placeholder generated by Game Dev Harness BYOK')\n"))
    return created


@app.command()
def init(project_dir: Path = typer.Option(Path("."), "--project-dir", "-p"), project_name: str = typer.Option("Untitled Game", "--name", "-n"), engine_profile: str = typer.Option("generic", "--profile"), base_url: str = typer.Option("https://api.openai.com/v1", "--base-url"), model: str = typer.Option("gpt-5.5", "--model"), fast_model: Optional[str] = typer.Option(None, "--fast-model"), scaffold: bool = typer.Option(True, "--scaffold/--no-scaffold")) -> None:
    if engine_profile not in ENGINE_PROFILES:
        raise typer.BadParameter(f"Choose one of: {', '.join(sorted(ENGINE_PROFILES))}")
    cfg = HarnessConfig(provider=ProviderConfig(base_url=base_url.rstrip('/'), model=model, fast_model=fast_model), project_name=project_name, engine_profile=engine_profile)
    path = save_config(project_dir, cfg)
    ws = Workspace(project_dir)
    AdvancedProjectMemory(ws).ensure(project_name, engine_profile)
    made = scaffold_profile(ws, engine_profile, project_name) if scaffold else []
    console.print(f"[green]Initialized:[/] {path}")
    console.print("Put your key in a local .env file as GDH_API_KEY=...")
    if made:
        console.print(f"Created {len(made)} starter files.")


@app.command()
def doctor() -> None:
    table = Table(title="Game Dev Harness Doctor")
    table.add_column("Check"); table.add_column("Status"); table.add_column("Detail")
    for name, exe, cmd in [("Python", "python", ["python", "--version"]), ("Git", "git", ["git", "--version"])]:
        found = shutil.which(exe)
        detail = "Install it" if not found else subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout.strip()
        table.add_row(name, "OK" if found else "Missing", detail)
    table.add_row("Unity", "OK" if os.getenv("UNITY_EXE") else "Optional", os.getenv("UNITY_EXE") or "Set UNITY_EXE for Unity automation")
    table.add_row("Unreal", "OK" if os.getenv("UNREAL_ENGINE_ROOT") else "Optional", os.getenv("UNREAL_ENGINE_ROOT") or "Set UNREAL_ENGINE_ROOT for RunUAT")
    table.add_row("devkitPro", "OK" if os.getenv("DEVKITPRO") and os.getenv("DEVKITARM") else "Optional", os.getenv("DEVKITPRO") or "Set DEVKITPRO/DEVKITARM for GBA builds")
    console.print(table)


@app.command()
def start(prompt: str, project_dir: Path = typer.Option(Path("."), "--project-dir", "-p"), swarm: Optional[str] = typer.Option(None, "--swarm")) -> None:
    cfg = load_config(project_dir)
    record = asyncio.run(SwarmRunner(Workspace(project_dir), cfg).run(prompt, swarm or cfg.default_swarm))
    console.rule("Director Synthesis"); console.print(record["synthesis"])
    if record.get("memory_audit"):
        console.rule("Memory Audit"); console.print(record["memory_audit"])


@app.command()
def resume(project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    cfg = load_config(project_dir)
    mem = AdvancedProjectMemory(Workspace(project_dir)); mem.ensure(cfg.project_name, cfg.engine_profile)
    console.print(mem.context())


@app.command("add-note")
def add_note(file_name: str, heading: str, body: str, project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    p = AdvancedProjectMemory(Workspace(project_dir)).append_note(file_name, heading, body)
    console.print(f"[green]Updated[/] {p}")


@app.command("pin-fact")
def pin_fact(heading: str, body: str, project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    cfg = load_config(project_dir)
    mem = AdvancedProjectMemory(Workspace(project_dir)); mem.ensure(cfg.project_name, cfg.engine_profile)
    console.print(f"[green]Pinned[/] {mem.append_note('pinned_facts.md', heading, body)}")


@app.command("memory-status")
def memory_status(project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    cfg = load_config(project_dir)
    mem = AdvancedProjectMemory(Workspace(project_dir)); mem.ensure(cfg.project_name, cfg.engine_profile)
    table = Table(title="Memory Status"); table.add_column("Metric"); table.add_column("Value")
    for k, v in mem.status(cfg.compression_trigger_chars).items():
        table.add_row(k, str(v))
    console.print(table)


@app.command("memory-search")
def memory_search(query: str, project_dir: Path = typer.Option(Path("."), "--project-dir", "-p"), limit: int = typer.Option(8, "--limit", "-n")) -> None:
    cfg = load_config(project_dir)
    mem = AdvancedProjectMemory(Workspace(project_dir)); mem.ensure(cfg.project_name, cfg.engine_profile)
    for chunk in mem.retrieve(query, limit):
        console.rule(f"{chunk.source} :: {chunk.heading} :: score {chunk.score:.2f}")
        console.print(chunk.text[:2000])


@app.command("memory-compress")
def memory_compress(reason: str = typer.Option("manual compression", "--reason"), project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    cfg = load_config(project_dir)
    runner = SwarmRunner(Workspace(project_dir), cfg)
    snapshot = asyncio.run(runner.memory.compress(runner.client, reason, cfg.compression_keep_recent_runs))
    console.rule("Compressed Memory Snapshot"); console.print(snapshot)


@app.command("memory-rebuild-index")
def memory_rebuild_index(project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    cfg = load_config(project_dir)
    mem = AdvancedProjectMemory(Workspace(project_dir)); mem.ensure(cfg.project_name, cfg.engine_profile)
    console.print(f"[green]Rebuilt memory index[/] with {mem.rebuild_index()} chunks.")


@app.command("ui")
def ui() -> None:
    from .desktop_app import main
    main()


if __name__ == "__main__":
    app()
