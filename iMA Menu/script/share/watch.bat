@echo off

set "output="
setlocal enabledelayedexpansion

:input
set "input="
set /p "input=Watch from: "

set "prefix=Croc "

if "%input:~5%" neq "" (
    set "repeat=0"
) else if "%input:~4%" neq "" (
    set "repeat=1"
) else if "%input:~3%" neq "" (
    set "repeat=2"
) else if "%input:~2%" neq "" (
    set "repeat=3"
) else if "%input:~1%" neq "" (
    set "repeat=4"
) else (
    set "repeat=5"
)

set "repeated="
for /l %%b in (1,1,%repeat%) do (
    set "repeated=!repeated!!input:~-1!"
)

set "output=!prefix!!input!!repeated!"
echo The text to be sent: !output!

for /f "delims=" %%a in ('powershell.exe -Command "!output!"') do (
    set "last_line=%%a"
)

echo %last_line% | clip
echo Last line copied to clipboard: %last_line%

start "" "C:\Program Files\Nilesoft Shell\script\share\watch.vbs"

exit
