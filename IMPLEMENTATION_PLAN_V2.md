# 角（Sharp Edge）保全システム 実装計画書 Ver2.0

## 概要

本計画は、LLMによる品質向上後のコンテンツから「角（Sharp Edge）」が正しく保全されているかを検証するシステムを72の小さなステップに分割して実装するためのものである。

**前提**: 低性能なLLMでも実装できるように、各ステップは独立して検証可能で依存関係を明示する。

---

## 前提知識（実装前に理解しておくこと）

### 「角（Sharp Edge）」とは
- 物語の核となる要素（プロット тон, キャラクター設定, 感情的な訴求点）
- 品質向上ステップで誤って削除されやすい部分
- 偽陽性（false positive）検出が課題

### 既存の問題
1. `description[:20]` で角を検出するため、説明文の冒頭20文字が類似すると誤検出
2. 低性能LLMでは意味的類似度計算のコストが高い
3. 非ASCIIテキスト（日本語等）対応が不十分

### 解決策のアーキテクチャ
```
Step 1-20: モデル拡張（key_phrase追加）
Step 21-40: プロンプト・テンプレート更新
Step 41-60: 保全チェック実装
Step 61-72: テスト・統合
```

---

## フェーズ1: モデル定義（Step 1-20）

### Step 1: SharpEdgeSpecモデルの場所を確認する
- ファイル: `src/models/sharp_edge.py`
- タスク: 既存の `SharpEdgeSpec` クラスを見つける
- 検証: ファイルを読んで class 定義を確認する

### Step 2: SharpEdgeSpecの既存フィールドを確認する
- タスク: 既存のフィールドを確認する
  - `edge_type`: str
  - `description`: str (max_length=200)
  - `preserve_on_quality_polish`: bool
- 検証: 既存の Pydantic モデルが動作することを確認

### Step 3: key_phraseフィールドを定義する（暫定版）
- 追加するフィールド:
  ```python
  key_phrase: str = Field(default="", description="本文から直接引用した20文字以内のキーフレーズ")
  ```
- 検証: `SharpEdgeSpec(key_phrase="test")` でインスタンス作成できる

### Step 4: key_phraseのmax_length validationを追加する
- `Field(max_length=20)` を設定
- 検証: 21文字以上で ValidationError が発生することを確認

### Step 5: key_phraseのカスタム validatorを追加する
- `field_validator("key_phrase")` で 20文字超過時に警告ではなくエラーを出す
- 検証: 21文字以上で ValueError が発生することを確認

### Step 6: edge_typevalidatorとの協調を確認する
- `edge_type_must_be_known` validatorが正しく動作することを確認
- 検証: 未知のedge_typeで ValueError が発生することを確認

### Step 7: edge_type whitelistを確認する
- ファイル: `config/sharp_edge_vocabulary.py`
- `SHARP_EDGE_TYPES` set に許可された種類が定義されていることを確認
- 検証: 主要なedge_type（protagonist_flaw, ending_pullback等）が含まれる

### Step 8: SharpEdgeSpecのimportを確認する
- `from pydantic import BaseModel, Field, field_validator` が存在すること
- `from config.sharp_edge_vocabulary import SHARP_EDGE_TYPES` が存在すること
- 検証: 相互参照エラーがない

### Step 9: SharpEdgeSpecの基本テストを書く
- テストファイル: `tests/test_sharp_edge.py`（既存）
- `test_key_phrase_default_empty`: key_phrase のデフォルトが空文字
- `test_key_phrase_20_chars_ok`: 20文字ちょうどでエラーなし
- `test_key_phrase_21_chars_raises`: 21文字でエラー発生
- 検証: 3テスト 모두 통과

### Step 10: preserve_on_quality_polishvalidatorの動作を確認する
- `warn_if_not_preserved` validatorがwarningログを出力すること
- 検証: `preserve_on_quality_polish=False` でログ出力される

### Step 11: SharpEdgeSpecのdescriptionフィールドmax_lengthを確認する
- `max_length=200` が設定されていること
- 検証: 201文字以上で ValidationError

### Step 12: Edge type毎の仕様を文書化する（メモ）
- `config/sharp_edge_vocabulary.py` に各edge_typeの説明コメントを追加
- これは実装ではなく文書化（スキップ可能）

### Step 13: モデル全体のimport sortを確認する
- `ruff check src/models/sharp_edge.py --select I001`
- 検証: I001 エラーがない

### Step 14: SharpEdgeSpecモデルのreprを確認する
- `repr(SharpEdgeSpec(...))` で key_phrase が表示されることを確認
- 検証: デバッグ時にkey_phraseが見える

