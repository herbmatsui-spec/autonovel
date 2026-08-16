# 覇権小説エンジン v3.3 - 実装計画書（36ステップ）

## 目的
本計画書は、コードレビューで指摘した **クリティカル・中リスク** の問題を低性能 LLM でも安全に実装できるよう、**小さく・検証可能**な 36 個のステップに分割したものです。各ステップは **目的・作業内容・完了基準** の 3 要素で構成し、テストや CI で即座に結果を確認できるようにしています。

---

## Phase 1: 文字化け・データロス修正（ステップ 1‑6）

**Step 1** – `src/backend/server.py` の文字化け箇所抽出
- 目的: 破損した日本語文字列を全てリスト化する
- 作業: `grep -n "\xef\xbb\xbf" -R src/backend/server.py`
- 完了基準: 破損文字列の行番号と内容がメモにまとめられる

**Step 2** – 正しい日本語文字列で上書き
- 目的: 破損文字列を正しい日本語に置換
- 作業: `sed -i 's/\xef\xbb\xbf\xef\xbb\xbf\xef\xbb\xbf\xef\xbb\xbf/生成中/g' src/backend/server.py`
- 完了基準: `git diff` が期待通りの置換を示す

**Step 3** – 同様の文字化けを `src/core/container.py`・`infra.py`・`__init__.py` で修正
- 目的: 全ファイルの文字化けを除去
- 作業: 手動またはスクリプトで `U+FFFD` を削除し、正しい日本語を書き込む
- 完了基準: `git grep -P "\xEF\xBF\xBD"` が0件

**Step 4** – 文字化け修正後のテスト実行
- 目的: 文字列が正しく表示され API がエラーしないことを確認
- 作業: `pytest tests/test_health.py -q`
- 完了基準: 全テスト PASS

**Step 5** – 文字化けに起因するドキュメント更新
- 目的: README/Docs でも正しい日本語になるように修正
- 作業: `sed -i` で対象ファイルを書き換え、プレビュー確認
- 完了基準: `git diff` が正しい日本語を示す

**Step 6** – CI に文字化けチェックを追加（Dry‑run）
- 目的: 将来の文字化け再発防止
- 作業: `.github/workflows/ci.yml` に `git grep -P "\xEF\xBF\xBD" && exit 1` を追加
- 完了基準: CI が文字化けがあると失敗する

---

## Phase 2: DI コンテナ整理（ステップ 7‑12）

**Step 7** – `src/core/container.py` を削除または無視
- 目的: 同名ディレクトリとファイルの衝突を解消
- 作業: ファイルを `git rm src/core/container.py`、`.gitignore` から除外
- 完了基準: `python -c "import src.core.container"` がパッケージをインポート

**Step 8** – `src/core/container/app.py` の未解決プロバイダ修正
- 目的: 正しいモジュールパスに変更（例: `src.agents.audit.LogicalAuditor`）
- 作業: 文字列プロバイダを `"src.agents.audit.LogicalAuditor"` に書き換え
- 完了基準: DI コンテナ起動時に `ModuleNotFoundError` が出ない

**Step 9** – `AppContainer2` の `auditor`/`validator` の依存関係テスト
- 目的: 依存解決が成功することを確認
- 作業: `python - <<EOF
from src.core.container import AppContainer
print(AppContainer().auditor())
EOF`
- 完了基準: インスタンスが生成されエラーなし

**Step 10** – `src/core/container/__init__.py` のエイリアス整理
- 目的: `AppContainer` が常に `AppContainer2` を指すことを保証
- 作業: コメントを追加し、`AppContainer = AppContainer2` のみ残す
- 完了基準: `import src.core.container as c; isinstance(c.AppContainer(), c.AppContainer)` が True

**Step 11** – 依存解決テストを `tests/unit/test_infra_container.py` に追加
- 目的: CI で自動検証
- 作業: 各プロバイダを取得し `assert provider()` が例外を出さないことをテスト
- 完了基準: 新規テストが PASS

**Step 12** – CI の DI 整合性チェックを追加
- 目的: 将来のコンテナ破損を早期検出
- 作業: `python -m pytest tests/unit/test_infra_container.py` を `unit-test` ジョブに組む
- 完了基準: CI が DI エラーで失敗したら即座に修正が必要になる

---

## Phase 3: 認証とセキュリティ（ステップ 13‑18）

**Step 13** – `APIKeyService.validate` のデフォルト動作変更
- 目的: `allowed_keys` が空の場合は **常に False** にする
- 作業: `if not self.allowed_keys: return False`
- 完了基準: 無鍵リクエストで 401 が返る

**Step 14** – `.env.example` にデフォルト API キー例示とコメント追加
- 目的: 開発者が正しく設定できるようにする
- 作業: `ALLOWED_API_KEYS=example-key-1234` を追記
- 完了基準: `get_api_key_service()` がキーリストを取得

