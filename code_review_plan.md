# autonovel コードレビュー改善計画書

## 1. 概要

本計画書は、autonovel プロジェクト全体のコードレビューにおいて指摘された課題を解消するためのロードマップである。レビューでは「重大な問題 5 件」「主要な問題 6 件」「軽微な問題 6 件」「改善提案 10 件」が挙げられた。本計画の目的は、これらを優先度順に整理し、セキュリティ・信頼性・保守性を向上させるとともに、プロジェクトが採用している厳格な品質ゲート（ruff / mypy --strict / pre-commit）への完全準拠を達成することである。

想定工数は約 3 〜 4 週間（1 名〜2 名の開発者）。各フェーズは独立して検証可能とし、CI によって品質が regression しないことを担保する。

## 2. 現状分析と優先度

### 2.1 重大（P0：即時対応）
1. `EngineService` のシングルトンが可変状態を共有し、非同期環境で競合・状態漏洩のリスクがある。
2. `RedisRateLimiter.is_allowed` が Redis エラー時に「許可」とみなすフェイルオープン動作で、DDoS 耐性がない。
3. `commercial_validation.py` の Playwright 呼び出しにタイムアウトがなく、イベントループを.blockする。
4. `AUTH_DISABLED` 環境変数により認証が誤ってバイパスされる可能性がある。
5. `safe_model_validate` が Pydantic バリデーションエラーを丸め込み、開発時の検知が遅れる。

### 2.2 主要（P1：短期対応）
- 公開関数の型ヒント・docstring 不足（mypy --strict 違反）。
- `compute_ngram_similarity` の空白除去による類似度精度低下。
- `extract_markdown_content` のフェンス検出が言語指定に対応していない。
- `AdaptiveCooldown._fire_adjust_rate` が生成タスクを待機せず例外を捨てる。
- `PromptCacheService.invalidate_task_type` の無効化パターンが実キーと不一致。
- `generate_task_id` の UUID 12 文字切り詰めによる衝突リスク。

### 2.3 軽微（P2：継続改善）
- 未使用インポートの残存。
- 本番モジュール内の `print` 文。
- マジックナンバーの散在。
- 大容量オブジェクトのログ出力。
- Redis パターン文字列のエスケープ不足。
- レートリミット例外時のフォールバック動作。

## 3. 目標

- 重大項目 5 件を 100% 解消し、本番環境でのセキュリティ・可用性インシデントを防止する。
- `mypy --strict` と `ruff` の Warning を 0 にし、pre-commit フックがすべてパスする状態を維持する。
- 外部 I/O（Redis / Playwright / HTTP）に統一されたタイムアウトとリトライ戦略を導入する。
- キャッシュ無効化の正確性を単体テストで証明する。
- 機密情報（API キー等）がログに露出しないよう、マスキング方針を標準化する。

## 4. 実施フェーズ

### フェーズ 0：準備（Day 1-2）
- 品質ゲートの現状確認：`pre-commit run --all-files` と `mypy --strict src` を実行し、ベースライン件数を記録。
- ブランチ `refactor/code-review-plan` を作成し、CI に「品質ゲート必須」ステップを追加。
- 定数管理モジュール `config/constants.py` を新設し、既存のマジックナンバーを抽出。

### フェーズ 1：セキュリティ・信頼性の即時修正（Day 3-8）
- `EngineService` を依存性注入（DI）コンテナ経由で取得するよう変更し、インメモリストアをリクエストスコープのリポジトリへ移動。シングルトンは廃止または読み取り専用設定のみに限定。
- `RedisRateLimiter` に `RATE_LIMIT_FAIL_OPEN` 設定を追加し、デフォルトをフェイルクローズ（リクエスト拒否）に変更。Redis 障害時は `429` または `503` を返す。
- `commercial_validation.py` の `page.goto` / `browser.launch` に `timeout=30000` 等の引数を追加し、`asyncio.wait_for` で全体を包む。
- `auth.py` の `disabled` プロパティを修正：`ENVIRONMENT != "development"` かつ `AUTH_DISABLED=true` の場合は起動時に例外を送出。
- `safe_model_validate` で元例外を `logger.debug` に出力（機密は除外）してから再試行し、失敗時は詳細を含む `LLMValidationError` をraise。

