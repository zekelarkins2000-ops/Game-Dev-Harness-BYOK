from __future__ import annotations

import datetime as dt
import fnmatch
import json
import os
import shutil
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

STATUSES = ["planned", "in_progress", "blocked", "implemented", "verified", "rejected", "deprecated"]
CONFIDENCE = [
    "confirmed", "assumption", "stale", "deprecated", "contradicted",
    "needs_verification", "verified_by_build", "verified_by_test",
]


def now() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat()


def short_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


@dataclass
class RoadmapTask:
    id: str
    title: str
    description: str = ""
    epic_id: str | None = None
    milestone_id: str | None = None
    status: str = "planned"
    priority: int = 3
    confidence: str = "needs_verification"
    acceptance: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)


class RoadmapManager:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.path = self.root / ".harness" / "roadmap.json"

    def ensure(self, project_name: str = "Untitled Game") -> dict[str, Any]:
        data = read_json(self.path, {})
        if data:
            return data
        data = {
            "schema": 1,
            "project_name": project_name,
            "vision": "",
            "epics": [],
            "milestones": [],
            "tasks": [],
            "definition_of_done": [
                "Task has acceptance checks.",
                "Changed files are listed.",
                "Build/test command is identified or marked not available.",
                "Known risks and assumptions are recorded.",
                "Memory updates are written or explicitly skipped.",
            ],
            "updated_at": now(),
        }
        write_json(self.path, data)
        return data

    def load(self) -> dict[str, Any]:
        return self.ensure()

    def save(self, data: dict[str, Any]) -> Path:
        data["updated_at"] = now()
        return write_json(self.path, data)

    def add_epic(self, title: str, description: str = "") -> dict[str, Any]:
        data = self.load()
        epic = {"id": short_id("epic"), "title": title, "description": description, "status": "planned", "created_at": now(), "updated_at": now()}
        data["epics"].append(epic)
        self.save(data)
        return epic

    def add_milestone(self, title: str, description: str = "", epic_id: str | None = None) -> dict[str, Any]:
        data = self.load()
        milestone = {"id": short_id("milestone"), "title": title, "description": description, "epic_id": epic_id, "status": "planned", "created_at": now(), "updated_at": now()}
        data["milestones"].append(milestone)
        self.save(data)
        return milestone

    def add_task(self, title: str, description: str = "", milestone_id: str | None = None, epic_id: str | None = None, acceptance: list[str] | None = None, priority: int = 3) -> RoadmapTask:
        data = self.load()
        task = RoadmapTask(id=short_id("task"), title=title, description=description, milestone_id=milestone_id, epic_id=epic_id, priority=priority, acceptance=acceptance or [])
        data["tasks"].append(asdict(task))
        self.save(data)
        return task

    def update_task(self, task_id: str, **updates: Any) -> dict[str, Any]:
        data = self.load()
        for task in data["tasks"]:
            if task["id"] == task_id:
                if "status" in updates and updates["status"] not in STATUSES:
                    raise ValueError(f"Invalid status. Choose one of {STATUSES}")
                if "confidence" in updates and updates["confidence"] not in CONFIDENCE:
                    raise ValueError(f"Invalid confidence. Choose one of {CONFIDENCE}")
                for key, value in updates.items():
                    if value is not None:
                        task[key] = value
                task["updated_at"] = now()
                self.save(data)
                return task
        raise KeyError(f"No task found: {task_id}")

    def next_tasks(self, limit: int = 5) -> list[dict[str, Any]]:
        data = self.load()
        candidates = [t for t in data.get("tasks", []) if t.get("status") in {"planned", "blocked", "in_progress"}]
        order = {"in_progress": 0, "blocked": 1, "planned": 2}
        candidates.sort(key=lambda t: (order.get(t.get("status", "planned"), 9), int(t.get("priority", 3)), t.get("created_at", "")))
        return candidates[:limit]

    def summary_markdown(self) -> str:
        data = self.load()
        lines = [f"# Roadmap: {data.get('project_name', 'Untitled Game')}", ""]
        lines.append("## Definition of Done")
        for item in data.get("definition_of_done", []):
            lines.append(f"- {item}")
        lines.append("\n## Epics")
        for epic in data.get("epics", []):
            lines.append(f"- **{epic['title']}** (`{epic['id']}`) - {epic.get('status', 'planned')}")
        lines.append("\n## Milestones")
        for milestone in data.get("milestones", []):
            lines.append(f"- **{milestone['title']}** (`{milestone['id']}`) - {milestone.get('status', 'planned')}")
        lines.append("\n## Tasks")
        for task in data.get("tasks", []):
            checks = "; ".join(task.get("acceptance", []))
            lines.append(f"- [{task.get('status','planned')}] **{task['title']}** (`{task['id']}`) p{task.get('priority',3)} confidence={task.get('confidence','needs_verification')} :: {checks}")
        return "\n".join(lines) + "\n"


