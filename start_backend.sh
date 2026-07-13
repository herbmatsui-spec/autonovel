#!/bin/bash
# バックエンドAPIとワーカーをバックグラウンドで起動するスクリプト

echo "Starting backend API and worker in background..."

# ログディレクトリの作成
mkdir -p logs

# PYTHONPATH の設定
export PYTHONPATH=$PYTHONPATH:$(pwd)

# 1. Backend API の起動 (バックグラウンド)
nohup uvicorn src.backend.server:app --host 127.0.0.1 --port 8200 > logs/backend_api.log 2>&1 &

# 2. Huey Worker の起動 (バックグラウンド)
nohup python -m huey.bin.huey_consumer src.backend.tasks.huey > logs/backend_worker.log 2>&1 &

echo "Processes started. Check logs/backend_api.log and logs/backend_worker.log for details."
