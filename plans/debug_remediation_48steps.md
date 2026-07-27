# プロジェクト精査 デバッグ修正実装計画書（48ステップ）

> 対象プロジェクト: `d:/autonovel/autonovel`（正本リポジトリ）
> 作成日: 2026-07-26
> 目的: 低性能LLMでも確実に実装できるよう、各ステップを極小化して分割した修正計画
>
> **前提ルール**
> - 全ステップ、1ステップ = 1ファイルの1箇所変更原則（複数編集禁止）
> - 各ステップは「対象ファイル → 現在の問題 → 修正内容 → 確認コマンド → 完了条件」で構成
> - ステップ完了ごとに必ず `git diff` で差分確認を行うこと
> - 実行ディレクトリは原則 `d:/autonovel/autonovel`
> - 確認コマンドの exit code 0 をもって完了とする

---

## フェーズA: プロジェクト構造・設定の矛盾解消（ステップ 1〜6）

### ステップ 1: 正本ディレクトリの決定と文書化
- 対象: `plans/debug_remediation_48steps.md`（本ファイルの冒頭）
- 問題: ルート `d:/autonovel` とサブ `d:/autonovel/autonovel` の二重構造で正本が不明
- 修正内容: 正本は **`d:/autonovel/autonovel`** と明記し、以後全作業はこのディレクトリで行う
- 確認: なし（文書化のみ）
- 完了条件: チーム内で正本ディレクトリが合意されていること
- ステータス: [x] 完了

### ステップ 2: ルート側 `d:/autonovel/src/` の棚卸し（調査のみ）
- 対象: `d:/autonovel/src/`（ルート側、誤配置）
- 問題: 正本外の `src/` が存在し紛れが生じている
- 修正内容: `git -C d:/autonovel ls-files src/ frontend/` を実行し追跡対象か確認のみ（削除しない）
- 確認コマンド: `git -C d:/autonovel ls-files src/ frontend/ | Measure-Object -Line`
- 完了条件: 追跡ファイル数を記録し、以後この領域を編集対象外とする
- ステータス: [ ] 未完了

### ステップ 3: `pyproject.toml` の mypy_path 修正
- 対象: [`autonovel/pyproject.toml`](autonovel/pyproject.toml:3)
- 問題: `mypy_path = ["autonovel/src"]` だが、`autonovel/` 内から実行するとパス解決不可
- 修正内容: `mypy_path = ["src"]` および `files = ["src"]` に変更（実行コンテキストを `autonovel/` 配下に統一）
- 確認コマンド: `cd autonovel ; python -m mypy --version` の後 `python -m mypy src/core/null_objects.py 2>&1 | Select-String "Cannot read"`
- 完了条件: `Cannot read file` エラーが表示されないこと
- ステータス: [ ] 未完了

### ステップ 4: mypy.ini 復元判断（不要ならスキップ登録）
- 対象: `autonovel/mypy.ini`（削除済み）
- 問題: git 上 `D mypy.ini` を確認済み。pyproject.toml で代替済みであるため、復元不要と確定。
- ステータス: [x] 完了

### ステップ 5: `src/models/` 不足モジュール import 確認
- 対象: [`autonovel/src/models/__init__.py`](autonovel/src/models/__init__.py:1)
- 問題: `*` import だが `__all__` 未定義で mypy 解決不可
- 修正内容: 変更せず、ステップ6で `__all__` 定義する前提で現状を把握するため `Get-Content autonovel/src/models/audit.py | Select-String "__all__"` を実行
- 完了条件: `__all__` の有無を記録（無ければステップ6で追加）
- ステータス: [ ] 未完了

### ステップ 6: `src/models/audit.py` に `__all__` 追加
- 対象: [`autonovel/src/models/audit.py`](autonovel/src/models/audit.py:1)
- 問題: `HegemonyAuditResult` `LogicalAuditResult` `LogicalAuditIssueList` が `__init__` の `*` import で公開されない
- 修正内容: ファイル先頭（import 群の直後）に `__all__ = ["HegemonyAuditResult", "LogicalAuditResult", "LogicalAuditIssueList", "NarrativeWavePattern", "CriticFeedback", "ImmersionScore", ...]` のように当該クラス名を明示
- 確認コマンド: `cd autonovel ; python -c "from src.models import HegemonyAuditResult, LogicalAuditResult, LogicalAuditIssueList; print('OK')"`
- 完了条件: `OK` が表示されること
- ステータス: [ ] 未完了

