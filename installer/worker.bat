@echo off
:: Uninstaller Worker Script - vFinal
:: This is executed silently by uninstall.vbs

:: 1. Terminate running application processes
taskkill /f /im launcher.exe > nul 2>&1

:: 2. Change directory to the script's location
cd /d "%~dp0"

:: 3. Run the application's own uninstaller as recommended by the guide
if exist "shell.exe" (
    start /wait "" "shell.exe" -u -s -t -restart
)

:: 4. Manually clean registry as a fallback
REG DELETE "HKEY_CLASSES_ROOT\CLSID\{BAE3934B-8A6A-4BFB-81BD-3FC599A1BAF1}" /f > nul 2>&1
REG DELETE "HKEY_CLASSES_ROOT\CLSID\{BAE3934B-8A6A-4BFB-81BD-3FC599A1BAF2}" /f > nul 2>&1
REG DELETE "HKEY_CLASSES_ROOT\CLSID\{BAE3934B-8A6A-4BFB-81BD-3FC599A1BAF3}" /f > nul 2>&1
REG DELETE "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\iMA Menu" /f > nul 2>&1
REG DELETE "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Shell Extensions\Approved" /v "{BAE3934B-8A6A-4BFB-81BD-3FC599A1BAF1}" /f > nul 2>&1
REG DELETE "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\ShellIconOverlayIdentifiers\@nilesoft.shell" /f > nul 2>&1
REG DELETE "HKEY_CLASSES_ROOT\Directory\shellex\ContextMenuHandlers\@nilesoft.shell" /f > nul 2>&1
REG DELETE "HKEY_CLASSES_ROOT\Drive\shellex\ContextMenuHandlers\@nilesoft.shell" /f > nul 2>&1
REG DELETE "HKEY_CLASSES_ROOT\Folder\shellex\ContextMenuHandlers\@nilesoft.shell" /f > nul 2>&1
REG DELETE "HKEY_CLASSES_ROOT\Directory\Background\shellex\ContextMenuHandlers\@nilesoft.shell" /f > nul 2>&1
REG DELETE "HKEY_CLASSES_ROOT\DesktopBackground\shellex\ContextMenuHandlers\@nilesoft.shell" /f > nul 2>&1
REG DELETE "HKEY_CLASSES_ROOT\LibraryFolder\shellex\ContextMenuHandlers\@nilesoft.shell" /f > nul 2>&1
REG DELETE "HKEY_CLASSES_ROOT\LibraryFolder\Background\shellex\ContextMenuHandlers\@nilesoft.shell" /f > nul 2>&1
REG DELETE "HKEY_CLASSES_ROOT\.nss" /f > nul 2>&1
REG DELETE "HKEY_CLASSES_ROOT\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}" /f > nul 2>&1

:: 5. Restart Explorer to release all file locks
taskkill /f /im explorer.exe > nul 2>&1
start explorer.exe

:: 6. Delete Shortcuts
if exist "%ProgramData%\Microsoft\Windows\Start Menu\Programs\iMA Menu.lnk" (
    del /f /q "%ProgramData%\Microsoft\Windows\Start Menu\Programs\iMA Menu.lnk"
)
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\iMA Menu.lnk" (
    del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\iMA Menu.lnk"
)
if exist "%USERPROFILE%\Desktop\iMA Menu.lnk" (
    del /f /q "%USERPROFILE%\Desktop\iMA Menu.lnk"
)
if exist "%PUBLIC%\Desktop\iMA Menu.lnk" (
    del /f /q "%PUBLIC%\Desktop\iMA Menu.lnk"
)

:: 7. Create and launch the finalizer script to delete the installation folder
set "InstallDir=%~dp0"
(
    echo @echo off
    echo :: This script waits for locks to be released, then deletes the application folder.
    echo timeout /t 5 /nobreak ^>nul
    echo rmdir /s /q "%InstallDir%"
    echo del "%%~f0"
) > "%TEMP%\finalizer.bat"

start "" /b cmd /c "%TEMP%\finalizer.bat"

exit
