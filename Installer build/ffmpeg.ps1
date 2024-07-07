
if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "`nInstalling Chocolatey..." -ForegroundColor Cyan
    Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; 
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
}


Write-Host "`nInstalling FFMPEG..." -ForegroundColor Cyan
choco install ffmpeg -y
Write-Host "Done." -ForegroundColor Green

ffmpeg -version

Write-Host "`nThe above was returned after running 'ffmpeg -version'" -ForegroundColor Green

