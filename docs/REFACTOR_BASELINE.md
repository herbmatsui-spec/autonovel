=== �循環依存 ===
madge未導入

=== 最大ファイル行数 ===
    972 src/services/writing_services.py
   1142 src/models/plot.py
   1173 src/easy_mode/phase3/if_routes.py
   2770 src/agents/erotic_integrity.py
  49387 total

=== Any 使用�箇所数 ===
1140

=== mypy エラー数 ===
src/backend/workflows/full_auto_workflow.py:130: error: "StatusReporter" has no attribute "state"  [attr-defined]
src/backend/workflows/full_auto_workflow.py:150: error: Item "None" of "DataRepositoryFacade | None" has no attribute "get_book"  [union-attr]
src/backend/health/checks.py:107: error: Missing positional argument "cooldown" in call to "LLMProviderFactory"  [call-arg]
src/backend/health/checks.py:109: error: "LLMProviderFactory" has no attribute "generate_text"  [attr-defined]
Found 663 errors in 127 files (checked 345 source files)

=== テスト結果 ===
tests/test_minimal.py .                                                  [ 52%]
tests/test_narrative_engineering.py F                                    [ 52%]
tests/test_ncs_calibration.py .....                                      [ 53%]
tests/test_novel_producer.py ..........                                  [ 54%]
tests/test_outbox_worker.py F                                            [ 54%]
tests/test_parse_character_registry.py ......                            [ 55%]
tests/test_patch_validator.py ......                                     [ 55%]
tests/test_phase1_preset_integration.py .................                [ 57%]
tests/test_phase1to3_e2e.py ....                                         [ 58%]
tests/test_phase2_pipeline_integration.py ...................Step 3: Test baseline verified. See docs/REFACTOR_BASELINE.md for test results.
