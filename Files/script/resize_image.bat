@echo off
setlocal enabledelayedexpansion

for /f "tokens=*" %%a in ('powershell -command "Get-Clipboard"') do (
    set "image_path=%%a"
)

set /p dimensions="Dimensions (e.g 30x30): "

ffmpeg -i "!image_path!" -s !dimensions! resized_image.jpg

exit
