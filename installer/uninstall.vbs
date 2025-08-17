Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
workerBat = fso.BuildPath(scriptDir, "worker.bat")

If fso.FileExists(workerBat) Then
    Set shellApp = CreateObject("Shell.Application")
    shellApp.ShellExecute fso.GetFileName(workerBat), "", scriptDir, "runas", 0
Else
    MsgBox "Error: worker.bat not found. Please ensure both uninstall.vbs and worker.bat are in the iMA Menu directory.", 16, "Uninstaller Error"
End If