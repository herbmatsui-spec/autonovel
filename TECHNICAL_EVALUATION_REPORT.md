# 覇権小説エンジン v3.0 技術評価レポート

## 1. Executive Summary

覇権小説エンジン v3.0 は、FastAPI + Streamlit + Huey の3層アーキテクチャによるWeb小説自動生成プラットフォームです。生成AI（Google Gemini）を活用し、企画・プロット・執筆・監査・納品までの全工程を自動化することを目的としています。

**総合評価：6.5 / 10**

- アーキテクチャは層状分離・DI・UoWなど一定の設計品質を持つ
- テストカバレッジが広く（150+ファイル、~14k LOC）、CI/CDが整備されている
- 型安全性（mypy strict）がCIで非阻止になっている点や、Alembicマイグレーションがバイパスされている点など、成熟度ギャップが存在する
- 実行検証の結果、データベーススキーマ不整合（`internal_state.updated_at`のDATETIME型と文字列挿入の不整合）が実際に発生し、修正が必要であった

---

## 2. アーキテクチャ・設計

### 2.1 層状分離
- **src/backend/**: FastAPIルーター、ワークフロー、Hueyタスク
- **src/services/**: LLMサービス、ベクトルストア、ビジネスロジック
- **src/agents/**: AIオーケストレーション（ADR-0002）
- **src/core/**: 例外、トレースID、共通ユーティリティ
- **src/llm/**: Geminiクライアント、モデル選択
- **src/infrastructure/**: APIクライアント、DIコンテナ

ルーターは薄く、ワークフローに委譲する構造になっている（`src/backend/server.py:117-132`）。

### 2.2 依存性注入
- `dependency-injector` を使用したDIコンテナが2つ存在する（`config/container.py:9`、`src/core/container.py:23`）
- リクエストごとのAPIキー注入が可能で、テスト時の差し替えが容易

### 2.3 非同期処理
- SQLAlchemy 2.0 の非同期エンジンを使用
- Hueyタスクワーカー（SQLiteフォールバック対応）で重い生成処理を非同期化
- ExecutorManagerによるIO/CPUプールの分離

## 3. コード品質

### 3.1 型安全性
- `pyproject.toml` で `strict = true` が設定されているが、CIの`typecheck`ジョブは `continue-on-error: true`（`github/workflows/ci.yml:38-51`）
- 残余エラー数：1,769件（CIコメントより）
- 型安全性は「努力目標」であり、 enforced ではない

### 3.2 コードスメル
- **広域例外処理**: `src/` 内に253件の `except Exception`、7件の bare `except` が存在
- **print文**: 31件の `print()` がログフレームワークの代わりに使用されている（例: `src/backend/database/core.py:273`）
- **デバッグコードの残留**: `print(f"DEBUG: ini_path=...")` が本番コードに残存

### 3.3 重複コード
- リポジトリ層が2重化: `src/backend/database/repo_*.py` と `src/backend/database/repositories/*.py`
- 特に`foreshadow`関連は`repositories/plot.py`の foreshadow メソッドが「 dead code」と注釈されている（`src/backend/routers/foreshadow.py:8-9`）

### 3.4 設定管理
- `config/base.py` に多数のアーキタイプ variant が存在（`archetypes.py`、`archetypes_ascii.py`、`archetypes_stub.py`、`archetypes_test.py` など）
- SSOT（Single Source of Truth）が `config/settings.toml` に移ったと記載があるが、`config/base.py` が実質的なインポート元になっている

## 4. テスト・品質管理

### 4.1 テスト規模
- テストファイル数：150+（`tests/unit` ~57、`tests/integration` ~17、`tests/performance` 3、`tests/mocks` 8、`tests/ui` 4、ルート `test_*.py` 8）
- テストLOC：~14,144
- CIは lint（ruff）、型検査（mypy）、ユニット/統合テスト（pytest）を実行

### 4.2 テスト戦略
- モックが充実（25+モジュール）
- 統合テストはChromaDB（0.5.5）とRedis（7）のコンテナを必要とする
- ユニットテストは実ファイルが少なく、モック依存が高い

## 5. パフォーマンス・信頼性

### 5.1 LLM耐性
- `src/services/retry_decorator.py:80-261` に適応型指数バックオフ、温度減衰、5xx連続時のモデルフォールバック（STABLE → ULTRA_STABLE）を実装
- 回復不能エラーは `LLMUnrecoverableError` として早期に失敗

### 5.2 データベース
- SQLAlchemy 2.0 async + `pool_pre_ping`、WAL mode、busy_timeout
- Unit of Work + Outboxパターン（`src/backend/database/uow.py:33-219`）
- **問題点**: Alembicマイグレーションが起動時にバイパスされ、`create_all` が使用される（`src/backend/database/core.py:283-284`）
- **問題点**: 23件のマイグレーションスクリプトが存在するが、実运行では使われていない（スキーマドリフトのリスク）

### 5.3 ベクトル検索
- ChromaDB（RAG/文体ラボ等）をOptionalで使用
- 未導入時は機能が無効化される

## 6. セキュリティ

### 6.1 シークレット管理
- APIキーはリクエストボディで受け渡し（`req.api_key`）
- 認証レイヤーは存在せず、ローカルツールとしては許容範囲内
- レート制限はLLMクールダウンのみで、APIレベルでのレートリミットは未実装

### 6.2 入力検証
- Pydanticモデルによるバリデーション
- AI生成パッチに対するASTベースのガード（`src/backend/patch_validator.py:22-26`）— `eval/exec/os.system/subprocess/open/getattr` をブロック

### 6.3 CORS
- `allow_credentials=True` と `allow_methods=["*"]`、`allow_headers=["*"]` の組み合わせは、幅広いオリジンが設定された場合に危険

## 7. 機能完全性

### 7.1 かんたんモード
- フルオートワークフロー: `src/backend/workflows/full_auto_workflow.py`
- 企画生成 → 並列執筆 → 納品パッケージ作成の3ステップ
- ストレス/カタルシス自動制御ループを内蔵
- 実行時には `is_easy_mode=True` が各所で品質チェックをスキップする設計

### 7.2 上級者モード
- プロット管理、本文執筆、監査・チケット管理、文体ラボ、伏線トラッカー、官能描写サブエンジンなど多機能
- ただしUIの複雑性が高く、学習コストが大きい

### 7.3 UI
- Streamlit UIが実装済み
- React（`frontend/`）は移行中だが未着手で、`frontend/dist/` にビルド済み資産が存在する状態（矛盾）

## 8. 実行検証で発見された問題

### 8.1 データベーススキーマ不整合
- **事象**: `internal_state` テーブルの `updated_at` カラムが `DATETIME` 型であるにもかかわらず、複数の箇所で文字列（`time.strftime(...)`）を挿入しようとして `SQLite DateTime type only accepts Python datetime and date objects` エラーが発生
- **影響**: タスク状態の保存が失敗し、進捗表示が機能しない
- **修正**: `save_internal_state` のシグネチャと全呼び出し元をdatetimeオブジェクトに修正（実装済み）

### 8.2 古いAPIキーの漏洩ブロック
- **事象**: コードベースにハードコードされたテスト用APIキー (`AIzaSyD5vwqaRbquOO554oX7pfESV7Rv5ooleR4`) は、Google側で「漏洩」として報告され、403 PERMISSION_DENIED でブロックされている
- **影響**: レガシースクリプトやテストが全て失敗する
- **推奨**: ハードコードされたキーを削除し、環境変数管理に統一

### 8.3 Hueyワーカーのインポート不備
- **事象**: `save_prompt_metrics` タスク内で `asyncio` がインポートされておらず、`name 'asyncio' is not defined` エラーが発生
- **影響**: プロンプトメトリクスの保存が失敗

### 8.4 ProgressStateのDB保存不整合
- **事象**: `src/backend/background.py:129` で `datetime.datetime.now().isoformat()` が文字列を生成し、`save_internal_state`（datetimeオブジェクト要求）に渡されている
- **影響**: 進捗状態のDB保存が失敗

## 9. 弱点・リスク

| リスク | 深刻度 | 備考 |
|---|---|---|
| mypy strict がCIで非阻止 | 中 | 1,769件の残余エラーが放置されている |
| Alembicマイグレーションの未使用 | 高 | スキーマドリフト、非再現性のリスク |
| 重複リポジトリ層 | 中 | 保守性とバグ混入リスク |
| プラグインシステムのADR不整合 | 低 | ドキュメントと実装が乖離 |
| broad exception handling | 中 | エラー原因の特定を困難にする |
| 未実装React UIのビルド資産混在 | 低 | 混乱の原因 |
| APIキーの漏洩リスク | 高 | ハードコードされた古いキーが存在 |

## 10. 推奨アクション

### 即時対応（クリティカル）
1. `save_internal_state` の型不整合を修正（実施済み）
2. 古いハードコードAPIキーの削除
3. Alembicマイグレーションの再有効化、または`create_all`方針を明確化

### 短期対応（1〜2スプリント）
4. mypy残余エラーの段階的解消（`continue-on-error`を段階的に厳格化）
5. 重複リポジトリ層の統合（`repo_*.py` または `repositories/*.py` のいずれかに統一）
6. broad exception handling の具体化
7. `print()` のログフレームワークへの置き換え

### 中期対応（3〜6スプリント）
8. プラグインシステムのADR再設計または実装修正
9. React UI移行の進捗管理（`frontend/dist/` の整理）
10. APIレート制限と認証レイヤーの実装

---

*評価日: 2026-07-16*
*評価者: Kilo (automated technical evaluation)*
