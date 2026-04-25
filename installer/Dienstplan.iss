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
AppVerName={#MyAppName} {#MyAppVersion}

; Install per user by default so no admin rights are required
DefaultDirName={localappdata}\Programs\{#MyAppName}
; Start-menu group
DefaultGroupName={#MyAppName}
; Licence shown during install
LicenseFile=..\LICENSE

; Output
OutputDir=..\dist
OutputBaseFilename=Dienstplan-Windows-Setup-v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes

; No admin rights required; app runs in user context
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Close running instances automatically before upgrade to avoid file-lock errors
CloseApplications=yes
CloseApplicationsFilter={#MyAppExeName}

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
; data\ is intentionally NOT listed here.
; The [Code] section below asks the user whether to delete it.

[Code]
// Ask the user during uninstall whether to also remove the data directory.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    DataDir := ExpandConstant('{localappdata}\Dienstplan\data');
    if DirExists(DataDir) then
    begin
      if MsgBox(
        'Möchten Sie auch die gespeicherten Daten (Datenbank, Einstellungen) löschen?' + #13#10 +
        'Wenn Sie Nein wählen, bleiben Ihre Daten erhalten und können bei einer Neuinstallation weiterverwendet werden.',
        mbConfirmation, MB_YESNO) = IDYES
      then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;

// Nothing extra needed during install; standard upgrade handling is sufficient.
procedure CurStepChanged(CurStep: TSetupStep);
begin
end;