---

## フェーズB: 致命的モジュール参照エラーの解消（ステップ 7〜14）

### ステップ 7: `src/models/world.py` に `__all__` 追加
- 対象: [`autonovel/src/models/world.py`](autonovel/src/models/world.py:1)
- 問題: `WorldState` `ForeshadowingAudit` が `__init__` の `*` で公開されない
- 修正内容: import 群直後に `__all__ = ["WorldState", "ForeshadowingAudit", ...]` を追加
- 確認コマンド: `cd autonovel ; python -c "from src.models import WorldState, ForeshadowingAudit; print('OK')"`
- 完了条件: `OK` が表示されること
- ステータス: [ ] 未完了

### ステップ 8: 残りモデルモジュールの `__all__` 一括確認
- 対象: `autonovel/src/models/` の `base.py` `beat_sheet.py` `bible.py` `character.py` `db.py` `marketing.py` `planning_config.py` `plot.py` `prompt_version.py` `writing.py`
- 問題: 同様の `*` import 公開漏れの可能性
- 修正内容: 変更せず、`Get-ChildItem autonovel/src/models/*.py | ForEach-Object { Select-String -Path $_.FullName "__all__" }` で現状把握のみ
- 完了条件: `__all__` 未定義ファイルの一覧を記録（必要に応じフェーズDで対応）
- ステータス: [ ] 未完了

### ステップ 9: `null_objects.py` import 動作確認
- 対象: [`autonovel/src/core/null_objects.py`](autonovel/src/core/null_objects.py:4)
- 問題: ステップ6・7の修正前に存在しない属性参照エラー
- 修正内容: 変更なし、再確認のみ
- 確認コマンド: `cd autonovel ; python -c "from src.core.null_objects import NullLogicalAuditor; print('OK')"`
- 完了条件: `OK` 表示。エラーの場合はステップ10へ
- ステータス: [ ] 未完了

### ステップ 10: `null_objects.py` の段階的 import 検証
- 対象: [`autonovel/src/core/null_objects.py`](autonovel/src/core/null_objects.py:4)
- 問題: どのクラス import が失敗するか特定
- 修正内容: 変更せず、5クラスを1つずつ import して失敗名を記録
- 確認コマンド: `cd autonovel ; python -c "from src.models import ForeshadowingAudit" ` → 次 `HegemonyAuditResult` → 以降順次
- 完了条件: 失敗クラス名を特定し、ステップ6/7で解決済みであることを確認
- ステータス: [ ] 未完了

### ステップ 11: `null_objects.py` の import 文整理
- 対象: [`autonovel/src/core/null_objects.py`](autonovel/src/core/null_objects.py:4)
- 問題: 5クラスを1行 `from src.models import (...)` で取得しているが、mypy 解決用に個別 import が望ましい
- 修正内容: 多重度は変えず `isort` 整合のみ確認。明示 import に変更せず維持（`__all__` 解決で対応済みのため）
- 確認コマンド: `cd autonovel ; python -m ruff check src/core/null_objects.py --select I`
- 完了条件: ruff の I 違反 0 件
- ステータス: [ ] 未完了

### ステップ 12: `core/null_objects.py` の mypy 検証
- 対象: [`autonovel/src/core/null_objects.py`](autonovel/src/core/null_objects.py:1)
- 修正内容: なし
- 確認コマンド: `cd autonovel ; python -m mypy src/core/null_objects.py`
- 完了条件: `Module has no attribute` エラー 0 件
- ステータス: [ ] 未完了

### ステップ 13: 全体 mypy の該当エラー消失確認
- 対象: `autonovel/src/` 全体
- 修正内容: なし
- 確認コマンド: `cd autonovel ; python -m mypy src/core | Select-String "no attribute" | Measure-Object -Line`
- 完了条件: 該当エラーが 0 件
- ステータス: [ ] 未完了

### ステップ 14: フェーズB完了記録
- 対象: 本計画書
- 修正内容: ステップ11〜13の完了日時を追記
- 完了条件: 記録済みであること
- ステータス: [ ] 未完了

