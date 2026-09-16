# P4: 非G004系Lintエラー修正実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.3（`e:/hhh`）  
**策定日**: 2026-09-16  
**前提**: G004（f-stringログ）は除外し、それ以外の約300件のエラーを対象とする。  
**目的**: 残存する非G004系Lintエラーを体系的に修正し、CIグリーン化に近づける。

---

## 📋 全12ステップ 実装マトリクス

| Step | エラーコード | 分類 | 対象ファイル数 | 主な作業内容 | 検証コマンド |
|:---:|:---:|:---|:---:|:---|:---|
| **Step 1** | E402 | インポート位置修正 | 20ファイル | 関数内/条件内インポートをファイル先頭（または TYPE_CHECKING ブロック）へ移動 | `py -m ruff check --select E402 src tests \| wc -l` |
| **Step 2** | F821 | 未定義名修正 | 15件 | テストフィクスチャの未定義変数（`chadb_host`等）を適切に定義または削除 | `py -m ruff check --select F821 src tests \| wc -l` |
| **Step 3** | E741 | あいまい変数名 `l` 変更 | 10件 | 1文字変数 `l` を `line`/`char`/`item` 等の意味ある名前にリネーム | `py -m ruff check --select E741 src tests \| wc -l` |
| **Step 4** | F811 | 重複フィクスチャ削除 | 5件 | 同名 `@pytest.fixture` の重複定義を統合・削除 | `py -m ruff check --select F811 src tests \| wc -l` |
| **Step 5** | F401 | 未使用インポート削除 | 15件 | `__all__` 追加、未使用インポート削除、テスト用インポートの `if TYPE_CHECKING` 移動 | `py -m ruff check --select F401 src tests \| wc -l` |
| **Step 6** | E712 | 真偽値比較修正 | 5件 | `== True`/`== False` を `is_xxx`/`not` に置換 | `py -m ruff check --select E712 src tests \| wc -l` |
| **Step 7** | F403 | ワイルドカードインポート排除 | 1件 | `from ... import *` を明示的インポートに置換 | `py -m ruff check --select F403 src tests \| wc -l` |
| **Step 8** | W293 | 空白行の空白削除 | 多数 | 空白行に含まれるスペース/タブを削除（一括置換） | `py -m ruff check --select W293 src tests \| wc -l` |
| **Step 9** | W292 | ファイル末尾改行追加 | 多数 | 改行なしファイルに末尾改行を追加（一括処理） | `py -m ruff check --select W292 src tests \| wc -l` |
| **Step 10** | E302/E902/F841 | その他微修正 | 数件 | 予期せぬ `await` 外 `yield`、ブロックコメント先頭、未使用変数 `_` 化等 | `py -m ruff check --select E302,E902,F841 src tests \| wc -l` |
| **Step 11** | 自動修復実行 | 全リポジトリ | 全体 | `ruff --fix --unsafe-fixes` で残存自動修正可能項目を一括適用 | `py -m ruff check --fix --unsafe-fixes src tests` |
| **Step 12** | 最終検証 | 全リポジトリ | 全体 | 非G004エラーが0であることを確認 | `py -m ruff check --ignore G004 src tests` |

---

## 🛠 各ステップ詳細仕様

### Step 1: E402 モジュールレベルインポート移動
- **目的**: 関数内、条件ブロック内、または `try/except` 内にあるインポート文をモジュール先頭に移動し、静的解析の正確性を向上させる。
- **主な対象ファイル**:
  - `src/services/writing_services.py` (4件: `from pydantic import BaseModel`, `from src.agents.audit import PlotIntegrityMonitor`, `from src.models import WritingContext`, `import re`)
  - `tests/conftest.py` (4件: `from tests.mocks.llm_adapter import ...`, `import pytest`, `from sqlalchemy ...`, `from src.infrastructure...`)
  - `tests/unit/services/test_marketing.py` (2件: `import pytest`, `from unittest.mock import MagicMock`)
  - `tests/unit/test_commercial_prompts.py` (1件: 商用プロンプトインポート)
  - `tests/contract/test_api_contracts.py` (1件: `from src.backend.server import app`)
- **修正パターン**:
  ```python
  # 変更前（関数内）
  def func():
      except ImportError:
          from src.config.project_context import ProjectContext  # type: ignore
  # 変更後（ファイル先頭、TYPE_CHECKING使用）
  from __future__ import annotations
  if TYPE_CHECKING:
      from src.config.project_context import ProjectContext
  ```
- **実行コマンド例**（手動またはスクリプトで各ファイル修正）:
  ```powershell
  # 例: writing_services.py の先頭へ移動
  # エディタで該当行をカット＆ペースト、必要なら TYPE_CHECKING ブロックへ
  ```
