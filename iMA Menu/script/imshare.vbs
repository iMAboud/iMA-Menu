Dim objShell, strPath, strClipCommand, strPythonScript

' Get path from context menu and copy to clipboard
strPath = WScript.Arguments(0)
strClipCommand = "cmd /c echo " & strPath & " | clip"

' Create a shell object and run clip.exe
Set objShell = CreateObject("WScript.Shell")
objShell.Run strClipCommand, 0, True

' Set the path for the python script
strPythonScript = Chr(34) & WScript.Arguments(1) & Chr(34)

' Run the python script.
objShell.Run strPythonScript, 0, False

' Clean up the object
Set objShell = Nothing