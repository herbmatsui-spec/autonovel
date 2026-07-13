# 改善案提案：9つのアプローチ

## 前提条件

本改善案は、分析レポート [WORK_ANALYSIS_REPORT.md](WORK_ANALYSIS_REPORT.md) の結果を元に、機械的な生成においても高品質な作品を提供するための具体的アプローチを提示する。

---

## 改善案 1: 世界観の深層化プロンプトの導入

### 概要

現在の生成プロンプトには舞台設定とキャラクター背景に関する情報が不足している。プロンプトに「世界構築パラメータ」を追加し、地理、歴史、政治体制などの情報を自動的に挿入させる。

### 実装方法

```python
# src/engine/prompts/world_building.py (新規作成)
def build_world_context(genre: str, setting: str) -> str:
    """世界観背景文を生成するプロンプトビルダー"""
    templates = {
        "fantasy": """王国名: {kingdom_name}。政治体制: {government_type}。
        主要民族: {main_race}。宗教: {religion}。技術レベル: {tech_level}。""",
        # ... other genres
    }
    return templates.get(genre, "").format(**context)
```

### 期待効果

- 舞台の説得力が向上し、読者の没入感が増加
- キャラクターの行動に論理的な根拠が生まれる
- シリーズ化した際の設定管理が容易になる

---

## 改善案 2: 五感描写のバランス制御フィルター

### 概要

現在の作品では「視覚」と「精神描写」に偏りがある。LLM 生成時に五感全てを最低1回は使用することを義務付けるフィルターを実装する。

### 実装方法

```python
# src/services/sensory_balance_filter.py (新規作成)
class SensoryBalanceFilter:
    """五感バランスをチェックするフィルター"""
    SENSES = ["視覚", "聴覚", "嗅覚", "触覚", "味覚"]
    
    def check_and_augment(self, text: str) -> str:
        """各感覚の使用回数をカウントし、不足があれば補完プロンプトを挿入"""
        counts = self._count_sensory_words(text)
        for sense, count in counts.items():
            if count == 0:
                text += self._generate_sensory_prompt(sense)
        return text
```

### 期待効果

- 読者の感覚的な没入感が向上
- 文章のリズムと多彩性が生まれる
- 差別化された描写パターンが生成される

---

## 改善案 3: 感情蓄積フェーズ拡張プロンプト

### 概要

カタルシスの効果を最大化するため、感情起点を設定する際に「苦悩蓄積フェーズ」の最低文字数を確保するプロンプトエンジニアリングを実施する。

### 実装方法

```yaml
# prompts/writing/extended_catharsis.yaml
catharsis_prompt:
  minimum_agony_ratio: 0.4  # 感情蓄積フェーズは全体の最低40%を維持
  required_agony_elements:
    - 身体的苦痛の描写
    - 精神的崩壊の過程
    - 外的支援の欠如
    - 絶望の段階的深化
```

### 期待効果

- カタルシス時の感情落差が大きくなり、読者の感動が深まる
- 「展開が急」というフィードバックが減少する
- 物語に「SLOW BURN」的な緊張感が生まれる

---

## 改善案 4: キャラクター深度評価モデル

### 概要

現在の作品では国王ゼノンが「悪役」で終わっている。キャラクターに矛盾した動機や内面挣扎を追加するための評価モデルを作成し、一定の深度スコアに満たない場合は再生成をリクエストする。

### 実装方法

```python
# src/services/character_depth_evaluator.py (新規作成)
class CharacterDepthEvaluator:
    """キャラクターの深度を評価するサービス"""
    
    def evaluate(self, text: str, character_name: str) -> dict:
        """矛盾度、動機明確度、成長軌跡をスコア化"""
        return {
            "contradiction_score": self._calc_contradiction(text, character_name),
            "motivation_clarity": self._calc_motivation(text, character_name),
            "arc_completeness": self._calc_arc(text, character_name),
            "overall_depth": (score1 + score2 + score3) / 3
        }
    
    def requires_regeneration(self, evaluation: dict) -> bool:
        """深度スコアが閾値以下ならTrue"""
        return evaluation["overall_depth"] < 0.6
```

### 期待効果

- 敵キャラクターにも人間味が追加され、物語の複雑さが増す
- 主人公と敵の関係性に皮肉や共感が生まれる
- 読者が「正しいか正しくないか」判断に迷うキャラクター造型が可能に

---

## 改善案 5: 語彙多様性フィードバックループ

### 概要

現在の作品では感情語彙が「苦悩」「絶望」「恐怖」に偏っている。同じ語根や同義語が連続して使用されることを検出し、代替語彙を提案するフィードバックループを実装する。

### 実装方法

```python
# src/services/vocabulary_diversity.py (新規作成)
class VocabularyDiversityAnalyzer:
    """語彙の多様性を 분석하고フィードバック하는サービス"""
    
    def analyze(self, text: str) -> dict:
        """形態素分析を行い、繰り返し率をチェック"""
        return {
            "repeated_word_rate": self._calc_repetition_rate(text),
            "avg_sentence_variety": self._calc_sentence_variety(text),
            "emotion_word_diversity": self._calc_emotion_diversity(text),
            "problematic_repetitions": self._find_repetitions(text)
        }
    
    def suggest_alternatives(self, problematic_word: str) -> list:
        """繰り返し問題の語に対して代替候補を提示"""
```

### 期待効果

