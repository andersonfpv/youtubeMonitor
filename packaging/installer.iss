[Setup]
AppId=YouTubeMonitorDesktop
AppName=Monitor YouTube
AppVersion=2.0.1
DefaultDirName={localappdata}\Programs\YouTubeMonitor
DefaultGroupName=Monitor YouTube
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\..\..\outputs
OutputBaseFilename=Instalar-Monitor-YouTube-2.0.1
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\MonitorYouTube.exe
CloseApplications=yes
[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
[Dirs]
Name: "{localappdata}\YouTubeMonitor\data"
Name: "{localappdata}\YouTubeMonitor\data\logs"
[Files]
Source: "..\dist\MonitorYouTube\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Monitor YouTube"; Filename: "{app}\MonitorYouTube.exe"
Name: "{userdesktop}\Monitor YouTube"; Filename: "{app}\MonitorYouTube.exe"
[Run]
Filename: "{app}\MonitorYouTube.exe"; Description: "Abrir Monitor YouTube"; Flags: nowait postinstall skipifsilent
