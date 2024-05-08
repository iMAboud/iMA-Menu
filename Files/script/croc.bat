@echo off

powershell -NoExit -Command "Croc send --code SET_YOUR_CODE_HERE \"$(Get-Clipboard)\"" 
