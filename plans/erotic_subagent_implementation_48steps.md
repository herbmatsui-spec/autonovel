# 官能A改善 48ステップ実装計画

## 概要

9つの改善案を低性能LLMでも実装可能な粒度（1ステップ≒1ファイル・1関数レベル）に分解した実装計画。

---

## 改善案 #1: ボキャブラリ拡張（Steps 1-8）

### Step 1: `config/erotic_vocabulary.py` — `METAPHOR_BANK` を15→30個に増加

**対象ファイル**: `config/erotic_vocabulary.py`

**変更内容**:
`METAPHOR_BANK` に以下15個を追加する（既存の10個と合わせて25個になる）。

```python
METAPHOR_BANK = [
    # 既存10個（省略なし、そのままで）
    "肌を陶磁の表面に似せる",
    "欲望を逆向きの波に例える",
    "呼吸を風の流れに例える",
    "瞳を星の瞬きに例える",
    "体温を夕暮れの大地に例える",
    "声を風鈴の音に例える",
    "影を夕闇に例える",
    "笑顔を朝日のように例える",
    "背徳感を闇の底に例える",
    "官能を月光に例える",
    # 新規15個
    "絹のような髪の流れ",
    "脈打つ熱量の伝播",
    "溶け合う輪郭の境界",
    "沈黙が震えるほどの緊張",
    "吐息が混じり合う距離",
    "駆け引きの終わる瞬間",
    "抗えない引力のように",
    "燃え上がる血液の赤",
    "失衡する世界の中心",
    "言葉にならない渴きが満ちる",
    "濡れるような静寂",
    "焦がれるような未練",
    "崩れる理性の大厦",
    "凍てつく空気が熱を帯びる",
    "闇が二人を包み込む",
]
```

**確認**: `len(METAPHOR_BANK)` が25になっていることを `python -c "from config.erotic_vocabulary import METAPHOR_BANK; print(len(METAPHOR_BANK))"` で確認する。

---

### Step 2: `config/erotic_vocabulary.py` — `ONOMATOPOEIA_BANK` を10→25個に増加

**対象ファイル**: `config/erotic_vocabulary.py`

**変更内容**:
`ONOMATOPOEIA_BANK` に以下15個を追加。

```python
ONOMATOPOEIA_BANK = [
    # 既存10個
    "呼吸の微かな音",
    "衣の擦れ音",
    "足音の静かなリズム",
    "呼吸の乱れ",
    "肌に触れる微かな感触",
    "呼吸の深さ",
    "静寂の沈黙",
    "微かな汗の匂い",
    "衣装の摩擦音",
    "心臓の鼓動",
    # 新規15個
    "髪が擦れる微かな音",
    "肌と肌の温度差が消える瞬間",
    "重なる影の輪郭",
    " textiles の滑らかな感触",
    "乱れる脈拍の音",
    "吐息の温もりが唇に届く",
    "動くことが怖い静けさ",
    "解ける髪の結び目",
    "汗ばむ肌の艶",
    "重なる二つの影",
    "緩慢になる時間",
    "押し殺した声",
    "薄い布地に残る体温",
    "乱れた髪が額にかかる",
    "近づく二つの重心",
]
```

---

### Step 3: `config/erotic_vocabulary.py` — `PSYCHOLOGY_TEMPLATES` を10→25個に増加

**対象ファイル**: `config/erotic_vocabulary.py`

**変更内容**:
`PSYCHOLOGY_TEMPLATES` に以下15個を追加。

```python
PSYCHOLOGY_TEMPLATES = [
    # 既存10個
    "陶酔の境界線",
    "自失の瞬間",
    "背徳感の消失",
    "解き放ちの瞬間",
    "心の奥底への旅",
    "欲望の芽生え",
    "禁断の誘惑",
    "心の奥底への探求",
    "感情の波紋",
    "心の距離の縮小",
    # 新規15個
    "理性の糸が切れる瞬間",
    "抗えない波の音",
    "世界が二人だけになる感覚",
    "凍りついた時間が動き出す",
    "信頼の危うい均衡",
    "隠していた想いの溢出",
    "試される心の限界",
    "抗うことと拒めないこと",
    "自分でも知らない自分の発見",
    "言葉にならない充足感",
    "抗えない下降",
    "抗う力の源泉の消失",
    "脆い精神の防御線",
    "甘い自救の構造",
    "抗えない共鳴",
]
```

---

### Step 4: `config/erotic_vocabulary.py` — `"full"` tier のボキャブラリ数を35個に拡大

**対象ファイル**: `config/erotic_vocabulary.py`

**変更内容**:
`VOCABULARY_TIERS["full"]` を以下のように拡張する。

```python
"full": {
    "metaphors": METAPHOR_BANK + [
        # 既存extended分（2個）+ 新規8個 = 計35個以上のmetaphors
        "潮の満ち引きに例える情動",
        "溶岩のように広がる体温",
        "抗えない重力の指向",
        "崩れ落ちる白い壁",
        "熱を帯びた沈黙の叫び",
        "二人のリズムが一つになる瞬間",
        "世界が遠のく感覚",
        "凍てつく空気の崩壊",
    ],
    "onomatopoeia": ONOMATOPOEIA_BANK + [
        "荒い呼吸の連なり",
        "肌と肌が触れ合う微音",
        "乱れる髪の感触",
        "触れ合う肌の温度差",
        "崩れ落ちる緊張",
    ],
    "psychology": PSYCHOLOGY_TEMPLATES + [
        "境界の消失",
        "自我の融解",
        "世界との境界の曖昧化",
        "抗えない下降の記録",
        "時間感覚の消失",
    ],
},
```

**確認**: `python -c "from config.erotic_vocabulary import get_vocabulary_for_tier; v=get_vocabulary_for_tier('full'); print(len(v['metaphors']), len(v['onomatopoeia']), len(v['psychology']))"` で35/30/20以上を確認。

---

### Step 5: 新規 `config/erotic_vocabulary_ext.py` — `"intense"` tier の追加

**対象ファイル**: 新規 `config/erotic_vocabulary_ext.py`

**内容**:

```python
"""
config/erotic_vocabulary_ext.py
intense tier — 強度5専用の追加ボキャブラリ（full + α）
"""
from config.erotic_vocabulary import METAPHOR_BANK, ONOMATOPOEIA_BANK, PSYCHOLOGY_TEMPLATES

INTENSE_METAPHORS = [
    "抗えない重力の指向",
    "崩れ落ちる白い壁",
    "熱を帯びた沈黙の叫び",
    "二人のリズムが一つになる瞬間",
    "世界が遠のく感覚",
    "凍てつく空気の崩壊",
    "失衡する宇宙の核心",
    "溶け合う魂の輪郭",
    "無法なまでの親密",
    "燃え尽きる火の強さ",
]

INTENSE_ONOMATOPOEIA = [
    "崩れ落ちる緊張",
    "触れ合う肌の温度差",
    "乱れる髪の感触",
    "肌の上で乱れる呼吸",
    "混ざり合う二人の体温",
]

INTENSE_PSYCHOLOGY = [
    "世界との境界の消滅",
    "抗えない下降の渦",
    "時間感覚の崩壊",
    "自我の完全なる融解",
    "無法な充足の渦",
]

VOCABULARY_TIERS_EXT = {
    "intense": {
        "metaphors": METAPHOR_BANK + INTENSE_METAPHORS,
        "onomatopoeia": ONOMATOPOEIA_BANK + INTENSE_ONOMATOPOEIA,
        "psychology": PSYCHOLOGY_TEMPLATES + INTENSE_PSYCHOLOGY,
    }
}

def get_vocabulary_for_tier_ext(tier: str) -> dict:
    from config.erotic_vocabulary import get_vocabulary_for_tier
    if tier == "intense":
        return VOCABULARY_TIERS_EXT["intense"]
    return get_vocabulary_for_tier(tier)
```

---

### Step 6: `config/erotic_platform_presets.py` — `intense` tier の許可追加

**対象ファイル**: `config/erotic_platform_presets.py`

**変更内容**:
`adult_selfhost` プリセットの `allowed_vocabulary_tier` を `"full"` → `"intense"` に変更し、`max_intensity: 5` でも `intense` が使えるようにする。

```python
"adult_selfhost": {
    "name": "自サイト/フル表現",
    "max_intensity": 5,
    "allowed_vocabulary_tier": "intense",   # "full" から変更
    "censorship_mode": "none",
    "description": "表現の制限なし（倫理ガードラインのみ適用）",
},
```

---

### Step 7: `config/erotic_vocabulary.py` — `"mild"` tier を10個に整理

**対象ファイル**: `config/erotic_vocabulary.py`

**変更内容**:
`VOCABULARY_TIERS["mild"]` を以下のように再定義し、10個確保する。

```python
"mild": {
    "metaphors": METAPHOR_BANK[:5] + ["影を夕闇に例える", "笑顔を朝日のように例える", "声を風鈴の音に例える", "体温を夕暮れの大地に例える", "瞳を星の瞬きに例える"],
    "onomatopoeia": ONOMATOPOEIA_BANK[:5] + ["静寂の沈黙", "心臓の鼓動", "衣の擦れ音", "呼吸の微かな音", "足音の静かなリズム"],
    "psychology": PSYCHOLOGY_TEMPLATES[:5] + ["心の距離の縮小", "感情の波紋", "禁断の誘惑", "欲望の芽生え", "心の奥底への探求"],
},
```

**確認**: `python -c "from config.erotic_vocabulary import get_vocabulary_for_tier; v=get_vocabulary_for_tier('mild'); print(len(v['metaphors']))"` が10以上を確認。

---

### Step 8: `config/erotic_vocabulary.py` — 型ヒントとドキュメント追加

**対象ファイル**: `config/erotic_vocabulary.py`

**変更内容**:
ファイル冒頭に以下を追加し、型安全性を高める。

```python
from typing import Dict, List

# METAPHOR_BANK: 官能を比喩で表現するための視覚的・触覚的アナロジー
# ONOMATOPOEIA_BANK: 五感で捕捉できる音・触感・匂いのリスト
# PSYCHOLOGY_TEMPLATES: 心理状態を抽象化する上位概念のリスト
# 各リストは random.choices(population, k=N) で利用されることを想定
```

`get_vocabulary_for_tier` 関数の返り値に `-> dict` 型ヒントを付与する（すでに付与されていれば変更不要）。

---

## 改善案 #2: エントロピースコア閾値定義（Steps 9-14）

### Step 9: 新規 `config/erotic_thresholds.py` — 閾値定数ファイルの作成

**対象ファイル**: 新規 `config/erotic_thresholds.py`

**内容**:

```python
"""
config/erotic_thresholds.py
官能関連のスコア閾値を定義する。
閾値は人間評価との照合により定期校正される。
"""

# 多様性スコア閾値（erotic_diversity_score 戻り値 0.0-1.0）
DIVERSITY_SCORE_PASS = 0.5   # この値以上就是「良好」
DIVERSITY_SCORE_WARN = 0.3   # この値以上0.5未満は「要改善」
DIVERSITY_SCORE_FAIL = 0.3  # この値未満は「不合格」

# 強度閾値
INTENSITY_R15 = 3           # R15相当（官能A）の下限
INTENSITY_SAFE_MAX = 2      # セーフティ範囲の上限
INTENSITY_EXTREME = 5       # 過激表現の下限

# afterglow 品質閾値
AFTERGLOW_MIN_PARAGRAPHS = 2    # 最低段落数
AFTERGLOW_MIN_CHARS = 400      # 最低文字数

# 衣装整合性閾値
MAX_CONSECUTIVE_PEAK_EPISODES = 2  # 連続ピーク話数の上限（erotic_density_controller.pyと重複注意）
```

**補足**: `MAX_CONSECUTIVE_PEAK_EPISODES` は `erotic_density_controller.py` と重複するため、両方を同じ定数を参照するよう later Stepで統合する。

---

### Step 10: `src/services/erotic_diversity_score.py` — 閾値分類ラッパ関数追加

**対象ファイル**: `src/services/erotic_diversity_score.py`

**変更内容**:
ファイル末尾に以下を追加する。

```python
from config.erotic_thresholds import DIVERSITY_SCORE_PASS, DIVERSITY_SCORE_WARN, DIVERSITY_SCORE_FAIL

def classify_diversity(score: float) -> str:
    """多様性スコアを閾値に基づいて分類する。"""
    if score >= DIVERSITY_SCORE_PASS:
        return "pass"
    elif score >= DIVERSITY_SCORE_WARN:
        return "warn"
    else:
        return "fail"

def check_diversity(text: str, vocabulary_bank: list) -> dict:
    """スコア計算と分類を一度に行うユーティリティ。"""
    score = compute_diversity_score(text, vocabulary_bank)
    classification = classify_diversity(score)
    warnings = check_repetition(text, vocabulary_bank, max_repeat=3)
    return {
        "score": score,
        "classification": classification,
        "warnings": warnings,
    }
```

---

### Step 11: `src/services/erotic_diversity_score.py` — 閾値設定のエクスポート確認

**対象ファイル**: `src/services/erotic_diversity_score.py`

**変更内容**:
`compute_diversity_score` 関数冒頭の docstring に閾値に関する注意書きを追加。

```python
def compute_diversity_score(text: str, vocabulary_bank: List[str]) -> float:
    """
    テキスト中のボキャブラリー使用の多様性をエントロピーで算出する。0.0-1.0。

    閾値:
        - 0.5以上: 良好 (pass)
        - 0.3-0.5: 要改善 (warn)
        - 0.3未満: 不合格 (fail)

    See Also:
        classify_diversity(): 閾値による分類を行うユーティリティ
    """
```

---

### Step 12: `tests/test_erotic_workflow.py` — 閾値分類テスト追加

**対象ファイル**: `tests/test_erotic_workflow.py`

**変更内容**:
ファイル末尾に以下を追加する。

```python
def test_diversity_classify():
    from src.services.erotic_diversity_score import classify_diversity
    assert classify_diversity(0.6) == "pass"
    assert classify_diversity(0.4) == "warn"
    assert classify_diversity(0.2) == "fail"
    assert classify_diversity(0.5) == "pass"

def test_diversity_check():
    from src.services.erotic_diversity_score import check_diversity
    from config.erotic_vocabulary import METAPHOR_BANK
    result = check_diversity("瞳を星の瞬きに例える 声が風鈴の音に例える", METAPHOR_BANK)
    assert "score" in result
    assert "classification" in result
    assert "warnings" in result
```

---

### Step 13: 新規 `tests/test_erotic_thresholds.py` — 閾値ファイルのユニットテスト

**対象ファイル**: 新規 `tests/test_erotic_thresholds.py`

**内容**:

```python
"""tests/test_erotic_thresholds.py"""
import pytest
from config.erotic_thresholds import (
    DIVERSITY_SCORE_PASS,
    DIVERSITY_SCORE_WARN,
    DIVERSITY_SCORE_FAIL,
    INTENSITY_R15,
    INTENSITY_SAFE_MAX,
    AFTERGLOW_MIN_PARAGRAPHS,
    AFTERGLOW_MIN_CHARS,
)

def test_diversity_thresholds_order():
    assert DIVERSITY_SCORE_PASS > DIVERSITY_SCORE_WARN >= DIVERSITY_SCORE_FAIL

def test_intensity_order():
    assert INTENSITY_SAFE_MAX < INTENSITY_R15

def test_afterglow_thresholds():
    assert AFTERGLOW_MIN_PARAGRAPHS >= 2
    assert AFTERGLOW_MIN_CHARS >= 400
```

---

### Step 14: `config/erotic_thresholds.py` — `__all__` と型ヒント追加

**対象ファイル**: `config/erotic_thresholds.py`

**変更内容**:

```python
from typing import Final

DIVERSITY_SCORE_PASS: Final[float] = 0.5
DIVERSITY_SCORE_WARN: Final[float] = 0.3
DIVERSITY_SCORE_FAIL: Final[float] = 0.3
INTENSITY_R15: Final[int] = 3
INTENSITY_SAFE_MAX: Final[int] = 2
INTENSITY_EXTREME: Final[int] = 5
AFTERGLOW_MIN_PARAGRAPHS: Final[int] = 2
AFTERGLOW_MIN_CHARS: Final[int] = 400
MAX_CONSECUTIVE_PEAK_EPISODES: Final[int] = 2

__all__ = [
    "DIVERSITY_SCORE_PASS",
    "DIVERSITY_SCORE_WARN",
    "DIVERSITY_SCORE_FAIL",
    "INTENSITY_R15",
    "INTENSITY_SAFE_MAX",
    "INTENSITY_EXTREME",
    "AFTERGLOW_MIN_PARAGRAPHS",
    "AFTERGLOW_MIN_CHARS",
    "MAX_CONSECUTIVE_PEAK_EPISODES",
]
```

