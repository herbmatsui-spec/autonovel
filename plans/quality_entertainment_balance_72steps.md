# 高品質×面白い バランス実装計画書（72ステップ）

**作成日**: 2026-07-09
**対象プロジェクト**: cR15 (覇権小説自動生成エンジン)
**目的**: 「高品質≠面白い」問題を解決し、高品質かつ面白い作品を生み出す3改善案を低性能LLMでも確実に実装できる粒度で分割する。

---

## 3改善案と対応フェーズ

| 改善案 | 概要 | フェーズ | ステップ |
|--------|------|----------|----------|
| A | まず「刺さり」を設計し、品質はその手段に落とす（感情設計先行） | Phase 1-3 | 1-30 |
| B | 意図的に「未完成の尖り」を残す（角保全システム） | Phase 4-5 | 31-54 |
| C | 早期の「面白さ検証」ループを必須にする（ラフ検証ループ） | Phase 6-8 | 55-72 |

## 設計思想（低性能LLM対応の方針）
1. **1ステップ＝1ファイル変更or1関数追加**を厳守し、cognitive load を最小化する。
2. 既存DBモデル（`Plot`, `Foreshadowing`, `Character.registry_data`, `narrative_metrics`等）と定数（`EMOTIONAL_CURVES`, `DEFAULT_DESIRES`）を最大限活用する。
3. LLMの推論に頼る部分は「プロンプトで構造化JSONを要求」し、Python側でバリデーション＆フォールバックする堅牢設計とする。
4. 各ステップは単体テスト可能な粒度とし、TDD（Red-Green-Refactor）を前提とする。
5. 「品質は感情の従属変数」「尖りは品質化の過程でも保持」「面白さは品質整備の前に検証」をシステム的に強制する。

## 既存資産の再利用マップ
| 既存資産 | 場所 | 用途 |
|----------|------|------|
| `EMOTIONAL_CURVES` | `src/backend/tension_curve_config.py` | 改善案A: 目標tension曲线の基盤 |
| `NarrativeMetricScore` | `src/models/narrative_metrics.py` | 改善案A,B: 指標スコアの格納 |
| `CritiqueAgent` | `src/backend/engine_critique.py` | 改善案C: 検証ループの実装基盤 |
| `DeAIAuditor` | `src/agents/audit.py` | 改善案B: 品質監査の既存パターン |
| `DEFAULT_DESIRES` | `streamlit_app/app.py:41` | 改善案A: 感情起点のUI選択肢 |
| `prompt_manager` | `prompts/manager.py` | 改善案全て: プロンプト注入 |

---

# Phase 1: 改善案A - 感情設計先行インフラ（ステップ1-10）

## 目標
プロット生成の**前**に「刺さり」（カタルシス/共感/背筋/怒り等の感情反応）を1行で定義し、その感情に到達する最小プロットを書く準備をする。「品質は感情の従属変数」を型で強制する。

### ステップ1: 感情起点の定数定義ファイル作成
- **ファイル**: `config/emotional_hook_vocabulary.py`（新規）
- **内容**: `EMOTIONAL_HOOKS` 辞書を定義。キー=フック名（`catharsis`, `empathy_peak`, `chilling`, `righteous_anger`, `triumph`等）、値=（日本語表示名, 1行の感情定義, 推奨tensionピーク値）のタプル。純粋なPython定数のみ。テスト不要。

### ステップ2: 感情起点からtensionピーク値を取得する関数
- **ファイル**: `config/emotional_hook_vocabulary.py` に追記
- **内容**: `get_hook_peak_tension(hook_name: str) -> int` 関数。`EMOTIONAL_HOOKS` から該当フックのtensionピーク値を返す。未知フックは `50` を返すフォールバック付き。

### ステップ3: 感情起点選択のバリデーション関数
- **ファイル**: `config/emotional_hook_vocabulary.py` に追記
- **内容**: `validate_hook(hook_name: str) -> bool` 関数。フック名が `EMOTIONAL_HOOKS` に存在するかを返す。

### ステップ4: ステップ1-3の単体テスト作成
- **ファイル**: `tests/test_emotional_hook_vocabulary.py`（新規）
- **内容**: `get_hook_peak_tension` の未知フック時フォールバック、`validate_hook` の真偽値、全フック名が空文字でないことを検証。

