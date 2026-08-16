# シーケンス図 - SpiceGuard 動作フロー

## 概要
テキストから「尖り要素」を自動抽出し、リライト時に保護マーカーを注入・除去する SpiceGuard の内部動作フロー。

```mermaid
sequenceDiagram
    autonumber
    participant Client as 呼び出し元\n(EpisodeRewriter / Pipeline)
    participant SpiceGuard as SpiceGuard
    participant Extractor as SpiceExtractor
    participant PatternReg as PatternRegistry\n(普遍/ジャンル別パターン定義)
    participant Preset as プリセット\n(キャラクター定義)
    participant MarkerInj as SpiceMarkerInjector
    participant PromptBuilder as RewritePromptBuilder
    participant LLM as LLMゲートウェイ

    Note over Client,SpiceGuard: === 1. 抽出フェーズ ===
    Client->>SpiceGuard: extract_spice(text)
    SpiceGuard->>Extractor: extract(text)
    
    Note over Extractor,PatternReg: === 1-1. 普遍パターン抽出 ===
    Extractor->>PatternReg: get_universal_patterns()
    PatternReg-->>Extractor: {unique_metaphor, plot_twist_marker, emotional_raw}
    Extractor->>Extractor: 正規表現マッチ (re.finditer)\n- unique_metaphor: まるで〜ようだ, かのよう\n- plot_twist_marker: キーワード検索 (実は, 真実, 裏切り...)\n- emotional_raw: 胸が締め付けられ, 恐怖が体を...
    Extractor->>Extractor: SpiceElement 生成 (type, text, position, priority, metadata)
    
    Note over Extractor,PatternReg: === 1-2. ジャンル別パターン抽出 ===
    Extractor->>PatternReg: get_genre_patterns(genre)
    PatternReg-->>Extractor: GENRE_PATTERNS[genre] (例: zarma: catharsis_payoff, villain_despair, power_gap)
    Extractor->>Extractor: キーワード検索 (str.find)\n- zarma_catharsis_payoff: ざまぁ, 無双, 圧倒的...\n- zarma_villain_despair: 正規表現 (敵/悪党が顔面蒼白...)\n- zarma_power_gap: 正規表現 (レベル差/圧倒/無効...)
    Extractor->>Extractor: SpiceElement 生成 (type="zarma_catharsis_payoff" 等)
    
    Note over Extractor,Preset: === 1-3. キャラクター固有要素抽出 ===
    Extractor->>Preset: load_preset(genre) → characters.archetypes
    Preset-->>Extractor: {protagonist: {speech_patterns: {forbidden_words, catchphrases}}}
    Extractor->>Extractor: 禁句・キャッチフレーズで検索\n→ type="character_voice", priority="high"
    
    Note over Extractor: === 1-4. 重複除去・ソート ===
    Extractor->>Extractor: _deduplicate_and_sort()\n- (type, text, position) で重複判定 → Set で除去\n- priority_order: critical(0) > high(1) > medium(2) > low(3)\n- 同一 priority なら position 昇順
    Extractor-->>SpiceGuard: List[SpiceElement] (ソート済み)
    SpiceGuard-->>Client: List[SpiceElement]

    Note over Client,MarkerInj: === 2. マーカー注入フェーズ ===
    Client->>SpiceGuard: inject_markers(text, elements)
    SpiceGuard->>MarkerInj: inject(text, elements)
    MarkerInj->>MarkerInj: elements を position 降順でソート (後ろから置換)
    loop 各 element
        MarkerInj->>MarkerInj: 元テキストと一致確認\nif result[pos:pos+len] == elem.text
        MarkerInj->>MarkerInj: marker_id = f"{type}_{pos}"
        MarkerInj->>MarkerInj: result = before + f"<<<SPICE:{marker_id}>>> {target} <<</SPICE>>>" + after
    end
    MarkerInj-->>SpiceGuard: protected_text
    SpiceGuard-->>Client: protected_text

    Note over Client,PromptBuilder: === 3. リライトプロンプト構築 ===
    Client->>SpiceGuard: build_rewrite_prompt(content, improvements, elements)
    SpiceGuard->>PromptBuilder: build(content, improvements, elements)
    PromptBuilder->>MarkerInj: inject(content, elements) (再利用)
    PromptBuilder->>PromptBuilder: プロンプトテンプレート適用
    PromptBuilder-->>SpiceGuard: rewrite_prompt
    SpiceGuard-->>Client: rewrite_prompt

    Note over Client,LLM: === 4. LLMリライト実行 ===
    Client->>LLM: generate_text(rewrite_prompt)
    LLM->>LLMClient: get_client(model)
    LLMClient->>GeminiAPI: HTTPS generateContent
    GeminiAPI-->>LLMClient: rewritten_text
    LLMClient-->>LLM: 正規化
    LLM-->>Client: rewritten_text

    Note over Client,MarkerInj: === 5. マーカー除去フェーズ ===
    Client->>SpiceGuard: clean_output(rewritten_text) / remove_markers()
    SpiceGuard->>MarkerInj: remove(text) / clean_output(text)
    MarkerInj->>MarkerInj: re.sub(r"<<<SPICE:[^>]+>>>|<<</SPICE>>>", "", text)
    MarkerInj-->>SpiceGuard: clean_text
    SpiceGuard-->>Client: final_text
```