- 文章の読みやすさが向上し、同じ語句による疲労感が減少
- より精细な感情表現が可能になる
- 読者の記憶に残りやすいidiosyncraticな表現が生まれる

---

## 改善案 6: 敵対的多声型ナレーションの導入

### 概要

現在の作品は「俺」という一人称で統一されている。物語の途中で視点が敵キャラクターに切り替わる「多声型ナレーション」を導入し、敵視点も同時に描写する。

### 実装方法

```yaml
# prompts/writing/multi_voice_narration.yaml
narration_config:
  enable_pov_switch: true
  switch_triggers:
    - 主人公_actionの直後
    - 感情曲線の転換点
    - 重大なRevelationの後
  min_pov_segments: 2
  max_pov_segments: 4
```

### 期待効果

- 物語に奥行きと緊張感が生まれる
- 読者が複数のキャラクターに感情移入できるようになる
- 「復讐もの」の定番演出である「敵の恐怖」を直接描写できる

---

## 改善案 7: 伏線自動生成・管理システム

### 概要

現在のサンプルは冒頭部のみのため伏線の評価が困難だが、システムとして「本文中に2つ以上の後段で回収される伏線」を自動的に挿入・管理する仕組みを実装する。

### 実装方法

```python
# src/services/foreshadowing_manager.py (新規作成)
class ForeshadowingManager:
    """伏線管理サービス"""
    
    def __init__(self):
        self.foreshadows: list[ForeshadowItem] = []
        self.resolutions: list[ResolutionItem] = []
    
    def insert_foreshadow(self, chapter_num: int, text: str) -> str:
        """伏線として機能するアイテムを本文に埋め込み、マクロ名を記録"""
        # 名前付きエンティティ、シンボル、予言などのパターンを検出
        foreshadow_items = self._extract_symbolic_elements(text)
        for item in foreshadow_items:
            self.foreshadows.append(ForeshadowItem(item=item, insert_point=chapter_num))
        return text
    
    def validate_foreshadow_balance(self, full_text: str) -> bool:
        """伏線と回収のバランスが適切か検証"""
        return len(self.foreshadows) == len(self.resolutions)
```

### 期待効果

- 長編作品になった際の「後から繋がる感」が向上
- 読者の再読欲を刺激する要素が生まれる
- 作品的完成度の高い体験を提供できる

---

## 改善案 8: 感情語彙の感情価（Valence）データベース

### 概要

感情語の「肯定的/否定的」「強さ」を数値化し、カテゴリ別に自動挿入する辞書ベースシステムを構築する。これにより、感情のカーブをより正確に制御できる。

### 実装方法

```python
# src/services/emotion_valence_db.py (新規作成)
EMOTION_VALENCE_DB = {
    "negative_intense": {
        "words": ["絶望", "苦悩", "絶叫", "恐怖", "憤怒", "怨み", "憎悪", "悲嘆"],
        "valence": -0.9,
        "arousal": 0.9
    },
    "negative_mild": {
        "words": ["沈黙", "憂鬱", "寂寥", "後晦", "不安"],
        "valence": -0.4,
        "arousal": 0.3
    },
    "positive_intense": {
        "words": ["歓喜", "恍惚", "至福", "感激", "狂喜"],
        "valence": 0.9,
        "arousal": 0.9
    },
    "positive_mild": {
        "words": ["温もり", "安堵", "平静", "穏やか", "満足"],
        "valence": 0.5,
        "arousal": 0.2
    }
}
```

### 期待効果

- 感情カーブの可视化・数値化管理が可能に
- 意図した感情走向と生成结果的のズレを最小化
- 作家や編集者が感情設計を精緻に行える

---

## 改善案 9: エンド・オブ・チャプタ Hook（掴み）自動生成

### 概要

現在のサンプルは「始まり」のみで構成されている。チャプタ終端に「次への引力」を生成する hook 要素を自動挿入するプロンプトを追加する。

### 実装方法

```yaml
# prompts/writing/chapter_ending_hook.yaml
chapter_ending_config:
  min_hook_elements: 2
  hook_types:
    - cliffhanger: 物語の決着を先延ばしにする
    - revelation: 新たな情報を揭示する
    - question: 読者の疑問を提起する
    - tension_boost: 緊張感を急激に高める
  forbidden_patterns:
    - 完全解決（Next Chapterへの引力がない）
    - 唐突な終結（感情の流れが途中で切れる）
```

### 期待効果

- 読者の「続きを読みたい」心理を最大化
- チャプター間の連続性を確保
- 作品全体の没頭度と読了率が向上

---

## まとめ：優先順位マトリクス

| 優先度 | 改善案 | 実装コスト | 効果 |
|--------|--------|-----------|------|
| **高** | 3. 感情蓄積フェーズ拡張 | 低 | 大 |
| **高** | 9. エンド・オブ・チャプタ Hook | 低 | 大 |
| **高** | 2. 五感バランス制御 | 中 | 中 |
| **中** | 1. 世界観深層化 | 中 | 大 |
| **中** | 4. キャラクター深度評価 | 高 | 中 |
| **中** | 5. 語彙多様性フィードバック | 中 | 中 |
| **低** | 6. 多声型ナレーション | 高 | 中 |
| **低** | 7. 伏線管理システム | 高 | 大（長編時） |
| **低** | 8. 感情Valence DB | 中 | 中 |

---

*提案作成日: 2026-07-11*
*分析方法: 分析レポート [WORK_ANALYSIS_REPORT.md](WORK_ANALYSIS_REPORT.md) に基づいている*