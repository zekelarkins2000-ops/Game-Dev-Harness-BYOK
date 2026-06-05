from __future__ import annotations

import json
import os
import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .cli import load_config
from .long_horizon import (
    AssetRegistry,
    BuildRunner,
    DocsGenerator,
    KnowledgeManager,
    PluginRegistry,
    ProfileDoctor,
    RoadmapManager,
    SnapshotManager,
    VisualQARegistry,
)

ACCENTS = {
    "Blue": ("#2563eb", "#1d4ed8"),
    "Violet": ("#7c3aed", "#6d28d9"),
    "Emerald": ("#059669", "#047857"),
    "Orange": ("#ea580c", "#c2410c"),
    "Rose": ("#e11d48", "#be123c"),
    "Slate": ("#475569", "#334155"),
}


def settings_path() -> Path:
    root = Path(os.getenv("APPDATA", str(Path.home()))) / "GameDevHarnessBYOK"
    root.mkdir(parents=True, exist_ok=True)
    return root / "dashboard_settings.json"


def load_settings() -> dict[str, str]:
    p = settings_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"appearance": "Dark", "accent": "Blue", "font_scale": "100%"}


def save_settings(data: dict[str, str]) -> None:
    settings_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


class LongHorizonDashboard(ctk.CTk):
    def __init__(self) -> None:
        self.settings = load_settings()
        ctk.set_appearance_mode(self.settings.get("appearance", "Dark"))
        ctk.set_default_color_theme("blue")
        super().__init__()
        self.title("Game Dev Harness Dashboard")
        self.geometry("1320x860")
        self.minsize(1100, 720)
        self.queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.accent_name = self.settings.get("accent", "Blue")
        self.accent = ACCENTS.get(self.accent_name, ACCENTS["Blue"])
        self.project_dir = ctk.StringVar(value=str(Path.cwd()))
        self._build()
        self._apply_scale()
        self.after(120, self._drain)

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        side = ctk.CTkFrame(self, width=310, corner_radius=0)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_rowconfigure(10, weight=1)
        ctk.CTkLabel(side, text="Long-Horizon\nDashboard", font=ctk.CTkFont(size=27, weight="bold"), justify="left").grid(row=0, column=0, padx=24, pady=(28, 10), sticky="w")
        ctk.CTkLabel(side, text="Roadmap • Assets • QA • Builds", text_color=("gray35", "gray70")).grid(row=1, column=0, padx=24, pady=(0, 20), sticky="w")

        row = ctk.CTkFrame(side, fg_color="transparent")
        row.grid(row=2, column=0, padx=24, pady=8, sticky="ew")
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(row, text="Project folder", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkEntry(row, textvariable=self.project_dir).grid(row=1, column=0, sticky="ew", pady=(4, 0))
        ctk.CTkButton(row, text="Browse", width=78, fg_color=self.accent[0], hover_color=self.accent[1], command=self._browse).grid(row=1, column=1, padx=(8, 0), pady=(4, 0))

        self.appearance = ctk.StringVar(value=self.settings.get("appearance", "Dark"))
        self.accent_var = ctk.StringVar(value=self.accent_name)
        self.font_scale = ctk.StringVar(value=self.settings.get("font_scale", "100%"))
        ctk.CTkLabel(side, text="Customize", font=ctk.CTkFont(size=13, weight="bold")).grid(row=3, column=0, padx=24, pady=(18, 5), sticky="w")
        custom = ctk.CTkFrame(side, fg_color="transparent")
        custom.grid(row=4, column=0, padx=24, pady=0, sticky="ew")
        custom.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkOptionMenu(custom, values=["Dark", "Light", "System"], variable=self.appearance, command=self._theme).grid(row=0, column=0, padx=(0, 5), sticky="ew")
        ctk.CTkOptionMenu(custom, values=list(ACCENTS), variable=self.accent_var, command=self._accent).grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkOptionMenu(custom, values=["90%", "100%", "110%", "120%"], variable=self.font_scale, command=self._scale).grid(row=0, column=2, padx=(5, 0), sticky="ew")

        for i, (text, cmd) in enumerate([
            ("Refresh Dashboard", self.refresh),
            ("Run Profile Doctor", self.profile_doctor),
            ("Generate Living Docs", self.docs_generate),
            ("Create Safety Snapshot", self.snapshot_create),
            ("Run Default Build", self.build_run),
            ("Open Project Folder", self.open_folder),
        ], start=5):
            ctk.CTkButton(side, text=text, height=40, corner_radius=12, fg_color=self.accent[0], hover_color=self.accent[1], command=cmd).grid(row=i, column=0, padx=24, pady=6, sticky="ew")

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, padx=24, pady=24, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)
        hero = ctk.CTkFrame(main, corner_radius=24)
        hero.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        hero.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hero, text="Keep huge game projects organized across months.", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=24, pady=(22, 4), sticky="w")
        ctk.CTkLabel(hero, text="Track tasks, assets, visual QA, builds, snapshots, plugins, and knowledge packs from one simple dashboard.", text_color=("gray35", "gray70")).grid(row=1, column=0, padx=24, pady=(0, 22), sticky="w")

        self.tabs = ctk.CTkTabview(main, corner_radius=24)
        self.tabs.grid(row=1, column=0, sticky="nsew")
        for name in ["Roadmap", "Assets", "Visual QA", "Builds", "Snapshots", "Knowledge", "Output"]:
            self.tabs.add(name)
            self.tabs.tab(name).grid_columnconfigure(0, weight=1)
            self.tabs.tab(name).grid_rowconfigure(0, weight=1)
        self.texts: dict[str, ctk.CTkTextbox] = {}
        for name in ["Roadmap", "Assets", "Visual QA", "Builds", "Snapshots", "Knowledge", "Output"]:
            box = ctk.CTkTextbox(self.tabs.tab(name), corner_radius=16, wrap="word")
            box.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
            self.texts[name] = box
        self.refresh()

    def root_path(self) -> Path:
        return Path(self.project_dir.get()).expanduser().resolve()

    def _browse(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.project_dir.get() or str(Path.cwd()))
        if selected:
            self.project_dir.set(selected)
            self.refresh()

    def write_tab(self, tab: str, text: str) -> None:
        box = self.texts[tab]
        box.delete("1.0", "end")
        box.insert("1.0", text)

    def log(self, text: str) -> None:
        self.texts["Output"].insert("end", text + "\n")
        self.texts["Output"].see("end")

    def refresh(self) -> None:
        root = self.root_path()
        root.mkdir(parents=True, exist_ok=True)
        try:
            cfg = load_config(root)
            RoadmapManager(root).ensure(cfg.project_name)
        except Exception:
            RoadmapManager(root).ensure("Untitled Game")
        self.write_tab("Roadmap", RoadmapManager(root).summary_markdown())
        self.write_tab("Assets", AssetRegistry(root).summary_markdown())
        self.write_tab("Visual QA", VisualQARegistry(root).summary_markdown())
        self.write_tab("Snapshots", json.dumps(SnapshotManager(root).list(), indent=2))
        self.write_tab("Knowledge", "\n".join(KnowledgeManager(root).list()))
        self.write_tab("Builds", "Build logs are written to .harness/build_logs.\nUse Run Default Build or gdh-long build-run.")

    def background(self, title: str, fn) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Game Dev Harness", "A dashboard task is already running.")
            return
        def target() -> None:
            self.queue.put(f"\n=== {title} ===")
            try:
                self.queue.put(str(fn()))
            except Exception as exc:
                self.queue.put(f"ERROR: {exc}")
            finally:
                self.queue.put("__REFRESH__")
        self.worker = threading.Thread(target=target, daemon=True)
        self.worker.start()

    def _drain(self) -> None:
        try:
            while True:
                item = self.queue.get_nowait()
                if item == "__REFRESH__":
                    self.refresh()
                else:
                    self.log(item)
        except queue.Empty:
            pass
        self.after(120, self._drain)

    def profile_doctor(self) -> None:
        def task() -> str:
            root = self.root_path()
            cfg = load_config(root)
            return json.dumps(ProfileDoctor(root).check(cfg.engine_profile), indent=2)
        self.background("Profile Doctor", task)

    def docs_generate(self) -> None:
        self.background("Generate Living Docs", lambda: "\n".join(str(p) for p in DocsGenerator(self.root_path()).generate()))

    def snapshot_create(self) -> None:
        self.background("Create Safety Snapshot", lambda: json.dumps(SnapshotManager(self.root_path()).create("dashboard snapshot"), indent=2))

    def build_run(self) -> None:
        def task() -> str:
            root = self.root_path()
            cfg = load_config(root)
            return json.dumps(BuildRunner(root).run_profile(cfg.engine_profile), indent=2)
        self.background("Run Default Build", task)

    def open_folder(self) -> None:
        root = self.root_path()
        root.mkdir(parents=True, exist_ok=True)
        os.startfile(root)  # type: ignore[attr-defined]

    def _theme(self, value: str) -> None:
        ctk.set_appearance_mode(value)
        self.settings["appearance"] = value
        save_settings(self.settings)

    def _accent(self, value: str) -> None:
        self.accent = ACCENTS.get(value, ACCENTS["Blue"])
        self.settings["accent"] = value
        save_settings(self.settings)
        for widget in self._all_children():
            if isinstance(widget, ctk.CTkButton):
                widget.configure(fg_color=self.accent[0], hover_color=self.accent[1])

    def _scale(self, value: str) -> None:
        self.settings["font_scale"] = value
        save_settings(self.settings)
        self._apply_scale()

    def _apply_scale(self) -> None:
        ctk.set_widget_scaling(int(self.settings.get("font_scale", "100%").replace("%", "")) / 100)

    def _all_children(self) -> list[object]:
        out: list[object] = []
        def walk(widget) -> None:
            for child in widget.winfo_children():
                out.append(child)
                walk(child)
        walk(self)
        return out


def main() -> None:
    app = LongHorizonDashboard()
    app.mainloop()


if __name__ == "__main__":
    main()
