@echo off

powershell -NoLogo -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::Clear()"

start /min timeout /t 1 /nobreak >nul

echo Running Chrome...
start "" "C:\Program Files\Nilesoft Shell\script\share\stream.vbs"

timeout /t 5 /nobreak >nul

:LOOP
for /f "usebackq delims=" %%a in (`powershell -NoLogo -NoProfile -Command "Get-Clipboard"`) do (
    set "link=%%a"
)

echo %link% | findstr /R "^http[s]*://.*$" >nul
if not errorlevel 1 (
    echo Link copied to clipboard. Sending link using Croc...
    powershell -Command "Croc send --text \"%link%\" --code immmmm"
    if %errorlevel% equ 0 (
        echo Link sent successfully.
    ) else (
        echo Failed to send the link.
    )
) else (
    rem echo No link found or link not in correct format.
)

timeout /t 1 /nobreak >nul

goto :LOOP
