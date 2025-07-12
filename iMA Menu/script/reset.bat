@echo off
ipconfig /release
timeout /t 4 /nobreak >nul
ipconfig /renew
timeout /t 1 /nobreak >nul
ipconfig /flushdns
exit