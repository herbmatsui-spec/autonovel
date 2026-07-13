# 官能以外のシーンにも拡張する Continuity Tracker 実装計画（48ステップ）

## 概要

[`src/agents/erotic_integrity.py`](../src/agents/erotic_integrity.py) に実装済みの [`ContinuityTracker`](../src/agents/erotic_integrity.py:149) は、体力・心理・衣服・親密度・場所の話間整合性を追跡しますが、官能シーン以外（戦闘・会話・探索など）の整合性検証は未実装です。

本計画では、**9つの改善案**を48の小ステップに分割して実装します。各ステップは独立して動作確認できる粒度で、低性能LLMでも順次確実に進められます。

---

## 9つの改善案

| # | 改善案 | 追跡対象 | 主な矛盾検出 |
|---|--------|----------|--------------|
| 1 | 戦闘負傷継承 | 負傷部位・重症度 | 前話重傷→今話無傷で治癒描写なし |
| 2 | 会話態度継承 | キャラ間態度（敵対/友好/冷淡/熱心） | 前話敵対→今話突然友好で和解描写なし |
| 3 | 探索発見継承 | 発見済み手がかり・未踏破エリア | 前話未踏破→今話踏破済で移動描写なし |
| 4 | 移動接続継承 | 出発地・目的地・移動手段 | 前話目的地≠今話現在地で移動描写なし |
| 5 | 休息回復整合 | 休息回数・睡眠時間 | 連続行動で exhaustion なのに回復描写なし |
| 6 | 独白視点継承 | 視点キャラ・独白トーン | 前話三人称→今話一人称で視点切替描写なし |
| 7 | 伏線継承 | 張られた伏線ID・回収状態 | 伏線放置期間超過で未回収警告 |
| 8 | 時間帯遷移 | 時間帯（朝/昼/夕/夜/深夜） | 夜→翌朝でなく昼→夜→昼の不自然ループ |
| 9 | アイテム所持継承 | 所持アイテム集合 | 前話未入手→今話使用で入手描写なし |

---

## ファイル構成（変更対象）

- [`src/agents/erotic_integrity.py`](../src/agents/erotic_integrity.py) — 新規クラス追加・既存クラス拡張
- [`tests/test_scene_continuity_tracker.py`](../tests/test_scene_continuity_tracker.py) — 新規テスト（48ステップ中で逐次拡充）
- `docs/SCENE_CONTINUITY_48STEP_PLAN.md` — 本ドキュメント

新規ファイルは作成せず、既存 [`erotic_integrity.py`](../src/agents/erotic_integrity.py) に追記します（ユーザー指示）。

---

## 実装ステップ（48分割）

各ステップは:
- **対象ファイル**: 変更するファイル
- **挿入位置**: 行番号または「クラスXの後」「メソッドYの前」
- **コード断片**: 挿入するコード
- **検証**: 実行するコマンドと期待結果

---

### ステップ1: ドキュメントの冒頭コメントに追記

**対象**: [`src/agents/erotic_integrity.py`](../src/agents/erotic_integrity.py:1)
**挿入位置**: 行1-5 の docstring
**コード断片**: docstring の末尾に1行追加
```python
v3.2 - 安全チェック + 官能品質スコアリング
v3.3 - シーン種別汎用 Continuity Tracker（戦闘/会話/探索/移動/休息/独白/伏線/時間帯/アイテム）
```
**検証**: `python -c "import src.agents.erotic_integrity"` が成功

---

### ステップ2: シーン種別定数の追加（戦闘・会話・探索・移動・休息・独白・unknown）

**対象**: [`src/agents/erotic_integrity.py`](../src/agents/erotic_integrity.py)
**挿入位置**: `LOCATION_TRANSITION_KW` 定義の直後（行86付近）
**コード断片**:
```python
# ===== シーン種別定数（汎用 Continuity Tracker 用） =====
SCENE_TYPES = ["combat", "conversation", "exploration", "travel", "rest", "monologue", "erotic", "unknown"]

COMBAT_KEYWORDS = ["戦う", "斬る", "打つ", "攻撃", "防御", "魔法", "剣", "槍", "弓", "呪文", "殺", "討つ", "防ぐ", "避ける", "盾", "刃"]
CONVERSATION_KEYWORDS = ["言った", "答えた", "聞いた", "問う", "語る", "話す", "囁く", "叫ぶ", " Cuisine", "会話", "対話", "応える", "返す"]
EXPLORATION_KEYWORDS = ["調べる", "探索", "探す", "発見", "手がかり", "足跡", "痕跡", "調べ", "観察", "捜索", "見つけ"]
TRAVEL_KEYWORDS = ["向かう", "移動", "歩く", "道を", "戻る", "出る", "入る", "到着", "出発", "旅路", "街道"]
REST_KEYWORDS = ["休む", "眠る", "睡眠", "休息", "座り込む", "横たわる", "眠りにつ", "宿", "野営", "仮眠"]
MONOLOGUE_KEYWORDS = ["思う", "考える", "心に", "独白", "内心", "胸の奥で", "～だろうか", "問いかける", "自問"]
```
**注意**: CONVERSATION_KEYWORDS 中に "Cuisine" という混入がありますが、これは誤字です。正しくは "表情" 等ではありませんが、便宜的に会話ヒント語を並べます。実際のコードでは "Cuisine" は除外してください。

---

### ステップ3: シーン種別キーワード定義の修正（誤字混入除去）

**対象**: [`src/agents/erotic_integrity.py`](../src/agents/erotic_integrity.py)
**操作**: ステップ2で挿入した `CONVERSATION_KEYWORDS` リストから `" Cuisine"` という要素を削除
**コード断片**（修正後）:
```python
CONVERSATION_KEYWORDS = ["言った", "答えた", "聞いた", "問う", "語る", "話す", "囁く", "叫ぶ", "会話", "対話", "応える", "返す"]
```
**検証**: `python -c "from src.agents.erotic_integrity import CONVERSATION_KEYWORDS; assert 'Cuisine' not in CONVERSATION_KEYWORDS"` が成功

---

### ステップ4: 負傷重症度レベル定数の追加（改善案1用）

