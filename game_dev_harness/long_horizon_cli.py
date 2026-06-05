from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.table import Table

from .cli import load_config
from .long_horizon import (
    AssetRegistry,
    BuildRunner,
    CommandRunner,
    DocsGenerator,
    KnowledgeManager,
    PatchManager,
    PluginRegistry,
    ProfileDoctor,
    RoadmapManager,
    SnapshotManager,
    VisualQARegistry,
)

app = typer.Typer(help="Long-horizon game development toolkit: roadmap, builds, assets, QA, snapshots, plugins, and docs.")
console = Console()


def print_json(data: Any) -> None:
    console.print(json.dumps(data, indent=2, ensure_ascii=False))


@app.command("doctor-profile")
def doctor_profile(profile: Optional[str] = None, project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    cfg = load_config(project_dir)
    rows = ProfileDoctor(project_dir).check(profile or cfg.engine_profile)
    table = Table(title=f"Profile Doctor: {profile or cfg.engine_profile}")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    for row in rows:
        table.add_row(row["check"], row["status"], row["detail"])
    console.print(table)


@app.command("build-run")
def build_run(command: Optional[str] = None, timeout: int = 1800, project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    cfg = load_config(project_dir)
    print_json(BuildRunner(project_dir).run_profile(cfg.engine_profile, command, timeout))


@app.command("run-command")
def run_command(command: str, timeout: int = 1800, project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    print_json(CommandRunner(project_dir).run(command, timeout))


@app.command("roadmap-init")
def roadmap_init(project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    cfg = load_config(project_dir)
    print_json(RoadmapManager(project_dir).ensure(cfg.project_name))


@app.command("roadmap-add-epic")
def roadmap_add_epic(title: str, description: str = "", project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    print_json(RoadmapManager(project_dir).add_epic(title, description))


@app.command("roadmap-add-milestone")
def roadmap_add_milestone(title: str, description: str = "", epic_id: Optional[str] = None, project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    print_json(RoadmapManager(project_dir).add_milestone(title, description, epic_id))


@app.command("roadmap-add-task")
def roadmap_add_task(title: str, description: str = "", acceptance: str = typer.Option("", "--acceptance", help="Semicolon-separated acceptance checks"), milestone_id: Optional[str] = None, epic_id: Optional[str] = None, priority: int = 3, project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    checks = [x.strip() for x in acceptance.split(";") if x.strip()]
    task = RoadmapManager(project_dir).add_task(title, description, milestone_id, epic_id, checks, priority)
    print_json(asdict(task))


@app.command("roadmap-update-task")
def roadmap_update_task(task_id: str, status: Optional[str] = None, confidence: Optional[str] = None, note: Optional[str] = None, project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    roadmap = RoadmapManager(project_dir)
    updates: dict[str, Any] = {"status": status, "confidence": confidence}
    if note:
        data = roadmap.load()
        task = next((t for t in data["tasks"] if t["id"] == task_id), None)
        updates["notes"] = (task or {}).get("notes", []) + [note]
    print_json(roadmap.update_task(task_id, **updates))


@app.command("roadmap-next")
def roadmap_next(limit: int = 5, project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    print_json(RoadmapManager(project_dir).next_tasks(limit))


@app.command("roadmap-export")
def roadmap_export(project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    console.print(RoadmapManager(project_dir).summary_markdown())


@app.command("asset-add")
def asset_add(name: str, kind: str, status: str = "placeholder", owner: str = "unassigned", source: str = "", notes: str = "", project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    print_json(AssetRegistry(project_dir).add(name, kind, status, owner, source, notes))


@app.command("asset-update")
def asset_update(asset_id: str, status: Optional[str] = None, owner: Optional[str] = None, notes: Optional[str] = None, project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    print_json(AssetRegistry(project_dir).update(asset_id, status=status, owner=owner, notes=notes))


@app.command("asset-list")
def asset_list(project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    console.print(AssetRegistry(project_dir).summary_markdown())


@app.command("visual-qa-add")
def visual_qa_add(image: Path, title: str, notes: str = "", severity: str = "medium", project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    print_json(VisualQARegistry(project_dir).add(image, title, notes, severity))


@app.command("visual-qa-list")
def visual_qa_list(project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    console.print(VisualQARegistry(project_dir).summary_markdown())


@app.command("patch-apply")
def patch_apply(patch_file: Path, commit: bool = False, project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    print_json(PatchManager(project_dir).apply_patch_file(patch_file, commit))


@app.command("snapshot-create")
def snapshot_create(name: str, project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    print_json(SnapshotManager(project_dir).create(name))


@app.command("snapshot-list")
def snapshot_list(project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    print_json(SnapshotManager(project_dir).list())


@app.command("snapshot-restore")
def snapshot_restore(snapshot_id: str, project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    print_json(SnapshotManager(project_dir).restore(snapshot_id))


@app.command("docs-generate")
def docs_generate(project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    for path in DocsGenerator(project_dir).generate():
        console.print(f"[green]Wrote[/] {path}")


@app.command("plugin-create")
def plugin_create(name: str, description: str = "", project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    console.print(f"[green]Created[/] {PluginRegistry(project_dir).create(name, description)}")


@app.command("plugin-list")
def plugin_list(project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    print_json(PluginRegistry(project_dir).list())


@app.command("knowledge-list")
def knowledge_list(project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    for name in KnowledgeManager(project_dir).list():
        console.print(name)


@app.command("knowledge-show")
def knowledge_show(name: str, project_dir: Path = typer.Option(Path("."), "--project-dir", "-p")) -> None:
    console.print(KnowledgeManager(project_dir).read(name))


if __name__ == "__main__":
    app()