---

## フェーズC: `audit.py` の None 安全性確保（ステップ 15〜22）

### ステップ 15: `audit.py` 341行 周辺の再読込
- 対象: [`autonovel/src/agents/audit.py`](autonovel/src/agents/audit.py:333)
- 問題: `self.wave_analyzer` が None になる経路の確認
- 修正内容: 変更せず 333〜341行を読込確認
- 完了条件: None チェックが必要と判断されたこと
- ステータス: [ ] 未完了

### ステップ 16: `wave_analyzer` 初期化ロジック確認
- 対象: [`autonovel/src/agents/audit.py`](autonovel/src/agents/audit.py:333)
- 問題: 333行 `if self.wave_analyzer is None:` の後 336行で代入、341行で利用
- 修正内容: 変更せず、代入と利用の順序確認のみ
- 完了条件: 341行時点で確実に非Noneか判明（例外経路の可能性を含む）
- ステータス: [ ] 未完了

### ステップ 17: `try` ブロック内での None 利用経路特定
- 対象: [`autonovel/src/agents/audit.py:320`](autonovel/src/agents/audit.py:320)
- 問題: try 内で早期 return 後の再代入漏れがないか
- 修正内容: 変更せず確認
- 完了条件: ロジック把握
- ステータス: [ ] 未完了

### ステップ 18: `self.wave_analyzer` の型注釈追加
- 対象: [`autonovel/src/agents/audit.py`](autonovel/src/agents/audit.py:1)
- 修正内容: クラス定義部の `__init__` で `self.wave_analyzer: Optional["WavePatternAnalyzer"] = None` を明示（型注釈のみ）
- 確認コマンド: `cd autonovel ; python -m mypy src/agents/audit.py 2>&1 | Select-String "wave_analyzer"`
- 完了条件: 該当エラーの表示内容が変化すること
- ステータス: [ ] 未完了

### ステップ 19: 341行の None ガード追加
- 対象: [`autonovel/src/agents/audit.py:341`](autonovel/src/agents/audit.py:341)
- 修正内容: `return self.wave_analyzer.analyze(tension_history)` を `if self.wave_analyzer is None:\n    return NarrativeWavePattern()\nreturn self.wave_analyzer.analyze(tension_history)` に変更
- 確認コマンド: `cd autonovel ; python -m mypy src/agents/audit.py 2>&1 | Select-String "341"`
- 完了条件: 341行の None 呼出エラー消失
- ステータス: [ ] 未完了

### ステップ 20: `repo` の None ガード再確認
- 対象: [`autonovel/src/agents/audit.py:324`](autonovel/src/agents/audit.py:324)
- 修正内容: 変更せず、既存ガードの有効性確認のみ
- 完了条件: 変更不要と判断されたこと
- ステータス: [ ] 未完了

### ステップ 21: `analyze_tension_wave` の戻り値型注釈確認
- 対象: [`autonovel/src/agents/audit.py:318`](autonovel/src/agents/audit.py:318)
- 修正内容: `-> Any` を `-> "NarrativeWavePattern"` に変更（TYPE_CHECKING import 使用可）
- 確認コマンド: `cd autonovel ; python -m mypy src/agents/audit.py 2>&1 | Select-String "analyze_tension_wave"`
- 完了条件: 型エラー発生しないこと
- ステータス: [ ] 未完了

### ステップ 22: フェーズCの mypy 総合確認
- 確認コマンド: `cd autonovel ; python -m mypy src/agents/audit.py`
- 完了条件: 既存エラーが増加していないこと
- ステータス: [ ] 未完了

---

## フェーズD: テストファイル `test_async_ui_sync.py` の修復（ステップ 23〜30）

### ステップ 23: テストファイル全行読込
- 対象: [`autonovel/tests/unit/test_async_ui_sync.py`](autonovel/tests/unit/test_async_ui_sync.py:1)
- 修正内容: なし、1〜66行を把握
- 完了条件: 編集対象箇所の特定
- ステータス: [ ] 未完了

