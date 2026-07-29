Set-Location $PSScriptRoot\..
Write-Host "=== ruff ==="
py -m ruff check --fix src tests
Write-Host "=== mypy ==="
py -m mypy src
Write-Host "=== pytest collect ==="
py -m pytest --collect-only -q
Write-Host "=== frontend lint/typecheck/test:ci ==="
$frontendDir = "frontend"
if (Test-Path $frontendDir) {
  Push-Location $frontendDir
  if (Test-Path "node_modules") {
    npm run lint
    npm run typecheck
    npm run test:ci
  } else {
    Write-Host "前端 node_modules なし。docker/npm ci で先にインストールしてください" -ForegroundColor Yellow
  }
  Pop-Location
} else {
  Write-Host "frontend/ ディレクトリなし。スキップします" -ForegroundColor Yellow
}
Write-Host "=== done ==="