### ステップ5: Pydantineモデル `EmotionalHookSpec` 作成
- **ファイル**: `src/models/emotional_hook.py`（新規）
- **内容**: 
  ```python
  class EmotionalHookSpec(BaseModel):
      hook_name: str = Field(..., description="感情起点名")
      one_line_intent: str = Field(..., max_length=120, description="1行で表した刺さり")
      target_tension_peak: int = Field(default=80, ge=0, le=100)
      subordinate_to_quality: bool = Field(default=True, description="品質はこの感情の従属変数")
  ```

### ステップ6: `EmotionalHookSpec` のバリデータ追加
- **ファイル**: `src/models/emotional_hook.py` に追記
- **内容**: `@field_validator("hook_name")` で `validate_hook` を呼び出し、未知フックは `ValueError`。`subordinate_to_quality` が `False` の場合は警告ログ（品質が感情に従属しない設定）。

### ステップ7: ステップ5-6の単体テスト作成
- **ファイル**: `tests/test_emotional_hook.py`（新規）
- **内容**: 正常系（既存フック）、異常系（未知フックで `ValueError`）、`one_line_intent` の120文字超過で `ValidationError` を検証。

### ステップ8: `Plot` モデルへ `emotional_hook` 項目追加
- **ファイル**: `src/models/plot.py` の該当クラス（`PlotAnalytics` 或いは `Plot`）に `emotional_hook: Optional[EmotionalHookSpec] = Field(default=None)` を追記。
- **理由**: プロット生成時に感情起点をDB永続化し、後工程で「まだ刺さりが残っているか」を検証可能にする。

### ステップ9: DBマイグレーション（`Plot` テーブルへ `emotional_hook_json` 追加）
- **ファイル**: `alembic/versions/XXXX_add_emotional_hook.py`（新規）
- **内容**: `Plot` テーブルへ `emotional_hook_json` (Text, nullable=True) 追加。JSON文字列で格納。`alembic revision --autogenerate` で生成し、既存データには影響なし。

### ステップ10: マイグレーションのロールバック確認
- **アクション**: `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` を実行し、冪等性確認。結果をコミットメッセージに記録。

---

# Phase 2: 改善案A - 感情起点プロンプト注入（ステップ11-20）

## 目標
プロット生成プロンプトに「本話の刺さり: {one_line_intent}（目標tensionピーク: {target_tension_peak}）」を注入し、LLMが品質を感情の従属変数として扱うよう誘導する。

### ステップ11: プロンプトテンプレート調査と箇所特定
- **ファイル**: `prompts/plotting.py` を調査
- **作業**: プロット生成用システムプロンプト内の tension 指定箇所を特定し、変数化可能か確認。該当行をメモ（`HOOK_INJECTION_POINT` と名付ける）。

### ステップ12: 感情起点注入用テンプレート文字列の定数化
- **ファイル**: `prompts/plotting.py`
- **内容**: `EMOTIONAL_HOOK_TEMPLATE = "本話の刺さり: {one_line_intent}（目標tensionピーク: {target_tension_peak}/100、品質はこの感情に従属させること）"` を定数定義。

### ステップ13: `PromptManager.build_plot_prompt` へフック引数追加
- **ファイル**: `prompts/manager.py`
- **内容**: `build_plot_prompt` メソッドへ `emotional_hook: Optional[EmotionalHookSpec] = None` を引数追加。`None` の場合は従来通りのプロンプトを返す（後方互換）。

### ステップ14: フック注入ロジックの実装
- **ファイル**: `prompts/manager.py`
- **内容**: `emotional_hook` が `None` でなければ `EMOTIONAL_HOOK_TEMPLATE.format(...)` をプロンプトの `HOOK_INJECTION_POINT` に挿入。

### ステップ15: ステップ13-14の単体テスト作成
- **ファイル**: `tests/test_emotional_hook_prompt.py`（新規）
- **内容**: `emotional_hook=None` で従来プロンプトと同一、`emotional_hook` 指定で `本話の刺さり` 文字列が含まれることを検証。

### ステップ16: `Engine` へフック取得処理の組み込み（設計）
- **ファイル**: `src/backend/engine_plot.py`（プロット生成エンジン）の該当メソッドを特定
- **作業**: フックを `Plot.emotional_hook` から取得する箇所を設計。既存の `get_target_tension` 呼び出し箇所付近への統合を想定。

