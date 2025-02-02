Dim objShell, strPath, strClipCommand, strPythonScript

strPath = WScript.Arguments(0)

strClipCommand = "powershell -noprofile -command ""'" & strPath & "' | Set-Clipboard"""

Set objShell = CreateObject("WScript.Shell")
objShell.Run strClipCommand, 0, True

strPythonScript = Chr(34) & WScript.Arguments(1) & Chr(34)

objShell.Run strPythonScript, 0, False

Set objShell = Nothing
