# 新改善案 48ステップ実装計画

## 概要

改善案 #4「快感キーワードの多様化」と改善案 #5「読者反応の擬似シミュレーション」を、低性能LLMでも実装可能な粒度（1ステップ＝1ファイル・1関数レベル）に分解した実装計画。

---

## 改善案 #4: 快感キーワードの多様化（Steps 1-24）

### Step 1: 新規 `config/pleasure_vocabulary.py` — 基本、快感情語彙ファイル作成

**対象ファイル**: 新規 `config/pleasure_vocabulary.py`

**内容**:

```python
"""
config/pleasure_vocabulary.py
心理的快感を表現する語彙集モジュール。

「絶望」「震える」以外に、読者の快感を喚起する心理表現を
多様に定義する。
"""
from typing import Dict, List

# PLEASURE_KEYWORDS: 快感・多幸感・陶酔を表現する基本語彙
PLEASURE_KEYWORDS = [
    "陶酔",
    "多幸感",
    "恍惚",
    "恍惚感",
    "恍惚とした感覚",
    "至福",
    "至福感",
    " bliss ",
    "恍惚の域",
    "天国",
    "天上の喜び",
    "官能的恍惚",
    "陶然",
    "有頂天",
    "心が弾む",
    "血が騒ぐ",
    "息が詰まる",
    "思考が溶ける",
    "世界が眩しい",
    "体が軽い",
    "時が止まる",
    "世界が遠のく",
    "思考が跳ねる",
    "臓々が躍る",
    "手足が酥ける",
]

# EMOTIONAL_PLEASURE_TEMPLATES: 感情的な快感情のテンプレート
EMOTIONAL_PLEASURE_TEMPLATES = [
    "心の奥から込み上げる温かさ",
    "胸が熱くなる感覚",
    "意識が浮遊する",
    "世界が柔らかく濾過される",
    "他者の存在が宇宙より広く感じる",
    "時間軸が歪む",
    "自己溶解感",
    "宇宙との一体化",
    "生死の境を超える感覚",
    "純粋な喜びだけの状態",
    "言葉にならない充足",
    "抗えない開放感",
    "抗えない没入",
    "抗えない没入感",
    "抗えない高揚",
    "抗えない陶酔",
]

# TACTILE_PLEASURE_TEMPLATES: 触感ベースの快感情テンプレート
TACTILE_PLEASURE_TEMPLATES = [
    "肌が粟立つ",
    "肌が燻る",
    "体が痙攣する",
    "手足が絡まる",
    "体が沈む",
    "体が浮く",
    "臓物が躍る",
    "背筋が走る",
    "腰椎が跳ねる",
    "首筋が熱を帯びる",
]

# DIVERSE_PLEASURE_CATEGORIES: 快感の多様性カテゴリ
DIVERSE_PLEASURE_CATEGORIES: Dict[str, List[str]] = {
    "sublimation": [
        "昇華",
        "純化",
        "洗脳",
        "恍惚状態",
        "宗教的恍惚",
        "芸術的恍惚",
        "美的恍惚",
        "詩的恍惚",
    ],
    "tension_release": [
        "緊張の解放",
        "抗えない開放",
        "検索結果",
        "溜飲の低下",
        "塊が降りる",
        "肩の力が抜ける",
        "腰が砕ける",
    ],
    "intimacy_pleasure": [
        "親密の喜び",
        "繋がりの深さ",
        "心を開ける",
        "壁が崩れる",
        "距離がゼロになる",
        "呼吸が同期する",
        "心臓が同じリズムを刻む",
    ],
    "surrender_pleasure": [
        "降伏の快楽",
        "抗えない甘受",
        "抗えない身を委ねる",
        "抗えない隷属",
        "抗えない隷属の喜び",
        "抗えない傾倒",
        "抗えない信頼",
    ],
    "transgression_pleasure": [
        "禁忌を踏み越える快感",
        "背徳感の逆利用",
        "罪恶感の甘さ",
        "風險を冒す快感",
        "禁止された喜び",
        "抗えない誘惑",
        "抗えない深淵",
    ],
    "ecstasy_diversity": [
        "神秘的恍惚",
        "音楽的恍惚",
        "身体的恍惚",
        "精神的恍惚",
        "官能的恍惚",
        "宇宙的恍惚",
        "存在的恍惚",
        "空虚の恍惚",
        "充溢の恍惚",
    ],
}

__all__ = [
    "PLEASURE_KEYWORDS",
    "EMOTIONAL_PLEASURE_TEMPLATES",
    "TACTILE_PLEASURE_TEMPLATES",
    "DIVERSE_PLEASURE_CATEGORIES",
]
```

**確認**: `python -c "from config.pleasure_vocabulary import PLEASURE_KEYWORDS, EMOTIONAL_PLEASURE_TEMPLATES, TACTILE_PLEASURE_TEMPLATES, DIVERSE_PLEASURE_CATEGORIES; print(len(PLEASURE_KEYWORDS), len(EMOTIONAL_PLEASURE_TEMPLATES), len(TACTILE_PLEASURE_TEMPLATES), len(DIVERSE_PLEASURE_CATEGORIES))"` で 25/20/10/6 を確認。

---

### Step 2: 新規 `src/services/pleasure_vocabulary_selector.py` — 語彙選択サービス

**対象ファイル**: 新規 `src/services/pleasure_vocabulary_selector.py`

**内容**:

```python
"""
src/services/pleasure_vocabulary_selector.py
快感語彙を選択・提供するサービス。
"""
import random
from typing import Dict, List, Optional
from config.pleasure_vocabulary import (
    PLEASURE_KEYWORDS,
    EMOTIONAL_PLEASURE_TEMPLATES,
    TACTILE_PLEASURE_TEMPLATES,
    DIVERSE_PLEASURE_CATEGORIES,
)


class PleasureVocabularySelector:
    """快感語彙を選択するサービス"""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def select_keywords(self, count: int = 3) -> List[str]:
        """基本快感を示すキーワードをランダム選択する。"""
        return random.choices(PLEASURE_KEYWORDS, k=count)

    def select_emotional_templates(self, count: int = 2) -> List[str]:
        """感情的快感情テンプレートをランダム選択する。"""
        return random.choices(EMOTIONAL_PLEASURE_TEMPLATES, k=count)

    def select_tactile_templates(self, count: int = 2) -> List[str]:
        """触感ベースの快感情テンプレートをランダム選択する。"""
        return random.choices(TACTILE_PLEASURE_TEMPLATES, k=count)

    def select_from_category(self, category: str, count: int = 2) -> List[str]:
        """指定カテゴリの快感情語彙をランダム選択する。"""
        bank = DIVERSE_PLEASURE_CATEGORIES.get(category, [])
        if not bank:
            return []
        return random.choices(bank, k=min(count, len(bank)))

    def select_all_categories(self, count_per_category: int = 1) -> Dict[str, List[str]]:
        """全カテゴリから均等選択する。"""
        return {
            cat: self.select_from_category(cat, count_per_category)
            for cat in DIVERSE_PLEASURE_CATEGORIES.keys()
        }

    def get_diverse_pleasure_set(self, intensity: int = 3) -> Dict[str, List[str]]:
        """
        強度に応じた多様性ある快感語彙セットを返す。

        intensity: 1-5 の強度パラメータ
            1-2: 控えめ（sublimation, tension_release 中心）
            3: 中程度（全カテゴリ均等）
            4-5: 強度（ecstasy_diversity, transgression_pleasure 中心）
        """
        if intensity <= 2:
            categories = ["sublimation", "tension_release", "intimacy_pleasure"]
            counts = [3, 3, 2]
        elif intensity == 3:
            categories = list(DIVERSE_PLEASURE_CATEGORIES.keys())
            counts = [2] * len(categories)
        else:
            categories = ["ecstasy_diversity", "transgression_pleasure", "surrender_pleasure", "intimacy_pleasure"]
            counts = [3, 3, 2, 2]

        result = {
            "keywords": self.select_keywords(min(5, intensity * 2)),
            "emotional": self.select_emotional_templates(min(3, intensity)),
            "tactile": self.select_tactile_templates(min(3, intensity)),
            "categories": {
                cat: self.select_from_category(cat, cnt)
                for cat, cnt in zip(categories, counts)
            },
        }
        return result
```

---

### Step 3: `config/pleasure_vocabulary.py` — `__all__` への追加確認

**対象ファイル**: `config/pleasure_vocabulary.py`

**変更内容**:
`__all__` に以下の3つを追記確認する。

```python
__all__ = [
    "PLEASURE_KEYWORDS",
    "EMOTIONAL_PLEASURE_TEMPLATES",
    "TACTILE_PLEASURE_TEMPLATES",
    "DIVERSE_PLEASURE_CATEGORIES",
    "get_pleasure_vocabulary",
]
```

---

### Step 4: 新規 `config/pleasure_vocabulary.py` — `get_pleasure_vocabulary` 関数追加

**対象ファイル**: `config/pleasure_vocabulary.py`

**変更内容**:
ファイル末尾に以下を追加する。

```python
def get_pleasure_vocabulary(intensity: int = 3) -> Dict[str, List[str]]:
    """強度に応じた快感語彙を取得するユーティリティ関数。"""
    if intensity <= 2:
        return {
            "keywords": [k for k in PLEASURE_KEYWORDS if k in ["陶酔", "多幸感", "至福", "恍惚", " Bliss "]],
            "emotional": EMOTIONAL_PLEASURE_TEMPLATES[:5],
            "tactile": TACTILE_PLEASURE_TEMPLATES[:3],
        }
    elif intensity == 3:
        return {
            "keywords": PLEASURE_KEYWORDS[:15],
            "emotional": EMOTIONAL_PLEASURE_TEMPLATES[:10],
            "tactile": TACTILE_PLEASURE_TEMPLATES[:5],
        }
    else:
        return {
            "keywords": PLEASURE_KEYWORDS,
            "emotional": EMOTIONAL_PLEASURE_TEMPLATES,
            "tactile": TACTILE_PLEASURE_TEMPLATES,
        }
```

