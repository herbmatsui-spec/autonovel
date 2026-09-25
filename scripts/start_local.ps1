# AutoNovel Local Development Launcher (PowerShell) - Step 4
# Starts: Backend (SQLite) + Huey Worker + Frontend (Vite)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/start_local.ps1          # full launch
#   powershell -ExecutionPolicy Bypass -File scripts/start_local.ps1 -DryRun  # plan only
#   powershell -ExecutionPolicy Bypass -File scripts/start_local.ps1 -SkipInstall  # no pip/npm
#
# Robustness features:
#   - Auto-detects / creates .venv
#   - Sets HUEY_BACKEND=sqlite and DATABASE_URL deterministically
#   - Tracks child processes and kills them when this script exits (no orphans)

param(
    [switch]$DryRun,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "        AutoNovel - Local Development Launcher          " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot\..

# Track child process IDs for orphan prevention
$script:ChildPIDs = @()

# 1. Check Python and create venv if needed
Write-Host "[1/5] Checking Python environment..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    Write-Host "[venv] Creating virtual environment..." -ForegroundColor Green
    py -3.12 -m venv .venv 2>$null
    if (-not (Test-Path ".venv")) {
        py -m venv .venv
    }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path ".venv")) {
        Write-Host "[ERROR] Failed to create venv. Ensure Python 3.12+ is installed." -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }
} else {
    Write-Host "[venv] Found existing .venv" -ForegroundColor Gray
}

# 2. Activate venv and set environment variables deterministically
Write-Host "[2/5] Setting environment variables..." -ForegroundColor Yellow
$venvPath = (Resolve-Path ".venv").Path
$env:HUEY_BACKEND = "sqlite"
$env:DATABASE_URL = "sqlite:///./autonovel.db"
$env:HUEY_IMMEDIATE = "false"
Write-Host "  HUEY_BACKEND  = $env:HUEY_BACKEND" -ForegroundColor Gray
Write-Host "  DATABASE_URL  = $env:DATABASE_URL" -ForegroundColor Gray

if (-not $SkipInstall) {
    Write-Host "[3/5] Installing backend dependencies..." -ForegroundColor Yellow
    & "$venvPath\Scripts\Activate.ps1"
    py -m pip install --upgrade pip -q
    py -m pip install -e .[dev,rag] -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Backend dependency installation failed." -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }

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
} else {
    Write-Host "[3/5] Skipping dependency installation (-SkipInstall)" -ForegroundColor Gray
}

# 4. Prepare .env and run initial migration
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "[.env] Creating .env from .env.example..." -ForegroundColor Green
        Copy-Item ".env.example" ".env"
    }
}

Write-Host "[4/5] Initializing database (safe migration)..." -ForegroundColor Yellow
py scripts\init_db.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Database initialization failed." -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}

if ($DryRun) {
    Write-Host ""
    Write-Host "[DryRun] Would start the following services:" -ForegroundColor Magenta
    Write-Host "  - Backend : py -m uvicorn src.backend.server:app --port 8200" -ForegroundColor Gray
    Write-Host "  - Worker  : py -m huey.bin.huey_consumer src.backend.tasks.huey.huey" -ForegroundColor Gray
    Write-Host "  - Frontend: npm run dev (frontend/)" -ForegroundColor Gray
    Write-Host "[DryRun] Done. No processes started." -ForegroundColor Magenta
    exit 0
}

# Helper to launch a background process and track its PID
function Start-TrackedProcess {
    param(
        [string]$Name,
        [scriptblock]$ScriptBlock
    )
    $job = Start-Job -ScriptBlock $ScriptBlock
    $script:ChildPIDs += $job.Id
    Write-Host "  [$Name] started (Job Id: $($job.Id))" -ForegroundColor Green
    return $job
}

# 5. Start services in background jobs
Write-Host "[5/5] Starting Backend API (SQLite)..." -ForegroundColor Green
$backendJob = Start-TrackedProcess -Name "Backend" -ScriptBlock {
    param($vp)
    & "$vp\Scripts\Activate.ps1"
    $env:HUEY_BACKEND = "sqlite"
    $env:DATABASE_URL = "sqlite:///./autonovel.db"
    Set-Location (Split-Path $vp -Parent)
    py -m uvicorn src.backend.server:app --port 8200
} -ArgumentList $venvPath

Write-Host "[5/5] Starting Huey Worker..." -ForegroundColor Green
$workerJob = Start-TrackedProcess -Name "Worker" -ScriptBlock {
    param($vp)
    & "$vp\Scripts\Activate.ps1"
    $env:HUEY_BACKEND = "sqlite"
    $env:DATABASE_URL = "sqlite:///./autonovel.db"
    Set-Location (Split-Path $vp -Parent)
    # Note: no --skip-migrations flag; migrations are handled by scripts/init_db.py
    py -m huey.bin.huey_consumer src.backend.tasks.huey.huey
} -ArgumentList $venvPath

Write-Host "[+] Starting Frontend (Vite)..." -ForegroundColor Green
$frontendJob = Start-TrackedProcess -Name "Frontend" -ScriptBlock {
    param($root)
    Set-Location (Join-Path $root "frontend")
    npm run dev
} -ArgumentList $PSScriptRoot

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
Write-Host " Press Ctrl+C (or close this window) to stop all services." -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Wait for user interrupt; ensure children are killed on exit
try {
    while ($true) {
        Start-Sleep -Seconds 5
        $jobs = Get-Job -Id $script:ChildPIDs -ErrorAction SilentlyContinue
        $running = @($jobs | Where-Object { $_.State -eq 'Running' })
        if ($running.Count -eq 0) {
            Write-Host "[WARN] All services stopped unexpectedly." -ForegroundColor Yellow
            break
        }
    }
}
finally {
    Write-Host ""
    Write-Host "[AutoNovel] Stopping all services..." -ForegroundColor Cyan
    Get-Job -Id $script:ChildPIDs -ErrorAction SilentlyContinue | Stop-Job -PassThru | Remove-Job -Force
    Get-Job | Where-Object { $_.State -eq 'Running' } | Stop-Job -PassThru | Remove-Job -Force
    Write-Host "[AutoNovel] All services stopped." -ForegroundColor Green
}
