# LLMゲートウェイ改善 実装計画書

**方針**: 破壊的変更を避け、既存APIを維持しつつ、即効性のある改善を優先。レガシー層は「委譲ラッパー」で段階的移行。

---

## 📋 実装タスク一覧（優先度順）

### Phase 0: 即日完了（破壊的変更なし・リスクゼロ）

| # | タスク | ファイル | 工数 | 確認方法 |
|---|--------|----------|------|----------|
| 0-1 | `llm_gateway.py`の`generate()`スタブ削除 | `src/core/llm_gateway.py:211-214` | 5分 | `grep -r "\.generate(" --include="*.py" src/` で呼び出し元0確認 |
| 0-2 | `model_router.py`の`_DEFAULTS`/`_PURPOSES`削除 | `src/llm/model_router.py:8-21, 51-59` | 15分 | `select_model("writing")`等が`GlobalConfigModel`から正しく解決されること確認 |
| 0-3 | `MODEL_PRICING`に埋め込みモデル価格追加 | `src/config/cost_optimization.py` | 5分 | 価格は公式ドキュメント準拠（`text-embedding-004`: $0.02/1M入力） |

**📝 回帰テスト（Phase 0）**
| # | テストファイル | テストケース | 目的 |
|---|----------------|--------------|------|
| T0-1 | `tests/unit/llm/test_model_router.py` (新規) | `test_select_model_uses_global_config`、`test_resolve_model_for_purpose_fallback` | ルーターが設定から正しくモデル解決すること確認 |
| T0-2 | `tests/unit/config/test_cost_optimization.py` (新規) | `test_model_pricing_includes_embedding` | 埋め込み価格が定義されていること確認 |
| T0-3 | `tests/unit/llm/test_gateway_api.py` (既存拡張) | `test_generate_method_removed` | `generate()`呼出しで`AttributeError`になること確認 |

---

### Phase 1: 高ROI改善（1-3日・破壊的変更なし）

| # | タスク | ファイル | 工数 | 実装詳細 |
|---|--------|----------|------|----------|
| 1-1 | **インフライト重複排除** | `src/core/llm_gateway.py` | 2時間 | `LLMGenerateResultProxy`に`_inflight: dict[str, asyncio.Task]`追加。`generate_text/json`でキー生成→既存タスク待機→新規作成→完了後削除。ストリーミング時はスキップ |
| 1-2 | **埋め込みコスト追跡** | `src/services/semantic_cache.py`<br>`src/config/cost_optimization.py` | 1時間 | ①`cost_optimization.py`に価格追加 ②`SemanticCacheManager.__init__`で`cost_tracker`受取 ③`_get_embedding()`で`track_request()`呼出し |
| 1-3 | **ErrorClassifierユーティリティ作成** | `src/services/llm/error_classifier.py` (新規) | 2時間 | `classify_error(e: Exception) -> ErrorCategory`実装。OpenAI/Gemini/Anthropic/Ollama/vLLMの主要例外を網羅。文字列フォールバック残す |
| 1-4 | **リトライデコレータへErrorClassifier適用** | `src/services/retry_decorator.py` | 1時間 | `except Exception as e:`ブロック内で`category = classify_error(e)`し、カテゴリごとに分岐。既存文字列判定はフォールバックとして残す |

