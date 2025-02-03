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

for /f "usebackq delims=" %%a in (`powershell -command "Get-Clipboard"`) do (
    set "file_path=%%a"
)

if not exist "!file_path!" (
    echo File does not exist!
    pause
    exit /b
)

ffmpeg -i "!file_path!" -hide_banner 2>&1 | find "Video:" >nul
if %errorlevel% equ 0 (
    set "is_video=true"
) else (
    set "is_video=false"
)

if !is_video! == true (
   start /min ffmpeg -i "!file_path!" -vf scale=-1:720 -c:a copy "!file_path!.compressed.mp4"
) else (
    echo The file is not a video.
)

exit
