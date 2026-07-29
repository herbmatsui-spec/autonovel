<#
.SYNOPSIS
    AutoNovel リリース検証 & タグ付けスクリプト。

.DESCRIPTION
    1. ruff check / pytest / frontend typecheck を実行し全グリーンを確認。
    2. OpenAPI 仕様を docs/openapi.json へ再生成。
    3. 現在の pyproject.toml バージョンを取得し git tag を付与。
    4. リリースノート案 (CHANGELOG.md の対応セクション) を表示。

.PARAMETER Tag
    明示的なタグ名 (例: v0.2.0)。省略時は pyproject.toml の version を使用。

.EXAMPLE
    .\scripts\release.ps1
    .\scripts\release.ps1 -Tag v0.2.1
#>

[CmdletBinding()]
param(
    [string]$Tag
)

$ErrorActionPreference = "Stop"
$projectRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $projectRoot

Write-Host "==> ruff check" -ForegroundColor Cyan
py -m ruff check src tests
if ($LASTEXITCODE -ne 0) { Write-Error "ruff check failed"; exit 1 }

Write-Host "==> pytest" -ForegroundColor Cyan
py -m pytest -q --tb=short
if ($LASTEXITCODE -ne 0) { Write-Error "pytest failed"; exit 1 }

Write-Host "==> OpenAPI 生成" -ForegroundColor Cyan
py scripts\generate_openapi.py --output docs\openapi.json
if ($LASTEXITCODE -ne 0) { Write-Error "OpenAPI generation failed"; exit 1 }

if (Test-Path "$projectRoot\frontend\package.json") {
    Write-Host "==> frontend typecheck" -ForegroundColor Cyan
    Push-Location "$projectRoot\frontend"
    npm run typecheck
    if ($LASTEXITCODE -ne 0) { Write-Error "frontend typecheck failed"; Pop-Location; exit 1 }
    Pop-Location
}

# バージョン取得 (明示されなかった場合)
if (-not $Tag) {
    $pyproject = Get-Content "$projectRoot\pyproject.toml" -Raw
    if ($pyproject -match 'version\s*=\s*"([^"]+)"') {
        $Tag = "v$($Matches[1])"
    } else {
        Write-Error "pyproject.toml から version を読み取れません"
        exit 1
    }
}

Write-Host "==> release tag: $Tag" -ForegroundColor Green
& git tag $Tag
if ($LASTEXITCODE -ne 0) { Write-Error "git tag failed (already exists?)"; exit 1 }

Write-Host "==> リリースノート (CHANGELOG.md 該当セクション)" -ForegroundColor Cyan
$changelog = Get-Content "$projectRoot\CHANGELOG.md" -Raw
if ($changelog -match "(?ms)## \[$($Tag -replace '^v','')\].*?(?=^## )") {
    Write-Output $Matches[0]
} else {
    Write-Warning "CHANGELOG.md に $Tag のセクションが見つかりません"
}

Write-Host "Done. git push origin $Tag で公開してください" -ForegroundColor Green
