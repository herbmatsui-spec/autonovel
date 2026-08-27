@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ===================================================
echo  Autonovel (覇権小説生成) ローカル一括起動ランチャー
echo ===================================================
echo.

set PYTHONPATH=%cd%

rem 1. Pythonの確認
where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Pythonが見つかりません。PythonをインストールしてPATHを通してください。
        pause
        exit /b 1
    ) else (
        set PY_CMD=py
    )
) else (
    set PY_CMD=python
)

rem 2. バックエンドAPIの起動
echo [1/4] バックエンドAPIサーバーを起動しています (ポート: 8200)...
start "Autonovel - Backend API" cmd /k "set PYTHONPATH=%cd%&& %PY_CMD% -m uvicorn src.backend.server:app --host 127.0.0.1 --port 8200"

rem 3. バックグラウンドワーカー(Huey)の起動
echo [2/4] バックグラウンドワーカー (Huey) を起動しています...
start "Autonovel - Worker (Huey)" cmd /k "set PYTHONPATH=%cd%&& %PY_CMD% -m huey.bin.huey_consumer src.backend.tasks.huey"

rem 4. APIサーバー起動待機
echo [3/4] APIサーバーの起動完了を待機しています...
set RETRIES=0
:WAIT_LOOP
%PY_CMD% -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8200/health').getcode() == 200 else 1)" >nul 2>&1
if errorlevel 1 (
    set /a RETRIES+=1
    if !RETRIES! geq 20 (
        echo [WARNING] APIサーバーの応答待機がタイムアウトしました。手動でウィンドウを確認してください。
        goto START_FRONTEND
    )
    timeout /t 2 >nul
    goto WAIT_LOOP
)
echo バックエンドAPIサーバー (http://127.0.0.1:8200) の起動を確認しました。

:START_FRONTEND
echo.
echo [4/4] フロントエンド開発サーバーを起動しています (ポート: 5173)...
cd /d "%~dp0frontend"

where bun >nul 2>&1
if errorlevel 1 (
    echo [INFO] bun が見つからないため、npm run dev を使用します。
    start "Autonovel - Frontend (React/Vite)" cmd /k "npm run dev"
) else (
    echo [INFO] bun を検出しました。bun run dev で高速起動します。
    start "Autonovel - Frontend (React/Vite)" cmd /k "bun run dev"
)

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
