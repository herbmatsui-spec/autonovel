# P3: 既存のLintエラー修正実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.3（`e:/hhh`）  
**策定日**: 2026-09-16  
**目的**:
1. Ruff ランターで検出された既存のエラー（約900件）を体系的に修正し、CI グリーン化を達成する。
2. 各ステップは1〜2ファイルまたはエラータイプに焦点を当て、低負荷LLMでも容易に実装できるように極小分割する。
3. 修正後は該当ファイルまたはエラータイプに関する検証コマンドで`OK`またはエラー0を確認する。

---

## 📋 全12ステップ 実装マトリクス

| Step | 分類 | 対象 | 主な作業内容 | 検証コマンド |
|:---:|:---|:---|:---|:---|
| **Step 1** | G004 f-string ログ変換 | 複数ファイル | ロガーの f-string を `%` 形式に変換（例: `logger.warning(f"...")` → `logger.warning("...")`） | `py -m ruff check --select G004 src tests \| wc -l` |
| **Step 2** | F401 未使用インポート削除 | 複数ファイル | 未使用のインポート文を削除（`import pytest` など） | `py -m ruff check --select F401 src tests \| wc -l` |
| **Step 3** | E402 モジュールレベルインポート移動 | 複数ファイル | 関数内や条件ブロック内のインポートをファイル先頭に移動 | `py -m ruff check --select E402 src tests \| wc -l` |
| **Step 4** | W293 空白行の空白削除 | 複数ファイル | 空白行に含まれるスペースやタブを削除 | `py -m ruff check --select W293 src tests \| wc -l` |
| **Step 5** | W292 ファイル末尾改行追加 | 複数ファイル | ファイル末尾に改行がないものに改行を追加 | `py -m ruff check --select W292 src tests \| wc -l` |
| **Step 6** | E712 真偽値比較修正 | 複数ファイル | `== True`/`== False` を `is_xxx` または `not` に置換 | `py -m ruff check --select E712 src tests \| wc -l` |
| **Step 7** | E741 あいまい変数名 `l` 変更 | 複数ファイル | 1文字変数 `l` を意味のある名前にリネーム | `py -m ruff check --select E741 src tests \| wc -l` |
| **Step 8** | F821 未定義名修正 | 複数ファイル | 未定義変数（`chadb_host` など）を適切に定義または削除 | `py -m ruff check --select F821 src tests \| wc -l` |
| **Step 9** | F811 重複フィクスチャ削除 | テストファイル | 同名のフィクスチャが重複して定義されているものを片方削除 | `py -m ruff check --select F811 src tests \| wc -l` |
| **Step 10** | その他微修正 (E302, etc.) | 複数ファイル | 行末セミコロン削除、インデント修正など雑多なエラーを修正 | `py -m ruff check --select E302,E902,F841 src tests \| wc -l` |
| **Step 11** | 自動修復実行 | 全リポジトリ | `ruff --fix --unsafe-fixes` で自動修復可能なものを一括適用 | `py -m ruff check --fix --unsafe-fixes src tests` |
| **Step 12** | 最終検証 | 全リポジトリ | すべてのlintエラーが0であることを確認 | `py -m ruff check src tests` |

---

## 🛠 各ステップ詳細仕様

### Step 1: G004 f-string ログ変換
- **目的**: `logger.warning(f"...")` などの f-string ログを遅延評価の `%` 形式に変換し、パフォーマンスとベストプラクティスに準拠する。
- **対象ファイル**: 多数（`src/services/*.py`, `tests/*.py` 等、ルフ出力参照）
- **修正内容例**:
  ```python
  # 変更前
  logger.warning(f"Redis クリーンアップ中にエラーが発生しました: {e}")
  # 変更後
  logger.warning("Redis クリーンアップ中にエラーが発生しました: %s", e)
  ```
- **実行コマンド**（一例）:
  ```powershell
  # 特定ファイルに対して手動修正またはスクリプト実行
  # ここでは代表例として 1 ファイルを示す
  (Get-Content src/services/redis_cache.py) -replace 'logger\.warning\(f"([^"]*)\{(.+?)\}"\)', 'logger.warning("\1%s", \2)' | Set-Content src/services/redis_cache.py
  ```
