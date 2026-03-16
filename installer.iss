; Wbo BAMP — установщик (Inno Setup 6)
; Сборка: build_installer.bat передаёт /DMyOutputDir="полный_путь" чтобы exe попал в нужную папку

#define MyAppName "Wbo BAMP"
#define MyAppVersion "0.1.2.2.1"
#define MyAppPublisher "Wbo BAMP"
#define MyAppExeName "WboBAMP.exe"
#define MyAppAssocName "Wbo BAMP"
#ifndef MyOutputDir
#define MyOutputDir "installer_output"
#endif

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Стандартный путь: диск C, Program Files
DisableProgramGroupPage=yes
; Баннер и изображения мастера — PNG из папки dist\INSTALL
WizardImageFile=dist\INSTALL\installer_banner.png
WizardSmallImageFile=dist\INSTALL\installer_small.png
; Иконка установщика и приложения
SetupIconFile=Assets\images\faicon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; Папка вывода: из /DMyOutputDir или по умолчанию installer_output
OutputDir={#MyOutputDir}
OutputBaseFilename=WboBAMP_Setup_{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
; Стандартные фразы мастера: Default.isl (всегда есть). Подписи к задачам и т.п. — русские в скрипте ниже.
Name: "russian"; MessagesFile: "compiler:Default.isl"

[Tasks]
; По умолчанию задачи отмечены (галочка). Снять по умолчанию: добавить Flags: unchecked
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные значки:"
Name: "quicklaunchicon"; Description: "Создать ярлык на панели быстрого запуска"; GroupDescription: "Дополнительные значки:"

[Files]
; Вся папка dist\WboBAMP копируется в {app}
Source: "dist\WboBAMP\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Удалить {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: dirifempty; Name: "{app}"
