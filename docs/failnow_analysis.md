# FailNow Analysis

## 分類
- [x] エロティックパイプライン
- [x] DB周り
- [x] Stripe Webhook
- [x] 認証ミドルウェア
- [x] 廃止機能
- [x] その他

## 各項目の詳細
### エロティックパイプライン
- テスト名: 
  - tests/unit/agents/test_erotic_pipeline.py::TestEroticCurve::test_curve_creation
  - tests/unit/agents/test_erotic_pipeline.py::TestEroticCurve::test_add_point
  - tests/unit/agents/test_erotic_pipeline.py::TestEroticCurve::test_get_phase_intensity
  - tests/unit/agents/test_erotic_pipeline.py::TestEroticCurve::test_curve_validation_u_shape
  - tests/unit/agents/test_erotic_pipeline.py::TestCharacterStateSnapshot::test_snapshot_creation
  - tests/unit/agents/test_erotic_pipeline.py::TestCharacterStateSnapshot::test_snapshot_defaults
  - tests/unit/agents/test_erotic_pipeline.py::TestContinuityTracker::test_update_and_get_character_state
  - tests/unit/agents/test_erotic_pipeline.py::TestContinuityTracker::test_get_nonexistent_character
  - tests/unit/agents/test_erotic_pipeline.py::TestContinuityTracker::test_stamina_transition_validation
  - tests/unit/agents/test_erotic_pipeline.py::TestContinuityTracker::test_psychological_transition_validation
  - tests/unit/agents/test_erotic_pipeline.py::TestContinuityTracker::test_invalid_stamina_transition
  - tests/unit/agents/test_erotic_pipeline.py::TestContinuityTracker::test_invalid_psychological_transition
  - tests/unit/agents/test_erotic_pipeline.py::TestContinuityTracker::test_intimacy_progression
  - tests/unit/agents/test_erotic_pipeline.py::TestContinuityTracker::test_location_transition
  - tests/unit/agents/test_erotic_pipeline.py::TestContinuityTracker::test_items_held_tracking
  - tests/unit/agents/test_erotic_pipeline.py::TestContinuityTracker::test_body_marks_tracking
  - tests/unit/agents/test_erotic_pipeline.py::TestContinuityReport::test_report_creation
  - tests/unit/agents/test_erotic_pipeline.py::TestContinuityReport::test_report_with_issues
  - tests/unit/agents/test_erotic_pipeline.py::TestEroticIntegrityChecker::test_check_coercive_context_coercion
  - tests/unit/agents/test_erotic_pipeline.py::TestEroticIntegrityChecker::test_full_integrity_check_pass
  - tests/unit/agents/test_erotic_pipeline.py::TestEroticPipelineIntegration::test_pipeline_with_explicit_consent
  - tests/unit/agents/test_erotic_pipeline.py::TestEroticPipelineIntegration::test_pipeline_rejects_coercive_content
  - tests/unit/agents/test_erotic_pipeline.py::TestEroticPipelineIntegration::test_continuity_across_episodes
- 失敗理由: 未調査（推定: 環境依存、モック不足、実装バグ等）
- 推定工数: 未調査
- 依存関係: 未調査

### DB周り
- テスト名:
  - tests/unit/test_repository_concurrency.py::test_repository_get_set_state_async
  - tests/unit/test_sqlite_rag_embedding.py::test_sqlite_rag_batch_vector_search_and_no_truncation
  - tests/unit/test_sqlite_rag_embedding.py::test_backfill_missing_embeddings
  - tests/unit/test_uow_repositories.py::test_uow_all_repositories_instantiate_without_name_error
  - tests/unit/test_uow_repositories.py::test_uow_cleanup_clears_repo_cache
  - tests/unit/test_p4_async_and_db_concurrency.py::TestTasksRouterAsyncRedis::test_get_task_status_uses_async_redis
  - tests/unit/test_multimedia_real_db.py::test_empty_book_router_returns_422
- 失敗理由: 未調査
- 推定工数: 未調査
- 依存関係: 未調査

### Stripe Webhook
- テスト名: tests/unit/services/test_stripe_payment.py::test_stripe_webhook_grants_credits
- 失敗理由: 未調査（典型的な問題: await 漏れ）
- 推定工数: 未調査
- 依存関係: 未調査

### 認証ミドルウェア
- テスト名: （fail_now.txt に認証ミドルウェア関連のテストが見つからないため、空）
  注意: fail_now.txt に認証ミドルウェアのテストが含まれていない可能性があります。しかし、計画には含まれているため、調査が必要です。
- 失敗理由: 未調査
- 推定工数: 未調査
- 依存関係: 未調査

### 廃止機能
- テスト名: （fail_now.txt に廃止機能関連のテストが見つからないため、空）
  注意: fail_now.txt に廃止機能のテストが含まれていない可能性があります。しかし、計画には含まれているため、調査が必要です。
- 失敗理由: 未調査
- 推定工数: 未調査
- 依存関係: 未調査

### その他
- テスト名:
  - tests/unit/marketing/test_marketing_ctr_router.py::test_generate_viral_titles_endpoint
  - tests/unit/services/test_editor_autosave.py::test_writing_manager_saves_checkpoint
  - tests/unit/test_closed_loop_pdca.py::test_pdca_cycle_convergence_and_improvement
  - tests/unit/test_enrichment_phase4_step55_60.py::test_step56_llm_sensory_generation_call
  - tests/unit/test_marketing_agent.py::test_post_export_package_endpoint
  - tests/unit/test_multimedia_tasks.py::test_generate_asset_pack_task_runs_sync
  - tests/unit/test_narrative_spine_enforcement.py::test_narrative_spine_composer
  - tests/unit/test_orchestrator_skills.py::test_build_execution_order_circular
  - tests/unit/test_pipeline_websocket.py::test_pipeline_websocket_and_hub
  - tests/unit/test_pipeline_websocket.py::test_sse_pipeline_stream
  - tests/unit/test_reader_hook_windowing.py::test_reader_hook_auditor_windowing_long_draft
  - tests/unit/test_regeneration_directive_integration.py::test_adapter_to_agent_result_injects_actionable_diffs
  - tests/unit/test_voicevox_pipeline.py::test_speaker_mapper
  - tests/unit/workflows/test_writing_graph_flow.py::test_writing_graph_complete_flow
- 失敗理由: 未調査
- 推定工数: 未調査
- 依存関係: 未調査