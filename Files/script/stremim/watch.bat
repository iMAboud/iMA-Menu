@echo off

set "output="
setlocal enabledelayedexpansion

:input
set "input="
set /p "input=Watch from: "

set "prefix=Croc "

set "output=!prefix!!input!"
echo The text to be sent: !output!

for /f "delims=" %%a in ('powershell.exe -Command "!output!"') do (
    set "last_line=%%a"
)

echo %last_line% | clip
echo Last line copied to clipboard: %last_line%

:: Check if the last line is a valid URL
set "url=!last_line!"
set "pattern=https://"

:: Ensure the pattern matches the beginning of the URL
if "!url:~0,8!"=="%pattern%" (
    start "" "C:\Program Files\Nilesoft Shell\script\imstream\watch.vbs"
) else (
    echo The last line is not a valid URL, not opening the site.
)

exit
