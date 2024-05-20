' Define Stremio executable path
stremioPath = "C:\Users\" & CreateObject("WScript.Network").UserName & "\AppData\Local\Programs\LNV\Stremio-4\Stremio.exe"

' Define Chrome executable path
chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"

' Define function to get clipboard text
Function GetClipBoardText()
    Set objHTML = CreateObject("htmlfile")
    GetClipBoardText = objHTML.ParentWindow.ClipboardData.GetData("text")
End Function

' Start Stremio in the background
Set objShell = CreateObject("WScript.Shell")
objShell.Run stremioPath, 0, False

' Get URL from clipboard and open in Chrome
url = GetClipBoardText()
objShell.Run """" & chromePath & """ --start-fullscreen --app=" & url, 1, True