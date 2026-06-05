param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [string]$CreateDesktop = "true",
  [string]$CreateStartMenu = "true"
)

$ErrorActionPreference = "Stop"
$exe = Resolve-Path $ExePath
$wsh = New-Object -ComObject WScript.Shell

function New-AppShortcut($ShortcutPath, $TargetPath) {
  $shortcut = $wsh.CreateShortcut($ShortcutPath)
  $shortcut.TargetPath = $TargetPath
  $shortcut.WorkingDirectory = Split-Path $TargetPath
  $shortcut.Description = "Game Dev Harness BYOK"
  $shortcut.IconLocation = "$TargetPath,0"
  $shortcut.Save()
}

if ($CreateDesktop -eq "true") {
  $desktopPath = [Environment]::GetFolderPath("Desktop")
  New-AppShortcut (Join-Path $desktopPath "Game Dev Harness BYOK.lnk") $exe
  Write-Host "Created desktop shortcut."
}

if ($CreateStartMenu -eq "true") {
  $startRoot = [Environment]::GetFolderPath("StartMenu")
  $folder = Join-Path $startRoot "Programs\Game Dev Harness BYOK"
  New-Item -ItemType Directory -Force -Path $folder | Out-Null
  New-AppShortcut (Join-Path $folder "Game Dev Harness BYOK.lnk") $exe
  Write-Host "Created Start Menu shortcut."
}
