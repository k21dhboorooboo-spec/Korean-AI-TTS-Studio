[Setup]
AppName=Korean AI TTS Studio Neural
AppVersion=1.1
DefaultDirName={autopf}\KoreanAITTSStudioNeural
DefaultGroupName=Korean AI TTS Studio
OutputDir=..\dist_installer
OutputBaseFilename=KoreanAITTSStudioNeural_Setup
Compression=lzma
SolidCompression=yes
[Files]
Source: "..\dist\KoreanAITTSStudioNeural\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Korean AI TTS Studio Neural"; Filename: "{app}\KoreanAITTSStudioNeural.exe"
