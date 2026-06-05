from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(help="Package Game Dev Harness BYOK as a Windows desktop application.")
console = Console()
APP_NAME = "Game Dev Harness BYOK"
EXE_NAME = "GameDevHarness"
DASHBOARD_EXE_NAME = "GameDevHarnessDashboard"


def root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_icon(path: Path) -> Path:
    """Create a simple local .ico if one does not exist."""
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:  # pragma: no cover - depends on optional build extra
        raise RuntimeError("Install desktop build extras first: pip install -e .[desktop-build]") from exc

    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []
    for size in sizes:
        img = Image.new("RGBA", (size, size), (15, 23, 42, 255))
        draw = ImageDraw.Draw(img)
        pad = max(2, size // 8)
        draw.rounded_rectangle((pad, pad, size - pad, size - pad), radius=max(4, size // 5), fill=(37, 99, 235, 255))
        draw.rounded_rectangle((pad * 2, pad * 2, size - pad * 2, size - pad * 2), radius=max(3, size // 7), outline=(255, 255, 255, 230), width=max(1, size // 18))
        draw.text((size * 0.33, size * 0.30), "G", fill=(255, 255, 255, 255))
        images.append(img)
    images[-1].save(path, format="ICO", sizes=[(s, s) for s in sizes])
    return path


def run(cmd: list[str], cwd: Path) -> None:
    console.print("[cyan]$[/] " + " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def pyinstaller_args(entry: str, name: str, icon: Path, out: Path, onefile: bool) -> list[str]:
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        name,
        "--icon",
        str(icon),
        "--distpath",
        str(out / "dist"),
        "--workpath",
        str(out / "build"),
        "--specpath",
        str(out / "spec"),
        "--collect-all",
        "customtkinter",
        "--hidden-import",
        "PIL._tkinter_finder",
        entry,
    ]
    if onefile:
        args.insert(6, "--onefile")
    return args


@app.command("portable")
def build_portable(
    onefile: bool = typer.Option(False, "--onefile", help="Build a single exe instead of an app folder."),
    dashboard: bool = typer.Option(True, "--dashboard/--no-dashboard", help="Also build the long-horizon dashboard."),
) -> None:
    """Build portable Windows desktop executables with PyInstaller."""
    root = root_dir()
    out = root / "packaging" / "out"
    icon = ensure_icon(root / "packaging" / "assets" / "game-dev-harness.ico")
    out.mkdir(parents=True, exist_ok=True)

    main_entry = root / "game_dev_harness" / "desktop_app.py"
    run(pyinstaller_args(str(main_entry), EXE_NAME, icon, out, onefile), root)
    if dashboard:
        dash_entry = root / "game_dev_harness" / "desktop_dashboard.py"
        run(pyinstaller_args(str(dash_entry), DASHBOARD_EXE_NAME, icon, out, onefile), root)

    console.print(f"[green]Portable build complete:[/] {out / 'dist'}")


@app.command("shortcut")
def create_shortcut(
    exe: Path = typer.Option(..., "--exe", help="Path to GameDevHarness.exe"),
    desktop: bool = typer.Option(True, "--desktop/--no-desktop"),
    start_menu: bool = typer.Option(True, "--start-menu/--no-start-menu"),
) -> None:
    """Create Windows shortcuts for a built executable."""
    exe = exe.expanduser().resolve()
    if not exe.exists():
        raise FileNotFoundError(exe)
    script = root_dir() / "packaging" / "create_shortcuts.ps1"
    run([
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-ExePath",
        str(exe),
        "-CreateDesktop",
        str(desktop).lower(),
        "-CreateStartMenu",
        str(start_menu).lower(),
    ], root_dir())


@app.command("installer")
def build_installer() -> None:
    """Build an Inno Setup installer after the portable build folder exists."""
    root = root_dir()
    iscc = shutil.which("ISCC.exe") or shutil.which("ISCC")
    if not iscc:
        raise RuntimeError("Inno Setup compiler not found. Install Inno Setup or use gdh-package portable.")
    iss = root / "packaging" / "windows_installer.iss"
    run([iscc, str(iss)], root)
    console.print(f"[green]Installer output:[/] {root / 'packaging' / 'out' / 'installer'}")


@app.command("all")
def build_all() -> None:
    """Build portable app folder, then try to build installer if Inno Setup is installed."""
    build_portable(onefile=False, dashboard=True)
    if shutil.which("ISCC.exe") or shutil.which("ISCC"):
        build_installer()
    else:
        console.print("[yellow]Inno Setup not found; skipped installer. Portable app folder is ready.[/]")


if __name__ == "__main__":
    app()