---

## 改善案 #3: consent_state 動的検証（Steps 15-20）

### Step 15: `src/agents/erotic_integrity.py` — `consent_state` 検証メソッド追加

**対象ファイル**: `src/agents/erotic_integrity.py`

**変更内容**:
ファイル冒頭に以下を追加し、`EroticIntegrityChecker` クラスに検証ロジックを実装する。

```python
# 同意確認キーワード（明示的）
CONSENT_EXPLICIT_KEYWORDS = ["同意", "了承", "承諾", "OK", "いいよ", "求めて", "欲しい", "させて"]
# 同意確認キーワード（暗黙的）
CONSENT_IMPLICIT_KEYWORDS = ["促す", "引き寄せる", "唇が触れる", "近づく", "体が触れる", "手を伸ばす"]
# 拒否・不同意キーワード
CONSENT_REFUSAL_KEYWORDS = ["嫌", "やだ", "断る", "拒否", "抗拒", "逃げる", "拒む"]
```

`check_clothing_consistency` メソッドの後に以下のメソッドを追加する。

```python
def check_consent_state(self, scene_text: str, declared_consent: str = "implicit") -> Tuple[bool, List[str]]:
    """
    シーン内の同意表現是否符合 declared_consent を検証する。

    Args:
        scene_text: 検証対象テキスト
        declared_consent: "explicit" | "implicit" | "established"

    Returns:
        (is_ok, issues)
    """
    issues: List[str] = []

    explicit_count = sum(scene_text.count(kw) for kw in CONSENT_EXPLICIT_KEYWORDS)
    implicit_count = sum(scene_text.count(kw) for kw in CONSENT_IMPLICIT_KEYWORDS)
    refusal_count = sum(scene_text.count(kw) for kw in CONSENT_REFUSAL_KEYWORDS)

    if refusal_count > 0:
        issues.append(f"拒否表現が{refusal_count}箇所検出されました（同意確認が必要です）")

    if declared_consent == "explicit":
        if explicit_count == 0 and implicit_count == 0:
            issues.append("明示的同意が宣言されているが、同意表現が検出されなかった")
    elif declared_consent == "implicit":
        if explicit_count == 0 and implicit_count == 0:
            issues.append("暗黙的同意が宣言されているが、同意表現が検出されなかった")

    return len(issues) == 0, issues
```

---

### Step 16: `src/agents/erotic_integrity.py` — `check_all` に consent 検証を組み込む

**対象ファイル**: `src/agents/erotic_integrity.py`

**変更内容**:
`check_all` メソッドを以下のように変更する。

```python
def check_all(self, scene_text: str, consent_state: str = "implicit") -> Tuple[bool, List[str]]:
    """
    全整合性チェックを実行する。

    Args:
        scene_text: 検証対象テキスト
        consent_state: "explicit" | "implicit" | "established"
    """
    all_issues: List[str] = []
    _, clothing_issues = self.check_clothing_consistency(scene_text)
    all_issues.extend(clothing_issues)
    _, consent_issues = self.check_consent_state(scene_text, consent_state)
    all_issues.extend(consent_issues)
    return len(all_issues) == 0, all_issues
```

---

### Step 17: `config/erotic_pacing.py` — `EroticBeat` に `consent_state` デフォルト追加

**対象ファイル**: `config/erotic_pacing.py`

**変更内容**:
`EroticBeat` dataclass の `consent_state` フィールドにデフォルト値 `"implicit"` を追加する。

```python
@dataclass
class EroticBeat:
    phase: Literal["build", "peak", "afterglow"]
    desire_level: int           # 0-100
    sensory_focus: List[str]    # ["touch", "scent", "breath", "gaze", "sound"]
    consent_state: str = "implicit"  # デフォルトを implicit に
```

**注意**: `create_default` メソッドで明示的に指定しているので後方互換性は維持される。デフォルト値追加は安全。

---

### Step 18: `src/backend/workflows/refine_erotic_workflow.py` — consent_state 検証の呼び出し追加

**対象ファイル**: `src/backend/workflows/refine_erotic_workflow.py`

**変更内容**:
`execute` メソッド内の整合性チェック部分で、`consent_state` を渡すように変更する。

```python
# 3. 整合性チェック (EroticIntegrityChecker)
from src.agents.erotic_integrity import EroticIntegrityChecker
from config.erotic_pacing import EroticCurve
checker = EroticIntegrityChecker()
curve = EroticCurve.create_default(intensity)
peak_beat = curve.get_peak_beat()
declared_consent = peak_beat.consent_state if peak_beat else "implicit"
is_ok, issues = checker.check_all(refined_content, declared_consent)
```

---

### Step 19: `tests/test_erotic_workflow.py` — consent 検証テスト追加

**対象ファイル**: `tests/test_erotic_workflow.py`

**変更内容**:
末尾に以下を追加する。

```python
def test_consent_explicit_detected():
    checker = EroticIntegrityChecker()
    ok, issues = checker.check_consent_state("彼が同意を求めて、彼女がOKと言った", "explicit")
    assert ok is True

def test_consent_explicit_missing():
    checker = EroticIntegrityChecker()
    ok, issues = checker.check_consent_state("二人は黙って近づいた", "explicit")
    assert ok is False
    assert any("明示的同意" in i for i in issues)

def test_consent_refusal_detected():
    checker = EroticIntegrityChecker()
    ok, issues = checker.check_consent_state("彼女は嫌だと言い、逃げた", "implicit")
    assert ok is False
    assert any("拒否表現" in i for i in issues)

def test_consent_implicit_ok():
    checker = EroticIntegrityChecker()
    ok, issues = checker.check_consent_state("二人は促し合い、唇が触れた", "implicit")
    assert ok is True
```

---

### Step 20: `src/agents/erotic_integrity.py` — ファイル末尾にキーワードリストを移動確認

**対象ファイル**: `src/agents/erotic_integrity.py`

**変更内容**:
`CONSENT_*_KEYWORDS` 定数群がファイルの `import` 文の直後、`EroticIntegrityChecker` クラスの定義の前に配置されていることを確認する。配置がクラスの内部になってしまった場合は外部に移動する。

現在のファイル構造が以下になっていることを確認する。

```
CONSENT_EXPLICIT_KEYWORDS = [...]
CONSENT_IMPLICIT_KEYWORDS = [...]
CONSENT_REFUSAL_KEYWORDS = [...]

class EroticIntegrityChecker:
    ...
```

---

## 改善案 #4: afterglow 品質評価（Steps 21-28）

### Step 21: 新規 `src/services/erotic_afterglow_evaluator.py` — メイン評価クラス作成

**対象ファイル**: 新規 `src/services/erotic_afterglow_evaluator.py`

**内容**:

```python
"""
src/services/erotic_afterglow_evaluator.py
afterglow フェーズ専用の品質評価サービス
"""
from typing import List, Tuple
import re
from config.erotic_thresholds import AFTERGLOW_MIN_PARAGRAPHS, AFTERGLOW_MIN_CHARS

class AfterglowEvaluator:
    """afterglow フェーズの質评估価を行う。"""

    EMOTIONAL_SETTLING_KEYWORDS = ["沈静", "静けさ", "余韻", "穏やか", "温もり", "安らぎ", "沈降", "静まる"]
    DISTANCE_RECONFIRM_KEYWORDS = ["距離", "近了", "確認", "並べ", "隣", "寄り添う", "離れた"]
    FOREShadow_KEYWORDS = ["次", "話", "伏線", "予感", "接下来", "明らかになる", "待ち望む"]

    def count_paragraphs(self, text: str) -> int:
        """空行で区切られた段落数をカウントする。"""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return len(paragraphs)

    def check_emotional_settling(self, text: str) -> bool:
        """感情の沈降表現が含まれているかチェックする。"""
        return any(kw in text for kw in self.EMOTIONAL_SETTLING_KEYWORDS)

    def check_distance_reconfirm(self, text: str) -> bool:
        """心理的・物理的距離の再確認表現が含まれているかチェックする。"""
        return any(kw in text for kw in self.DISTANCE_RECONFIRM_KEYWORDS)

    def check_foreshadow(self, text: str) -> bool:
        """次話への伏線が含まれているかチェックする。"""
        return any(kw in text for kw in self.FOREShadow_KEYWORDS)

    def evaluate(self, text: str) -> Tuple[bool, List[str]]:
        """
        afterglow テキストを多角的に評価する。

        Returns:
            (is_acceptable, issues): 評価結果と問題リスト
        """
        issues: List[str] = []

        paragraph_count = self.count_paragraphs(text)
        if paragraph_count < AFTERGLOW_MIN_PARAGRAPHS:
            issues.append(f"段落数が不足: {paragraph_count}/{AFTERGLOW_MIN_PARAGRAPHS}")

        char_count = len(text)
        if char_count < AFTERGLOW_MIN_CHARS:
            issues.append(f"文字数が不足: {char_count}/{AFTERGLOW_MIN_CHARS}")

        if not self.check_emotional_settling(text):
            issues.append("感情の沈降表現（余韻・穏やか・温もり等）が含まれていません")

        if not self.check_distance_reconfirm(text):
            issues.append("心理的・物理的距離の再確認表現が含まれていません")

        if not self.check_foreshadow(text):
            issues.append("次話への伏線が含まれていません")

        return len(issues) == 0, issues
```

---

### Step 22: `src/services/erotic_afterglow_evaluator.py` — `__init__.py` へのエクスポート追加

**対象ファイル**: `src/services/__init__.py`（または `src/services/exports.py`  если存在）

**変更内容**:
既存 `__init__.py` 末尾に以下を追加する。

```python
from src.services.erotic_afterglow_evaluator import AfterglowEvaluator
```

または新規 `src/services/exports.py` を作成し、`src/services/__init__.py` から import する。

---

### Step 23: `src/engine/prompts/erotic_specialist.py` — afterglow 品質チェック連携追加

**対象ファイル**: `src/engine/prompts/erotic_specialist.py`

**変更内容**:
`build_aftercare_prompt` メソッドのdocstringに以下を追加する。

```python
def build_aftercare_prompt(self, context: Dict[str, Any]) -> str:
    """
    余韻（afterglow）生成プロンプトを構築する。

    生成後は AfterglowEvaluator.evaluate() で品質検証すること。
    品質閾値: 最低2段落 / 最低400文字 / 感情沈降表現 / 距離再確認表現 / 次話伏線
    """
```

---

### Step 24: `src/backend/workflows/refine_erotic_workflow.py` — afterglow 評価の組み込み

**対象ファイル**: `src/backend/workflows/refine_erotic_workflow.py`

**変更内容**:
`execute` メソッドの研磨処理後に afterglow 評価を追加する。

```python
# 3-2. afterglow 品質評価（peak の後に afterglow がある場合）
from src.services.erotic_afterglow_evaluator import AfterglowEvaluator
evaluator = AfterglowEvaluator()
# afterglow 部分を簡易抽出（最後の 1/4 を afterglow 傾向として評価）
afterglow_start = len(refined_content) * 3 // 4
afterglow_candidate = refined_content[afterglow_start:]
afterglow_ok, afterglow_issues = evaluator.evaluate(afterglow_candidate)

# (existing整合性チェック部分是省略...)
if not afterglow_ok:
    for issue in afterglow_issues:
        reporter.add_log(f"⚠️ afterglow品質警告: {issue}")
```

---

### Step 25: 新規 `tests/test_erotic_afterglow_evaluator.py` — ユニットテスト

**対象ファイル**: 新規 `tests/test_erotic_afterglow_evaluator.py`

**内容**:

```python
"""tests/test_erotic_afterglow_evaluator.py"""
import pytest
from src.services.erotic_afterglow_evaluator import AfterglowEvaluator

def test_afterglow_passes():
    evaluator = AfterglowEvaluator()
    good_text = """
二人の体温がゆっくりと下がっていく。

静寂の中、彼女は彼の肩に頭を預けた。
このまま時間が止まればいいと、二人は同時に思った。

次話への伏線がここに張られる。帝国の陰謀が近づいている。
    """.strip()
    ok, issues = evaluator.evaluate(good_text)
    assert ok is True, issues

def test_afterglow_fails_paragraph_count():
    evaluator = AfterglowEvaluator()
    short_text = "二人の夜が更けていった。" * 20  # ~400文字だが1段落
    ok, issues = evaluator.evaluate(short_text)
    assert ok is False
    assert any("段落数" in i for i in issues)

def test_afterglow_fails_char_count():
    evaluator = AfterglowEvaluator()
    tiny_text = "温もりが残る。" * 5  # 短すぎる
    ok, issues = evaluator.evaluate(tiny_text)
    assert ok is False
    assert any("文字数" in i for i in issues)

def test_afterglow_fails_no_emotional_settling():
    evaluator = AfterglowEvaluator()
    # 段落・文字数は十分だが感情沈降表現なし
    text = ("動き続ける。" * 50 + "\n\n" + "次話への伏線。") * 3
    ok, issues = evaluator.evaluate(text)
    assert ok is False
    assert any("沈降" in i or "余韻" in i for i in issues)

def test_count_paragraphs():
    evaluator = AfterglowEvaluator()
    assert evaluator.count_paragraphs("a\n\nb\n\nc") == 3
    assert evaluator.count_paragraphs("a\n\n\n\nb") == 2  # 空行は無視
```

---

### Step 26: `config/erotic_thresholds.py` — `AFTERGLOW_MIN_PARAGRAPHS` と `AFTERGLOW_MIN_CHARS` の一元管理確認

**対象ファイル**: `config/erotic_thresholds.py`

**変更内容**:
`AfterglowEvaluator` 内_INLINE閾値不使用を確認し、`config.erotic_thresholds` の定数を import して使っていることを確認する。Step 21 で正しく実装済みであることを確認する。

---

### Step 27: `src/engine/prompts/erotic_specialist.py` — `build_scene_prompt` に afterglow 評価結果反映

**対象ファイル**: `src/engine/prompts/erotic_specialist.py`

**変更内容**:
`build_scene_prompt` メソッドの返り値に、afterglow が最低要件を満たすようにテンプレートを調整する。具体的には `SCENE_TEMPLATE_AFTERGLOW` 定数を参照し、生成プロンプト内に最低文字数・段落数を明記する。

```python
# prompts/erotic/scene_templates.py の SCENE_TEMPLATE_AFTERGLOW を以下に変更する
# (Step 28 で対応)
```

---

### Step 28: `prompts/erotic/scene_templates.py` — afterglow テンプレートに品質要件明記

**対象ファイル**: `prompts/erotic/scene_templates.py`

**変更内容**:
`SCENE_TEMPLATE_AFTERGLOW` を以下のように更新する。

```python
SCENE_TEMPLATE_AFTERGLOW = """
【官能シーン: 余韻（Afterglow）フェーズ】
desire_level: {desire_level}/100
sensory_focus: {sensory_focus}
consent_state: {consent_state}

以下のルールに従って「余韻」の描写を生成してください:
- 感情の沈降と身体的な弛緩を描写すること（最低2段落、合計400字以上）
- 二人の距離感の再確認（心理的・物理的）を含めること
- 最低1つ以上の次話への伏線を含めること
- 感情のキーワード（沈静、余韻、温もり、安らぎ、静まる等）を必ず使用すること
"""
```

---

## 改善案 #5: 統合テスト追加（Steps 29-35）

### Step 29: 新規 `tests/integration/test_erotic_full_pipeline.py` — smoke test

**対象ファイル**: 新規 `tests/integration/test_erotic_full_pipeline.py`

**内容**:

