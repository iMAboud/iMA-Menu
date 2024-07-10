@echo off
setlocal enabledelayedexpansion

for /f "usebackq tokens=*" %%A in (`powershell -command "Get-Clipboard"`) do (
    set "filepath=%%A"
)

if not defined filepath (
    echo Error: No file path found in clipboard.
    exit /b 1
)

curl -X POST -H "Authorization: Client-ID YOUR_ID" -F "image=@!filepath!" https://api.imgur.com/3/image > response.json

for /f "usebackq tokens=*" %%A in (`powershell -command "(Get-Content response.json | ConvertFrom-Json).data.link"`) do (
    set "imgur_link=%%A"
)

for /f "tokens=3 delims=/" %%A in ("!imgur_link!") do (
    set "direct_link=%%A"
)

powershell -command "Set-Clipboard -Value 'https://i.imgur.com/!direct_link!'"

del response.json


exit