---

### Step 5: `src/engine/prompts/erotic_specialist.py` — 快感語彙選択のインポート追加

**対象ファイル**: `src/engine/prompts/erotic_specialist.py`

**変更内容**:
ファイル冒頭（既存の import 群の後）に以下を追加する。

```python
from config.pleasure_vocabulary import get_pleasure_vocabulary
```

または import 群の最後に追加する。

---

### Step 6: `src/engine/prompts/erotic_specialist.py` — `build_scene_prompt` に快感語彙注入

**対象ファイル**: `src/engine/prompts/erotic_specialist.py`

**変更内容**:
`build_scene_prompt` メソッド内で、プロンプトテンプレートに快感語彙を挿入する箇所を見つける。既存の `desire_level` 等の変数注入後に以下を追加する。

```python
# 快感語彙の多様性注入
pleasure_vocab = get_pleasure_vocabulary(intensity=context.get("intensity", 3))
pleasure_section = f"""
【快感表現の多様性ガイド】
基本快感情語彙: {', '.join(pleasure_vocab['keywords'])}
感情的快感情: {', '.join(pleasure_vocab['emotional'])}
触感的快感情: {', '.join(pleasure_vocab['tactile'])}
"""
prompt += pleasure_section
```

**注意**: 具体的な挿入位置はファイルの現在構造を確認する。`context` 辞書に `intensity` キーが存在しない場合はデフォルト値 3 を使う。

---

### Step 7: `prompts/erotic/scene_templates.py` —快感テンプレートセクション追加

**対象ファイル**: `prompts/erotic/scene_templates.py`

**変更内容**:
`SCENE_TEMPLATE_BUILD` または該当テンプレートに以下のセクションを追加する。

```python
# scene_templates.py 内の該当テンプレートに追記
PLEASURE_EXPRESSION_GUIDE = """
【快感表現の多様性について】
以下の表現を반복せず、 文脈に応じて使い分けてください:
- 陶酔、恍惚、至福、有頂天、 bliss （高揚感）
- 緊張の解放、块的低下、肩の力が抜ける（緊張緩慢型快感）
- 親密の喜び、心を開ける、呼吸の同期（繋がり型快感）
- 抗えない甘受、身を委ねる、隷属の喜び（降伏型快感）
- 禁忌を踏み越える快感、背徳感の逆利用（禁忌侵犯型快感）
"""
```

**確認**: テンプレート定数に `PLEASURE_EXPRESSION_GUIDE` が含まれるようにし、生成プロンプトに включён されることを確認する。

---

### Step 8: `src/engine/prompts/erotic_specialist.py` — `build_aftercare_prompt` への快感語彙追加

**対象ファイル**: `src/engine/prompts/erotic_specialist.py`

**変更内容**:
`build_aftercare_prompt` メソッド内（もし存在すれば）に、快感情後の余韻としての快感語彙を追加する。

```python
# aftercare 用の快感語彙（控えめ）
aftercare_pleasure = get_pleasure_vocabulary(intensity=2)
aftercare_section = f"""
【余韻の快感情ガイド】
- {', '.join(aftercare_pleasure['emotional'][:3])}
- {', '.join(aftercare_pleasure['tactile'][:2])}
"""
prompt += aftercare_section
```

---

### Step 9: 新規 `tests/test_pleasure_vocabulary.py` — 基本テスト

**対象ファイル**: 新規 `tests/test_pleasure_vocabulary.py`

**内容**:

```python
"""tests/test_pleasure_vocabulary.py"""
import pytest
from config.pleasure_vocabulary import (
    PLEASURE_KEYWORDS,
    EMOTIONAL_PLEASURE_TEMPLATES,
    TACTILE_PLEASURE_TEMPLATES,
    DIVERSE_PLEASURE_CATEGORIES,
    get_pleasure_vocabulary,
)


def test_pleasure_keywords_not_empty():
    assert len(PLEASURE_KEYWORDS) >= 20


def test_emotional_templates_not_empty():
    assert len(EMOTIONAL_PLEASURE_TEMPLATES) >= 15


def test_tactile_templates_not_empty():
    assert len(TACTILE_PLEASURE_TEMPLATES) >= 8


def test_diverse_pleasure_categories_count():
    assert len(DIVERSE_PLEASURE_CATEGORIES) == 6


def test_get_pleasure_vocabulary_intensity_1():
    vocab = get_pleasure_vocabulary(intensity=1)
    assert "keywords" in vocab
    assert "emotional" in vocab
    assert "tactile" in vocab
    assert len(vocab["keywords"]) <= 5


def test_get_pleasure_vocabulary_intensity_3():
    vocab = get_pleasure_vocabulary(intensity=3)
    assert len(vocab["keywords"]) >= 10


def test_get_pleasure_vocabulary_intensity_5():
    vocab = get_pleasure_vocabulary(intensity=5)
    assert len(vocab["keywords"]) >= 20
    assert len(vocab["emotional"]) >= 15
    assert len(vocab["tactile"]) >= 8


def test_sublimation_category_exists():
    assert "sublimation" in DIVERSE_PLEASURE_CATEGORIES
    assert len(DIVERSE_PLEASURE_CATEGORIES["sublimation"]) >= 5


def test_transgression_pleasure_category():
    assert "transgression_pleasure" in DIVERSE_PLEASURE_CATEGORIES
    assert any("禁忌" in k or "背徳" in k for k in DIVERSE_PLEASURE_CATEGORIES["transgression_pleasure"])
```

---

### Step 10: 新規 `tests/test_pleasure_vocabulary_selector.py` — 選択サービステスト

**対象ファイル**: 新規 `tests/test_pleasure_vocabulary_selector.py`

**内容**:

```python
"""tests/test_pleasure_vocabulary_selector.py"""
import pytest
from src.services.pleasure_vocabulary_selector import PleasureVocabularySelector


def test_select_keywords():
    selector = PleasureVocabularySelector(seed=42)
    keywords = selector.select_keywords(5)
    assert len(keywords) == 5
    assert isinstance(keywords[0], str)


def test_select_emotional_templates():
    selector = PleasureVocabularySelector(seed=42)
    templates = selector.select_emotional_templates(3)
    assert len(templates) == 3


def test_select_from_category():
    selector = PleasureVocabularySelector(seed=42)
    items = selector.select_from_category("sublimation", 2)
    assert len(items) == 2
    assert isinstance(items[0], str)


def test_select_from_invalid_category():
    selector = PleasureVocabularySelector()
    items = selector.select_from_category("nonexistent", 2)
    assert items == []


def test_select_all_categories():
    selector = PleasureVocabularySelector(seed=42)
    result = selector.select_all_categories(count_per_category=1)
    assert "sublimation" in result
    assert "tension_release" in result
    assert all(isinstance(v, list) for v in result.values())


def test_get_diverse_pleasure_set_low():
    selector = PleasureVocabularySelector(seed=42)
    result = selector.get_diverse_pleasure_set(intensity=1)
    assert "keywords" in result
    assert "emotional" in result
    assert "tactile" in result
    assert "categories" in result
    assert len(result["categories"]) > 0


def test_get_diverse_pleasure_set_high():
    selector = PleasureVocabularySelector(seed=42)
    result = selector.get_diverse_pleasure_set(intensity=5)
    assert len(result["categories"]["ecstasy_diversity"]) >= 2
    assert len(result["categories"]["transgression_pleasure"]) >= 2
```

---

### Step 11: `src/services/erotic_diversity_score.py` — 快感語彙の多様性評価追加

**対象ファイル**: `src/services/erotic_diversity_score.py`

**変更内容**:
`compute_diversity_score` 関数の隣に以下を追加する。

```python
from config.pleasure_vocabulary import PLEASURE_KEYWORDS, EMOTIONAL_PLEASURE_TEMPLATES


def compute_pleasure_diversity_score(text: str) -> float:
    """
    テキスト中の快感語彙の多様性を計算する。
    0.0-1.0 を返す。1.0 が最も多様。

    快感語彙のカテゴリ:
    - PLEASURE_KEYWORDS: 基本快感情語彙
    - EMOTIONAL_PLEASURE_TEMPLATES: 感情的快感情テンプレート
    """
    all_pleasure_words = PLEASURE_KEYWORDS + EMOTIONAL_PLEASURE_TEMPLATES

    # 出現頻度をカウント
    word_counts = {}
    for word in all_pleasure_words:
        count = text.count(word)
        if count > 0:
            word_counts[word] = count

    if not word_counts:
        return 0.0

    # エントロピー計算
    total = sum(word_counts.values())
    if total == 0:
        return 0.0

    import math
    entropy = 0.0
    for count in word_counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)

    # 正規化（最大エントロピーはカテゴリ数）
    max_entropy = math.log2(len(all_pleasure_words))
    if max_entropy == 0:
        return 0.0

    return min(1.0, entropy / max_entropy)


def check_pleasure_repetition(text: str, max_repeat: int = 3) -> List[str]:
    """
    快感語彙の過度な繰り返しを検出する。

    Returns:
        繰り返し問題のリスト
    """
    warnings = []
    all_pleasure_words = PLEASURE_KEYWORDS + EMOTIONAL_PLEASURE_TEMPLATES

    for word in all_pleasure_words:
        count = text.count(word)
        if count > max_repeat:
            warnings.append(f"'{word}' が{count}回使用されています（最大{max_repeat}）")

    return warnings
```

