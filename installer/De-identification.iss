[Setup]
AppId={{8D1F0A2C-6C32-4CE4-9D05-7A4B19D0F2C1}}
AppName=De-identification
SetupIconFile=..\assets\De-identification.ico
UninstallDisplayIcon={app}\De-identification.exe
AppVersion=0.1.0
DefaultDirName={autopf}\De-identification
DefaultGroupName=De-identification
OutputBaseFilename=De-identification-Setup
OutputDir=..\dist\windows
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

[Files]
Source: "..\dist\De-identification\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\De-identification"; Filename: "{app}\De-identification.exe"
Name: "{autodesktop}\De-identification"; Filename: "{app}\De-identification.exe"

[Run]
Filename: "{app}\De-identification.exe"; Description: "Запустить De-identification"; Flags: nowait postinstall skipifsilent
