#!/bin/bash
# run_tests.sh - テスト実行スクリプト

set -e

echo "=== AutoNovel Test Suite ==="

# 依存チェック
echo "Checking dependencies..."
pip list | grep -E "(pytest|ruff|mypy|black|prometheus-client|pyyaml)" > /dev/null || {
    echo "Missing dependencies. Install with: pip install -e \".[dev]\""
    exit 1
}

# リンター
echo "Running ruff..."
ruff check src tests

# 型チェック（緩め）
echo "Running mypy..."
mypy src --ignore-missing-imports

# フォーマットチェック
echo "Running black check..."
black --check src tests

# テスト実行
echo "Running unit tests..."
pytest tests/unit -v --tb=short

echo "Running integration tests..."
pytest tests/integration -v --tb=short

echo "=== All checks passed ==="