```python
"""
tests/integration/test_erotic_full_pipeline.py
官能ワークフローの End-to-End 統合テスト
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from config.erotic_pacing import EroticCurve
from config.erotic_vocabulary import get_vocabulary_for_tier
from config.erotic_platform_presets import get_preset
from src.services.erotic_diversity_score import compute_diversity_score
from src.agents.erotic_integrity import EroticIntegrityChecker
from src.services.erotic_density_controller import EroticDensityController
from formatters.erotic_censor import apply_censorship

def test_erotic_curve_default_r15():
    curve = EroticCurve.create_default(3)
    assert curve.target_intensity == 3
    assert len(curve.beats) == 3
    peak = curve.get_peak_beat()
    assert peak.phase == "peak"
    assert peak.consent_state == "explicit"

def test_vocabulary_tier_intensity_mapping():
    mild = get_vocabulary_for_tier("mild")
    moderate = get_vocabulary_for_tier("moderate")
    full = get_vocabulary_for_tier("full")
    assert len(full["metaphors"]) > len(mild["metaphors"])
    assert len(moderate["metaphors"]) >= len(mild["metaphors"])

def test_nocturn_preset_censorship():
    preset = get_preset("nocturn_novel")
    assert preset["max_intensity"] == 3
    text = "二人の夜は続いた。セックス是不明。"
    censored = apply_censorship(text, "nocturn_novel")
    assert "◆" in censored

def test_adult_preset_no_censorship():
    preset = get_preset("adult_selfhost")
    text = "二人の夜は続いた"
    censored = apply_censorship(text, "adult_selfhost")
    assert "◆" not in censored

def test_density_controller_allow_peak():
    controller = EroticDensityController()
    assert controller.should_allow_peak([1, 2, 3]) is True
    assert controller.should_allow_peak([4, 5]) is False
    assert controller.should_allow_peak([4, 3, 4]) is True  # 3連続でない

def test_integrity_checker_clothing():
    checker = EroticIntegrityChecker()
    ok, issues = checker.check_all("彼女は衣を解いた。静かに横たわる。")
    assert ok is True

def test_integrity_checker_consent_implicit_ok():
    checker = EroticIntegrityChecker()
    ok, issues = checker.check_consent_state("二人は唇が触れる距離まで近づいた", "implicit")
    assert ok is True

def test_diversity_score_compute():
    from config.erotic_vocabulary import METAPHOR_BANK
    text = "瞳を星の瞬きに例える 声が風鈴の音に例える 体温を夕暮れの大地に例える"
    score = compute_diversity_score(text, METAPHOR_BANK)
    assert 0.0 <= score <= 1.0

def test_platform_preset_count():
    from config.erotic_platform_presets import get_preset_names
    names = get_preset_names()
    assert len(names) == 3
    assert "nocturn_novel" in names
    assert "kakuyomu_romance" in names
    assert "adult_selfhost" in names

def test_intensity_scale_r15():
    from config.erotic_thresholds import INTENSITY_R15, INTENSITY_SAFE_MAX, INTENSITY_EXTREME
    assert INTENSITY_SAFE_MAX < INTENSITY_R15 < INTENSITY_EXTREME
```

---

### Step 30: `tests/test_erotic_workflow.py` — 密度管理ケース追加

**対象ファイル**: `tests/test_erotic_workflow.py`

**変更内容**:
以下を末尾に追加する。

```python
def test_density_controller_book_scenario():
    controller = EroticDensityController()
    # Book全10話想定。4,4,4 は3連続なので拒否
    assert controller.should_allow_peak([1, 2, 3, 4, 4, 4]) is False
    # 4,4,3 は2連続なので許可
    assert controller.should_allow_peak([1, 2, 3, 4, 4, 3]) is True
    # 5話目で3 → 4 への上昇は許可（3連続でない）
    assert controller.should_allow_peak([1, 2, 3, 4, 5, 4]) is True

def test_density_controller_recommend_intensity():
    controller = EroticDensityController()
    # 序盤 (20%未満) は2以下に抑制
    assert controller.recommend_intensity(1, 10, 4) <= 2
    # 終盤 (80%超え) は+1
    assert controller.recommend_intensity(9, 10, 4) >= 4
```

---

### Step 31: `tests/integration/test_erotic_full_pipeline.py` — 強度別の閾値分類テスト追加

**対象ファイル**: `tests/integration/test_erotic_full_pipeline.py`

**変更内容**:
末尾に以下を追加する。

```python
def test_diversity_threshold_pass():
    from src.services.erotic_diversity_score import classify_diversity
    assert classify_diversity(0.6) == "pass"

def test_diversity_threshold_warn():
    from src.services.erotic_diversity_score import classify_diversity
    assert classify_diversity(0.4) == "warn"

def test_diversity_threshold_fail():
    from src.services.erotic_diversity_score import classify_diversity
    assert classify_diversity(0.2) == "fail"

def test_avg_intensity():
    controller = EroticDensityController()
    avg = controller.compute_avg_intensity([1, 2, 3, 4, 5])
    assert avg == 3.0
    assert controller.compute_avg_intensity([]) == 0.0
```

---

### Step 32: 新規 `tests/integration/test_erotic_refine_workflow.py` — refine_erotic 統合テスト

**対象ファイル**: 新規 `tests/integration/test_erotic_refine_workflow.py`

**内容**:

```python
"""
tests/integration/test_erotic_refine_workflow.py
refine_erotic_workflow の統合テスト
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

@pytest.mark.asyncio
async def test_refine_erotic_workflow_mock():
    # モックでのみ動作確認（DB不要）
    from src.backend.workflows.refine_erotic_workflow import RefineEroticWorkflow
    from src.backend.background import StatusReporter, ProgressState

    class DummyReporter(StatusReporter):
        def __init__(self):
            super().__init__()
            self.state = ProgressState(is_running=True)
            self.messages = []
            self.logs = []
        def report(self, message, status="info"):
            self.messages.append((status, message))
        def add_log(self, message):
            self.logs.append(message)
        def update_progress(self, *args, **kwargs): pass
        def update_streaming_text(self, *args, **kwargs): pass

    # Mock workflows with dummy chapters
    with patch.object(RefineEroticWorkflow, 'execute', autospec=True) as mock_exec:
        mock_exec.return_value = {
            "success": True,
            "issues": [],
            "is_ok": True,
            "intensity_applied": 3
        }
        result = await mock_exec(None, book_id=1, ep_num=1, intensity=3)
        assert result["success"] is True

def test_metaphor_filter_intensity_3():
    from src.engine.prompts.erotic_specialist import EroticSpecialist
    specialist = EroticSpecialist()
    text = "二人はセックスをした"
    filtered = specialist.metaphor_filter(text, 3)
    assert "セックス" not in filtered
    assert "二人の夜" in filtered or "肌を重ねる" in filtered

def test_metaphor_filter_intensity_2_more_abstract():
    from src.engine.prompts.erotic_specialist import EroticSpecialist
    specialist = EroticSpecialist()
    text = "唇を重ねる"
    filtered = specialist.metaphor_filter(text, 2)
    assert "温もりを確かめ合う" in filtered or "二人の夜" in filtered

def test_metaphor_filter_no_change_for_safe():
    from src.engine.prompts.erotic_specialist import EroticSpecialist
    specialist = EroticSpecialist()
    text = "静かに二人は寄り添った"
    filtered = specialist.metaphor_filter(text, 1)
    assert "セックス" not in filtered
```

---

### Step 33: `tests/test_erotic_workflow.py` — vocabulary full tier 最小数確認テスト

**対象ファイル**: `tests/test_erotic_workflow.py`

**変更内容**:
末尾に追加する。

```python
def test_full_tier_minimum_vocabulary():
    from config.erotic_vocabulary import get_vocabulary_for_tier
    full = get_vocabulary_for_tier("full")
    assert len(full["metaphors"]) >= 30, f"metaphors: {len(full['metaphors'])}"
    assert len(full["onomatopoeia"]) >= 25, f"onomatopoeia: {len(full['onomatopoeia'])}"
    assert len(full["psychology"]) >= 20, f"psychology: {len(full['psychology'])}"

def test_intense_tier_accessible():
    try:
        from config.erotic_vocabulary_ext import get_vocabulary_for_tier_ext
        intense = get_vocabulary_for_tier_ext("intense")
        assert len(intense["metaphors"]) >= len(get_vocabulary_for_tier("full")["metaphors"])
    except ImportError:
        pytest.skip("erotic_vocabulary_ext not yet created")
```

---

### Step 34: `tests/conftest.py` — erotic 向け fixture 追加（既存conftestがある場合）

**対象ファイル**: `tests/conftest.py`（既存ファイルを読み、なければ作成）

**変更内容**:
erotic workflow test 用の共通 fixture を追加する。

```python
import pytest
from config.erotic_vocabulary import METAPHOR_BANK, ONOMATOPOEIA_BANK, PSYCHOLOGY_TEMPLATES

@pytest.fixture
def erotic_vocabulary():
    return {
        "metaphors": METAPHOR_BANK,
        "onomatopoeia": ONOMATOPOEIA_BANK,
        "psychology": PSYCHOLOGY_TEMPLATES,
    }

@pytest.fixture
def sample_erotic_text():
    return """
瞳を星の瞬きに例える。声が風鈴の音に例える。
体温を夕暮れの大地に例える。呼吸を風の流れに例える。

二人の夜は更けていった。静寂の中、二人は互いの温もりを確かめ合った。
    """.strip()
```

---

### Step 35: `pytest.ini` または `pyproject.toml` — test paths 設定確認

**対象ファイル**: `pytest.ini` または `pyproject.toml`（いずれか存在するもの）

**変更内容**:
`testpaths` に `tests/integration` が含まれていることを確認する。

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

または `pyproject.toml` の `[tool.pytest.ini_options]` に同じ設定を追加する。

---

## 改善案 #6: 密度管理機能拡張（Steps 36-40）

### Step 36: `src/services/erotic_density_controller.py` — `suggest_next_intensity` メソッド追加

**対象ファイル**: `src/services/erotic_density_controller.py`

**変更内容**:
ファイル末尾のクラス外に以下を追加する（または `EroticDensityController` クラスのメソッドとして追加）。

```python
    def suggest_next_intensity(self, recent_intensities: List[int], base_intensity: int) -> int:
        """
        直近話数の強度リストから、次話の推奨強度を提案する。
        連続ピークが続いている場合は1段階下げる。
        """
        if len(recent_intensities) >= MAX_CONSECUTIVE_PEAK_EPISODES:
            recent = recent_intensities[-MAX_CONSECUTIVE_PEAK_EPISODES:]
            if all(i >= 4 for i in recent):
                return max(1, base_intensity - 1)

        if len(recent_intensities) >= 1:
            last = recent_intensities[-1]
            if last >= 4:
                return max(1, base_intensity - 1)

        return base_intensity
```

**注意**: `MAX_CONSECUTIVE_PEAK_EPISODES` のインポートが先頭にあることを確認する。

---

### Step 37: `src/services/erotic_density_controller.py` — 定数の集中管理化

**対象ファイル**: `src/services/erotic_density_controller.py`

**変更内容**:
先頭附近の `MAX_CONSECUTIVE_PEAK_EPISODES = 2` を削除し、`config/erotic_thresholds.py` から import するように変更する。

```python
from config.erotic_thresholds import MAX_CONSECUTIVE_PEAK_EPISODES
```

**注意**: `compute_avg_intensity` メソッドの下に `@property` として閾値参照を追加する。

---

### Step 38: `tests/test_erotic_workflow.py` — `suggest_next_intensity` のテスト追加

**対象ファイル**: `tests/test_erotic_workflow.py`

**変更内容**:

```python
def test_density_controller_suggest_next():
    controller = EroticDensityController()
    # 連続ピークがないのでそのまま
    assert controller.suggest_next_intensity([1, 2, 3], 4) == 4
    # 連続ピーク4,4 があるので1段階下げる
    assert controller.suggest_next_intensity([1, 2, 4, 4], 4) == 3
    # 直近が4以上なので1段階下げる
    assert controller.suggest_next_intensity([1, 2, 3, 5], 4) == 3
    # 最低値は1
    assert controller.suggest_next_intensity([1, 2, 4, 4], 1) == 1
```

---

### Step 39: `src/services/erotic_density_controller.py` — `compute_avg_intensity` の閾値警告追加

**対象ファイル**: `src/services/erotic_density_controller.py`

**変更内容**:
`compute_avg_intensity` メソッドを以下のように拡張する。

```python
    def compute_avg_intensity(self, intensities: List[int]) -> float:
        """Book全体の平均強度を算出する。"""
        if not intensities:
            return 0.0
        avg = sum(intensities) / len(intensities)
        if avg > 4.0:
            logger.warning(f"Book全体の平均強度が{avg:.1f}と高すぎます。読者疲労の可能性があります。")
        return avg
```

`import logging` が先頭にあることを確認する。

---

### Step 40: 新規 `tests/test_erotic_density_controller.py` —密度管理単独テスト

**対象ファイル**: 新規 `tests/test_erotic_density_controller.py`

**内容**:

```python
"""tests/test_erotic_density_controller.py"""
import pytest
from src.services.erotic_density_controller import EroticDensityController

def test_should_allow_peak_edge_cases():
    controller = EroticDensityController()
    assert controller.should_allow_peak([]) is True
    assert controller.should_allow_peak([3]) is True
    assert controller.should_allow_peak([4, 5, 4]) is True  # 3連続的不是

def test_recommend_intensity_by_progress():
    controller = EroticDensityController()
    # 序盤 (10%)
    assert controller.recommend_intensity(1, 10, 5) <= 2
    # 中盤 (50%)
    assert controller.recommend_intensity(5, 10, 3) == 3
    # 終盤 (90%)
    assert controller.recommend_intensity(9, 10, 4) >= 4

def test_recommend_intensity_bounds():
    controller = EroticDensityController()
    # 上限5
    assert controller.recommend_intensity(9, 10, 6) <= 5
    # 下限1
    assert controller.recommend_intensity(1, 10, 0) >= 1

def test_avg_intensity_empty():
    controller = EroticDensityController()
    assert controller.compute_avg_intensity([]) == 0.0

def test_avg_intensity_normal():
    controller = EroticDensityController()
    assert controller.compute_avg_intensity([1, 2, 3, 4, 5]) == 3.0
```

---

## 改善案 #7: キャリブレーションパイプライン（Steps 41-43）

### Step 41: `src/services/ncs_calibration.py` — `erotic_diversity_score` 校正機能追加

**対象ファイル**: `src/services/ncs_calibration.py`

**変更内容**:
ファイル末尾（`calibrate_thresholds` メソッドの後）に以下を追加する。

```python
    def calibrate_diversity_threshold(self, training_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        erotic_diversity_score の閾値を人間評価データから校正する。

        Args:
            training_data: List of {"score": float, "rating": int} where rating is 1-5 human rating

        Returns:
            {"threshold_pass": float, "threshold_warn": float}
        """
        if not training_data:
            return {"threshold_pass": 0.5, "threshold_warn": 0.3}

        # 人間評価が4以上のデータを "良好" とする
        good_scores = [d["score"] for d in training_data if d.get("rating", 0) >= 4]
        bad_scores = [d["score"] for d in training_data if d.get("rating", 0) < 4]

        if good_scores and bad_scores:
            # .good と bad の境界線を閾値とする
            threshold_pass = (max(good_scores) + min(bad_scores)) / 2
            threshold_warn = threshold_pass * 0.6  # warn は pass の60%地点
        elif good_scores:
            threshold_pass = min(good_scores)
            threshold_warn = threshold_pass * 0.6
        else:
            threshold_pass = 0.5
            threshold_warn = 0.3

        return {
            "threshold_pass": threshold_pass,
            "threshold_warn": threshold_warn,
        }
```

---

### Step 42: `src/services/ncs_calibration.py` — `__init__.py` へのエクスポート追加

**対象ファイル**: `src/services/__init__.py`

**変更内容**:
既存 import 行に以下を追加する。

```python
from src.services.ncs_calibration import NarrativeCoherenceScorer
```

または `src/services/__init__.py` 末尾に以下を追加する。

```python
from src.services.ncs_calibration import NarrativeCoherenceScorer
```

---

### Step 43: 新規 `tests/test_ncs_calibration.py` — NCS + 多様性校正テスト

**対象ファイル**: 新規 `tests/test_ncs_calibration.py`

**内容**:

```python
"""tests/test_ncs_calibration.py"""
import pytest
from src.services.ncs_calibration import NarrativeCoherenceScorer

def test_calibrate_diversity_threshold_with_data():
    scorer = NarrativeCoherenceScorer()
    training_data = [
        {"score": 0.8, "rating": 5},
        {"score": 0.7, "rating": 4},
        {"score": 0.4, "rating": 3},
        {"score": 0.2, "rating": 1},
    ]
    result = scorer.calibrate_diversity_threshold(training_data)
    assert "threshold_pass" in result
    assert "threshold_warn" in result
    assert result["threshold_pass"] > result["threshold_warn"]

def test_calibrate_diversity_threshold_empty():
    scorer = NarrativeCoherenceScorer()
    result = scorer.calibrate_diversity_threshold([])
    assert result["threshold_pass"] == 0.5
    assert result["threshold_warn"] == 0.3

def test_calibrate_diversity_threshold_all_good():
    scorer = NarrativeCoherenceScorer()
    training_data = [
        {"score": 0.8, "rating": 5},
        {"score": 0.9, "rating": 5},
    ]
    result = scorer.calibrate_diversity_threshold(training_data)
    assert result["threshold_pass"] == 0.8  # min of good

def test_calculate_ncs_empty():
    scorer = NarrativeCoherenceScorer()
    assert scorer.calculate_ncs(1, [], []) == 0.0

def test_ncs_weights():
    scorer = NarrativeCoherenceScorer()
    assert abs(scorer.weights["plot_continuity"] +
               scorer.weights["character_consistency"] +
               scorer.weights["theme_unity"] - 1.0) < 0.001
```

