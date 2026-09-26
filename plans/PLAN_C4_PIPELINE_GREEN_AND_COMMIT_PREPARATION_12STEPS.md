# AutoNovel 実装計画書【C4】
# パイプライン残存エラー解消と v5.2.0 完成形コミット準備（12 Steps）

- **文書ID**: PLAN_C4_PIPELINE_GREEN_AND_COMMIT_PREPARATION_12STEPS
- **作成日**: 2026-09-26
- **対象バージョン**: AutoNovel v5.2.0
- **前提計画書**:
  - [PLAN_C1_RUNTIME_CRASH_AND_GREEN_TESTS_36STEPS.md](./PLAN_C1_RUNTIME_CRASH_AND_GREEN_TESTS_36STEPS.md)（実装完了）
  - [PLAN_C2_FORESHADOWING_INTEGRITY_AND_DI_36STEPS.md](./PLAN_C2_FORESHADOWING_INTEGRITY_AND_DI_36STEPS.md)（実装完了）
  - [PLAN_C3_COMMERCIAL_PLANNING_SSOT_36STEPS.md](./PLAN_C3_COMMERCIAL_PLANNING_SSOT_36STEPS.md)（実装完了）
- **対象読者**: 小型・低性能LLM（7Bクラス等）。**1ステップ＝1ファイル1変更**に分割し、「検証コマンド → 期待結果」まで自己完結で記述。

---

## 1. 目的

C1〜C3 で解消した 12 系統の重要課題に加え、テストスイート完走を阻む最後の残余課題（`fakeredis` 未導入による `tests/unit/pipeline` の 5 エラー）を解消し、計画書の DoD チェックリストおよびコミットを整備して v5.2.0 を完全完成形とする。

| 対象 | 課題 | 対策 |
|:---:|---|---|
| **Pipeline 5件** | `fakeredis` 未導入による ModuleNotFoundError | dev 依存追加 + `pytest.importorskip("fakeredis")` ガード |
| **計画書整合性** | C1 / C2 / C3 の DoD チェックリストが `[ ]` のまま | 実装・テスト通過を反映し `[x]` に同期 |
| **インデックス** | `plans/README.md` のステータスが未反映 | C1 / C2 / C3 を完了ステータスへ更新 |
| **Git 状態** | 成果物が未ステージング | コミット準備の完了確認 |

---

## 2. 全体構成（12ステップ）

```
[Part 1] Step 1- 4  fakeredis 導入とスキップガード（環境非依存化）
[Part 2] Step 5- 6  パイプラインテスト全緑化の確認
[Part 3] Step 7- 9  C1〜C3 計画書 DoD チェックリスト更新
[Part 4] Step10-12  インデックス更新・静的検査・コミット準備
```

---

## Part 1: fakeredis 導入とスキップガード (Step 1-4)

### Step 1: `pyproject.toml` に `fakeredis` を dev 依存として追加する

- **目的**: 開発・CI 環境で `fakeredis` が自動インストールされるようにする。
- **対象ファイル**: `pyproject.toml`
- **変更内容**: `[project.optional-dependencies].dev` 内の `pytest-timeout` の直後に `"fakeredis>=2.20.0",` を追加する。
- **検証コマンド**:
  ```powershell
  Select-String -Path pyproject.toml -Pattern "fakeredis"
  ```
- **期待結果**: 追加した行が出力される。

### Step 2: `.venv` に `fakeredis` をインストールする

- **目的**: ローカル環境でパイプラインテストを実行可能にする。
- **作業内容**: pip でインストールを実行する。
  ```powershell
  .venv\Scripts\python.exe -m pip install "fakeredis>=2.20.0"
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -c "import fakeredis; print('fakeredis ok', fakeredis.__version__)"
  ```
- **期待結果**: `fakeredis ok <version>` が出力される。

### Step 3: `test_prompt_builder.py` に importorskip ガードを追加する

