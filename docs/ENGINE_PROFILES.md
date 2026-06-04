# Engine Profiles

## `gba`

Creates a starter homebrew shape and memory plan for devkitPro/devkitARM projects. Local GBA builds require devkitPro.

## `unity`

Creates starter Unity C# scripts and an editor build command.

Example batch build command:

```powershell
& $env:UNITY_EXE -batchmode -quit -projectPath . -executeMethod BuildCommand.BuildWindows -logFile Logs\unity-build.log
```

## `unreal`

Creates a minimal `.uproject` placeholder. Real Unreal projects may require opening the project once in the Editor or generating project files.

Example AutomationTool location:

```powershell
$env:UNREAL_ENGINE_ROOT\Engine\Build\BatchFiles\RunUAT.bat
```

## `webapp`

Creates a tiny static app in `app/`.

## `desktop`

Creates a tiny Python app placeholder.
