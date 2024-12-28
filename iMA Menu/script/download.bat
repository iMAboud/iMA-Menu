@echo off
chcp 65001 > nul



echo                                   ▄█     ▄▄▄▄███▄▄▄▄      ▄████████ 
echo                                  ███   ▄██▀▀▀███▀▀▀██▄   ███    ███ 
echo                                  ███▌  ███   ███   ███   ███    ███ 
echo                                  ███▌  ███   ███   ███   ███    ███ 
echo                                  ███▌  ███   ███   ███ ▀███████████ 
echo                                  ███   ███   ███   ███   ███    ███ 
echo                                  ███   ███   ███   ███   ███    ███ 
echo                                  █▀     ▀█   ███   █▀    ███    █▀  
echo.                                                 
echo.

setlocal enabledelayedexpansion

:input
set "input="
set /p "input=Download from: "

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
powershell.exe -Command "!output!"
goto :input
