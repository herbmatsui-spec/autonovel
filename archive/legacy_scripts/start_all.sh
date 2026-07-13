#!/bin/bash

echo "=================================================="
echo "⚔️ 覇権小説エンジン v3.0 - 一括起動スクリプト"
echo "=================================================="

# 仮想環境がある場合は自動で有効化
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "[1/3] FastAPI バックエンドサーバーを起動します..."
cd backend && python -m uvicorn server:app --port 8000 &
cd ..

echo "[2/3] バックグラウンドワーカーを起動します..."
cd backend && python -m huey.bin.huey_consumer tasks.huey &
cd ..

echo "[3/3] メイン画面（Streamlit）を起動します..."
cd streamlit_app && streamlit run app.py