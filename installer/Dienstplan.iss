; Inno Setup script for Dienstplan
;
; Builds a proper Windows installer (.exe) from the PyInstaller One-Dir output.
; The installer is created AFTER running PyInstaller, so dist\Dienstplan\ must exist.
;
; Usage (command line):
;   iscc /DMyAppVersion=2.1.42 installer\Dienstplan.iss
;
; If no version is passed on the command line the fallback below is used.

#ifndef MyAppVersion
  #define MyAppVersion "2.1.0"
#endif

#define MyAppName      "Dienstplan"
#define MyAppPublisher "Fritz Winter Eisengießerei GmbH & Co. KG"
#define MyAppURL       "https://github.com/TimUx/Dienstplan"
#define MyAppExeName   "Dienstplan.exe"
#define MyAppID        "{B4E2A3C1-7F5D-4A8E-9B2F-1C3D5E7A9B0F}"

[Setup]
; Unique application ID - do NOT change after initial release
AppId={{#MyAppID}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; Install to Program Files by default
DefaultDirName={autopf}\{#MyAppName}
; Start-menu group
DefaultGroupName={#MyAppName}
; Licence shown during install
LicenseFile=..\LICENSE

; Output
OutputDir=..\dist
OutputBaseFilename=Dienstplan-Windows-Setup-v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes

; Require admin rights so the app can be installed for all users
PrivilegesRequired=admin

; Windows Vista SP1 or later
MinVersion=6.1sp1

; Installer appearance
WizardStyle=modern
WizardSizePercent=120

[Languages]
Name: "german";  MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copy the entire One-Dir output folder produced by PyInstaller.
; The {#MyAppExeName} file ends up directly in {app}\ and all
; libraries go into {app}\_internal\ (PyInstaller 6+ layout).
Source: "..\dist\Dienstplan\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}";         Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Offer to launch the application directly after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove the automatically created data directory on uninstall
Type: filesandordirs; Name: "{app}\data"

[Code]
// Show a warning if a previous installation is detected
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    // Nothing extra needed; standard upgrade handling is sufficient
  end;
end;