**📝 回帰テスト（Phase 1）**
| # | テストファイル | テストケース | 目的 |
|---|----------------|--------------|------|
| T1-1 | `tests/unit/llm/test_inflight_dedup.py` (新規) | `test_same_prompt_concurrent_single_call`、`test_different_params_separate_calls`、`test_streaming_skips_dedup`、`test_exception_cleans_up_inflight` | 重複排除の正常系・異常系・ストリーミング除外・クリーンアップ確認 |
| T1-2 | `tests/unit/services/test_embedding_cost_tracking.py` (新規) | `test_embedding_call_recorded_in_cost_tracker`、`test_cache_hit_no_embedding_cost`、`test_batch_embedding_cost_allocation` | 埋め込みコスト記録・キャッシュヒット時無課金・バッチ時按分確認 |
| T1-3 | `tests/unit/llm/test_error_classifier.py` (新規) | `test_openai_rate_limit_classified`、`test_gemini_quota_classified`、`test_auth_error_unrecoverable`、`test_unknown_fallback_to_string`、`test_network_timeout_temporary` | 全プロバイダ主要エラー分類・フォールバック動作確認 |
| T1-4 | `tests/unit/services/test_retry_with_classifier.py` (新規/既存拡張) | `test_retry_on_temporary_error`、`test_no_retry_on_unrecoverable`、`test_temp_adjustment_on_validation_error`、`test_model_fallback_on_5xx` | 分類ベースリトライ・温度調整・モデルフォールバック確認 |

---

### Phase 2: 設定・構造整理（1週間・破壊的変更なし）

| # | タスク | ファイル | 工数 | 実装詳細 |
|---|--------|----------|------|----------|
| 2-1 | **CostGuardProtocol定義** | `src/services/cost_guard/protocol.py` (新規) | 2時間 | `track_and_check(model, usage) -> CostCheckResult`、`get_summary(scope) -> CostSummary`等のプロトコル定義 |
| 2-2 | **既存3クラスをProtocol実装化** | `src/services/cost_guard/token_circuit_breaker.py`<br>`src/services/billing/token_budget_tracker.py`<br>`src/services/observability/token_cost_tracker.py` | 3時間 | 各クラスに`implements CostGuardProtocol`追加。既存メソッドを委譲メソッドでラップ |
| 2-3 | **統一CostGuardファサード作成** | `src/services/cost_guard/__init__.py` | 1時間 | `def get_cost_guard() -> CostGuardProtocol:`で設定ベースのインスタンス返却。既存インポート互換維持 |
| 2-4 | **ゲートウェイでCostGuard自動呼出し** | `src/core/llm_gateway.py` | 1時間 | `generate_text/json`完了時に`cost_guard.track_and_check()`呼出し。設定で無効化可能 |

**📝 回帰テスト（Phase 2）**
| # | テストファイル | テストケース | 目的 |
|---|----------------|--------------|------|
| T2-1 | `tests/unit/cost_guard/test_protocol.py` (新規) | `test_protocol_methods_exist`、`test_all_implementations_conform` | プロトコル定義・実装クラス適合確認 |
| T2-2 | `tests/unit/cost_guard/test_circuit_breaker_adapter.py` (新規) | `test_track_and_check_token_limit`、`test_track_and_check_cost_limit`、`test_reset_per_episode` | 既存CircuitBreaker機能がアダプタ経由で動作確認 |
| T2-3 | `tests/unit/cost_guard/test_budget_tracker_adapter.py` (新規) | `test_track_and_check_budget_enforced`、`test_is_within_budget`、`test_configurable_limits` | 既存BudgetTracker機能がアダプタ経由で動作確認 |
| T2-4 | `tests/unit/cost_guard/test_cost_tracker_adapter.py` (新規) | `test_calculate_cost_usd_jpy`、`test_cache_savings_calculation`、`test_track_request_returns_breakdown` | 既存CostTracker機能がアダプタ経由で動作確認 |
| T2-5 | `tests/integration/llm/test_gateway_cost_guard.py` (新規) | `test_generate_auto_tracks_cost`、`test_budget_exceeded_raises`、`test_cost_guard_disabled_via_config` | ゲートウェイ経由の自動コスト追跡・予算超過遮断・無効化確認 |

---

### Phase 3: プロバイダ隔離（2週間・破壊的変更なし・委譲パターン）

