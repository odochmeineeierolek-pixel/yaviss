[Setup]
AppName=YAVIS
AppVersion=0.1.0
DefaultDirName={autopf}\YAVIS
DefaultGroupName=YAVIS
OutputDir=installer
OutputBaseFilename=YAVIS-Setup
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

[Icons]
Name: "{group}\YAVIS"; Filename: "{app}\YAVIS.exe"
Name: "{group}\YAVIS Ersteinrichtung"; Filename: "{app}\YAVIS.exe"; Parameters: "--setup"
Name: "{autodesktop}\YAVIS"; Filename: "{app}\YAVIS.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "YAVIS"; ValueData: """{app}\YAVIS.exe"" --minimized"; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\YAVIS.exe"; Parameters: "--setup"; Description: "Ersteinrichtung (lädt KI-Modelle, einmalig)"; Flags: postinstall waituntilterminated
Filename: "{app}\YAVIS.exe"; Description: "YAVIS jetzt starten"; Flags: postinstall nowait skipifsilent unchecked