### Step 15: SharpEdgeSpecのdict変換を確認する
- `model.model_dump()` でkey_phraseが含まれること
- 検証: JSONシリアライズ時にkey_phraseがに出る

### Step 16: Edge type blacklist應 tosureを追加する
- 無効なedge_typeが渡された時のエラーメッセージを確認する
- 検証: `edge_type_must_be_known` のエラーメッセージが適切

### Step 17: 複合インスタンス作成テスト
- 全てのフィールドを設定したSharpEdgeSpecを作成する
- `edge_type="protagonist_flaw", description="...", key_phrase="...", preserve_on_quality_polish=True`
- 検証: インスタンス作成成功

### Step 18: Edge case - 空文字key_phrase
- `key_phrase=""` でインスタンス作成
- 検証: エラーなく作成可能

### Step 19: Edge case - 空白-only key_phrase
- `key_phrase="   "` でインスタンス作成（空白のみ）
- 検証: 空白のみも許容（strip後のEmpty判定は呼出側で）

### Step 20: フェーズ1のまとめテスト
- `tests/test_sharp_edge.py` 全体を再実行
- 検証: 10/10 tests passed

---

## フェーズ2: パース・テンプレート（Step 21-40）

### Step 21: _parse_sharp_edges関数の場所を確認
- ファイル: `src/backend/engine_plot.py`
- タスク: `_parse_sharp_edges` 関数を見つける
- 検証: 関数定義があることを確認

### Step 22: _parse_sharp_edgesの基本動作を確認する
- 空文字列 `""` を渡した場合、空リストが返る
- `None` を渡した場合、空リストが返る
- 検証: テスト確認

### Step 23: _parse_sharp_edgesにkey_phrase extractionを追加する
- 追加コード:
  ```python
  key_phrase = item.get("key_phrase", "").strip()
  if len(key_phrase) > 20:
      key_phrase = key_phrase[:20]
  ```
- 検証: 20文字超過時に切り詰められる

### Step 24: key_phrase_warningログを追加する
- 20字超過時に logger.warning を出力
- 検証: 超過時にログに出る

### Step 25: SharpEdgeSpec生成時にkey_phraseを渡す
- `_parse_sharp_edges` 内の `SharpEdgeSpec(...)` に `key_phrase=key_phrase` を追加
- 検証: key_phraseが正しく設定されたSharpEdgeSpecが返る

### Step 26: edge_type whitelistチェックの動作確認
- 未知のedge_typeが渡された場合にそのitemがスキップされること
- 検証: `edge_type="invalid"` のアイテムがparsedリストに入らない

### Step 27: descriptionのtrim確認
- `description = item.get("description", "").strip()` が動作すること
- 検証: 前後空白が取り除かれる

### Step 28: preserve_on_quality_polishのデフォルト確認
- `item.get("preserve_on_quality_polish", True)` が動作すること
- 検証: 指定なし時はTrue

### Step 29: JSON parsing error handlingの確認
- 不正なJSONを渡した場合に空リストが返ること
- 検証: 例外が出ない

### Step 30: SHARP_EDGE_PROPOSAL_TEMPLATEの場所を確認
- ファイル: `prompts/plotting.py`
- `SHARP_EDGE_PROPOSAL_TEMPLATE` テンプレート変数を見つける
- 検証: テンプレート定義がある

### Step 31: テンプレートに変数注入部分を確認する
- `plot_summary` 等の変数がテンプレートに含まれていること
- 検証: テンプレートをrenderして確認

### Step 32: テンプレートにkey_phrase必須説明を追加する
- テンプレート内に以下を追加:
  ```
  - key_phrase: 本文から直接引用した20文字以内の句。品質管理後も同一の字句が保持されること。
  ```
- 検証: テンプレートを更新

### Step 33: few-shot examplesにkey_phrase 포함を追加
- 既存のfew-shot例に `key_phrase` フィールドを追加
- 日本語・非ASCII文字の例を含める
- 検証: few-shot例でkey_phraseのフォーマットが分かる

### Step 34: _parse_sharp_edgesのテストファイルを確認する
- ファイル: `tests/test_engine_sharp_edge_proposal.py`
- `TestParseSharpEdges` クラスを見つける
- 検証: テストが存在

### Step 35: key_phrase handlingテストを追加する
- `test_key_phrase_handling`:
  - key_phraseあり → そのまま保持
  - key_phraseなし → 空文字
  - key_phrase20字超過 → 20字に切り詰め
  - key_phrase空白のみ → trim後の空文字
- 検証: テストパス

### Step 36: unknown edge type skipテストを確認する
- `test_unknown_edge_type_skips` が動作すること
- 検証: テストパス

