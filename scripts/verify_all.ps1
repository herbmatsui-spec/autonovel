Set-Location $PSScriptRoot\..
Write-Host "=== ruff ==="
py -m ruff check src tests
Write-Host "=== mypy ==="
py -m mypy src
Write-Host "=== pytest collect ==="
py -m pytest --collect-only -q
Write-Host "=== done ==="