### ステップ17: `Engine` へフック取得処理の実装
- **ファイル**: `src/backend/engine_plot.py`
- **内容**: `Plot.emotional_hook` が存在すればそれを `build_plot_prompt` へ渡す。未設定時は `DEFAULT_DESIRES` の先頭（`カタルシス`）から `EmotionalHookSpec` を構築するフォールバック。

### ステップ18: フック未設定時の警告ログ
- **ファイル**: `src/backend/engine_plot.py`
- **内容**: フック未設定でフォールバック動作した場合 `logger.warning("emotional_hook未設定、デフォルト(catharsis)で補完")` を出力。

### ステップ19: 統合テスト - フック注入のE2E
- **ファイル**: `tests/test_engine_plot_hook_integration.py`（新規）
- **内容**: モックLLM + モックリポジトリで `engine_plot` を実行し、`build_plot_prompt` へフックが渡ることを `mock.assert_called_once_with` で検証。

### ステップ20: 品質監査時の「刺さり維持」チェック項目追加
- **ファイル**: `src/agents/audit.py` の `DeAIAuditor.audit` に、`emotional_hook` がプロットに含まれる場合「本文に刺さりが残っているか」を審査項目へ追加する設計メモを記述（実装はステップ54）。現時点ではTODOコメントのみ。

---

# Phase 3: 改善案A - 目標tension調整と面白さ優先順序の強制（ステップ21-30）

## 目標
感情起点から `EMOTIONAL_CURVES` を選択し、「面白さ先行 → 品質は後工程」の順序をコードで強制する。`subordinate_to_quality` フラグで品質監査が感情を殺さないようにする。

### ステップ21: フックから曲線選択関数の追加
- **ファイル**: `src/backend/tension_curve_config.py` に追記
- **内容**: `select_curve_by_hook(hook_name: str) -> str` 関数。`catharsis` → `zamaa_heavy`、`empathy_peak` → `slow_burn` 等の単純マッピング辞書 `HOOK_CURVE_MAP` を定義して返す。

### ステップ22: ステップ21の単体テスト作成
- **ファイル**: `tests/test_tension_curve_config.py` に追記（既存ファイルがあれば）
- **内容**: `select_curve_by_hook("catharsis")` が `"zamaa_heavy"` を返すこと、未知フックで `DEFAULT_CURVE` を返すことを検証。

### ステップ23: `get_target_tension` のフック対応拡張
- **ファイル**: `src/backend/tension_curve_config.py` の `get_target_tension` を拡張
- **内容**: 第3引数に `hook_name` を追加し、内部で `select_curve_by_hook` を使用。既存の `archetype_key` 引数は後方互換のため維持。

### ステップ24: ステップ23の単体テスト作成
- **ファイル**: `tests/test_tension_curve_config.py` に追記
- **内容**: `get_target_tension(5, 20, hook_name="catharsis")` で `zamaa_heavy` 曲線から値が返ること、`hook_name=None` で従来挙動を維持することを検証。

### ステップ25: プロット生成順序制御フラグの定数定義
- **ファイル**: `src/backend/engine_plot.py` に追記
- **内容**: `ENFORCE_ENTERTAINMENT_FIRST = True` 定数。`True` の場合「面白さ検証が通らない限り品質監査工程をスキップしない」挙動を后续工程で強制。

### ステップ26: `yield_*.py` に面白さ優先順序のガード節追加
- **ファイル**: `src/backend/engine_plot.py` のプロット生成エントリ
- **内容**: `ENFORCE_ENTERTAINMENT_FIRST` が `True` で、かつ `Plot.emotional_hook` が `None` の場合は `RuntimeError("面白さ先行モード: emotional_hook が未設定です")`。強制的に感情設計を経由させる。

### ステップ27: ステップ25-26の単体テスト作成
- **ファイル**: `tests/test_engine_plot_enforce.py`（新規）
- **内容**: フック未設定で `RuntimeError`、フック設定済みで正常終了を検証。

### ステップ28: `UIStateStore.selected_desires` とフックの同期
- **ファイル**: `streamlit_app/state.py`
- **内容**: `runtime.selected_desires` の先頭をフック名として `EmotionalHookSpec` を構築するヘルパー `desires_to_hook()` を追加。UI 既存選択肢を低コストで流用。