### ステップ 24: `MagicMock` import 追加
- 対象: [`autonovel/tests/unit/test_async_ui_sync.py:1`](autonovel/tests/unit/test_async_ui_sync.py:1)
- 修正内容: 1行目 `import asyncio` の次行に `from unittest.mock import MagicMock` を追加
- 確認コマンド: `cd autonovel ; python -m ruff check tests/unit/test_async_ui_sync.py --select F811`
- 完了条件: `MagicMock` 未定義エラー消失
- ステータス: [ ] 未完了

### ステップ 25: `mock_progress_state` 変数定義追加（関数1）
- 対象: [`autonovel/tests/unit/test_async_ui_sync.py:27`](autonovel/tests/unit/test_async_ui_sync.py:27)
- 修正内容: 26行（reporter生成の前）に `mock_progress_state = MagicMock()` を追加
- 確認コマンド: `cd autonovel ; python -m ruff check tests/unit/test_async_ui_sync.py --select F821`
- 完了条件: `mock_progress_state` 未定義エラー消失
- ステータス: [ ] 未完了

### ステップ 26: `mock_db` 変数定義追加
- 対象: [`autonovel/tests/unit/test_async_ui_sync.py:37`](autonovel/tests/unit/test_async_ui_sync.py:37)
- 問題: `mock_db.save_internal_state.assert_called()` が未定義参照
- 修正内容: `mock_progress_state` に関連付ける形で `mock_db = MagicMock()` を追加し、reporter に `db=mock_db` を渡すあるいは `mock_progress_state.db = mock_db` とする（実装に依存。`BackgroundReporter` の実態確認を優先）
- 確認コマンド: `cd autonovel ; python -m ruff check tests/unit/test_async_ui_sync.py --select F821`
- 完了条件: `mock_db` 未定義エラー消失
- ステータス: [ ] 未完了

### ステップ 27: `BackgroundReporter` 実態確認
- 対象: `autonovel/src/backend/background.py`
- 修正内容: 変更せず、`BackgroundReporter.__init__` の引数（state/db の有無）を確認
- 完了条件: reporter 初期化に必要な引数を把握
- ステータス: [ ] 未完了

### ステップ 28: 関数2 `test_async_ui_state_sync_consistency` の変数整合確認
- 対象: [`autonovel/tests/unit/test_async_ui_sync.py:41`](autonovel/tests/unit/test_async_ui_sync.py:41)
- 修正内容: 50行以降で `UIStateStore.update` が未 import の可能性確認。必要なら import 追加
- 確認コマンド: `cd autonovel ; python -m ruff check tests/unit/test_async_ui_sync.py --select F821`
- 完了条件: 未定義参照 0 件
- ステータス: [ ] 未完了

### ステップ 29: テストファイル単独実行
- 確認コマンド: `cd autonovel ; python -m pytest tests/unit/test_async_ui_sync.py -x --tb=short`
- 完了条件: import/NameError で停止しないこと（テスト本体の失敗は別途対処）
- ステータス: [ ] 未完了

### ステップ 30: フェーズD完了記録
- 対象: 本計画書
- 完了条件: ステップ24〜28完了日時の追記
- ステータス: [ ] 未完了

---

## フェーズE: 静的解析（Ruff）未使用変数の段階的解消（ステップ 31〜40）

### ステップ 31: Ruff 全件実行で現状把握
- 確認コマンド: `cd autonovel ; python -m ruff check . --select F841 2>&1 | Measure-Object -Line`
- 完了条件: F841 件数を記録
- ステータス: [ ] 未完了

### ステップ 32: F841 ファイル別集計
- 確認コマンド: `cd autonovel ; python -m ruff check . --select F841 --output-format=grouped > logs/ruff_f841_grouped.txt`
- 完了条件: ログ保存完了
- ステータス: [ ] 未完了

### ステップ 33: テストファイル群の未使用変数の一括確認
- 対象: `autonovel/tests/`
- 修正内容: なし
- 確認コマンド: `cd autonovel ; python -m ruff check tests/ --select F841 | Measure-Object -Line`
- 完了条件: 件数記録
- ステータス: [ ] 未完了

### ステップ 34: テストファイル 1件目の未使用変数削除
- 対象: ログ先頭のファイル
- 修正内容: 当該行の未使用変数 assignment を削除（`_` 接頭辞化は次ステップ）
- 確認コマンド: `cd autonovel ; python -m ruff check <file> --select F841`
- 完了条件: 該当ファイル F841 = 0
- ステータス: [ ] 未完了

