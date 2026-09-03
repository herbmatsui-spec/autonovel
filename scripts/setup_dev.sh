#!/bin/bash
# setup_dev.sh - 開発環境セットアップ

set -e

echo "=== AutoNovel Development Setup ==="

# Python バージョンチェック
python_version=$(python3 --version | cut -d' ' -f2)
echo "Python version: $python_version"

# 仮想環境作成（存在しない場合）
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# 仮想環境アクティベート
source .venv/bin/activate

# pip アップグレード
pip install --upgrade pip

# 依存インストール
echo "Installing dependencies..."
pip install -e ".[dev]"

# マイグレーション実行
echo "Running database migrations..."
cd src/backend
alembic upgrade head
cd ../..

echo "=== Setup complete ==="
echo "Activate virtual environment with: source .venv/bin/activate"
echo "Run tests with: ./run_tests.sh"