| # | タスク | ファイル | 工数 | 実装詳細 |
|---|--------|----------|------|----------|
| 3-1 | **ProviderProtocol定義** | `src/core/llm/providers/protocol.py` (新規) | 1時間 | `generate_json/text`のみの最小インターフェース |
| 3-2 | **Gemini/OpenAI実装を内部クラス化** | `src/core/llm_clients/gemini.py`<br>`src/core/llm_clients/openai.py` | 4時間 | 既存クラスを`_GeminiImpl`/`_OpenAIImpl`にリネーム、公開クラスは`ProviderProtocol`実装の薄いラッパーに |
| 3-3 | **共通ユーティリティ抽出** | `src/core/llm/providers/utils.py` (新規) | 2時間 | `build_generation_config`、`handle_api_error`、`sanitize_output`等を共通化 |
| 3-4 | **ファクトリで新プロバイダ返却** | `src/core/llm_gateway.py` (`LLMProviderFactory`) | 1時間 | `get_client()`が`ProviderProtocol`返却。既存`BaseLLMClient`は互換エイリアスとして残す |

**📝 回帰テスト（Phase 3）**
| # | テストファイル | テストケース | 目的 |
|---|----------------|--------------|------|
| T3-1 | `tests/unit/llm/providers/test_protocol.py` (新規) | `test_provider_protocol_minimal_interface` | プロトコル最小インターフェース確認 |
| T3-2 | `tests/unit/llm/providers/test_gemini_provider.py` (既存拡張/移行) | `test_generate_json_with_schema_fallback`、`test_generate_text_streaming`、`test_nsfw_mode_safety_settings`、`test_schema_mode_fallback_chain` | Gemini固有機能（スキーマフォールバック・ストリーミング・NSFW・モード連鎖）がラッパー経由で動作確認 |
| T3-3 | `tests/unit/llm/providers/test_openai_provider.py` (既存拡張/移行) | `test_generate_json_response_format`、`test_openrouter_model_id`、`test_retry_state_temp_adjustment` | OpenAI固有機能（JSON強制・OpenRouterモデルID・リトライ時温度調整）がラッパー経由で動作確認 |
| T3-4 | `tests/unit/llm/providers/test_utils.py` (新規) | `test_build_generation_config_temperature_decay`、`test_handle_api_error_classification`、`test_sanitize_output_metadata_extraction` | 共通ユーティリティ単体確認 |
| T3-5 | `tests/integration/llm/test_factory_provider_selection.py` (新規) | `test_factory_returns_gemini_for_gemini_models`、`test_factory_returns_openai_for_openrouter`、`test_factory_returns_openai_for_claude`、`test_fallback_to_gemini` | ファクトリのプロバイダ選択ロジック確認 |

---

### Phase 4: レガシーアダプタ層段階的撤廃（4週間・非破壊的移行）

> **方針**: 既存アダプタを`IUnifiedLLMClient`への**委譲ラッパー**化し、呼び出し元を徐々に移行。最終削除は別PR。

| # | タスク | ファイル | 工数 | 実装詳細 |
|---|--------|----------|------|----------|
| 4-1 | **委譲ラッパーベースクラス作成** | `src/services/llm/legacy_wrapper.py` (新規) | 1時間 | `BaseLLMAdapter`継承し、内部で`IUnifiedLLMClient`保持。全メソッドを委譲 |
| 4-2 | **各アダプタをラッパー化** | `src/services/llm/*.py` (6ファイル) | 3時間 | `OpenAIAdapter`等を`LegacyOpenAIAdapter(LegacyWrapperBase)`に。警告ログ付与 |
| 4-3 | **SPI層も同様にラッパー化** | `src/core/spi/llm/*.py` (3ファイル) | 1時間 | 同上 |
| 4-4 | **呼び出し元移行ガイド作成** | `docs/llm_migration_guide.md` (新規) | 1時間 | 移行パターン・モック書き換え例・非同期コンテキスト対処法を文書化 |
| 4-5 | **段階的移行（呼び出し元毎）** | 各呼び出し元ファイル | 継続的 | 1ファイルずつ`IUnifiedLLMClient`直接利用に書き換え。テスト通過確認後コミット |

