from __future__ import annotations

from pathlib import Path

from game_dev_harness.cli import HarnessConfig, ProviderConfig, Workspace, roles_for_swarm, save_config
from game_dev_harness.long_horizon import (
    AssetRegistry,
    DocsGenerator,
    KnowledgeManager,
    PluginRegistry,
    ProfileDoctor,
    RoadmapManager,
    SnapshotManager,
    VisualQARegistry,
)
from game_dev_harness.memory import AdvancedProjectMemory


def test_memory_initializes_and_retrieves(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    mem = AdvancedProjectMemory(ws)
    mem.ensure("Smoke Game", "desktop")
    mem.append_note("pinned_facts.md", "Engine", "The smoke project uses the desktop profile.")
    hits = mem.retrieve("desktop profile engine", limit=5)
    assert hits
    assert any("desktop" in hit.text.lower() for hit in hits)
    status = mem.status(10_000)
    assert status["markdown_files"] >= 1


def test_roadmap_assets_docs_and_knowledge(tmp_path: Path) -> None:
    save_config(tmp_path, HarnessConfig(provider=ProviderConfig(), project_name="Smoke Game", engine_profile="desktop"))
    roadmap = RoadmapManager(tmp_path)
    roadmap.ensure("Smoke Game")
    epic = roadmap.add_epic("First Playable")
    milestone = roadmap.add_milestone("Vertical Slice", epic_id=epic["id"])
    task = roadmap.add_task("Add player movement", milestone_id=milestone["id"], acceptance=["Player moves", "Build command identified"])
    assert task.id.startswith("task-")
    assert roadmap.next_tasks(1)[0]["title"] == "Add player movement"

    asset = AssetRegistry(tmp_path).add("Player idle sprite", "sprite")
    assert asset["status"] == "placeholder"

    packs = KnowledgeManager(tmp_path).list()
    assert "gba_homebrew.md" in packs

    written = DocsGenerator(tmp_path).generate()
    assert any(path.name == "GDD.md" for path in written)
    assert (tmp_path / "docs" / "ROADMAP.md").exists()


def test_swarm_roles_and_profile_doctor(tmp_path: Path) -> None:
    names = [role.name for role in roles_for_swarm("studio")]
    assert "Memory Auditor" in names
    rows = ProfileDoctor(tmp_path).check("desktop")
    assert any(row["check"] == "Python" for row in rows)


def test_snapshot_plugin_and_visual_qa_smoke(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('hello')\n", encoding="utf-8")
    snapshot = SnapshotManager(tmp_path).create("before change")
    assert snapshot["id"].startswith("snap-")

    plugin_path = PluginRegistry(tmp_path).create("Example Plugin", "Smoke test plugin")
    assert plugin_path.exists()

    image = tmp_path / "screenshot.png"
    image.write_bytes(b"fakepng")
    issue = VisualQARegistry(tmp_path).add(image, "Alignment issue", "Smoke test note")
    assert issue["id"].startswith("vqa-")