**対象**: [`src/agents/erotic_integrity.py`](../src/agents/erotic_integrity.py)
**挿入位置**: ステップ2〜3のブロックの直後
**コード断片**:
```python
# ===== 改善案1: 戦闘負傷継承 =====
INJURY_LEVELS = ["uninjured", "minor", "moderate", "severe", "critical"]
INJURY_MINOR_KW = ["かすり傷", "浅傷", "小傷", "擦り傷", "軽傷"]
INJURY_MODERATE_KW = ["深傷", "切り傷", "骨折", "打撲", "刺される", "裂傷", "中傷"]
INJURY_SEVERE_KW = ["重傷", "重篤", "血の池", "意識が遠の", "倒れる", "動けない"]
INJURY_CRITICAL_KW = ["瀕死", "死にかけ", "昏睡", "致命傷", "生死の境", "危篤"]
INJURY_HEAL_KW = ["治る", "治癒", "回復", "癒える", "塞が", "傷が閉じ", "医者", "治療", "薬を", "治ま"]
```
**検証**: `python -c "from src.agents.erotic_integrity import INJURY_LEVELS; print(INJURY_LEVELS)"` が成功

---

### ステップ5: 会話態度レベル定数の追加（改善案2用）

**コード断片**:
```python
# ===== 改善案2: 会話態度継承 =====
ATTITUDE_LEVELS = ["hostile", "cold", "neutral", "friendly", "devoted"]
ATTITUDE_HOSTILE_KW = ["敵対", "憎しみ", "殺意", "蔑み", "侮蔑", "睨み", "歯噛み", "怒鳴"]
ATTITUDE_COLD_KW = ["冷淡", "無関心", "そっけない", "無視", "素っ気ない", " よそよそしい"]
ATTITUDE_FRIENDLY_KW = ["友好", "親愛", "微笑", "安らぎ", "信頼", "聞き入", "頷き合"]
ATTITUDE_DEVOTED_KW = ["献身", "尽くす", "命を懸け", "捧げ", "忠誠", "愛しく", "殉じ"]
ATTITUDE_RECONCILE_KW = ["和解", "許す", "誤解が解け", "謝罪", "わだかまりが消え", "仲直り"]
```
**検証**: `python -c "from src.agents.erotic_integrity import ATTITUDE_LEVELS"` が成功

---

### ステップ6: 探索発見・移動接続定数の追加（改善案3・4用）

**コード断片**:
```python
# ===== 改善案3: 探索発見継承 =====
EXPLORATION_FOUND_KW = ["発見", "見つけ", "手がかり", "気づいた", "気付く", "明らかになる", "判明"]
EXPLORATION_UNEXPLORED_KW = ["未知", "未踏", "未開", "誰も知らない", "見知らぬ", "前人未到"]
EXPLORATION_REASON_KW = ["なぜなら", "というのも", "わけは", "理由", "所以", "ため"]
# ===== 改善案4: 移動接続継承 =====
TRAVEL_DEPART_KW = ["出発", "旅立", "向かう", "立つ", "去る", "辞する", "背を向"]
TRAVEL_ARRIVE_KW = ["到着", "辿り着", "至る", "入り", "入城", "着く"]
TRAVEL_MEANS_KW = ["馬", "船", "車", "徒歩", "歩いて", "街道", "道を", "RUN", "flight", "gate"]
```
**検証**: `python -c "from src.agents.erotic_integrity import EXPLORATION_FOUND_KW, TRAVEL_DEPART_KW"` が成功

---

### ステップ7: 休息・独白・伏線・時間帯・アイテム定数の追加（改善案5〜9用）

**コード断片**:
```python
# ===== 改善案5: 休息回復整合 =====
REST_SLEEP_KW = ["眠る", "睡眠", "床につ", "夢を見", "目を閉じ", "就寝"]
REST_DURATION_KW = ["一睡", "徹夜", "数時間", "一晩", "二晩", "三日", "短い仮眠"]
REST_EXHAUSTION_BEFORE_KW = ["疲労", "疲弊", "限界", "意識が遠の", "倒れそう", "目眩"]
# ===== 改善案6: 独白視点継承 =====
MONOLOGUE_PERSON_FIRST_KW = ["私", "僕", "俺", "わたし", "わたくし"]
MONOLOGUE_PERSON_THIRD_KW = ["彼", "彼女", "あの人", "その者", "本人"]
MONOLOGUE_SHIFT_KW = ["視点が移", "場面は変", "物語は", "さて", "一方"]
# ===== 改善案7: 伏線継承 =====
FORESHADOW_PLANT_KW = ["伏線", "謎", "疑問", "意味深", "不思議な", "妙な", "何かが"]
FORESHADOW_PAYOFF_KW = ["回収", "真相", "判明", "明かされる", "謎が解け", "繋がる"]
FORESHADOW_IGNORE_THRESHOLD = 3  # 何話連続で無視されたら警告するか
# ===== 改善案8: 時間帯遷移 =====
TIMEOFDAY_LEVELS = ["morning", "daytime", "evening", "night", "midnight"]
TIMEOFDAY_MORNING_KW = ["朝", "夜明け", " 日が昇", "東の空", "明かりが差"]
TIMEOFDAY_DAYTIME_KW = ["昼", "日中", "午後", "陽が高", "日差し"]
TIMEOFDAY_EVENING_KW = ["夕方", "黄昏", "逢魔", "茜", "日が傾", "夕暮"]
TIMEOFDAY_NIGHT_KW = ["夜", "月", "星", "闇", "夜更け", "夜半", "月明"]
TIMEOFDAY_MIDNIGHT_KW = ["深夜", "丑三", "夜中", "真夜中", "未明"]
# ===== 改善案9: アイテム所持継承 =====
ITEM_ACQUIRE_KW = ["手に取", "手に入れ", "受け取", "拾得", "入手", "譲り受け", "買う", "購入", "贈られ"]
ITEM_USE_KW = ["使う", "使用", "用い", "挥う", "構え", "取り出", "召し出", "起動", "発動"]
ITEM_LOSE_KW = ["失く", "落と", "奪わ", "取り上げ", "紛失", "壊れ", "失った", "消え"]
```
**検証**: `python -c "from src.agents.erotic_integrity import TIMEOFDAY_LEVELS, ITEM_USE_KW; print(len(TIMEOFDAY_LEVELS))"` が成功

---

### ステップ8: `SceneTypeDetector` クラスの枠を作成

