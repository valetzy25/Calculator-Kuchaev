;---------------------------------------
; Установщик "Калькулятор"
;---------------------------------------

[Setup]
AppId={{7C1E7F6E-2E11-4C1B-9D93-FA11B2C1C001}}
AppName=Калькулятор
AppVersion=2.1
VersionInfoVersion=2.1.0.0
AppPublisher=Кучаев Влад и Шурупов Олег
AppPublisherURL=https://dalink.to/kuchaev_vlad
AppSupportURL=https://dalink.to/kuchaev_vlad
AppComments=Разработчики: Кучаев Влад и Шурупов Олег

; Установка в Program Files (автоматически правильная папка x64)
DefaultDirName={autopf}\Калькулятор
UsePreviousAppDir=yes

DefaultGroupName=Калькулятор
OutputBaseFilename=CalculatorSetup
OutputDir=.
SetupIconFile=icon.ico

Compression=lzma
SolidCompression=yes
WizardStyle=modern

; Современные идентификаторы архитектуры
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Требуются админ-права
PrivilegesRequired=admin
CloseApplications=yes

UninstallDisplayIcon={app}\Calculator.exe
UninstallDisplayName=Калькулятор
AppCopyright=© 2025 Кучаев Влад и Шурупов Олег

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
; Копируем всё из dist\Calculator в папку приложения
Source: "dist\Calculator\*"; \
    DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Калькулятор"; \
    Filename: "{app}\Calculator.exe"; \
    IconFilename: "{app}\Calculator.exe"

Name: "{commondesktop}\Калькулятор"; \
    Filename: "{app}\Calculator.exe"; \
    IconFilename: "{app}\Calculator.exe"; \
    Tasks: desktopicon

[Tasks]
Name: "desktopicon"; \
    Description: "Создать ярлык на рабочем столе"; \
    GroupDescription: "Дополнительно:"; \
    Flags: unchecked

[Run]
Filename: "{app}\Calculator.exe"; \
    Description: "Запустить Калькулятор"; \
    Flags: nowait postinstall skipifsilent

[Messages]
SetupAppTitle=Калькулятор — разработчики: Кучаев Влад и Шурупов Олег
WelcomeLabel2=Это установщик программы "Калькулятор". Разработчики: Кучаев Влад и Шурупов Олег.
FinishedLabel=Установка программы "Калькулятор" завершена. Разработчики: Кучаев Влад и Шурупов Олег.