---

## 改善案 #8: afterglow 必須項目強制力（Steps 44-46）

### Step 44: `src/agents/writing.py` — afterglow 存在チェック追加

**対象ファイル**: `src/agents/writing.py`

**変更内容**:
`write_episode` メソッドの `result = specialist.metaphor_filter(result, erotic_intensity)` の後に以下を追加する。

```python
        if specialist and erotic_intensity > 0 and nsfw_enabled:
            try:
                result = specialist.metaphor_filter(result, erotic_intensity)
            except Exception as e:
                logger.warning(f"metaphor_filter failed: {e}")

            # afterglow 必須項目の検証
            try:
                from src.services.erotic_afterglow_evaluator import AfterglowEvaluator
                evaluator = AfterglowEvaluator()
                # テキストの最後1/4を afterglow 傾向として検証
                afterglow_candidate = result[len(result) * 3 // 4:]
                afterglow_ok, afterglow_issues = evaluator.evaluate(afterglow_candidate)
                if not afterglow_ok:
                    logger.warning(
                        f"Episode {ep_num} afterglow quality issues: {afterglow_issues}. "
                        "Consider regeneration or supplementation."
                    )
            except Exception as e:
                logger.warning(f"Afterglow evaluation failed: {e}")
```

**注意**: `evaluator.evaluate` の呼び出しが `try` ブロックでラップされこと、失败しても執筆結果全体をロールバックしないことを確認する（警告ログのみ）。

---

### Step 45: `src/agents/writing.py` — `check_all` への consent_state 伝播確認

**対象ファイル**: `src/agents/writing.py`

**変更内容**:
`write_episode` メソッド内の `EroticSpecialist` delegation 部分で、`consent_state` を `build_scene_prompt` に渡していることを確認する。

```python
        if erotic_intensity > 0 and nsfw_enabled:
            try:
                from src.engine.prompts.erotic_specialist import EroticSpecialist
                from config.erotic_pacing import EroticCurve
                specialist = EroticSpecialist()
                curve = EroticCurve.create_default(erotic_intensity)
                peak_beat = curve.get_peak_beat()
                context["consent_state"] = peak_beat.consent_state if peak_beat else "implicit"
                erotic_prompt = specialist.build_scene_prompt(curve, context)
                prompt = prompt + "\n\n" + erotic_prompt
            except Exception as e:
                logger.warning(f"EroticSpecialist delegation failed, falling back: {e}")
```

---

### Step 46: `src/agents/writing.py` — エピソード生成時のログ強化

**対象ファイル**: `src/agents/writing.py`

**変更内容**:
`write_episode` メソッドの `logger.info` 行を以下のように拡張する。

```python
        logger.info(
            f"Generated episode {ep_num} for book {book_id}, "
            f"length {len(result)} chars, "
            f"erotic_intensity={erotic_intensity}, nsfw={nsfw_enabled}"
        )
```

---

## 改善案 #9: 伏字テーブル拡張性（Steps 47-48）

### Step 47: 新規 `config/platform_censorship_rules.py` — 動的ルール定義ファイル

**対象ファイル**: 新規 `config/platform_censorship_rules.py`

**内容**:

```python
"""
config/platform_censorship_rules.py
プラットフォーム別の伏字変換ルール定義。
"""
from typing import Dict, List

PLATFORM_CENSORSHIP_RULES: Dict[str, List[Dict[str, str]]] = {
    "kakuyomu_romance": [
        {"src": "肌を重ねる", "dst": "肌を重ね◆◆"},
        {"src": "唇を重ねる", "dst": "唇を◆◆◆"},
        {"src": "腕の中に包む", "dst": "腕の中に◆◆"},
        {"src": "衣が滑り落ちる", "dst": "衣が◆◆◆◆◆"},
        {"src": "柔らかな丘", "dst": "◆◆◆◆丘"},
        {"src": "二人の夜", "dst": "二人の◆"},
    ],
    "nocturn_novel": [
        {"src": "セックス", "dst": "二人の夜"},
        {"src": "性行為", "dst": "親密な時間"},
        {"src": "裸", "dst": "衣を解いた姿"},
        {"src": "胸", "dst": "柔らかな起伏"},
        {"src": "キ・ス", "dst": "◆◆◇◆"},  # かすり防止
        {"src": "抱く", "dst": "腕の中に包む"},
        {"src": "脱ぐ", "dst": "衣が滑り落ちる"},
    ],
    "adult_selfhost": [],  # 変換なし
}

def get_censorship_rules(platform: str) -> List[Dict[str, str]]:
    """プラットフォーム別の伏字ルールリストを返す。"""
    return PLATFORM_CENSORSHIP_RULES.get(platform, PLATFORM_CENSORSHIP_RULES.get("kakuyomu_romance", []))
```

---

### Step 48: `formatters/erotic_censor.py` — 動的ルールベースリファクタリング

**対象ファイル**: `formatters/erotic_censor.py`

**変更内容**:
ファイルを以下のように全面リファクタリングする。

```python
"""
formatters/erotic_censor.py
プラットフォーム別の伏字（shading）変換フォーマッター。
リファクタリング済み: 固定dict → config/platform_censorship_rules.py 参照
"""
from typing import Dict, List
from config.platform_censorship_rules import get_censorship_rules
from config.erotic_platform_presets import get_preset

def apply_censorship(text: str, preset_name: str = "kakuyomu_romance") -> str:
    """
    プリセットに基づいて伏字変換を適用する。

    変換ルールは config/platform_censorship_rules.py で管理される。
    """
    preset = get_preset(preset_name)
    mode = preset.get("censorship_mode", "heavy")

    if mode == "none":
        return text

    rules = get_censorship_rules(preset_name)
    result = text
    for rule in rules:
        src = rule["src"]
        dst = rule["dst"]
        result = result.replace(src, dst)

    return result


def generate_censored_filename(original: str) -> str:
    """元ファイル名から伏字版ファイル名を生成する。"""
    if original.endswith(".txt"):
        return original.replace(".txt", "_censored.txt")
    return f"{original}_censored"


# 後方互換性: 旧 CENSORSHIP_TABLE は廃止済み
# 旧テーブルユーザーは get_censorship_rules("kakuyomu_romance") に移行すること
CENSORSHIP_TABLE: Dict[str, str] = {}  # deprecated, 空dictで維持
```

**既存テストへの影響確認**: `tests/test_erotic_workflow.py` の `test_censorship_kakuyomu` と `test_censorship_selfhost` が引き続き通ることを手動で確認する。

```bash
pytest tests/test_erotic_workflow.py::test_censorship_kakuyomu tests/test_erotic_workflow.py::test_censorship_selfhost -v
```

---

## ステップ一覧表

| Step | 対象ファイル | 概要 |
|------|-------------|------|
| 1 | `config/erotic_vocabulary.py` | `METAPHOR_BANK` 25個に拡張 |
| 2 | `config/erotic_vocabulary.py` | `ONOMATOPOEIA_BANK` 25個に拡張 |
| 3 | `config/erotic_vocabulary.py` | `PSYCHOLOGY_TEMPLATES` 25個に拡張 |
| 4 | `config/erotic_vocabulary.py` | `"full"` tier 35個以上に拡張 |
| 5 | 新規 `config/erotic_vocabulary_ext.py` | `"intense"` tier 追加 |
| 6 | `config/erotic_platform_presets.py` | `adult_selfhost` → `"intense"` tier 許可 |
| 7 | `config/erotic_vocabulary.py` | `"mild"` tier 10個に整理 |
| 8 | `config/erotic_vocabulary.py` | 型ヒント・docstring追加 |
| 9 | 新規 `config/erotic_thresholds.py` | 閾値定数ファイル作成 |
| 10 | `src/services/erotic_diversity_score.py` | 分類ラッパー追加 |
| 11 | `src/services/erotic_diversity_score.py` | docstring に閾値注記 |
| 12 | `tests/test_erotic_workflow.py` | 閾値分類テスト追加 |
| 13 | 新規 `tests/test_erotic_thresholds.py` | 閾値ユニットテスト |
| 14 | `config/erotic_thresholds.py` | `Final` 型ヒント・`__all__` 追加 |
| 15 | `src/agents/erotic_integrity.py` | `check_consent_state` メソッド追加 |
| 16 | `src/agents/erotic_integrity.py` | `check_all` に consent 検証統合 |
| 17 | `config/erotic_pacing.py` | `EroticBeat.consent_state` デフォルト追加 |
| 18 | `src/backend/workflows/refine_erotic_workflow.py` | consent_state 検証呼び出し追加 |
| 19 | `tests/test_erotic_workflow.py` | consent 検証テスト追加 |
| 20 | `src/agents/erotic_integrity.py` | キーワード定数配置確認 |
| 21 | 新規 `src/services/erotic_afterglow_evaluator.py` | `AfterglowEvaluator` クラス作成 |
| 22 | `src/services/__init__.py` | `AfterglowEvaluator` エクスポート |
| 23 | `src/engine/prompts/erotic_specialist.py` | docstring に品質検証注記 |
| 24 | `src/backend/workflows/refine_erotic_workflow.py` | afterglow 評価呼び出し追加 |
| 25 | 新規 `tests/test_erotic_afterglow_evaluator.py` | afterglow ユニットテスト |
| 26 | `config/erotic_thresholds.py` |閾値一元管理確認 |
| 27 | `src/engine/prompts/erotic_specialist.py` | 返り値 afterglow 要件注記追加 |
| 28 | `prompts/erotic/scene_templates.py` | afterglow テンプレート品質要件明記 |
| 29 | 新規 `tests/integration/test_erotic_full_pipeline.py` | E2E smoke test 作成 |
| 30 | `tests/test_erotic_workflow.py` | 密度管理ケース追加 |
| 31 | `tests/integration/test_erotic_full_pipeline.py` | 閾値分類・avg 強度テスト追加 |
| 32 | 新規 `tests/integration/test_erotic_refine_workflow.py` | refine ワークフロー統合テスト |
| 33 | `tests/test_erotic_workflow.py` | full tier 最少数確認テスト追加 |
| 34 | `tests/conftest.py` | erotic 向け fixture 追加 |
| 35 | `pytest.ini` / `pyproject.toml` | testpaths 設定確認 |
| 36 | `src/services/erotic_density_controller.py` | `suggest_next_intensity` メソッド追加 |
| 37 | `src/services/erotic_density_controller.py` | 集中管理化（`erotic_thresholds` import） |
| 38 | `tests/test_erotic_workflow.py` | `suggest_next_intensity` テスト追加 |
| 39 | `src/services/erotic_density_controller.py` | avg 強度警告ログ追加 |
| 40 | 新規 `tests/test_erotic_density_controller.py` | 密度管理単独テスト |
| 41 | `src/services/ncs_calibration.py` | 多様性スコア校正メソッド追加 |
| 42 | `src/services/__init__.py` | `NarrativeCoherenceScorer` エクスポート |
| 43 | 新規 `tests/test_ncs_calibration.py` | 校正パイプラインテスト |
| 44 | `src/agents/writing.py` | afterglow 存在チェック追加 |
| 45 | `src/agents/writing.py` | consent_state `build_scene_prompt` へ伝播 |
| 46 | `src/agents/writing.py` | ログ強化 |
| 47 | 新規 `config/platform_censorship_rules.py` | 動的ルール定義ファイル作成 |
| 48 | `formatters/erotic_censor.py` | 動的ルールベースリファクタリング |

---

## 依存グラフ

```
Step9 (erotic_thresholds.py) ──┬──→ Step10/11/12 (diversity_score)
                                ├──→ Step14 (thresholds Final)
                                ├──→ Step17 (pacing default)
                                ├──→ Step21/26 (afterglow evaluator)
                                ├──→ Step36/37/39 (density_controller)
                                └──→ Step48 (censor refactor)

Step15/16 (consent_state) ───→ Step18 (refine_erotic_workflow)
                               ──→ Step19 (tests)

Step21 (afterglow evaluator) ──→ Step24 (refine_erotic_workflow)
                               ──→ Step25 (tests)

Step29 (integration test) ──────→ Step30/31/32/33 (more tests)
Step34 (conftest fixtures) ────→ 全テスト

Step47 (platform_censorship_rules) ──→ Step48 (censor refactor)

Step41 (ncs_calibration ext) ──→ Step42/43 (tests)
```

---

## 推奨実装順

1. **Phase 1（Steps 9-14）**: 閾値定義 → テストが書けるので品質基盤確立
2. **Phase 2（Steps 15-20）**: consent_state 検証 → 安全性向上
3. **Phase 3（Steps 21-28）**: afterglow 評価 → 品質保証
4. **Phase 4（Steps 1-8, 36-40）**: ボキャブラリ拡張 + 密度管理強化
5. **Phase 5（Steps 29-35, 41-43）**: 統合テスト + キャリブレーション
6. **Phase 6（Steps 44-48）**: 強制力 + 伏字拡張性

各 Phase 内でステップ番号順に実装すると安全。

---

## 改善案 #6: 世界観（Bible）の深化（Steps 49-72）

魔法体系や社会構造の詳細設定を、プロット生成前にさらに深掘りさせるステップを追加する。設定が記号的（王府すぎ）であるため、独自性を出し「覇権」を狙うため。

### Step 49: 新規 `config/world_bible.py` — 世界観Bible基本構造定義

**対象ファイル**: 新規 `config/world_bible.py`

**内容**:

```python
"""
config/world_bible.py
世界観（Bible）定義ファイル。
プロット生成前に世界观设定をachus的に 深掘りし、独自性を確保するための設定群。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class MagicSystem:
    """魔法体系の定義。"""
    name: str                               # 例: "脈動魔法"
    source: str                             # 例: "使用者の体温"
    cost: str                               # 例: "体温の低下"
    side_effect: str                        # 例: "着用衣が熱を帯びる"
    visual_metaphor: List[str]             # 例: ["脈打つ光", "血管の赤"]
    social_perception: str                  # 例: "帝国では禁忌とされる"
    restricted_to: Optional[str] = None    # 例: "皇族のみ"

@dataclass
class SocialStructure:
    """社会構造の定義。"""
    name: str                               # 例: "帝國体制"
    power_hierarchy: List[str]             # 例: ["皇帝", "貴族", "平民"]
    erotically_charged_positions: List[str]  # 例: ["側室", "女官長"]
    taboo_relationships: List[str]         # 例: ["貴族×平民", "同一階級厳守"]
    gender_roles: str                       # 例: "女官は男性的役割も兼任"

@dataclass
class WorldBible:
    """全体世界観コンテナ。"""
    title: str
    magic_systems: List[MagicSystem] = field(default_factory=list)
    social_structures: List[SocialStructure] = field(default_factory=list)
    lore_tags: List[str] = field(default_factory=list)     # 例: ["帝國", "禁忌", "血統"]
    unique_rules: List[str] = field(default_factory=list)  # 例: ["魔法使用者は体温を失う"]
    setting_tone: str = "dark"                               # "dark" | "light" | "erotic"

# デフォルトBible（王府設定からの脱却用）
DEFAULT_BIBLE = WorldBible(
    title="帝国脈動世界",
    magic_systems=[
        MagicSystem(
            name="脈動魔法",
            source="使用者の体温",
            cost="体温の低下（持続的）",
            side_effect="肌髪が透ける",
            visual_metaphor=["脈打つ光", "血管の赤", "湯気"],
            social_perception="皇帝家にのみ伝わる禁術",
            restricted_to="皇族",
        )
    ],
    social_structures=[
        SocialStructure(
            name="帝國体制",
            power_hierarchy=["皇帝", "側用人", "貴族", "商人", "平民"],
            erotically_charged_positions=["側室", "女官長", "高等女官"],
            taboo_relationships=["貴族×平民の結婚禁止", "側室は平民出身"],
            gender_roles="女性貴族は政治的聯姻の駒として扱われる",
        )
    ],
    lore_tags=["帝國", "禁忌の魔法", "体温取引", "階級制度"],
    unique_rules=[
        "魔法使用者は体温を代価として支払う",
        "体温が一定以下になると魔法は無力化",
        "体温が高いほど魔法が強くなるが、副作用も增大"
    ],
    setting_tone="dark_erotic",
)
```

---

### Step 50: `config/world_bible.py` — `get_bible` / `register_bible` 関数追加

**対象ファイル**: `config/world_bible.py`

**変更内容**:
ファイル末尾に以下を追加する。

