#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$PROJECT_ROOT"

BACKEND_PID=""

# スクリプト終了時にバックグラウンドプロセスを停止するクリーンアップ関数
cleanup() {
    echo ""
    echo "アプリケーションを終了します..."
    if [ -n "$BACKEND_PID" ]; then
        echo "Backend API (PID: $BACKEND_PID) を停止中..."
        kill "$BACKEND_PID" 2>/dev/null
    fi
    echo "終了しました。"
}

# Ctrl+C や正常終了シグナル (EXIT) を捕捉して cleanup 関数を呼び出す
trap cleanup EXIT

echo "覇権小説自動生成ツール v3.0 を起動します..."
echo ""

echo "[1/3] Backend API を起動中 (ポート 8200)..."
LOG_FILE="/tmp/kaku_backend.log"
uvicorn src.backend.server:app --host 127.0.0.1 --port 8200 > "$LOG_FILE" 2>&1 &
BACKEND_PID=$!

echo "[2/3] API サーバーの起動を待機中..."
MAX_WAIT_SECONDS=30
SECONDS=0
while ! curl -sf http://127.0.0.1:8200/health > /dev/null; do
    if (( SECONDS > MAX_WAIT_SECONDS )); then
        echo "エラー: Backend API の起動がタイムアウトしました (>${MAX_WAIT_SECONDS}秒)。"
        echo "ログファイルを確認してください: $LOG_FILE"
        exit 1
    fi
    sleep 2
done
echo "  Backend API 起動完了"

echo ""
echo "========================================="
echo "Streamlit UI : http://localhost:8501"
echo "Backend API  : http://localhost:8200"
echo "========================================="
echo ""

echo "[3/3] Streamlit UI を起動中 (ポート 8501)..."
streamlit run streamlit_app/app.py \
    --server.port 8501 \
    --server.address 127.0.0.1 \
    --server.headless true
