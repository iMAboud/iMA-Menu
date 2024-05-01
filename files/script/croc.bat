@echo off

powershell -NoExit -Command "Croc send \"$(Get-Clipboard)\"" 
