from __future__ import annotations

import asyncio
import json
import os
import queue
import subprocess
import threading
from pathlib import Path
from shutil import which
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .cli import HarnessConfig, ProviderConfig, SwarmRunner, Workspace, load_config, save_config, scaffold_profile
from .memory import AdvancedProjectMemory

APP_TITLE = "Game Dev Harness BYOK"
SWARMS = ["studio", "minimal", "gba", "research-heavy"]
PROFILES = ["desktop", "generic", "gba", "unity", "unreal", "webapp"]
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
    return root / "desktop_settings.json"


def load_ui_settings() -> dict[str, str]:
    path = settings_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"appearance": "Dark", "accent": "Blue", "font_scale": "100%"}


def save_ui_settings(data: dict[str, str]) -> None:
    settings_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_env(project_dir: Path, values: dict[str, str]) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    env_path = project_dir / ".env"
    existing: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                existing[key.strip()] = value.strip()
    existing.update({k: v for k, v in values.items() if v is not None})
    env_path.write_text("\n".join(f"{k}={v}" for k, v in existing.items()) + "\n", encoding="utf-8")


class HarnessDesktopApp(ctk.CTk):
    def __init__(self) -> None:
        self.ui_settings = load_ui_settings()
        ctk.set_appearance_mode(self.ui_settings.get("appearance", "Dark"))
        ctk.set_default_color_theme("blue")
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1280x820")
        self.minsize(1040, 700)
        self.task_queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.accent_name = self.ui_settings.get("accent", "Blue")
        self.accent = ACCENTS.get(self.accent_name, ACCENTS["Blue"])
        self._build()
        self._apply_font_scale()
        self.after(120, self._drain_queue)

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(13, weight=1)
        ctk.CTkLabel(self.sidebar, text="Game Dev\nHarness", font=ctk.CTkFont(size=28, weight="bold"), justify="left").grid(row=0, column=0, padx=24, pady=(28, 8), sticky="w")
        ctk.CTkLabel(self.sidebar, text="BYOK swarm control center", text_color=("gray35", "gray70")).grid(row=1, column=0, padx=24, pady=(0, 20), sticky="w")

        self.project_dir = ctk.StringVar(value=str(Path.cwd()))
        self.project_name = ctk.StringVar(value="Untitled Game")
        self.profile = ctk.StringVar(value="desktop")
        self.base_url = ctk.StringVar(value="https://api.openai.com/v1")
        self.model = ctk.StringVar(value="gpt-5.5")
        self.fast_model = ctk.StringVar(value="")
        self.api_key = ctk.StringVar(value="")
        self.swarm = ctk.StringVar(value="studio")
        self.appearance = ctk.StringVar(value=self.ui_settings.get("appearance", "Dark"))
        self.accent_var = ctk.StringVar(value=self.accent_name)
        self.font_scale = ctk.StringVar(value=self.ui_settings.get("font_scale", "100%"))

        self._entry("Project folder", self.project_dir, 2, browse=True)
        self._entry("Project name", self.project_name, 3)
        self._option("Profile", self.profile, PROFILES, 4)
        self._entry("Base URL", self.base_url, 5)
        self._entry("Model", self.model, 6)
        self._entry("Fast model", self.fast_model, 7)
        self._entry("API key", self.api_key, 8, show="•")
        self._option("Swarm", self.swarm, SWARMS, 9)

        ctk.CTkLabel(self.sidebar, text="Customize", font=ctk.CTkFont(size=14, weight="bold")).grid(row=10, column=0, padx=24, pady=(18, 4), sticky="w")
        settings = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        settings.grid(row=11, column=0, padx=24, pady=0, sticky="ew")
        settings.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkOptionMenu(settings, values=["Dark", "Light", "System"], variable=self.appearance, command=self._theme_changed).grid(row=0, column=0, padx=(0, 6), sticky="ew")
        ctk.CTkOptionMenu(settings, values=list(ACCENTS), variable=self.accent_var, command=self._accent_changed).grid(row=0, column=1, padx=6, sticky="ew")
        ctk.CTkOptionMenu(settings, values=["90%", "100%", "110%", "120%"], variable=self.font_scale, command=self._font_changed).grid(row=0, column=2, padx=(6, 0), sticky="ew")

        self.save_button = self._sidebar_button("Save BYOK Settings", self._save_byok, 14)
        self.init_button = self._sidebar_button("Initialize / Update Workspace", self._init_workspace, 15)
        self.doctor_button = self._sidebar_button("Run Doctor", self._doctor, 16)
        self.open_button = self._sidebar_button("Open Project Folder", self._open_folder, 17)

        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.grid(row=0, column=1, padx=24, pady=24, sticky="nsew")
        self.main.grid_rowconfigure(2, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        hero = ctk.CTkFrame(self.main, corner_radius=24)
        hero.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        hero.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hero, text="Prompt-driven game development, without losing the plot.", font=ctk.CTkFont(size=24, weight="bold"), anchor="w").grid(row=0, column=0, padx=24, pady=(22, 4), sticky="ew")
        ctk.CTkLabel(hero, text="Run specialist swarms, preserve project truth, compress memory safely, and keep every milestone grounded.", text_color=("gray35", "gray70"), anchor="w").grid(row=1, column=0, padx=24, pady=(0, 22), sticky="ew")

        prompt_card = ctk.CTkFrame(self.main, corner_radius=24)
        prompt_card.grid(row=1, column=0, sticky="ew", pady=(0, 18))
        prompt_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(prompt_card, text="Mission prompt", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=20, pady=(18, 4), sticky="w")
        self.prompt_box = ctk.CTkTextbox(prompt_card, height=120, corner_radius=16)
        self.prompt_box.grid(row=1, column=0, padx=20, pady=(0, 14), sticky="ew")
        self.prompt_box.insert("1.0", "Create the next smallest milestone. Use memory, avoid assumptions, and include acceptance checks.")
        row = ctk.CTkFrame(prompt_card, fg_color="transparent")
        row.grid(row=2, column=0, padx=20, pady=(0, 18), sticky="ew")
        row.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.run_button = self._action_button(row, "Run Swarm", self._run_swarm, 0)
        self.compress_button = self._action_button(row, "Compress Memory", self._compress_memory, 1)
        self.status_button = self._action_button(row, "Memory Status", self._memory_status, 2)
        self.clear_button = self._action_button(row, "Clear Output", self._clear_output, 3)

        output_card = ctk.CTkFrame(self.main, corner_radius=24)
        output_card.grid(row=2, column=0, sticky="nsew")
        output_card.grid_rowconfigure(1, weight=1)
        output_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(output_card, text="Output", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=20, pady=(18, 4), sticky="w")
        self.output = ctk.CTkTextbox(output_card, corner_radius=16, wrap="word")
        self.output.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self._log("Ready. Save BYOK settings, initialize a workspace, then run a swarm.\n")

    def _entry(self, label: str, var: ctk.StringVar, row: int, show: str | None = None, browse: bool = False) -> None:
        frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame.grid(row=row, column=0, padx=24, pady=6, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkEntry(frame, textvariable=var, show=show).grid(row=1, column=0, sticky="ew", pady=(3, 0))
        if browse:
            ctk.CTkButton(frame, text="Browse", width=74, command=self._browse, fg_color=self.accent[0], hover_color=self.accent[1]).grid(row=1, column=1, padx=(8, 0), pady=(3, 0))

    def _option(self, label: str, var: ctk.StringVar, values: list[str], row: int) -> None:
        frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame.grid(row=row, column=0, padx=24, pady=6, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkOptionMenu(frame, values=values, variable=var).grid(row=1, column=0, sticky="ew", pady=(3, 0))

    def _sidebar_button(self, text: str, command, row: int) -> ctk.CTkButton:
        b = ctk.CTkButton(self.sidebar, text=text, command=command, height=40, corner_radius=12, fg_color=self.accent[0], hover_color=self.accent[1])
        b.grid(row=row, column=0, padx=24, pady=6, sticky="ew")
        return b

    def _action_button(self, parent: ctk.CTkFrame, text: str, command, col: int) -> ctk.CTkButton:
        b = ctk.CTkButton(parent, text=text, command=command, height=42, corner_radius=14, fg_color=self.accent[0], hover_color=self.accent[1])
        b.grid(row=0, column=col, padx=6, sticky="ew")
        return b

    def _project_path(self) -> Path:
        return Path(self.project_dir.get()).expanduser().resolve()

    def _browse(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.project_dir.get() or str(Path.cwd()))
        if selected:
            self.project_dir.set(selected)

    def _log(self, text: str) -> None:
        self.output.insert("end", text)
        self.output.see("end")

    def _clear_output(self) -> None:
        self.output.delete("1.0", "end")

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for b in [self.save_button, self.init_button, self.doctor_button, self.run_button, self.compress_button, self.status_button, self.open_button]:
            b.configure(state=state)

    def _run_background(self, title: str, fn) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo(APP_TITLE, "A task is already running.")
            return
        def target() -> None:
            self.task_queue.put(f"\n=== {title} ===\n")
            try:
                result = fn()
                if result:
                    self.task_queue.put(str(result) + "\n")
            except Exception as exc:
                self.task_queue.put(f"ERROR: {exc}\n")
            finally:
                self.task_queue.put("__DONE__")
        self._set_busy(True)
        self.worker = threading.Thread(target=target, daemon=True)
        self.worker.start()

    def _drain_queue(self) -> None:
        try:
            while True:
                item = self.task_queue.get_nowait()
                if item == "__DONE__":
                    self._set_busy(False)
                else:
                    self._log(item)
        except queue.Empty:
            pass
        self.after(120, self._drain_queue)

    def _save_byok(self) -> None:
        p = self._project_path()
        write_env(p, {"GDH_API_KEY": self.api_key.get(), "GDH_BASE_URL": self.base_url.get().rstrip("/"), "GDH_MODEL": self.model.get(), "GDH_FAST_MODEL": self.fast_model.get()})
        self._log(f"Saved BYOK settings to {p / '.env'}\n")

    def _init_workspace(self) -> None:
        def task() -> str:
            p = self._project_path()
            p.mkdir(parents=True, exist_ok=True)
            write_env(p, {"GDH_API_KEY": self.api_key.get(), "GDH_BASE_URL": self.base_url.get().rstrip("/"), "GDH_MODEL": self.model.get(), "GDH_FAST_MODEL": self.fast_model.get()})
            cfg = HarnessConfig(provider=ProviderConfig(base_url=self.base_url.get().rstrip("/"), model=self.model.get(), fast_model=self.fast_model.get() or None), project_name=self.project_name.get(), engine_profile=self.profile.get())
            cfg_path = save_config(p, cfg)
            ws = Workspace(p)
            AdvancedProjectMemory(ws).ensure(cfg.project_name, cfg.engine_profile)
            made = scaffold_profile(ws, cfg.engine_profile, cfg.project_name)
            return f"Workspace initialized.\nConfig: {cfg_path}\nStarter files created: {len(made)}"
        self._run_background("Initialize Workspace", task)

    def _doctor(self) -> None:
        def task() -> str:
            lines = []
            for name, exe, cmd in [("Python", "python", ["python", "--version"]), ("Git", "git", ["git", "--version"])]:
                found = which(exe)
                if found:
                    out = subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout.strip()
                    lines.append(f"[OK] {name}: {out}")
                else:
                    lines.append(f"[Missing] {name}: install required")
            lines.append(f"[{'OK' if os.getenv('UNITY_EXE') else 'Optional'}] Unity: {os.getenv('UNITY_EXE') or 'Set UNITY_EXE for Unity automation'}")
            lines.append(f"[{'OK' if os.getenv('UNREAL_ENGINE_ROOT') else 'Optional'}] Unreal: {os.getenv('UNREAL_ENGINE_ROOT') or 'Set UNREAL_ENGINE_ROOT for RunUAT'}")
            lines.append(f"[{'OK' if os.getenv('DEVKITPRO') and os.getenv('DEVKITARM') else 'Optional'}] devkitPro: {os.getenv('DEVKITPRO') or 'Set DEVKITPRO/DEVKITARM for GBA builds'}")
            return "\n".join(lines)
        self._run_background("Doctor", task)

    def _run_swarm(self) -> None:
        prompt = self.prompt_box.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning(APP_TITLE, "Enter a mission prompt first.")
            return
        def task() -> str:
            p = self._project_path()
            write_env(p, {"GDH_API_KEY": self.api_key.get(), "GDH_BASE_URL": self.base_url.get().rstrip("/"), "GDH_MODEL": self.model.get(), "GDH_FAST_MODEL": self.fast_model.get()})
            cfg = load_config(p)
            record = asyncio.run(SwarmRunner(Workspace(p), cfg).run(prompt, self.swarm.get()))
            out = "# Director Synthesis\n\n" + record["synthesis"]
            if record.get("memory_audit"):
                out += "\n\n# Memory Audit\n\n" + record["memory_audit"]
            return out
        self._run_background("Run Swarm", task)

    def _compress_memory(self) -> None:
        def task() -> str:
            p = self._project_path()
            write_env(p, {"GDH_API_KEY": self.api_key.get(), "GDH_BASE_URL": self.base_url.get().rstrip("/"), "GDH_MODEL": self.model.get(), "GDH_FAST_MODEL": self.fast_model.get()})
            cfg = load_config(p)
            runner = SwarmRunner(Workspace(p), cfg)
            return asyncio.run(runner.memory.compress(runner.client, reason="desktop manual compression", keep_recent_runs=cfg.compression_keep_recent_runs))
        self._run_background("Compress Memory", task)

    def _memory_status(self) -> None:
        def task() -> str:
            p = self._project_path()
            cfg = load_config(p)
            mem = AdvancedProjectMemory(Workspace(p))
            mem.ensure(cfg.project_name, cfg.engine_profile)
            return "\n".join(f"{k}: {v}" for k, v in mem.status(cfg.compression_trigger_chars).items())
        self._run_background("Memory Status", task)

    def _open_folder(self) -> None:
        p = self._project_path()
        p.mkdir(parents=True, exist_ok=True)
        os.startfile(p)  # type: ignore[attr-defined]

    def _theme_changed(self, value: str) -> None:
        ctk.set_appearance_mode(value)
        self.ui_settings["appearance"] = value
        save_ui_settings(self.ui_settings)

    def _accent_changed(self, value: str) -> None:
        self.accent = ACCENTS.get(value, ACCENTS["Blue"])
        self.ui_settings["accent"] = value
        save_ui_settings(self.ui_settings)
        for widget in self._all_children():
            if isinstance(widget, ctk.CTkButton):
                widget.configure(fg_color=self.accent[0], hover_color=self.accent[1])

    def _font_changed(self, value: str) -> None:
        self.ui_settings["font_scale"] = value
        save_ui_settings(self.ui_settings)
        self._apply_font_scale()

    def _apply_font_scale(self) -> None:
        scale = int(self.ui_settings.get("font_scale", "100%").replace("%", "")) / 100
        ctk.set_widget_scaling(scale)

    def _all_children(self) -> list[object]:
        items: list[object] = []
        def walk(widget) -> None:
            for child in widget.winfo_children():
                items.append(child)
                walk(child)
        walk(self)
        return items


def main() -> None:
    app = HarnessDesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