## 内部データフロー詳細

### SpiceExtractor 内部処理

```
text (入力文字列)
    │
    ├─ _extract_universal() ──▶ universal_patterns (3種類)
    │     ├─ unique_metaphor: regex finditer
    │     ├─ plot_twist_marker: keyword finditer
    │     └─ emotional_raw: regex finditer
    │
    ├─ _extract_genre() ──▶ genre_patterns (ジャンル×3-4種類)
    │     ├─ keyword-based: str.find (高速)
    │     └─ regex-based: regex finditer
    │
    ├─ _extract_character() ──▶ preset.archetypes
    │     ├─ forbidden_words → type="character_voice"
    │     └─ catchphrases → type="character_voice"
    │
    └─ _deduplicate_and_sort()
          ├─ key=(type, text, position) で Set 除去
          └─ sort by (priority_order, position)
```

### PatternRegistry パターン定義例

```python
# 普遍パターン
UNIVERSAL_PATTERNS = {
    "unique_metaphor": {
        "patterns": [
            r"(?:まるで|まるで|ようだ|かのように|ような)(.{10,60}?)(?:だ|です|。|！)",
            r"(?:かのよう|ごとく|如く)(.{5,40}?)(?:だ|です|。)",
        ],
        "priority": "high",
    },
    "plot_twist_marker": {
        "keywords": ["実は", "真実", "正体", "裏切り", "秘密", "覚醒", "真の", "隠された", "偽り", "罠"],
        "priority": "critical",
    },
    "emotional_raw": {
        "patterns": [
            r"(?:胸が|心が|背筋が|息が|震えが|涙が|熱が|冷や汗が)(?:締め付けられ|凍る|跳ねる|詰まる|止まらない|溢れる|引く|熱くなる|冷たくなる)(.{0,20}?)",
        ],
        "priority": "high",
    },
}

# ジャンル別 (zarma 抜粋)
GENRE_PATTERNS = {
    "zarma": {
        "catharsis_payoff": {
            "keywords": ["ざまぁ", "見返し", "無双", "圧倒的", "完全制圧", "土下座", "謝罪", "恐怖", "絶望", "無様"],
            "priority": "critical",
        },
        "villain_despair": {
            "patterns": [r"(?:敵|悪党|裏切り者|元仲間)(?:の|が)(?:顔面蒼白|青ざめ|震え|叫び|懇願|涙目)"],
            "priority": "high",
        },
        "power_gap": {
            "patterns": [r"(?:レベル|ステータス|戦力|実力)(?:差|圧倒|無効|通用しない|ゴミ|雑魚)"],
            "priority": "high",
        },
    },
    # ... 他8ジャンル
}
```

### CompiledPatternCache (正規表現事前コンパイル)

```python
class CompiledPatternCache:
    def __init__(self):
        self._cache: Dict[str, Dict[str, List[re.Pattern]]] = {}
    
    def get(self, genre: str) -> Dict[str, List[re.Pattern]]:
        if genre not in self._cache:
            self._cache[genre] = self._compile_for_genre(genre)
        return self._cache[genre]
    
    def _compile_for_genre(self, genre: str):
        compiled = {}
        # 普遍パターン
        for ptype, config in UNIVERSAL_PATTERNS.items():
            if "patterns" in config:
                compiled[ptype] = [re.compile(p) for p in config["patterns"]]
        # ジャンル別
        for ptype, config in GENRE_PATTERNS.get(genre, {}).items():
            if "patterns" in config:
                key = f"{genre}_{ptype}"
                compiled[key] = [re.compile(p) for p in config["patterns"]]
        return compiled
```

### パフォーマンス最適化ポイント

| 箇所 | 対策 | 効果 |
|------|------|------|
| キーワード検索 | `str.find` + 事前小文字化 | `re.finditer` より高速 |
| 正規表現 | 事前コンパイル (`re.compile`) | 再利用で高速 |
| 重複除去 | Set + tuple key | O(n) で除去 |
| ソート | priority_order dict + position | O(n log n) |
| マーカー注入 | 逆順ソートで後ろから置換 | 位置ズレ防止・O(n) |
| キャッシュ | CompiledPatternCache (グローバル) | ジャンル毎1回のみコンパイル |

### パフォーマンス目標

- 10,000文字テキスト: 抽出 < 100ms
- メモリ使用量: ジャンル毎 < 5MB (コンパイル済みパターン含む)
- マーカー注入: 要素数 100 個 < 10ms