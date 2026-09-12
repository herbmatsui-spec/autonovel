# AutoNovel Docker Development Launcher (PowerShell)
$ErrorActionPreference = "Continue"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "        AutoNovel - Docker Development Launcher         " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot\..

# 1. Detect and add Docker CLI path to PATH if needed
$dockerPaths = @(
    "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin",
    "C:\Program Files\Docker\Docker\resources\bin"
)

foreach ($p in $dockerPaths) {
    if ((Test-Path "$p\docker.exe") -and ($env:PATH -notlike "*$p*")) {
        $env:PATH = "$p;$env:PATH"
    }
}

# 2. Check docker executable
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Host "[ERROR] Docker CLI (docker.exe) not found." -ForegroundColor Red
    Write-Host "Please ensure Docker Desktop is installed." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit..."
    exit 1
}

# 3. Check .env file
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "[.env] Creating .env from .env.example..." -ForegroundColor Green
        Copy-Item ".env.example" ".env"
    }
}

# 4. Check Docker daemon status and launch Docker Desktop if not running
Write-Host "[Docker] Checking Docker daemon status..." -ForegroundColor Gray
$null = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[Docker] Docker Desktop is not running. Launching..." -ForegroundColor Yellow
    
    $desktopExes = @(
        "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe",
        "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    )
    $launched = $false
    foreach ($exe in $desktopExes) {
        if (Test-Path $exe) {
            Start-Process $exe
            $launched = $true
            break
        }
    }
    
    if (-not $launched) {
        Write-Host "[WARN] Docker Desktop application not found automatically. Please launch it manually." -ForegroundColor Yellow
    }

    Write-Host "[Docker] Waiting for Docker daemon to become ready (up to 90s)..." -ForegroundColor Cyan
    $timer = 0
    while ($timer -lt 90) {
        Start-Sleep -Seconds 3
        $timer += 3
        $null = docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[Docker] Docker daemon is ready!" -ForegroundColor Green
            break
        }
        Write-Host "  ... waiting ($timer/90s)" -ForegroundColor Gray
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[ERROR] Timed out waiting for Docker daemon." -ForegroundColor Red
        Write-Host "Please start Docker Desktop manually and wait until it is running." -ForegroundColor Yellow
        Write-Host ""
        Read-Host "Press Enter to exit..."
        exit 1
    }
} else {
    Write-Host "[Docker] Docker daemon is running." -ForegroundColor Green
}

# 5. Build and start services via Docker Compose
Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Building and starting containers..." -ForegroundColor White
Write-Host " - Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host " - Backend:  http://localhost:8200" -ForegroundColor Green
Write-Host " - Swagger:  http://localhost:8200/docs" -ForegroundColor Green
Write-Host " Note: Press Ctrl+C in this window to stop all services." -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 既存イメージが存在するか確認し、存在する場合は不要なビルドをスキップ（高速起動＆BuildKitのメモリクラッシュ防止）
$hasDb = docker images -q autonovel-db:latest 2>$null
$hasBackend = docker images -q autonovel-backend:latest 2>$null
$hasFrontend = docker images -q autonovel-frontend-dev:latest 2>$null

if (-not $hasDb) {
    Write-Host "[1/3] Building database (PostgreSQL + pgvector + Apache AGE)..." -ForegroundColor Yellow
    docker compose build db
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Database image build failed." -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }
} else {
    Write-Host "[1/3] Database image already built. (skipping build)" -ForegroundColor Green
}

if (-not $hasBackend) {
    Write-Host "[2/3] Building backend & worker..." -ForegroundColor Yellow
    docker compose build backend
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Backend image build failed." -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }
} else {
    Write-Host "[2/3] Backend image already built. (skipping build)" -ForegroundColor Green
}

if (-not $hasFrontend) {
    Write-Host "[3/3] Building frontend..." -ForegroundColor Yellow
    docker compose build frontend-dev
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Frontend image build failed." -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }
} else {
    Write-Host "[3/3] Frontend image already built. (skipping build)" -ForegroundColor Green
}

Write-Host ""
Write-Host "[Docker] Starting all services..." -ForegroundColor Green

# サービスが実際に起動して応答を返すようになってからブラウザを開く
Start-Job -ScriptBlock {
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 2
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($resp.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {}
    }
    if ($ready) {
        Start-Process "http://localhost:5173"
    }
} | Out-Null

docker compose up

Write-Host ""
Write-Host "[AutoNovel] Containers have stopped." -ForegroundColor Cyan
Read-Host "Press Enter to exit..."