**注意**: `List` と `math` のインポートを先頭に追加する。

---

### Step 12: `tests/test_erotic_workflow.py` —快感多様性テスト追加

**対象ファイル**: `tests/test_erotic_workflow.py`

**変更内容**:
末尾に以下を追加する。

```python
def test_pleasure_diversity_score_empty():
    from src.services.erotic_diversity_score import compute_pleasure_diversity_score
    score = compute_pleasure_diversity_score("")
    assert score == 0.0


def test_pleasure_diversity_score_diverse():
    from src.services.erotic_diversity_score import compute_pleasure_diversity_score
    text = "陶酔と恍惚が交錯する。 至福と多幸感。沈黙が震える。"
    score = compute_pleasure_diversity_score(text)
    assert 0.0 <= score <= 1.0


def test_pleasure_repetition_detection():
    from src.services.erotic_diversity_score import check_pleasure_repetition
    text = "陶酔 陶酔 陶酔 陶酔 陶酔 恍惚"
    warnings = check_pleasure_repetition(text, max_repeat=3)
    assert any("陶酔" in w for w in warnings)
```

---

### Step 13: `src/engine/prompts/erotic_specialist.py` — プロンプト生成時に快感語彙を明示

**対象ファイル**: `src/engine/prompts/erotic_specialist.py`

**変更内容**:
`build_scene_prompt` メソッドのdocstringに以下を追記する。

```python
"""
シーンプロンプトを構築する。

快感語彙は config.pleasure_vocabulary.get_pleasure_vocabulary() から取得され、
プロンプト内に「快感表現の多様性ガイド」として挿入される。
これにより「絶望」「震える」だけに頼らない多様な快感情表現が可能になる。

See Also:
    config.pleasure_vocabulary: 快感語彙定義
    src.services.pleasure_vocabulary_selector: 語彙選択サービス
"""
```

---

### Step 14: `src/agents/erotic_integrity.py` —快感語彙の多様性チェック追加

**対象ファイル**: `src/agents/erotic_integrity.py`

**変更内容**:
`check_all` メソッドまたは新規 `check_pleasure_diversity` メソッドを追加する。

```python
def check_pleasure_diversity(self, text: str, min_score: float = 0.3) -> Tuple[bool, List[str]]:
    """
    快感語彙の多様性をチェックする。

    Returns:
        (is_ok, issues)
    """
    from src.services.erotic_diversity_score import compute_pleasure_diversity_score, check_pleasure_repetition

    score = compute_pleasure_diversity_score(text)
    issues = check_pleasure_repetition(text, max_repeat=3)

    if score < min_score:
        issues.append(f"快感語彙の多様性が低すぎます（スコア: {score:.2f}）")

    return len(issues) == 0, issues
```

---

### Step 15: `src/backend/workflows/refine_erotic_workflow.py` —快感多様性検証の組み込み

**対象ファイル**: `src/backend/workflows/refine_erotic_workflow.py`

**変更内容**:
整合性チェックセクションに快感多様性チェックを追加する。

```python
# 快感語彙の多様性チェック
try:
    from src.agents.erotic_integrity import EroticIntegrityChecker
    checker = EroticIntegrityChecker()
    pleasure_ok, pleasure_issues = checker.check_pleasure_diversity(refined_content)
    if not pleasure_ok:
        for issue in pleasure_issues:
            reporter.add_log(f"⚠️ 快感多様性: {issue}")
except Exception as e:
    logger.warning(f"Pleasure diversity check failed: {e}")
```

---

### Step 16: `tests/test_erotic_workflow.py` —快感多様性検証テスト追加

**対象ファイル**: `tests/test_erotic_workflow.py`

**変更内容**:
末尾に以下を追加する。

```python
def test_pleasure_diversity_check_pass():
    from src.agents.erotic_integrity import EroticIntegrityChecker
    checker = EroticIntegrityChecker()
    text = "陶酔と恍惚が交錯する。 至福と多幸感。沈黙が震える。"
    ok, issues = checker.check_pleasure_diversity(text)
    assert ok is True


def test_pleasure_diversity_check_fail():
    from src.agents.erotic_integrity import EroticIntegrityChecker
    checker = EroticIntegrityChecker()
    text = "陶酔 陶酔 陶酔 陶酔 陶酔"  # 多様性なし
    ok, issues = checker.check_pleasure_diversity(text)
    assert ok is False
```

---

### Step 17: `src/services/erotic_diversity_score.py` — `check_diversity` に関数追加

**対象ファイル**: `src/services/erotic_diversity_score.py`

**変更内容**:
既存 `check_diversity` 関数（Step 10 で追加済み）に快感語彙チェックを組み込む。

```python
def check_diversity(text: str, vocabulary_bank: list) -> dict:
    """スコア計算と分類を一度に行うユーティリティ。"""
    score = compute_diversity_score(text, vocabulary_bank)
    classification = classify_diversity(score)
    warnings = check_repetition(text, vocabulary_bank, max_repeat=3)

    # 快感語彙の多様性チェック
    pleasure_score = compute_pleasure_diversity_score(text)
    pleasure_warnings = check_pleasure_repetition(text, max_repeat=3)

    if pleasure_score < 0.3:
        warnings.append(f"快感語彙の多様性が低すぎます（スコア: {pleasure_score:.2f}）")
    warnings.extend(pleasure_warnings)

    return {
        "score": score,
        "classification": classification,
        "warnings": warnings,
        "pleasure_score": pleasure_score,
    }
```

---

### Step 18: `config/pleasure_vocabulary.py` — エラー時フォールバック追加

**対象ファイル**: `config/pleasure_vocabulary.py`

**変更内容**:
`get_pleasure_vocabulary` に例外処理を追加する。

```python
def get_pleasure_vocabulary(intensity: int = 3) -> Dict[str, List[str]]:
    """強度に応じた快感語彙を取得するユーティリティ関数。"""
    try:
        if intensity <= 2:
            return {
                "keywords": [k for k in PLEASURE_KEYWORDS if k in ["陶酔", "多幸感", "至福", "恍惚", " bliss "]],
                "emotional": EMOTIONAL_PLEASURE_TEMPLATES[:5],
                "tactile": TACTILE_PLEASURE_TEMPLATES[:3],
            }
        elif intensity == 3:
            return {
                "keywords": PLEASURE_KEYWORDS[:15],
                "emotional": EMOTIONAL_PLEASURE_TEMPLATES[:10],
                "tactile": TACTILE_PLEASURE_TEMPLATES[:5],
            }
        else:
            return {
                "keywords": PLEASURE_KEYWORDS,
                "emotional": EMOTIONAL_PLEASURE_TEMPLATES,
                "tactile": TACTILE_PLEASURE_TEMPLATES,
            }
    except Exception:
        # フォールバック: 最小限の語彙を返す
        return {
            "keywords": ["陶酔", "恍惚", "至福"],
            "emotional": ["心の奥から込み上げる温かさ", "時間軸が歪む"],
            "tactile": ["肌が粟立つ", "臓物が躍る"],
        }
```

---

### Step 19: `src/engine/prompts/erotic_specialist.py` — 例外処理の追加

**対象ファイル**: `src/engine/prompts/erotic_specialist.py`

**変更内容**:
Step 6 と Step 8 で追加した快感語彙注入コードを `try/except` でラップする。

```python
try:
    from config.pleasure_vocabulary import get_pleasure_vocabulary
    pleasure_vocab = get_pleasure_vocabulary(intensity=context.get("intensity", 3))
    pleasure_section = f"""
【快感表現の多様性ガイド】
基本快感情語彙: {', '.join(pleasure_vocab['keywords'])}
感情的快感情: {', '.join(pleasure_vocab['emotional'])}
触感的快感情: {', '.join(pleasure_vocab['tactile'])}
"""
    prompt += pleasure_section
except Exception as e:
    logger.debug(f"Pleasure vocabulary injection skipped: {e}")
```

---

### Step 20: `tests/test_erotic_workflow.py` — pleasure_score 含むテスト追加

**対象ファイル**: `tests/test_erotic_workflow.py`

**変更内容**:
以下を追加する。

```python
def test_check_diversity_includes_pleasure_score():
    from src.services.erotic_diversity_score import check_diversity
    from config.erotic_vocabulary import METAPHOR_BANK
    text = "陶酔と恍惚が交錯する。 至福と多幸感。"
    result = check_diversity(text, METAPHOR_BANK)
    assert "pleasure_score" in result
    assert 0.0 <= result["pleasure_score"] <= 1.0
```

---

### Step 21: `src/services/erotic_diversity_score.py` — 型ヒント追加

**対象ファイル**: `src/services/erotic_diversity_score.py`

**変更内容**:
以下を追加する。

```python
from typing import Dict, List, Tuple
import math
```

---

### Step 22: `config/pleasure_vocabulary.py` — `Final` 型ヒント追加

**対象ファイル**: `config/pleasure_vocabulary.py`

**変更内容**:
ファイル冒頭に以下を追加する。

```python
from typing import Dict, Final, List
```

各定数に `Final` を付与する（任意。但しStep 14 と同じパターン）。

---

### Step 23: `tests/test_erotic_workflow.py` — 快感語彙の多様性を確認するテスト追加

**対象ファイル**: `tests/test_erotic_workflow.py`

**変更内容**:
以下を追加する。

