# AutoNovel Docker Stopper (PowerShell)
$ErrorActionPreference = "Continue"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "        AutoNovel - Docker Containers Stopper           " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot\..

# Detect and add Docker CLI path
$dockerPaths = @(
    "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin",
    "C:\Program Files\Docker\Docker\resources\bin"
)
foreach ($p in $dockerPaths) {
    if ((Test-Path "$p\docker.exe") -and ($env:PATH -notlike "*$p*")) {
        $env:PATH = "$p;$env:PATH"
    }
}

Write-Host "[Docker] Stopping and removing containers..." -ForegroundColor Yellow
docker compose down

Write-Host ""
Write-Host "[AutoNovel] All containers have been stopped successfully." -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit..."
