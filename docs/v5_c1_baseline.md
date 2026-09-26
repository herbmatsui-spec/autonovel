# AutoNovel v5.2.0 - C1 Baseline Record
- 採取日時: 2026-09-26 11:20 JST
- 基準コミット: `ec728cdc`

## Step 1: テスト収集・実行ベースライン

### 1. 全体収集 (`pytest tests --collect-only -q`)
```
5564 tests collected, 14 errors in 24.94s
```

### 2. 単体テスト実行 (`pytest tests/unit -q -p no:randomly`)
```
ERROR tests/unit/pipeline/test_character_extractor.py
ERROR tests/unit/pipeline/test_emotional_residue_extractor.py
ERROR tests/unit/pipeline/test_emotional_residue_integration.py
ERROR tests/unit/pipeline/test_nlp_init.py
ERROR tests/unit/pipeline/test_signal_extractor.py
!!!!!!!!!!!!!!!!!!! Interrupted: 5 errors during collection !!!!!!!!!!!!!!!!!!!
11 warnings, 5 errors in 16.13s
```

### 3. 要約
- 全体収集エラー数: 14件（pipeline 5件、その他環境依存 9件）
- tests/unit 収集エラー数: 5件（pipeline 配下の spacy 欠落）
- 完走状況: 収集段階で Interrupted（テスト実行まで到達せず）
- 所要時間: 収集 24.94s / unit 16.13s
