# サブテキスト・コントロールトークン展開 (Subtext Control Tokens) 運用ガイド

## 1. 概要
`subtext_tokens` は、初回LLM生成プロンプトに特殊コントロールトークン（`[CATEGORY:KEY:MODIFIER]`）の出力を促し、後処理（単一パス正規表現展開＋文脈整形）によって行間・沈黙・ト書きへと決定論的に置換するシステムです。LLMの追加API呼び出しは一切発生しません。

## 2. トークンBNF仕様
```bnf
TOKEN    := "[" CATEGORY ":" KEY [":" MODIFIER]* "]"
CATEGORY := "SUBTEXT" | "BEAT" | "ACTION" | "GLANCE" | "PAUSE" | "IRONY" | "INTERNAL"
KEY      := [a-z0-9_]+
MODIFIER := [a-z0-9_]+
```

### 主要トークン例
- `[SUBTEXT:irony]`: 本音と逆の皮肉な定型文と沈黙
- `[SUBTEXT:cold_acceptance]`: 冷ややかな受容と手の震えを隠す動作
- `[BEAT:pause:short]`: 「……」または一拍の沈黙
- `[BEAT:pause:long]`: 重苦しい長い沈黙
- `[ACTION:hide_hands:trembling]`: 震える手を隠す動作
- `[GLANCE:away]`: 視線を逸らす
- `[PAUSE:breath]`: 深く息を吐く・息を呑む
- `[INTERNAL:suppressed_rage]`: 怒りを押し殺す内面動作

## 3. 後処理パイプライン実行順序 (Step 7)
1. **トークン展開 (`TokenExpander`)**: 乱数シード固定による決定論的展開、最大3階層の再帰展開
2. **句読点正規化 (`normalize_punctuation`)**: 全角/半角統一、改行圧縮
3. **クライマックス前ビート確保 (`ensure_beat_before_climax`)**: 感情爆発語の直前に沈黙ビート挿入
4. **説明セリフ圧縮 (`compress_explanatory_dialogue`)**: 3行以上の連続セリフを1行＋ト書きへ圧縮
5. **台詞/ト書き比率調整 (`balance_dialogue_action_ratio`)**: 台詞過多時に安定ビート挿入
6. **同一話者連続台詞マージ (`merge_consecutive_dialogue`)**: 同一話者の連続発話をビート結合
7. **キャラクター口調フィルタ (`apply_speech_patterns`)**: 語尾・口調の最終変換

## 4. 多言語対応とプロンプト共進化検証
- 多言語辞書: `data/subtext/tokens.yaml` (日本語), `tokens.en.yaml` (英語), `tokens.zh.yaml` (中国語)
- 共進化検証: `python scripts/validate_prompt_tokens.py`
- 使用統計レポート: `python scripts/token_usage_report.py`
