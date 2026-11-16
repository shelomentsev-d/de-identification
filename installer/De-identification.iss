[Setup]
AppId={{8D1F0A2C-6C32-4CE4-9D05-7A4B19D0F2C1}}
AppName=de-Identification
SetupIconFile=..\assets\de-Identification.ico
UninstallDisplayIcon={app}\de-Identification.exe
AppVersion=0.1.4
DefaultDirName={autopf}\de-Identification
DefaultGroupName=de-Identification
OutputBaseFilename=de-Identification-Setup
OutputDir=..\dist\windows
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

[Files]
Source: "..\dist\de-Identification\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\de-Identification"; Filename: "{app}\de-Identification.exe"
Name: "{autodesktop}\de-Identification"; Filename: "{app}\de-Identification.exe"

[Run]
Filename: "{app}\de-Identification.exe"; Description: "Запустить de-Identification"; Flags: nowait postinstall skipifsilent