### Step 37: resolve_sharp_edges関数の確認
- `_parse_sharp_edges` を呼び出している `resolve_sharp_edges` を確認
- `PlotDbModel` から `sharp_edges_json` を取得して `_parse_sharp_edges` を呼ぶ
- 検証: 関数がある

### Step 38: resolve_sharp_edgesのNone handling確認
- `plot=None` の場合に空リストが返る
- 検証: テスト確認

### Step 39: engine_plot.pyのimport順序を確認する
- `ruff check src/backend/engine_plot.py --select I`
- 検証: I001 がない（または自動 fix 可能）

### Step 40: フェーズ2のまとめテスト
- `tests/test_engine_sharp_edge_proposal.py` 全体を再実行
- 検証: 5/5 tests passed

---

## フェーズ3: 保全チェック実装（Step 41-60）

### Step 41: check_edges_preserved関数の場所を確認
- ファイル: `src/backend/sharp_edge_preserver.py`
- `check_edges_preserved` 関数を見つける（同期バージョン）
- 検証: 関数定義がある

### Step 42: check_edges_preservedの基本動作を確認
- `edges=[]` の場合、空リストが返る
- 検証: テスト確認

### Step 43: check_edges_preservedにkey_phrase checkを追加する
- 追加コード:
  ```python
  key_phrase = edge.key_phrase.strip() if edge.key_phrase else ""
  if key_phrase:
      if key_phrase.lower() in after_content.lower():
          preserved = True
  ```
- 検証: key_phrase一致時にpreserved判定

### Step 44: description[:20] fallbackを追加する
- key_phraseが空または不一致の場合、`description[:20]` でチェック
- 検証: key_phrase 없을時 description[:20] で判定

### Step 45: 大文字小文字を区別しない matching実装
- `after_content.lower()` と `key_phrase.lower()` で比較
- 検証: 大文字小文字不同的 case でも一致

### Step 46: 空白正規化の動作確認
- `key_phrase.strip()` で前後の空白を削除して比較
- 検証: `key_phrase="  余韻  "` でも `"余韻"` に一致

### Step 47: check_edges_preserved戻り値の確認
- 削除されたedgeのみを含むリストを返す
- 保全されたedge は含まない
- 検証: テスト確認

### Step 48: check_edges_preservedのログ追加
- 各判定結果を logger.debug で出力
- 検証: debugログが出る

### Step 49: _check_string_onlyメソッドの場所を確認
- `SemanticEdgePreserver` クラス内の `_check_string_only` を見つける
- 検証: メソッド定義がある

### Step 50: _check_string_onlyの内容を確認
- Step 43-48と同じロジック（key_phrase優先、description[:20] fallback）
- 検証: sync版とロジック同一

### Step 51: SemanticEdgePreserver.__init__params確認
- `semantic_cache`, `similarity_threshold`, `use_semantic`, `use_ngram_fallback` パラメータ
- 検証: パラメータが存在

### Step 52: SemanticEdgePreserver.check_edges_preservedの確認
- async メソッド `check_edges_preserved(before, after, edges)` が2つのリストを返す
- `return semantic_lost, string_lost`
- 検証: async メソッドが存在

### Step 53: string match priorityの確認
- `_check_string_only` がstring_lost を返す
- 検証: string match で失われたもののみ

### Step 54: semantic similarity checkの確認
- `semantic_cache` が None でない場合、`_semantic_compare` を呼ぶ
- 検証: semantic similarity計算がある

### Step 55: _semantic_compareの基本動作確認
- key_phraseとafter_contentの類似度を計算
- しきい値（similarity_threshold）未満なら lost に追加
- 検証: テスト確認

### Step 56: N-gram fallback確認
- `semantic_cache` が None または similarity計算失敗時、`compute_ngram_similarity` を呼ぶ
- 検証: N-gram類似度が返る

### Step 57: compute_ngram_similarity関数の場所を確認
- ファイル: `src/backend/engine_utils.py`
- 関数定義がある
- 検証: 関数がある

### Step 58: N-gram algorithm実装確認
- Jaccard係数ベース（文字n-gram集合の交集/聯集）
- 検証: 同一テキストで1.0、関係ないテキストで低いスコア

### Step 59: use_semantic flagの確認
- `use_semantic=False` の場合、semantic check をスキップ
- 検証: string matchのみ実行

### Step 60: フェーズ3のまとめテスト
- `tests/test_sharp_edge_preserver.py` 全体を再実行
- 検証: 19/19 tests passed

---

## フェーズ4: N-gram類似度（Step 61-65）

### Step 61: N-gram実装の詳細確認
- 文字単位のn-gram（bi-gram または tri-gram）生成
- set(['今日', '日の', 'の天', ...]) のように分割
- 検証: compute_ngram_similarity 動作確認