- **検証コマンド**:
  ```powershell
  py -m ruff check --select E402 src tests; [ERRORCOUNT=$(py -m ruff check --select E402 src tests 2>&1 | grep -c "^"); echo "残り E402 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 「残り E402 エラー: 0」となること。

### Step 2: F821 未定義名修正
- **目的**: テストコードで未定義の変数（`chadb_host`, `chadb_port`, `chadb_container`, `chromadb_container`, `Any`, `mock` 等）を適切に定義または削除する。
- **主な対象ファイル**:
  - `tests/integration/conftest.py` (`chadb_host`, `chadb_port`)
  - `tests/integration/simple_container_info.py` (`chadb_container`)
  - `tests/integration/super_simple_test.py` (`chromadb_container`)
  - `tests/integration/test_chromadb_fixture.py` (`chromadb_container`)
  - `tests/integration/test_example_migration.py` (`chadb_host`, `chadb_port`)
  - `tests/integration/test_redis_chromadb.py` (`chadb_host`, `chadb_port`)
  - `tests/backend/test_database_core.py` (`mock` → `unittest.mock.ANY` または `mock.ANY` の import)
  - `tests/unit/test_series_serializer.py` (`Any` → `from typing import Any`)
- **修正内容例**:
  - フィクスチャから適切な値を取得するよう変更（`chadb_host = chromadb_container.get_container_host_ip()` 等）
  - 不要なテストコードの削除（`super_simple_test.py` 等は削除検討）
  - `mock` → `from unittest.mock import ANY` として `mock.ANY` → `ANY`
- **検証コマンド**:
  ```powershell
  py -m ruff check --select F821 src tests; [ERRORCOUNT=$(py -m ruff check --select F821 src tests 2>&1 | grep -c "^"); echo "残り F821 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 「残り F821 エラー: 0」となること。

### Step 3: E741 あいまい変数名 `l` 変更
- **目的**: 1文字変数 `l` を意味のある名前にリネームし、可読性向上と誤認防止。
- **主な対象ファイル**:
  - `tests/unit/test_blind_review_purifier.py` (3件: `for l in leaks` → `for leak in leaks`)
  - `tests/unit/test_synthesizer_emotions.py` (2件: `for l in lines` → `for line in lines`)
  - `tests/unit/test_voicevox_pipeline.py` (2件: `for l in lines` → `for line in lines`)
- **修正内容**: リスト内包表記やジェネレータ式内の `l` を `line`/`leak`/`item` 等に変更。
- **検証コマンド**:
  ```powershell
  py -m ruff check --select E741 src tests; [ERRORCOUNT=$(py -m ruff check --select E741 src tests 2>&1 | grep -c "^"); echo "残り E741 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 「残り E741 エラー: 0」となること。

### Step 4: F811 重複フィクスチャ削除
- **目的**: 同名の `@pytest.fixture` が複数定義されているのを統合・削除し、テストの安定性を確保。
- **対象ファイル**: `tests/integration/test_planning_3gacha.py` (3組の重複: `mock_bible_generator`, `mock_repo`, `mock_book_score_calculator`)
- **修正内容**: 重複するフィクスチャ定義のいずれかを削除し、共通のフィクスチャを `conftest.py` 等に移動するか、一方をリネームして用途を分ける。
- **検証コマンド**:
  ```powershell
  py -m ruff check --select F811 src tests; [ERRORCOUNT=$(py -m ruff check --select F811 src tests 2>&1 | grep -c "^"); echo "残り F811 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 「残り F811 エラー: 0」となること。

### Step 5: F401 未使用インポート削除
- **目的**: 使用されていないインポートを削除し、依存関係を明確化。
- **主な対象と修正**:
  - `src/services/vector_store/__init__.py`: `_metadata_matches`, `_embedding_to_pgvector` を `__all__` に追加または削除
  - `tests/mocks/__init__.py`: `from src.services.image_service import ImageService` 削除
  - `tests/factories/__init__.py`: `from typing import Optional` 削除
  - `tests/unit/application/test_writing_use_cases_complete.py`: `from src.application.dtos.episode_dto import WriteEpisodeDTO` 削除
  - `tests/unit/backend/test_cors_auth_headers.py`: `import pytest` 削除（pytestmark使用なし）
  - `src/agents/erotic_enhancer.py`: `from config.erotic_pacing import EroticCurve` 削除または使用
  - `src/application/use_cases/__init__.py`: `BookUseCases` を `__all__` に追加
  - `src/backend/multimedia_service.py`: テスト用フィクスチャインポートを `if TYPE_CHECKING:` ブロックへ移動または削除
  - `src/infrastructure/repositories/__init__.py`: `import sys` 削除
- **自動修正**: `ruff --fix --select F401` で大半解決可能。
- **検証コマンド**:
  ```powershell
  py -m ruff check --select F401 src tests; [ERRORCOUNT=$(py -m ruff check --select F401 src tests 2>&1 | grep -c "^"); echo "残り F401 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 「残り F401 エラー: 0」となること。

### Step 6: E712 真偽値比較修正
- **目的**: `== True`/`== False` を Pythonic な書き換え（`is_xxx`/`not`）に統一。
- **対象**: テストファイル中心（`tests/unit/test_circuit_breaker.py`, `tests/unit/test_erotic_baseline.py`, `tests/unit/workflows/test_writing_graph_nodes.py` 等）
- **修正例**:
  ```python
  # 変更前
  assert breaker.can_execute("test") == True
  # 変更後
  assert breaker.can_execute("test")
  # 変更前
  assert gate.enabled == False
  # 変更後
  assert not gate.enabled
  ```
- **検証コマンド**:
  ```powershell
  py -m ruff check --select E712 src tests; [ERRORCOUNT=$(py -m ruff check --select E712 src tests 2>&1 | grep -c "^"); echo "残り E712 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 「残り E712 エラー: 0」となること。

### Step 7: F403 ワイルドカードインポート排除
- **目的**: `from ... import *` を明示的インポートに置換し、未使用検出を可能にする。
- **対象ファイル**: `tests/unit/test_book_score_service.py:6` (`from tests.unit.services.test_book_score_calculator import *`)
- **修正内容**: 必要なシンボルのみ明示的にインポート（`from tests.unit.services.test_book_score_calculator import BookScoreCalculatorTest` 等）。
- **検証コマンド**:
  ```powershell
  py -m ruff check --select F403 src tests; [ERRORCOUNT=$(py -m ruff check --select F403 src tests 2>&1 | grep -c "^"); echo "残り F403 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 「残り F403 エラー: 0」となること。

### Step 8: W293 空白行の空白削除
- **目的**: 空白行にスペース/タブが混入しているのを削除し、diff ノイズを減らす。
- **対象**: 数百ファイル（主にテストファイル）
- **一括修正コマンド**:
  ```powershell
  Get-ChildItem -Recurse -Include *.py | ForEach-Object {
      (Get-Content $_.FullName) -replace '^\s+$', '' | Set-Content $_.FullName
  }
  ```
- **検証コマンド**:
  ```powershell
  py -m ruff check --select W293 src tests; [ERRORCOUNT=$(py -m ruff check --select W293 src tests 2>&1 | grep -c "^"); echo "残り W293 エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 「残り W293 エラー: 0」となること。

### Step 9: W292 ファイル末尾改行追加
- **目的**: ファイル末尾に改行がないと diff がノイジーになるため、改行を追加。
- **対象**: 数十ファイル
- **一括修正コマンド**:
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
- **合否基準**: 「残り W292 エラー: 0」となること。

### Step 10: E302/E902/F841 その他微修正
- **目的**: 残りの少数エラーを個別修正。
- **対象**:
  - E302: 予期せぬ `await` 外での `yield` → async generator として修正
  - E902: ブロックコメント先頭の `#` 修正
  - F841: 未使用変数 → `_` リネームまたは削除
- **対象ファイル**: 散在（`tests/unit/...`, `src/...`）
- **検証コマンド**:
  ```powershell
  py -m ruff check --select E302,E902,F841 src tests; [ERRORCOUNT=$(py -m ruff check --select E302,E902,F841 src tests 2>&1 | grep -c "^"); echo "残り その他エラー: $ERRORCOUNT"]
  ```
- **合否基準**: 「残り その他エラー: 0」となること。

### Step 11: 自動修復実行
- **目的**: ここまでで残った自動修正可能なエラーを一括適用。
- **実行コマンド**:
  ```powershell
  py -m ruff check --fix --unsafe-fixes src tests
  ```
- **検証コマンド**: Step 12 と同じ。

### Step 12: 最終検証（非G004）
- **目的**: G004を除くすべてのlintエラーが0であることを確認。
- **検証コマンド**:
  ```powershell
  py -m ruff check --ignore G004 src tests
  ```
- **合否基準**: 出力に `All checks passed!` と表示され、エラー数が0であること。

---

## 📌 実行上の注意
- **Step 1-7** はファイル単位で手動修正が必要なものが多いです。エディタの「すべて置換」や正規表現置換を活用してください。
- **Step 8-9** は一括 PowerShell コマンドで一括処理可能です（バックアップ推奨）。
- **Step 11** の自動修復は Step 1-10 実施後に実行し、取りこぼしを拾ってください。
- 最終的には **Step 12** で `--ignore G004` を付けてゼロエラーを目指します。
- 各ステップ完了後は対応する検証コマンドを実行し、エラー数減少を確認してから次ステップへ進んでください。

---

## 📊 進捗管理用チェックリスト

- [ ] Step 1: E402 解消
- [ ] Step 2: F821 解消
- [ ] Step 3: E741 解消
- [ ] Step 4: F811 解消
- [ ] Step 5: F401 解消
- [ ] Step 6: E712 解消
- [ ] Step 7: F403 解消
- [ ] Step 8: W293 解消
- [ ] Step 9: W292 解消
- [ ] Step 10: その他微修正解消
- [ ] Step 11: 自動修復実行
- [ ] Step 12: 最終検証パス (`py -m ruff check --ignore G004 src tests` → `All checks passed!`)

完了後、CIパイプラインが緑になることを確認してください。