### ステップ29: ステップ28の単体テスト作成
- **ファイル**: `tests/test_state_desires_to_hook.py`（新規）
- **内容**: `selected_desires=["カタルシス"]` → `hook_name="catharsis"` に変換されることを検証。

### ステップ30: Phase 1-3 統合E2Eテスト
- **ファイル**: `tests/test_phase1to3_e2e.py`（新規）
- **内容**: UI選択 → フック構築 → tension曲線選択 → プロンプト注入 → モックLLM応答 → `Plot.emotional_hook` 永続化までの流れをモックで検証。

---

# Phase 4: 改善案B - 「未完成の尖り」保全システム基盤（ステップ31-42）

## 目標
「削ってはいけない角」を3つ固定し、品質向上工程（`DeAIAuditor`, `CritiqueAgent`）で角が削られないようシステム的に強制する。

### ステップ31: 尖り定義定数ファイル作成
- **ファイル**: `config/sharp_edge_vocabulary.py`（新規）
- **内容**: `SHARP_EDGE_TYPES = ["ending_pullback", "protagonist_flaw", "abnormal_dialogue"]` と日本語説明辞書 `SHARP_EDGE_DESCRIPTIONS` を定義。純粋定数。

### ステップ32: `SharpEdgeSpec` Pydanticモデル作成
- **ファイル**: `src/models/sharp_edge.py`（新規）
- **内容**: 
  ```python
  class SharpEdgeSpec(BaseModel):
      edge_type: str  # SHARP_EDGE_TYPESのいずれか
      description: str = Field(..., max_length=200, description="この角の内容")
      preserve_on_quality_polish: bool = Field(default=True)
  ```

### ステップ33: `SharpEdgeSpec` バリデータ追加
- **ファイル**: `src/models/sharp_edge.py` に追記
- **内容**: `@field_validator("edge_type")` で `edge_type` が `SHARP_EDGE_TYPES` に含まれるか検証。`preserve_on_quality_polish=False` の場合は警告ログ。

### ステップ34: ステップ31-33の単体テスト作成
- **ファイル**: `tests/test_sharp_edge.py`（新規）
- **内容**: 正常系3型、異常系（未知 `edge_type` で `ValueError`）、`description` 200文字超過で `ValidationError` を検証。

### ステップ35: `Plot` モデルへ `sharp_edges` リスト項目追加
- **ファイル**: `src/models/plot.py` に追記
- **内容**: `sharp_edges: List[SharpEdgeSpec] = Field(default_factory=list, description="削ってはいけない3つの角")` を追加。

### ステップ36: DBマイグレーション（`sharp_edges_json` 追加）
- **ファイル**: `alembic/versions/YYYY_add_sharp_edges.py`（新規）
- **内容**: `Plot` テーブルへ `sharp_edges_json` (Text, nullable=True) 追加。JSON配列で格納。

### ステップ37: マイグレーションのロールバック確認
- **アクション**: ステップ10と同様に `upgrade` / `downgrade` / `upgrade` で冪等性確認。

### ステップ38: 尖り自動提案プロンプトのテンプレート作成
- **ファイル**: `prompts/plotting.py`
- **内容**: `SHARP_EDGE_PROPOSAL_TEMPLATE` 定数。LLMに「削ってはいけない3つの角を `ending_pullback`, `protagonist_flaw`, `abnormal_dialogue` 型で提案せよ（JSON配列）」と要求するテンプレート。構造化JSONを要求しPython側で検証。

### ステップ39: `PromptManager.build_sharp_edge_proposal_prompt` 追加
- **ファイル**: `prompts/manager.py`
- **内容**: ステップ38のテンプレートを利用するメソッド。引数はプロット概要文字列。戻り値は `(prompt_str, expected_schema)`。

### ステップ40: ステップ38-39の単体テスト作成
- **ファイル**: `tests/test_sharp_edge_prompt.py`（新規）
- **内容**: 生成プロンプトに3型の `edge_type` が列挙されていること、JSON配列要求が含まれることを検証。

### ステップ41: `Engine` へ尖り提案取得処理の組み込み
- **ファイル**: `src/backend/engine_plot.py`
- **内容**: プロット生成後に `build_sharp_edge_proposal_prompt` を呼び、LLM応答を `List[SharpEdgeSpec]` としてパース＆バリデーション。失敗時は空リストでフォールバック。

