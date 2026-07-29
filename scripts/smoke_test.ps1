<#
.SYNOPSIS
    AutoNovel スモークテスト - 起動済みバックエンドに対して基本エンドポイントを叩く。

.DESCRIPTION
    バックエンドが起動済みの前提で以下を検証:
      1. GET /health                          -> 200 + status ok
      2. POST /easy_mode/generate             -> 200 + suggestions にタスク ID
      3. GET /easy_mode/status/{task_id}       -> 200 + status フィールド存在
      4. GET /easy_mode/export/0              -> 422 (バリデーション)
      5. GET /easy_mode/export/1              -> 200 または 404 (DB 状態依存、500 は禁止)

    いずれかが期待外の場合は非ゼロで終了。CI のデプロイ後検証にも利用可。

.PARAMETER BaseUrl
    バックエンドの BASE URL (既定: http://localhost:8200)

.EXAMPLE
    .\scripts\smoke_test.ps1
    .\scripts\smoke_test.ps1 -BaseUrl http://localhost:8200
#>

[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:8200"
)

$ErrorActionPreference = "Stop"
$overallOk = $true

function Invoke-Check {
    param(
        [string]$Name,
        [scriptblock]$Action,
        [scriptblock]$Assert
    )
    Write-Host "==> $Name" -ForegroundColor Cyan
    try {
        $result = & $Action
        $ok = & $Assert $result
        if ($ok) {
            Write-Host "    PASS" -ForegroundColor Green
        } else {
            Write-Host "    FAIL" -ForegroundColor Red
            $script:overallOk = $false
        }
    } catch {
        Write-Host "    ERROR: $_" -ForegroundColor Red
        $script:overallOk = $false
    }
}

# 1. /health
Invoke-Check "GET /health" {
    Invoke-RestMethod -Uri "$BaseUrl/health" -Method GET -TimeoutSec 5
} {
    param($r)
    $r.status -eq "ok"
}

# 2. /easy_mode/generate
$taskId = $null
Invoke-Check "POST /easy_mode/generate" {
    $body = @{
        current_chapter         = "煙が晴れると、怪物が姿を現した。"
        chapter_history         = @()
        character_params       = @{}
        content_length_limit   = 2000
    } | ConvertTo-Json -Depth 3
    Invoke-RestMethod -Uri "$BaseUrl/easy_mode/generate" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 5
} {
    param($r)
    if (-not $r.suggestions) { return $false }
    $joined = ($r.suggestions -join " ")
    if ($joined -match "/easy_mode/status/(\d+)") {
        $script:taskId = $Matches[1]
        return $true
    }
    return $false
}

# 3. /easy_mode/status/{task_id}
if ($taskId) {
    Invoke-Check "GET /easy_mode/status/$taskId" {
        Invoke-RestMethod -Uri "$BaseUrl/easy_mode/status/$taskId" -Method GET -TimeoutSec 5
    } {
        param($r)
        $r.task_id -eq $taskId -and $null -ne $r.status
    }
}

# 4. /easy_mode/export/0 (422)
Invoke-Check "GET /easy_mode/export/0 (expect 422)" {
    try {
        Invoke-WebRequest -Uri "$BaseUrl/easy_mode/export/0" -Method GET -TimeoutSec 5 -SkipHttpErrorCheck
    } catch { $_.Exception.Response }
} {
    param($r)
    $null -ne $r -and ($r.StatusCode -band 0) -ne 0 -and [int]$r.StatusCode -eq 422
}

# 5. /easy_mode/export/1 (200 or 404, but not 500)
Invoke-Check "GET /easy_mode/export/1 (expect 200/404, never 500)" {
    Invoke-WebRequest -Uri "$BaseUrl/easy_mode/export/1" -Method GET -TimeoutSec 5 -SkipHttpErrorCheck
} {
    param($r)
    $code = [int]$r.StatusCode
    $code -eq 200 -or $code -eq 404
}

if ($overallOk) {
    Write-Host "`nSmoke test PASSED." -ForegroundColor Green
    exit 0
} else {
    Write-Host "`nSmoke test FAILED." -ForegroundColor Red
    exit 1
}