```python
# グローバルBibleレジストリ
_BIBLE_REGISTRY: Dict[str, WorldBible] = {
    "default": DEFAULT_BIBLE,
}

def get_bible(name: str = "default") -> WorldBible:
    """登録されたBibleを取得する。"""
    return _BIBLE_REGISTRY.get(name, DEFAULT_BIBLE)

def register_bible(name: str, bible: WorldBible) -> None:
    """新規Bibleを登録する。"""
    _BIBLE_REGISTRY[name] = bible

def list_bibles() -> List[str]:
    """登録されているBible名のリストを返す。"""
    return list(_BIBLE_REGISTRY.keys())
```

---

### Step 51: 新規 `src/services/world_bible_deepener.py` — 深掘りサービス

**対象ファイル**: 新規 `src/services/world_bible_deepener.py`

**内容**:

```python
"""
src/services/world_bible_deepener.py
世界観Bibleをプロット生成前に 深掘りさせるサービス。
王府設定から独自性を出すための supplemental 質問生成・評価を行う。
"""
from typing import List, Tuple, Dict
from config.world_bible import WorldBible, MagicSystem, SocialStructure

class WorldBibleDeepener:
    """Bible の 深掘りを行うクラス。"""

    # 深掘り質問テンプレート（王府設定からの脱却用）
    MAGIC_DEEPENING_QUESTIONS = [
        "この魔法は「体温」を媒介にするなら、なぜ体温なのか？体温と感情の関連は？",
        "副作用として「肌髪が透ける」とあるが、透けた場合どんな意味を持つ？",
        "禁忌とされる魔法を、なぜ人は使うのか？その欲求の根源は？",
        "魔法使用者体温が低下すると、身体的特徴はどうかわるか？",
        "この魔法体系で「一番使ってはいけない場面」はいつか？",
    ]

    SOCIAL_DEEPENING_QUESTIONS = [
        "「側室」という存在は帝國でどのように見做されているか？",
        "女官長という立場にある人物は、どんな力学关系的隙にあるか？",
        "「貴族×平民の結婚禁止」はなぜ存在し、破った場合誰が困るのか？",
        "政治的聯姻の駒とされる女性」は自分の欲望を持てるか？",
        "この社会で「愛」と「権力」はをどう区別するか？",
    ]

    UNIQUE_RULE_QUESTIONS = [
        "このルールが物語にどう影を落とすか？",
        "このルールを破った人物はどうなるか？",
        "このルールが官能シーンにどう影響するか？",
    ]

    def generate_deepening_questions(self, bible: WorldBible) -> List[str]:
        """Bible全体に対して深掘り質問リストを生成する。"""
        questions = []

        for magic in bible.magic_systems:
            questions.append(f"【魔法体系: {magic.name}】")
            questions.extend(self.MAGIC_DEEPENING_QUESTIONS)

        for social in bible.social_structures:
            questions.append(f"【社会構造: {social.name}】")
            questions.extend(self.SOCIAL_DEEPENING_QUESTIONS)

        for rule in bible.unique_rules:
            questions.append(f"【固有ルール: {rule}】")
            questions.extend(self.UNIQUE_RULE_QUESTIONS)

        return questions

    def evaluate_bible_originality(self, bible: WorldBible) -> Tuple[float, List[str]]:
        """
        Bibleの独自性を評価する。

        Returns:
            (score 0.0-1.0, issues)
        """
        issues = []
        score = 1.0

        # チェック1: 魔法体系に「体温」以外のエネルギー源があるか？
        for magic in bible.magic_systems:
            if "体温" in magic.source and len(bible.magic_systems) == 1:
                issues.append("魔法体系が「体温」のみ。複数のエネルギー源を検討してください。")
                score -= 0.2

        # チェック2: 社会構造に「側室」「女官」が含まれている場合、役割が単一でないか？
        for social in bible.social_structures:
            if "側室" in social.erotically_charged_positions:
                if "政治的联姻" not in social.gender_roles and "愛欲の題材" not in str(social.__dict__):
                    issues.append("側室の存在が官能的に单一描写になりがち。心理的深みを追加してください。")
                    score -= 0.15

        # チェック3: unique_rules が3つ未満の場
        if len(bible.unique_rules) < 3:
            issues.append(f"固有ルールが{len(bible.unique_rules)}個と少ない。最低3つ以上を設定してください。")
            score -= 0.1

        # チェック4: lore_tags が5つ未満の場
        if len(bible.lore_tags) < 5:
            issues.append(f"ロアタグが{len(bible.lore_tags)}個と少ない。最低5つ以上を設定してください。")
            score -= 0.1

        # チェック5: 設定が王府すぎないか（王府設定の典型パターンを検出）
        generic_patterns = ["帝国", "王妃", "側室", "贵族", "平民"]
        generic_count = sum(1 for tag in bible.lore_tags if tag in generic_patterns)
        if generic_count >= 3:
            issues.append("設定が王府パターンに依存しています。独自の要素を追加してください。")
            score -= 0.2

        return max(0.0, score), issues
```

---

### Step 52: `src/services/world_bible_deepener.py` — `apply_bible_to_context` メソッド追加

**対象ファイル**: `src/services/world_bible_deepener.py`

**変更内容**:
クラス末尾（ファイル末尾）に以下を追加する。

```python
    def apply_bible_to_context(self, bible: WorldBible, context: Dict) -> Dict:
        """
        Bible設定をコンテキスト辞書に注入する。
        プロンプト生成時に世界观情報を含めるために使う。

        Returns:
            bible_context: プロンプト注入用辞書
        """
        bible_context = {
            "bible_title": bible.title,
            "magic_systems": [],
            "social_structures": [],
            "unique_rules": bible.unique_rules,
            "lore_tags": bible.lore_tags,
            "setting_tone": bible.setting_tone,
        }

        for magic in bible.magic_systems:
            bible_context["magic_systems"].append({
                "name": magic.name,
                "source": magic.source,
                "cost": magic.cost,
                "side_effect": magic.side_effect,
                "visual_metaphor": magic.visual_metaphor,
                "social_perception": magic.social_perception,
                "restricted_to": magic.restricted_to,
            })

        for social in bible.social_structures:
            bible_context["social_structures"].append({
                "name": social.name,
                "power_hierarchy": social.power_hierarchy,
                "erotically_charged_positions": social.erotically_charged_positions,
                "taboo_relationships": social.taboo_relationships,
                "gender_roles": social.gender_roles,
            })

        # context にマージ（上書きなし、深いマージ）
        merged = context.copy()
        merged["world_bible"] = bible_context
        return merged
```

---

### Step 53: `src/services/world_bible_deepener.py` — `__init__.py` エクスポート追加

**対象ファイル**: `src/services/__init__.py`（または既存 exports ファイル）

**変更内容**:
末尾に以下を追加する。

```python
from src.services.world_bible_deepener import WorldBibleDeepener
```

---

### Step 54: `src/engine/prompts/erotic_specialist.py` — Bible 注入プロンプトビルダー追加

**対象ファイル**: `src/engine/prompts/erotic_specialist.py`

**変更内容**:
ファイル末尾に以下を追加する。

```python
    def build_bible_injection_prompt(self, bible: WorldBible) -> str:
        """
        世界観Bible情報をプロンプトに注入する。

        この情報は官能シーンの背景に深みを与えるために使われる。
        プロンプト例:

        【世界観設定】
        魔法体系: {name} - エネルギー源: {source}
        社会構造: {name} - 階級: {hierarchy}
        固有ルール: {rules}
        """
        lines = ["【世界観設定】"]
        for magic in bible.magic_systems:
            lines.append(f"魔法体系: {magic.name}")
            lines.append(f"  エネルギー源: {magic.source}")
            lines.append(f"  代償: {magic.cost}")
            lines.append(f"  副作用: {magic.side_effect}")
            lines.append(f"  視覚的比喩: {', '.join(magic.visual_metaphor)}")
            lines.append(f"  社会的認知: {magic.social_perception}")
            lines.append(f"  利用者制限: {magic.restricted_to or 'なし'}")
            lines.append("")

        for social in bible.social_structures:
            lines.append(f"社会構造: {social.name}")
            lines.append(f"  階級: {' > '.join(social.power_hierarchy)}")
            lines.append(f"  官能的立場: {', '.join(social.erotically_charged_positions)}")
            lines.append(f"  禁忌関係: {', '.join(social.taboo_relationships)}")
            lines.append(f"  ジェンダー役割: {social.gender_roles}")
            lines.append("")

        if bible.unique_rules:
            lines.append(f"固有ルール: {' / '.join(bible.unique_rules)}")

        lines.append(f"設定トーン: {bible.setting_tone}")

        return "\n".join(lines)
```

---

### Step 55: `src/engine/prompts/erotic_specialist.py` — `build_scene_prompt` にBible情報注入

**対象ファイル**: `src/engine/prompts/erotic_specialist.py`

**変更内容**:
`build_scene_prompt` メソッドの冒頭で `bible` パラメータを受け取り、返すプロンプトの先頭にBible情報を追加する。

```python
def build_scene_prompt(
    self,
    curve: EroticCurve,
    context: Dict[str, Any],
    bible: Optional[WorldBible] = None,
) -> str:
    """
    官能シーン生成プロンプトを構築する。

    Args:
        curve: EroticCurve インスタンス
        context: プロンプト生成所需的上下文情報
        bible: 世界観Bible情報（オプション）
    """
    parts = []

    # Bible情報注入（最も最初に）
    if bible is not None:
        parts.append(self.build_bible_injection_prompt(bible))

    # 以下、既存の scene prompt 构建...
```

**注意**: `WorldBible` と `Optional` の import を確認すること。

---

### Step 56: `src/agents/writing.py` — `write_episode` にBible情報伝播追加

**対象ファイル**: `src/agents/writing.py`

**変更内容**:
`write_episode` メソッド найдите `erotic_prompt = specialist.build_scene_prompt(curve, context)` 附近を以下に変更する。

```python
            # Bible 情報の取得と伝播
            from config.world_bible import get_bible
            from src.services.world_bible_deepener import WorldBibleDeepener
            bible = get_bible(context.get("bible_name", "default"))
            deepener = WorldBibleDeepener()
            context = deepener.apply_bible_to_context(bible, context)

            # シーンプロンプト生成にBibleを含める
            erotic_prompt = specialist.build_scene_prompt(curve, context, bible=bible)
            prompt = prompt + "\n\n" + erotic_prompt
```

---

### Step 57: 新規 `tests/test_world_bible_deepener.py` — 深掘りサービスユニットテスト

**対象ファイル**: 新規 `tests/test_world_bible_deepener.py`

**内容**:

```python
"""tests/test_world_bible_deepener.py"""
import pytest
from config.world_bible import DEFAULT_BIBLE, get_bible, register_bible
from src.services.world_bible_deepener import WorldBibleDeepener

def test_generate_deepening_questions():
    deepener = WorldBibleDeepener()
    questions = deepener.generate_deepening_questions(DEFAULT_BIBLE)
    assert len(questions) > 5
    assert any("体温" in q for q in questions)

def test_evaluate_bible_originality_good():
    deepener = WorldBibleDeepener()
    score, issues = deepener.evaluate_bible_originality(DEFAULT_BIBLE)
    assert 0.0 <= score <= 1.0
    # 問題なければ issues は空、または score は高い
    if score < 0.5:
        assert len(issues) > 0

def test_evaluate_bible_originality_low_rules():
    from config.world_bible import WorldBible, MagicSystem
    weak_bible = WorldBible(
        title="Simple",
        magic_systems=[MagicSystem(name="M", source="X", cost="Y", side_effect="Z",
                                    visual_metaphor=["a"], social_perception="none")],
        unique_rules=["only one rule"],  # 3つ未満
        lore_tags=["a"],                # 5つ未満
    )
    deepener = WorldBibleDeepener()
    score, issues = deepener.evaluate_bible_originality(weak_bible)
    assert score < 1.0
    assert len(issues) > 0

def test_apply_bible_to_context():
    deepener = WorldBibleDeepener()
    context = {"chapter": 1}
    merged = deepener.apply_bible_to_context(DEFAULT_BIBLE, context)
    assert "world_bible" in merged
    assert merged["world_bible"]["bible_title"] == DEFAULT_BIBLE.title

def test_get_default_bible():
    bible = get_bible("default")
    assert bible.title == "帝国脈動世界"

def test_register_and_get_bible():
    from config.world_bible import WorldBible
    new_bible = WorldBible(title="Test World")
    register_bible("test", new_bible)
    assert get_bible("test").title == "Test World"
```

---

### Step 58: `tests/test_erotic_workflow.py` — Bible統合テスト追加

**対象ファイル**: `tests/test_erotic_workflow.py`

**変更内容**:
末尾に追加する。

```python
def test_world_bible_deepener_questions():
    from src.services.world_bible_deepener import WorldBibleDeepener
    from config.world_bible import DEFAULT_BIBLE
    deepener = WorldBibleDeepener()
    questions = deepener.generate_deepening_questions(DEFAULT_BIBLE)
    assert len(questions) > 10

def test_bible_apply_to_context():
    from src.services.world_bible_deepener import WorldBibleDeepener
    from config.world_bible import DEFAULT_BIBLE
    deepener = WorldBibleDeepener()
    ctx = deepener.apply_bible_to_context(DEFAULT_BIBLE, {"ep": 1})
    assert "world_bible" in ctx
    assert ctx["world_bible"]["bible_title"] == "帝国脈動世界"
```

---

### Step 59: `config/world_bible.py` — 型ヒント追加と `__all__`

**対象ファイル**: `config/world_bible.py`

**変更内容**:
先頭に `from typing import List, Dict, Optional` を追加し、各 dataclass と関数に型ヒントを付与する。

```python
__all__ = [
    "WorldBible",
    "MagicSystem",
    "SocialStructure",
    "DEFAULT_BIBLE",
    "get_bible",
    "register_bible",
    "list_bibles",
]
```

---

### Step 60: 新規 `src/engine/prompts/world_bible_prompt.py` — 深掘り質問プロンプト生成

**対象ファイル**: 新規 `src/engine/prompts/world_bible_prompt.py`

**内容**:

```python
"""
src/engine/prompts/world_bible_prompt.py
世界観深掘り用のプロンプトテンプレート。
Bible設定に 深掘り質問を追加するプロンプトを 生成する。
"""
from typing import Dict, Any
from config.world_bible import WorldBible
from src.services.world_bible_deepener import WorldBibleDeepener

def build_deepening_prompt(bible: WorldBible, user_questionnaire: str = "") -> str:
    """
    Bible 深掘り質問票を生成するプロンプトを返す。

    Args:
        bible: 対象Bible
        user_questionnaire: ユーザーが答えた深掘り質問（空欄で全部生成）
    """
    deepener = WorldBibleDeepener()
    questions = deepener.generate_deepening_questions(bible)

    prompt = f"""【世界観設定 - 深掘り質問票】

現在の設定:
- タイトル: {bible.title}
- 設定トーン: {bible.setting_tone}

以下の質問に全て回答してください。回答は物語の深度と官能表現の豊かさに直結します。

"""
    for i, q in enumerate(questions, 1):
        prompt += f"{i}. {q}\n   回答: "

    prompt += """

【回答時の注意】
- 「なぜそうなるか」を必ず説明してください
- 官能シーンへの影響を意識してください
- 王府設定からの脱却を意識してください
"""
    return prompt
```

---

### Step 61: `src/backend/tasks.py` — `deepen_bible` タスク関数追加

**対象ファイル**: `src/backend/tasks.py`

**変更内容**:
ファイル末尾（または `generate_chapter` タスク関数の後に）に以下を追加する。

```python
@shared_task
def deepen_bible_task(bible_name: str = "default") -> dict:
    """
    世界観Bibleを 深掘りさせるバックグラウンドタスク。

    深的掘り質問票を生成し、独自性評価を行う。
    """
    from config.world_bible import get_bible
    from src.services.world_bible_deepener import WorldBibleDeepener

    bible = get_bible(bible_name)
    deepener = WorldBibleDeepener()

    questions = deepener.generate_deepening_questions(bible)
    score, issues = deepener.evaluate_bible_originality(bible)

    return {
        "bible_name": bible_name,
        "questions": questions,
        "originality_score": score,
        "issues": issues,
        "status": "completed",
    }
```

---

### Step 62: `src/backend/server.py` — `/api/bible/deepen` エンドポイント追加

**対象ファイル**: `src/backend/server.py`

**変更内容**:
既存の API route 定義部に以下を追加する。

