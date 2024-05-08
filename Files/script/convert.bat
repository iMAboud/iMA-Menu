@echo off

set /p output_format=Please insert desired output format (e.g., mp4, avi, mkv): 

for /f "delims=" %%a in ('powershell Get-Clipboard') do (
    set "file_path=%%a"
)

for %%i in ("%file_path%") do set "file_name=%%~ni"

start /min ffmpeg -i "%file_path%" -c:v copy -c:a copy "%file_name%.%output_format%"

exit