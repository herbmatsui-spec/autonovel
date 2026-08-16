# シーケンス図 - エピソードリライトフロー (SpiceGuard統合)

## 概要
監査スコアが閾値未満の場合、SpiceGuard を用いて「尖り要素」を保護しながらリライトを行うフロー。

```mermaid
sequenceDiagram
    autonumber
    participant Pipeline as EasyModePipeline
    participant EpRewriter as EpisodeRewriter
    participant SpiceGuard as SpiceGuard
    participant SpiceExtractor as SpiceExtractor
    participant MarkerInjector as SpiceMarkerInjector
    participant PromptBuilder as RewritePromptBuilder
    participant LLM as LLMゲートウェイ
    participant LLMClient as LLMクライアント
    participant GeminiAPI as Gemini API

    Note over Pipeline,EpRewriter: 監査スコア < target_audit_score (95.0) の場合
    
    Pipeline->>EpRewriter: rewrite(content, improvements, spice_elements)
    
    Note over EpRewriter,SpiceExtractor: === Step 1: 尖り要素抽出 (初回のみキャッシュ) ===
    EpRewriter->>SpiceGuard: extract_spice(content)
    SpiceGuard->>SpiceExtractor: extract(content)
    
    Note over SpiceExtractor: === 1. 普遍パターン抽出 ===
    SpiceExtractor->>SpiceExtractor: 正規表現パターンでマッチ\n(unique_metaphor, plot_twist_marker, emotional_raw)
    SpiceExtractor->>SpiceExtractor: キーワード検索\n(実は, 真実, 正体, 裏切り, 覚醒...)
    
    Note over SpiceExtractor: === 2. ジャンル別パターン抽出 ===
    SpiceExtractor->>SpiceExtractor: ジャンル固有キーワード検索\n(zarma_catharsis_payoff: ざまぁ, 無双, 圧倒的...)
    
    Note over SpiceExtractor: === 3. キャラクター固有要素 ===
    SpiceExtractor->>SpiceExtractor: プリセットから禁句・キャッチフレーズ抽出
    
    Note over SpiceExtractor: === 4. 重複除去・優先度ソート ===
    SpiceExtractor->>SpiceExtractor: (type, text, position) で重複除去\npriority: critical > high > medium > low
    SpiceExtractor-->>SpiceGuard: List[SpiceElement]
    SpiceGuard-->>EpRewriter: List[SpiceElement]
    
    Note over EpRewriter,MarkerInjector: === Step 2: マーカー注入 ===
    EpRewriter->>MarkerInjector: inject_markers(content, spice_elements)
    Note over MarkerInjector: 位置逆順でソート → 後ろから置換\n<<<SPICE:type_position>>> text <<</SPICE>>>
    MarkerInjector-->>EpRewriter: protected_content
    
    Note over EpRewriter,PromptBuilder: === Step 3: リライトプロンプト構築 ===
    EpRewriter->>PromptBuilder: build_rewrite_prompt(content, improvements, spice_elements)
    PromptBuilder->>MarkerInjector: inject_markers(content, spice_elements) (再利用)
    PromptBuilder->>PromptBuilder: プロンプト組み立て\n"""
    以下の小説を改善せよ。ただし、<<<SPICE:...>>> で囲まれた部分は
    『絶対に変更するな。一文字も触るな。そこがこの話の『命』だ。』
    
    【改善指示】
    - 改善点1
    - 改善点2
    
    【原文】
    {protected_content}
    
    改善後の本文のみを出力せよ。SPICEマーカーはそのまま残せ。
    """
    PromptBuilder-->>EpRewriter: rewrite_prompt
    
    Note over EpRewriter,LLM: === Step 4: LLMリライト実行 (リトライ付き) ===
    loop 最大3回 (リトライ)
        EpRewriter->>LLM: generate_text(purpose="rewrite", rewrite_prompt)
        LLM->>LLMClient: get_client(model)
        LLMClient->>GeminiAPI: HTTPS generateContent
        alt 成功
            GeminiAPI-->>LLMClient: 改善済みテキスト
            LLMClient-->>LLM: 正規化済みレスポンス
            LLM-->>EpRewriter: rewritten_text
        else 失敗 (タイムアウト/エラー)
            LLM->>LLM: 指数バックオフ待機 (1s, 2s, 3s)
            LLM->>LLMClient: リトライ
        end
    end
    
    Note over EpRewriter,MarkerInjector: === Step 5: マーカー除去 ===
    EpRewriter->>MarkerInjector: clean_markers(rewritten_text)
    Note over MarkerInjector: 正規表現で除去\nr"<<<SPICE:[^>]+>>>|<<</SPICE>>>"
    MarkerInjector-->>EpRewriter: clean_content
    
    EpRewriter-->>Pipeline: final_content
    
    Pipeline->>Pipeline: 再監査 → スコア向上なら完了、未達なら再リライト (最大3回)
```

