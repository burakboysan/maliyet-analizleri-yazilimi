#define MyAppName "Bomaksan Maliyet Analizleri"
#define MyAppPublisher "Bomaksan"
#include "version.iss"
#define MySetupSourceDir AddBackslash(SourcePath) + "..\\Bomaksan_Maliyet_Analizleri_Setup"

[Setup]
AppId={{F8B6E8A1-2665-49ED-8B59-27D67D2B9D7D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Bomaksan\Maliyet Analizleri
DefaultGroupName=Bomaksan
DisableProgramGroupPage=yes
OutputDir=..\dist_installer
OutputBaseFilename={#MyOutputBaseFilename}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
SetupIconFile=..\assets\logo_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaustu kisayolu olustur"; GroupDescription: "Ek gorevler:"

[InstallDelete]
Type: files; Name: "{app}\Bomaksan_Maliyet_Analizleri_*.exe"
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\Maliyet Analiz Yazılımı - Destek Dosyalar"
Type: files; Name: "{app}\Maliyet_Analiz_Yazilimi_Destek_Dosyalar.zip"

[Files]
Source: "{#MySetupSourceDir}\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MySetupSourceDir}\README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MySetupSourceDir}\logo_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MySetupSourceDir}\update_config.json"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#MySetupSourceDir}\update_config.template.json"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\logo_icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\logo_icon.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} uygulamasini ac"; Flags: postinstall nowait skipifsilent