### Step 62: compute_ngram_similarityの基本テスト
- `test_identical_text_returns_one`: 同一テキスト → 1.0
- `test_empty_input_returns_zero`: 空入力 → 0.0
- `test_unrelated_text_low_score`: 関係なし → 低スコア
- `test_partial_overlap_mid_score`: 一致あり → 中間スコア
- 検証: 4テスト 모두 통과

### Step 63: N-gram performance確認
- 長いテキスト（1000文字程度）でも処理できること
- 検証: 実行時間が許容範囲内（1秒以下目安）

### Step 64: N-gram Unicode対応確認
- 日本語テキストでも正しくn-gram生成されること
- 検証: bi-gram分割が文字単位で動作

### Step 65: N-gram fallback 使用確認
- `SemanticEdgePreserver(use_semantic=True, use_ngram_fallback=True, semantic_cache=None)` で動作
- 検証: N-gram類似度が返る

---

## フェーズ5: DI・設定・統合（Step 66-72）

### Step 66: settings.tomlにedge_preservation設定を追加
- 追加場所: `config/settings.toml`
- 追加内容:
  ```toml
  [quality.edge_preservation]
  enabled = true
  similarity_threshold = 0.75
  use_ngram_fallback = true
  ```
- 検証: TOMLとして不正でない

### Step 67: GlobalConfigModel更新確認
- `schemas/config.py` に `EdgePreservationConfig` モデルがある
- `GlobalConfigModel` に `edge_preservation` フィールドがある
- 検証: モデルが定義されている

### Step 68: DIコンテナ登録確認
- `src/core/container.py` に `edge_preserver` 登録がある
- `SemanticEdgePreserver` インスタンスがコンテナにある
- 検証: コンテナから解決できる

### Step 69: DeAIAuditorでのSemanticEdgePreserver使用確認
- `src/backend/engine_critique.py` の `DeAIAuditor` が `edge_preserver` を使用
- 検証: `audit()` メソッドで使用されている

### Step 70: CritiqueAgentでのSemanticEdgePreserver使用確認
- `src/backend/engine_critique.py` の `CritiqueAgent` が `edge_preserver` を使用
- 検証: agent内でedge_preserverが呼ばれている

### Step 71: import順序Lint修正
- `ruff check src/agents/audit.py --fix --select I,F`
- 検証: F401 (unused import), I001 (乱れたimport) が解消

### Step 72: 全テストスイート実行・最終確認
- `python -m pytest tests/test_sharp_edge.py tests/test_sharp_edge_preserver.py tests/test_engine_sharp_edge_proposal.py -v`
- 検証: 全34テスト passed

---

## 付録: テスト早見表

| テスト | 対象ファイル | 期待 |
|--------|-------------|------|
| SharpEdgeSpec作成 | tests/test_sharp_edge.py | 10/10 passed |
| key_phrase parsing | tests/test_engine_sharp_edge_proposal.py | 5/5 passed |
| check_edges_preserved | tests/test_sharp_edge_preserver.py | 19/19 passed |

## 付録: ファイル別担当表

| ファイル | 担当ステップ |
|---------|------------|
| src/models/sharp_edge.py | Step 1-20 |
| config/sharp_edge_vocabulary.py | Step 7 |
| src/backend/engine_plot.py | Step 21-40 |
| prompts/plotting.py | Step 30-33 |
| src/backend/sharp_edge_preserver.py | Step 41-60 |
| src/backend/engine_utils.py | Step 61-64 |
| src/backend/engine_critique.py | Step 69-70 |
| src/agents/audit.py | Step 71 |
| config/settings.toml | Step 66 |
| schemas/config.py | Step 67 |
| src/core/container.py | Step 68 |

## 付録: 既知の既存問題（未対応）

以下のlint警告は本件Scope外：
- F821 `Undefined name 'EntertainmentCheckResult'` (engine_plot.py:189) → 他ファイルで定義済み、まだ参照なし
- E701 `Multiple statements on one line` (engine_utils.py:107,112,118) → N-gram実装の既存スタイル
- E402 `Module level import not at top of file` (engine_utils.py:148) → 条件付きimportの既存パターン

---

## 計画遂行のヒント

1. **1日1ステップ**: 72ステップ全てを1日で終わらせず、毎日数ステップずつ進める
2. **各ステップ後にテスト**: 失敗したらそのステップをに戻す
3. **低性能LLM向け**: 各ステップは1つのファイル、少数の変更のみを原則とする
4. **依存関係を重視**: フェーズ1→2→3→4→5の順に進む（前のステップが完了してから次へ）
5. **テストは各フェーズ末**: フェーズ途中でテストせず、フェーズ完了時にまとめてテスト