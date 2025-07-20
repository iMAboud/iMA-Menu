if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\Add-Exclusion.ps1`""
    Stop-Process -Id $PID
}

$pathToExclude = (Get-Clipboard).Trim('"')

if (-not [string]::IsNullOrWhiteSpace($pathToExclude)) {
    try {
        Add-MpPreference -ExclusionPath $pathToExclude -ErrorAction Stop
        Write-Host "Success" -ForegroundColor Green -NoNewline
        Write-Host ": '$pathToExclude' has been added to the Windows Defender exclusion list."
    }
    catch {
        Write-Host "Error: Failed to add exclusion. The error was: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Please make sure you are running this script as an Administrator." -ForegroundColor Red
    }
}
else {
    Write-Host "The clipboard is empty. Please copy a file or folder path first." -ForegroundColor Yellow
}
