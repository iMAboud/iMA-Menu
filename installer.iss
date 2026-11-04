#define AppName "iMA Menu"
#define AppVersion "2.0.0.3"
#define AppPublisher "iMA"
#define AppExeName "shell.exe"
#define AppFolder "iMA Menu"


[Setup]
AppId={{C6E2E1A4-F2D7-4B5C-9E4B-8E2E8C2B3F6D}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
; Force installation to Program Files (All Users)
DefaultDirName={pf}\{#AppFolder}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=iMA Menu
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Force Administrative privileges (Install for all users)
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
DirExistsWarning=no
; UI Customization
DisableProgramGroupPage=yes
DisableReadyPage=yes
DisableDirPage=yes
DisableWelcomePage=no
DisableFinishedPage=no
ChangesEnvironment=yes
CloseApplications=yes
RestartApplications=yes
; Handle Launcher closing
AppMutex=iMAMenuLauncherMutex
; Icon for the installer
SetupIconFile=iMA Menu\ima.ico
UninstallDisplayIcon={app}\ima.ico
UninstallDisplayName={#AppName}
; Digital signing configuration (Uncomment when sign tool is configured)
; SignTool=mysigntool
; SignedUninstaller=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; 1. Launcher: Always replace (must be closed)
Source: "iMA Menu\Launcher\launcher.exe"; DestDir: "{app}\Launcher"; Flags: ignoreversion
Source: "iMA Menu\Launcher\*"; DestDir: "{app}\Launcher"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "launcher.exe"

; 2. Shell components: Replace ONLY if version is higher
Source: "iMA Menu\shell.dll"; DestDir: "{app}"; Flags: restartreplace; Check: IsShellUpdateNeeded
Source: "iMA Menu\shell.exe"; DestDir: "{app}"; Flags: ignoreversion restartreplace; Check: IsShellUpdateNeeded

; 3. Configuration & Themes: Copy ONLY if they don't exist (Preserve user config)
Source: "iMA Menu\theme\*"; DestDir: "{app}\theme"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist
Source: "iMA Menu\imports\*"; DestDir: "{app}\imports"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist
Source: "iMA Menu\shell.nss"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

; 4. Support files: Copy only if missing
Source: "iMA Menu\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist; Excludes: "Launcher\*,theme\*,imports\*,shell.dll,shell.exe,shell.nss"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"

[Registry]
; 1. Clean up modern context menu TreatAs redirection and HKCU overrides on uninstall
Root: HKA; Subkey: "Software\Classes\CLSID\{{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\TreatAs"; Flags: uninsdeletekey dontcreatekey
Root: HKA; Subkey: "Software\Classes\CLSID\{{51668040-5e31-4023-bbe3-149163bd80f1}\TreatAs"; Flags: uninsdeletekey dontcreatekey
Root: HKCU; Subkey: "Software\Classes\CLSID\{{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}"; Flags: uninsdeletekey dontcreatekey
Root: HKCU; Subkey: "Software\Classes\CLSID\{{51668040-5e31-4023-bbe3-149163bd80f1}"; Flags: uninsdeletekey dontcreatekey

; 2. Remove the app's CLSID and handler entries
Root: HKA; Subkey: "Software\Classes\CLSID\{{73ADF364-5A70-45E1-BD9D-F3D4636956BA}"; Flags: uninsdeletekey dontcreatekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Shell Extensions\Approved"; ValueType: none; ValueName: "{{73ADF364-5A70-45E1-BD9D-F3D4636956BA}"; Flags: uninsdeletevalue
Root: HKA; Subkey: "*\shellex\ContextMenuHandlers\Shell"; Flags: uninsdeletekey dontcreatekey
Root: HKA; Subkey: "Directory\shellex\ContextMenuHandlers\Shell"; Flags: uninsdeletekey dontcreatekey
Root: HKA; Subkey: "Directory\Background\shellex\ContextMenuHandlers\Shell"; Flags: uninsdeletekey dontcreatekey
Root: HKA; Subkey: "Drive\shellex\ContextMenuHandlers\Shell"; Flags: uninsdeletekey dontcreatekey
Root: HKA; Subkey: "Folder\shellex\ContextMenuHandlers\Shell"; Flags: uninsdeletekey dontcreatekey

[Run]
; Registration command: shell.exe -register -restart
; Only run if a shell update actually happened or if it's a new install
Filename: "{app}\{#AppExeName}"; Parameters: "-register -treat -silent -restart"; Flags: waituntilterminated; StatusMsg: "Registering shell extension and refreshing desktop..."; Check: IsShellUpdateNeeded

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[UninstallRun]
; 1. Unregister the app logic
Filename: "{app}\{#AppExeName}"; Parameters: "-unregister -treat -silent"; Flags: waituntilterminated; RunOnceId: "UnregShell"; StatusMsg: "Unregistering shell extension..."
; 2. Fallback: Unregister the DLL
Filename: "regsvr32.exe"; Parameters: "/u /s ""{app}\shell.dll"""; Flags: waituntilterminated

[Code]
var
  DirText: TNewStaticText;
  DirBrowseBtn: TNewButton;
  ShellUpdateChecked: Boolean;
  ShellUpdateNeeded: Boolean;

function CompareVersion(V1, V2: String): Integer;
var
  P1, P2, Num1, Num2: Integer;
begin
  Result := 0;
  while (Length(V1) > 0) or (Length(V2) > 0) do
  begin
    P1 := Pos('.', V1);
    if P1 > 0 then
    begin
      Num1 := StrToIntDef(Copy(V1, 1, P1 - 1), 0);
      Delete(V1, 1, P1);
    end
    else
    begin
      Num1 := StrToIntDef(V1, 0);
      V1 := '';
    end;

    P2 := Pos('.', V2);
    if P2 > 0 then
    begin
      Num2 := StrToIntDef(Copy(V2, 1, P2 - 1), 0);
      Delete(V2, 1, P2);
    end
    else
    begin
      Num2 := StrToIntDef(V2, 0);
      V2 := '';
    end;

    if Num1 > Num2 then
    begin
      Result := 1;
      Exit;
    end
    else if Num1 < Num2 then
    begin
      Result := -1;
      Exit;
    end;
  end;
end;

function IsShellUpdateNeeded: Boolean;
var
  ExistingVersion: String;
begin
  if not ShellUpdateChecked then
  begin
    ShellUpdateNeeded := True;
    // Check shell.dll version
    if FileExists(ExpandConstant('{app}\shell.dll')) then
    begin
      if GetVersionNumbersString(ExpandConstant('{app}\shell.dll'), ExistingVersion) then
      begin
        if CompareVersion('{#AppVersion}', ExistingVersion) < 0 then
          ShellUpdateNeeded := False;
      end;
    end;
    
    // If shell.dll was same, double check shell.exe just in case
    if not ShellUpdateNeeded then
    begin
       if FileExists(ExpandConstant('{app}\shell.exe')) then
       begin
         if GetVersionNumbersString(ExpandConstant('{app}\shell.exe'), ExistingVersion) then
         begin
           if CompareVersion('{#AppVersion}', ExistingVersion) > 0 then
             ShellUpdateNeeded := True;
         end;
       end;
    end;

    ShellUpdateChecked := True;
  end;
  Result := ShellUpdateNeeded;
end;

procedure BrowseButtonClick(Sender: TObject);
var
  Dir: string;
begin
  Dir := WizardForm.DirEdit.Text;
  if BrowseForFolder('Select Installation Folder', Dir, True) then
    WizardForm.DirEdit.Text := Dir;
end;

procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel1.Caption := 'Install ' + '{#AppName}';
  WizardForm.WelcomeLabel2.Caption := 'Click Install to continue with the default settings, or change the installation path below.';

  DirText := TNewStaticText.Create(WizardForm);
  DirText.Parent := WizardForm.WelcomePage;
  DirText.Caption := 'Installation Folder:';
  DirText.Left := WizardForm.WelcomeLabel2.Left;
  DirText.Top := 180;
  DirText.Font.Style := [fsBold];
  DirText.Visible := True;

  DirBrowseBtn := TNewButton.Create(WizardForm);
  DirBrowseBtn.Parent := WizardForm.WelcomePage;
  DirBrowseBtn.Caption := 'Change...';
  DirBrowseBtn.Width := 75;
  DirBrowseBtn.Left := WizardForm.WelcomePage.Width - DirBrowseBtn.Width - 10;
  DirBrowseBtn.Top := DirText.Top + DirText.Height + 5;
  DirBrowseBtn.OnClick := @BrowseButtonClick;
  DirBrowseBtn.Visible := True;

  WizardForm.DirEdit.Parent := WizardForm.WelcomePage;
  WizardForm.DirEdit.Left := DirText.Left;
  WizardForm.DirEdit.Top := DirText.Top + DirText.Height + 5;
  WizardForm.DirEdit.Width := DirBrowseBtn.Left - DirText.Left - 10;
  WizardForm.DirEdit.Visible := True;

  WizardForm.NextButton.Caption := '&Install';
  WizardForm.BringToFront;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpWelcome then
    WizardForm.NextButton.Caption := '&Install';
end;

procedure AddToPath(PathToAdd: string);
var
  OldPath: string;
  NewPath: string;
begin
  // Standard Admin PATH modification (HKLM)
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', OldPath) then
    OldPath := '';

  if Pos(UpperCase(PathToAdd), UpperCase(OldPath)) = 0 then
  begin
    NewPath := OldPath;
    if (NewPath <> '') and (NewPath[Length(NewPath)] <> ';') then NewPath := NewPath + ';';
    NewPath := NewPath + PathToAdd;
    RegWriteStringValue(HKEY_LOCAL_MACHINE, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', NewPath);
  end;
end;

procedure RemoveFromPath(PathToRemove: string);
var
  OldPath: string;
  NewPath: string;
  P: Integer;
begin
  if RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', OldPath) then
  begin
    P := Pos(UpperCase(PathToRemove), UpperCase(OldPath));
    if P > 0 then
    begin
      NewPath := OldPath;
      Delete(NewPath, P, Length(PathToRemove));
      StringChangeEx(NewPath, ';;', ';', True);
      if (Length(NewPath) > 0) and (NewPath[Length(NewPath)] = ';') then Delete(NewPath, Length(NewPath), 1);
      if (Length(NewPath) > 0) and (NewPath[1] = ';') then Delete(NewPath, 1, 1);
      RegWriteStringValue(HKEY_LOCAL_MACHINE, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', NewPath);
    end;
  end;
end;

procedure RestartExplorer;
var
  ResultCode: Integer;

begin
  // Forcefully kill explorer to release file locks
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/f /im explorer.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(1000); // Give Windows a moment to clean up
  // Properly restart the shell
  if not Exec(ExpandConstant('{win}\explorer.exe'), '', '', SW_SHOWNORMAL, ewNoWait, ResultCode) then
    ShellExec('open', ExpandConstant('{win}\explorer.exe'), '', '', SW_SHOWNORMAL, ewNoWait, ResultCode);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;

begin
  Result := '';
  // Only proceed with unregister/restart if we actually need to update the shell
  // If it's a fresh install (no shell.dll), we don't need to unhook/restart before copying
  if IsShellUpdateNeeded and FileExists(ExpandConstant('{app}\shell.dll')) then
  begin
    // Extension exists and needs update: unregister and restart explorer to unlock
    if FileExists(ExpandConstant('{app}\shell.exe')) then
    begin
      Exec(ExpandConstant('{app}\shell.exe'), '-unregister -treat -silent', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Sleep(500);

    end;
    RestartExplorer;
    Sleep(2000);
  end;
end;

procedure GrantPermissions(Path: string);
var
  ResultCode: Integer;

begin
  // Grant Full Control to Administrators group (S-1-5-32-544)
  Exec(ExpandConstant('{sys}\icacls.exe'), '"' + Path + '" /grant *S-1-5-32-544:(OI)(CI)F /T /C /Q', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  // Grant Full Control to Authenticated Users (S-1-5-11) to ensure the launcher can update itself without admin prompts if needed
  Exec(ExpandConstant('{sys}\icacls.exe'), '"' + Path + '" /grant *S-1-5-11:(OI)(CI)F /T /C /Q', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    AddToPath(ExpandConstant('{app}\Launcher\lib'));
    // Ensure the application folder has correct permissions for self-updates
    GrantPermissions(ExpandConstant('{app}'));
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;

begin
  if CurUninstallStep = usUninstall then
  begin
    RemoveFromPath(ExpandConstant('{app}\Launcher\lib'));

    // Unregister cleanly while shell.dll still exists on disk
    if FileExists(ExpandConstant('{app}\shell.exe')) then
      Exec(ExpandConstant('{app}\shell.exe'), '-unregister -treat -silent', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    // Terminate locking processes before file deletion
    Exec(ExpandConstant('{sys}\taskkill.exe'), '/f /im launcher.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec(ExpandConstant('{sys}\taskkill.exe'), '/f /im ima_updater.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec(ExpandConstant('{sys}\taskkill.exe'), '/f /im explorer.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Sleep(1000);

    // Clean up modern context menu TreatAs redirection and HKCU overrides
    RegDeleteKeyIncludingSubkeys(HKEY_LOCAL_MACHINE, 'Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\TreatAs');
    RegDeleteKeyIncludingSubkeys(HKEY_LOCAL_MACHINE, 'Software\Classes\CLSID\{51668040-5e31-4023-bbe3-149163bd80f1}\TreatAs');
    RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER, 'Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}');
    RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER, 'Software\Classes\CLSID\{51668040-5e31-4023-bbe3-149163bd80f1}');

    // If any 3rd party process still holds shell.dll, rename it and schedule deletion on reboot
    if FileExists(ExpandConstant('{app}\shell.dll')) then
    begin
      if not DeleteFile(ExpandConstant('{app}\shell.dll')) then
      begin
        if FileExists(ExpandConstant('{app}\shell.dll.bak')) then
          DeleteFile(ExpandConstant('{app}\shell.dll.bak'));
        RenameFile(ExpandConstant('{app}\shell.dll'), ExpandConstant('{app}\shell.dll.bak'));
        RestartReplace(ExpandConstant('{app}\shell.dll.bak'), '');
      end;
    end;
  end;
  
  if CurUninstallStep = usPostUninstall then
  begin
    // Gracefully notify the user or refresh shell without aggressive taskkill if possible
    // But if we must restart explorer, we do it with a slight delay to ensure uninstallation is clean
    Sleep(1000);
    Exec(ExpandConstant('{sys}\taskkill.exe'), '/f /im explorer.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Sleep(500);

    DelTree(ExpandConstant('{app}'), True, True, True);
    if not ShellExec('open', ExpandConstant('{win}\explorer.exe'), '', '', SW_SHOWNORMAL, ewNoWait, ResultCode) then
       Exec(ExpandConstant('{win}\explorer.exe'), '', '', SW_SHOWNORMAL, ewNoWait, ResultCode);
  end;
end;

