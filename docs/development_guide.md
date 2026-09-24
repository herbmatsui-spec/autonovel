# AutoNovel 開発者ガイド

新規参入者が **15 分で環境構築してテストを実行できる** ことを目標としたオンボーディング資料。

---

## 1. 前提条件（3 分）

| 必須 | バージョン | 確認コマンド |
|------|-----------|-------------|
| Python | 3.12+ | `python --version` |
| Node.js / npm | 18+ / 9+ | `npm --version` |
| Git | 任意 | `git --version` |
| Docker（オプション） | 任意 | `docker --version` |

> **自動診断**: `python scripts/check_env.py` で上記すべてを一括検査できます。
> 不足時は解決策がカラー表示されます。

---

## 2. 環境構築（5 分）

```powershell
# 1. リポジトリをクローン
git clone <repository-url>
cd autonovel

# 2. Python 仮想環境を作成
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. 依存をインストール（バックエンド）
py -m pip install --upgrade pip
py -m pip install -e .[dev,rag]

# 4. 依存をインストール（フロントエンド）
cd frontend
npm install
cd ..

# 5. 環境変数を準備
Copy-Item .env.example .env
# 必要に応じて .env の LLM_PROVIDER 等を編集
```

> **ショートカット**: `アプリ起動_ローカル.bat` をダブルクリックすれば
> 上記 1〜5 と DB 初期化・3 プロセス起動がすべて自動実行されます。

---

## 3. データベース初期化（1 分）

```powershell
# 安全マイグレーション（既存 DB は保護される）
python scripts/init_db.py

# 既存 DB に対しても強制実行する場合
python scripts/init_db.py --force
```

---

## 4. テスト実行（3 分）

```powershell
# 単体テスト（最速）
pytest tests/unit/ -x -q

# 特定ステップの検証テスト
pytest tests/unit/scripts/ tests/unit/cli/ tests/unit/plugins/ tests/unit/interfaces/

# 統合テスト
pytest tests/integration/ -q

# 全体回帰（Step 36 基準: failed=0, errors=0, <180秒）
pytest -q --tb=short
```

---

## 5. ローカル起動確認（2 分）

```powershell
# 3 プロセス (Backend / Huey Worker / Frontend) を協調起動
powershell -ExecutionPolicy Bypass -File scripts/start_local.ps1

# 起動計画だけ確認（プロセス起動なし）
powershell -ExecutionPolicy Bypass -File scripts/start_local.ps1 -DryRun

# 停止
powershell -ExecutionPolicy Bypass -File scripts/stop_local.ps1
```

起動後のアクセス先:

- フロントエンド UI: <http://localhost:5173>
- FastAPI Swagger UI: <http://localhost:8200/docs>
- ヘルスチェック: <http://localhost:8200/health>

---

## 6. コーディング規約

### Python（Ruff + Mypy）

```powershell
# Lint
ruff check .

# Format チェック
ruff format --check .

# 自動修正
ruff check --fix .

# 型チェック
mypy src
```

規約のポイント:

- **型ヒント必須**: すべての公開関数に型ヒントを付ける
- **docstring 必須**: モジュール・クラス・公開関数に日本語 docstring を書く
- **命名**: snake_case（関数・変数）、PascalCase（クラス）
- **import 順**: 標準ライブラリ → サードパーティ → ローカル

### TypeScript（ESLint）

```powershell
cd frontend
npm run lint
npm run typecheck
```

---

## 7. アーキテクチャ概要

```
autonovel/
├── src/
│   ├── backend/          # FastAPI バックエンド（routers / database / tasks / observability）
│   ├── cli/              # 統一 CLI (autonovel コマンド)
│   ├── core/             # コアドメイン + PluginRegistry (Step 18)
│   ├── easy_mode/        # かんたんモードパイプライン
│   ├── engine/           # 執筆エンジン
│   ├── interfaces/       # PluginProtocol / ImageProviderProtocol (Step 15-16)
│   ├── plugins/          # オプショナルプラグイン (multimedia / audio / social_posting)
│   └── services/         # ドメインサービス
├── frontend/             # React 18 + TypeScript + Vite
├── scripts/              # 起動・停止・検証スクリプト (Step 2-6)
├── tests/                # unit / integration / e2e (Step 7, 14, 21, 27, 35)
└── docs/                 # ドキュメント
```

### プラグイン疎結合の原則 (Step 15-22)

- コア機能（執筆・圧縮・整形・エクスポート）はプラグインなしで完結する
- オプショナル拡張（マルチメディア・音声・外部投稿）は `ENABLE_*` 環境変数フラグで有効化
- プラグインは [`src/interfaces/plugin.py`](src/interfaces/plugin.py) の `PluginProtocol` に従う
- 無効なプラグインはルーターごとマウントされない（[`src/backend/server.py`](src/backend/server.py) Step 19）

---

## 8. トラブルシューティング

| 症状 | 解決策 |
|------|--------|
| ポート 8200/5173 が使用中 | `powershell -File scripts/stop_local.ps1` |
| マイグレーション失敗 | `python scripts/init_db.py --force`（既存 DB はバックアップ推奨） |
| Huey ワーカーが落ちる | `HUEY_BACKEND=sqlite` と `DATABASE_URL` を確認（`check_env.py`） |
| LLM 応答が固定フォールバック | `.env` の `LLM_PROVIDER` / API キーを確認 |
| マルチメディア 503 | `ENABLE_MULTIMEDIA=true` を `.env` に追加 |

---

## 9. 次のステップ

- [README.md](README.md) でプロダクト全体像を把握
- [docs/architecture.md](docs/architecture.md) でアーキテクチャ詳細を確認
- [CHANGELOG.md](CHANGELOG.md) で最近の変更履歴を確認
