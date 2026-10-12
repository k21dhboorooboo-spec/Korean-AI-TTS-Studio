#define AppName "Korean AI TTS Studio"
#define AppVersion "0.7.0"
[Setup]
AppId={{D709196C-980C-4C50-9E43-BC4A2010AB72}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\Korean AI TTS Studio
DefaultGroupName={#AppName}
OutputDir=..\dist_installer
OutputBaseFilename=KoreanAITTSStudio_Setup_v0.7
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
[Files]
Source: "..\dist\KoreanAITTSStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Korean AI TTS Studio"; Filename: "{app}\KoreanAITTSStudio.exe"
Name: "{autodesktop}\Korean AI TTS Studio"; Filename: "{app}\KoreanAITTSStudio.exe"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "바탕화면 바로가기 만들기"; GroupDescription: "추가 옵션:"
[Run]
Filename: "{app}\KoreanAITTSStudio.exe"; Description: "프로그램 실행"; Flags: nowait postinstall skipifsilent
