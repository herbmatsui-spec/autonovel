# 懸念点対応 詳細実装計画（48ステップ）

## 概要
前回の評価で指摘した2つの懸念点について、低性能LLMでも実装可能な粒度（1タスク≒1ファイル・1関数レベル）に分解した実装計画です。

---

## Phase A: アーキテクチャの複雑化対策（ドキュメント整備・可視化） - Steps 1-24

### A-1: アーキテクチャ決定記録（ADR）の導入
| Step | タスク名 | 対象ファイル/成果物 | 実装内容 | 完了条件 |
|:---|:---|:---|:---|:---|
| 1 | ADRテンプレート作成 | `docs/adr/template.md` | タイトル、背景、決定事項、影響、代替案のセクションを持つMarkdownテンプレートを作成 | テンプレートファイルが存在し、サンプルが1つ入っている |
| 2 | 既存アーキテクチャのADR化（State管理） | `docs/adr/001-state-management.md` | `UIStateStore` 採用の理由と代替案（st.session_state直書き等）を記述 | ファイルが存在し、意思決定ログが残っている |
| 3 | 既存アーキテクチャのADR化（Pluginシステム） | `docs/adr/002-plugin-system.md` | `PluginLoader` 採用理由、フックポイント、拡張方法を記述 | ファイルが存在し、拡張ガイドへのリンクがある |
| 4 | 既存アーキテクチャのADR化（Engine仲介） | `docs/adr/003-engine-mediator.md` | `EngineService` と `engine.py` の役割分担、非同期境界の扱いを記述 | ファイルが存在し、シーケンス図(Mermaid)が含まれる |

### A-2: コードベース構造の可視化（自動生成）
| Step | タスク名 | 対象ファイル/成果物 | 実装内容 | 完了条件 |
|:---|:---|:---|:---|:---|
| 5 | ディレクトリツリー生成スクリプト | `scripts/gen_tree.py` | `tree` コマンド風のMarkdownツリーを `docs/architecture/structure.md` に出力するスクリプト | 実行すると最新の構造がMarkdownで出力される |
| 6 | モジュール依存グラフ生成 | `scripts/gen_deps.py` | `pydeps` または `importlib` を用い、主要モジュール(`streamlit_app/`, `src/`)の依存関係をMermaidグラフで `docs/architecture/deps.md` に出力 | Mermaid記法で依存関係が可視化される |
| 7 | CIへの組み込み | `.github/workflows/docs.yml` | PR作成時に上記スクリプトを実行し、ドキュメントを自動更新するワークフロー | GitHub Actionsで自動実行され、コミットされる |
| 8 | アーキテクチャ概要図（Mermaid） | `docs/architecture/overview.mmd` | C4モデル(Context/Container)レベルで全体像を記述。コンテナ: Frontend(Streamlit), Backend(API), DB, LLM | Mermaid Live Editorで正しく描画される |

### A-3: データフロー・シーケンスのドキュメント化
| Step | タスク名 | 対象ファイル/成果物 | 実装内容 | 完了条件 |
|:---|:---|:---|:---|:---|
| 9 | 起動シーケンス図 | `docs/sequences/startup.mmd` | `app.py:main()` から `PluginLoader` -> `health_check` -> `sidebar` -> `navigation` までの流れ | Mermaidシーケンス図として正しく描画される |
| 10 | 生成リクエストシーケンス図 | `docs/sequences/generation.mmd` | UIタブ -> `EngineService` -> Backend API -> SSE/Stream -> UI更新 の流れ | 非同期境界とエラーハンドリング箇所が明記されている |
| 11 | 状態変更フロー図 | `docs/sequences/state_change.mmd` | `UIStateStore.subscribe` / `set_runtime` -> UI再描画 のトリガーと伝播 | どのコンポーネントが購読しているかリスト化されている |
| 12 | プラグインロードフロー図 | `docs/sequences/plugin_load.mmd` | `PluginLoader.load_all_plugins` -> エントリーポイント発見 -> `register` 呼び出し -> フック登録 | 自作プラグイン開発者が読んで実装できるレベルの詳細さ |

