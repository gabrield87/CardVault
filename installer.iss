; CardVault - Inno Setup script
; Copyright (c) 2026 Gabriel Dobre. All rights reserved.
; Built by the GitHub workflow:  ISCC /DAppVersion=1.3.0 installer.iss
; Locally: open in Inno Setup and press Compile (needs dist\CardVault from build.bat).

#define AppName "CardVault"
; The version comes from the workflow (/DAppVersion=...); fallback for local builds:
#ifndef AppVersion
  #define AppVersion "1.3.0"
#endif
#define AppPublisher "Gabriel Dobre"
#define AppYear GetDateTimeString('yyyy', '', '')

[Setup]
AppId={{6F1B4C2E-9A57-4D7B-9E35-3C1D6A2B8F10}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppCopyright=© {#AppYear} Gabriel Dobre. All rights reserved.
DefaultDirName={autopf}\CardVault
DefaultGroupName=CardVault
UninstallDisplayIcon={app}\CardVault.exe
SetupIconFile=assets\icon.ico
OutputDir=installer
OutputBaseFilename=CardVault-Setup-{#AppVersion}
Compression=lzma2/ultra
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
; Administrator rights: required for the Windows Firewall rules below.
PrivilegesRequired=admin
WizardStyle=modern
LicenseFile=LICENSE

[Languages]
; English is the default. Only languages shipped officially with Inno Setup 6 are
; used, so the build never depends on unofficial translation files.
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\CardVault\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\CardVault"; Filename: "{app}\CardVault.exe"
Name: "{group}\{cm:UninstallProgram,CardVault}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\CardVault"; Filename: "{app}\CardVault.exe"; Tasks: desktopicon

[Run]
; System-level lockdown: Windows Firewall blocks ALL traffic of CardVault.exe
; (internet and local network, inbound and outbound). Block rules take precedence
; over any allow rule. Old rules are removed first.
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""CardVault - block outbound"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""CardVault - block inbound"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""CardVault - block outbound"" dir=out action=block program=""{app}\CardVault.exe"" enable=yes profile=any"; Flags: runhidden waituntilterminated; StatusMsg: "Configuring Windows Firewall (CardVault has no network access)..."
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""CardVault - block inbound"" dir=in action=block program=""{app}\CardVault.exe"" enable=yes profile=any"; Flags: runhidden waituntilterminated
Filename: "{app}\CardVault.exe"; Description: "{cm:LaunchProgram,CardVault}"; Flags: nowait postinstall skipifsilent

; The database (default C:\Users\<user>\CardVault) is NOT deleted on uninstall.

[UninstallRun]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""CardVault - block outbound"""; Flags: runhidden waituntilterminated; RunOnceId: "CardVaultFwOut"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""CardVault - block inbound"""; Flags: runhidden waituntilterminated; RunOnceId: "CardVaultFwIn"
