@echo off
setlocal enabledelayedexpansion

for /f "tokens=*" %%a in ('powershell -command "Get-Clipboard"') do (
    set "input_path=%%a"
)


    set /p aspect="Aspect ratio (e.g 16:9, 4:3): "
   start /min ffmpeg -i "!input_path!" -aspect !aspect! resized_video.mp4
)

exit
