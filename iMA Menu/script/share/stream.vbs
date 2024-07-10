chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
chromeURL = "https://www.jitbit.com/screensharing"

Set objShell = CreateObject("WScript.Shell")

' Open Chrome in fullscreen mode and navigate to the specified URL
objShell.Run """" & chromePath & """ --start-fullscreen --app=""" & chromeURL & """", 1, True