```python
def test_pleasure_vocabulary_has_diverse_categories():
    from config.pleasure_vocabulary import DIVERSE_PLEASURE_CATEGORIES
    assert "sublimation" in DIVERSE_PLEASURE_CATEGORIES
    assert "tension_release" in DIVERSE_PLEASURE_CATEGORIES
    assert "intimacy_pleasure" in DIVERSE_PLEASURE_CATEGORIES
    assert "surrender_pleasure" in DIVERSE_PLEASURE_CATEGORIES
    assert "transgression_pleasure" in DIVERSE_PLEASURE_CATEGORIES
    assert "ecstasy_diversity" in DIVERSE_PLEASURE_CATEGORIES


def test_pleasure_vocabulary_intensity_mapping():
    from config.pleasure_vocabulary import get_pleasure_vocabulary
    low = get_pleasure_vocabulary(1)
    mid = get_pleasure_vocabulary(3)
    high = get_pleasure_vocabulary(5)
    assert len(low["keywords"]) < len(mid["keywords"])
    assert len(mid["keywords"]) < len(high["keywords"])
```

---

### Step 24: `src/services/erotic_diversity_score.py` — `compute_pleasure_diversity_score` のみ的张こと確認

**対象ファイル**: `src/services/erotic_diversity_score.py`

**変更内容**:
`compute_pleasure_diversity_score` の冒頭に以下の注釈を追加する。

```python
def compute_pleasure_diversity_score(text: str) -> float:
    """
    テキスト中の快感語彙の多様性をエントロピーで算出する。0.0-1.0。

    快感語彙のカテゴリ:
        - PLEASURE_KEYWORDS: 基本快感情語彙
        - EMOTIONAL_PLEASURE_TEMPLATES: 感情的快感情テンプレート

    閾値:
        - 0.5以上: 良好
        - 0.3-0.5: 要改善
        - 0.3未満: 不合格

    See Also:
        config.pleasure_vocabulary: 快感語彙定義
        PleasureVocabularySelector: 語彙選択サービス
    """
```

---

## 改善案 #5: 読者反応の擬似シミュレーション（Steps 25-48）

### Step 25: 新規 `src/agents/reader_simulator.py` — 読者エージェント基本クラス

**対象ファイル**: 新規 `src/agents/reader_simulator.py`

**内容**:

```python
"""
src/agents/reader_simulator.py
読者反応の擬似シミュレーションを行うエージェント。

生成したプロットを「想定読者エージェント」に読ませ、
「つまらない」「退屈」と感じる箇所を自動検知して返す。
"""
from typing import Dict, List, Tuple, Optional
import random


class ReaderSimulator:
    """
    読者反応をシミュレートするクラス。
    低性能LLMでも動作可能なルールベース実装。
    """

    BOREDOM_KEYWORDS = [
        "長い",
        "展開が遅い",
        "退屈",
        "単調",
        "平坦",
        "繰り返し",
        "ダレる",
        "マンネリ",
        "同じ調子",
        "変化がない",
        "進まない",
        "停滞",
        "引っ張る",
        "有意義でない",
        "不要",
    ]

    ENGAGEMENT_KEYWORDS = [
        "展開が早い",
        "面白い",
        "気になる",
        "先が知りたい",
        "ドキドキ",
        "ハラハラ",
        "引き込まれる",
        "否応なく",
        "思わず",
        "吸い込まれる",
    ]

    PACING_ISSUE_PATTERNS = [
        ("同じ単語の連続", 5),
        ("会話なしの長い段落", 200),
        ("説明的描写の連続", 150),
        ("心理描写の过长", 300),
    ]

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def analyze_boredom(self, text: str, paragraph_length_threshold: int = 150) -> List[Dict[str, any]]:
        """
        テキスト中の「退屈ポイント」を検出する。

        検出方法:
        1. 退屈キーワードの出現回数
        2. 長い単段落の検出
        3. 会話なしの区长測定
        4. 展開の停滞を示す表現の検出

        Returns:
            List of {"position": int, "type": str, "detail": str, "severity": str}
        """
        issues = []
        paragraphs = text.split("\n\n")

        for idx, para in enumerate(paragraphs):
            para_len = len(para)

            # 長い段落を検出
            if para_len > paragraph_length_threshold * 2:
                issues.append({
                    "position": idx,
                    "type": "too_long",
                    "detail": f"段落{idx+1}が非常に長い（{para_len}文字）",
                    "severity": "high",
                })
            elif para_len > paragraph_length_threshold:
                issues.append({
                    "position": idx,
                    "type": "long",
                    "detail": f"段落{idx+1}が長い（{para_len}文字）",
                    "severity": "medium",
                })

            # 退屈キーワードの検出
            for kw in self.BOREDOM_KEYWORDS:
                if kw in para:
                    issues.append({
                        "position": idx,
                        "type": "boredom_keyword",
                        "detail": f"段落{idx+1}に'{kw}'が含まれている",
                        "severity": "medium",
                    })

            # 会話なしの長いテキストを検出
            if "\n" not in para and "」" not in para and para_len > 200:
                issues.append({
                    "position": idx,
                    "type": "no_dialogue",
                    "detail": f"段落{idx+1}に会話が含まれない（{para_len}文字）",
                    "severity": "medium",
                })

        return issues

    def analyze_engagement(self, text: str) -> Dict[str, any]:
        """
        読者の「惹きつけポイント」を検出する。

        Returns:
            {"engagement_score": float, "hooks": List[Dict], "issues": List[Dict]}
        """
        hooks = []
        paragraphs = text.split("\n\n")

        for idx, para in enumerate(paragraphs):
            for kw in self.ENGAGEMENT_KEYWORDS:
                if kw in para:
                    hooks.append({
                        "position": idx,
                        "keyword": kw,
                        "detail": f"段落{idx+1}に惹きつけ要素'{kw}'",
                    })

        # エンゲージメントスコア（0.0-1.0）
        hook_ratio = len(hooks) / max(len(paragraphs), 1)
        engagement_score = min(1.0, hook_ratio * 2)  # 2割以上で满分

        return {
            "engagement_score": engagement_score,
            "hooks": hooks,
        }

    def simulate_reader_response(self, text: str) -> Dict[str, any]:
        """
        読者反応の全体的シミュレーションを行う。

        Returns:
            {
                "boredom_issues": [...],
                "engagement": {...},
                "overall_score": float,
                "recommendations": [...],
            }
        """
        boredom_issues = self.analyze_boredom(text)
        engagement = self.analyze_engagement(text)

        # overall score: 0.0-1.0 (高い程良い)
        boredom_penalty = len(boredom_issues) * 0.05
        overall_score = max(0.0, engagement["engagement_score"] - boredom_penalty)

        recommendations = []
        if overall_score < 0.5:
            recommendations.append("退屈ポイントの修正を検討してください")
        if len(boredom_issues) > 3:
            recommendations.append("文章の展開を早めるか、对话を差し込んでください")
        if engagement["engagement_score"] < 0.3:
            recommendations.append("惹きつけ要素（ ENGAGEMENT_KEYWORDS ）を追加してください")

        return {
            "boredom_issues": boredom_issues,
            "engagement": engagement,
            "overall_score": overall_score,
            "recommendations": recommendations,
        }

    def suggest_improvement(self, text: str, issue: Dict[str, any]) -> str:
        """
        検出された問題に対して修正案を提示する（ルールベース）。

        Returns:
            修正案の文字列
        """
        issue_type = issue.get("type", "")

        suggestions = {
            "too_long": "この段落を分割するか、要点を削ってください。",
            "long": "もう少し簡潔にまとめてはどうですか。",
            "boredom_keyword": "この表現を見直すか、別の言い回しにしてください。",
            "no_dialogue": "キャラクターの会话や独白を追加してリズムを作ってください。",
        }

        return suggestions.get(issue_type, "この箇所を見直すことをお勧めします。")
```

---

### Step 26: `src/agents/reader_simulator.py` — `__init__.py` へのエクスポート追加

**対象ファイル**: `src/agents/__init__.py`（または `src/agents/exports.py`）

**変更内容**:
既存 `__init__.py` 末尾に以下を追加する。

```python
from src.agents.reader_simulator import ReaderSimulator
```

---

### Step 27: 新規 `src/services/reader_pacing_analyzer.py` — テンポ分析サービス

**対象ファイル**: 新規 `src/services/reader_pacing_analyzer.py`

**内容**:

```python
"""
src/services/reader_pacing_analyzer.py
プロットのテンポ（ pace ）分析サービス。
読者シミュレーションの結果を 기반으로、
「退屈な箇所」を自動検知し、修正案を生成する。
"""
from typing import Dict, List, Optional
from src.agents.reader_simulator import ReaderSimulator


class ReaderPacingAnalyzer:
    """読者ベースのパシング分析サービス"""

    def __init__(self, seed: Optional[int] = None):
        self.simulator = ReaderSimulator(seed=seed)

    def analyze_plot(self, plot_text: str) -> Dict[str, any]:
        """
        プロットテキスト全体のテンポ分析を行う。

        Returns:
            {
                "overall_score": float,
                "boredom_issues": List[Dict],
                "engagement": Dict,
                "recommendations": List[str],
                "boring_paragraph_indices": List[int],
            }
        """
        result = self.simulator.simulate_reader_response(plot_text)

        # 退屈な段落のインデックス列表
        boring_indices = sorted(set(issue["position"] for issue in result["boredom_issues"]))

        return {
            "overall_score": result["overall_score"],
            "boredom_issues": result["boredom_issues"],
            "engagement": result["engagement"],
            "recommendations": result["recommendations"],
            "boring_paragraph_indices": boring_indices,
        }

    def get_boring_paragraphs(self, plot_text: str) -> List[str]:
        """退屈だと判定された段落のリストを返す。"""
        result = self.analyze_plot(plot_text)
        paragraphs = plot_text.split("\n\n")
        return [paragraphs[idx] for idx in result["boring_paragraph_indices"] if idx < len(paragraphs)]

    def get_modification_plan(self, plot_text: str) -> List[Dict[str, any]]:
        """
        各退屈ポイントに対する修正計画リストを生成する。

        Returns:
            List of {"paragraph_index": int, "paragraph_text": str, "suggestion": str}
        """
        result = self.analyze_plot(plot_text)
        paragraphs = plot_text.split("\n\n")
        plan = []

        for idx in result["boring_paragraph_indices"]:
            if idx < len(paragraphs):
                issue_list = [i for i in result["boredom_issues"] if i["position"] == idx]
                issue_types = [i["type"] for i in issue_list]
                suggestion = self.simulator.suggest_improvement(paragraphs[idx], issue_list[0] if issue_list else {})
                plan.append({
                    "paragraph_index": idx,
                    "paragraph_text": paragraphs[idx][:100] + "..." if len(paragraphs[idx]) > 100 else paragraphs[idx],
                    "issue_types": issue_types,
                    "suggestion": suggestion,
                })

        return plan
```

