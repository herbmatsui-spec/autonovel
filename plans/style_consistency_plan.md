# Style Consistency Improvement Implementation Plan
# 不十分な点3: 長編トーン・文体のズレ 対策

## 概要
各話の文体統計（平均文長・常体率・ユニーク語数）を算出し、直前5話の移動平均から外れ値を検出する `score_style_consistency` を新設。`world.yaml` に `style_guide` を定義しプロンプト生成時にスタイル制約として注入。外れ話には `polish_tool` で「トーンを基準話に合わせてリライト」フラグを付与し校正対象として再処理。

---

## 実装ステップ (全24ステップ)

### フェーズ1: world.yaml への style_guide 追加

**Step 1**: world.yaml に style_guide セクションを追加
- ファイル: `novel_50ep/world.yaml`
- 追加内容:
```yaml
style_guide:
  tone: "常体"          # または "敬体"
  vocabulary_level: "中級"  # 初級/中級/上級
  avg_sentence_length: 45   # 目標平均文長（文字）
  unique_words_target: 180  # 目標ユニーク語数
  formality: "やや硬め"      # カジュアル/標準/やや硬め/硬い
  sentence_endings:
    - "だ。"
    - "である。"
    - "た。"
  forbidden_endings:
    - "です。"
    - "ます。"
```

**Step 2**: config.py に STYLE_GUIDE_DEFAULT 定数を追加
- ファイル: `novel_50ep/config.py`
- デフォルト値を定義（world.yaml 未設定時のフォールバック用）

---

### フェーズ2: 文体統計計算ユーティリティの新設

**Step 3**: count_chars.py に文体統計関数を追加
- ファイル: `novel_50ep/count_chars.py`
- 新規関数: `calculate_style_stats(text: str) -> StyleStats`
- 戻り値 dataclass `StyleStats`:
  - `avg_sentence_length: float` - 平均文長
  - `plain_form_ratio: float` - 常体率（だ/である/た 文末の割合）
  - `unique_word_count: int` - ユニーク語数（形態素解析なしで簡易実装：単語分割＋重複除去）
  - `sentence_count: int` - 文数

**Step 4**: 簡易単語分割ヘルパー `_split_words(text: str) -> List[str]` を実装
- 正規表現で「ひらがな/カタカナ/漢字/英数字」の連続を単語とみなす簡易実装
- 低性能LLM環境でも動作するよう辞書不要の簡易版

---

### フェーズ3: score_style_consistency の実装

**Step 5**: score_reviewer.py に StyleStats データクラスを追加
- ファイル: `novel_50ep/score_reviewer.py`
- `EpisodeScore` に `style_score: float` と `style_details: Dict[str, str]` を追加

**Step 6**: ScoreReviewer クラスに `score_style_consistency` メソッドを追加
- 引数: `ep: int, text: str, prev_scores: List[EpisodeScore]`
- 処理:
  1. `calculate_style_stats(text)` で当該話の統計を取得
  2. `prev_scores` から直前5話（`ep-5` 〜 `ep-1`）の StyleStats を抽出
  3. 移動平均・標準偏差を計算（各指標ごと）
  4. 当該話が各指標で「移動平均 ± 2σ」外ならペナルティ
  5. スコア = 1.0 - ペナルティ合計（最小0.0）
  6. 詳細情報を `style_details` に格納

**Step 7**: `score_episode` メソッドに style_score を統合
- 重み: 既存4指標の合計を 0.8、style を 0.2 とする（合計1.0）
- `total = (pacing*0.24) + (emotion*0.20) + (world*0.16) + (cliff*0.20) + (style*0.20)`
- `EpisodeScore` に `style_score` と `style_details` を追加格納

**Step 8**: CSV出力ヘッダーに "style" 列を追加
- `writer.writerow(["ep", "pacing", "emotion", "world", "cliff", "style", "total_score", "evaluation"])`

---

### フェーズ4: プロンプト生成へのスタイル制約注入

**Step 9**: generator.py の `_load_world` で style_guide を読み込み保持
- `self.style_guide = world_data.get("style_guide", DEFAULT_STYLE_GUIDE)`

**Step 10**: `_load_prompt_template` または `generate_part` でスタイル制約文を生成
- 新規メソッド: `_build_style_constraint() -> str`
- 出力例:
```
【文体制約】
- 文体: 常体（だ・である調）を厳守。敬体（です・ます）は使用禁止。
- 平均文長: 45文字前後を目安に、長文・短文の極端な偏りを避ける。
- 語彙レベル: 中級程度。難解な専門語・過度な口語は避ける。
- 文末表現: 「だ。」「である。」「た。」を基本とし、「です。」「ます。」は使わない。
```

**Step 11**: `generate_part` のプロンプトフォーマットに `style_constraint` 変数を追加
- `prompt_str = prompt_tmpl.format(..., style_constraint=style_constraint)`
- 各パートのプロンプトテンプレート（part1〜part7）に `{style_constraint}` プレースホルダを追加

**Step 12**: 全7つのプロンプトテンプレートファイルに `{style_constraint}` を追加
- ファイル: `novel_50ep/prompts/part1_symbol.txt` など
- 適切な位置（冒頭や文体指示付近）に挿入

---

### フェーズ5: polish_tool へのリライトフラグ追加

