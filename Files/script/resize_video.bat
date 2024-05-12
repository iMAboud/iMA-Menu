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
    set "input_path=%%a"
)


    set /p aspect="Aspect ratio (e.g 16:9, 4:3): "
   start /min ffmpeg -i "!input_path!" -aspect !aspect! resized_video.mp4
)

exit
