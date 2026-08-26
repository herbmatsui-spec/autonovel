# ソフトウェアエンジニアリング品質向上実装計画書

本ドキュメントは、コードベースを世界クラスのエンジニアリング水準に引き上げるための詳細な実装計画である。

## 全体ロードマップ

### フェーズ 1: 基盤強化 (Foundation & Core)
**目的: 型安全性、ドメインモデルの純粋化、およびプロンプト管理の柔軟性を向上させ、開発速度と保守性を最大化する。
- **項目 1: ドメイン駆動設計 (DDD) の深化**
- **項目 2: 強力な型安全性と静的解析の徹底**
- **項目 5: プロンプトエンジニアリングのライフサイクル管理 (PromptOps)**

### フェーズ 2:堅牢性と観測可能性 (Robustness & Observability)
目的: システムの信頼性を高め、本番環境での挙動を完全に可視化する。
- **項目 3: 非同期処理の堅牢化とバックプレッシャー制御**
- **項目 4: 観測可能性 (Observability) の高度化**
- **項目 7: エラーハンドリングの戦略的統一**

### フェーズ 3: 拡張性と品質保証 (Scalability & QA)
目的: 外部拡張性を高め、自動化された品質ゲートによりデプロイリスクをゼロにする。
- **項目 6: テスト戦略の多層化 (Testing Pyramid)**
- **項目 8: プラグインアーキテクチャの動的拡張性の向上**
- **項目 9: CI/CD パイプラインの完全自動化と品質ゲート**

---

## フェーズ 1 詳細設計

### 1. ドメイン駆動設計 (DDD) の深化
#### 1.1 ドメイン層の新設
- `src/domain/` ディレクトリを作成し、インフラストラクチャ（SQLAlchemy, ChromaDB）から独立した純粋な Python クラスを定義する。
- `src/domain/models/`: エンティティ（Book, Plot, Character 等）を定義。
- `src/domain/services/`: ドメインロジック（例：プロットの整合性チェック）を定義。

#### 1.2 値オブジェクト (Value Object) の導入
- `PlotTension`, `CharacterRole`, `Genre` など、単なる文字列ではなくバリデーションを持つ不変クラスを導入し、不正な状態への遷移をコンパイル/実行時初期段階で防ぐ。

#### 1.3 リポジトリインターフェースの厳格化
- `src/backend/database/repositories/` の実装を、`src/domain/interfaces/` で定義した抽象リポジトリに従わせ、ビジネスロジックが DB 実装に依存することを排除する。

### 2. 強力な型安全性と静的解析の徹底
#### 2.1 mypy / pyright の厳格設定
- `pyproject.toml` または `mypy.ini` を作成し、`disallow_untyped_defs = True`, `warn_return_any = True` 等の Strict モードを有効化。
- `Any` の使用を禁止し、ジェネリクス (`TypeVar`, `Generic`) を活用して型を正確に伝搬させる。

#### 2.2 NewType による ID 型の区別
- `BookId = NewType('BookId', str)` 等を導入し、`chapter_id` を期待する関数に `book_id` を渡す等の論理エラーを静的に検出する。

#### 2.3 Pydantic V2 の完全活用
- API スキーマ (`src/models/api_schemas.py`) および設定モデルにおいて、Strict モードのバリデーションを適用。

### 5. プロンプトエンジニアリングのライフサイクル管理 (PromptOps)
#### 5.1 プロンプト・レジストリの構築
- `prompts/` 内の `.j2` ファイルを動的にロードし、バージョン管理を行う `PromptRegistry` クラスを実装。
- コードを書き換えずに YAML/JSON 設定ファイルからプロンプトのバージョンやパラメータを切り替え可能にする。

#### 5.2 プロンプト・バージョニングの統合
- `PromptVersionRepository` を通じて、DB 上でプロンプトの履歴を管理し、特定のバージョンを指定して LLM を呼び出せるようにする。

#### 5.3 A/B テスト用ルーターの実装
- `llm_service.py` または `model_router.py` に、ユーザー属性やリクエストに基づき、異なるバージョンのプロンプトを割り振るルーター機能を実装。

---

## フェーズ 2 詳細設計

### 4. 観測可能性 (Observability) の高度化

#### 4.1 OpenTelemetry 依存関係の追加 (Steps 1-3)
- **ステップ 1**: `requirements.txt` に `opentelemetry-api>=1.24.0` を追加
- **ステップ 2**: `requirements.txt` に `opentelemetry-sdk>=1.24.0` を追加
- **ステップ 3**: `requirements.txt` に `opentelemetry-exporter-otlp>=1.24.0` を追加

#### 4.2 OpenTelemetry 基盤の構築 (Steps 4-9)
- **ステップ 4**: `pyproject.toml` に OpenTelemetry 依存関係を追加
- **ステップ 5**: `oatentelemetry-sdk` の設定モジュールを `src/core/otel_setup.py` に作成
- **ステップ 6**: OTLP エクスポーターの設定（JSON、OTLP HTTP、OTLP gRPC の3つの設定オプション）
- **ステップ 7**: バッググラウンド/フロントエンド向けのトレーサー初期化関数
- **ステップ 8**: 環境変数ベースの設定構成 (OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_SERVICE_NAME)
- **ステップ 9**: デフォルトスペンダー/メトロクス収集の有効化

