# AutoNovel Local Development Launcher (PowerShell)
# Starts: Backend (SQLite) + Huey Worker + Frontend (Vite)
$ErrorActionPreference = "Continue"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "        AutoNovel - Local Development Launcher          " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot\..

# 1. Check Python and create venv if needed
Write-Host "[1/5] Checking Python environment..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    Write-Host "[venv] Creating virtual environment..." -ForegroundColor Green
    py -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create venv. Ensure Python 3.12+ is installed." -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }
}

# 2. Activate venv and install backend deps
Write-Host "[2/5] Installing backend dependencies..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip -q
py -m pip install -r requirements-dev.txt -q
py -m pip install -e . -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Backend dependency installation failed." -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}

# 3. Install frontend deps
Write-Host "[3/5] Installing frontend dependencies..." -ForegroundColor Yellow
if (-not (Test-Path "frontend\node_modules")) {
    Push-Location frontend
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Frontend dependency installation failed." -ForegroundColor Red
        Pop-Location
        Read-Host "Press Enter to exit..."
        exit 1
    }
    Pop-Location
} else {
    Write-Host "[frontend] node_modules exists, skipping npm install" -ForegroundColor Gray
}

# 4. Prepare .env
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "[.env] Creating .env from .env.example..." -ForegroundColor Green
        Copy-Item ".env.example" ".env"
    }
}

# 5. Start services in background jobs
Write-Host "[4/5] Starting Backend API (SQLite)..." -ForegroundColor Green
$env:HUEY_BACKEND = "sqlite"
$env:DATABASE_URL = "sqlite:///./autonovel.db"
$backendJob = Start-Job -ScriptBlock {
    param($venvPath)
    & "$venvPath\Scripts\Activate.ps1"
    $env:HUEY_BACKEND = "sqlite"
    $env:DATABASE_URL = "sqlite:///./autonovel.db"
    py -m uvicorn src.backend.server:app --reload --port 8200
} -ArgumentList (Resolve-Path .venv).Path

Write-Host "[5/5] Starting Huey Worker..." -ForegroundColor Green
$workerJob = Start-Job -ScriptBlock {
    param($venvPath)
    & "$venvPath\Scripts\Activate.ps1"
    $env:HUEY_BACKEND = "sqlite"
    $env:DATABASE_URL = "sqlite:///./autonovel.db"
    py -m huey.bin.huey_consumer src.backend.tasks.huey.huey
} -ArgumentList (Resolve-Path .venv).Path

Write-Host "[+] Starting Frontend (Vite)..." -ForegroundColor Green
$frontendJob = Start-Job -ScriptBlock {
    Push-Location frontend
    npm run dev
    Pop-Location
}

# Open browser after delay
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 10
    Start-Process "http://localhost:5173"
} | Out-Null

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " All services starting in background..." -ForegroundColor White
Write-Host " - Frontend:  http://localhost:5173" -ForegroundColor Green
Write-Host " - Backend:   http://localhost:8200" -ForegroundColor Green
Write-Host " - Swagger:   http://localhost:8200/docs" -ForegroundColor Green
Write-Host "" -ForegroundColor Yellow
Write-Host " Press Ctrl+C in this window to stop all services." -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Wait for user interrupt
try {
    while ($true) {
        Start-Sleep -Seconds 5
        # Check if jobs are still alive
        $jobs = Get-Job $backendJob, $workerJob, $frontendJob -ErrorAction SilentlyContinue
        if ($jobs.Count -eq 0 -or ($jobs | Where-Object { $_.State -eq 'Running' }).Count -eq 0) {
            Write-Host "[WARN] One or more services stopped unexpectedly." -ForegroundColor Yellow
            break
        }
    }
}
finally {
    Write-Host ""
    Write-Host "[AutoNovel] Stopping all services..." -ForegroundColor Cyan
    Get-Job $backendJob, $workerJob, $frontendJob -ErrorAction SilentlyContinue | Stop-Job | Remove-Job
    Write-Host "[AutoNovel] All services stopped." -ForegroundColor Green
    Read-Host "Press Enter to exit..."
}