[Setup]
AppId={{C6E332E1-D6FE-4A43-93A2-6F8F52B4F2D4}
AppName=TOEFL Scorer
AppVersion=1.0.0
AppPublisher=leekangmmin
DefaultDirName={autopf}\TOEFL Scorer
DefaultGroupName=TOEFL Scorer
OutputDir=..\..\dist_windows\installer
OutputBaseFilename=TOEFLScorer-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64 arm64
ArchitecturesInstallIn64BitMode=x64 arm64

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Files]
Source: "..\..\dist_windows\TOEFLScorer.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\TOEFL Scorer"; Filename: "{app}\TOEFLScorer.exe"
Name: "{autodesktop}\TOEFL Scorer"; Filename: "{app}\TOEFLScorer.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "바탕 화면 바로가기 만들기"; GroupDescription: "추가 작업:"; Flags: unchecked

[Run]
Filename: "{app}\TOEFLScorer.exe"; Description: "TOEFL Scorer 실행"; Flags: nowait postinstall skipifsilent