#### 4.3 既存コードのOpenTelemetry化 (Steps 10-20)
- **ステップ 10**: `src/core/observability.py` をリファクタリング（既存TraceContext保持、OTLPエクスポーター追加）
- **ステップ 11**: FastAPI アプリケーションに `FastAPIInstrumentor` を適用
- **ステップ 12**: HTTPクライアント (`requests`, `aiohttp`) 用インストルメンテーション
- **ステップ 13**: データベース接続 (SQLAlchemy) 用インストルメンテーション
- **ステップ 14**: ChromaDB クライアントのトレーシング
- **ステップ 15**: Redis クライアントのトレーシング
- **ステップ 16**: Huey バックグラウンドジョブのトレーシング
- **ステップ 17**: LLM API 呼び出し (`google-genai`) 用スパン計測
- **ステップ 18**: プロンプトテンプレートレンダリングのトレーシング
- **ステップ 19**: コンテキスト管理 (`contextvars`) との連携
- **ステップ 20**: 例外ハンドリングとエラースパンの強化

#### 4.4 カスタムメトリクス実装 (Steps 21-27)
- **ステップ 21**: `CostMetrics` クラスを `src/core/metrics.py` に作成
- **ステップ 22**: LLMコスト計測 (トークン数 × 単価) 用メトリクスCollector
- **ステップ 23**: 生成品質指標 (BLEU, ROUGE相当指標) 用メトリクス
- **ステップ 24**: 応答時間レイテンシメトリクスの計測
- **ステップ 25**: エラーレート計測メトリクス
- **ステップ 26**: リクエスト数 / バックループ検出 用メトリクス
- **ステップ 27**: カスタムプロップメトリックのRedis保存

#### 4.5 OpenTelemetry Collector 設定 (Steps 28-32)
- **ステップ 28**: `otel-collector-config.yaml` テンプレート作成
- **ステップ 29**: エクスポート先設定 (Grafana Cloud/OTLP HTTPエンドポイント)
- **ステップ 30**: データ処理パイプライン (batch, memory limiter) 設定
- **ステップ 31**: サンプリングポリシー (head-based, tail-based) 設定
- **ステップ 32**: 再送/バックオットレ抑制機能の有効化

#### 4.6 Grafana ダッシュボード構築 (Steps 33-40)
- **ステップ 33**: Grafana OTLP データソース接続設定
- **ステップ 34**: '生成品質ダッシュボード' (Quality Dashboard) - BLEU/ROUGE類似度推移
- **ステップ 35**: 'コスト分析ダッシュボード' (Cost Dashboard) - 日次/月次LLM利用コスト
- **ステップ 36**: 'レイテンシダッシュボード' (Latency Dashboard) - P99/P95/P50応答時間
- **ステップ 37**: 'エラーレートダッシュボード' (Error Dashboard) - エラー発生率推移
- **ステップ 38**: 'トレーシングビューア' 用 dashboard の構築
- **ステップ 39**: アラート用メトリクスの可視化パネル
- **ステップ 40**: マルチサービスモニタリング用 Overview Dashboard

#### 4.7 アラート設定 (Steps 41-46)
- **ステップ 41**: P99 レイテンシアラート 定義 (5秒を超える場合)
- **ステップ 42**: P95 レイテンシアラート 定義 (3秒を超える場合)
- **ステップ 43**: エラーレート >= 5% のアラート設定
- **ステップ 44**: LLM コスト閾値アラート (月間 $100超過時)
- **ステップ 45**: バックプレッシャー検知アラート (キュー長 > 1000)
- **ステップ 46**: 通知ルール (Slack/Email) の設定

#### 4.8 本番運用準備 (Steps 47-48)
- **ステップ 47**: 環境別設定 (dev/staging/prod) の分離
- **ステップ 48**: ドキュメンテーション作成 (運用マニュアル, トラブルシューティングガイド)

---

## 完了定義 (Definition of Done) - フェーズ 1
1. [ ] `src/domain/` が構築され、主要なエンティティが DB モデルから分離されている。
2. [ ] `mypy` による静的解析がエラーなく通り、`Any` の使用が極小化されている。
3. [ ] プロンプトの変更が Python コードの変更を伴わず、設定ファイルまたは DB 経由で完結している。
4. [ ] `NewType` により ID の型安全性が確保されている。

## 完了定義 (Definition of Done) - フェーズ 2 項目4
1. [ ] `pyproject.toml` / `requirements.txt` に OpenTelemetry 依存関係が追加されている
2. [ ] `src/core/otel_setup.py` が作成され、OTLP エクスポーターが正しく設定されている
3. [ ] `src/core/observability.py` が OpenTelemetry SDK と連携している
4. [ ] FastAPI アプリケーションがトレースを生成している
5. [ ] 主要サービス (LLM, DB, Redis, ChromaDB) がスパンを生成している
6. [ ] コストメトリクスが正しく計測されている
7. [ ] OpenTelemetry Collector 設定ファイルが作成されている
8. [ ] Grafana ダッシュボード (4種) が作成され、データが表示されている
9. [ ] P99/P95/エラーレート/コストアラートが設定され、正しく動作している
10. [ ] 本番環境向け設定とドキュメントが整備されている
