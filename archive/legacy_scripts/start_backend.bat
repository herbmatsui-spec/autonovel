@echo off
setlocal

echo バックエンドAPIとワーカーをバックグラウンドで起動しています...

set PYTHONPATH=%cd%

start "Backend API" cmd /c "uvicorn src.backend.server:app --host 127.0.0.1 --port 8200"
start "Huey Worker" cmd /c "python -m huey.bin.huey_consumer src.backend.tasks.huey"

exit
