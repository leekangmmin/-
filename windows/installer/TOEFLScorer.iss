; Inno Setup 스크립트 — TOEFL Writing Windows 설치 패키지.
; 버전은 CI에서 /DAppVersion=<x> 로 덮어쓸 수 있고, 없으면 아래 기본값을 쓴다.
; 실행 파일 이름은 app/version.py의 APP_BUNDLE_NAME("TOEFL Writing")과 일치해야 한다.
#ifndef AppVersion
  #define AppVersion "0.6.0"
#endif
#define AppName "TOEFL Writing"
#define ExeName "TOEFL Writing.exe"

[Setup]
AppId={{C6E332E1-D6FE-4A43-93A2-6F8F52B4F2D4}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=leekangmin
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=..\..\dist_windows\installer
OutputBaseFilename=TOEFL-Writing-Setup-{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64 arm64
ArchitecturesInstallIn64BitMode=x64 arm64
SetupIconFile=..\..\packaging\resources\app.ico
UninstallDisplayIcon={app}\{#ExeName}

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\..\dist_windows\{#ExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#ExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "바탕 화면 바로가기 만들기"; GroupDescription: "추가 작업:"; Flags: unchecked

[Run]
Filename: "{app}\{#ExeName}"; Description: "{#AppName} 실행"; Flags: nowait postinstall skipifsilent