### ステップ 35: 未使用変数の命名規則導入判断
- 対象: 本計画書
- 修正内容: 削除困難な意図的未使用変数には `_` 接頭辞を付与する方針を記載
- 完了条件: 方針文書化
- ステータス: [ ] 未完了

### ステップ 36〜39: 主要ファイル 4件の F841 解消
- 対象: ログ上位4ファイル（各ステップ1件）
- 修正内容: 各ファイルの F841 を1件ずつ解消（削除 or `_` 接頭辞）
- 確認コマンド: 各ステップで `python -m ruff check <file> --select F841`
- 完了条件: 各ファイル F841 = 0
- ステータス: [ ] 未完了

### ステップ 40: F841 全体再集計
- 確認コマンド: `cd autonovel ; python -m ruff check . --select F841 2>&1 | Measure-Object -Line`
- 完了条件: ステップ31比で件数が減少していること
- ステータス: [ ] 未完了

---

## フェーズF: 型注釈欠落の段階的補完（ステップ 41〜46）

### ステップ 41: mypy 未注釈関数の抽出
- 確認コマンド: `cd autonovel ; python -m mypy src/ 2>&1 | Select-String "Function is missing a return type annotation|Argument .* has no type" | Measure-Object -Line`
- 完了条件: 件数記録
- ステータス: [ ] 未完了

### ステップ 42: `services/prompt_manager.py` の優先対応
- 対象: `autonovel/services/prompt_manager.py`
- 修正内容: ファイル先頭の公開関数3件に戻り値型注釈を付与（`-> str` 等を推定で付与、厳密化は後続）
- 確認コマンド: `cd autonovel ; python -m mypy services/prompt_manager.py 2>&1 | Measure-Object -Line`
- 完了条件: 該当関数のエラー消失
- ステータス: [ ] 未完了

### ステップ 43: `core/exceptions.py` の型注釈補完
- 対象: `autonovel/src/core/exceptions.py`
- 修正内容: 例外クラスの `__init__` 等に型注釈付与
- 確認コマンド: `cd autonovel ; python -m mypy src/core/exceptions.py`
- 完了条件: 新規エラーなし、注釈不足エラー減少
- ステータス: [ ] 未完了

### ステップ 44: `disallow_untyped_defs` の段階有効化検討
- 対象: [`autonovel/pyproject.toml:8`](autonovel/pyproject.toml:8)
- 修正内容: 変更せず、ファイル単位の per-module override 案を本計画書に記載
- 完了条件: 段階strict化の方針文書化
- ステータス: [ ] 未完了

### ステップ 45: 型注釈 PR 分割方針の記録
- 対象: 本計画書
- 修正内容: 「1ファイル = 1PR」で進める旨を追記
- 完了条件: 文書化完了
- ステータス: [ ] 未完了

### ステップ 46: フェーズFの mypy 総合確認
- 確認コマンド: `cd autonovel ; python -m mypy src/ 2>&1 | Measure-Object -Line`
- 完了条件: エラー総数がステップ41比で減少
- ステータス: [ ] 未完了

---

## フェーズG: 全体検証・クロージング（ステップ 47〜48）

### ステップ 47: 全テスト実行
- 確認コマンド: `cd autonovel ; python -m pytest --tb=short -q`
- 完了条件: import / NameError 由来の失敗が 0 件。残失敗は別チケット化
- ステータス: [ ] 未完了

### ステップ 48: 修正完了報告書の作成
- 対象: `plans/debug_remediation_report.md`（新規）
- 修正内容: 各フェーズの完了状況、残課題、次回strict化スケジュールを記載
- 完了条件: 報告書作成完了。本48ステップ計画をクローズ
- ステータス: [ ] 未完了

---

## 付録: 実行時の安全策

1. 各ステップ開始前に `git -C autonovel stash list` で作業中 stash がないか確認
2. 1ステップ完了ごとに `git -C autonovel add -A ; git -C autonovel commit -m "step NN: <概要>"` を推奨（低性能LLMの戻し安全性向上）
3. mypy/ruff 実行時は必ず `cd autonovel` を前置すること（ステップ3以降の前提）
4. 確認コマンドの exit code が非0の場合は次ステップに進まず、當該ステップを再実行すること