### A-4: 開発者向けガイド（How-to）の整備
| Step | タスク名 | 対象ファイル/成果物 | 実装内容 | 完了条件 |
|:---|:---|:---|:---|:---|
| 13 | 新規UIタブ追加ガイド | `docs/guides/add_ui_tab.md` | `ui_tabs_*.py` 作成 -> `pages_config.py` 登録 -> `workflow_types.py` 定義 の手順 | ガイド通りに実施すると新タブがメニューに表示される |
| 14 | 新規プラグイン作成ガイド | `docs/guides/add_plugin.md` | `src/plugins/` 配下にディレクトリ作成 -> `plugin.yaml` 定義 -> `register()` 実装 -> フック活用例 | サンプルプラグイン(`echo_plugin`)が動作する |
| 15 | 状態管理のベストプラクティス | `docs/guides/state_management.md` | `UIStateStore` の `get_runtime`/`set_runtime` 使い分け、副作用のない書き方、テスト時のモック方法 | 典型的なアンチパターン（直接 `st.session_state` 書き込み）が警告されている |
| 16 | バックエンドAPI呼び出し共通化ガイド | `docs/guides/api_client_usage.md` | `api_client.py` の `request_with_retry` 利用法、タイムアウト設定、ストリーミング対応 | 既存の `engine.py` 内の呼び出し箇所がこのガイドに準拠している |

### A-5: オンボーディング支援
| Step | タスク名 | 対象ファイル/成果物 | 実装内容 | 完了条件 |
|:---|:---|:---|:---|:---|
| 17 | 用語集 | `docs/glossary.md` | Orchestrator, State Keeper, Engine Mediator, Plugin Hub, UI Components, Reliability Agent 等の定義 | プロジェクト固有用語が全て定義されている |
| 18 | よくある質問（FAQ） | `docs/faq.md` | 「なぜPluginシステムなのか」「StateStoreとst.session_stateの違い」「非同期処理のデバッグ方法」等 | 実運用で出た質問ベースで10件以上記載 |
| 19 | クイックスタート（開発環境） | `docs/quickstart_dev.md` | `uv sync` / `pre-commit install` / `streamlit run streamlit_app/app.py` までの手順 | 新規クローンから5分で起動確認できる |
| 20 | アーキテクチャ決定ログ索引 | `docs/adr/index.md` | 全ADRへのリンク集と、ステータス（提案中/承認済/廃止）一覧 | 索引から全ADRに遷移可能 |

### A-6: 静的解析・品質ゲートのドキュメント化
| Step | タスク名 | 対象ファイル/成果物 | 実装内容 | 完了条件 |
|:---|:---|:---|:---|:---|
| 21 | 型チェック設定の説明 | `docs/quality/typing.md` | `mypy.ini` の厳格度設定理由、`# type: ignore` 許可基準、段階的導入戦略 | 現状のエラー数と目標値が記載されている |
| 22 | 循環的依存チェックルール | `docs/quality/circular_deps.md` | `import-linter` または `pydeps` で禁止している層間依存（UI->Domain逆依存等）のルール定義 | CIで検知され、違反時にエラーになる |
| 23 | 複雑度メトリクス閾値 | `docs/quality/complexity.md` | `radon` / `wemake-python-styleguide` での関数/クラス複雑度の上限値とリファクタリング基準 | 数値基準が明文化され、CIでチェックされる |
| 24 | ドキュメント整合性テスト | `tests/test_docs_consistency.py` | ADR/ガイド内のコードスニペットが実際に動くか `doctest` または簡易実行で検証するテスト | `pytest tests/test_docs_consistency.py` がパスする |

---

## Phase B: バックエンド依存・耐障害性強化 - Steps 25-48

### B-1: 共通リトライ・サーキットブレーカー基盤
| Step | タスク名 | 対象ファイル/成果物 | 実装内容 | 完了条件 |
|:---|:---|:---|:---|:---|
| 25 | リトライ設定データクラス定義 | `src/shared/retry_policy.py` | `RetryPolicy(max_attempts, base_delay, max_delay, exponential_base, jitter, retryable_status_codes)` を `dataclass` で定義 | 型ヒント付きでインポート可能 |
| 26 | サーキットブレーカー状態管理 | `src/shared/circuit_breaker.py` | `CircuitBreakerState(CLOSED, OPEN, HALF_OPEN)` Enum と、失敗カウント/成功カウント/最終失敗時刻を持つ `CircuitBreaker` クラス | 状態遷移テスト(`tests/unit/test_circuit_breaker.py`)がパスする |
| 27 | 統合HTTPクライアント実装 | `src/shared/resilient_http.py` | `httpx.AsyncClient` ラッパー。`RetryPolicy` と `CircuitBreaker` を併用し、指定例外/ステータスコードでリトライ・遮断 | 既存 `api_client.py` の `request_with_retry` をこのクラスに置き換え可能 |
| 28 | 設定外部化（YAML） | `config/resilience.yaml` | エンドポイントごとの `RetryPolicy` / `CircuitBreaker` 閾値を定義（デフォルト値含む） | `yaml.safe_load` で読み込み、Pydanticモデルでバリデーション可能 |
| 29 | 設定ローダー実装 | `src/shared/resilience_config.py` | `config/resilience.yaml` を読み込み、`ResilienceConfig` シングルトンとして提供するローダー | アプリ起動時に一度だけ読み込まれ、ホットリロード不要 |

