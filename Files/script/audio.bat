@echo off
setlocal EnableDelayedExpansion

set "current_dir=%cd%"

set "ffmpeg_location=C:\Program Files\ffmpeg\bin\ffmpeg.exe"

powershell -Command "(Get-Clipboard) -match '^https://www.youtube.com/'" > nul 2>&1
if not errorlevel 1 (
    set /p "video_url=" < nul
    for /f "delims=" %%a in ('powershell -command "Get-Clipboard"') do set "video_url=%%a"
    
    echo Retrieved YouTube URL: !video_url!
    
    start /min yt-dlp -x --audio-format mp3 --no-playlist --ffmpeg-location "!ffmpeg_location!" -o "%%current_dir%%\%%(title)s.%%(ext)s" !video_url!
) else (
    exit /b
)

exit
