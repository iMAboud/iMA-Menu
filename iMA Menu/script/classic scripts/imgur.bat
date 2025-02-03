@echo off
setlocal enabledelayedexpansion

REM Get file path from clipboard using PowerShell
for /f "usebackq tokens=*" %%A in (`powershell -command "Get-Clipboard"`) do (
    set "filepath=%%A"
)

REM Check if filepath variable is set
if not defined filepath (
    echo Error: No file path found in clipboard.
    exit /b 1
)

REM Upload file to Imgur using cURL
curl -X POST -H "Authorization: Client-ID 07d8ebac38608e9" -F "image=@!filepath!" https://api.imgur.com/3/image > response.json

REM Parse the response JSON to get the image link
for /f "usebackq tokens=*" %%A in (`powershell -command "(Get-Content response.json | ConvertFrom-Json).data.link"`) do (
    set "imgur_link=%%A"
)

REM Extract the direct image link starting with "https://i.imgur.com/"
for /f "tokens=3 delims=/" %%A in ("!imgur_link!") do (
    set "direct_link=%%A"
)

REM Set the direct image link to clipboard using PowerShell
powershell -command "Set-Clipboard -Value 'https://i.imgur.com/!direct_link!'"

REM Clean up temporary files
del response.json


exit