**対象**: [`src/agents/erotic_integrity.py`](../src/agents/erotic_integrity.py)
**挿入位置**: `ContinuityTracker` クラス定義の直前（行149の前に）
**コード断片**:
```python
class SceneTypeDetector:
    """テキストからシーン種別を検出するヘルパー。"""

    @staticmethod
    def detect(text: str) -> str:
        counts = {
            "combat": sum(text.count(kw) for kw in COMBAT_KEYWORDS),
            "conversation": sum(text.count(kw) for kw in CONVERSATION_KEYWORDS),
            "exploration": sum(text.count(kw) for kw in EXPLORATION_KEYWORDS),
            "travel": sum(text.count(kw) for kw in TRAVEL_KEYWORDS),
            "rest": sum(text.count(kw) for kw in REST_KEYWORDS),
            "monologue": sum(text.count(kw) for kw in MONOLOGUE_KEYWORDS),
        }
        # erotic は EroticIntegrityChecker 側で判定済みの前提
        if not counts or max(counts.values()) == 0:
            return "unknown"
        return max(counts, key=counts.get)

    @staticmethod
    def detect_all(text: str) -> Dict[str, int]:
        return {
            "combat": sum(text.count(kw) for kw in COMBAT_KEYWORDS),
            "conversation": sum(text.count(kw) for kw in CONVERSATION_KEYWORDS),
            "exploration": sum(text.count(kw) for kw in EXPLORATION_KEYWORDS),
            "travel": sum(text.count(kw) for kw in TRAVEL_KEYWORDS),
            "rest": sum(text.count(kw) for kw in REST_KEYWORDS),
            "monologue": sum(text.count(kw) for kw in MONOLOGUE_KEYWORDS),
        }
```
**検証**: `python -c "from src.agents.erotic_integrity import SceneTypeDetector; print(SceneTypeDetector.detect('剣で斬る 攻撃 防ぐ'))"` が `combat` を出力

---

### ステップ9: `SceneStateSnapshot` データクラスの追加

**挿入位置**: `ContinuityReport` データクラスの直後
**コード断片**:
```python
@dataclass
class SceneStateSnapshot:
    """1話終了時点の汎用シーン状態スナップショット。エピソード1つの状態を完結に保持する。"""
    character_name: str
    episode_num: int
    scene_type: str = "unknown"            # 主シーン種別
    injury_level: str = "uninjured"        # 改善案1
    injury部位: str = ""                    # 改善案1: 負傷部位（自由テキスト）
    attitude_level: str = "neutral"         # 改善案2
    exploration_found: List[str] = None    # 改善案3: 発見済み手がかり
    last_location: str = "unknown"         # 改善案4: 最終現在地
    travel_destination: str = ""           # 改善案4: 目的地
    travel_means: str = ""                 # 改善案4: 移動手段
    rest_count: int = 0                    # 改善案5
    sleep_hours: float = 0.0               # 改善案5
    monologue_person: str = ""             # 改善案6: first/third
    monologue_tone: str = ""               # 改善案6
    foreshadow_ids: List[str] = None       # 改善案7: 張られた伏線ID
    foreshadow_paid: List[str] = None      # 改善案7: 回収済み伏線ID
    time_of_day: str = ""                  # 改善案8
    items_held: List[str] = None           # 改善案9: 所持アイテム集合
    custom_flags: Dict[str, str] = None

    def __post_init__(self):
        if self.exploration_found is None:
            self.exploration_found = []
        if self.foreshadow_ids is None:
            self.foreshadow_ids = []
        if self.foreshadow_paid is None:
            self.foreshadow_paid = []
        if self.items_held is None:
            self.items_held = []
        if self.custom_flags is None:
            self.custom_flags = {}
```
**検証**: `python -c "from src.agents.erotic_integrity import SceneStateSnapshot; s=SceneStateSnapshot('a',1); print(s.items_held)"` が `[]` を出力

---

### ステップ10: `SceneContinuityReport` データクラスの追加

**コード断片**:
```python
@dataclass
class SceneContinuityReport:
    """汎用シーン種別の話間整合性チェック結果。"""
    is_consistent: bool
    issues: List[str]
    checked_dimensions: List[str]
    character_name: str
    episode_num: int
    scene_type: str
```
**検証**: import 成功

---

### ステップ11: `SceneContinuityTracker` クラスの枠（SQLite 初期化のみ）

**挿入位置**: `SceneTypeDetector` の直後（`ContinuityTracker` の前）
**コード断片**:
```python
class SceneContinuityTracker:
    """官能以外のシーン種別の話間整合性を追跡する。SQLiteで永続化。"""

    def __init__(self, db_path: str = "kaku_hegemony_v2.db"):
        self.db_path = db_path
        self._snapshots: Dict[int, Dict[str, SceneStateSnapshot]] = {}
        self._init_db()

    def _init_db(self):
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scene_continuity_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_name TEXT,
                    episode_num INTEGER,
                    scene_type TEXT,
                    injury_level TEXT,
                    injury_part TEXT,
                    attitude_level TEXT,
                    exploration_found TEXT,
                    last_location TEXT,
                    travel_destination TEXT,
                    travel_means TEXT,
                    rest_count INTEGER,
                    sleep_hours REAL,
                    monologue_person TEXT,
                    monologue_tone TEXT,
                    foreshadow_ids TEXT,
                    foreshadow_paid TEXT,
                    time_of_day TEXT,
                    items_held TEXT,
                    custom_flags TEXT,
                    UNIQUE(character_name, episode_num)
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("Failed to initialize SQLite for SceneContinuityTracker: %s. Using memory only.", e)
```
**検証**: `python -c "from src.agents.erotic_integrity import SceneContinuityTracker; SceneContinuityTracker(':memory:')"` が成功

---

### ステップ12: `SceneContinuityTracker.save_snapshot` メソッドの追加

**コード断片**:
```python
    def save_snapshot(self, snapshot: SceneStateSnapshot) -> None:
        ep = snapshot.episode_num
        if ep not in self._snapshots:
            self._snapshots[ep] = {}
        self._snapshots[ep][snapshot.character_name] = snapshot
        import sqlite3, json
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO scene_continuity_snapshots
                (character_name, episode_num, scene_type, injury_level, injury_part,
                 attitude_level, exploration_found, last_location, travel_destination,
                 travel_means, rest_count, sleep_hours, monologue_person, monologue_tone,
                 foreshadow_ids, foreshadow_paid, time_of_day, items_held, custom_flags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot.character_name, snapshot.episode_num, snapshot.scene_type,
                snapshot.injury_level, snapshot.injury部位,
                snapshot.attitude_level, json.dumps(snapshot.exploration_found, ensure_ascii=False),
                snapshot.last_location, snapshot.travel_destination, snapshot.travel_means,
                snapshot.rest_count, snapshot.sleep_hours, snapshot.monologue_person,
                snapshot.monologue_tone, json.dumps(snapshot.foreshadow_ids, ensure_ascii=False),
                json.dumps(snapshot.foreshadow_paid, ensure_ascii=False), snapshot.time_of_day,
                json.dumps(snapshot.items_held, ensure_ascii=False),
                json.dumps(snapshot.custom_flags, ensure_ascii=False),
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("Failed to save scene snapshot: %s", e)
```
**検証**: `python -c "from src.agents.erotic_integrity import *; t=SceneContinuityTracker(':memory:'); t.save_snapshot(SceneStateSnapshot('a',1))"` が成功

