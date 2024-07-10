@echo off
chcp 65001 > nul



echo                                          ▄█     ▄▄▄▄███▄▄▄▄      ▄████████ 
echo                                         ███   ▄██▀▀▀███▀▀▀██▄   ███    ███ 
echo                                         ███▌  ███   ███   ███   ███    ███ 
echo                                         ███▌  ███   ███   ███   ███    ███ 
echo                                         ███▌  ███   ███   ███ ▀███████████ 
echo                                         ███   ███   ███   ███   ███    ███ 
echo                                         ███   ███   ███   ███   ███    ███ 
echo                                         █▀     ▀█   ███   █▀    ███    █▀  
echo.                                                 
echo.

setlocal enabledelayedexpansion

:input
set "input="
set /p "input=Download from: "
set "prefix=Croc "
  set "output=!prefix!!input!"

powershell.exe -Command "!output!"
goto :input