### ステップ42: ステップ41の統合テスト
- **ファイル**: `tests/test_engine_sharp_edge_proposal.py`（新規）
- **内容**: モックLLMが正しいJSONを返した場合 `Plot.sharp_edges` に3件格納されること、不正JSONで空リストになることを検証。

---

# Phase 5: 改善案B - 品質監査での尖り保全強制（ステップ43-54）

## 目標
`DeAIAuditor` と `CritiqueAgent` の品質向上ルックで「角が削られたら没戻し」を実装し、高品質化が尖りを殺す副作用を遮断する。

### ステップ43: 尖り保全チェッカー関数の作成
- **ファイル**: `src/backend/sharp_edge_preserver.py`（新規）
- **内容**: `check_edges_preserved(before_content: str, after_content: str, edges: List[SharpEdgeSpec]) -> List[SharpEdgeSpec]` 関数。各 `edge.description` のキーフレーズが `after_content` に存在するかを単純文字列検索で検証。削除された `edge` リストを返す。

### ステップ44: ステップ43の単体テスト作成
- **ファイル**: `tests/test_sharp_edge_preserver.py`（新規）
- **内容**: キーフレーズ保持で空リスト、削除で該当 `edge` が返ることを検証。大文字小文字・前後空白の正規化も確認。

### ステップ45: `DeAIAuditor` へ尖り保全チェック統合
- **ファイル**: `src/agents/audit.py` の `DeAIAuditor.audit`
- **内容**: `audit(content, before_content=None, edges=None)` へ引数追加。`edges` が渡れば `check_edges_preserved` を呼び、削除された `edge` があれば `(False, "以下の角が削られました: ...")` を返す。

### ステップ46: ステップ45の単体テスト作成
- **ファイル**: `tests/test_deai_auditor_edges.py`（新規）
- **内容**: 角保持で `(True, ...)`, 角削除で `(False, "削られました")` を検証。

### ステップ47: `CritiqueAgent` へ尖り保全チェック統合
- **ファイル**: `src/backend/engine_critique.py` の `run_iterative_gap_analysis`
- **内容**: 改修前後のコンテンツを比較し `check_edges_preserved` を呼ぶ。削除された `edge` があれば改善案レポートに「尖りが削られたため没戻し推奨: {edge_type}」を追記。

### ステップ48: 没戻しフラグのDB永続化
- **ファイル**: `alembic/versions/ZZZZ_add_quality_polish_status.py`（新規）
- **内容**: `Plot` テーブルへ `quality_polish_status` (String, default="pending") を追加。`pending` / `passed` / `rejected_edge_loss` の3状態。

### ステップ49: `quality_polish_status` のPydantic列挙型定義
- **ファイル**: `src/models/plot.py` に追記
- **内容**: `QualityPolishStatus = Literal["pending", "passed", "rejected_edge_loss"]` を定義し、`Plot.quality_polish_status` に付与。

### ステップ50: ステップ48-49のロールバック確認
- **アクション**: `upgrade` / `downgrade` / `upgrade` で冪等性確認。

### ステップ51: 品質監査パイプラインへステータス更新処理追加
- **ファイル**: `src/backend/engine_critique.py`
- **内容**: `check_edges_preserved` 結果に応じて `Plot.quality_polish_status` を `passed` or `rejected_edge_loss` に更新するリポジトリ呼び出しを追加。

### ステップ52: ステップ47-51の統合テスト作成
- **ファイル**: `tests/test_critique_edge_rejection.py`（新規）
- **内容**: モックリポジトリで角削除シナリオ → `quality_polish_status=rejected_edge_loss`、角保持 → `passed` を検証。

### ステップ53: ステップ20のTODO実装 - `DeAIAuditor` の刺さり維持チェック
- **ファイル**: `src/agents/audit.py`
- **内容**: ステップ20でメモしたTODOを実装。`emotional_hook.one_line_intent` のキーフレーズが本文に残っているかを `check_edges_preserved` と同様に検証。`EmotionalHookSpec` を `SharpEdgeSpec` にラップして再利用可能に。

### ステップ54: Phase 4-5 統合E2Eテスト
- **ファイル**: `tests/test_phase4to5_e2e.py`（新規）
- **内容**: 尖り3件提案 → 品質監査で角削除 → `rejected_edge_loss` → 再生成要求フローをモックで検証。

---

# Phase 6: 改善案C - 早期面白さ検証ループ基盤（ステップ55-62）

