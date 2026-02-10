; Inno Setup script for Accessible Email Client
; Build steps:
; 1) pyinstaller --clean --noconfirm --onefile --name "AccessibleEmailClient" -w accessible_email_client/main.py
; 2) Set MyAppExeDir below to your PyInstaller dist folder (e.g. C:\path\to\dist\AccessibleEmailClient)
; 3) Compile this .iss in Inno Setup

#define MyAppName "Accessible Email Client"
#define MyAppVersion "1.1"
#define MyAppPublisher "Abhishek Raut"
#define MyAppURL "https://github.com/abhisheksraut"
#define MyAppExeDir "C:\\path\\to\\dist\\AccessibleEmailClient"
#define MyAppExeName "AccessibleEmailClient.exe"

[Setup]
AppId={{D8D9A6A2-9C3F-4A6B-9B2A-9B5F6E4D0F25}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=.
OutputBaseFilename=AccessibleEmailClient-Setup
Compression=lzma
SolidCompression=yes
LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#MyAppExeDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
