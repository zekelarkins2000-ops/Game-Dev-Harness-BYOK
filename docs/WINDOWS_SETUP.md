# Windows 11 Setup Guide

## Required

1. Python 3.11+
2. Git for Windows
3. A model provider with an OpenAI-compatible `/chat/completions` endpoint

## Recommended PowerShell setup

```powershell
git clone https://github.com/zekelarkins2000-ops/Game-Dev-Harness-BYOK.git
cd Game-Dev-Harness-BYOK
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\scripts\setup_windows.ps1
copy .env.example .env
notepad .env
gdh doctor
```

## Engine paths

Set these in `.env` or your Windows environment when needed:

```text
UNITY_EXE=C:\Program Files\Unity\Hub\Editor\6000.0.0f1\Editor\Unity.exe
UNREAL_ENGINE_ROOT=C:\Program Files\Epic Games\UE_5.7
DEVKITPRO=C:\devkitPro
DEVKITARM=C:\devkitPro\devkitARM
```

## Common issue: Activate.ps1 blocked

Run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then reopen PowerShell.