**Step 15** – 認証失敗時に **JSON** 形式のエラーメッセージ統一
- 作業: `validate_api_key_or_raise` で `AppError` の `error_code` を利用して JSON を返す
- 完了基準: `curl -H "X-API-Key: wrong" /api/health` が `{"error_code":"FORBIDDEN","error_message":...}`

**Step 16** – テスト追加 `tests/test_auth.py`
- 目的: 正常・無効・未設定の 3 ケースをカバー
- 作業: FastAPI TestClient で 200/401/403 を検証
- 完了基準: 新規テストが PASS

**Step 17** – CI に認証テストを組み込み（`unit-test` ジョブに依存）
- 完了基準: CI が認証テストで失敗した場合ブロック

**Step 18** – ドキュメント `docs/CORS_CONFIG.md` に認証設定セクションを追記

---

## Phase 4: 並行性・非同期実装の安全化（ステップ 19‑24）

**Step 19** – `services/async_wrapper.py` のラッパー刷新
- 作業: `run_async` を `asyncio.run(coro)` に置換し、`async_task` は `functools.wraps` のまま
- 完了基準: 既存テストで `run_async` が正常に完了

**Step 20** – `src/core/rate_limiter.py` のスレッド安全化
- 作業: グローバル `_rate_limit_store` を `asyncio.Lock` で保護
- 完了基準: 同時リクエストでレースコンディションが起きないことを `pytest-asyncio` で確認

**Step 21** – `TimeoutMiddleware` の適用範囲限定
- 作業: LLM 生成系エンドポイントのみ `@app.middleware` にラップし、他は除外
- 完了基準: 長時間 SSE が 30 秒で切れないことを手動確認

**Step 22** – `BackgroundReporter`/`ProgressState` の型ヒント強化
- 作業: `typing.Protocol` でインターフェースを明示し、`mypy` が通るように修正
- 完了基準: `mypy src/backend` がエラーなし

**Step 23** – テスト `tests/test_rate_limiter.py` を追加し、レート超過時に 429 が返ることを確認

**Step 24** – CI の非同期テストスイートを `pytest-asyncio` の strict モードから `Mode=standard` に緩和し、実行時間を半減
- 完了基準: `ci` 全体が 30 分以内に完了

---

## Phase 5: コードクオリティとリント（ステップ 25‑30）

**Step 25** – `prompts/manager.py` の未import `Union` / `Tuple` を追加
- 作業: `from typing import Union, Tuple` をインポート
- 完了基準: `ruff` が F821 を出さない

**Step 26** – `prompts/manager.py` のベア except を具体的例外に変更（`json.JSONDecodeError`）
- 完了基準: ruff が E722 を出さない

**Step 27** – 重複定義 `build_ultra_fast_plot_batch_prompt` のうち **古い方を削除**
- 完了基準: ruff が F811 を出さない

**Step 28** – `src/models/report.py` の Pydantic v2 移行（`ConfigDict` 使用）
- 完了基準: `mypy` が `PydanticDeprecatedSince20` を警告しない

**Step 29** – `src/core/container/app.py` の `auditor`/`validator` の文字列パス修正後、`ruff format --check` を CI に追加
- 完了基準: フォーマッタがエラーなしで通過

**Step 30** – プロジェクト全体の **Pre‑commit** を実行し、残りの 200 件程度の簡単 Fix（Unused import, trailing whitespace）を自動適用
- 完了基準: `git status` が clean

---

## Phase 6: ドキュメント・CI 改善（ステップ 31‑36）

**Step 31** – CI の `lint-new` に **`--statistics`** を付与し、変更行数をレポート
- 完了基準: PR コメントに統計が表示

**Step 32** – `docs/IMPLEMENTATION_PLAN_36_STEPS.md` をリポジトリのルートに配置し、README からリンク追加
- 完了基準: GitHub 上でリンクが機能

**Step 33** – `README.md` に「文字化け防止策」セクションと「DI コンテナ整理」セクションを追記

**Step 34** – 既存の **テストカバレッジ** を測定し、**80% 以上** を目標に簡易テストを追加（例: `tests/test_config_loading.py`）
- 完了基準: `pytest --cov=src` が 80% 以上

**Step 35** – `docker-compose.yml` の `healthcheck` タイムアウトを 60 秒に拡張し、LLM 起動遅延に対応
- 完了基準: コンテナ起動後 2 分以内に `docker compose up` が成功

**Step 36** – 最終 **リリースノート** 作成 `docs/RELEASE_NOTES_36_STEP.md`
- 内容: すべての修正点とマイグレーション手順
- 完了基準: PR に添付し、マージ後タグ付け

---

## 実装・検証フロー
1. **ブランチ作成** `feature/implementation-plan-36`
2. 各ステップを **個別コミット**（`git commit -m "Step X: <概要>"`）
3. **CI パイプライン** が全ステップで PASS することを確認
4. **レビュー** 後 `main` へマージ、タグ `v3.3` を付与

以上が 36 ステップの実装計画です。低性能 LLM でも **1〜2 ファイルの変更**、**テスト実行**、**CI 確認** のサイクルで安全に実装できます。