## 目標
品質整備の**前**に、ラフプロット・冒頭500字・立ち絵CLIPのみで「面白さ検証」を実施し、興味が取れなければ基幹構造に戻すループを作る。

### ステップ55: 面白さ検証用Pydanticモデル作成
- **ファイル**: `src/models/entertainment_check.py`（新規）
- **内容**: 
  ```python
  class EntertainmentCheckResult(BaseModel):
      interest_score: int = Field(..., ge=0, le=100, description="興味を引く度")
      physiological_reaction: str = Field(..., description="読者の生理反応: 涙/怒り/背筋/共感/無反応 等")
      would_continue_reading: bool
      feedback: str = Field(..., max_length=300)
  ```

### ステップ56: ステップ55の単体テスト作成
- **ファイル**: `tests/test_entertainment_check_model.py`（新規）
- **内容**: `interest_score` 境界値（0, 100, 101で `ValidationError`）、必須フィールド欠落で `ValidationError` を検証。

### ステップ57: 早期検証用プロンプトテンプレート作成
- **ファイル**: `prompts/plotting.py`
- **内容**: `EARLY_ENTERTAINMENT_CHECK_TEMPLATE` 定数。冒頭500字・ラフプロットのみを与え「品質を評価せず、面白さのみを評価せよ。`EntertainmentCheckResult` のJSONを返せ」と要求。

### ステップ58: `PromptManager.build_early_entertainment_check_prompt` 追加
- **ファイル**: `prompts/manager.py`
- **内容**: ステップ57のテンプレートを利用するメソッド。引数は `rough_plot: str`, `opening_500_chars: str`。LLM推論結果のJSONをパースする際 `EntertainmentCheckResult` でバリデーション。

### ステップ59: ステップ57-58の単体テスト作成
- **ファイル**: `tests/test_early_entertainment_prompt.py`（新規）
- **内容**: 生成プロンプトに「品質を評価せず」「面白さのみ」という指示が含まれること、入力文字列が埋め込まれることを検証。

### ステップ60: `EarlyEntertainmentChecker` エージェントクラス作成
- **ファイル**: `src/agents/early_entertainment_checker.py`（新規）
- **内容**: `__init__(self, llm, prompt_manager)` と `check(rough_plot, opening_500_chars) -> EntertainmentCheckResult` メソッド。LLM応答のJSONパース失敗時は `interest_score=0` のフォールバック `EntertainmentCheckResult` を返す。

### ステップ61: ステップ60の単体テスト作成
- **ファイル**: `tests/test_early_entertainment_checker.py`（新規）
- **内容**: モックLLM正常応答で `interest_score=85`、不正応答でフォールバック `interest_score=0` を検証。

### ステップ62: DB永続化 - `entertainment_check_log` テーブル
- **ファイル**: `alembic/versions/WWWW_add_entertainment_check_log.py`（新規）
- **内容**: `entertainment_check_log` テーブル新規作成。`id`, `book_id`, `ep_num`, `interest_score`, `physiological_reaction`, `would_continue_reading`, `feedback`, `created_at`。ロールバック確認付き。

---

# Phase 7: 改善案C - 検証ループをプロット生成パイプラインへ統合（ステップ63-68）

## 目標
「面白さ検証 → 興味不足なら基幹構造戻し → 興味OKなら品質整備」の順序を `Engine` パイプラインに強制する。

### ステップ63: 検証ループ制御関数の作成
- **ファイル**: `src/backend/entertainment_loop.py`（新規）
- **内容**: `async def run_entertainment_first_loop(checker, rough_plot, opening_chars, threshold=60, max_retries=2) -> EntertainmentCheckResult` 関数。`interest_score < threshold` で基幹構造再生成を要求（最大 `max_retries` 回）。しきい値未満のままの場合は最後の結果を返す。

### ステップ64: ステップ63の単体テスト作成
- **ファイル**: `tests/test_entertainment_loop.py`（新規）
- **内容**: `interest_score=85` で1回成功、`interest_score=40` で2回リトライ後最終結果返却をモックで検証。

### ステップ65: `Engine` パイプラインへループ統合
- **ファイル**: `src/backend/engine_plot.py`
- **内容**: プロット生成後、本文執筆の**前**に `run_entertainment_first_loop` を挿入。`ENFORCE_ENTERTAINMENT_FIRST`（ステップ25）が `True` で、かつ最終 `interest_score < threshold` の場合は `RuntimeError("面白さ検証不合格: 基幹構造の再設計が必要")`。