### B-2: 既存APIクライアントへの適用
| Step | タスク名 | 対象ファイル/成果物 | 実装内容 | 完了条件 |
|:---|:---|:---|:---|:---|
| 30 | `api_client.py` リファクタ | `streamlit_app/api_client.py` | 内部実装を `ResilientHttpClient` に委譲。インターフェース(`get`, `post`, `stream`)は維持 | 既存テスト `tests/mocks/mock_api_client.py` 互換性を保ち全テストパス |
| 31 | `engine.py` ストリーミング対応強化 | `streamlit_app/engine.py` | SSE/ストリーミング応答時もリトライ・タイムアウト制御が効くよう `ResilientHttpClient.stream` を使用 | 通信断絶時にリトライログが出力され、復旧後に継続または適切にエラー終了 |
| 32 | ヘルスチェック専用ポリシー適用 | `streamlit_app/health_check.py` | `ensure_backend_available` で短いタイムアウト・リトライ1回・即時遮断の専用ポリシーを使用 | バックエンド起動待ち時間が短縮され、誤検知が減る |

### B-3: Graceful Degradation（段階的縮退）機構
| Step | タスク名 | 対象ファイル/成果物 | 実装内容 | 完了条件 |
|:---|:---|:---|:---|:---|
| 33 | 機能フラグ/可用性レジストリ | `src/shared/feature_registry.py` | `FeatureRegistry` クラス。機能名 -> `available: bool`, `fallback: Callable`, `degraded_message: str` を管理 | 機能ごとに有効/無効/代替動作を切り替え可能 |
| 34 | バックエンド依存機能の登録 | `streamlit_app/app.py` (初期化部) | 起動時・ヘルスチェック時に `FeatureRegistry.register("generation", ...)`, `"analysis"`, `"audit"` 等を登録 | レジストリに主要機能が登録され、UI側から参照可能 |
| 35 | UIタブ側の可用性チェック共通化 | `streamlit_app/ui_utils.py` | `render_if_available(feature_name: str, render_fn: Callable)` ヘルパー作成。不可時はフォールバックUI表示 | 全 `ui_tabs_*.py` がこのヘルパー経由でラップ可能 |
| 36 | フォールバックUIコンポーネント | `streamlit_app/ui_components.py` | `render_degraded_banner(feature_name, message)`, `render_cached_result_if_any(feature_name)` を追加 | ユーザーに「現在この機能は制限付きで利用可能」等が明示される |
| 37 | キャッシュベースの読み取り専用モード | `streamlit_app/background.py` | バックエンド不可時、過去の生成結果(DB/ローカルストレージ)を読み取り専用で表示するモード実装 | `FeatureRegistry` で `fallback=lambda: render_cached_results()` が動作する |

### B-4: 観測性・運用支援
| Step | タスク名 | 対象ファイル/成果物 | 実装内容 | 完了条件 |
|:---|:---|:---|:---|:---|
| 38 | 構造化ログへのリトライ/遮断情報付与 | `config/logging_config.py` | `ResilientHttpClient` / `CircuitBreaker` が `structlog` で `event="retry_attempt"`, `event="circuit_open"` 等を出力 | ログ集約基盤でリトライ回数・遮断発生をダッシュボード化可能 |
| 39 | メトリクス公開 | `src/shared/metrics.py` | `prometheus_client` Counter/Gauge: `http_retry_total`, `circuit_breaker_state`, `feature_degraded_total` | `/metrics` エンドポイント(またはPushgateway)で取得可能 |
| 40 | ヘルスチェックエンドポイント拡張 | `src/api/health.py` (新規) | FastAPI/Starletteエンドポイント `/health/detailed` を追加。各下流依存(DB, LLM API, VectorStore)の到達性・レイテンシを返す | `curl /health/detailed` でJSONが返り、各依存のstatusが見える |
| 41 | フロントエンド側ヘルス表示 | `streamlit_app/sidebar.py` | サイドバーに「バックエンド: 正常/劣化/停止」「機能別可用性バッジ」を表示 | ユーザーが現在のシステム状態を視認可能 |

