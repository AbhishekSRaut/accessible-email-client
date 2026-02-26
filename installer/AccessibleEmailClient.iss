; Inno Setup script for Accessible Email Client
; Build steps:
; 1) pyinstaller --clean --noconfirm --onefile --name "AccessibleEmailClient" -w accessible_email_client/main.py
; 2) Set MyAppExeDir below to your PyInstaller dist folder (e.g. C:\path\to\dist\AccessibleEmailClient)
; 3) Compile this .iss in Inno Setup

#define MyAppName "Accessible Email Client"
#define MyAppVersion "1.1"
#define MyAppPublisher "Abhishek Raut"
#define MyAppURL "https://github.com/AbhishekSRaut/accessible-email-client"
#define MyAppExeDir "E:\python\custom_email\accessible_email_client\dist\AccessibleEmailClient"
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
OutputDir=..\release
OutputBaseFilename=AccessibleEmailClient-Setup
Compression=lzma
SolidCompression=yes
LicenseFile=..\LICENSE
AppMutex=AccessibleEmailClientMutex
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; -------------------------------
; NEW: Desktop icon option
; -------------------------------
[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#MyAppExeDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; -------------------------------
; NEW: Desktop shortcut (optional)
; -------------------------------
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

; -------------------------------
; NEW: Open GitHub checkbox on Finish
; -------------------------------
Filename: "{#MyAppURL}"; Description: "Open GitHub Repository"; Flags: shellexec postinstall skipifsilent