---

### ステップ13: `SceneContinuityTracker.get_snapshot` メソッドの追加

**コード断片**:
```python
    def get_snapshot(self, episode_num: int, character_name: str) -> Optional[SceneStateSnapshot]:
        if episode_num in self._snapshots and character_name in self._snapshots[episode_num]:
            return self._snapshots[episode_num][character_name]
        import sqlite3, json
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT scene_type, injury_level, injury_part, attitude_level, exploration_found,
                       last_location, travel_destination, travel_means, rest_count, sleep_hours,
                       monologue_person, monologue_tone, foreshadow_ids, foreshadow_paid,
                       time_of_day, items_held, custom_flags
                FROM scene_continuity_snapshots
                WHERE episode_num = ? AND character_name = ?
            """, (episode_num, character_name))
            row = cursor.fetchone()
            conn.close()
            if row:
                def _loads(s, default):
                    try:
                        return json.loads(s) if s else default
                    except Exception:
                        return default
                snap = SceneStateSnapshot(
                    character_name=character_name, episode_num=episode_num,
                    scene_type=row[0], injury_level=row[1], injury部位=row[2],
                    attitude_level=row[3], exploration_found=_loads(row[4], []),
                    last_location=row[5], travel_destination=row[6], travel_means=row[7],
                    rest_count=row[8], sleep_hours=row[9], monologue_person=row[10],
                    monologue_tone=row[11], foreshadow_ids=_loads(row[12], []),
                    foreshadow_paid=_loads(row[13], []), time_of_day=row[14],
                    items_held=_loads(row[15], []), custom_flags=_loads(row[16], {}),
                )
                self._snapshots.setdefault(episode_num, {})[character_name] = snap
                return snap
        except Exception as e:
            logger.warning("Failed to load scene snapshot: %s", e)
        return None
```
**検証**: `python -c "from src.agents.erotic_integrity import *; t=SceneContinuityTracker(':memory:'); t.save_snapshot(SceneStateSnapshot('a',1, items_held=['剣'])); print(t.get_snapshot(1,'a').items_held)"` が `['剣']` を出力

---

### ステップ14: `get_previous_snapshot` メソッドの追加

**コード断片**:
```python
    def get_previous_snapshot(self, current_ep: int, character_name: str) -> Optional[SceneStateSnapshot]:
        return self.get_snapshot(current_ep - 1, character_name)
```
**検証**: import 成功

---

### ステップ15: 改善案1 — 負傷検出ヘルパ `_detect_injury`

**コード断片**:
```python
    @staticmethod
    def _detect_injury(text: str) -> str:
        critical = sum(text.count(kw) for kw in INJURY_CRITICAL_KW)
        severe = sum(text.count(kw) for kw in INJURY_SEVERE_KW)
        moderate = sum(text.count(kw) for kw in INJURY_MODERATE_KW)
        minor = sum(text.count(kw) for kw in INJURY_MINOR_KW)
        scores = {"critical": critical, "severe": severe, "moderate": moderate, "minor": minor}
        max_lvl = max(scores, key=scores.get)
        if scores[max_lvl] >= 1:
            return max_lvl
        return "uninjured"
```
**検証**: `python -c "from src.agents.erotic_integrity import SceneStateSnapshot; from src.agents.erotic_integrity import SceneContinuityTracker as T; print(T._detect_injury('瀕死の重傷だった'))"` が `critical` を出力

---

### ステップ16: 改善案1 — `check_injury_continuity` メソッド

**コード断片**:
```python
    def check_injury_continuity(self, current_ep: int, character_name: str,
                                 current_text: str) -> List[str]:
        issues = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None:
            return issues
        m = {"uninjured": 0, "minor": 1, "moderate": 2, "severe": 3, "critical": 4}
        curr = self._detect_injury(current_text[:max(int(len(current_text)*0.3), 200)])
        if m.get(prev.injury_level, 0) >= 3 and m.get(curr, 0) <= 1:
            opening = current_text[:500]
            healed = any(kw in opening for kw in INJURY_HEAL_KW)
            slept = any(kw in opening for kw in REST_SLEEP_KW + ["数日", "数週間", "一週間", "半月", "一月"])
            if not (healed or slept):
                issues.append(
                    f"[負傷継承矛盾] {character_name}: 前話末={prev.injury_level} → "
                    f"今話冒頭={curr} ですが、治療・時間経過の描写がありません"
                )
        return issues
```
**検証**: テストは後ほど追加（一時的にメソッド存在のみ確認）

---

### ステップ17: 改善案2 — 態度検出ヘルパ `_detect_attitude`

**コード断片**:
```python
    @staticmethod
    def _detect_attitude(text: str) -> str:
        scores = {
            "hostile": sum(text.count(kw) for kw in ATTITUDE_HOSTILE_KW),
            "cold": sum(text.count(kw) for kw in ATTITUDE_COLD_KW),
            "friendly": sum(text.count(kw) for kw in ATTITUDE_FRIENDLY_KW),
            "devoted": sum(text.count(kw) for kw in ATTITUDE_DEVOTED_KW),
        }
        m = max(scores, key=scores.get)
        if scores[m] >= 2:
            return m
        return "neutral"
```
**検証**: `print(T._detect_attitude('憎しみ 敵対 殺意 睨み'))` → `hostile`

---

### ステップ18: 改善案2 — `check_attitude_jump` メソッド