---

### Step 28: `src/services/__init__.py` — `ReaderPacingAnalyzer` エクスポート追加

**対象ファイル**: `src/services/__init__.py`

**変更内容**:
末尾に以下を追加する。

```python
from src.services.reader_pacing_analyzer import ReaderPacingAnalyzer
```

---

### Step 29: 新規 `tests/test_reader_simulator.py` — 基本テスト

**対象ファイル**: 新規 `tests/test_reader_simulator.py`

**内容**:

```python
"""tests/test_reader_simulator.py"""
import pytest
from src.agents.reader_simulator import ReaderSimulator


def test_simulator_init():
    simulator = ReaderSimulator()
    assert simulator is not None


def test_analyze_boredom_empty():
    simulator = ReaderSimulator()
    issues = simulator.analyze_boredom("")
    assert isinstance(issues, list)


def test_analyze_boredom_long_paragraph():
    simulator = ReaderSimulator()
    long_text = "これは非常に長い段落です。" * 50  # ~1500文字
    issues = simulator.analyze_boredom(long_text)
    assert any(i["type"] in ("long", "too_long") for i in issues)


def test_analyze_boredom_no_dialogue():
    simulator = ReaderSimulator()
    text = "静寂が二人を包んでいた。時間だけが静かに流れていく。何も変わらない日常が繰り返される。" * 5
    issues = simulator.analyze_boredom(text)
    assert any(i["type"] == "no_dialogue" for i in issues)


def test_analyze_boredom_boredom_keyword():
    simulator = ReaderSimulator()
    text = "このシーンは退屈で、展開が遅い。"
    issues = simulator.analyze_boredom(text)
    assert any(i["type"] == "boredom_keyword" for i in issues)


def test_analyze_engagement():
    simulator = ReaderSimulator()
    text = "彼は急ぎ足で歩いた。先がどうなるか気になった。"
    result = simulator.analyze_engagement(text)
    assert "engagement_score" in result
    assert "hooks" in result
    assert 0.0 <= result["engagement_score"] <= 1.0


def test_simulate_reader_response():
    simulator = ReaderSimulator()
    text = "静寂が二人を包んでいた。" * 20
    result = simulator.simulate_reader_response(text)
    assert "boredom_issues" in result
    assert "engagement" in result
    assert "overall_score" in result
    assert "recommendations" in result


def test_suggest_improvement():
    simulator = ReaderSimulator()
    issue = {"type": "too_long", "detail": "段落が長すぎる"}
    suggestion = simulator.suggest_improvement("dummy text", issue)
    assert isinstance(suggestion, str)
    assert len(suggestion) > 0
```

---

### Step 30: 新規 `tests/test_reader_pacing_analyzer.py` — テンポ分析テスト

**対象ファイル**: 新規 `tests/test_reader_pacing_analyzer.py`

**内容**:

```python
"""tests/test_reader_pacing_analyzer.py"""
import pytest
from src.services.reader_pacing_analyzer import ReaderPacingAnalyzer


def test_analyzer_init():
    analyzer = ReaderPacingAnalyzer()
    assert analyzer is not None


def test_analyze_plot_good():
    analyzer = ReaderPacingAnalyzer()
    good_text = """
    「行こう」と彼女は言った。

    彼の心はドキドキした。先がどうなるか気になった。

    結果は予測できなかったが、展開は早かった。
    """
    result = analyzer.analyze_plot(good_text)
    assert "overall_score" in result
    assert "boredom_issues" in result
    assert "recommendations" in result
    assert 0.0 <= result["overall_score"] <= 1.0


def test_analyze_plot_boring():
    analyzer = ReaderPacingAnalyzer()
    boring_text = "静寂が二人を包んでいた。時間が流れる。何も変わらない。退屈だ。単調だ。" * 10
    result = analyzer.analyze_plot(boring_text)
    assert result["overall_score"] < 0.8  # 退屈なのでスコアが低い
    assert len(result["boredom_issues"]) > 0


def test_get_boring_paragraphs():
    analyzer = ReaderPacingAnalyzer()
    text = """
    短い段落。

    これは非常に長い段落です。これは非常に長い段落です。これは非常に長い段落です。
    これは非常に長い段落です。これは非常に長い段落です。これは非常に長い段落です。
    これは非常に長い段落です。これは非常に長い段落です。これは非常に長い段落です。

    短い段落。
    """
    boring = analyzer.get_boring_paragraphs(text)
    assert isinstance(boring, list)
    assert len(boring) > 0


def test_get_modification_plan():
    analyzer = ReaderPacingAnalyzer()
    text = """
    短い段落。

    静寂が二人を包んでいた。時間が流れる。何も変わらない。退屈だ。単調だ。長い長い長い。

    短い段落。
    """
    plan = analyzer.get_modification_plan(text)
    assert isinstance(plan, list)
    assert all("paragraph_index" in p for p in plan)
    assert all("suggestion" in p for p in plan)
```

---

### Step 31: `src/backend/workflows/refine_erotic_workflow.py` — 読者シミュレーショ組み込み

**対象ファイル**: `src/backend/workflows/refine_erotic_workflow.py`

**変更内容**:
`execute` メソッドの整合性チェック後に読者シミュレーション結果を追加する。

```python
# 4. 読者反応シミュレーション
try:
    from src.services.reader_pacing_analyzer import ReaderPacingAnalyzer
    analyzer = ReaderPacingAnalyzer()
    pacing_result = analyzer.analyze_plot(refined_content)

    if pacing_result["overall_score"] < 0.5:
        reporter.add_log(f"⚠️ 読者反応: スコア{pacing_result['overall_score']:.2f} - 退屈ポイント{len(pacing_result['boredom_issues'])}件")
        for rec in pacing_result["recommendations"]:
            reporter.add_log(f"  → {rec}")

    # 修正計画を提供
    if pacing_result["boring_paragraph_indices"]:
        modification_plan = analyzer.get_modification_plan(refined_content)
        for item in modification_plan[:3]:  # 最初3つをログに
            reporter.add_log(f"  段落{item['paragraph_index']+1}: {item['suggestion']}")
except Exception as e:
    logger.warning(f"Reader pacing analysis failed: {e}")
```

---

### Step 32: 新規 `src/services/plot_quality_reporter.py` — 品質レポート生成サービス

**対象ファイル**: 新規 `src/services/plot_quality_reporter.py`

**内容**:

```python
"""
src/services/plot_quality_reporter.py
プロットの品質レポートを生成するサービス。
読者シミュレーション結果を 기반으로、総合的な品質評価を行う。
"""
from typing import Dict, List, Optional
from src.services.reader_pacing_analyzer import ReaderPacingAnalyzer
from src.services.erotic_diversity_score import compute_diversity_score, classify_diversity
from config.erotic_vocabulary import METAPHOR_BANK


class PlotQualityReporter:
    """プロット品質レポート生成サービス"""

    def __init__(self, seed: Optional[int] = None):
        self.analyzer = ReaderPacingAnalyzer(seed=seed)

    def generate_report(self, plot_text: str, erotic_intensity: int = 3) -> Dict[str, any]:
        """
        プロットの総合品質レポートを生成する。

        Returns:
            {
                "overall_score": float,
                "reader_response": {...},
                "vocabulary_diversity": float,
                "boredom_count": int,
                "recommendations": List[str],
                "summary": str,
            }
        """
        # 読者反応分析
        reader_result = self.analyzer.analyze_plot(plot_text)

        # ボキャブラリ多様性分析
        diversity_score = compute_diversity_score(plot_text, METAPHOR_BANK)
        diversity_class = classify_diversity(diversity_score)

        # 総合スコア算出
        # 読者反応(50%) + ボキャブラリ多様性(30%) + 退屈回避(20%)
        boredom_score = 1.0 - min(1.0, len(reader_result["boredom_issues"]) * 0.05)
        overall_score = (
            reader_result["overall_score"] * 0.5 +
            diversity_score * 0.3 +
            boredom_score * 0.2
        )

        recommendations = list(reader_result["recommendations"])
        if diversity_class in ("warn", "fail"):
            recommendations.append(f"ボキャブラリ多様性: {diversity_class}（スコア: {diversity_score:.2f}）")

        # サマリー生成
        if overall_score >= 0.7:
            summary = "高品質: 読者を引きつける展開と多様な表現力が特徴です。"
        elif overall_score >= 0.5:
            summary = "要改善: 一部で退屈さや表現の繰り返しが見られます。"
        else:
            summary = "低品質: 全体的なテンポと見せかけの多様性に問題があります。早急に修正をお勧めします。"

        return {
            "overall_score": round(overall_score, 3),
            "reader_response": reader_result,
            "vocabulary_diversity": round(diversity_score, 3),
            "diversity_class": diversity_class,
            "boredom_count": len(reader_result["boredom_issues"]),
            "recommendations": recommendations,
            "summary": summary,
        }

    def get_modification_priority(self, plot_text: str) -> List[Dict[str, any]]:
        """
        修正優先度付きリストを返す。
        影響度の高い（退屈度の高い）段落から順に並べる。
        """
        return self.analyzer.get_modification_plan(plot_text)
```

