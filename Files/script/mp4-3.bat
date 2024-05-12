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

setlocal

where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: ffmpeg not found in PATH. Please install ffmpeg and ensure it's added to your system's PATH.
    exit /b
)

for /f "delims=" %%I in ('powershell -command "Get-Clipboard"') do set "input_file=%%I"

for %%F in ("%input_file%") do (
    set "input_filename=%%~nxF"
    set "input_extension=%%~xF"
)

set "output_extension=.mp3"

for %%F in ("%input_file%") do (
    set "output_file=%%~dpnF.mp3"
)

start /min ffmpeg -i "%input_file%" "%output_file%"

exit
