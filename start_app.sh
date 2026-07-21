#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$PROJECT_ROOT"

echo "覇権小説自動生成ツール v3.0 を起動します..."
echo ""

echo "[1/3] Backend API を起動中 (ポート 8200)..."
uvicorn src.backend.server:app --host 127.0.0.1 --port 8200 > /tmp/kaku_backend.log 2>&1 &
BACKEND_PID=$!

echo "[2/3] API サーバーの起動を待機中..."
while ! curl -sf http://127.0.0.1:8200/health > /dev/null; do
    sleep 2
done
echo "  Backend API 起動完了"

echo "[3/3] Streamlit UI を起動中 (ポート 8501)..."
streamlit run streamlit_app/app.py \
    --server.port 8501 \
    --server.address 127.0.0.1 \
    --server.headless true

echo ""
echo "========================================="
echo "Streamlit UI : http://localhost:8501"
echo "Backend API  : http://localhost:8200"
echo "========================================="
