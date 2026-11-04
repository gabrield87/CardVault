; CardVault - script Inno Setup (optional, https://jrsoftware.org/isinfo.php)
; Copyright (c) 2026 Gabriel Dobre. All rights reserved.
; Deschide fisierul in Inno Setup si apasa Compile. Rezulta CardVault-Setup-1.2.0.exe.

#define AppName "CardVault"
; Versiunea vine din workflow:  ISCC /DAppVersion=1.3.0 installer.iss
; (implicit 1.2.0 când compilezi local fără s-o dai)
#ifndef AppVersion
  #define AppVersion "1.2.0"
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
; Drepturi de administrator: necesare pentru regulile Windows Firewall de mai jos.
PrivilegesRequired=admin
WizardStyle=modern
LicenseFile=LICENSE

[Languages]
Name: "romanian"; MessagesFile: "compiler:Languages\Romanian.isl"
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
; Blocare la nivel de sistem: Windows Firewall interzice ORICE trafic al CardVault.exe
; (internet și rețea locală, la intrare și la ieșire). Regulile de blocare au prioritate
; față de orice regulă de permitere. Se șterg întâi eventualele reguli vechi.
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""CardVault - blocare iesire"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""CardVault - blocare intrare"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""CardVault - blocare iesire"" dir=out action=block program=""{app}\CardVault.exe"" enable=yes profile=any"; Flags: runhidden waituntilterminated; StatusMsg: "Configurez Windows Firewall (CardVault fara retea)..."
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""CardVault - blocare intrare"" dir=in action=block program=""{app}\CardVault.exe"" enable=yes profile=any"; Flags: runhidden waituntilterminated
Filename: "{app}\CardVault.exe"; Description: "{cm:LaunchProgram,CardVault}"; Flags: nowait postinstall skipifsilent

; Baza de date (implicit C:\Users\<utilizator>\CardVault) NU se sterge la dezinstalare.

[UninstallRun]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""CardVault - blocare iesire"""; Flags: runhidden waituntilterminated; RunOnceId: "CardVaultFwOut"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""CardVault - blocare intrare"""; Flags: runhidden waituntilterminated; RunOnceId: "CardVaultFwIn"