```python
@app.get("/api/bible/deepen")
def deepen_bible(bible_name: str = "default"):
    """
    世界観Bibleの深掘り質問と独自性評価を返す。

    Query Params:
        bible_name: 対象Bible名（デフォルト "default"）
    """
    from config.world_bible import get_bible
    from src.services.world_bible_deepener import WorldBibleDeepener

    bible = get_bible(bible_name)
    deepener = WorldBibleDeepener()

    questions = deepener.generate_deepening_questions(bible)
    score, issues = deepener.evaluate_bible_originality(bible)

    return {
        "bible_name": bible_name,
        "title": bible.title,
        "questions": questions,
        "originality_score": score,
        "issues": issues,
        "originality_level": "good" if score >= 0.7 else "warn" if score >= 0.5 else "poor",
    }
```

---

### Step 63: `config/world_bible.py` — Bible独自性チェック用定数追加

**対象ファイル**: `config/world_bible.py`

**変更内容**:
`WorldBibleDeepener` の評価ロジックに影響する定数を追加する。

```python
# Bible 独自性評価閾値
BIBLE_ORIGINALITY_THRESHOLD = 0.6  # この値以上なら「良好」と判定
BIBLE_ORIGINALITY_WARN = 0.4       # この値以上0.6未満は「要改善」
BIBLE_ORIGINALITY_FAIL = 0.4      # この値未満は「王府すぎ」と判定

# 最低設定数要件
MIN_UNIQUE_RULES = 3
MIN_LORE_TAGS = 5
MAX_GENERIC_TAGS = 2  # 王府典型タグの最大数
```

---

### Step 64: `src/services/world_bible_deepener.py` — 評価閾値定数の活用

**対象ファイル**: `src/services/world_bible_deepener.py`

**変更内容**:
`evaluate_bible_originality` メソッド冒頭に以下を追加する。

```python
from config.world_bible import (
    BIBLE_ORIGINALITY_THRESHOLD,
    BIBLE_ORIGINALITY_WARN,
    MIN_UNIQUE_RULES,
    MIN_LORE_TAGS,
    MAX_GENERIC_TAGS,
)
```

また、閾値を使って score 計算部分を整理する（既に Step 51 で実装したロジックを上述の定数で置換）。

---

### Step 65: `tests/test_world_bible_deepener.py` — 独自性評価テスト強化

**対象ファイル**: `tests/test_world_bible_deepener.py`

**変更内容**:
末尾に以下を追加する。

```python
def test_bible_originality_threshold_constants():
    from config.world_bible import (
        BIBLE_ORIGINALITY_THRESHOLD,
        BIBLE_ORIGINALITY_WARN,
        MIN_UNIQUE_RULES,
        MIN_LORE_TAGS,
    )
    assert BIBLE_ORIGINALITY_THRESHOLD > BIBLE_ORIGINALITY_WARN
    assert MIN_UNIQUE_RULES >= 3
    assert MIN_LORE_TAGS >= 5

def test_deepen_endpoint_mock(monkeypatch):
    """deepen API endpoint のモックテスト"""
    from src.services.world_bible_deepener import WorldBibleDeepener

    def mock_evaluate(self, bible):
        return 0.8, []

    monkeypatch.setattr(WorldBibleDeepener, "evaluate_bible_originality", mock_evaluate)

    from src.services.world_bible_deepener import WorldBibleDeepener
    from config.world_bible import DEFAULT_BIBLE
    deepener = WorldBibleDeepener()
    score, issues = deepener.evaluate_bible_originality(DEFAULT_BIBLE)
    assert score == 0.8
    assert issues == []
```

---

### Step 66: `src/services/world_bible_deepener.py` — `get_supplemental_lore` メソッド追加

**対象ファイル**: `src/services/world_bible_deepener.py`

**変更内容**:
ファイル末尾のクラス外に以下を追加する。

```python
def generate_supplemental_lore(bible: WorldBible) -> List[str]:
    """
    Bible設定から自動的に補足ロアを 生成する。
    「王府からの脱却」に役立つ追加設定案を返す。

    Args:
        bible: 対象Bible

    Returns:
        補足ロアリスト
    """
    supplements = []

    # 魔法体系からの補足
    for magic in bible.magic_systems:
        if magic.restricted_to:
            supplements.append(
                f"{magic.restricted_to}以外の者が{magic.nameを使うと"
                f"{magic.side_effect}という副作用が必ず発生する"
            )
        if "体温" in magic.source:
            supplements.append(
                f"{magic.name}使用者は体温が低下するため、寒い環境では能力が発揮できない"
            )
        supplements.append(
            f"一般市民は{magic.name}を「{magic.social_perception}」と思っている"
        )

    # 社会構造からの補足
    for social in bible.social_structures:
        if social.taboo_relationships:
            supplements.append(
                f"禁忌: {social.taboo_relationships[0]}。破った場合の影響: "
                f"{social.name}全体の信認が揺らぐ"
            )
        if social.erotically_charged_positions:
            pos = social.erotically_charged_positions[0]
            supplements.append(
                f"{pos}の役職者は常に{magic.name}使用者との接触を強いられる"
                if bible.magic_systems else f"{pos}の役職者は権力と欲望の狭間にいる"
            )

    return supplements
```

---

### Step 67: `src/services/world_bible_deepener.py` — `generate_supplemental_lore` テスト追加

**対象ファイル**: `tests/test_world_bible_deepener.py`

**変更内容**:
末尾に以下を追加する。

```python
def test_generate_supplemental_lore():
    from src.services.world_bible_deepener import generate_supplemental_lore
    from config.world_bible import DEFAULT_BIBLE
    lore = generate_supplemental_lore(DEFAULT_BIBLE)
    assert len(lore) >= 2
    assert any("体温" in l or "禁忌" in l or "側室" in l for l in lore)
```

---

### Step 68: `src/engine/prompts/world_bible_prompt.py` — 補足ロア生成プロンプト追加

**対象ファイル**: `src/engine/prompts/world_bible_prompt.py`

**変更内容**:
ファイル末尾に以下を追加する。

```python
def build_supplemental_lore_prompt(bible: WorldBible) -> str:
    """
    補足ロア生成のためのプロンプトを返す。
    「王府設定からの脱却」を目的に、現在のBibleに存在しない独自設定を追加する。
    """
    supplements = generate_supplemental_lore(bible)

    prompt = f"""【補足ロア生成プロンプト】

現在のBibleには以下の設定が存在します:
"""
    for s in supplements:
        prompt += f"- {s}\n"

    prompt += """
上記に加えて、以下のような「王府設定にありがちでない」独自設定を3つ以上生成してください。
各設定は:
1. 物語の展開に影を落とす可能性があるもの
2. 官能シーンの描写に深みを与えるもの
3. 既存のBible設定と矛盾しないもの

回答形式:
A. [設定名]: [詳細説明]
B. [設定名]: [詳細説明]
C. [設定名]: [詳細説明]
"""
    return prompt
```

---

### Step 69: `src/backend/tasks.py` — `supplemental_lore_task` 追加

**対象ファイル**: `src/backend/tasks.py`

**変更内容**:
`deepen_bible_task` の後に以下を追加する。

```python
@shared_task
def supplemental_lore_task(bible_name: str = "default") -> dict:
    """
    補足ロアを生成するバックグラウンドタスク。
    """
    from config.world_bible import get_bible
    from src.services.world_bible_deepener import generate_supplemental_lore

    bible = get_bible(bible_name)
    lore = generate_supplemental_lore(bible)

    return {
        "bible_name": bible_name,
        "supplemental_lore": lore,
        "status": "completed",
    }
```

---

### Step 70: `src/backend/server.py` — `/api/bible/lore` エンドポイント追加

**対象ファイル**: `src/backend/server.py`

**変更内容**:
`/api/bible/deepen` エンドポイントの後に以下を追加する。

```python
@app.get("/api/bible/lore")
def get_supplemental_lore(bible_name: str = "default"):
    """補足ロアリストを返す。"""
    from config.world_bible import get_bible
    from src.services.world_bible_deepener import generate_supplemental_lore

    bible = get_bible(bible_name)
    lore = generate_supplemental_lore(bible)

    return {
        "bible_name": bible_name,
        "supplemental_lore": lore,
    }
```

---

### Step 71: 新規 `tests/test_world_bible_integration.py` — Bible × 官能ワークフロー統合テスト

**対象ファイル**: 新規 `tests/test_world_bible_integration.py`

**内容**:

```python
"""tests/test_world_bible_integration.py"""
import pytest
from unittest.mock import MagicMock
from config.world_bible import DEFAULT_BIBLE, get_bible
from config.erotic_pacing import EroticCurve
from src.services.world_bible_deepener import WorldBibleDeepener

def test_bible_in_context():
    """Bible情報がコンテキストに正しく注入されることを確認"""
    deepener = WorldBibleDeepener()
    ctx = deepener.apply_bible_to_context(DEFAULT_BIBLE, {"ep": 1})
    assert "world_bible" in ctx
    wb = ctx["world_bible"]
    assert wb["bible_title"] == "帝国脈動世界"
    assert len(wb["magic_systems"]) > 0
    assert len(wb["social_structures"]) > 0
    assert wb["setting_tone"] == "dark_erotic"

def test_bible_deepener_with_default_bible():
    """デフォルトBibleで深掘り質問が生成されることを確認"""
    deepener = WorldBibleDeepener()
    questions = deepener.generate_deepening_questions(DEFAULT_BIBLE)
    assert len(questions) > 5

def test_bible_originality_scores():
    """独自性評価が0-1の範囲内であることを確認"""
    deepener = WorldBibleDeepener()
    score, issues = deepener.evaluate_bible_originality(DEFAULT_BIBLE)
    assert 0.0 <= score <= 1.0
    assert isinstance(issues, list)

def test_world_bible_prompt_integration():
    """Bible情報がプロンプトに含まれることを確認"""
    from src.engine.prompts.erotic_specialist import EroticSpecialist
    specialist = EroticSpecialist()
    prompt = specialist.build_bible_injection_prompt(DEFAULT_BIBLE)
    assert "帝国脈動世界" in prompt
    assert "魔法体系" in prompt
    assert "社会構造" in prompt
```

---

### Step 72: `src/backend/workflows/refine_erotic_workflow.py` — Bible 品質評価ステップ追加

**対象ファイル**: `src/backend/workflows/refine_erotic_workflow.py`

**変更内容**:
`execute` メソッドの冒頭（設定読み込み後）に Bible 独自性チェックを追加する。

```python
# 0. 世界観Bible 独自性チェック（プロット生成前）
from config.world_bible import get_bible, BIBLE_ORIGINALITY_THRESHOLD
from src.services.world_bible_deepener import WorldBibleDeepener

bible = get_bible(context.get("bible_name", "default"))
deepener = WorldBibleDeepener()
_, bible_issues = deepener.evaluate_bible_originality(bible)
if bible_issues:
    for issue in bible_issues:
        reporter.add_log(f"⚠️ 世界観Bible警告: {issue}")
```

---

## 改善案 #7: エピソード間接続の滑らかさ（Steps 73-96）

前話のラストの引き（クリフハンガー）を次話の冒頭に強く連動させる制御を強化する。1話完結感が出すぎているため、ページを捲らせる「引き」を強化するため。

### Step 73: 新規 `config/episode_hooks.py` — エピソード間接続定数定義

**対象ファイル**: 新規 `config/episode_hooks.py`

**内容**:

```python
"""
config/episode_hooks.py
エピソード間の接続（クリフハンガー / Continuation hooks）定義。
前話ラストと次話冒頭の連動を制御するための定数群。
"""
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CliffhangerTemplate:
    """クリフハンガーテンプレート。"""
    tag: str                              # 例: "kiss_interrupted"
    ending_mood: str                      # 例: "未完の口づけ"
    continuation_mood: str                # 例: "口づけの続き"
    keywords: List[str]                   # 検出用キーワード
    required_continuation_element: str     # 次話冒頭に必ず含める要素

@dataclass
class EpisodeHook:
    """個別エピソードの接続情報。"""
    episode_number: int
    cliffhanger_tag: str
    next_episode_preview: str            # 次話冒頭の誘導文
    unresolved_tension: str               # 未解決の緊張


# 標準クリフハンガーテンプレート
CLIFFHANGER_TEMPLATES = [
    CliffhangerTemplate(
        tag="kiss_interrupted",
        ending_mood="未完の口づけ",
        continuation_mood="口づけの続き",
        keywords=["唇が触れる直前", "唇が触れ", "言葉を飲み込む"],
        required_continuation_element="唇接着の瞬間描写",
    ),
    CliffhangerTemplate(
        tag="clothes_removed_halfway",
        ending_mood="衣の半分だけ脱げた状態",
        continuation_mood="衣の下の視覚",
        keywords=["衣が半分", "一半だけ", "了一半"],
        required_continuation_element="衣装状態の詳細描写",
    ),
    CliffhangerTemplate(
        tag="confession_interrupted",
        ending_mood="告白の言葉が途切れる",
        continuation_mood="告白の続き",
        keywords=["好きだと", "言葉にならない", "告白の言葉"],
        required_continuation_element="未完の言葉の再現",
    ),
    CliffhangerTemplate(
        tag="magic_burst",
        ending_mood="魔法失控の瞬間",
        continuation_mood="魔法の影響",
        keywords=["魔法が暴走", "脈打つ光", "制御が効かない"],
        required_continuation_element="魔法効果の詳細描写",
    ),
    CliffhangerTemplate(
        tag="power_imbalance",
        ending_mood="力が傾いた瞬間",
        continuation_mood="力の劣位側の状況",
        keywords=["立場が逆転", "優位", "劣位", "崩れる均衡"],
        required_continuation_element="力関係の描写",
    ),
    CliffhangerTemplate(
        tag="temperature_rising",
        ending_mood="体温が臨界点に達する",
        continuation_mood="体温上昇の継続",
        keywords=["体温が上がり", "熱い", "火照り", "臨界点"],
        required_continuation_element="体温変化の継続描写",
    ),
]

def get_cliffhanger_template(tag: str) -> Optional[CliffhangerTemplate]:
    """タグに対応するテンプレートを返す。"""
    for t in CLIFFHANGER_TEMPLATES:
        if t.tag == tag:
            return t
    return None

def detect_cliffhanger_type(last_text: str) -> Optional[str]:
    """
    テキストからクリフハンガータイプを自動検出する。

    Returns:
        検出したテンプレートタグ、見つかれば
    """
    for t in CLIFFHANGER_TEMPLATES:
        if any(kw in last_text for kw in t.keywords):
            return t.tag
    return None
```

---

### Step 74: `config/episode_hooks.py` — `__all__` 追加

**対象ファイル**: `config/episode_hooks.py`

**変更内容**:
ファイル末尾に以下を追加する。

```python
__all__ = [
    "CliffhangerTemplate",
    "EpisodeHook",
    "CLIFFHANGER_TEMPLATES",
    "get_cliffhanger_template",
    "detect_cliffhanger_type",
]
```

---

### Step 75: 新規 `src/services/episode_connector.py` — エピソード接続サービス

**対象ファイル**: 新規 `src/services/episode_connector.py`

**内容**:

