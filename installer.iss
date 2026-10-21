[Setup]
AppName=YAVIS
AppVersion=0.2.0
DefaultDirName={autopf}\YAVIS
DefaultGroupName=YAVIS
OutputDir=installer
OutputBaseFilename=YAVIS-Setup
SetupIconFile=yavis.ico
UninstallDisplayIcon={app}\YAVIS.exe
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; Flags: checkedonce
Name: "autostart"; Description: "YAVIS mit Windows starten"; Flags: unchecked

[Files]
Source: "dist\YAVIS\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "music\*"; DestDir: "{app}\music"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\YAVIS"; Filename: "{app}\YAVIS.exe"
Name: "{autodesktop}\YAVIS"; Filename: "{app}\YAVIS.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "YAVIS"; ValueData: """{app}\YAVIS.exe"" --minimized"; Tasks: autostart; Flags: uninsdeletevalue

[Run]
; Beim ersten Start richtet YAVIS alles selbst ein (Fortschritt im Kreis-Fenster), danach ist es sofort bereit.
Filename: "{app}\YAVIS.exe"; Description: "YAVIS jetzt starten (erste Einrichtung läuft automatisch)"; Flags: postinstall nowait skipifsilent
