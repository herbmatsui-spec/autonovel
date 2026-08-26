@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ===================================================
echo  Autonovel (覇権小説生成) ローカル一括起動ランチャー
echo ===================================================
echo.

set PYTHONPATH=%cd%

echo [1/4] バックエンドAPIサーバーを起動しています (ポート: 8200)...
start "Autonovel - Backend API" cmd /k "python -m uvicorn src.backend.server:app --host 127.0.0.1 --port 8200"

echo [2/4] バックグラウンドワーカー(Huey)を起動しています...
start "Autonovel - Worker (Huey)" cmd /k "python -m huey.bin.huey_consumer src.backend.tasks.huey"

echo [3/4] APIサーバーの起動完了を待機しています...
:WAIT_LOOP
python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8200/health').getcode() == 200 else 1)" >nul 2>&1
if errorlevel 1 (
    timeout /t 2 >nul
    goto WAIT_LOOP
)
echo バックエンドAPIサーバーの起動を確認しました。

echo.
echo [4/4] フロントエンド開発サーバーを起動しています (ポート: 5173)...
cd /d "%~dp0frontend"
start "Autonovel - Frontend (React/Vite)" cmd /k "npm run dev"
cd /d "%~dp0"

echo.
echo ===================================================
echo  システムが正常に起動しました！
echo   - フロントエンド UI : http://localhost:5173
echo   - バックエンド API  : http://localhost:8200
echo   - APIドキュメント  : http://localhost:8200/docs
echo ===================================================
echo ブラウザを開いています...
timeout /t 3 >nul
start http://localhost:5173

echo.
echo ※ 終了する際は起動した各コマンドプロンプトウィンドウを閉じてください。
pause
