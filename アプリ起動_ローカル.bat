@echo off
cd /d "%~dp0"
cls
echo =========================================
echo  Autonovel App Launcher (Local Mode)
echo =========================================
echo  React UI: http://localhost:5173
echo  Backend : http://localhost:8200
echo =========================================
echo.
echo 仮想環境・依存関係の確認中...

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv が存在しません。先に py -m venv .venv を実行してください。
    pause
    exit /b 1
)

set HUEY_BACKEND=sqlite
set DATABASE_URL=sqlite:///./autonovel.db

echo ブラウザを10秒後に起動します...
start "AutoOpenBrowser" cmd /c "timeout /t 10 >nul & start http://localhost:5173"

echo バックエンド (uvicorn) を起動中...
start "AutoNovel Backend" cmd /k ".\.venv\Scripts\python.exe -m uvicorn src.backend.server:app --reload --port 8200"

echo ワーカー (huey) を起動中...
start "AutoNovel Worker" cmd /k ".\.venv\Scripts\python.exe -m huey.bin.huey_consumer src.backend.tasks.huey.huey"

echo フロントエンド (vite dev) を起動中...
cd frontend
start "AutoNovel Frontend" cmd /k "npm run dev"

echo.
echo すべてのプロセスを別ウィンドウで起動しました。
echo このウィンドウを閉じても動作は継続します。
pause