```python
"""
src/services/episode_connector.py
エピソード間の接続を制御するサービス。
前話のクリフハンガーと次話冒頭の連動を管理する。
"""
from typing import Tuple, List, Optional
from config.episode_hooks import (
    CliffhangerTemplate,
    get_cliffhanger_template,
    detect_cliffhanger_type,
    EpisodeHook,
)

class EpisodeConnector:
    """エピソード接続を 管理するクラス。"""

    # 次話冒頭の誘導キーワード
    CONTINUATION_LEADINS = [
        "引き続き",
        "その瞬間",
        "そのまま",
        "唇が触れ",
        "言葉が途切れる",
        "衣の隙間から",
        "体温が臨界点に達した",
    ]

    # 検出成功后、次話冒頭に必ず含める要素パターン
    MANDATORY_ELEMENTS = {
        "kiss_interrupted": ["唇", "触れる", "瞬間"],
        "clothes_removed_halfway": ["衣", "脱げ", "状態"],
        "confession_interrupted": ["言葉", "未完", "続く"],
        "magic_burst": ["魔法", "失控", "影響"],
        "power_imbalance": ["力関係", "優位", "劣位"],
        "temperature_rising": ["体温", "上昇", "続ける"],
    }

    def detect_cliffhanger(self, text: str) -> Optional[str]:
        """前話ラストからクリフハンガータイプを検出する。"""
        return detect_cliffhanger_type(text)

    def build_continuation_leadin(self, cliffhanger_tag: str) -> str:
        """
        次話冒頭の誘導文を生成する。

        Args:
            cliffhanger_tag: 検出したクリフハンガー类型

        Returns:
            次話冒頭の誘導文（1文程度）
        """
        template = get_cliffhanger_template(cliffhanger_tag)
        if template:
            return f"【Continuation】{template.continuation_mood} — {template.required_continuation_element}"
        return "【Continuation】前話の続き"

    def validate_continuation(self, prev_ending: str, next_start: str) -> Tuple[bool, List[str]]:
        """
        次話冒頭の続き方が前話ラストと矛盾しないかを検証する。

        Returns:
            (is_valid, issues)
        """
        issues = []

        # 1. クリフハンガー検出
        detected_tag = self.detect_cliffhanger(prev_ending)

        if detected_tag:
            required_elements = self.MANDATORY_ELEMENTS.get(detected_tag, [])
            missing = [elem for elem in required_elements if elem not in next_start]
            if missing:
                issues.append(
                    f"クリフハンガー「{detected_tag}」の続きに必須の要素がありません: {missing}"
                )

        # 2. 誘導キーワードチェック
        has_leadin = any(lead in next_start for lead in self.CONTINUATION_LEADINS)
        if not has_leadin and len(next_start) > 10:
            issues.append(
                "次話冒頭に CONTINUATION_LEADINS のキーワードが含まれていません。"
                "ページめくり感を強化するために、前話の続きを示す表現を追加してください。"
            )

        # 3. 時間帯・場所の一貫性（簡易チェック）
        # 「夜」「朝」「部屋」などのキーワードが前話から継続しているか
        setting_keywords = ["夜", "朝", "部屋", "庭", "廊下", "殿堂"]
        prev_has_setting = any(kw in prev_ending for kw in setting_keywords)
        next_has_setting = any(kw in next_start for kw in setting_keywords)
        if prev_has_setting and not next_has_setting:
            issues.append(
                "前話に設定された時間・場所情報が次話冒頭に引き継がれていません。"
            )

        return len(issues) == 0, issues
```

---

### Step 76: `src/services/episode_connector.py` — `create_episode_hook` メソッド追加

**対象ファイル**: `src/services/episode_connector.py`

**変更内容**:
クラス末尾（ファイル末尾）に以下を追加する。

```python
    def create_episode_hook(self, ep_num: int, prev_ending: str, next_start: str) -> EpisodeHook:
        """
        前話ラストと次話冒頭から EpisodeHook を生成する。

        Returns:
            EpisodeHook: 接続情報オブジェクト
        """
        cliffhanger_tag = self.detect_cliffhanger(prev_ending) or "generic"
        template = get_cliffhanger_template(cliffhanger_tag)
        preview = self.build_continuation_leadin(cliffhanger_tag)

        return EpisodeHook(
            episode_number=ep_num,
            cliffhanger_tag=cliffhanger_tag,
            next_episode_preview=preview,
            unresolved_tension=template.continuation_mood if template else "未完の緊張",
        )
```

---

### Step 77: `src/services/episode_connector.py` — `__init__.py` エクスポート追加

**対象ファイル**: `src/services/__init__.py`

**変更内容**:
既存の export 行に以下を追加する。

```python
from src.services.episode_connector import EpisodeConnector
```

---

### Step 78: 新規 `tests/test_episode_connector.py` — 接続サービスユニットテスト

**対象ファイル**: 新規 `tests/test_episode_connector.py`

**内容**:

```python
"""tests/test_episode_connector.py"""
import pytest
from src.services.episode_connector import EpisodeConnector
from config.episode_hooks import detect_cliffhanger_type

def test_detect_kiss_interrupted():
    text = "唇が触れる直前で、彼女は息を止めた。"
    tag = detect_cliffhanger_type(text)
    assert tag == "kiss_interrupted"

def test_detect_clothes_removed_halfway():
    text = "衣が半分だけ脱げかけた状態で、彼は立ち尽くした。"
    tag = detect_cliffhanger_type(text)
    assert tag == "clothes_removed_halfway"

def test_detect_confession_interrupted():
    text = "好きだと、言葉が途切れた。"
    tag = detect_cliffhanger_type(text)
    assert tag == "confession_interrupted"

def test_detect_magic_burst():
    text = "魔法が暴走し、脈打つ光が彼女を包み込んだ。"
    tag = detect_cliffhanger_type(text)
    assert tag == "magic_burst"

def test_detect_temperature_rising():
    text = "体温が臨界点に達し、彼女の視界が揺らいだ。"
    tag = detect_cliffhanger_type(text)
    assert tag == "temperature_rising"

def test_detect_no_cliffhanger():
    text = "二人は静かに別れた。明日また会おうと彼女は言った。"
    tag = detect_cliffhanger_type(text)
    assert tag is None

def test_validate_continuation_valid():
    connector = EpisodeConnector()
    prev = "唇が触れる直前で、彼女は息を止めた。"
    next_start = "そのまま、唇が触れ合った。二人の体温が混ざり合う。"
    is_valid, issues = connector.validate_continuation(prev, next_start)
    assert is_valid is True or len(issues) == 0  # 警告级别

def test_validate_continuation_missing_elements():
    connector = EpisodeConnector()
    prev = "唇が触れる直前で、彼女は息を止めた。"
    next_start = "翌朝、二人は黙って歩いていた。"  # 唇のcontinuation がない
    is_valid, issues = connector.validate_continuation(prev, next_start)
    assert is_valid is False
    assert any("唇" in i for i in issues)

def test_build_continuation_leadin():
    connector = EpisodeConnector()
    leadin = connector.build_continuation_leadin("kiss_interrupted")
    assert "口づけの続き" in leadin or "Continuation" in leadin

def test_create_episode_hook():
    connector = EpisodeConnector()
    hook = connector.create_episode_hook(2, "唇が触れる直前で停止", "唇，接着して")
    assert hook.episode_number == 2
    assert hook.cliffhanger_tag == "kiss_interrupted"
```

---

### Step 79: `src/engine/prompts/erotic_specialist.py` — `build_continuation_prompt` 追加

**対象ファイル**: `src/engine/prompts/erotic_specialist.py`

**変更内容**:
ファイル末尾（Step 54 で追加した `build_bible_injection_prompt` の後に）に以下を追加する。

```python
    def build_continuation_prompt(self, prev_ending: str, ep_num: int, bible: Optional[WorldBible] = None) -> str:
        """
        前話ラストを受けて次話冒頭を生成するためのプロンプトを 构建する。

        Args:
            prev_ending: 前話のエピソードラスト文
            ep_num: 次話のエピソード番号
            bible: 世界観Bible（オプション）

        Returns:
            Continuation 注入用プロンプト文字列
        """
        from src.services.episode_connector import EpisodeConnector
        connector = EpisodeConnector()

        cliffhanger_tag = connector.detect_cliffhanger(prev_ending)
        leadin = connector.build_continuation_leadin(cliffhanger_tag or "generic")

        prompt_parts = [f"【Episode {ep_num} 冒頭 - Continuation Requirement】"]
        prompt_parts.append(f"前話 Episode {ep_num - 1} のラスト: 「{prev_ending}」")
        prompt_parts.append(f"次話冒頭の誘導: {leadin}")

        if cliffhanger_tag:
            template = get_cliffhanger_template(cliffhanger_tag)
            if template:
                prompt_parts.append(f"必須継続要素: {template.required_continuation_element}")
                prompt_parts.append(f"継続ムード: {template.continuation_mood}")

        prompt_parts.append("【続きを書く際の注意】")
        prompt_parts.append("- 前話の最後の緊張をそのまま維持すること")
        prompt_parts.append("- 场景・時間・人物配置を前話から自然に継続すること")
        prompt_parts.append("- 1話完結に陥らず、ページをめくらせる構成にすること")

        return "\n".join(prompt_parts)
```

**注意**: `EpisodeConnector`, `get_cliffhanger_template` の import を確認すること。

---

### Step 80: `src/agents/writing.py` — `write_episode` に Continuation プロンプト注入追加

**対象ファイル**: `src/agents/writing.py`

**変更内容**:
`write_episode` メソッド内で、`prompt = system_prompt + "\n\n" + user_prompt` を構築する部分（または同等の位置）を以下に変更する。

```python
        # Continuation プロンプト注入（前話ラスト情報がある場合）
        if prev_episode_ending:
            from src.engine.prompts.erotic_specialist import EroticSpecialist
            specialist = EroticSpecialist()
            continuation_prompt = specialist.build_continuation_prompt(
                prev_episode_ending,
                ep_num,
                bible=bible if 'bible' in dir() else None,
            )
            prompt = prompt + "\n\n" + continuation_prompt

        # 官能シーン処理（既存コード省略...）
```

**注意**: `prev_episode_ending` は `context` 辞書から取得できるように事前に設定されていることを確認する。

---

### Step 81: `src/backend/tasks.py` — `write_episode` タスクに prev_episode_ending 対応追加

**対象ファイル**: `src/backend/tasks.py`

**変更内容**:
`write_episode` タスク関数 найдите `context = {...}` の部分を以下のように変更する。

```python
    context = {
        "book_id": book_id,
        "chapter_id": chapter_id,
        "ep_num": ep_num,
        "nsfw_enabled": nsfw_enabled,
        "erotic_intensity": erotic_intensity,
        "prev_episode_ending": prev_episode_ending,  # 追加
        "bible_name": bible_name,                    # 追加
    }
```

**注意**: `prev_episode_ending` と `bible_name` が関数の引数になければ追加する。

---

### Step 82: `src/services/episode_connector.py` — `inject_continuation_guidance` メソッド追加

**対象ファイル**: `src/services/episode_connector.py`

**変更内容**:
`validate_continuation` メソッドの後に以下を追加する。

```python
    def inject_continuation_guidance(self, prev_ending: str, draft_text: str) -> str:
        """
        執筆ドラフトの冒頭にContinuation 注記を挿入する。

        檢證結果に基づいて、ドラフトの冒頭を修正する。
        """
        issues = []

        # 1. クリフハンガー検出
        detected_tag = self.detect_cliffhanger(prev_ending)
        if detected_tag:
            required_elements = self.MANDATORY_ELEMENTS.get(detected_tag, [])
            missing = [elem for elem in required_elements if elem not in draft_text[:100]]
            if missing:
                issues.append(f"冒頭に必須要素不足: {missing}")

        # 2. 誘導キーワードチェック
        has_leadin = any(lead in draft_text for lead in self.CONTINUATION_LEADINS)
        if not has_leadin:
            issues.append("誘導キーワード不足。冒頭に『そのまま』『引き続き』等を追加してください。")

        # 問題がなければそのまま返す
        if not issues:
            return draft_text

        # 問題がある場合、冒頭に警告を注入
        warning = "\n".join([f"[Continuation Warning] {i}" for i in issues])
        return f"{warning}\n\n{draft_text}"
```

---

### Step 83: `src/services/episode_connector.py` — `inject_continuation_guidance` テスト追加

**対象ファイル**: `tests/test_episode_connector.py`

**変更内容**:
末尾に以下を追加する。

```python
def test_inject_continuation_guidance_valid():
    connector = EpisodeConnector()
    prev = "唇が触れる直前で、彼女は息を止めた。"
    next_draft = "そのまま唇が触れ合った。二人の呼吸が混ざり合う。"
    result = connector.inject_continuation_guidance(prev, next_draft)
    assert "[Continuation Warning]" not in result

def test_inject_continuation_guidance_missing_warning():
    connector = EpisodeConnector()
    prev = "唇が触れる直前で、彼女は息を止めた。"
    next_draft = "翌朝、二人は静かに会った。"  # 唇continuation がない
    result = connector.inject_continuation_guidance(prev, next_draft)
    assert "[Continuation Warning]" in result
```

---

### Step 84: `src/backend/workflows/refine_erotic_workflow.py` — Continuation 検証追加

**対象ファイル**: `src/backend/workflows/refine_erotic_workflow.py`

**変更内容**:
`execute` メソッド内の研磨処理後に、 Continuation 検証を追加する。

```python
# 4. Continuation 検証（前話ラスト → 次話冒頭の連動チェック）
if prev_episode_ending:
    from src.services.episode_connector import EpisodeConnector
    connector = EpisodeConnector()
    next_start = refined_content[:200]  # 先頭200文字を次話冒頭として検証
    is_valid, cont_issues = connector.validate_continuation(prev_episode_ending, next_start)
    if not is_valid:
        for issue in cont_issues:
            reporter.add_log(f"⚠️ Continuation警告: {issue}")
    # inject_continuation_guidance でドラフト修正注記を付与
    refined_content = connector.inject_continuation_guidance(prev_episode_ending, refined_content)
```

---

### Step 85: `config/episode_hooks.py` — 新規クリフハンガーテンプレート追加

**対象ファイル**: `config/episode_hooks.py`

**変更内容**:
`CLIFFHANGER_TEMPLATES` リストに以下5個を追加する。

```python
    CliffhangerTemplate(
        tag="authority_challenge",
        ending_mood="権限への反抗の瞬間",
        continuation_mood="反抗の后果",
        keywords=["反発", "逆らう", "主張する", "嫌悪"],
        required_continuation_element="対抗势力の描写",
    ),
    CliffhangerTemplate(
        tag="secret_revealed",
        ending_mood="秘密が明かされる瞬間",
        continuation_mood="秘密を知った後の反応",
        keywords=["秘密を知った", "正体が判明", "실명"],
        required_continuation_element="秘密の影響描写",
    ),
    CliffhangerTemplate(
        tag="desire_escalation",
        ending_mood="欲望が臨界点を迎える",
        continuation_mood="欲望の奔流",
        keywords=["抑えきれない", "欲望が满ちる", "抗えない"],
        required_continuation_element="欲望描写の継続",
    ),
    CliffhangerTemplate(
        tag="social_boundary_crossed",
        ending_mood="社会的立場を超えた接触",
        continuation_mood="越境的行動的后果",
        keywords=["立場を越え", "禁断の", "realm越え"],
        required_continuation_element="社会的緊張の継続",
    ),
    CliffhangerTemplate(
        tag="trust_broken",
        ending_mood="信頼が崩れる瞬間",
        continuation_mood="裏切りの影響",
        keywords=["裏切られた", "信頼が揺らぐ", "期待が崩れる"],
        required_continuation_element="信頼問題の詳細描写",
    ),
```

---

### Step 86: `src/services/episode_connector.py` — `MANDATORY_ELEMENTS` 更新

**対象ファイル**: `src/services/episode_connector.py`

**変更内容**:
`MANDATORY_ELEMENTS` 辞리에 Step 85 で追加したテンプレート用の要素を追加する。

```python
    MANDATORY_ELEMENTS = {
        "kiss_interrupted": ["唇", "触れる", "瞬間"],
        "clothes_removed_halfway": ["衣", "脱げ", "状態"],
        "confession_interrupted": ["言葉", "未完", "続く"],
        "magic_burst": ["魔法", "失控", "影響"],
        "power_imbalance": ["力関係", "優位", "劣位"],
        "temperature_rising": ["体温", "上昇", "続ける"],
        "authority_challenge": ["反発", "対抗", "主張"],
        "secret_revealed": ["秘密", "実名", "判明"],
        "desire_escalation": ["欲望", "臨界点", "抑えない"],
        "social_boundary_crossed": ["立場を越え", "禁断", "越え"],
        "trust_broken": ["信頼", "裏切り", "期待"],
    }
```

---

### Step 87: `src/services/episode_connector.py` — `generate_continuation_advice` メソッド追加

**対象ファイル**: `src/services/episode_connector.py`

**変更内容**:
`inject_continuation_guidance` の後に以下を追加する。

```python
    def generate_continuation_advice(self, prev_ending: str) -> str:
        """
        前話ラストに基づいて、次話執筆へのアドバイスを提供する。

        Args:
            prev_ending: 前話ラストテキスト

        Returns:
            アドバイス文字列
        """
        cliffhanger_tag = self.detect_cliffhanger(prev_ending)

        if cliffhanger_tag is None:
            return (
                "【Advise】前話ラストに明らかなクリフハンガーが検出されませんでした。\n"
                "-pagesをめくらせるために、未解決の緊張をラストに含めることを検討してください。\n"
                "例: 未完の口づけ、言葉が途切れる瞬間、魔法の暴走等等。"
            )

        template = get_cliffhanger_template(cliffhanger_tag)
        if template:
            return (
                f"【Advise】検出されたクリフハンガー: {template.ending_mood}\n"
                f"次話冒頭では「{template.required_continuation_element}」を必ず含めてください。\n"
                f"継続ムード: {template.continuation_mood}\n"
                f"禁止: 時間を大きく飛ばすこと (§§ 翌朝等)、人物配置を変更すること。"
            )

        return "【Advise】継続執筆の注意: 前話ラストの緊張を維持してください。"
```

---

