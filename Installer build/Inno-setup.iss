[Setup]
AppName=iMA Menu
AppVersion=1.0
AppPublisher=iMA
DefaultDirName={commonpf64}\iMA Menu
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputDir=.
OutputBaseFilename=iMA Menu
SetupIconFile=iMA Menu Installer\iMA Menu\icons\ima.ico
Compression=lzma
SolidCompression=yes

[Files]
Source: "iMA Menu Installer\iMA Menu\*"; DestDir: "{commonpf64}\iMA Menu"; Flags: recursesubdirs createallsubdirs; Excludes: "*.tmp;*.bak"
Source: "python.exe"; DestDir: "{tmp}"; Flags: ignoreversion
Source: "ffmpeg.ps1"; DestDir: "{tmp}"; Flags: ignoreversion

[Run]
Filename: "{tmp}\python.exe"; Parameters: "/quiet InstallAllUsers=1 PrependPath=1"; StatusMsg: "Installing Python..."; Flags: waituntilterminated runhidden
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command Start-Process winget -ArgumentList 'install schollz.croc --accept-source-agreements' -NoNewWindow -Wait"; StatusMsg: "Installing croc..."; Flags: runhidden waituntilterminated
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command $pythonPath = 'C:\\Program Files\\Python312\\python.exe'; Start-Process $pythonPath -ArgumentList '-m pip install -U yt-dlp[default]' -NoNewWindow -Wait"; StatusMsg: "Installing yt-dlp..."; Flags: runhidden waituntilterminated
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command $pipPath = 'C:\\Program Files\\Python312\\Scripts\\pip.exe'; Start-Process $pipPath -ArgumentList 'install backgroundremover pyautogui pyperclip pynput colorama pillow PyQt5' -NoNewWindow -Wait"; StatusMsg: "Installing Python packages..."; Flags: runhidden waituntilterminated
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{tmp}\ffmpeg.ps1"""; StatusMsg: "Installing FFMPEG..."; Flags: runhidden waituntilterminated
Filename: "{commonpf64}\iMA Menu\shell.exe"; Parameters: ""; Flags: runhidden

[Code]
var
  Progress: Integer;

procedure UpdateProgress(Value: Integer);
begin
  Progress := Progress + Value;
  WizardForm.ProgressGauge.Position := Progress;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    Progress := 0;
    WizardForm.ProgressGauge.Position := 0;
    UpdateProgress(0);
  end;
end;

procedure CurInstallProgressChanged(CurProgress, MaxProgress: Integer);
begin
  if CurProgress = MaxProgress then
  begin
    if WizardForm.StatusLabel.Caption = 'Installing Python...' then
      UpdateProgress(20)
    else if WizardForm.StatusLabel.Caption = 'Installing croc...' then
      UpdateProgress(20)
    else if WizardForm.StatusLabel.Caption = 'Installing yt-dlp...' then
      UpdateProgress(20)
    else if WizardForm.StatusLabel.Caption = 'Installing Python packages...' then
      UpdateProgress(20)
    else if WizardForm.StatusLabel.Caption = 'Installing FFMPEG...' then
      UpdateProgress(20);
  end;
end;

procedure SetMarqueeProgress(Marquee: Boolean);
begin
  if Marquee then
  begin
    WizardForm.ProgressGauge.Style := npbstMarquee;
  end
  else
  begin
    WizardForm.ProgressGauge.Style := npbstNormal;
  end;
end;

procedure InitializeWizard();
begin
  SetMarqueeProgress(True);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
end;
