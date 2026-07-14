@echo off
chcp 65001 > nul
echo ==========================================
echo 覇権小説エンジン v3.0 起動スクリプト
echo ==========================================

cd /d "%~dp0"

:: モジュールの読み込みエラーを防ぐためにPYTHONPATHを設定
set PYTHONPATH=%~dp0;%~dp0\backend;%~dp0\config

:: 仮想環境(venv)を使っている場合は、以下の行の先頭の「::」を消して有効化してください
call venv\Scripts\activate

echo [1/4] バックエンドAPIサーバー(FastAPI)を起動しています...
start "FastAPI Server" cmd /k "python -m uvicorn src.backend.server:app --host 127.0.0.1 --port 8200"


echo [2/4] バックグラウンドワーカー(Huey)を起動しています...
start "Huey Worker" /MIN cmd /k "python -m huey.bin.huey_consumer src.backend.tasks.huey"

echo [3/4] フロントエンドUI(Streamlit)を起動しています...
start "Streamlit UI" /MIN cmd /k "python -m streamlit run streamlit_app\app.py"

echo [4/4] パイプライン・モニターを起動しています...
start "Pipeline Monitor" /MIN cmd /k "python monitor.py"

echo 起動コマンドの送信が完了しました。4つのプロセスが最小化されて起動しています。