- **検証コマンド**:
  ```powershell
  py -m ruff check --select G004 src tests; [ERRORCOUNT=$(py -m ruff check --select G004 src tests 2>&1 | grep -c "^"); echo "残り G004 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 検証コマンドの出力で「残り G004 エラー: 0」となること。

### Step 2: F401 未使用インポート削除
- **目的**: 使用されていない `import pytest`, `from typing import Any` などのインポートを削除し、インポートクリーンアップを行う。
- **対象ファイル**: 多数（`tests/**/*.py`, `src/**/*.py`）
- **修正内容例**:
  ```python
  # 変更前
  import pytest
  from typing import Any
  # 変更後（削除）
  ```
- **実行コマンド**（一例）:
  ```powershell
  # 1 ファイル例
  (Get-Content tests/unit/application/test_writing_use_cases_complete.py) -where { $_ -notmatch '^\s*from src\.application\.dtos\.episode_dto\s+import\s+WriteEpisodeDTO' } | Set-Content tests/unit/application/test_writing_use_cases_complete.py
  ```
- **検証コマンド**:
  ```powershell
  py -m ruff check --select F401 src tests; [ERRORCOUNT=$(py -m ruff check --select F401 src tests 2>&1 | grep -c "^"); echo "残り F401 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 検証コマンドの出出力で「残り F401 エラー: 0」となること。

### Step 3: E402 モジュールレベルインポート移動
- **目的**: 関数内や条件ブロック内にあるインポートをファイルの先頭に移動し、静的解析の正確性を向上させる。
- **対象ファイル**: 多数（`src/services/writing_services.py`, `tests/conftest.py` 等）
- **修正内容例**：
  ```python
  # 変更前（関数内）
  def some_func():
      except ImportError:
          from src.config.project_context import ProjectContext  # type: ignore
  # 変更後（ファイル先頭に移動し、必要なら TYPE_CHECKING ブロック内に）
  from __future__ import annotations
  if TYPE_CHECKING:
      from src.config.project_context import ProjectContext
  ```
- **実行コマンド**（代表的なファイルに対して手動修正）。
- **検証コマンド**:
  ```powershell
  py -m ruff check --select E402 src tests; [ERRORCOUNT=$(py -m ruff check --select E402 src tests 2>&1 | grep -c "^"); echo "残り E402 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 検証コマンドの出出力で「残り E402 エラー: 0」となること。

### Step 4: W293 空白行の空白削除
- **目的**: 空白行にスペースやタブが混入しているのを削除し、無意味な変更を防ぐ。
- **対象ファイル**: 多数（`tests/**/*.py`）
- **修正内容**: 空白行を完全に空にする（`""` に置換）。
- **実行コマンド例**：
  ```powershell
  Get-ChildItem -Recurse -Include *.py | ForEach-Object {
      (Get-Content $_.FullName) -replace '^\s+$', '' | Set-Content $_.FullName
  }
  ```
- **検証コマンド**:
  ```powershell
  py -m ruff check --select W293 src tests; [ERRORCOUNT=$(py -m ruff check --select W293 src tests 2>&1 | grep -c "^"); echo "残り W293 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 検証コマンドの出出力で「残り W293 エラー: 0」となること。

### Step 5: W292 ファイル末尾改行追加
- **目的**: ファイル末尾に改行がないと diff がノイジーになるため、改行を追加する。
- **対象ファイル**: 多数
- **修正内容**: ファイル末尾に `\n` を追加。
- **実行コマンド例**：
  ```powershell
  Get-ChildItem -Recurse -Include *.py | ForEach-Object {
      $content = Get-Content $_.FullName -Raw
      if (-not $content.EndsWith("`n")) { $content += "`n"; Set-Content -Path $_.FullName -Value $content -NoNewline }
  }
  ```
- **検証コマンド**:
  ```powershell
  py -m ruff check --select W292 src tests; [ERRORCOUNT=$(py -m ruff check --select W292 src tests 2>&1 | grep -c "^"); echo "残り W292 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 検証コマンドの出出力で「残り W292 エラー: 0」となること。

### Step 6: E712 真偽値比較修正
- **目的**: `== True` や `== False` は Pythonic でないため、`is_xxx` または `not` に置換する。
- **対象ファイル**: 多数（テストファイルが中心）
- **修正内容例**：
  ```python
  # 変更前
  assert result["is_ok"] == True
  # 変更後
  assert result["is_ok"]
  # または
  assert result["is_ok"] == False  →  assert not result["is_ok"]
  ```
- **実行コマンド例**（手動またはスクリプト）。
- **検証コマンド**:
  ```powershell
  py -m ruff check --select E712 src tests; [ERRORCOUNT=$(py -m ruff check --select E712 src tests 2>&1 | grep -c "^"); echo "残り E712 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 検証コマンドの出出力で「残り E712 エラー: 0」となること。

### Step 7: E741 あいまい変数名 `l` 変更
- **目的**: 1文字変数 `l` は意味がわかりにくいため、`line` や `char` など適切な名前にリネームする。
- **対象ファイル**: テストファイルが中心（`tests/unit/test_blind_review_purifier.py` 等）
- **修正内容例**：
  ```python
  # 変更前
  dialogue_lines = [l for l in lines if l.is_dialogue]
  # 変更後
  dialogue_lines = [line for line in lines if line.is_dialogue]
  ```
- **実行コマンド例**。
- **検証コマンド**:
  ```powershell
  py -m ruff check --select E741 src tests; [ERRORCOUNT=$(py -m ruff check --select E741 src tests 2>&1 | grep -c "^"); echo "残り E741 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 検証コマンドの出出力で「残り E741 エラー: 0」となること。

### Step 8: F821 未定義名修正
- **目的**: `chadb_host`, `chadb_port` など、未定義の変数を参照しているエラーを修正する。多くはテスト用フィクスチャやコンテキストの問題。
- **対象ファイル**: 主に `tests/integration/**/*.py`
- **修正内容例**：
  - 未定義変数を適切に定義（フィクスチャから取得するなど）。
  - または使用箇所を削除。
- **実行コマンド例**（代表的なファイルを修正）。
- **検証コマンド**:
  ```powershell
  py -m ruff check --select F821 src tests; [ERRORCOUNT=$(py -m ruff check --select F821 src tests 2>&1 | grep -c "^"); echo "残り F821 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 検証コマンドの出出力で「残り F821 エラー: 0」となること。

### Step 9: F811 重複フィクスチャ削除
- **目的**: 同名の `pytest.fixture` が複数定義されていると重複定義エラーになるため、古い方または重複しないよう削除・統合する。
- **対象ファイル**: テストファイル（`tests/integration/test_planning_3gacha.py` 等）
- **修正内容例**：重複するフィクスチャ定義のいずれかを削除し、残った方でテストを賄う。
- **実行コマンド例**（手動削除）。
- **検証コマンド**:
  ```powershell
  py -m ruff check --select F811 src tests; [ERRORCOUNT=$(py -m ruff check --select F811 src tests 2>&1 | grep -c "^"); echo "残り F811 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 検証コマンドの出出力で「残り F811 エラー: 0」となること。

### Step 10: その他微修正 (E302, E902, F841 など)
- **目的**: 残りの比較的少数のエラー（`await` 外での `yield`、ブロックコメントの先頭 `#`、未使用変数など）を修正する。
- **対象ファイル**: 散在
- **修正内容例**：
  - E302: 関数内で見つからない `await` の外での `yield` 修正（async ジェネレータの見直し）。
  - E902: ファイル末尾のブロックコメントの不適切な修正。
  - F841: 代入したが使われていない変数を削除または `_` にリネーム。
- **実行コマンド例**（手動またはスクリプトで個別修正）。
- **検証コマンド**:
  ```powershell
  py -m ruff check --select E302,E902,F841 src tests; [ERRORCOUNT=$(py -m ruff check --select E302,E902,F841 src tests 2>&1 | grep -c "^"); echo "残り その他エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 検証コマンドの出出力で「残り その他エラー: 0」となること。

### Step 11: 自動修復実行
- **目的**: Ruff の `--fix` と `--unsafe-fixes` オプションで自動修復可能なものを一括適用し、手間を削減する。
- **対象ファイル**: 全リポジトリ (`src`, `tests`)
- **修正内容**: Ruff が提案する自動修roff（インポート順序、未使用変数削除、ダブルクォーテーション統一など）を適用。
- **実行コマンド**：
  ```powershell
  py -m ruff check --fix --unsafe-fixes src tests
  ```
- **検証コマンド**：
  ```powershell
  py -m ruff check src tests
  ```
- **合否基準**: 検証コマンドの出力に `All checks passed!` と表示されること（または少なくとも前ステップより大幅にエラー数が減少すること）。

### Step 12: 最終検証
- **目的**: すべてのlintエラーが解消され、コードベースが健全な状態であることを確認する。
- **対象ファイル**: 全リポジトリ
- **検証コマンド**：
  ```powershell
  py -m ruff check src tests
  ```
- **合否基準**: 出力に `All checks passed!` と表示され、エラー数が0であること。

---

## 📌 実行上の注意
- 各ステップは可能な限り自動化スクリプトまたは手動での置換で実施してください。
- 大規模な置換は誤りを招く可能性があるため、変更前後で差分を確認し、必要ならテストを実行してください。
- ステップ11の自動修復は多くのエラーを一掃しますが、一部は手動での判断が必要となります（ログの f-string 変換など）。
- 最終的にはStep12の検証コマンドでゼロエラーを達成することを目標とします。

完了後は、CI パイプラインが緑になることを確認してください。