**📝 回帰テスト（Phase 4）**
| # | テストファイル | テストケース | 目的 |
|---|----------------|--------------|------|
| T4-1 | `tests/unit/llm/legacy/test_wrapper_base.py` (新規) | `test_wrapper_delegates_generate_text`、`test_wrapper_delegates_stream_text`、`test_wrapper_delegates_generate_sync`、`test_deprecation_warning_emitted` | ラッパーベースクラスが全メソッド委譲・警告出力確認 |
| T4-2 | `tests/unit/llm/legacy/test_legacy_adapters.py` (新規) | `test_legacy_openai_adapter_works`、`test_legacy_gemini_adapter_works`、`test_legacy_claude_adapter_works`、`test_legacy_ollama_adapter_works`、`test_legacy_vllm_adapter_works`、`test_legacy_mock_adapter_works` | 6種レガシーアダプタがラッパー経由で動作確認 |
| T4-3 | `tests/unit/llm/legacy/test_spi_adapters.py` (新規) | `test_spi_gemini_adapter_works`、`test_spi_mock_adapter_works` | SPI層アダプタも同様確認 |
| T4-4 | `tests/integration/llm/test_legacy_callers_migrated.py` (新規/継続的追加) | `test_query_reformulator_uses_unified`、`test_pipeline_steps_use_unified`、`test_extraction_service_uses_unified`、`test_prose_refiner_uses_unified`、`test_unified_auditor_uses_unified` | 主要呼び出し元（17ファイル）が新インターフェース移行済み確認。移行完了ごとにテストケース追加 |
| T4-5 | `tests/regression/test_legacy_removal.py` (新規・最終段階) | `test_no_direct_imports_of_legacy_adapters`、`test_no_base_llm_adapter_subclasses_outside_legacy` | レガシー層完全削除前の最終確認（import検知・継承検知） |

---

### Phase 5: オプション（必要に応じて）

| # | タスク | 判断基準 |
|---|--------|----------|
| 5-1 | `LLMPipeline`実装 | Phase 2-3完了後、横断ロジック追加需要が出たら着手 |
| 5-2 | ストリーミング対応ゲートウェイ | リアルタイムUX要件が出たら着手 |
| 5-3 | A/Bテスト対応ルーター | モデル比較実験要件が出たら着手 |

---

## 🛠 実装時の共通ルール

### コーディング規約
```python
# 1. 型ヒント必須（public API）
# 2. 非同期はasync/await統一（同期ラッパー禁止）
# 3. 設定はGlobalConfigModelから取得（ハードコード禁止）
# 4. ログはStructuredLogger使用（trace_id自動付与）
# 5. 例外は独自例外階層（LLMTemporaryError等）でラップ
```

### テスト要件
- 単体テスト: 新規関数・クラスごとに`tests/unit/`配下に作成（**Phaseごとに上記テーブル参照**）
- 統合テスト: ゲートウェイ経由のエンドツーエンド`tests/integration/test_llm_gateway.py` + **各Phaseの統合テスト**
- 回帰テスト: 既存機能破壊検知用`tests/regression/test_llm_gateway_regression.py`（Phase 4最終段階で作成）
- 既存テスト全通過必須（`pytest tests/ -x`）
- **新規テストカバレッジ80%以上**（`pytest --cov=src/core/llm_gateway --cov=src/llm --cov=src/services/llm`等）
- [ ] 既存全テストパス
- [ ] 新機能テストカバレッジ80%以上
- [ ] ベンチマーク: インフライト重複排除で同一プロンプト並行実行時レイテンシ50%以上削減
- [ ] コスト追跡: 埋め込みAPI呼出しが`TokenCostTracker`に記録されること確認

---

## 📦 成果物チェックリスト