**Step 13**: polish_tool.py に `rewrite_tone_to_baseline` 関数を追加
- 引数: `text: str, baseline_ep: int, baseline_stats: StyleStats`
- 処理:
  1. 基準話（直前5話の中央値に最も近い話、または ep-1）を特定
  2. 基準話の統計を取得
  3. リライト用プロンプトを生成:
```
以下の文章を、基準話（第{baseline_ep}話）の文体に合わせてリライトしてください。

【基準話の文体統計】
- 平均文長: {avg_len:.1f}文字
- 常体率: {plain_ratio:.1%}
- ユニーク語数: {unique_words}語

【リライト指示】
- 文末をすべて常体（だ/である/た）に統一
- 文長を基準話の平均±10%に収める
- 語彙レベルを基準話に合わせる
- 物語の内容・展開は変更しない
```
  4. LLM呼び出し（または mock_generator）でリライト実行
  5. リライト後の文体統計を再計算し、基準話の±1σ以内なら成功

**Step 14**: PolishTool クラスに `polish_style_outlier` メソッドを追加
- 引数: `ep: int, baseline_ep: Optional[int] = None`
- 処理:
  1. スコアファイルから当該話の style_score と style_details を読み取り
  2. style_score < 0.7 なら「文体外れ値」と判定
  3. `rewrite_tone_to_baseline` を呼び出しリライト
  4. 上書き保存＆再検証

**Step 15**: CLI に `--fix-style` オプションを追加
- `parser.add_argument("--fix-style", type=int, nargs="*", help="文体外れ値話数を基準話に合わせてリライト")`
- 実行時: 指定話数（未指定なら全話チェック）に対して `polish_style_outlier` 実行

---

### フェーズ6: バッチ処理・統合

**Step 16**: batch_runner.py に文体チェック・修正ステップを追加
- `batch_runner.py` の生成フロー内で、生成完了後に `ScoreReviewer().score_all()` 呼び出し
- style_score 低い話を検出し、自動で `polish_tool --fix-style` を呼ぶか、レポート出力

**Step 17**: メタデータ（metadata.json）に文体統計を記録
- `generate_episode` 完了時に、当該話の StyleStats を metadata.json に追記
- 形式: `{"ep": 1, "style_stats": {...}}`

**Step 18**: continuity_tracker との連携（任意）
- 文体ズレも「継続性違反」の一種として扱い、tracker.violations に追加
- 既存の `score_episode` の継続性ペナルティに統合

---

### フェーズ7: テスト・検証

**Step 19**: tests/test_novel_50ep.py に文体統計テストを追加
- `calculate_style_stats` の単体テスト
- `score_style_consistency` の単体テスト（既知データで外れ値検出確認）

**Step 20**: 手動検証用スクリプト作成
- `scripts/check_style_consistency.py` 
- 全話の文体統計を可視化（移動平均プロット等）

**Step 21**: 既存エピソードへの適用テスト
- `python -m novel_50ep.score_reviewer --all` でスコア再計算
- `python -m novel_50ep.polish_tool --fix-style` で外れ値修正実行

**Step 22**: 閾値調整・チューニング
- 移動平均ウィンドウ（5話）、外れ値判定閾値（±2σ → ±1.5σ等）を調整
- 重み配分（style 0.2）の妥当性確認

---

### フェーズ8: ドキュメント・仕上げ

**Step 23**: README/ドキュメント更新
- `novel_50ep/BATCH_GUIDE.md` に文体一貫性チェック・修正手順を追記
- `world.yaml` の style_guide 設定例をドキュメント化

**Step 24**: 統合テスト・最終確認
- 全50話生成→スコアリング→文体修正のフルパイプライン実行
- 平均総合スコア 0.90 以上、かつ style_score 全話 0.7 以上を確認

---

## 依存関係図

```
world.yaml (style_guide)
    ↓
config.py (DEFAULT_STYLE_GUIDE)
    ↓
count_chars.py (calculate_style_stats)
    ↓
score_reviewer.py (score_style_consistency) ←─ metadata.json (過去統計)
    ↓
generator.py (promptに style_constraint 注入)
    ↓
polish_tool.py (rewrite_tone_to_baseline / --fix-style)
    ↓
batch_runner.py (統合フロー)
```

---

## 低性能LLM対応のポイント

1. **形態素解析なし**: 正規表現ベースの簡易単語分割でユニーク語数を推定
2. **決定論的計算**: 統計計算はすべてルールベース（LLM不要）
3. **プロンプト注入のみ**: LLMへの指示は「文体制約テキスト」をプロンプトに追加するだけ
4. **リライトもプロンプトベース**: polish_tool のリライトも専用プロンプトでLLMに指示（mock_generatorでも代替可能）
5. **外部依存ゼロ**: MeCab, Janome, Sudachi 等の形態素解析器を一切使用しない

---

## 実装順序の推奨

1. Steps 1-2: 設定追加（最優先・影響範囲小）
2. Steps 3-4: 統計計算基盤（核心ロジック）
3. Steps 5-8: スコアリング統合（既存機能拡張）
4. Steps 9-12: プロンプト注入（生成側対策）
5. Steps 13-15: 校正ツール拡張（事後修正）
6. Steps 16-18: 統合・自動化
7. Steps 19-22: テスト・調整
8. Steps 23-24: ドキュメント・仕上げ