### Step 88: `tests/test_episode_connector.py` — `generate_continuation_advice` テスト追加

**対象ファイル**: `tests/test_episode_connector.py`

**変更内容**:
末尾に以下を追加する。

```python
def test_generate_continuation_advice_with_cliffhanger():
    connector = EpisodeConnector()
    prev = "唇が触れる直前で、彼女は息を止めた。"
    advice = connector.generate_continuation_advice(prev)
    assert "口づけの続き" in advice or "Continuation" in advice or "唇" in advice

def test_generate_continuation_advice_without_cliffhanger():
    connector = EpisodeConnector()
    prev = "二人は静かに別れた。明日また会おうと彼女は言った。"
    advice = connector.generate_continuation_advice(prev)
    assert "Advise" in advice
```

---

### Step 89: `src/backend/server.py` — `/api/episode/continuation-check` エンドポイント追加

**対象ファイル**: `src/backend/server.py`

**変更内容**:
既存の API route 部に以下を追加する。

```python
@app.post("/api/episode/continuation-check")
def check_continuation(prev_ending: str, next_start: str):
    """
    前話ラストと次話冒頭のContinuityを検証する。

    Body (JSON):
        prev_ending: 前話ラストテキスト
        next_start: 次話冒頭テキスト
    """
    from src.services.episode_connector import EpisodeConnector

    connector = EpisodeConnector()
    is_valid, issues = connector.validate_continuation(prev_ending, next_start)

    return {
        "is_valid": is_valid,
        "issues": issues,
        "detected_cliffhanger": connector.detect_cliffhanger(prev_ending),
        "advice": connector.generate_continuation_advice(prev_ending),
    }
```

---

### Step 90: `src/backend/server.py` — `/api/episode/continuation-advice` エンドポイント追加

**対象ファイル**: `src/backend/server.py`

**変更内容**:
`/api/episode/continuation-check` の後に以下を追加する。

```python
@app.get("/api/episode/continuation-advice")
def get_continuation_advice(prev_ending: str):
    """
    前話ラストに基づいて次話執筆へのアドバイスを提供する。

    Query Params:
        prev_ending: 前話ラストテキスト
    """
    from src.services.episode_connector import EpisodeConnector

    connector = EpisodeConnector()
    advice = connector.generate_continuation_advice(prev_ending)
    cliffhanger_tag = connector.detect_cliffhanger(prev_ending)

    return {
        "advice": advice,
        "detected_cliffhanger": cliffhanger_tag,
        "has_cliffhanger": cliffhanger_tag is not None,
    }
```

---

### Step 91: 新規 `tests/integration/test_episode_connector_integration.py` — エピソード接続統合テスト

**対象ファイル**: 新規 `tests/integration/test_episode_connector_integration.py`

**内容**:

```python
"""tests/integration/test_episode_connector_integration.py"""
import pytest
from config.episode_hooks import (
    CLIFFHANGER_TEMPLATES,
    get_cliffhanger_template,
    detect_cliffhanger_type,
)
from src.services.episode_connector import EpisodeConnector

def test_all_templates_have_required_elements():
    """全テンプレートに必須継続要素が定義されていることを確認"""
    for template in CLIFFHANGER_TEMPLATES:
        assert template.required_continuation_element
        assert template.tag
        assert len(template.keywords) >= 2

def test_detect_all_template_types():
    """全テンプレート类型のテキストを正しく検出できることを確認"""
    test_cases = [
        ("kiss_interrupted", "唇が触れる直前で停止"),
        ("clothes_removed_halfway", "衣が半分脱げた"),
        ("confession_interrupted", "好きだと言葉が途切れた"),
        ("magic_burst", "魔法が脈打つ光とともに暴走した"),
        ("power_imbalance", "立場が崩れ、優位が劣位に変わった"),
        ("temperature_rising", "体温が臨界点を越えた"),
        ("authority_challenge", "彼は反撥の声を上げた"),
        ("secret_revealed", "秘密を知った彼女の顔が凍った"),
        ("desire_escalation", "欲望が抑えきれなくなった"),
        ("social_boundary_crossed", "立場を超えて，抱きしめた"),
        ("trust_broken", "信頼が崩れる音が聞こえた"),
    ]
    connector = EpisodeConnector()
    for expected_tag, text in test_cases:
        detected = connector.detect_cliffhanger(text)
        assert detected == expected_tag, f"Expected {expected_tag}, got {detected} for text: {text}"

def test_episode_connector_validate_all_templates():
    """全テンプレート类型で Continuation 検証が正しく動作することを確認"""
    connector = EpisodeConnector()
    for template in CLIFFHANGER_TEMPLATES:
        # 必須要素を含んだ次話冒頭
        good_next = f"{template.required_continuation_element}が明確に描写されている。"
        # 検出用の前話
        prev = f"何かが{template.ending_mood}の状態で終わった。"
        is_valid, issues = connector.validate_continuation(prev, good_next)
        # 必須要素が含まれているので issues は空であるべき
        assert len(issues) == 0, f"Template {template.tag}: {issues}"

def test_no_cliffhanger_detection():
    """クリフハンガーがない平常的文章は検出されないことを確認"""
    connector = EpisodeConnector()
    normal_texts = [
        "二人は静かに茶を飲んだ。",
        "彼女は窓の外を見た。特になかった。",
        "夜が更けて、眠気が差し込んだ。",
    ]
    for text in normal_texts:
        assert connector.detect_cliffhanger(text) is None
```

---

### Step 92: `config/episode_hooks.py` — `EpisodeHook` シリアライズ対応

**対象ファイル**: `config/episode_hooks.py`

**変更内容**:
`EpisodeHook` dataclass にシリアライズ用のメソッドを追加する。

```python
@dataclass
class EpisodeHook:
    episode_number: int
    cliffhanger_tag: str
    next_episode_preview: str
    unresolved_tension: str

    def to_dict(self) -> dict:
        """辞書に変換する（API返値用）。"""
        return {
            "episode_number": self.episode_number,
            "cliffhanger_tag": self.cliffhanger_tag,
            "next_episode_preview": self.next_episode_preview,
            "unresolved_tension": self.unresolved_tension,
        }
```

---

### Step 93: `src/services/episode_connector.py` — `create_episode_hook` の返り値を更新

**対象ファイル**: `src/services/episode_connector.py`

**変更内容**:
`create_episode_hook` メソッドの返り値の docstring を以下のように更新する。

```python
    def create_episode_hook(self, ep_num: int, prev_ending: str, next_start: str) -> EpisodeHook:
        """
        前話ラストと次話冒頭から EpisodeHook を生成する。

        Returns:
            EpisodeHook: 接続情報オブジェクト（to_dict() でシリアライズ可能）
        """
```

---

### Step 94: `src/backend/tasks.py` — `generate_chapter` タスクに Continuation 対応追加

**対象ファイル**: `src/backend/tasks.py`

**変更内容**:
`generate_chapter` タスク関数 найдите `ep_data_list` を構築する部分を以下のように変更する。

```python
    # prev_episode_ending は前話の最終文を設定
    prev_episode_ending = None
    if len(results) > 0:
        last_result = results[-1]
        # 前話の結果からラスト3文を抽出
        sentences = last_result["content"].split("。")
        if len(sentences) >= 2:
            prev_episode_ending = "。".join(sentences[-2:]) + "。"

    # EpisodeHook 生成
    from src.services.episode_connector import EpisodeConnector
    connector = EpisodeConnector()
    if prev_episode_ending:
        current_start = chapter_content[:100]  # 暫定
        hook = connector.create_episode_hook(ep_num, prev_episode_ending, current_start)
        reporter.add_log(f"🔗 Episode {ep_num} Hook: {hook.cliffhanger_tag} / {hook.unresolved_tension}")
```

---

### Step 95: 新規 `tests/test_episode_hooks_config.py` — episode_hooks 設定ファイルユニットテスト

**対象ファイル**: 新規 `tests/test_episode_hooks_config.py`

**内容**:

```python
"""tests/test_episode_hooks_config.py"""
import pytest
from config.episode_hooks import (
    CliffhangerTemplate,
    EpisodeHook,
    CLIFFHANGER_TEMPLATES,
    get_cliffhanger_template,
    detect_cliffhanger_type,
)

def test_all_templates_valid():
    """全テンプレートが必須フィールドを持つことを確認"""
    for t in CLIFFHANGER_TEMPLATES:
        assert t.tag
        assert t.ending_mood
        assert t.continuation_mood
        assert len(t.keywords) >= 2
        assert t.required_continuation_element

def test_get_cliffhanger_template_valid():
    """存在タグの取得が正常工作することを確認"""
    t = get_cliffhanger_template("kiss_interrupted")
    assert t is not None
    assert t.tag == "kiss_interrupted"

def test_get_cliffhanger_template_invalid():
    """存在しないタグを取得した場合に None が返ることを確認"""
    t = get_cliffhanger_template("nonexistent_tag")
    assert t is None

def test_episode_hook_to_dict():
    """EpisodeHook.to_dict() が正常工作することを確認"""
    hook = EpisodeHook(
        episode_number=2,
        cliffhanger_tag="kiss_interrupted",
        next_episode_preview="口づけの続き",
        unresolved_tension="未完の口づけ",
    )
    d = hook.to_dict()
    assert d["episode_number"] == 2
    assert d["cliffhanger_tag"] == "kiss_interrupted"

def test_no_duplicate_tags():
    """テンプレートタグが重複していないことを確認"""
    tags = [t.tag for t in CLIFFHANGER_TEMPLATES]
    assert len(tags) == len(set(tags))

def test_continuation_mood_differs_from_ending():
    """各テンプレートのending_moodとcontinuation_moodが異なることを確認"""
    for t in CLIFFHANGER_TEMPLATES:
        assert t.ending_mood != t.continuation_mood, f"Template {t.tag}: moods should differ"
```

---

### Step 96: `src/backend/workflows/refine_erotic_workflow.py` — 全ワークフローへの統合確認

**対象ファイル**: `src/backend/workflows/refine_erotic_workflow.py`

**変更内容**:
以下の統合項目が確認・実装済みであることを確認する。

1. **Step 72 済み**: `execute` 冒頭に Bible 独自性チェック追加済み
2. **Step 84 済み**: `execute` 研磨処理後に Continuation 検証追加済み
3. `prev_episode_ending` 変数が context から正しく渡されていることを確認

```python
# execute メソッド冒頭の context 確認ポイント
# prev_episode_ending = context.get("prev_episode_ending")
# bible_name = context.get("bible_name", "default")
```

`refine_erotic_workflow.py` を開き、上述の統合項目が全て含まれていることを目で確認する（コード変更は必要なし）。

---

## 新規 Steps 一覧表（49-96）

| Step | 対象ファイル | 概要 |
|------|-------------|------|
| 49 | 新規 `config/world_bible.py` | Bible 基本構造定義 |
| 50 | `config/world_bible.py` | `get_bible`/`register_bible` 関数追加 |
| 51 | 新規 `src/services/world_bible_deepener.py` | 深掘りサービスクラス作成 |
| 52 | `src/services/world_bible_deepener.py` | `apply_bible_to_context` メソッド追加 |
| 53 | `src/services/__init__.py` | `WorldBibleDeepener` エクスポート |
| 54 | `src/engine/prompts/erotic_specialist.py` | Bible 注入プロンプトビルダー追加 |
| 55 | `src/engine/prompts/erotic_specialist.py` | `build_scene_prompt` に bible パラメータ追加 |
| 56 | `src/agents/writing.py` | `write_episode` に Bible 伝播追加 |
| 57 | 新規 `tests/test_world_bible_deepener.py` | 深掘りサービスユニットテスト |
| 58 | `tests/test_erotic_workflow.py` | Bible 統合テスト追加 |
| 59 | `config/world_bible.py` | 型ヒント追加と `__all__` |
| 60 | 新規 `src/engine/prompts/world_bible_prompt.py` | 深掘り質問票プロンプト生成 |
| 61 | `src/backend/tasks.py` | `deepen_bible_task` 追加 |
| 62 | `src/backend/server.py` | `/api/bible/deepen` エンドポイント追加 |
| 63 | `config/world_bible.py` | 独自性評価定数追加 |
| 64 | `src/services/world_bible_deepener.py` | 評価閾値定数の活用 |
| 65 | `tests/test_world_bible_deepener.py` | 独自性評価テスト強化 |
| 66 | `src/services/world_bible_deepener.py` | `generate_supplemental_lore` 追加 |
| 67 | `tests/test_world_bible_deepener.py` | 補足ロア生成テスト追加 |
| 68 | `src/engine/prompts/world_bible_prompt.py` | 補足ロア生成プロンプト追加 |
| 69 | `src/backend/tasks.py` | `supplemental_lore_task` 追加 |
| 70 | `src/backend/server.py` | `/api/bible/lore` エンドポイント追加 |
| 71 | 新規 `tests/test_world_bible_integration.py` | Bible × 官能ワークフロー統合テスト |
| 72 | `src/backend/workflows/refine_erotic_workflow.py` | Bible 独自性チェック統合 |
| 73 | 新規 `config/episode_hooks.py` | クリフハンガー・テンプレート定義 |
| 74 | `config/episode_hooks.py` | `__all__` 追加 |
| 75 | 新規 `src/services/episode_connector.py` | 接続サービスクラス作成 |
| 76 | `src/services/episode_connector.py` | `create_episode_hook` メソッド追加 |
| 77 | `src/services/__init__.py` | `EpisodeConnector` エクスポート |
| 78 | 新規 `tests/test_episode_connector.py` | 接続サービスユニットテスト |
| 79 | `src/engine/prompts/erotic_specialist.py` | `build_continuation_prompt` 追加 |
| 80 | `src/agents/writing.py` | Continuation プロンプト注入追加 |
| 81 | `src/backend/tasks.py` | `write_episode` タスクに prev_episode_ending 対応 |
| 82 | `src/services/episode_connector.py` | `inject_continuation_guidance` 追加 |
| 83 | `tests/test_episode_connector.py` | 注記注入テスト追加 |
| 84 | `src/backend/workflows/refine_erotic_workflow.py` | Continuation 検証統合 |
| 85 | `config/episode_hooks.py` | 5種新規テンプレート追加 |
| 86 | `src/services/episode_connector.py` | `MANDATORY_ELEMENTS` 更新 |
| 87 | `src/services/episode_connector.py` | `generate_continuation_advice` 追加 |
| 88 | `tests/test_episode_connector.py` | アドバイス生成テスト追加 |
| 89 | `src/backend/server.py` | `/api/episode/continuation-check` 追加 |
| 90 | `src/backend/server.py` | `/api/episode/continuation-advice` 追加 |
| 91 | 新規 `tests/integration/test_episode_connector_integration.py` | 全テンプレート統合テスト |
| 92 | `config/episode_hooks.py` | `EpisodeHook.to_dict()` 追加 |
| 93 | `src/services/episode_connector.py` | `create_episode_hook` docstring 更新 |
| 94 | `src/backend/tasks.py` | `generate_chapter` に Hook 記録追加 |
| 95 | 新規 `tests/test_episode_hooks_config.py` | episode_hooks 設定ファイルテスト |
| 96 | `src/backend/workflows/refine_erotic_workflow.py` | 全ワークフロー統合確認 |

---

## 推奨実装順（Steps 49-96 を含む全体）

| Phase | Steps | 内容 |
|-------|-------|------|
| Phase 1 | 49-53, 59-60 | Bible 基本構造 + 深掘りサービス基盤 |
| Phase 2 | 54-58, 61-62 | Prompt 注入 + API + 基本テスト |
| Phase 3 | 63-67, 71-72 | 独自性評価 + 補足ロア + ワークフロー統合 |
| Phase 4 | 73-78, 92-95 | 接続テンプレート + 接続サービス基盤 |
| Phase 5 | 79-83, 87-88 | Prompt 注入 + 注記生成 + アドバイス |
| Phase 6 | 84, 89-91, 96 | ワークフロー統合 + API + 全統合テスト |

Bible（Steps 49-72）と Episode Connector（Steps 73-96）は独立に実装可能。どちらから先に実施しても良い。

---

## 全 Steps 概要表（1-96）

| Step | 概要 |
|------|------|
| 1-8 | ボキャブラリ拡張 |
| 9-14 | 閾値定義 |
| 15-20 | consent_state 動的検証 |
| 21-28 | afterglow 品質評価 |
| 29-35 | 統合テスト追加 |
| 36-40 | 密度管理機能拡張 |
| 41-43 | キャリブレーションパイプライン |
| 44-48 | 強制力 + 伏字拡張性 |
| **49-72** | **世界観Bible深化** |
| **73-96** | **エピソード間接続滑らか化** |