### フェーズ 2：主要課題の解消（Day 9-16）
- 全公開関数へ型ヒントを付与し、docstring を整備。`mypy --strict` のエラーを 0 にする。
- `compute_ngram_similarity` をトークンベース（`re.findall(r"\w+", text.lower())`）へ変更、または「日本語専用」と明記。
- `extract_markdown_content` を `markdown-it-py` 等のパーサへ置換、または任意言語フェンスを受け入れる正規表現へ拡張。
- `AdaptiveCooldown._fire_adjust_rate` を `async def` とし、呼び出し側で `await` するか結果をログに記録。
- `PromptCacheService` のキャッシュキー形式を `prompt:{template}:{model}:{version}:{hash}` に固定し、無効化パターンを実構造へ合わせる。タスクタイプ別は `prompt:{template}:*:{task_type}:*` を使用。
- `generate_task_id` の UUID 切り出しを 16 文字以上に拡張。

### フェーズ 3：軽微・保守性向上（Day 17-22）
- `ruff` の未使用インポート検出を有効化し、自動修正を適用。
- 本番モジュールの `print` を `logger` 呼び出しへ置換。
- マジックナンバーを `config/constants.py` の定数へ統合。
- ログ出力前にオブジェクトを要約・切り詰め、機密フィールドはマスク関数を通す。
- Redis パターン生成時に `template_name` をサニタイズ。
- レートリミット例外時は `503` を返す方針へ変更。

### フェーズ 4：テスト・ドキュメント・検証（Day 23-28）
- 認証バイパス、レートリミット障害、キャッシュ無効化、Playwright タイムアウトの失敗シナリオを模した単体・統合テストを追加。
- `mock_redis` / `mock_playwright` を活用し、CI で安定実行できること dangerを確認。
- 本計画の成果を `coverage_review.md` へ追記し、品質メトリクス（mypy エラー数、ruff 違反数、テストカバレッジ）の推移を記録。

## 5. スケジュール（目安）

| 週 | フェーズ | 成果物 |
|----|----------|--------|
| 1 | 0, 1 | DI 対応、レートリミット・認証・タイムアウト修正 |
| 2 | 2 | 型ヒント完了、キャッシュキー整合 |
| 3 | 3 | 軽微修正、定数集約、ログ保護 |
| 4 | 4 | テスト追加、ドキュメント更新、CI グリーン |

## 6. 成果指標（KPI）

- `mypy --strict` エラー数：現状 → 0
- `ruff` 違反数：現状 → 0
- pre-commit フック：全項目パス
- 重大項目解消率：100%
- 単体テスト追加数：最低 20 件（失敗系含む）
- 認証バイパス未遂をログで検知可能であること

## 7. リスクと対策

- **DI リファクタの影響範囲が広い**：既存の `get_instance()` 呼び出しを段階的に `AppContainer` 経由へ移行し、互換レイヤーを一時的に残す。
- **Redis フェイルクローズによる誤拒否**：本番導入前にカナリア環境で検証し、監視アラートを設定。
- **型ヒント追加での動作 regression**：mypy 修正と併せて既存テストを全件実行し、API 契約に変化がないことを確認。
- **外部ライブラリ追加（markdown-it-py 等）の重量**：Poetry / requirements に最小バージョンを固定し、CI のキャッシュを活用。

## 8. まとめ

本計画に沿って優先度順に修正を進めることで、autonovel のセキュリティインシデントリスクを大幅に低減し、非同期・分散環境下での信頼性を高めることができる。同時に厳格な静的解析・lint ゲートを完全準拠とすることで、今後の機能拡張時にも品質が持続的に保たれる基盤が完成する。
