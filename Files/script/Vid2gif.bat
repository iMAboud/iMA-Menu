@echo off
for /f "delims=" %%I in ('powershell -command "Get-Clipboard"') do set "clipboard=%%I"
for %%F in ("%clipboard%") do set "filename=%%~nF"
set "outputname=%filename%"
start /min ffmpeg -i "%clipboard%" -vf "fps=15,scale=320:-1:flags=lanczos" -c:v gif -loop 0 "%outputname%.gif"
exit