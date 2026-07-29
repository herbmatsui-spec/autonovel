# AutoNovel Makefile - 一般的な開発タスクのエイリアス。
# Windows でも GNU Make (Git for Windows 同梱等) で実行可能。

.PHONY: help install dev test lint typecheck openapi frontend-test frontend-lint run dev-up dev-down prod-up prod-down clean verify

help:  ## 利用可能ターゲット一覧を表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install:  ## バックエンド依存をインストール
	py -m pip install -r requirements-dev.txt
	py -m pip install -e .

dev: install  ## 開発用インストール (バック + フロント)
	cd frontend && npm install

test:  ## pytest を実行 (バックエンド)
	py -m pytest -q --tb=short

lint:  ## ruff チェック
	py -m ruff check src tests

typecheck:  ## mypy (optional)
	py -m mypy src || echo "mypy 未インストールまたは問題検出 (warn only)"

openapi:  ## OpenAPI 仕様を docs/openapi.json へ生成
	py scripts/generate_openapi.py --output docs/openapi.json

frontend-test:  ## フロントエンド vitest
	cd frontend && npm run test:ci

frontend-lint:  ## フロントエンド eslint + typecheck
	cd frontend && npm run lint && npm run typecheck

run:  ## 開発サーバ (backend only) を起動
	py -m uvicorn src.backend.server:app --reload --port 8200

dev-up:  ## docker compose 開発環境を起動
	docker compose up --build

dev-down:  ## docker compose 開発環境を停止
	docker compose down

prod-up:  ## docker compose 本番環境を起動
	docker compose -f docker-compose.prod.yml up -d --build

prod-down:  ## docker compose 本番環境を停止
	docker compose -f docker-compose.prod.yml down

clean:  ## 生成物・キャッシュを削除
	-rm -rf .pytest_cache .ruff_cache .mypy_cache
	-rm -f autonovel.db huey.db docs/openapi.json
	-find . -type d -name __pycache__ -prune -exec rm -rf {} +

verify: lint test openapi frontend-lint frontend-test  ## PR 前のフル検証
	@echo "All checks passed."
