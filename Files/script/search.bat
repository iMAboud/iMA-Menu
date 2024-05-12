@echo off
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




:input
set /p searchTerm="Search for: "

if /i "%searchTerm%"=="c:" (
    echo Searching on drive C:...
    dir /s /b /a-d "C:\*%searchTerm%*"
) else if /i "%searchTerm%"=="d:" (
    echo Searching on drive D:...
    dir /s /b /a-d "D:\*%searchTerm%*"
) else (
    if exist "%searchTerm%" (
        for %%I in ("%searchTerm%") do (
            echo Opening directory containing "%%~dpI"...
            start "" /d "%%~dpI" explorer.exe /select,"%%~nxI"
        )
    ) else (
        echo Searching for "%searchTerm%"...

        set savedLocale=%chcp%
        chcp 1256 > nul

        dir /s /b /a-d "C:\*%searchTerm%*"

        dir /s /b /a-d "D:\*%searchTerm%*"

        chcp %savedLocale% > nul
    )
)

goto input