## SpiceElement データ構造

```python
@dataclass
class SpiceElement:
    type: str              # "zarma_catharsis_payoff", "plot_twist_marker", "character_voice" 等
    text: str              # 元テキスト (例: "ざまぁ見ろ")
    position: int          # 文字位置 (0-indexed)
    priority: str          # "critical" | "high" | "medium" | "low"
    metadata: Dict         # {"keyword": "ざまぁ", "source": "genre", "pattern_type": "catharsis_payoff"}
```

## マーカー形式

```
元: ざまぁ見ろ。実はチートだった。
    ↓ inject_markers()
保護: <<<SPICE:zarma_catharsis_payoff_0>>> ざまぁ見ろ <<</SPICE>>>。<<<SPICE:plot_twist_marker_6>>> 実は <<</SPICE>>>チートだった。
    ↓ LLMリライト (マーカー保持)
改善: <<<SPICE:zarma_catharsis_payoff_0>>> ざまぁ見ろ <<</SPICE>>>。<<<SPICE:plot_twist_marker_6>>> 実は <<</SPICE>>>、全ては計算され尽くしていた。
    ↓ clean_markers()
完成: ざまぁ見ろ。実は、全ては計算され尽くしていた。
```

## 優先度順序と抽出パターン

| Priority | パターン例 | ジャンル |
|---------|-----------|---------|
| critical | zarma_catharsis_payoff (ざまぁ, 無双, 圧倒的) | zarma |
| critical | aku_reijo_flag_avoidance (フラグ, 回避, 折る) | aku_reijo |
| critical | cheat_tensei_system_flavor (スキル習得, ∞, 無限) | cheat_tensei |
| critical | slow_life_sensory_richness (香り, ふわふわ, とろけ) | slow_life |
| critical | dungeon_admin_trap_creativity (罠, ギミック, 落とし穴) | dungeon_admin |
| critical | modern_cheat_tech_metaphor (ルート権限, パッチ, バグ) | modern_cheat |
| critical | ts_tensei_gender_euphoria (可愛い, 美少女, 少女) | ts_tensei |
| critical | vrmmo_reality_bleed (実体化, 侵食, 統合) | vrmmo |
| critical | loop_loop_count (周目, ループ, 回帰) | loop |
| high | plot_twist_marker (実は, 真実, 裏切り, 覚醒) | 全ジャンル共通 |
| high | unique_metaphor (まるで〜ようだ, かのよう) | 全ジャンル共通 |
| high | emotional_raw (胸が締め付けられ, 恐怖が体を) | 全ジャンル共通 |

## リトライ・エラーハンドリング

| 状況 | 動作 |
|------|------|
| LLM タイムアウト | 指数バックオフ (1s, 2s, 3s) で最大3回リトライ |
| LLM 空レスポンス | 同リトライ |
| マーカー除去後も残存 | ログ警告、元テキストで継続 |
| 改善後もスコア未達 | 最大 `max_rewrite_iterations` (デフォルト3) 回まで繰り返し |
| 最後まで未達 | `needs_human_review = True` フラグ立てて継続 |