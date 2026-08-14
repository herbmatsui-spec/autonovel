=== �������� �������� ������� ������ ������ ����� ������ ������ ����� ���� ���� ��循環依存 (after Step 20) ===
madge未導入 (インストール失敗のためスキップ)

=== 最大ファイル行数 ===
    972 src/services/writing_services.py
   1142 src/models/plot.py
   1173 src/easy_mode/phase3/if_routes.py
   2770 src/agents/erotic_integrity.py
  49745 total

=== Any 使用�������������������������������箇所数 ===
1201

=== mypy エラー数 ===
src/services/novel_producer.py:137: error: Item "None" of "NovelProject | None" has no attribute "target_episodes"  [union-attr]
src/services/novel_producer.py:138: error: Item "None" of "NovelProject | None" has no attribute "target_word_count_per_episode"  [union-attr]
src/backend/routers/commercial.py:39: error: Missing positional argument "self" in call to "run" of "CommercialPipeline"  [call-arg]
src/backend/routers/commercial.py:44: error: Value of type "int" is not indexable  [index]
Found 662 errors in 128 files (checked 348 source files)

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
tests/test_phase2_pipeline_integration.py ...................