### ステップ66: ステップ65の統合テスト
- **ファイル**: `tests/test_engine_entertainment_gate.py`（新規）
- **内容**: 検証合格で本文執筆へ進む、不合格で `RuntimeError` をモックで検証。

### ステップ67: 検証結果のDB保存処理追加
- **ファイル**: `src/backend/entertainment_loop.py`
- **内容**: ループ終了時に `entertainment_check_log` へ結果をINSERTするリポジトリ呼び出しを追加。

### ステップ68: ステップ67の統合テスト
- **ファイル**: `tests/test_entertainment_loop_persistence.py`（新規）
- **内容**: モックリポジトリでINSERT呼び出しが1回行われることを検証。

---

# Phase 8: 改善案C - UI連携と全体E2E・検証（ステップ69-72）

## 目標
Streamlit UI で「面白さ検証スコア」「尖り保全状況」「感情起点」を可視化し、全フェーズのE2Eテストで品質↔面白さバランスを検証する。

### ステップ69: UI - 感情起点選択サイドバー項目追加
- **ファイル**: `streamlit_app/sidebar.py`
- **内容**: `EMOTIONAL_HOOKS` から `selectbox` を生成し `UIStateStore.selected_desires` の代わりに `selected_emotional_hook` を設定するUI項目を追加。既存の `selected_desires` は後方互換のため残す。

### ステップ70: UI - 尖り保全ダッシュボード追加
- **ファイル**: `streamlit_app/pages_config.py` と該当ページ
- **内容**: `Plot.sharp_edges` と `quality_polish_status` を表示するパネルを追加。`rejected_edge_loss` の場合は警告表示。

### ステップ71: UI - 面白さ検証スコア表示
- **ファイル**: `streamlit_app/pages_config.py` と該当ページ
- **内容**: `entertainment_check_log` の最新スコアを `plotly_chart` でエピソード推移グラフとして表示。`interest_score < 60` は赤色マーカー。

### ステップ72: 全フェーズ統合E2Eテスト
- **ファイル**: `tests/test_full_balance_pipeline_e2e.py`（新規）
- **内容**: モックLLM・モックリポジトリで以下のフルフローを検証:
  1. UI選択 → `EmotionalHookSpec` 構築（Phase 1）
  2. フック注入プロンプトでプロット生成（Phase 2）
  3. tension曲線選択と面白さ優先順序強制（Phase 3）
  4. 尖り3件提案 → `Plot.sharp_edges` 永続化（Phase 4）
  5. 品質監査で角削除シナリオ → `rejected_edge_loss`（Phase 5）
  6. 早期面白さ検証ループ → 興味不足でリトライ → 合格（Phase 6-7）
  7. UI表示項目のデータ存在確認（Phase 8）
  - **期待結果**: 高品質化が尖りを殺さず、面白さ検証不合格時は品質工程へ進まないこと。

---

## 完了定義（Definition of Done）
- [x] Phase 1-3: 感情設計先行インフラ（改善案A）完了
- [x] Phase 4-5: 尖り保全システム（改善案B）完了
- [x] Phase 6-8: 早期面白さ検証ループ（改善案C）完了
- [x] 全72ステップのテストが `pytest` で `PASS`
- [x] `mypy` / `ruff` がエラー0
- [x] 全7本のAlembicマイグレーションがロールバック確認済み
- [x] Phase 8ステップ72の統合E2Eテストが「高品質↔面白さ」バランスを客観的に検証

## バランス設計のシステム的強制ポイント
| 改善案 | 強制箇所 | 強制メカニズム |
|--------|----------|----------------|
| A | `engine_plot.py` ステップ26 | `emotional_hook=None` で `RuntimeError` |
| B | `DeAIAuditor` ステップ45 / `CritiqueAgent` ステップ47 | `check_edges_preserved` → `rejected_edge_loss` |
| C | `engine_plot.py` ステップ65 | `interest_score < threshold` で本文執筆ブロック |

これにより「品質は感情の従属変数」「尖りは品質化で保持」「面白さは品質整備の前に検証」がコードレベルで強制され、人間の注意力に依存しない堅牢なバランス設計が実現する。
