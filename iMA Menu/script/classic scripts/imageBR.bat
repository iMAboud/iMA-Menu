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

for /f "tokens=*" %%a in ('powershell -command "Get-Clipboard"') do (
    set "clipboard_content=%%a"
)

for %%F in ("!clipboard_content!") do (
    set "file_path=%%~dpF"
    set "file_name=%%~nxF"
)

set "output_file=!file_path!!file_name!br.png"

start /min backgroundremover -i "!clipboard_content!" -a -ae 15 -o "!output_file!"

exit