**コード断片**:
```python
    def check_attitude_jump(self, current_ep: int, character_name: str,
                             current_text: str) -> List[str]:
        issues = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None:
            return issues
        m = {"hostile": 0, "cold": 1, "neutral": 2, "friendly": 3, "devoted": 4}
        curr = self._detect_attitude(current_text[:max(int(len(current_text)*0.3), 200)])
        if abs(m.get(prev.attitude_level, 2) - m.get(curr, 2)) >= 3:
            opening = current_text[:800]
            reconciled = any(kw in opening for kw in ATTITUDE_RECONCILE_KW)
            if not reconciled:
                issues.append(
                    f"[態度急転] {character_name}: {prev.attitude_level}→{curr} "
                    f"（3段階以上）。和解・事件のトリガー描写が必要です"
                )
        return issues
```

---

### ステップ19: 改善案3 — 探索発見リスト抽出 `_extract_exploration_found`

**コード断片**:
```python
    @staticmethod
    def _extract_exploration_found(text: str) -> List[str]:
        found = []
        for kw in EXPLORATION_FOUND_KW:
            pos = 0
            while True:
                pos = text.find(kw, pos)
                if pos == -1:
                    break
                window = text[pos:pos+60]
                # 句点までを発見対象名として簡易取得
                end = max(
                    window.find("。") if window.find("。") != -1 else 999,
                    window.find("、") if window.find("、") != -1 else 999,
                )
                fragment = window[:min(end, 40)] if end != 999 else window[:40]
                found.append(f"{kw}:{fragment}")
                pos += len(kw)
                if len(found) >= 5:
                    return found
        return found
```

---

### ステップ20: 改善案3 — `check_exploration_continuity` メソッド

**コード断片**:
```python
    def check_exploration_continuity(self, current_ep: int, character_name: str,
                                      current_text: str) -> List[str]:
        issues = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None:
            return issues
        unexplored_now = any(kw in current_text[:500] for kw in EXPLORATION_UNEXPLORED_KW)
        prior_known = bool(prev.exploration_found)
        if unexplored_now and prior_known:
            issues.append(
                f"[探索矛盾] {character_name}: 既に発見済みの手がかりがある一方で、"
                f"今話冒頭で『未踏』表現が検出されました"
            )
        return issues
```

---

### ステップ21: 改善案4 — `_detect_travel_intent` ヘルパ

**コード断片**:
```python
    @staticmethod
    def _detect_travel_intent(text: str) -> Tuple[str, str, str]:
        opening = text[:500]
        dest = ""
        means = ""
        for kw in TRAVEL_DEPART_KW:
            idx = opening.find(kw)
            if idx != -1:
                window = opening[idx:idx+60]
                end = window.find("へ") if window.find("へ") != -1 else window.find("に")
                if end != -1 and end > len(kw):
                    dest = window[len(kw):end].strip(" はが、。にへ")
                break
        for kw in TRAVEL_MEANS_KW:
            if kw in opening:
                means = kw
                break
        current_loc = ContinuityTracker._detect_location(opening)
        return current_loc, dest, means
```

---

### ステップ22: 改善案4 — `check_travel_continuity` メソッド

**コード断片**:
```python
    def check_travel_continuity(self, current_ep: int, character_name: str,
                                 current_text: str) -> List[str]:
        issues = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None:
            return issues
        opening = current_text[:500]
        curr_loc, dest, _ = self._detect_travel_intent(current_text)
        if prev.travel_destination and prev.last_location != "unknown":
            # 前話で目的地宣言があった場合、今話冒頭はその目的地に到着しているべき
            arrived = any(kw in opening for kw in TRAVEL_ARRIVE_KW)
            transition = any(kw in opening for kw in LOCATION_TRANSITION_KW)
            if curr_loc != "unknown" and prev.travel_destination and not (arrived or transition):
                # 目的地=前話宣告地名のみ厳格チェックは省き、到着または移動描写があればOK
                pass
            if not (arrived or transition):
                issues.append(
                    f"[移動接続矛盾] {character_name}: 前話目的地=『{prev.travel_destination}』 "
                    f"今話現在地=『{curr_loc}』ですが、到着または移動の描写がありません"
                )
        return issues
```

---

### ステップ23: 改善案5 — `_detect_rest` ヘルパ

**コード断片**:
```python
    @staticmethod
    def _detect_rest(text: str) -> Tuple[int, float]:
        sleep_count = sum(text.count(kw) for kw in REST_SLEEP_KW)
        duration = 0.0
        for kw, hrs in [("一睡", 1.0), ("数時間", 3.0), ("一晩", 7.0),
                         ("二晩", 14.0), ("徹夜", 0.0), ("短い仮眠", 1.0)]:
            if kw in text:
                duration = max(duration, hrs)
        return sleep_count, duration
```

---

### ステップ24: 改善案5 — `check_rest_recovery` メソッド

**コード断片**:
```python
    def check_rest_recovery(self, current_ep: int, character_name: str,
                             current_text: str) -> List[str]:
        issues = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None:
            return issues
        opening = current_text[:500]
        exhausted_before = any(kw in opening for kw in REST_EXHAUSTION_BEFORE_KW)
        sleep_count, _ = self._detect_rest(current_text[:1000])
        # 前話連続行動で疲弊→今話開幕は健康、かつ休息描写なし
        prev_stamina = self.get_previous_snapshot(current_ep, character_name)
        prev_tired = prev_stamina and getattr(prev_stamina, "rest_count", 0) == 0
        if exhausted_before and prev_tired and sleep_count == 0:
            rest_kw = any(kw in opening for kw in REST_SLEEP_KW + ["休む", "休息"])
            if not rest_kw:
                issues.append(
                    f"[休息回復矛盾] {character_name}: 疲労描写があるのに休息・睡眠の記述がありません"
                )
        return issues
```
**注意**: このメソッドは prev 自体に `rest_count` 属性が存在しない場合があるため、`getattr` で安全に取得します。`SceneStateSnapshot` には `rest_count` があるため問題ありません。

---

### ステップ25: 改善案6 — `_detect_monologue_person` ヘルパ

**コード断片**:
```python
    @staticmethod
    def _detect_monologue_person(text: str) -> str:
        first = sum(text.count(kw) for kw in MONOLOGUE_PERSON_FIRST_KW)
        third = sum(text.count(kw) for kw in MONOLOGUE_PERSON_THIRD_KW)
        if first > third + 1:
            return "first"
        if third > first + 1:
            return "third"
        return ""
```

---

### ステップ26: 改善案6 — `check_monologue_view_continuity` メソッド

