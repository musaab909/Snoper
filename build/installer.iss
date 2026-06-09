; ============================================================
;  Snoper - Inno Setup installer script
;  Requires Inno Setup 6 (https://jrsoftware.org/isdl.php).
;  Build the exe first (build\build_windows.bat), then compile
;  this script with the Inno Setup Compiler, or run
;  build\make_installer.bat.
;  Produces: build\Output\Snoper-Setup.exe
; ============================================================

#define AppName "Snoper"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppPublisher "Snoper"
#define AppExeName "Snoper.exe"

[Setup]
AppId={{8E2C9A41-7B3D-4E6F-9A1C-SNOPER000001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=Snoper-Setup
VersionInfoVersion={#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Per-user install needs no admin; use lowest privileges:
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
; Silent auto-updates: close the running app so its exe can be replaced.
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
Name: "startupicon"; Description: "Start Snoper automatically when Windows starts"; Flags: unchecked

[Files]
; The PyInstaller one-file exe produced in dist\
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; Optional auto-start on login (per-user Run key) when the task is selected.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "Snoper"; ValueData: """{app}\{#AppExeName}"""; \
    Flags: uninsdeletevalue; Tasks: startupicon

[Run]
; Interactive install: offer to launch. Also relaunch after a silent auto-update.
Filename: "{app}\{#AppExeName}"; Description: "Launch Snoper now"; \
    Flags: nowait postinstall skipifsilent
Filename: "{app}\{#AppExeName}"; Flags: nowait runasoriginaluser; Check: WizardSilent