class AssetRegistry:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.path = self.root / ".harness" / "assets_manifest.json"

    def ensure(self) -> dict[str, Any]:
        data = read_json(self.path, {})
        if data:
            return data
        data = {"schema": 1, "assets": [], "updated_at": now()}
        write_json(self.path, data)
        return data

    def add(self, name: str, kind: str, status: str = "placeholder", owner: str = "unassigned", source: str = "", notes: str = "") -> dict[str, Any]:
        data = self.ensure()
        asset = {"id": short_id("asset"), "name": name, "kind": kind, "status": status, "owner": owner, "source": source, "notes": notes, "created_at": now(), "updated_at": now()}
        data["assets"].append(asset)
        data["updated_at"] = now()
        write_json(self.path, data)
        return asset

    def update(self, asset_id: str, **updates: Any) -> dict[str, Any]:
        data = self.ensure()
        for asset in data["assets"]:
            if asset["id"] == asset_id:
                for key, value in updates.items():
                    if value is not None:
                        asset[key] = value
                asset["updated_at"] = now()
                data["updated_at"] = now()
                write_json(self.path, data)
                return asset
        raise KeyError(f"No asset found: {asset_id}")

    def summary_markdown(self) -> str:
        data = self.ensure()
        lines = ["# Asset Manifest", ""]
        for asset in data.get("assets", []):
            lines.append(f"- **{asset['name']}** (`{asset['id']}`) kind={asset.get('kind')} status={asset.get('status')} owner={asset.get('owner')}")
            if asset.get("notes"):
                lines.append(f"  - {asset['notes']}")
        return "\n".join(lines) + "\n"


class VisualQARegistry:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.visual_root = self.root / ".harness" / "visual_qa"
        self.screenshots = self.visual_root / "screenshots"
        self.path = self.visual_root / "issues.json"
        self.screenshots.mkdir(parents=True, exist_ok=True)

    def ensure(self) -> dict[str, Any]:
        data = read_json(self.path, {})
        if data:
            return data
        data = {"schema": 1, "issues": [], "updated_at": now()}
        write_json(self.path, data)
        return data

    def add(self, image_path: Path, title: str, notes: str = "", severity: str = "medium") -> dict[str, Any]:
        data = self.ensure()
        image_path = image_path.expanduser().resolve()
        if not image_path.exists():
            raise FileNotFoundError(image_path)
        dest = self.screenshots / f"{short_id('shot')}{image_path.suffix.lower()}"
        shutil.copy2(image_path, dest)
        issue = {"id": short_id("vqa"), "title": title, "notes": notes, "severity": severity, "status": "open", "screenshot": str(dest.relative_to(self.root)), "created_at": now(), "updated_at": now()}
        data["issues"].append(issue)
        data["updated_at"] = now()
        write_json(self.path, data)
        return issue

    def summary_markdown(self) -> str:
        data = self.ensure()
        lines = ["# Visual QA", ""]
        for issue in data.get("issues", []):
            lines.append(f"- [{issue.get('status','open')}] **{issue['title']}** (`{issue['id']}`) severity={issue.get('severity')} screenshot={issue.get('screenshot')}")
            if issue.get("notes"):
                lines.append(f"  - {issue['notes']}")
        return "\n".join(lines) + "\n"