### Phase 0 完了時
- [ ] `llm_gateway.py`から`generate()`削除
- [ ] `model_router.py`から`_DEFAULTS`/`_PURPOSES`削除
- [ ] `cost_optimization.py`に埋め込み価格追加
- [ ] **テスト**: `test_select_model_uses_global_config`、`test_resolve_model_for_purpose_fallback`、`test_model_pricing_includes_embedding`、`test_generate_method_removed` 通過

### Phase 1 完了時
- [ ] インフライト重複排除動作確認（同一プロンプト並行→1回のみAPI呼出し）
- [ ] 埋め込みコストが`TokenCostTracker`に記録されること確認
- [ ] `ErrorClassifier`で主要エラーが正しく分類されること確認
- [ ] **テスト**: `test_same_prompt_concurrent_single_call`、`test_embedding_call_recorded_in_cost_tracker`、`test_openai_rate_limit_classified`、`test_retry_on_temporary_error` 等通過

### Phase 2 完了時
- [ ] `CostGuardProtocol`定義済み
- [ ] 既存3クラスがプロトコル実装済み
- [ ] ゲートウェイ経由で自動コスト追跡・予算チェック動作
- [ ] **テスト**: `test_all_implementations_conform`、`test_track_and_check_token_limit`、`test_calculate_cost_usd_jpy`、`test_generate_auto_tracks_cost` 等通過

### Phase 3 完了時
- [ ] `ProviderProtocol`定義済み
- [ ] Gemini/OpenAI実装が内部クラス化済み
- [ ] 新プロバイダ追加手順文書化
- [ ] **テスト**: `test_gemini_schema_fallback_chain`、`test_openai_openrouter_model_id`、`test_factory_returns_openai_for_claude` 等通過

### Phase 4 完了時
- [ ] 全レガシーアダプタが委譲ラッパー化済み
- [ ] 移行ガイド文書化済み
- [ ] 主要呼び出し元（上位5-10ファイル）移行完了
- [ ] **テスト**: `test_legacy_openai_adapter_works`、`test_query_reformulator_uses_unified`、`test_no_direct_imports_of_legacy_adapters` 等通過

---

## ⚠️ リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| インフライトキー衝突（異なるparams同一prompt） | 低 | キーに`temperature`/`system_prompt`/`response_schema`含める |
| 埋め込みコスト二重計上（vector_store側でも生成） | 中 | `SemanticCacheManager`のみで追跡し、vector_store側は追跡しない旨コメント |
| ErrorClassifier漏れ（未知の例外） | 中 | 未分類は`ErrorCategory.UNKNOWN`とし、従来の文字列判定にフォールバック |
| 委譲ラッパーの性能オーバーヘッド | 低 | メソッド呼出し1回分のオーバーヘッドのみ（無視可能） |
| 移行期間中のデュアルメンテ | 中 | ラッパー化後は**レガシーコード変更凍結**、バグ修正は新インターフェース側のみ |

---

## 📅 マイルストーン

| マイルストーン | 目標日 | 成果物 |
|--------------|--------|--------|
| M1: 即効改善完了 | Day 3 | Phase 0-1完了、ベンチマーク取得 |
| M2: コストガード統合 | Day 10 | Phase 2完了、統一インターフェース動作 |
| M3: プロバイダ隔離 | Day 24 | Phase 3完了、新プロバイダ追加デモ |
| M4: レガシー移行開始 | Day 30 | Phase 4-1〜4-3完了、移行ガイド公開 |
| M5: 移行完了（目安） | Day 60+ | Phase 4-5継続的完了、レガシー削除PR作成 |

---

## 🔗 関連ドキュメント

- `src/core/llm_gateway.py` - ゲートウェイ実装
- `src/llm/model_router.py` - モデルルーティング
- `src/services/retry_decorator.py` - リトライロジック
- `src/services/semantic_cache.py` - セマンティックキャッシュ
- `src/services/cost_guard/` - コストガード関連
- `schemas/config.py` - 設定SSOT（`GlobalConfigModel`）

---

**承認**: この計画で着手してよいか確認してください。Phase 0-1から着手可能です。