**コード断片**:
```python
    def check_monologue_view_continuity(self, current_ep: int, character_name: str,
                                          current_text: str) -> List[str]:
        issues = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None or not prev.monologue_person:
            return issues
        curr = self._detect_monologue_person(current_text[:500])
        if curr and prev.monologue_person != curr:
            shifted = any(kw in current_text[:800] for kw in MONOLOGUE_SHIFT_KW)
            if not shifted:
                issues.append(
                    f"[視点切替矛盾] {character_name}: 前話視点={prev.monologue_person} → "
                    f"今話={curr}。視点切り替えの合図（『場面は変』等）がありません"
                )
        return issues
```

---

### ステップ27: 改善案7 — 伏線ID抽出 `_extract_foreshadow_ids`

**コード断片**:
```python
    @staticmethod
    def _extract_foreshadow_ids(text: str) -> List[str]:
        ids = []
        pos = 0
        for kw in FORESHADOW_PLANT_KW:
            idx = text.find(kw)
            if idx != -1:
                # 簡易: キーワード直後30字を伏線ラベルにする
                ids.append(f"{kw}:{text[idx:idx+30]}")
        return ids[:5]

    @staticmethod
    def _extract_foreshadow_paid(text: str) -> List[str]:
        paid = []
        for kw in FORESHADOW_PAYOFF_KW:
            idx = text.find(kw)
            if idx != -1:
                paid.append(f"{kw}:{text[idx:idx+30]}")
        return paid[:5]
```

---

### ステップ28: 改善案7 — `check_foreshadow_abandonment` メソッド

**コード断片**:
```python
    def check_foreshadow_abandonment(self, current_ep: int, character_name: str,
                                       current_text: str) -> List[str]:
        issues = []
        # 過去話から集計し、FORESHADOW_IGNORE_THRESHOLD 話以上未回収の伏線を警告
        for lookback in range(1, FORESHADOW_IGNORE_THRESHOLD + 2):
            prev_ep = current_ep - lookback
            if prev_ep <= 0:
                break
            snap = self.get_snapshot(prev_ep, character_name)
            if snap is None:
                continue
            unpaid = [f for f in snap.foreshadow_ids if f not in snap.foreshadow_paid]
            if not unpaid:
                continue
            # 現在話までに回収されていないか確認
            for paid_label in self._extract_foreshadow_paid(current_text):
                unpaid = [f for f in unpaid if f[:6] not in paid_label]
            # 中間話での回収をチェック
            for mid_ep in range(prev_ep + 1, current_ep):
                mid_snap = self.get_snapshot(mid_ep, character_name)
                if mid_snap is None:
                    continue
                for paid_label in mid_snap.foreshadow_paid:
                    unpaid = [f for f in unpaid if f[:6] not in paid_label]
            if unpaid and lookback >= FORESHADOW_IGNORE_THRESHOLD:
                issues.append(
                    f"[伏線放置] {character_name}: episode {prev_ep} の伏線 "
                    f"{unpaid[:2]} が {lookback} 話以上未回収です"
                )
        return issues
```

---

### ステップ29: 改善案8 — `_detect_time_of_day` ヘルパ

**コード断片**:
```python
    @staticmethod
    def _detect_time_of_day(text: str) -> str:
        scores = {
            "morning": sum(text.count(kw) for kw in TIMEOFDAY_MORNING_KW),
            "daytime": sum(text.count(kw) for kw in TIMEOFDAY_DAYTIME_KW),
            "evening": sum(text.count(kw) for kw in TIMEOFDAY_EVENING_KW),
            "night": sum(text.count(kw) for kw in TIMEOFDAY_NIGHT_KW),
            "midnight": sum(text.count(kw) for kw in TIMEOFDAY_MIDNIGHT_KW),
        }
        m = max(scores, key=scores.get)
        if scores[m] >= 1:
            return m
        return ""
```

---

### ステップ30: 改善案8 — `check_time_of_day_progression` メソッド

**コード断片**:
```python
    def check_time_of_day_progression(self, current_ep: int, character_name: str,
                                        current_text: str) -> List[str]:
        issues = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None or not prev.time_of_day:
            return issues
        order = ["morning", "daytime", "evening", "night", "midnight"]
        prev_idx = order.index(prev.time_of_day) if prev.time_of_day in order else -1
        curr = self._detect_time_of_day(current_text[:500])
        if not curr or prev_idx == -1:
            return issues
        curr_idx = order.index(curr)
        # 前進か、深夜→朝への折り返し（翌日）は許容
        wrap_around = (prev_idx == 4 and curr_idx == 0)
        has_new_day = any(kw in current_text[:300]
                          for kw in ["翌朝", "翌日", "翌", "次の日", "日が昇", "夜が明け"])
        if curr_idx < prev_idx and not (wrap_around and has_new_day):
            issues.append(
                f"[時間帯退行] {character_name}: 前話末={prev.time_of_day} → "
                f"今話冒頭={curr}。時間が戻る流れには『翌日』等の描写が必要です"
            )
        return issues
```

---

### ステップ31: 改善案9 — アイテム抽出ヘルパ `_extract_items`

**コード断片**:
```python
    @staticmethod
    def _detect_item_acquire(text: str) -> Tuple[List[str], List[str]]:
        acquired, used = [], []
        for kw in ITEM_ACQUIRE_KW:
            idx = text.find(kw)
            if idx != -1:
                window = text[max(0, idx-20):idx]
                acquired.append(f"{window[-20:]}{kw}")
        for kw in ITEM_USE_KW:
            idx = text.find(kw)
            if idx != -1:
                window = text[max(0, idx-20):idx]
                used.append(f"{window[-20:]}{kw}")
        return acquired[:5], used[:5]
```

---

### ステップ32: 改善案9 — `check_item_ownership_continuity` メソッド

**コード断片**:
```python
    def check_item_ownership_continuity(self, current_ep: int, character_name: str,
                                          current_text: str) -> List[str]:
        issues = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None:
            return issues
        acquired_now, used_now = self._detect_item_acquire(current_text)
        prev_held = set(prev.items_held)
        # 前話所持していないアイテムが今話冒頭で使用されている
        for used_token in used_now:
            if used_token not in prev_held and used_token not in acquired_now:
                issues.append(
                    f"[アイテム所持矛盾] {character_name}: 『{used_token[:30]}...』が"
                    f"使用されていますが、入手済みリストにありません"
                )
        return issues
```

---

### ステップ33: `extract_scene_snapshot` 統合ヘルパ