class CommandRunner:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.logs = self.root / ".harness" / "build_logs"
        self.logs.mkdir(parents=True, exist_ok=True)

    def run(self, command: str, timeout: int = 1800) -> dict[str, Any]:
        log_path = self.logs / f"{now().replace(':','-')}-command.log"
        proc = subprocess.run(command, shell=True, cwd=self.root, text=True, capture_output=True, timeout=timeout)
        body = f"$ {command}\n\n# STDOUT\n{proc.stdout}\n\n# STDERR\n{proc.stderr}\n\nexit_code={proc.returncode}\n"
        log_path.write_text(body, encoding="utf-8", errors="replace")
        return {"command": command, "exit_code": proc.returncode, "log": str(log_path), "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}


class BuildRunner(CommandRunner):
    def default_command(self, profile: str) -> str | None:
        profile = profile.lower()
        if profile == "unity":
            unity = os.getenv("UNITY_EXE", "Unity")
            return f'"{unity}" -batchmode -quit -projectPath . -executeMethod BuildCommand.BuildWindows -logFile Logs\\unity-build.log'
        if profile == "unreal":
            root = os.getenv("UNREAL_ENGINE_ROOT")
            if not root:
                return None
            return f'"{root}\\Engine\\Build\\BatchFiles\\RunUAT.bat" BuildCookRun -project="%CD%" -noP4 -platform=Win64 -clientconfig=Development -build -cook -stage -pak'
        if profile == "gba":
            return "make"
        if profile == "webapp":
            return "python -m py_compile app/main.js"
        if profile == "desktop":
            return "python -m py_compile app.py"
        return None

    def run_profile(self, profile: str, command: str | None = None, timeout: int = 1800) -> dict[str, Any]:
        cmd = command or self.default_command(profile)
        if not cmd:
            raise RuntimeError(f"No default build command for profile '{profile}'. Provide --command.")
        return self.run(cmd, timeout=timeout)


class ProfileDoctor:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def check(self, profile: str) -> list[dict[str, str]]:
        profile = profile.lower()
        rows: list[dict[str, str]] = []
        def add(name: str, ok: bool, detail: str) -> None:
            rows.append({"check": name, "status": "OK" if ok else "Missing/Warning", "detail": detail})
        add("Python", shutil.which("python") is not None, subprocess.getoutput("python --version"))
        add("Git", shutil.which("git") is not None, subprocess.getoutput("git --version"))
        if profile == "unity":
            unity = os.getenv("UNITY_EXE")
            add("UNITY_EXE", bool(unity and Path(unity).exists()), unity or "Set UNITY_EXE to Unity.exe")
            add("Assets folder", (self.root / "Assets").exists(), "Unity projects should contain Assets/")
        elif profile == "unreal":
            ue = os.getenv("UNREAL_ENGINE_ROOT")
            add("UNREAL_ENGINE_ROOT", bool(ue and Path(ue).exists()), ue or "Set UNREAL_ENGINE_ROOT")
            add("uproject", bool(list(self.root.glob("*.uproject"))), "Expected a .uproject file")
        elif profile == "gba":
            add("DEVKITPRO", bool(os.getenv("DEVKITPRO")), os.getenv("DEVKITPRO") or "Set DEVKITPRO")
            add("DEVKITARM", bool(os.getenv("DEVKITARM")), os.getenv("DEVKITARM") or "Set DEVKITARM")
            add("Makefile", (self.root / "Makefile").exists(), "Expected Makefile")
        elif profile == "webapp":
            add("app/index.html", (self.root / "app" / "index.html").exists(), "Expected app/index.html")
        elif profile == "desktop":
            add("app.py", (self.root / "app.py").exists(), "Expected app.py or your own desktop entry point")
        return rows


class PatchManager:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.applied = self.root / ".harness" / "patches"
        self.applied.mkdir(parents=True, exist_ok=True)

    def apply_patch_file(self, patch_file: Path, commit: bool = False) -> dict[str, Any]:
        patch_file = patch_file.expanduser().resolve()
        if not patch_file.exists():
            raise FileNotFoundError(patch_file)
        check = subprocess.run(["git", "apply", "--check", str(patch_file)], cwd=self.root, text=True, capture_output=True)
        if check.returncode != 0:
            return {"applied": False, "stage": "check", "stdout": check.stdout, "stderr": check.stderr}
        applied = subprocess.run(["git", "apply", str(patch_file)], cwd=self.root, text=True, capture_output=True)
        result: dict[str, Any] = {"applied": applied.returncode == 0, "stage": "apply", "stdout": applied.stdout, "stderr": applied.stderr}
        if applied.returncode == 0:
            dest = self.applied / f"{now().replace(':','-')}-{patch_file.name}"
            shutil.copy2(patch_file, dest)
            result["record"] = str(dest)
            if commit:
                subprocess.run(["git", "add", "-A"], cwd=self.root)
                commit_proc = subprocess.run(["git", "commit", "-m", f"Apply harness patch {patch_file.name}"], cwd=self.root, text=True, capture_output=True)
                result["commit_stdout"] = commit_proc.stdout
                result["commit_stderr"] = commit_proc.stderr
        return result


EXCLUDE_DIRS = {".git", ".venv", "venv", "env", "__pycache__", "Library", "Temp", "Build", "Builds", "Binaries", "Saved", "Intermediate", "DerivedDataCache", "node_modules", ".harness/snapshots"}


class SnapshotManager:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.snapshots = self.root / ".harness" / "snapshots"
        self.snapshots.mkdir(parents=True, exist_ok=True)
        self.manifest = self.snapshots / "manifest.json"

    def _ignore(self, dir_path: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        try:
            rel = Path(dir_path).resolve().relative_to(self.root)
        except ValueError:
            rel = Path()
        for name in names:
            candidate = (rel / name).as_posix()
            if name in EXCLUDE_DIRS or candidate in EXCLUDE_DIRS or any(fnmatch.fnmatch(candidate, pat) for pat in ["*.gba", "*.sav", "*.state"]):
                ignored.add(name)
        return ignored

    def create(self, name: str) -> dict[str, Any]:
        sid = short_id("snap")
        dest = self.snapshots / sid
        shutil.copytree(self.root, dest, ignore=self._ignore)
        data = read_json(self.manifest, {"snapshots": []})
        item = {"id": sid, "name": name, "path": str(dest), "created_at": now()}
        data["snapshots"].append(item)
        write_json(self.manifest, data)
        return item

    def list(self) -> list[dict[str, Any]]:
        return read_json(self.manifest, {"snapshots": []}).get("snapshots", [])

    def restore(self, snapshot_id: str) -> dict[str, Any]:
        matches = [s for s in self.list() if s["id"] == snapshot_id]
        if not matches:
            raise KeyError(snapshot_id)
        src = Path(matches[0]["path"])
        if not src.exists():
            raise FileNotFoundError(src)
        for item in src.iterdir():
            dest = self.root / item.name
            if item.name == ".harness":
                continue
            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        return {"restored": snapshot_id, "source": str(src)}


class PluginRegistry:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.plugins = self.root / "plugins"
        self.plugins.mkdir(parents=True, exist_ok=True)

    def create(self, name: str, description: str = "") -> Path:
        safe = "".join(c for c in name.lower().replace(" ", "-") if c.isalnum() or c in "-_") or "plugin"
        p = self.plugins / safe / "plugin.json"
        data = {"name": safe, "description": description, "commands": [], "validators": [], "memory_templates": [], "created_at": now()}
        write_json(p, data)
        readme = p.parent / "README.md"
        if not readme.exists():
            readme.write_text(f"# {safe} plugin\n\n{description}\n", encoding="utf-8")
        return p

    def list(self) -> list[dict[str, Any]]:
        return [read_json(p, {}) for p in sorted(self.plugins.glob("*/plugin.json"))]


class KnowledgeManager:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.knowledge = self.root / "knowledge"
        self.knowledge.mkdir(parents=True, exist_ok=True)

    def ensure_defaults(self) -> None:
        defaults = {
            "unity_2d.md": "# Unity 2D Knowledge Pack\n\n- Keep prototypes small.\n- Prefer scenes, prefabs, ScriptableObjects, and editor build commands.\n- Validate with batchmode builds when possible.\n",
            "unity_3d.md": "# Unity 3D Knowledge Pack\n\n- Prototype with primitives before final art.\n- Track controllers, cameras, prefabs, scenes, and input settings.\n",
            "unreal_blueprints.md": "# Unreal Blueprints Knowledge Pack\n\n- Keep blueprint systems modular.\n- Record plugin and engine-version assumptions.\n- Use packaged builds as verification.\n",
            "gba_homebrew.md": "# GBA Homebrew Knowledge Pack\n\n- Requires devkitPro/devkitARM.\n- Use original assets only.\n- Keep sprite, tile, palette, and memory limits visible in tasks.\n",
            "steam_release.md": "# Steam Release Knowledge Pack\n\n- Track capsules, builds, depots, store assets, achievements, and QA separately.\n",
            "itch_release.md": "# itch.io Release Knowledge Pack\n\n- Track web/desktop builds, screenshots, page copy, and downloadable artifacts.\n",
            "godot.md": "# Godot Knowledge Pack\n\n- Track Godot version, export templates, scenes, autoloads, and input map.\n",
            "aseprite.md": "# Aseprite Knowledge Pack\n\n- Track source .aseprite files, exported sprite sheets, palettes, and animation tags.\n",
            "blender.md": "# Blender Knowledge Pack\n\n- Track source .blend files, exports, rigs, materials, scale, and engine import settings.\n",
        }
        for name, body in defaults.items():
            p = self.knowledge / name
            if not p.exists():
                p.write_text(body, encoding="utf-8")

    def list(self) -> list[str]:
        self.ensure_defaults()
        return sorted(p.name for p in self.knowledge.glob("*.md"))

    def read(self, name: str) -> str:
        self.ensure_defaults()
        p = self.knowledge / name
        if not p.exists():
            raise FileNotFoundError(p)
        return p.read_text(encoding="utf-8")


class DocsGenerator:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.docs = self.root / "docs"
        self.docs.mkdir(parents=True, exist_ok=True)

    def generate(self) -> list[Path]:
        roadmap = RoadmapManager(self.root).summary_markdown()
        assets = AssetRegistry(self.root).summary_markdown()
        visual = VisualQARegistry(self.root).summary_markdown()
        memory_root = self.root / ".harness" / "memory"
        def mem(name: str) -> str:
            p = memory_root / name
            return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
        files = {
            "GDD.md": f"# Game Design Document\n\n{mem('project_brief.md')}\n\n{roadmap}\n\n{assets}\n",
            "TDD.md": f"# Technical Design Document\n\n{mem('decisions.md')}\n\n## Build and Tooling\n\n{mem('constraints.md')}\n",
            "ROADMAP.md": roadmap,
            "BUILD_AND_RELEASE.md": "# Build and Release\n\nRun `gdh doctor-profile`, `gdh build-run`, and record failures in QA.\n\n" + mem("qa_log.md"),
            "ART_DIRECTION.md": "# Art Direction\n\nTrack placeholder and final assets here.\n\n" + assets,
            "QA_PLAN.md": "# QA Plan\n\n" + mem("qa_log.md") + "\n\n" + visual,
        }
        written: list[Path] = []
        for name, body in files.items():
            path = self.docs / name
            path.write_text(body, encoding="utf-8")
            written.append(path)
        return written
