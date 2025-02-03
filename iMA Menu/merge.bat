@echo off
chcp 65001 > nul

setlocal EnableDelayedExpansion

for /f "delims=" %%a in ('powershell "Get-Clipboard"') do (
    set "audio1=%%a"
)

      
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

echo !audio1! to be merged with...

echo Select the second file to merge:
set "audio2="
for /f "delims=" %%a in ('powershell -Command "Add-Type -AssemblyName System.Windows.Forms; $fileDialog = New-Object System.Windows.Forms.OpenFileDialog; $fileDialog.Filter = 'All Files (*.*)|*.*'; $fileDialog.ShowDialog() | Out-Null; $fileDialog.FileName"') do (
    set "audio2=%%a"
)

echo Selected file: !audio2!

if not defined audio1 (
    echo No file found in the clipboard.
    exit 
)

if not defined audio2 (
    echo No second file selected.
    exit 
)

ffmpeg -i "!audio1!" -i "!audio2!" -filter_complex amix=inputs=2:duration=longest output.mp3

echo Merging complete.
exit