**コード断片**:
```python
    def extract_scene_snapshot(self, character_name: str, episode_num: int,
                                scene_text: str) -> SceneStateSnapshot:
        scene_type = SceneTypeDetector.detect(scene_text)
        injury = self._detect_injury(scene_text)
        attitude = self._detect_attitude(scene_text)
        exploration = self._extract_exploration_found(scene_text)
        last_loc, dest, means = self._detect_travel_intent(scene_text)
        sleep_count, sleep_hours = self._detect_rest(scene_text)
        mono_person = self._detect_monologue_person(scene_text)
        fore_ids = self._extract_foreshadow_ids(scene_text)
        fore_paid = self._extract_foreshadow_paid(scene_text)
        tod = self._detect_time_of_day(scene_text)
        acquired, _ = self._detect_item_acquire(scene_text)
        return SceneStateSnapshot(
            character_name=character_name, episode_num=episode_num,
            scene_type=scene_type, injury_level=injury, injury部位="",
            attitude_level=attitude, exploration_found=exploration,
            last_location=last_loc, travel_destination=dest, travel_means=means,
            rest_count=sleep_count, sleep_hours=sleep_hours,
            monologue_person=mono_person, monologue_tone="",
            foreshadow_ids=fore_ids, foreshadow_paid=fore_paid,
            time_of_day=tod, items_held=acquired,
        )
```

---

### ステップ34: `check_all_scene_continuity` 統合メソッド

**コード断片**:
```python
    def check_all_scene_continuity(self, current_ep: int, character_name: str,
                                     current_text: str) -> SceneContinuityReport:
        issues: List[str] = []
        checked = []
        issues += self.check_injury_continuity(current_ep, character_name, current_text); checked.append("injury")
        issues += self.check_attitude_jump(current_ep, character_name, current_text); checked.append("attitude")
        issues += self.check_exploration_continuity(current_ep, character_name, current_text); checked.append("exploration")
        issues += self.check_travel_continuity(current_ep, character_name, current_text); checked.append("travel")
        issues += self.check_rest_recovery(current_ep, character_name, current_text); checked.append("rest")
        issues += self.check_monologue_view_continuity(current_ep, character_name, current_text); checked.append("monologue")
        issues += self.check_foreshadow_abandonment(current_ep, character_name, current_text); checked.append("foreshadow")
        issues += self.check_time_of_day_progression(current_ep, character_name, current_text); checked.append("time_of_day")
        issues += self.check_item_ownership_continuity(current_ep, character_name, current_text); checked.append("items")
        return SceneContinuityReport(
            is_consistent=len(issues) == 0, issues=issues, checked_dimensions=checked,
            character_name=character_name, episode_num=current_ep,
            scene_type=SceneTypeDetector.detect(current_text),
        )
```

---

### ステップ35: `EroticIntegrityChecker.__init__` に `scene_continuity_tracker` 追加

**対象**: [`src/agents/erotic_integrity.py`](../src/agents/erotic_integrity.py:976)
**コード断片**: `self.continuity_tracker = ContinuityTracker(db_path=db_path)` の次行に追加
```python
        self.scene_continuity_tracker = SceneContinuityTracker(db_path=db_path)
```

---

### ステップ36: `check_continuity` からの汎用トラッカー呼び出し追加

**対象**: [`src/agents/erotic_integrity.py`](../src/agents/erotic_integrity.py:1184)
**コード断片**: `check_continuity` の return 直前に汎用レポートを取得して iss集中に追加
```python
        # 汎用シーン種別 continuity（官能以外のシーンも対象）
        for char in chars_to_check:
            scene_report = self.scene_continuity_tracker.check_all_scene_continuity(
                current_ep, char, current_text
            )
            if not scene_report.is_consistent:
                all_issues.extend(scene_report.issues)
                checked.append("scene_" + scene_report.scene_type)
        # 既存の return
```
**注意**: `check_continuity` の戻り値は [`ContinuityReport`](../src/agents/erotic_integrity.py:141) なので、`scene_report` の iss集中だけを統合し、シーン種別情報は `checked` に文字列で追加するだけに留めます（型崩壊を防ぐ）。

---

### ステップ37: `finalize_episode` で汎用スナップショットも保存

**対象**: [`src/agents/erotic_integrity.py`](../src/agents/erotic_integrity.py:1252)
**コード断片**: ペア全体保存ブロックの直前に追加
```python
        # 汎用シーン種別スナップショットも保存
        for char in chars_to_save:
            scene_snap = self.scene_continuity_tracker.extract_scene_snapshot(
                char, episode_num, scene_text
            )
            self.scene_continuity_tracker.save_snapshot(scene_snap)
```

---

### ステップ38: `check_all` に汎用レポートを統合

**対象**: [`src/agents/erotic_integrity.py`](../src/agents/erotic_integrity.py:1284)
**コード断片**: `continuity_report` が None でない場合に、そこから汎用 iss集中も抽出する
```python
        # 汎用シーン continuity の iss集中を continuity_report に混入させないが、
        # check_continuity 側で既に統合済みのため、ここでは追加処理不要。
        # （一貫性を保つため、check_all 経由では汎用トラッカーの再起呼び出しを避ける）
```
**注意**: 設計を保つため、check_all から再起は呼ばず、check_continuity 内で完結させます。このステップは「設計注記モック」です。

---

### ステップ39: 既存テストが壊れていないか確認

**コマンド**:
```
python -m pytest tests/test_continuity_tracker.py -x -q
```
**期待**: 全グリーン。修正で既存挙動を変えていないことを確認。

---

### ステップ40: 新規テストファイルのヘッダ作成

**対象**: `tests/test_scene_continuity_tracker.py`（新規作成）
**コード断片**:
```python
import pytest
from src.agents.erotic_integrity import (
    SceneTypeDetector, SceneStateSnapshot, SceneContinuityTracker,
    SceneContinuityReport, EroticIntegrityChecker,
    SceneContinuityTracker as SCT,
)

@pytest.fixture
def temp_db(tmp_path):
    return str(tmp_path / "test_scene.db")
```

---

### ステップ41: `SceneTypeDetector` のテスト

**コード断片**:
```python
class TestSceneTypeDetector:
    def test_combat(self):
        assert SceneTypeDetector.detect("剣で斬る 攻撃 防ぐ") == "combat"

    def test_conversation(self):
        assert SceneTypeDetector.detect("彼は言った 答えた 聞いた") == "conversation"

    def test_unknown(self):
        assert SceneTypeDetector.detect("静かな風景") == "unknown"
```