### B-5: テスト・カオスエンジニアリング
| Step | タスク名 | 対象ファイル/成果物 | 実装内容 | 完了条件 |
|:---|:---|:---|:---|:---|
| 42 | リトライ動作の単体テスト | `tests/unit/test_resilient_http.py` | `respx` または `httpx.MockTransport` で 500/Timeout を注入し、指定回数リトライ→成功/失敗を検証 | 設定通りの回数・間隔でリトライされることをアサート |
| 43 | サーキットブレーカー遷移テスト | `tests/unit/test_circuit_breaker.py` | 失敗閾値到達でOPEN -> クールダウン後HALF_OPEN -> 成功でCLOSED 遷移を検証 | 状態遷移図通りの振る舞いを時刻モック込みで検証 |
| 44 | Graceful Degradation 統合テスト | `tests/integration/test_graceful_degradation.py` | `TestClient` でバックエンドを落とし、UIタブアクセス時にフォールバックUIが出るか検証 (Playwright/Streamlit testing利用) | バックエンド停止中でも「キャッシュ表示」「読み取り専用」が動作 |
| 45 | カオス実験スクリプト | `scripts/chaos/fail_backend.py` | `toxiproxy` または `iptables` / Windowsファイアウォール操作でバックエンドポートを遮断・復旧させるスクリプト | 手動実行で「遮断->検知->遮断解除->復旧」シナリオが再現可能 |
| 46 | 負荷試験シナリオ | `tests/load/locustfile.py` | Locustシナリオ: 同時接続数を増やしつつ、バックエンドに遅延/エラーを注入し、フロントエンドのリトライ・遮断が連鎖障害を防ぐか観測 | シナリオ実行後、メトリクス(`circuit_breaker_state`)が適切に遷移し、フロントエンドがクラッシュしない |

### B-6: ドキュメント・運用手順
| Step | タスク名 | 対象ファイル/成果物 | 実装内容 | 完了条件 |
|:---|:---|:---|:---|:---|
| 47 | 障害対応ランブック | `docs/runbooks/backend_down.md` | 「バックエンドダウン検知 -> サーキットOPEN確認 -> フォールバック動作確認 -> 原因調査 -> 復旧手順 -> CLOSED確認」の手順書 | 当番エンジニアが初めて見ても対応可能な粒度 |
| 48 | 耐障害設計ドキュメント | `docs/architecture/resilience.md` | 全体像: リトライ/サーキット/フォールバック/オブザーバビリティ の相互作用図、設定値チューニング指針、既知の制限事項 | アーキテクチャレビューで承認可能な完成度 |

---

## 実装優先度の目安

| 優先度 | Steps | 理由 |
|:---|:---|:---|
| **P0 (即時)** | 25-32 | 共通基盤と既存クライアント適用で、現状の「リトライなし・即死」を即座に改善 |
| **P1 (1スプリント以内)** | 33-37, 42-44 | ユーザー視点の劣化体験を守る Graceful Degradation とその検証 |
| **P2 (2スプリント以内)** | 1-8, 38-41 | 可視化・観測性・運用ダッシュボードで「見える化」 |
| **P3 (継続)** | 9-24, 45-48 | ドキュメント整備・カオス実験・ランブックで組織的成熟度を高める |

---

## 進め方の Tips (低性能LLM向け)

1. **1ステップ = 1ファイル/1関数** の粒度を守る。複数ファイルまたがる場合はさらに分割する。
2. **テストファースト**: `tests/` 以下のテストを先に書かせ、実装は「テストを通すコード」のみ生成させる。
3. **既存コードの模倣**: `api_client.py` や `engine.py` の既存パターン（型ヒント、ログ出力、エラーハンドリング）をコピペベースで踏襲させる。
4. **設定のハードコード禁止**: 全て `config/*.yaml` → Pydanticモデル → シングルトンアクセス の流れを徹底させる。
5. **差分確認**: 各ステップ完了時に `git diff --stat` で変更行数が「数十〜百行以内」に収まっているか確認。超過なら分割不足。