---

### Step 33: `src/services/__init__.py` — `PlotQualityReporter` エクスポート追加

**対象ファイル**: `src/services/__init__.py`

**変更内容**:
末尾に以下を追加する。

```python
from src/services/plot_quality_reporter import PlotQualityReporter
```

---

### Step 34: 新規 `tests/test_plot_quality_reporter.py` — 品質レポートテスト

**対象ファイル**: 新規 `tests/test_plot_quality_reporter.py`

**内容**:

```python
"""tests/test_plot_quality_reporter.py"""
import pytest
from src.services.plot_quality_reporter import PlotQualityReporter


def test_reporter_init():
    reporter = PlotQualityReporter()
    assert reporter is not None


def test_generate_report_good():
    reporter = PlotQualityReporter()
    good_text = """
    「行こう」と彼女は言った。

    彼の心はドキドキした。展開が早く、面白い。

    陶酔と恍惚が交錯する。 至福と多幸感。
    """
    report = reporter.generate_report(good_text)
    assert "overall_score" in report
    assert "reader_response" in report
    assert "vocabulary_diversity" in report
    assert 0.0 <= report["overall_score"] <= 1.0


def test_generate_report_boring():
    reporter = PlotQualityReporter()
    boring_text = "静寂が二人を包んでいた。時間が流れる。何も変わらない。退屈だ。単調だ。" * 10
    report = reporter.generate_report(boring_text)
    assert report["overall_score"] < 0.6
    assert report["boredom_count"] > 0


def test_generate_report_has_summary():
    reporter = PlotQualityReporter()
    text = "静寂が二人を包んでいた。" * 20
    report = reporter.generate_report(text)
    assert "summary" in report
    assert isinstance(report["summary"], str)
    assert len(report["summary"]) > 0


def test_get_modification_priority():
    reporter = PlotQualityReporter()
    text = """
    短い段落。

    静寂が二人を包んでいた。時間が流れる。何も変わらない。退屈だ。

    短い段落。
    """
    priority_list = reporter.get_modification_priority(text)
    assert isinstance(priority_list, list)
    assert all("paragraph_index" in p for p in priority_list)
```

---

### Step 35: `src/agents/writing.py` — 読者シミュレーション結果のログ追加

**対象ファイル**: `src/agents/writing.py`

**変更内容**:
`write_episode` メソッドのログ出力部分に以下を追加する（Step 46 と重複しない位置）。

```python
# 読者シミュレーション結果のログ（リファインメント後）
if specialist and erotic_intensity > 0 and nsfw_enabled:
    try:
        from src.services.plot_quality_reporter import PlotQualityReporter
        quality_reporter = PlotQualityReporter()
        quality_report = quality_reporter.generate_report(result, erotic_intensity)
        logger.info(
            f"Plot quality: overall={quality_report['overall_score']:.2f}, "
            f"boredom_count={quality_report['boredom_count']}, "
            f"diversity={quality_report['vocabulary_diversity']:.2f}"
        )
        if quality_report["overall_score"] < 0.5:
            logger.warning(f"Plot quality low: {quality_report['summary']}")
            for rec in quality_report["recommendations"]:
                logger.warning(f"  Recommendation: {rec}")
    except Exception as e:
        logger.debug(f"Plot quality analysis skipped: {e}")
```

---

### Step 36: 新規 `src/services/auto_editor.py` — 自動編集サービス

**対象ファイル**: 新規 `src/services/auto_editor.py`

**内容**:

```python
"""
src/services/auto_editor.py
読者シミュレーション結果に基づく自動編集サービス。
退屈な箇所を自動的に検出し、簡略化された修正提案を行う。
"""
from typing import Dict, List, Optional
from src.services.reader_pacing_analyzer import ReaderPacingAnalyzer


class AutoEditor:
    """
    退屈ポイントの自動編集を提案するサービス。
    低性能LLM でも解釈可能なルールベース実装。
    """

    DIALOGUE_INJECTION_PHRASES = [
        "「...", "「...", "「...?」", "「...」と彼女は言った。",
        "「...」と彼は続けた。", "...と、声が响いた。",
    ]

    PACING_BREAK_PHRASES = [
        "その時 —",
        "突然、",
        "だが、その時、",
        "状況は一変する。",
        "彼女の表情が変わった。",
    ]

    def __init__(self, seed: Optional[int] = None):
        self.analyzer = ReaderPacingAnalyzer(seed=seed)

    def suggest_dialogue_injection(self, paragraph_text: str) -> str:
        """
        会話が足りない段落に、会話を注入する位置を提案する。

        Returns:
            "beginning" | "middle" | "end" のいずれかに注入すべき位置
        """
        para_len = len(paragraph_text)
        if para_len < 100:
            return "end"
        elif para_len < 200:
            return "middle"
        else:
            return "end"

    def split_long_paragraph(self, paragraph_text: str, max_chars: int = 150) -> List[str]:
        """
        長い段落を分割する。

        Returns:
            分割された段落のリスト
        """
        if len(paragraph_text) <= max_chars:
            return [paragraph_text]

        # 句点（。）で分割を試みる
        sentences = paragraph_text.split("。")
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= max_chars:
                current_chunk += sentence + "。"
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence + "。"

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [paragraph_text]

    def add_pacing_break(self, paragraph_text: str, insert_after: int = 100) -> str:
        """
        長い段落にペースブレイク（場面転換や唐突な要素）を挿入する。

        Returns:
            ペースブレイク挿入後のテキスト
        """
        if len(paragraph_text) < insert_after * 2:
            return paragraph_text

        phrases = self.PACING_BREAK_PHRASES
        import random
        break_phrase = random.choice(phrases)

        # 中央あたりにペースブレイクを挿入
        mid = len(paragraph_text) // 2
        return paragraph_text[:mid] + f"\n\n{break_phrase}\n\n" + paragraph_text[mid:]

    def auto_edit(self, plot_text: str) -> Dict[str, any]:
        """
        自動編集を提案する。

        Returns:
            {
                "original_length": int,
                "modified_length": int,
                "edits_applied": List[str],
                "modified_text": str,
            }
        """
        result = self.analyzer.analyze_plot(plot_text)
        boring_indices = result["boring_paragraph_indices"]
        paragraphs = plot_text.split("\n\n")

        edits_applied = []
        modified_paragraphs = list(paragraphs)

        for idx in boring_indices:
            if idx >= len(modified_paragraphs):
                continue

            para = modified_paragraphs[idx]
            original_len = len(para)

            # 長い段落の分割
            if len(para) > 300:
                split_result = self.split_long_paragraph(para)
                if len(split_result) > 1:
                    modified_paragraphs[idx:idx+1] = split_result
                    edits_applied.append(f"段落{idx+1}: 分割（{len(split_result)}個に）")

            # ペースブレイクの挿入
            elif len(para) > 200:
                modified = self.add_pacing_break(para)
                if modified != para:
                    modified_paragraphs[idx] = modified
                    edits_applied.append(f"段落{idx+1}: ペースブレイク挿入")

            # 会話を注入
            elif "\n" not in para and "」" not in para:
                injection_pos = self.suggest_dialogue_injection(para)
                import random
                dialogue = random.choice(self.DIALOGUE_INJECTION_PHRASES)
                if injection_pos == "end":
                    modified_paragraphs[idx] = para + f"\n\n{dialogue}"
                elif injection_pos == "middle":
                    mid = len(para) // 2
                    modified_paragraphs[idx] = para[:mid] + f"\n\n{dialogue}\n\n" + para[mid:]
                else:
                    modified_paragraphs[idx] = f"{dialogue}\n\n{para}"
                edits_applied.append(f"段落{idx+1}: 会話注入（{injection_pos}）")

        modified_text = "\n\n".join(modified_paragraphs)

        return {
            "original_length": len(plot_text),
            "modified_length": len(modified_text),
            "edits_applied": edits_applied,
            "modified_text": modified_text,
        }
```

---

### Step 37: `src/services/__init__.py` — `AutoEditor` エクスポート追加

**対象ファイル**: `src/services/__init__.py`

**変更内容**:
末尾に以下を追加する。

```python
from src/services/auto_editor import AutoEditor
```

---

### Step 38: 新規 `tests/test_auto_editor.py` — 自動編集テスト

**対象ファイル**: 新規 `tests/test_auto_editor.py`

**内容**:

```python
"""tests/test_auto_editor.py"""
import pytest
from src.services.auto_editor import AutoEditor


def test_auto_editor_init():
    editor = AutoEditor()
    assert editor is not None


def test_suggest_dialogue_injection_short():
    editor = AutoEditor()
    pos = editor.suggest_dialogue_injection("短い段落")
    assert pos in ("beginning", "middle", "end")


def test_suggest_dialogue_injection_long():
    editor = AutoEditor()
    pos = editor.suggest_dialogue_injection("これは長い段落です。" * 30)
    assert pos in ("beginning", "middle", "end")


def test_split_long_paragraph():
    editor = AutoEditor()
    long_para = "これはテストです。" * 50
    chunks = editor.split_long_paragraph(long_para, max_chars=100)
    assert len(chunks) > 1
    assert all(len(c) <= 120 for c in chunks)


def test_split_short_paragraph():
    editor = AutoEditor()
    short_para = "これは短い段落です。"
    chunks = editor.split_long_paragraph(short_para, max_chars=100)
    assert len(chunks) == 1
    assert chunks[0] == short_para


def test_add_pacing_break():
    editor = AutoEditor()
    long_para = "これはテストです。" * 50
    modified = editor.add_pacing_break(long_para, insert_after=100)
    assert modified != long_para
    assert any(phrase in modified for phrase in editor.PACING_BREAK_PHRASES)


def test_auto_edit_no_boring():
    editor = AutoEditor()
    text = "短い段落。\n\n別の段落。"
    result = editor.auto_edit(text)
    assert "edits_applied" in result
    assert "modified_text" in result


def test_auto_edit_with_long_paragraph():
    editor = AutoEditor()
    text = "これは非常に長い段落です。" * 50 + "\n\n短い段落。"
    result = editor.auto_edit(text)
    assert len(result["edits_applied"]) > 0
    assert len(result["modified_text"]) > 0


def test_auto_edit_with_no_dialogue():
    editor = AutoEditor()
    text = "静寂が二人を包んでいた。時間が流れる。何も変わらない。" * 10
    result = editor.auto_edit(text)
    assert "edits_applied" in result
    # 会話注入またはペースブレイクが適用される
    assert len(result["edits_applied"]) > 0
```

---

### Step 39: `src/backend/workflows/refine_erotic_workflow.py` — 自動編集組み込み

**対象ファイル**: `src/backend/workflows/refine_erotic_workflow.py`

**変更内容**:
Step 31 で追加した読者シミュレーション後に自動編集を提案するコードを追加する。

```python
# 自動編集の提案（読者シミュレーション後）
if pacing_result["overall_score"] < 0.6:
    try:
        from src.services.auto_editor import AutoEditor
        editor = AutoEditor()
        auto_edit_result = editor.auto_edit(refined_content)
        if auto_edit_result["edits_applied"]:
            reporter.add_log(f"📝 自動編集案: {len(auto_edit_result['edits_applied'])}件の編集を提案")
            for edit in auto_edit_result["edits_applied"][:3]:
                reporter.add_log(f"  → {edit}")
    except Exception as e:
        logger.debug(f"Auto edit skipped: {e}")
```

---

### Step 40: `tests/test_erotic_workflow.py` — 読者シミュレーション統合テスト追加

**対象ファイル**: `tests/test_erotic_workflow.py`

**変更内容**:
末尾に以下を追加する。

```python
def test_reader_simulator_integration():
    from src.agents.reader_simulator import ReaderSimulator
    simulator = ReaderSimulator()
    text = "静寂が二人を包んでいた。時間が流れる。何も変わらない。退屈だ。"
    result = simulator.simulate_reader_response(text)
    assert result["overall_score"] < 0.5
    assert len(result["boredom_issues"]) > 0


def test_reader_pacing_analyzer_integration():
    from src.services.reader_pacing_analyzer import ReaderPacingAnalyzer
    analyzer = ReaderPacingAnalyzer()
    text = "静寂が二人を包んでいた。" * 10 + "\n\n「行こう」と彼女は言った。"
    result = analyzer.analyze_plot(text)
    assert "overall_score" in result
    assert "boring_paragraph_indices" in result
    assert len(result["boring_paragraph_indices"]) > 0


def test_plot_quality_reporter_integration():
    from src.services.plot_quality_reporter import PlotQualityReporter
    reporter = PlotQualityReporter()
    text = "静寂が二人を包んでいた。" * 10 + "\n\n陶酔と恍惚。"
    report = reporter.generate_report(text)
    assert "overall_score" in report
    assert "summary" in report
    assert "recommendations" in report


def test_auto_editor_integration():
    from src.services.auto_editor import AutoEditor
    editor = AutoEditor()
    text = "静寂が二人を包んでいた。" * 20
    result = editor.auto_edit(text)
    assert "edits_applied" in result
    assert "modified_text" in result
```

---

### Step 41: `src/agents/reader_simulator.py` — 感情的高揚時と低落時のパターン追加

**対象ファイル**: `src/agents/reader_simulator.py`

**変更内容**:
`PACING_ISSUE_PATTERNS` の後に以下を追加する。

```python
    EXCITEMENT_BOOSTER_PATTERNS = [
        ("！「", 0.3),
        ("？」, 0.2),
        ("…」", 0.15),
        ("突然", 0.2),
        ("だが", 0.2),
        ("しかし", 0.15),
        (" контраст ", 0.25),
    ]

    MONOTONY_PATTERNS = [
        ("同じ", 0.15),
        ("繰り返し", 0.2),
        ("依然として", 0.1),
        ("単に", 0.1),
        ("単に", 0.1),
        ("ただ", 0.05),
    ]

    def analyze_excitement_level(self, text: str) -> float:
        """
        テキストの「高揚度」を算出する。0.0-1.0。

        Returns:
            高揚度スコア
        """
        score = 0.5  # ベースライン

        for pattern, weight in self.EXCITEMENT_BOOSTER_PATTERNS:
            if pattern in text:
                score += weight

        for pattern, weight in self.MONOTONY_PATTERNS:
            if pattern in text:
                score -= weight

        return max(0.0, min(1.0, score))
```

---

### Step 42: `src/agents/reader_simulator.py` — `simulate_reader_response` に高揚度追加

**対象ファイル**: `src/agents/reader_simulator.py`

**変更内容**:
`simulate_reader_response` メソッドの返り値に高揚度を追加する。

```python
    def simulate_reader_response(self, text: str) -> Dict[str, any]:
        """読者反応の全体的シミュレーションを行う。"""
        boredom_issues = self.analyze_boredom(text)
        engagement = self.analyze_engagement(text)
        excitement_level = self.analyze_excitement_level(text)

        boredom_penalty = len(boredom_issues) * 0.05
        overall_score = max(0.0, engagement["engagement_score"] - boredom_penalty)

        recommendations = []
        if overall_score < 0.5:
            recommendations.append("退屈ポイントの修正を検討してください")
        if excitement_level < 0.4:
            recommendations.append("展開に刺激を追加してください（疑問符、感嘆符、 контраст 等）")
        if len(boredom_issues) > 3:
            recommendations.append("文章の展開を早めるか、对话を差し込んでください")
        if engagement["engagement_score"] < 0.3:
            recommendations.append("惹きつけ要素を追加してください")

        return {
            "boredom_issues": boredom_issues,
            "engagement": engagement,
            "excitement_level": excitement_level,
            "overall_score": overall_score,
            "recommendations": recommendations,
        }
```

---

### Step 43: `tests/test_reader_simulator.py` — 高揚度テスト追加

**対象ファイル**: `tests/test_reader_simulator.py`

**変更内容**:
末尾に以下を追加する。

```python
def test_analyze_excitement_level():
    simulator = ReaderSimulator()
    # 高い高揚度
    exciting_text = "突然、彼女は叫んだ！「来るな！」"
    level = simulator.analyze_excitement_level(exciting_text)
    assert level > 0.5

    # 低い高揚度
    boring_text = "静寂が二人を包んでいた。時間が流れる。何も変わらない。"
    level = simulator.analyze_excitement_level(boring_text)
    assert level < 0.5


def test_simulate_reader_response_includes_excitement():
    simulator = ReaderSimulator()
    text = "静寂が二人を包んでいた。"
    result = simulator.simulate_reader_response(text)
    assert "excitement_level" in result
    assert 0.0 <= result["excitement_level"] <= 1.0
```

---

### Step 44: `src/services/plot_quality_reporter.py` — 高揚度をレポートに追加

**対象ファイル**: `src/services/plot_quality_reporter.py`

**変更内容**:
`generate_report` メソッドの返す辞書に `excitement_level` を追加する。

```python
def generate_report(self, plot_text: str, erotic_intensity: int = 3) -> Dict[str, any]:
    """プロットの総合品質レポートを生成する。"""
    reader_result = self.analyzer.analyze_plot(plot_text)
    diversity_score = compute_diversity_score(plot_text, METAPHOR_BANK)
    diversity_class = classify_diversity(diversity_score)

    boredom_score = 1.0 - min(1.0, len(reader_result["boredom_issues"]) * 0.05)
    excitement_level = reader_result.get("excitement_level", 0.5)

    overall_score = (
        reader_result["overall_score"] * 0.45 +
        diversity_score * 0.25 +
        boredom_score * 0.15 +
        excitement_level * 0.15
    )
    # ...
    return {
        "overall_score": round(overall_score, 3),
        "reader_response": reader_result,
        "vocabulary_diversity": round(diversity_score, 3),
        "diversity_class": diversity_class,
        "boredom_count": len(reader_result["boredom_issues"]),
        "excitement_level": round(excitement_level, 3),
        "recommendations": recommendations,
        "summary": summary,
    }
```

---

### Step 45: `src/services/auto_editor.py` — 高揚度ブースター注入機能追加

**対象ファイル**: `src/services/auto_editor.py`

**変更内容**:
`AutoEditor` クラスに以下を追加する。

```python
    def inject_excitement_booster(self, paragraph_text: str) -> str:
        """
        単調な段落に高揚度ブースターを注入する。

        Returns:
            修正後のテキスト
        """
        if len(paragraph_text) < 50:
            return paragraph_text

        import random
        boosters = [
            "だが、その時 —",
            "突然、状況が変わった。",
            "否応なく、彼女は...",  # Not appropriate, replace
            "彼の視線が動いた。",
            "緊張が走る。",
        ]

        # 段落の冒頭に注入
        booster = random.choice(boosters)
        return f"{booster}\n\n{paragraph_text}"
```

---

### Step 46: `src/services/auto_editor.py` — `auto_edit` に高揚度ブースター注入追加

**対象ファイル**: `src/services/auto_editor.py`

