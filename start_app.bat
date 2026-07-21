@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONPATH=%cd%

echo [1/3] Backend API...
start "Backend API" cmd /k "python -m uvicorn src.backend.server:app --host 127.0.0.1 --port 8200"

echo [2/3] Huey Worker...
start "Huey Worker" cmd /k "python -m huey.bin.huey_consumer src.backend.tasks.huey"

echo [3/3] Streamlit UI...
start "Streamlit UI" cmd /k "python -m streamlit run streamlit_app/app.py --server.port 8501 --server.address 127.0.0.1"

echo.
echo =========================================
echo  App Started Successfully!
echo  Streamlit UI : http://localhost:8501
echo  Backend API  : http://localhost:8200
echo =========================================