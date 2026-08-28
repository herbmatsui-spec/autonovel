# バックエンド 実装計画書

## 概要
このドキュメントは、コードレビューで指摘された問題に対する修正計画をまとめたものです。
重大度順に対応項目を列挙し、具体的な修正手順と見積もりを示します。

## 対応優先順位
1. **Critical**（致命的）: 認証バイパスなど、放置すると直ちにセキュリティ侵害につながる問題
2. **High**: セキュリティリスクまたはサービス可用性に重大な影響を与える問題
3. **Medium**: バグや保守性問題。早期修正推奨だが緊急性は低い
4. **Low**: 軽微な改善点またはベストプラクティスへの準拠

## 修正項目一覧

### Critical
| ID | ファイル | 行番号 | 問題 | 修正方針 | 見積もり工数 | 依存 |
|----|----------|--------|------|----------|--------------|------|
| C1 | src/backend/auth.py | 53-54 | `ALLOWED_API_KEYS` 未設定時に `test*` キーで認証が通る | フォールバックを削除し、キー未設定時は常に `False` を返す。開発用ブートストラップは `ENVIRONMENT != "production"` の場合のみ許可（例: `if env != "production" and api_key.startswith("test"): return True`） | 0.5h | なし |
| C2 | src/backend/server.py | 210-219 (および `config/cors_config.py`) | `allow_credentials=True` とワイルドカード/広いオリジンの組み合わせにより認証付きCSRFリスク | 起動時に検証: `allow_credentials=True` の場合、`allowed_origins` がリストで且つ `"*"` でないことを確認し、違反時はアプリ起動を失敗させる。デフォルト値を空リストに変更し、環境変数必須にする。 | 1.0h | CORS設定の見直し |

### High
| ID | ファイル | 行番号 | 問題 | 修正方針 | 見積もり工数 | 依存 |
|----|----------|--------|------|----------|--------------|------|
| H1 | src/backend/routers/narrative.py | 65, 204 | `override_affinity` と `rebuild_plot_with_foreshadows` エンドポイントに認証が欠如 | 両エンドポイントに `api_key: str = Depends(require_api_key)` を追加。さらに `rebuild_plot_with_foreshadows` は長時間タスクのため、結果をすぐに返さずバックグラウンドタスク（Huey）へ投入し、`task_id` を返すように変更。 | 1.5h | なし (タスクキューは既に存在) |
| H2 | src/backend/routers/commercial.py | 43 | `CommercialPipeline.run` が `await` されず、さらに同期的にLLM実行と `subprocess.run` がイベントループをブロック | 1. `await CommercialPipeline.run(...)` に修正。2. 長時間処理はバックグラウンドタスクへ移行。`CommercialPipeline.run` を Huey タスクとしてラップし、エンドポイントでは `task_id` を即時返却。ステータス取得用エンドポイントは既にあるため流用。 | 2.0h | Hueyタスクラッパー作成 |
| H3 | src/backend/sse.py | 60-69 | イベントループ上で同期 Redis `pubsub.get_message` を呼び出し、最大1秒ブロック | 同期Redis呼び出しを非同期版 (`redis.asyncio.Redis`) に置き換えるか、`loop.run_in_executor` でスレッドプールにオフロード。既に実装されている SQLite ポーリングフォールバックパスへ統合しても可。 | 1.5h | `redis.asyncio` インストール (既に依存している可能性あり) |
| H4 | src/backend/rate_limit.py | 28-51 | スライド窓レートリミットが非アトミック（3ステップ）で競合により上限超過 | Luaスクリプトまたは `pipeline(WATCH)` を使用して `zremrangebyscore` → `zcard` → `zadd` のチェック＆インクリメントを原子化。 | 1.0h | Luaスクリプト作成・テスト |
| H5 | src/backend/tasks.py | 56-70 | `_apply_config_overrides` が `ProjectContext.set_setting` でプロセスグローバル設定を書き換え、マルチユーザー環境で競合 | 設定オーバーライドをリクエスト/タスクスコープに閉じる。`ProjectContext` の代わりに、タスク実行コンテキスト（例: `contextvars` またはタスク引数）へ設定を渡す。`ProjectContext` は読み取り専用参照に変更。 | 2.0h | 他の設定参照箇所の調査（波及影響） |

### Medium
| ID | ファイル | 行番号 | 問題 | 修正方針 | 見積もり工数 | 依存 |
|----|----------|--------|------|----------|--------------|------|
| M1 | src/backend/routers/patches.py | 135,141 | `edit_patch` エンドポイントで `req.content` が `AttributeError`（`req` が dict のため） | Pydantic モデル `PatchEditRequest(content: str)` を定義し、エンドポイントの引数として使用。 | 0.5h | なし |
| M2 | src/backend/patch_validator.py | 194-200 | 危険キーワード (`os.system` 等) を含むパッチでも `is_safe=True` を返す | キーワード検出時に `is_safe=False` を返す。または人間による明示的承認フラグを必要とする。 | 0.5h | なし |
| M3 | src/backend/sse.py | 50 | `int(last_event_id)` が非数値で例外（外部例外でキャッチされるが不適切） | `try/except ValueError` でラップし、変換失敗時は `None` 扱いとする。 | 0.2h | なし |
| M4 | src/backend/database/repository.py | 30-90 | `__getattr__` が未知属性に対してコルーチンを返し、typo等を見逃す；さらに自動UoW対象に `illustrations` が欠落 | 委譲対象を明示的なメソッドホワイトリストに制限し、`illustrations` をリストに追加。未知属性は `AttributeError` を送出。 | 1.0h | なし |
| M5 | src/backend/server.py | 363 | 冗長な例外ハンドリング `except (ConnectionError, TimeoutError, OSError, Exception)` | `Exception` のみに統一（または特定例外のみを捕捉し、`Exception` は別ブロックで）。`KeyboardInterrupt`/`SystemExit` を意図的に捕捉しないことを明記。 | 0.2h | なし |
| M6 | src/backend/engine.py | 全体 (ctor 42引数) | `UltimateHegemonyEngine` が神クラスかつ依存が多すぎる | 徐々にリファクタリング: 設定オブジェクトやファサードへ分割。今回はドキュメント化と依注コンテナへの移行準備（フェーズ2以降）。 | 3.0h (長期) | アーキテクチャ検討 |

