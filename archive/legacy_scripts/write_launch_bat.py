fpath = r"i:\claude2\launch.bat"
code = """@echo off
setlocal enabledelayedexpansion
title 覇権小説自動生成ツール (起動中)
cd /d "%~dp0"

echo ===================================================
echo  覇権小説自動生成ツール v3.0
echo ===================================================

:: ログフォルダの作成
if not exist logs mkdir logs

set USE_VENV=1

:: 1. 仮想環境のチェックと作成 (pip.exe の存在で完全に完了したか判断)
if not exist ".venv\\Scripts\\pip.exe" (
    echo [INFO] Python仮想環境が見つからないか、不完全です。新規作成します...
    echo [INFO] （作成には1〜2分程度かかる場合があります。このままお待ちください）
    
    :: 古い不完全なフォルダがある場合は削除
    if exist .venv rmdir /s /q .venv >nul 2>&1
    
    :: Windowsのアプリ実行エイリアス対策として、まず py コマンドを試す
    where py >nul 2>&1
    if !errorlevel! equ 0 (
        echo [INFO] py ランチャーを使用して仮想環境を作成中...
        py -3 -m venv .venv
    ) else (
        echo [INFO] python コマンドを使用して仮想環境を作成中...
        python -m venv .venv
    )
    
    if not exist ".venv\\Scripts\\pip.exe" (
        echo [WARNING] 仮想環境の作成に失敗しました（ensurepipエラー等）。
        echo [WARNING] 代替として、グローバル（システム）のPython環境を使用します。
        set USE_VENV=0
        ping 127.0.0.1 -n 4 >nul
    ) else (
        echo [INFO] 仮想環境の作成が完了しました。
        :: 新規作成時はパッケージインストールを強制するマーカー削除
        if exist logs\\.packages_installed del logs\\.packages_installed >nul 2>&1
    )
)

:: 2. 仮想環境のアクティベート（有効な場合のみ）
if !USE_VENV! equ 1 (
    if exist ".venv\\Scripts\\activate.bat" (
        call .venv\\Scripts\\activate.bat
    )
)

:: 3. 依存関係のインストール/更新 (マーカーファイルによる初回限定・高速起動化)
if not exist "logs\\.packages_installed" (
    echo [INFO] 依存関係をチェック・インストールしています...
    echo [INFO] （初回または環境更新時のみ実行されます）
    python -m pip install -r requirements.txt >nul
    if !errorlevel! equ 0 (
        echo installed > logs\\.packages_installed
    ) else (
        echo [WARNING] パッケージの自動インストールに一部失敗したか、スキップされました。すでに依存関係がインストールされている場合は起動可能です。
        ping 127.0.0.1 -n 4 >nul
    )
)

:: 4. データベースの初期化
echo [INFO] データベースの状態を確認しています...
alembic upgrade head >nul 2>&1

:: 5. 各サービスの起動
set PYTHONPATH=%cd%

echo [INFO] バックエンドAPIを起動しています...
start /B "" cmd /c "python -m uvicorn src.backend.server:app --host 127.0.0.1 --port 8200 > logs\\uvicorn.log 2>&1"

echo [INFO] タスクワーカー(Huey)を起動しています...
start /B "" cmd /c "python -m huey.bin.huey_consumer src.backend.tasks.huey > logs\\huey.log 2>&1"

echo [INFO] Streamlit UIを起動しています...
start /B "" cmd /c "python -m streamlit run streamlit_app/app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true > logs\\streamlit.log 2>&1"

echo [INFO] APIの準備完了を待機しています...
:WAIT_LOOP
python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8200/health').getcode() == 200 else 1)" >nul 2>&1
if errorlevel 1 (
    ping 127.0.0.1 -n 3 >nul
    goto WAIT_LOOP
)

:: 少し待ってからブラウザを自動で開く
ping 127.0.0.1 -n 4 >nul
start http://localhost:8501

title 覇権小説自動生成ツール (実行中)
echo.
echo ===================================================
echo  すべてのサービスが起動しました！
echo  ブラウザが自動的に開きます。
echo  (開かない場合は http://localhost:8501 にアクセス)
echo ===================================================
echo.
echo ※ 各プロセスのログは logs\\ フォルダに出力されています。
echo ※ この黒いウィンドウを「×」で閉じると、すべてのプロセスが自動的に終了します。
echo ※ ツールを使用中は、このウィンドウを閉じないでください。
echo.

:: ウィンドウが閉じられるまで待機
:IDLE
ping 127.0.0.1 -n 3601 >nul
goto IDLE
"""
with open(fpath, "w", encoding="cp932") as f:
    f.write(code)
print("launch.bat has been written successfully in CP932.")