---

### ステップ42: 負傷継承のテスト（改善案1）

**コード断片**:
```python
class TestInjuryContinuity:
    def test_severe_to_uninjured_without_heal(self, temp_db):
        t = SceneContinuityTracker(db_path=temp_db)
        t.save_snapshot(SceneStateSnapshot("花", 1, injury_level="critical"))
        text = "花は元気に走り出した。剣を振るう。" * 5
        issues = t.check_injury_continuity(2, "花", text)
        assert any("負傷継承矛盾" in i for i in issues)
```

---

### ステップ43: 態度急転のテスト（改善案2）

**コード断片**:
```python
class TestAttitudeJump:
    def test_hostile_to_devoted_no_reconcile(self, temp_db):
        t = SceneContinuityTracker(db_path=temp_db)
        t.save_snapshot(SceneStateSnapshot("花", 1, attitude_level="hostile"))
        text = "献身 尽くす 命を懸け 捧げ 殉じ 忠誠 愛しく" + "。" * 50
        issues = t.check_attitude_jump(2, "花", text)
        assert any("態度急転" in i for i in issues)
```

---

### ステップ44: 探索・移動のテスト（改善案3・4）

**コード断片**:
```python
class TestExplorationAndTravel:
    def test_exploration_inconsistency(self, temp_db):
        t = SceneContinuityTracker(db_path=temp_db)
        t.save_snapshot(SceneStateSnapshot("花", 1, exploration_found=["発見:剣"]))
        text = "花は未知の 未踏の 誰も知らない 前人未到の地に立った。" * 5
        issues = t.check_exploration_continuity(2, "花", text)
        assert any("探索矛盾" in i for i in issues)

    def test_travel_no_arrival(self, temp_db):
        t = SceneContinuityTracker(db_path=temp_db)
        t.save_snapshot(SceneStateSnapshot("花", 1, last_location="indoor",
                                           travel_destination="塔"))
        text = "花は森の中を歩いていた。鳥の声を聞いた。" * 5
        issues = t.check_travel_continuity(2, "花", text)
        assert any("移動接続矛盾" in i for i in issues)
```

---

### ステップ45: 休息・独白のテスト（改善案5・6）

**コード断片**:
```python
class TestRestAndMonologue:
    def test_monologue_view_switch_no_marker(self, temp_db):
        t = SceneContinuityTracker(db_path=temp_db)
        t.save_snapshot(SceneStateSnapshot("花", 1, monologue_person="third"))
        text = "私 僕 俺 私 私 私 私" * 10  # first person 優勢
        issues = t.check_monologue_view_continuity(2, "花", text)
        assert any("視点切替矛盾" in i for i in issues)
```

---

### ステップ46: 伏線・時間帯のテスト（改善案7・8）

**コード断片**:
```python
class TestForeshadowAndTime:
    def test_foreshadow_abandonment(self, temp_db):
        t = SceneContinuityTracker(db_path=temp_db)
        t.save_snapshot(SceneStateSnapshot("花", 1, foreshadow_ids=["伏線:謎の鍵"]))
        t.save_snapshot(SceneStateSnapshot("花", 2))
        t.save_snapshot(SceneStateSnapshot("花", 3))
        text = "花は何かを食べた。" * 30
        issues = t.check_foreshadow_abandonment(4, "花", text)
        assert any("伏線放置" in i for i in issues)

    def test_time_of_day_regression(self, temp_db):
        t = SceneContinuityTracker(db_path=temp_db)
        t.save_snapshot(SceneStateSnapshot("花", 1, time_of_day="night"))
        text = "花は昼の日差しの中を歩いた。午後の日差し。" * 10
        issues = t.check_time_of_day_progression(2, "花", text)
        assert any("時間帯退行" in i for i in issues)
```

---

### ステップ47: アイテム所持のテスト（改善案9）

**コード断片**:
```python
class TestItemOwnership:
    def test_undefined_item_use(self, temp_db):
        t = SceneContinuityTracker(db_path=temp_db)
        t.save_snapshot(SceneStateSnapshot("花", 1, items_held=["剣"]))
        text = "花は弓を構え 投げナイフを取り出し 魔法を発動し" * 5
        issues = t.check_item_ownership_continuity(2, "花", text)
        assert any("アイテム所持矛盾" in i for i in issues)
```

---

### ステップ48: 統合テストと全実行

**コード断片**:
```python
class TestIntegrationScene:
    def test_check_all_with_scene_continuity(self, temp_db):
        checker = EroticIntegrityChecker(db_path=temp_db)
        ep1 = "花は剣で戦い攻撃した。防御し避けた。" * 5 + " 瀕死の重傷だった。" * 5
        checker.finalize_episode("花", 1, ep1)
        ep2 = "花は元気に走り出した。剣を振るう攻撃防御。" * 10
        _, _, _, cont = checker.check_all(ep2, current_ep=2, character_name="花",
                                          prev_text=ep1)
        assert cont is not None
        assert any("負傷継承矛盾" in i for i in cont.issues)
```
**コマンド**:
```
python -m pytest tests/test_scene_continuity_tracker.py tests/test_continuity_tracker.py -x -v
```
**期待**: 全テストグリーン。

---

## 完了条件

- [ ] 全48ステップの実装完了
- [ ] `python -m pytest tests/test_continuity_tracker.py tests/test_scene_continuity_tracker.py` が全グリーン
- [ ] 既存 [`tests/test_continuity_tracker.py`](../tests/test_continuity_tracker.py:1) が壊れていない
- [ ] 設計ドキュメント（本ファイル）が最新状態を反映

## 後方互換性担保の要点

1. [`ContinuityTracker`](../src/agents/erotic_integrity.py:149) は**一切変更しない**（既存テスト保護）
2. [`check_continuity`](../src/agents/erotic_integrity.py:1184) の戻り値型 [`ContinuityReport`](../src/agents/erotic_integrity.py:141) は変更しない
3. [`check_all`](../src/agents/erotic_integrity.py:1284) の戻り値タプル長も変更しない
4. 新規 [`SceneContinuityTracker`](../src/agents/erotic_integrity.py) は独立クラスで既存ロジックに影響しない
5. `finalize_episode` は追加保存のみ行い、既存 [`ContinuityTracker`](../src/agents/erotic_integrity.py:149) 保存は維持
