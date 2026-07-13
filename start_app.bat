@echo off

echo =========================================
echo 覇権小説自動生成ツール v3.0 (ローカル環境起動)
echo =========================================

set PYTHONPATH=%cd%

echo [INFO] 古いプロセスを終了しています...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM streamlit.exe >nul 2>&1


echo 古いプロセスが残っているとポート競合エラーが起きます。
echo エラーが出る場合は、タスクマネージャーから python.exe を終了してください。
echo.

echo バックエンドAPIを起動中 (ポート 8200)...
start "Backend API" cmd /k "uvicorn src.backend.server:app --host 127.0.0.1 --port 8200"

echo タスクワーカー(Huey)を起動中...
start "Huey Worker" cmd /k "python -m huey.bin.huey_consumer src.backend.tasks.huey"

echo Streamlit UIを起動中 (ポート 8501)...
start "Streamlit UI" cmd /k "streamlit run streamlit_app/app.py --server.port 8501 --server.address 127.0.0.1 --server.headless false"

echo.
echo =========================================
echo 起動完了
echo Streamlit UI : http://localhost:8501
echo Backend API : http://localhost:8200
echo.
echo ※各プロセスは別々の黒い画面（コマンドプロンプト）で立ち上がります。
echo 終了する際は、開いた3つのウィンドウをそれぞれ「×」ボタンで閉じてください。
echo =========================================
pause