### Low
| ID | ファイル | 行番号 | 問題 | 修正方針 | 見積もり工数 | 依存 |
|----|----------|--------|------|----------|--------------|------|
| L1 | src/backend/rate_limit.py | 25-26 / src/backend/auth.py:66 | レートリミットキーが APIキーの先頭8文字のみで衝突しやすい | フルハッシュ（例: `sha256(api_key)`）またはハmacを使用。ただし既存キーとの互換性のためマイグレーションが必要。 | 0.5h | なし (互換性考慮) |
| L2 | src/backend/patch_validator.py | 120-146 | ASTガードが文字列リテラル内の危険コードをすり抜ける | 文字列リテラルもスキャンする追加チェックを入れる（辞書ベース）。ただし実際の適用対象は制限されたフィールドのため低リスク。 | 0.5h | なし |
| L3 | src/backend/database/core.py | 304-356 | 廃止予定の文字列 `execute` / `fetch_*` が残っている | 使用箇所がないことを確認し、メソッド自体を削除または非推奨警告を例外に変更。将来的な誤用を防ぐ。 | 0.5h | なし |
| L4 | 各ルーターファイル (例: commercial.py, narrative.py) | 例外ハンドリング | `except Exception: raise HTTPException(500, str(e))` で内部情報漏洩および不適切なステータス | 登録済みのハンドラに任せるか、`ValidationError`/`NotFoundError` 等の型例外を投げる。共通のラッパーユーティリティを作成しても可。 | 1.0h (複数ファイル) | 共通例外ユーティリティ作成 |

## 実行フェーズとマイルストーン

### フェーズ0: 準備（0.5日）
- 依存ライブラリの確認 (`redis.asyncio` の有無等)
- テストカバレッジの確認（特に認証周り）
- 本計画のレビューおよび担当者割当

### フェーズ1: Critical対応（0.5日）
- C1: auth.py フォールバック削除
- C2: CORS 起動時検証およびデフォルト見直し

### フェーズ2: High対応（2.0日）
- H1: narrative.py 認証付与およびタスクオフロード設計
- H2: commercial.py await修正およびバックグラウンドタスク化
- H3: sse.py 非同期Redisまたはスレッドオフロード
- H4: rate_limit.py 原子化（Luaスクリプト）
- H5: tasks.py 設定スコープ隔離（設計段階で影響範囲確認）

### フェーズ3: Medium対応（1.5日）
- M1-M6 を順次実装（比較的独立）

### フェーズ4: Low対応および仕上げ（1.0日）
- L1-L4 を実装
- 全体テスト（特に認証・レートリミット・SSE・タスクキュー）
- ドキュメント更新およびコードレビュー

## リスクと代替案

| リスク | 説明 | 代替案/緩和策 |
|--------|------|----------------|
| 認証変更による後方互換性 | 本番で `ALLOWED_API_KEYS` 未設定かつ `test*` キーを使っていた場合、認証が切れる | 移行期間は警告ログを出し、猶予期間を設ける（例: 環境変数 `AUTH_ALLOW_TEST_KEY_FALLBACK=true` で一時許可） |
| Hueyタスク移行による遅延増加 | 同期実行から非同期へ変えることで即時レスポンスがなくなる | クライアント側でポーリングまたはWebSockets（既にSSEあり）へ移行を促す。タスク完了通知は既存SSE/エンドポイントで代用可 |
| Redis Luaスクリプトの互換性 | 一部RedisクラスターではLua制限がある | Luaが使えない場合は `pipeline(WATCH)` フォールバックを実装。テストで確認。 |
| 設定スコープ分離による大きな変更 | `ProjectContext` が広く使われているため影響範囲不明 | まずは読み取り専用参照にし、書き込みはタスクコンテキスト経由に徐々に移行。書き込み箇所を特定してから実装。 |

## 成果物
- 修正済みソースコード（各ファイル）
- 実装後の単体・結合テスト（既存テストを走らせ、カバレッジを維持/向上）
- 更新後のAPI仕様書（認証必須エンドポイントの明記、タスクIDベースの非同期エンドポイント追加等）
- 運用マニュアルへの追記（CORS設定方法、認証キーの必須設定等）

## 完了条件
- すべての Critical および High 項目が修正され、本番デプロイ可能な状態であること
- 既存の機能テストが全てパスすること（回帰なし）
- 新たに追加したセキュリティ・非同期に関するテストがパスすること
- コードレビューを経て、残る Medium/Low は改善余地としてバックログに残すこと

---
*作成日: 2026-08-28*
*対象リポジトリ: E:\sda*