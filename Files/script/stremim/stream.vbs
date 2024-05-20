stremioPath = "C:\Users\" & CreateObject("WScript.Network").UserName & "\AppData\Local\Programs\LNV\Stremio-4\Stremio.exe"

chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
chromeURL = "https://peario.xyz"

Set objShell = CreateObject("WScript.Shell")
objShell.Run stremioPath, 0, False

objShell.Run """" & chromePath & """ --start-fullscreen --app=" & chromeURL, 1, True