- **目的**: 万が一 `fakeredis` が無い環境でもエラー（FAILED/ERROR）にならず SKIP 扱いにする。
- **対象ファイル**: `tests/unit/pipeline/test_prompt_builder.py`
- **変更内容**: ファイル先頭付近に次を追加する。
  ```python
  import pytest
  pytest.importorskip("fakeredis")
  ```
  既存 fixture 内の `import fakeredis` はそのまま利用する。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/pipeline/test_prompt_builder.py -q
  ```
- **期待結果**: `4 passed`（または fakeredis 未導入時 `4 skipped`）。ERROR 0件。

### Step 4: `test_compression_pipeline_integration.py` に importorskip ガードを追加する

- **目的**: 同上。
- **対象ファイル**: `tests/unit/pipeline/test_compression_pipeline_integration.py`
- **変更内容**: ファイル先頭付近に次を追加する。
  ```python
  import pytest
  pytest.importorskip("fakeredis")
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/pipeline/test_compression_pipeline_integration.py -q
  ```
- **期待結果**: `1 passed`（または `1 skipped`）。ERROR 0件。

---

## Part 2: パイプラインテスト全緑化の確認 (Step 5-6)

### Step 5: `tests/unit/pipeline` 全体を実行しエラー 0 を確認する

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/pipeline -q -p no:randomly
  ```
- **期待結果**: `47 passed, 5 skipped, 0 error, 0 failed`。

### Step 6: C1 回帰テストで pipeline 収集エラー 0 を再確認する

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/pipeline/test_nlp_init.py -q
  ```
- **期待結果**: `passed`。

---

## Part 3: 計画書 DoD チェックリストの同期 (Step 7-9)

### Step 7: PLAN_C1 の DoD チェックリストを更新する

- **対象ファイル**: `plans/PLAN_C1_RUNTIME_CRASH_AND_GREEN_TESTS_36STEPS.md`
- **変更内容**: 「C1 完了判定（DoD）チェックリスト」の全8項目を `[x]` に変更する。
- **検証コマンド**:
  ```powershell
  Select-String -Path plans/PLAN_C1_RUNTIME_CRASH_AND_GREEN_TESTS_36STEPS.md -Pattern "- \[ \]"
  ```
- **期待結果**: ヒット件数 0件。

### Step 8: PLAN_C2 の DoD チェックリストを更新する

- **対象ファイル**: `plans/PLAN_C2_FORESHADOWING_INTEGRITY_AND_DI_36STEPS.md`
- **変更内容**: 「C2 完了判定（DoD）チェックリスト」の全9項目を `[x]` に変更する。
- **検証コマンド**:
  ```powershell
  Select-String -Path plans/PLAN_C2_FORESHADOWING_INTEGRITY_AND_DI_36STEPS.md -Pattern "- \[ \]"
  ```
- **期待結果**: ヒット件数 0件。

### Step 9: PLAN_C3 の DoD チェックリストを更新する

- **対象ファイル**: `plans/PLAN_C3_COMMERCIAL_PLANNING_SSOT_36STEPS.md`
- **変更内容**: 「C3 完了判定（DoD）チェックリスト」の全10項目を `[x]` に変更する。
- **検証コマンド**:
  ```powershell
  Select-String -Path plans/PLAN_C3_COMMERCIAL_PLANNING_SSOT_36STEPS.md -Pattern "- \[ \]"
  ```
- **期待結果**: ヒット件数 0件。

---

## Part 4: インデックス更新・静的検査・コミット準備 (Step 10-12)

### Step 10: `plans/README.md` を更新する

- **対象ファイル**: `plans/README.md`
- **変更内容**:
  1. C1, C2, C3 の表にステータス列を追加または記述し、「✅ 実装・検証完了」と明記する。
  2. PLAN_C4 のエントリを追加する。
- **検証コマンド**:
  ```powershell
  Select-String -Path plans/README.md -Pattern "PLAN_C4"
  ```
- **期待結果**: PLAN_C4 の行が出力される。

### Step 11: 変更ファイル全体の Ruff チェックを実行する

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check tests/unit/pipeline/test_prompt_builder.py tests/unit/pipeline/test_compression_pipeline_integration.py
  ```
- **期待結果**: `All checks passed!`。

### Step 12: Git コミット準備状況を確認する

- **検証コマンド**:
  ```powershell
  git status --short
  ```
- **期待結果**: C1〜C4 の関連ファイルが漏れなくリストアップされていることを確認。
