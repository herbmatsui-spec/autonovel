@echo off
setlocal

echo =========================================
echo 覇権小説自動生成ツール v3.0 (ワンクリック起動)
echo =========================================

set PYTHONPATH=%cd%

echo [1/3] バックエンドAPIおよびワーカーを起動しています...
start "Backend API" cmd /k "uvicorn src.backend.server:app --host 127.0.0.1 --port 8200"
start "Huey Worker" cmd /k "python -m huey.bin.huey_consumer src.backend.tasks.huey"

echo [2/3] APIサーバーの準備完了を待機しています...
:WAIT_LOOP
python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8200/health').getcode() == 200 else 1)" >nul 2>&1
if errorlevel 1 (
    timeout /t 2 >nul
    goto WAIT_LOOP
)

echo [3/3] Streamlit UIを起動しています...
echo ブラウザが自動的に開きます。
start "Streamlit UI" cmd /k "streamlit run streamlit_app/app.py --server.port 8501 --server.address 127.0.0.1"

echo.
echo =========================================
echo 起動が完了しました。
echo Streamlit UI : http://localhost:8501
echo Backend API  : http://localhost:8200
echo =========================================
echo ※終了する際は、開いた3つのコマンドプロンプト画面をそれぞれ閉じてください。
pause
