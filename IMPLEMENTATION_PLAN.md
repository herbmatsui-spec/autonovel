# 詳細実装計画書: コアサービスのユニットテスト追加

## 目的
カバレッジ0%の大型サービスに集中してテストを書く。以下の優先順位で実装：
1. src/services/vector_store.py (1,396行) - 最高優先度 - RAG 中核
2. src/services/writing_services.py (970行) - 最高優先度 - 小説生成中核
3. src/services/rag_service.py (675行) - 高優先度 - 検索機能
4. src/services/redis_cache.py (767行) - 高優先度 - キャッシュ層
5. src/services/book_score_service.py (916行) - 高優先度 - スコアリング
6. src/backend/sanitizer.py (879行) - 高優先度 - コンテンツ安全性
7. src/shared/* (circuit_breaker, retry_policy, resilient_http, result) 約200行計 - 中優先度 - 共通ユーティリティ

## アプローチ
- 各サービスは単体でテスト可能に設計
- hypothesis によるプロパティベーステストでバリデータ/シリアライザを検証
- エラーパス、境界値、契約遵守を網羅
- 低性能なLLMでも実装可能なように、それぞれのモジュールを小さなステップに分割

## 詳細な24ステップ実装計画

### ステップ 1-5: src/services/vector_store.py (1,396行) - RAG 中核

**ステップ 1: テストファイル作成と ChromaClientProvider 初期化テスト**
- `tests/unit/test_vector_store.py` を作成
- ChromaClientProvider クラスの `__init__` メソッドをテスト
- デフォルトパス、カスタムパス、ホスト/ポート指定のテスト
- HAS_CHROMA フラグのモックテスト

**ステップ 2: ChromaClientProvider.get_client() テスト**
- 正常なクライアント取得のテスト（PersistentClient と HttpClient）
- 接続失敗時のリトライロジックテスト
- HAS_CHROMA=False の場合の挙動テスト
- close メソッドのテスト

**ステップ 3: ChromaVectorStore 初期化とコレクション管理テスト**
- ChromaVectorStore クラスの `__init__` メソッドテスト
- client プロパティテスト
- initialize_collections メソッドテスト
- _ensure_collection メソッドのテスト（既存コレクション確認・作成）
- get_collection, get_collection_config メソッドテスト

**ステップ 4: ChromaVectorStore ドキュメント操作テスト**
- add_documents メソッドのテスト（チャンク分割処理含む）
- search メソッドのテスト（ベクトル類似度検索）
- search_with_score メソッドのテスト（スコア閾値付き検索）
- delete_by_id, clear_collection メソッドテスト

**ステップ 5: ChromaVectorStore 高度機能とエラーハンドリングテスト**
- get_collection_stats, list_collections, audit_collection_coverage テスト
- _build_bm25_index, add_documents_with_bm25 テスト
- hybrid_search, rebuild_bm25_index メソッドテスト
- PgVectorStore と InMemoryFallbackStore の基本テスト
- エッジケースとエラーハンドリングのテスト

### ステップ 6-10: src/services/writing_services.py (970行) - 小説生成中核

**ステップ 6: WritingGenerationContext テスト**
- デフォルト値のテスト
- build_sys_inst メソッドのテスト（各フィールドの組み合わせ）
- build_fw_prompt メソッドのテスト（各フィールドの組み合わせ）
- ファクトリーメソッドとしての振る舞いテスト

**ステップ 7: GenerationLoopManager 初期化とヘルパーメソッドテスト**
- コンストラクタと依存注入のテスト
- _determine_pov_instruction メソッドテスト（高緊張、カタルシス、通常エピソード）
- _calculate_ncs_score メソッドテスト（最初の話、最後の話、キーワードトリガー）
- _expand_scene_beats メソッドテスト（正常ケースとフォールバック）

**ステップ 8: GenerationLoopManager フェーズメソッドテスト**
- _phase_prepare_context メソッドテスト（文脈準備、フラグ設定）
- _phase_drafting メソッドテスト（前半/後半分割執筆、ポリッシング制御）
- _extract_episode_metadata メソッドテスト（メタデータ抽出成功・失敗ケース）

**ステップ 9: GenerationLoopManager 監査と修復メソッドテスト**
- _phase_audit メソッドテスト（整合性チェック、因果律監査）
- _run_causality_audits メソッドテスト（成功ケースと失敗ケース）
- _apply_surgical_healing メソッドテスト（修復成功・失敗ケース）
- _surgical_causality_healing_pass メソッドテスト（スニペット置換・非置換ケース）

**ステップ 10: GenerationLoopManager ループと遅延パッチテスト**
- _phase_critic メソッドテスト（Criticフィードバック生成・リライトトリガー）
- _run_dogfeeding_loop メソッドテスト（自己評価ループ、スコアに基づく再生成）
- _register_lazy_patch メソッドテスト（遅延パッチ作成・バイブル更新）
- 統合テスト：エージェントループ全体の流れテスト

### ステップ 11-14: src/services/rag_service.py (675行) - 検索機能

**ステップ 11: GraphRAGService 初期化と基本機能テスト**
- コンストラクタと依存注入のテスト
- get_reranker, get_last_stats メソッドテスト
- _get_cache_key, _get_cached, _set_cache メソッドテスト
- clear_cache メソッドテスト

**ステップ 12: 検索メソッドテスト**
- search_similar_chunks メソッドテスト（pgvectorバックエンド、SQLiteフォールバック、エラーケース）
- search_vectors_async メソッドテスト
- _cosine_similarity, _estimate_tokens, _truncate_to_budget メソッドテスト

**ステップ 13: ハイブリッド検索と結果融合テスト**
- hybrid_search メソッドテスト（重み正規化、RRF融合）
- _search_graph メソッドテスト（グラフ探索とセマンティック再ランキング）
- _search_fulltext メソッドテスト（PostgreSQL全文検索）
- _fuse_results メソッドテスト（RRFによる結果融合）
- rerank_graph_neighbors, rerank_with_cross_encoder メソッドテスト

**ステップ 14: RAGコンテキスト構築とキャッシュテスト**
- build_rag_context メソッドテスト（エンティティ特定、グラフ探索、ハイブリッド検索、トークン予算調整）
- get_community_context, retrieve_for_episode メソッドテスト
- キャッシュヒット/ミスのテスト（L1/L2/L3レイヤー）
- キャッシュTTLと無効化のテスト

### ステップ 15-17: src/services/redis_cache.py (767行) - キャッシュ層

**ステップ 15: RedisCacheService 基本操作テスト**
- コンストラクタと初期化のテスト（REDIS_AVAILABLE フラグのモック含む）
- _make_key, _serialize, _deserialize メソッドテスト
- get, set, delete, exists, expire, get_ttl メソッドテスト
- ヘルスチェックと接続クローズのテスト

**ステップ 16: RedisCacheService 高度操作テスト**
- mget, mset メソッドテスト（パイプライン使用）
- invalidate_pattern, invalidate_namespace メソッドテスト（SCAN+DEL使用）
- PromptCacheService の基本構造テスト（コンストラクタとメトリクス初期化）

**ステップ 17: PromptCacheService 層キャッシュとウォーミングテスト**
- _generate_cache_key, compute_prompt_hash メソッドテスト
- _get_ttl メソッドテスト（タスクタイプ別TTLポリシー）
- 3層キャッシュ(L1/L2/L3)の get/set メソッドテスト
- キャッシュ統計、ウォーミング、プリフェッチ機能テスト
- 特定無効化機能（invalidate_book, invalidate_template, invalidate_task_type）

### ステップ 18-20: src/services/book_score_service.py (916行) - スコアリング

**ステップ 18: BookScoreCalculator 初期化と重み計算テスト**
- コンストラクタと設定ファイル読み込みのテスト
- _get_weights メソッドテスト（デフォルト重み、ジャンルオーバーライド、フェーズオーバーライド）
- BookScore データクラスと BookScoreRepository プロトコルテスト

**ステップ 19: スコア計算メソッドテスト**
- calculate メソッドテスト（全体スコアと各次元スコアの計算）
- _score_structure, _score_coherency, _score_factual メソッドテスト
- _score_visual_textual, _score_reader_experience メソッドテスト
- 各スコアメソッドのエラーハンドリングとデフォルト値テスト
- save_score, get_latest_score メソッドテスト

**ステップ 20: トレンド分析とPDCAレポートテスト**
- _fetch_plot, _fetch_chapter, _fetch_illustration, _fetch_bible, _fetch_audit_report ヘルパーメソッドテスト
- _build_text_stats メソッドテスト
- analyze_trend メソッドテスト（線形回帰、移動平均、変化点検出、予測）
- generate_pdca_report メソッドテスト（Plan-Do-Check-Actサイクル）
- _get_anachronisms ヘルパーメソッドテスト

### ステップ 21-22: src/backend/sanitizer.py (879行) - コンテンツ安全性

**ステップ 21: OutputSanitizer と NormalizationFlow コアテスト**
- OutputSanitizer.parse_llm_json メソッドテスト（ラッピングテキスト、空文字列、無効JSON）
- OutputSanitizer.extract_content_and_metadata メソッドテスト（セパレーター形式、JSON末尾抽出、プレーンテキストフォールバック）
- OutputSanitizer._clean_story メソッドテスト（メタパターン除去、マークdown除去、区切り線除去）
- OutputSanitizer.normalize_metadata, fix_json, format_validation_error メソッドテスト
- NormalizationFlow クラスの各メソッドテスト（unwrap_nested_metadata, resolve_aliases, coerce_types, normalize_lists, apply_defaults, normalize_metadata）

**ステップ 22: テキスト品質とフォーマッティングテスト**
- ContentValidator クラスのテスト（check_rhythm, check_catharsis_reservation, auto_correct_rhythm, analyze_word_heaviness）
- TonePerfector クラスのテスト（enforce_tone メソッド）
- SeriousnessFilter クラスのテスト（filter メソッド）
- TextFormatter クラスのテスト（remove_ai_isms, enforce_cliffhanger, format_for_kakuyomu メソッド）
- AtmosphereGenerator クラスのテスト（get_prompt, get_sensory_anchors メソッド）

### ステップ 23-24: src/shared/* (~200行計) - 共通ユーティリティと最終検証

**ステップ 23: 共有モジュールのコア機能テスト**
- circuit_breaker.py: CircuitBreaker クラスの状態遷移テスト（CLOSED→OPEN→HALF_OPEN→CLOSED）
- retry_policy.py: RetryPolicy クラスの遅延計算テスト（指数バックオフ、ジッター、最大遅延キャップ）
- resilient_http.py: ResilientHttpClient クラスのテスト（成功ケース、リトライ後成功、サーキットブレーカーOPEN時ブロック）
- result.py: Result 型のテスト（is_ok/is_errプロパティ、unwrap/map/map_errメソッド、エラー型パラメータ）

**ステップ 24: 最終検証とテストスイート実行**
- すべての新規テストファイルが正しくインポートできるかテスト
- 各テストモジュールを個別に実行してパスするか確認
- 関連する既存テストが壊れていないか回帰テスト
- hypothesis を使用したプロパティベーステストの実装確認（バリデータ/シリアライザ対象）
- カバレッジレポート生成と目標達成確認

## 実装ガイドライン

### テスト作成の原則
1. 各テストは独立して実行可能であること
2. 外部依存は可能な限りモックまたはスタブを使用すること
3. テスト名は「what_being_tested_under_what_conditions」形式とすること
4. 1つのテストアサーションにつき1つの概念をテストすること
5. エラーケースと境界値を必ずテストすること

### モックとスタブの使用
- 外部サービス（データベース、API、ファイルシステム等）はすべてモックする
- unittest.mock の MagicMock, AsyncMock, patch を積極的に使用する
- データクラスやプロトコルについては、必要に応じて簡易実装のスタブを作成する
- 非同期メソッドは AsyncMock を使用してテストする

### プロパティベーステスト (hypothesis)
- バリデータとシリアライザに対して hypothesis を使用すること
- 入力の不変性（サニタイズ後の特性保持）をテストすること
- 境界値と異常系の自動生成を活用すること
- 例外が発生すべきケースと発生してはいけないケースを両方テストすること

### カバレッジ測定
- 各モジュールについて、行カバレッジ 80% 以上を目標とする
- 複雑なロジック（条件分岐、ループ）については、分岐カバレッジも考慮すること
- 未テストのパブリックメソッドがないことを確認すること

## 依存関係とセットアップ

### 必要なパッケージ
- pytest: テストフレームワーク
- unittest.mock: モッキング（Python標準ライブラリ）
- hypothesis: プロパティベーステスト
- pydantic: データバリデーション（既にプロジェクトに含まれている）
- pytest-asyncio: 非同期テストサポート

### テスト実行方法
```bash
# 個別テストファイルの実行
pytest tests/unit/test_vector_store.py -v

# すべての新規テストの実行
pytest tests/unit/test_*store.py tests/unit/test_writing_services.py tests/unit/test_rag_service.py tests/unit/test_redis_cache.py tests/unit/test_book_score_service.py tests/unit/test_sanitizer.py tests/unit/test_shared.py -v

# カバレッジ測定
pytest --cov=src/services --cov=src/backend --cov=src/shared tests/unit/
```

## 期待される成果

1. **vector_store.py**: 行カバレッジ 0% → 85% 以上
2. **writing_services.py**: 行カバレッジ 約40% → 85% 以上
3. **rag_service.py**: 行カバレッジ 約7% → 85% 以上
4. **redis_cache.py**: 行カバレッジ 約50% → 85% 以上
5. **book_score_service.py**: 行カバレッジ 約16% → 85% 以上
6. **sanitizer.py**: 行カバレッジ 約60% → 85% 以上
7. **shared modules**: 行カバレッジ 変動 → 80% 以上

全体として、対象とする大型モジュolesの平均カバレッジを大幅に向上させ、特に0%だった vector_store.py と 結果モジュールresult.py を確実にテスト対象とする。