**変更内容**:
`auto_edit` メソッドの `edits_applied` ロジックに以下を追加する。

```python
# 高揚度ブースターの注入（退屈だが短すぎる段落向け）
for idx in boring_indices:
    if idx >= len(modified_paragraphs):
        continue
    para = modified_paragraphs[idx]
    if 50 < len(para) <= 150 and "\n" not in para and "」" not in para:
        # 高揚度ブースターを注入
        modified = self.inject_excitement_booster(para)
        if modified != para:
            modified_paragraphs[idx] = modified
            edits_applied.append(f"段落{idx+1}: 高揚度ブースター注入")
```

---

### Step 47: `tests/test_auto_editor.py` — 高揚度ブースター侵入テスト追加

**対象ファイル**: `tests/test_auto_editor.py`

**変更内容**:
末尾に以下を追加する。

```python
def test_inject_excitement_booster():
    editor = AutoEditor()
    para = "静寂が二人を包んでいた。"
    modified = editor.inject_excitement_booster(para)
    assert modified != para
    assert any(booster in modified for booster in editor.PACING_BREAK_PHRASES)


def test_auto_edit_includes_excitement_booster():
    editor = AutoEditor()
    text = "静寂が二人を包んでいた。" * 5
    result = editor.auto_edit(text)
    assert any("高揚度" in e or "pace" in e.lower() for e in result["edits_applied"])
```

---

### Step 48: `src/services/plot_quality_reporter.py` — 最終確認テスト

**対象ファイル**: `src/services/plot_quality_reporter.py`

**変更内容**:
`generate_report` のdocstringに以下を追記する。

```python
def generate_report(self, plot_text: str, erotic_intensity: int = 3) -> Dict[str, any]:
    """
    プロットの総合品質レポートを生成する。

    評価軸:
        - 読者反応（overall_score, boredom_count）
        - 快感語彙多様性（vocabulary_diversity）
        - 退屈ポイント（boredom_count）
        - 高揚度（excitement_level）

    Returns:
        {
            "overall_score": float,
            "reader_response": {...},
            "vocabulary_diversity": float,
            "diversity_class": str,
            "boredom_count": int,
            "excitement_level": float,
            "recommendations": List[str],
            "summary": str,
        }

    See Also:
        ReaderSimulator: 読者反応シミュレーション
        AutoEditor: 自動編集サービス
    """
```

---

## ステップ一覧表

| Step | 対象ファイル | 概要 |
|------|-------------|------|
| 1 | 新規 `config/pleasure_vocabulary.py` | 基本快感語彙ファイル作成 |
| 2 | 新規 `src/services/pleasure_vocabulary_selector.py` | 語彙選択サービス |
| 3 | `config/pleasure_vocabulary.py` | `__all__` への追加確認 |
| 4 | `config/pleasure_vocabulary.py` | `get_pleasure_vocabulary` 関数追加 |
| 5 | `src/engine/prompts/erotic_specialist.py` | 快感語彙選択のインポート追加 |
| 6 | `src/engine/prompts/erotic_specialist.py` | `build_scene_prompt` に快感語彙注入 |
| 7 | `prompts/erotic/scene_templates.py` | 快感テンプレートセクション追加 |
| 8 | `src/engine/prompts/erotic_specialist.py` | `build_aftercare_prompt` への快感語彙追加 |
| 9 | 新規 `tests/test_pleasure_vocabulary.py` | 基本テスト |
| 10 | 新規 `tests/test_pleasure_vocabulary_selector.py` | 選択サービステスト |
| 11 | `src/services/erotic_diversity_score.py` | 快感語彙の多様性評価追加 |
| 12 | `tests/test_erotic_workflow.py` | 快感多様性テスト追加 |
| 13 | `src/engine/prompts/erotic_specialist.py` | docstring に快感語彙注記 |
| 14 | `src/agents/erotic_integrity.py` | 快感語彙の多様性チェック追加 |
| 15 | `src/backend/workflows/refine_erotic_workflow.py` | 快感多様性検証の組み込み |
| 16 | `tests/test_erotic_workflow.py` | 快感多様性検証テスト追加 |
| 17 | `src/services/erotic_diversity_score.py` | `check_diversity` に快感語彙チェック追加 |
| 18 | `config/pleasure_vocabulary.py` | 例外時フォールバック追加 |
| 19 | `src/engine/prompts/erotic_specialist.py` | 例外処理の追加 |
| 20 | `tests/test_erotic_workflow.py` | pleasure_score 含むテスト追加 |
| 21 | `src/services/erotic_diversity_score.py` | 型ヒント追加 |
| 22 | `config/pleasure_vocabulary.py` | `Final` 型ヒント追加 |
| 23 | `tests/test_erotic_workflow.py` | 快感語彙の多様性を確認するテスト追加 |
| 24 | `src/services/erotic_diversity_score.py` | docstring 注記追加 |
| 25 | 新規 `src/agents/reader_simulator.py` | 読者エージェント基本クラス |
| 26 | `src/agents/__init__.py` | `ReaderSimulator` エクスポート追加 |
| 27 | 新規 `src/services/reader_pacing_analyzer.py` | テンポ分析サービス |
| 28 | `src/services/__init__.py` | `ReaderPacingAnalyzer` エクスポート追加 |
| 29 | 新規 `tests/test_reader_simulator.py` | 基本テスト |
| 30 | 新規 `tests/test_reader_pacing_analyzer.py` | テンポ分析テスト |
| 31 | `src/backend/workflows/refine_erotic_workflow.py` | 読者シミュレーショ組み込み |
| 32 | 新規 `src/services/plot_quality_reporter.py` | 品質レポート生成サービス |
| 33 | `src/services/__init__.py` | `PlotQualityReporter` エクスポート追加 |
| 34 | 新規 `tests/test_plot_quality_reporter.py` | 品質レポートテスト |
| 35 | `src/agents/writing.py` | 読者シミュレーション結果のログ追加 |
| 36 | 新規 `src/services/auto_editor.py` | 自動編集サービス |
| 37 | `src/services/__init__.py` | `AutoEditor` エクスポート追加 |
| 38 | 新規 `tests/test_auto_editor.py` | 自動編集テスト |
| 39 | `src/backend/workflows/refine_erotic_workflow.py` | 自動編集組み込み |
| 40 | `tests/test_erotic_workflow.py` | 読者シミュレーション統合テスト追加 |
| 41 | `src/agents/reader_simulator.py` | 感情的高揚時・低落時パター追加追加 |
| 42 | `src/agents/reader_simulator.py` | `simulate_reader_response` に高揚度追加 |
| 43 | `tests/test_reader_simulator.py` | 高揚度テスト追加 |
| 44 | `src/services/plot_quality_reporter.py` | 高揚度をレポートに追加 |
| 45 | `src/services/auto_editor.py` | 高揚度ブースター注入機能追加 |
| 46 | `src/services/auto_editor.py` | `auto_edit` に高揚度ブースター注入追加 |
| 47 | `tests/test_auto_editor.py` | 高揚度ブースター注入テスト追加 |
| 48 | `src/services/plot_quality_reporter.py` | 最終確認テスト・docstring 注記追加 |

---

## 依存グラフ

```
# 快感キーワードの多様化 (Steps 1-24)
Step1 (pleasure_vocabulary.py) ──┬──→ Step2 (pleasure_vocabulary_selector)
                                 ├──→ Step4 (get_pleasure_vocabulary)
                                 ├──→ Step9/10 (tests)
                                 └──→ Step11 (erotic_diversity_score ext)

Step5/6/7/8 (erotic_specialist) ──→ Step13/19 (docstring & exception)
                                 ──→ Step17 (check_diversity integration)

Step11 (diversity_score ext) ────→ Step12/16 (tests)
                                 ──→ Step17 (check_diversity update)

Step14 (erotic_integrity ext) ───→ Step15 (refine_erotic_workflow)
                                 ──→ Step16 (tests)

# 読者反応の擬似シミュレーション (Steps 25-48)
Step25 (reader_simulator) ────────→ Step26 (exports)
                                ──→ Step29 (tests)

Step27 (reader_pacing_analyzer) ──→ Step28 (exports)
                                ──→ Step30 (tests)

Step32 (plot_quality_reporter) ──→ Step27/28 (ReaderPacingAnalyzer)
                                ──→ Step11 (diversity_score)
                                ──→ Step33/34 (exports & tests)

Step36 (auto_editor) ─────────────→ Step27 (ReaderPacingAnalyzer)
                                ──→ Step37/38 (exports & tests)

Step31 (refine_erotic_workflow) ──→ Step27/32 (pacing & quality)
                                ──→ Step39 (auto_edit integration)

Step41/42 (excitement patterns) ──→ Step43 (tests)
                                ──→ Step44 (plot_quality_reporter update)
                                ──→ Step45/46 (auto_editor update)
                                ──→ Step47 (tests)
```

---

## 推奨実装順

1. **Phase 1（Steps 1-12）**: 快感語彙の基本構造構築 → プロンプトへの注入 → 多様性評価テスト
2. **Phase 2（Steps 13-20）**: 整合性チェック統合 → 例外処理 → テスト強化
3. **Phase 3（Steps 21-24）**: 型安全性向上 → 最終確認
4. **Phase 4（Steps 25-30）**: 読者エージェント基本クラス → テンポ分析サービス → テスト
5. **Phase 5（Steps 31-35）**: ワークフロー組み込み → 品質レポート → ログ追加
6. **Phase 6（Steps 36-40）**: 自動編集サービス → ワークフロー統合 → 統合テスト
7. **Phase 7（Steps 41-48）**: 高揚度パターン追加 → 品質レポート更新 → ブースター注入 → 最終テスト

各 Phase 内でステップ番号順に実装すると安全。