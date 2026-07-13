@echo off
rem カレントディレクトリをこのファイルの場所に変更
cd /d %~dp0
echo Streamlit UI を起動しています...
cd streamlit_app
python -m streamlit run app.py
pause