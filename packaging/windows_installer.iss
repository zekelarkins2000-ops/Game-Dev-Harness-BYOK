#define MyAppName "Game Dev Harness BYOK"
#define MyAppVersion "0.4.0"
#define MyAppPublisher "Game Dev Harness BYOK"
#define MyAppExeName "GameDevHarness.exe"
#define MyDashExeName "GameDevHarnessDashboard.exe"

[Setup]
AppId={{A9E6F8E5-BD96-42CC-A4B7-5A1C29A3D6B5}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Game Dev Harness BYOK
DefaultGroupName=Game Dev Harness BYOK
DisableProgramGroupPage=yes
OutputDir=out\installer
OutputBaseFilename=GameDevHarnessBYOK-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=assets\game-dev-harness.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "out\dist\GameDevHarness\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "out\dist\GameDevHarnessDashboard\*"; DestDir: "{app}\Dashboard"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Game Dev Harness BYOK"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Game Dev Harness Dashboard"; Filename: "{app}\Dashboard\{#MyDashExeName}"
Name: "{autodesktop}\Game Dev Harness BYOK"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Game Dev Harness BYOK"; Flags: nowait postinstall skipifsilent
