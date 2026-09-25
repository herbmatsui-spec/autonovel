# AutoNovel Local Stop Script (PowerShell) - Step 6
# Gracefully terminates Uvicorn, Vite, and Huey processes occupying ports 8200 / 5173.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/stop_local.ps1
#
# Strategy:
#   1. Find PIDs listening on ports 8200 and 5173 (Get-NetTCPConnection).
#   2. Also match python/node processes with AutoNovel-specific command lines.
#   3. Send graceful termination (CloseMainWindow / taskkill without /F first),
#      then force-kill only if still alive after a short wait.

$ErrorActionPreference = "Continue"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "        AutoNovel - Local Service Stopper               " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$targetPorts = @(8200, 5173)
$stoppedPIDs = @()

function Stop-ProcessGracefully {
    param([int]$ProcessId, [string]$Label)

    if ($stoppedPIDs -contains $ProcessId) { return }
    $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $proc) { return }

    Write-Host "  [$Label] Stopping PID $ProcessId ($($proc.ProcessName))..." -ForegroundColor Yellow

    # 1) Graceful: close main window (equivalent to SIGTERM for GUI-less console apps,
    #    sends WM_CLOSE). For console apps use taskkill without /F (sends WM_CLOSE too).
    $null = taskkill /PID $ProcessId 2>$null
    Start-Sleep -Milliseconds 800

    # 2) Force only if still alive
    $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "  [$Label] Still alive, force-killing PID $ProcessId..." -ForegroundColor Yellow
        $null = taskkill /PID $ProcessId /T /F 2>$null
        Start-Sleep -Milliseconds 300
    }

    if (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue) {
        Write-Host "  [$Label] WARNING: PID $ProcessId could not be terminated." -ForegroundColor Red
    } else {
        Write-Host "  [$Label] PID $ProcessId stopped." -ForegroundColor Green
        $script:stoppedPIDs += $ProcessId
    }
}

# 1. Stop processes by port
foreach ($port in $targetPorts) {
    Write-Host "[Port $port] Searching listeners..." -ForegroundColor Yellow
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($connections) {
        $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($procId in $pids) {
            Stop-ProcessGracefully -ProcessId $procId -Label "Port $port"
        }
    } else {
        Write-Host "  [Port $port] No listeners found." -ForegroundColor Gray
    }
}

# 2. Stop residual AutoNovel worker processes (Huey consumer, uvicorn without port match)
Write-Host "[Processes] Searching residual AutoNovel processes..." -ForegroundColor Yellow
try {
    $candidates = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -and (
            $_.CommandLine -match "huey_consumer" -or
            ($_.CommandLine -match "uvicorn" -and $_.CommandLine -match "src\.backend\.server")
        )
    }
    foreach ($candidate in $candidates) {
        Stop-ProcessGracefully -ProcessId $candidate.ProcessId -Label "Process"
    }
    if (-not $candidates) {
        Write-Host "  [Processes] No residual processes found." -ForegroundColor Gray
    }
} catch {
    Write-Host "  [Processes] Could not enumerate processes: $_" -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "[AutoNovel] Stop sequence complete." -ForegroundColor Green
