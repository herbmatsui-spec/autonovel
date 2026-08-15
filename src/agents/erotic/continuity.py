"""
erotic/continuity.py - シーン・キャラクター連続性追跡

元 src/agents/erotic_integrity.py から抽出。
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, model_validator

from src.agents.erotic.vocabulary import (
    FORESHADOW_KEYWORDS,
    INTIMACY_BONDED_KW,
    INTIMACY_CLOSE_KW,
    INTIMACY_INTIMATE_KW,
    INTIMACY_STRANGER_KW,
    ITEM_KEYWORDS,
    LOCATION_INDOOR_KW,
    LOCATION_OUTDOOR_KW,
    LOCATION_TRANSITION_KW,
    PSYCH_ALLOWED_TRANSITIONS,
    PSYCH_ANXIOUS_KW,
    PSYCH_CONTENT_KW,
    PSYCH_DISTRESSED_KW,
    PSYCH_EUPHORIC_KW,
    PSYCH_STATES,
    STAMINA_ALLOWED_TRANSITIONS,
    STAMINA_ENERGETIC_KW,
    STAMINA_EXHAUSTED_KW,
    STAMINA_LEVELS,
    STAMINA_TIRED_KW,
    TIME_KEYWORDS,
)

logger = logging.getLogger(__name__)


class SceneStateSnapshot(BaseModel):
    """一般シーンの状態を保存するためのスナップショット。"""

    character_name: Optional[str] = None
    episode_num: Optional[int] = None
    scene_type: Optional[str] = None
    injury_level: str = "none"
    attitude: str = "neutral"
    discoveries: Optional[List[str]] = None
    travel_state: str = "stable"
    recovery_state: str = "full"
    perspective: str = "standard"
    foreshadowing_active: bool = False
    time_of_day: str = "unknown"
    items_held: Optional[List[str]] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _init_lists(self) -> "SceneStateSnapshot":
        if self.discoveries is None:
            self.discoveries = []
        if self.items_held is None:
            self.items_held = []
        return self


class SceneContinuityTracker:
    """一般シーンの一貫性を追跡する。SQLiteでの永続化に対応。"""

    def __init__(self, db_path: str = "storage/db/kaku_hegemony_v2.db"):
        self.db_path = db_path
        self._init_db()

    def save_snapshot(self, snapshot: SceneStateSnapshot) -> None:
        """シーン状態スナップショットを保存する。"""
        import json
        import sqlite3

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scene_snapshots
                (character_name, episode_num, scene_type, injury_level, attitude, discoveries,
                 travel_state, recovery_state, perspective, foreshadowing_active, time_of_day, items_held)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    snapshot.character_name,
                    snapshot.episode_num,
                    snapshot.scene_type,
                    snapshot.injury_level,
                    snapshot.attitude,
                    json.dumps(snapshot.discoveries),
                    snapshot.travel_state,
                    snapshot.recovery_state,
                    snapshot.perspective,
                    int(snapshot.foreshadowing_active),
                    snapshot.time_of_day,
                    json.dumps(snapshot.items_held),
                ),
            )

    def get_snapshot(self, episode_num: int, character_name: str) -> Optional[SceneStateSnapshot]:
        """指定エピソードのキャラクター状態を取得する。"""
        import json
        import sqlite3

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM scene_snapshots WHERE episode_num = ? AND character_name = ?",
                (episode_num, character_name),
            )
            row = cur.fetchone()
            if row:
                return SceneStateSnapshot(
                    character_name=row["character_name"],
                    episode_num=row["episode_num"],
                    scene_type=row["scene_type"],
                    injury_level=row["injury_level"],
                    attitude=row["attitude"],
                    discoveries=json.loads(row["discoveries"]),
                    travel_state=row["travel_state"],
                    recovery_state=row["recovery_state"],
                    perspective=row["perspective"],
                    foreshadowing_active=bool(row["foreshadowing_active"]),
                    time_of_day=row["time_of_day"],
                    items_held=json.loads(row["items_held"]),
                )
        return None

    def get_previous_snapshot(
        self, episode_num: int, character_name: str
    ) -> Optional[SceneStateSnapshot]:
        """直前のエピソードの状態を取得する。"""
        return self.get_snapshot(episode_num - 1, character_name)

    def _detect_injury_level(self, text: str) -> str:
        """テキストから負傷レベルを判定する。"""
        scores = {"none": 0, "light": 0, "moderate": 0, "severe": 0}

        # 判定用キーワード
        kw_map = {
            "severe": ["致命的", "瀕死", "意識不明", "血の海", "絶望的", "崩れ落ち", "深い傷", "絶望"],
            "moderate": ["深手", "激痛", "出血", "骨折", "動けない", "呻き"],
            "light": ["かすり傷", "打撲", "軽い", "痛み", "切り傷", "違和感"],
        }

        for level, keywords in kw_map.items():
            for kw in keywords:
                if kw in text:
                    scores[level] += 1

        # 最もスコアの高いものを選択（severe > moderate > light > none の優先順位）
        for level in ["severe", "moderate", "light"]:
            if scores[level] > 0:
                return level

        return "none"

    def check_injury_continuity(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        """戦闘負傷の一貫性をチェックする。"""
        issues = []
        prev_snapshot = self.get_previous_snapshot(current_ep, character_name)
        if not prev_snapshot:
            return issues

        current_level = self._detect_injury_level(current_text)
        prev_level = prev_snapshot.injury_level

        # 負傷レベルの遷移定義 (0: none, 1: light, 2: moderate, 3: severe)
        level_map = {"none": 0, "light": 1, "moderate": 2, "severe": 3}
        curr_val = level_map.get(current_level, 0)
        prev_val = level_map.get(prev_level, 0)

        # 矛盾チェック: 治療描写がないのに急激に回復している場合
        if curr_val < prev_val:
            # 回復キーワードのチェック
            recovery_keywords = ["治療", "手当て", "回復", "癒える", "包帯", "薬"]
            if not any(kw in current_text for kw in recovery_keywords):
                issues.append(
                    f"【整合性警告】{character_name}の負傷状態が {prev_level} から {current_level} へ不自然に回復しています（治療描写が見当たりません）。"
                )

        # 急激な悪化のチェック
        if curr_val - prev_val >= 2:
            issues.append(
                f"【状態急変】{character_name}の負傷が {prev_level} から {current_level} へ急激に悪化しています。描写に十分な説得力があるか確認してください。"
            )

        return issues

    def _detect_attitude(self, text: str) -> str:
        """テキストから会話態度を判定する。"""
        scores = {"friendly": 0, "neutral": 0, "hostile": 0, "tense": 0}

        # 判定用キーワード
        kw_map = {
            "hostile": ["拒絶", "怒り", "罵倒", "軽蔑", "激昂", "憎しみ", "突き放す", "敵意"],
            "tense": ["緊張", "気まずい", "沈黙", "警戒", "険しい", "冷ややか", "対立"],
            "friendly": ["親密", "信頼", "微笑み", "微笑んだ", "穏やか", "快諾", "共感", "温かい"],
        }

        for attitude, keywords in kw_map.items():
            for kw in keywords:
                if kw in text:
                    scores[attitude] += 1

        # 最もスコアの高いものを選択。同点なら hostile > tense > friendly > neutral の順で優先
        for attitude in ["hostile", "tense", "friendly"]:
            if scores[attitude] > 0:
                return attitude

        return "neutral"

    def check_attitude_continuity(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        """会話態度の一貫性をチェックする。"""
        issues = []
        prev_snapshot = self.get_previous_snapshot(current_ep, character_name)
        if not prev_snapshot:
            return issues

        current_attitude = self._detect_attitude(current_text)
        prev_attitude = prev_snapshot.attitude

        if (
            prev_attitude != "neutral"
            and current_attitude != "neutral"
            and prev_attitude != current_attitude
        ):
            # 態度が急激に変化した（例: hostile -> friendly）場合に警告
            issues.append(
                f"【整合性警告】{character_name}の態度が不自然に変化しています（{prev_attitude} → {current_attitude}）。心理描写やイベントによる変化があるか確認してください。"
            )

        return issues

    def _detect_discoveries(self, text: str) -> List[str]:
        """テキストから探索による発見事項を抽出する。"""
        discoveries = []
        discovery_keywords = [
            "発見した",
            "見つけた",
            "知った",
            "判明した",
            "気づいた",
            "明らかになった",
        ]

        sentences = text.split("。")
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and any(kw in sentence for kw in discovery_keywords):
                discoveries.append(sentence)

        return discoveries

    def check_discovery_continuity(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        """探索発見の一貫性をチェックする。"""
        issues = []
        prev_snapshot = self.get_previous_snapshot(current_ep, character_name)
        if not prev_snapshot:
            return issues

        current_discoveries = self._detect_discoveries(current_text)
        prev_discoveries = prev_snapshot.discoveries or []

        # 前回の発見事項が今回は出現していない場合は警告
        for prev_disc in prev_discoveries:
            # 簡易チェック: 内容が完全一致するか、または主要キーワードが含まれているか
            if prev_disc not in current_discoveries:
                disc_keywords = ["秘密", "真実", "弱点", "正体", "計画", "正体"]
                if any(kw in prev_disc for kw in disc_keywords):
                    issues.append(
                        f"【一貫性警告】{character_name}が前回発見した重要な情報「{prev_disc[:20]}...」に関する言及が不足しています。"
                    )

        return issues

    def _detect_travel_state(self, text: str) -> str:
        """テキストから移動状態を判定する。"""
        # 出発・移動中・到着の3状態を判定
        departure_kw = ["出発", "旅立", "去り", "去る", "立ち去る", "別れを告げ"]
        arriving_kw = ["到着", "辿り着", "辿りつ", "たどり着", "着いた", "目指す"]

        if any(kw in text for kw in departure_kw):
            return "departing"
        if any(kw in text for kw in arriving_kw):
            return "arriving"

        # 既定値
        return "staying"

    def check_travel_continuity(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        """移動接続の一貫性をチェックする。"""
        issues = []
        prev_snapshot = self.get_previous_snapshot(current_ep, character_name)
        if not prev_snapshot:
            return issues

        prev_state = prev_snapshot.travel_state
        current_state = self._detect_travel_state(current_text)

        # 前回「出発」で本次「滞在」の場合、到着描写があったかチェック
        if prev_state == "departing" and current_state == "staying":
            arriving_kw = ["到着", "辿り着", "着いた", "たどり着", "辿りつ"]
            if not any(kw in current_text for kw in arriving_kw):
                issues.append(
                    f"【移動断絶】{character_name}が前回出発したにもかかわらず、到着の描写がありません。途中経路か到着シーンを追加してください。"
                )

        # 前回「到着」で本次「出発」といきなり逆戻る場合、滞在描写があったか
        elif prev_state == "arriving" and current_state == "departing":
            staying_kw = ["滞在", "留ま", "過ごす", "とどまる", "宿", "宿屋", "野営"]
            if not any(kw in current_text for kw in staying_kw):
                issues.append(
                    f"【移動断絶】{character_name}が前回到着した直後にまた出発しています。間に滞在・休息描写を追加してください。"
                )

        return issues

    def _detect_monologue_perspective(self, text: str) -> str:
        """テキストから独白の視点を判定する。"""
        # 一人称 / 三人称 / 視点混在
        first_person_kw = ["私は", "僕は", "俺は", "私の中", "僕の", "俺の"]

        if any(kw in text for kw in first_person_kw):
            return "first_person"

        # 三人称的な描写（名前で呼ぶ、客観的な視点）
        # ここでは簡易的に一人称でなければ三人称とする
        return "third_person"

    def check_perspective_continuity(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        """独白視点の一貫性をチェックする。"""
        issues = []
        prev_snapshot = self.get_previous_snapshot(current_ep, character_name)
        if not prev_snapshot:
            return issues

        prev_perspective = prev_snapshot.perspective
        current_perspective = self._detect_monologue_perspective(current_text)

        if prev_perspective and current_perspective != prev_perspective:
            issues.append(
                f"【視点警告】{character_name}の視点が前回 {prev_perspective} でしたが、今回は {current_perspective} に変更されています。意図的な視点変更か確認してください。"
            )

        return issues

    def _detect_recovery_state(self, text: str) -> str:
        """テキストから休息・回復状態を判定する。"""
        # 休息中 / 回復中 / 戦闘中 の3状態
        resting_kw = ["休息", "眠り", "就寝", "ベッド", "布団", "野営", "止まり", "一息"]
        recovering_kw = ["回復", "傷が癒え", "癒える", "元気を取り戻", "体力が戻", "力が戻"]
        action_kw = ["戦い", "戦闘", "激走", "奔走", "怒涛", "激闘"]

        if any(kw in text for kw in resting_kw):
            return "resting"
        if any(kw in text for kw in recovering_kw):
            return "recovering"
        if any(kw in text for kw in action_kw):
            return "action"
        # 追加の行動判定キーワード
        extra_action_kw = ["猛烈", "激しい", "剣を振る", "攻撃", "戦う", "闘う"]
        if any(kw in text for kw in extra_action_kw):
            return "action"
        return "unknown"

    def check_recovery_continuity(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        """休息回復の一貫性をチェックする。"""
        issues = []
        prev_snapshot = self.get_previous_snapshot(current_ep, character_name)
        if not prev_snapshot:
            return issues

        prev_state = prev_snapshot.recovery_state
        current_state = self._detect_recovery_state(current_text)

        # 前回「戦闘中」で受傷していたのに本次いきなり「回復中」で治療描写がない場合
        prev_injury = prev_snapshot.injury_level
        if prev_state == "action" and prev_injury in ("moderate", "severe"):
            if current_state == "recovering":
                treatment_kw = ["治療", "手当て", "包帯", "薬", "魔法", "癒"]
                if not any(kw in current_text for kw in treatment_kw):
                    issues.append(
                        f"【一貫性警告】{character_name}が前回戦闘で負った傷（{prev_injury}）が、治療描写なしに回復しています。"
                    )
            elif current_state == "action":
                issues.append(
                    f"【連戦警告】{character_name}が前回の戦闘で負った負傷（{prev_injury}）を抱えたまま再び戦闘しています。負傷の影響を描写してください。"
                )

        # 前回「休息中」で本次「行動」の場合、回復描写がないまま戦闘している
        if prev_state in ("exhausted", "resting") and current_state == "action":
            recovery_kw = ["回復", "元気", "癒え", "休息", "眠り", "休憩"]
            if not any(kw in current_text for kw in recovery_kw):
                issues.append(
                    f"【整合性警告】{character_name}の回復描写がないまま、行動しています。休息からの回復プロセスを描写してください。"
                )

        return issues

    def _detect_foreshadowing(self, text: str) -> List[str]:
        """テキストから伏線と思われるキーワードを抽出する。"""
        found = []
        for keyword in FORESHADOW_KEYWORDS:
            if keyword in text:
                found.append(keyword)
        return found

    def check_foreshadowing_continuity(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        """伏線が適切に継承または回収されているかを確認する。"""
        issues = []
        prev_snapshot = self.get_previous_snapshot(current_ep, character_name)
        if not prev_snapshot or not prev_snapshot.foreshadowing_active:
            return issues

        # 前回の伏線が現在のテキストに含まれているか、または回収された形跡があるか
        # 伏線はリスト形式ではなくフラグ管理のため、
        # 具体的な伏線キーワードの追跡が必要な場合は、別途実装が必要。
        # ここでは、前話で伏線がアクティブだった場合、現在のテキストに
        # 伏線キーワードが含まれているか、回収キーワードがあるかをチェックする。

        current_foreshadows = self._detect_foreshadowing(current_text)
        recovery_keywords = ["判明", "解決", "正体", "理由", "気づく"]

        if not current_foreshadows and not any(rk in current_text for rk in recovery_keywords):
            issues.append(
                "【伏線警告】前話で伏線が提示されていましたが、今回のシーンで継承または回収されていません。"
            )

        return issues

    def extract_snapshot(self, text: str) -> SceneStateSnapshot:
        """テキストから現在のシーン状態を抽出し、スナップショットを作成する。"""
        return SceneStateSnapshot(
            injury_level=self._detect_injury_level(text),
            attitude=self._detect_attitude(text),
            discoveries=self._detect_discoveries(text),
            travel_state=self._detect_travel_state(text),
            recovery_state=self._detect_recovery_state(text),
            perspective=self._detect_monologue_perspective(text),
            foreshadowing_active=len(self._detect_foreshadowing(text)) > 0,
            time_of_day=self._detect_time_of_day(text),
            items_held=self._detect_item_ownership(text),
        )

    def check_time_continuity(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        """時間帯の不自然な遷移をチェックする。"""
        issues = []
        prev_snapshot = self.get_previous_snapshot(current_ep, character_name)
        if not prev_snapshot or prev_snapshot.time_of_day == "unknown":
            return issues

        current_time = self._detect_time_of_day(current_text)
        if current_time == "unknown":
            return issues

        transitions = {
            "morning": ["day"],
            "day": ["evening"],
            "evening": ["night"],
            "night": ["morning"],
        }

        prev_time = prev_snapshot.time_of_day
        if prev_time != current_time:
            if current_time not in transitions.get(prev_time, []):
                time_passage_keywords = ["翌日", "数時間後", "翌朝", "夜が明けて", "時間が経ち"]
                if not any(kw in current_text for kw in time_passage_keywords):
                    issues.append(
                        f"時間帯が {prev_time} から {current_time} へ不自然に遷移しています。経過描写が不足している可能性があります。"
                    )

        return issues

    def _detect_item_ownership(self, text: str) -> List[str]:
        """テキストから所持アイテムや重要な物品の記述を抽出する。"""
        found = []
        for item in ITEM_KEYWORDS:
            if item in text:
                found.append(item)
        return found

    def check_all_continuity(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        """全ての整合性チェックをまとめて実行する。"""
        all_issues = []

        # 各種チェックメソッドのリスト
        check_check_methods = [
            self.check_injury_continuity,
            self.check_attitude_continuity,
            self.check_discovery_continuity,
            self.check_travel_continuity,
            self.check_recovery_continuity,
            self.check_perspective_continuity,
            self.check_foreshadowing_continuity,
            self.check_time_continuity,
            self.check_item_continuity,
        ]

        for method in check_check_methods:
            all_issues.extend(method(current_ep, character_name, current_text))

        return all_issues

    def check_item_continuity(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        """アイテムの所持状態に矛盾がないか確認する。"""
        issues = []
        prev_snapshot = self.get_previous_snapshot(current_ep, character_name)
        if not prev_snapshot or not prev_snapshot.items_held:
            return issues

        current_items = self._detect_item_ownership(current_text)

        # 前話で持っていたアイテムが今回言及されているか、あるいは失った描写があるか
        for item in prev_snapshot.items_held:
            if item not in current_items:
                # 紛失・譲渡・消費のキーワードがあるか確認
                loss_keywords = [
                    "失う",
                    "なくす",
                    "捨てる",
                    "譲る",
                    "渡す",
                    "壊れる",
                    "消費",
                    "使う",
                ]
                if not any(kw in current_text for kw in loss_keywords):
                    # 重要アイテム（キーワードに含まれるもの）が突然消えた場合に警告
                    issues.append(
                        f"アイテム '{item}' が前話から消失していますが、紛失や消費の描写がありません。"
                    )

        return issues

    def _detect_time_of_day(self, text: str) -> str:
        """テキストから時間帯（朝・昼・夕・夜・不明）を判定する。"""
        scores = {"morning": 0, "day": 0, "evening": 0, "night": 0}

        # TIME_KEYWORDS は {'morning': [...], 'day': [...], ...} の形式を想定
        for period, keywords in TIME_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    scores[period] += 1

        # 最もスコアが高い時間帯を返す
        best_period = max(scores, key=scores.get)
        if scores[best_period] == 0:
            return "unknown"
        return best_period

    def _init_db(self) -> None:
        """シーン状態保存用テーブルを初期化する。"""
        import sqlite3

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scene_snapshots (
                    character_name TEXT,
                    episode_num INTEGER,
                    scene_type TEXT,
                    injury_level TEXT,
                    attitude TEXT,
                    discoveries TEXT,
                    travel_state TEXT,
                    recovery_state TEXT,
                    perspective TEXT,
                    foreshadowing_active INTEGER,
                    time_of_day TEXT,
                    items_held TEXT,
                    PRIMARY KEY (character_name, episode_num)
                )
            """)


class CharacterStateSnapshot(BaseModel):
    """1話終了時点のキャラクター状態スナップショット。"""

    character_name: str
    episode_num: int
    stamina_level: str = "normal"
    psych_state: str = "neutral"
    clothing_state: str = "fully_dressed"
    intimacy_level: str = "acquaintance"
    location: str = "unknown"
    custom_flags: Optional[Dict[str, str]] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _init_custom_flags(self) -> "CharacterStateSnapshot":
        if self.custom_flags is None:
            self.custom_flags = {}
        return self


class ContinuityReport(BaseModel):
    """話間整合性チェックの結果レポート。"""

    is_consistent: bool
    issues: List[str]
    checked_dimensions: List[str]
    character_name: str
    episode_num: int


class ContinuityTracker:
    """連続話間のキャラクター状態一貫性を追跡する。SQLiteでの永続化に対応。"""

    def __init__(self, db_path: str = "storage/db/kaku_hegemony_v2.db"):
        self.db_path = db_path
        self._snapshots: Dict[int, Dict[str, CharacterStateSnapshot]] = {}
        self._init_db()

    def _init_db(self):
        import sqlite3

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS character_continuity_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_name TEXT,
                    episode_num INTEGER,
                    stamina_level TEXT,
                    psych_state TEXT,
                    clothing_state TEXT,
                    intimacy_level TEXT,
                    location TEXT,
                    custom_flags TEXT,
                    UNIQUE(character_name, episode_num)
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(
                "Failed to initialize SQLite for ContinuityTracker: %s. Using memory only.", e
            )

    def save_snapshot(self, snapshot: CharacterStateSnapshot) -> None:
        """エピソード終了時の状態を保存する。"""
        ep = snapshot.episode_num
        if ep not in self._snapshots:
            self._snapshots[ep] = {}
        self._snapshots[ep][snapshot.character_name] = snapshot

        import json
        import sqlite3

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO character_continuity_snapshots
                (character_name, episode_num, stamina_level, psych_state, clothing_state, intimacy_level, location, custom_flags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    snapshot.character_name,
                    snapshot.episode_num,
                    snapshot.stamina_level,
                    snapshot.psych_state,
                    snapshot.clothing_state,
                    snapshot.intimacy_level,
                    snapshot.location,
                    json.dumps(snapshot.custom_flags),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("Failed to save snapshot to SQLite: %s", e)

    def get_snapshot(
        self, episode_num: int, character_name: str
    ) -> Optional[CharacterStateSnapshot]:
        """指定エピソードのキャラクター状態を取得する。"""
        # メモリ内キャッシュを優先
        if episode_num in self._snapshots and character_name in self._snapshots[episode_num]:
            return self._snapshots[episode_num][character_name]

        import json
        import sqlite3

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT stamina_level, psych_state, clothing_state, intimacy_level, location, custom_flags
                FROM character_continuity_snapshots
                WHERE episode_num = ? AND character_name = ?
            """,
                (episode_num, character_name),
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                flags = {}
                try:
                    flags = json.loads(row[5]) if row[5] else {}
                except Exception:
                    pass
                snap = CharacterStateSnapshot(
                    character_name=character_name,
                    episode_num=episode_num,
                    stamina_level=row[0],
                    psych_state=row[1],
                    clothing_state=row[2],
                    intimacy_level=row[3],
                    location=row[4],
                    custom_flags=flags,
                )
                # キャッシュに保存
                if episode_num not in self._snapshots:
                    self._snapshots[episode_num] = {}
                self._snapshots[episode_num][character_name] = snap
                return snap
        except Exception as e:
            logger.warning("Failed to load snapshot from SQLite: %s", e)

        return None

    def get_previous_snapshot(
        self, current_ep: int, character_name: str
    ) -> Optional[CharacterStateSnapshot]:
        """前話のキャラクター状態を取得する。"""
        return self.get_snapshot(current_ep - 1, character_name)

    @staticmethod
    def _detect_stamina(text: str) -> str:
        """テキストから体力状態を推定する。"""
        exhausted = sum(text.count(kw) for kw in STAMINA_EXHAUSTED_KW)
        tired = sum(text.count(kw) for kw in STAMINA_TIRED_KW)
        energetic = sum(text.count(kw) for kw in STAMINA_ENERGETIC_KW)

        if exhausted >= 2:
            return "exhausted"
        if tired >= 2:
            return "tired"
        if energetic >= 2:
            return "energetic"
        return "normal"

    @staticmethod
    def _detect_psych_state(text: str) -> str:
        """テキストから心理状態を推定する。"""
        distressed = sum(text.count(kw) for kw in PSYCH_DISTRESSED_KW)
        anxious = sum(text.count(kw) for kw in PSYCH_ANXIOUS_KW)
        content = sum(text.count(kw) for kw in PSYCH_CONTENT_KW)
        euphoric = sum(text.count(kw) for kw in PSYCH_EUPHORIC_KW)

        scores = {
            "distressed": distressed,
            "anxious": anxious,
            "content": content,
            "euphoric": euphoric,
        }
        max_state = max(scores, key=scores.get)
        if scores[max_state] >= 2:
            return max_state
        return "neutral"

    @staticmethod
    def _detect_location(text: str) -> str:
        """テキストから場所を推定する。"""
        indoor = sum(text.count(kw) for kw in LOCATION_INDOOR_KW)
        outdoor = sum(text.count(kw) for kw in LOCATION_OUTDOOR_KW)
        if indoor > outdoor:
            return "indoor"
        if outdoor > indoor:
            return "outdoor"
        return "unknown"

    @staticmethod
    def _detect_intimacy(text: str) -> str:
        """テキストから親密度を推定する。"""
        stranger = sum(text.count(kw) for kw in INTIMACY_STRANGER_KW)
        close = sum(text.count(kw) for kw in INTIMACY_CLOSE_KW)
        intimate = sum(text.count(kw) for kw in INTIMACY_INTIMATE_KW)
        bonded = sum(text.count(kw) for kw in INTIMACY_BONDED_KW)

        scores = {"stranger": stranger, "close": close, "intimate": intimate, "bonded": bonded}
        max_level = max(scores, key=scores.get)
        if scores[max_level] >= 1:
            return max_level
        return "acquaintance"

    def _detect_clothing_state(self, text: str) -> str:
        from src.agents.erotic.filter import EroticIntegrityChecker
        """テキスト末尾から衣服状態を推定する。"""
        end_text = text[max(0, len(text) - 500) :]
        undress_count = sum(end_text.count(v) for v in EroticIntegrityChecker.UNDRESS_VERBS)
        dress_count = sum(end_text.count(v) for v in EroticIntegrityChecker.DRESS_VERBS)

        if undress_count > dress_count + 1:
            return "fully_undressed"
        if undress_count > dress_count:
            return "partially_undressed"
        return "fully_dressed"

    def extract_snapshot(
        self, character_name: str, episode_num: int, scene_text: str, clothing_state: str = None
    ) -> CharacterStateSnapshot:
        """テキストを解析してスナップショットを自動生成する。"""
        text_len = len(scene_text)
        end_portion = scene_text[int(text_len * 0.7) :]

        if clothing_state is None:
            clothing_state = self._detect_clothing_state(scene_text)

        snapshot = CharacterStateSnapshot(
            character_name=character_name,
            episode_num=episode_num,
            stamina_level=self._detect_stamina(end_portion),
            psych_state=self._detect_psych_state(end_portion),
            clothing_state=clothing_state,
            intimacy_level=self._detect_intimacy(scene_text),
            location=self._detect_location(end_portion),
        )
        return snapshot

    def check_stamina_continuity(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        """前話の体力状態と今話冒層の体力状態の矛盾を検出する。"""
        issues: List[str] = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None:
            return issues

        opening_len = max(int(len(current_text) * 0.3), 100)
        opening_text = current_text[:opening_len]
        current_stamina = self._detect_stamina(opening_text)

        allowed = STAMINA_ALLOWED_TRANSITIONS.get(prev.stamina_level, STAMINA_LEVELS)
        if current_stamina not in allowed:
            issues.append(
                f"[体力矛盾] {character_name}: 前話末={prev.stamina_level} → "
                f"今話冒頭={current_stamina} は不自然です（許可遷移: {allowed}）"
            )
        return issues

    RECOVERY_KEYWORDS = ["休む", "眠る", "回復", "癒す", "治療", "休息", "睡眠", "朝", "目覚め"]

    def check_recovery_description(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        """前話で疲弊→今話で回復している場合、回復描写があるか検証する。"""
        issues: List[str] = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None:
            return issues

        if prev.stamina_level in ["exhausted", "tired"]:
            current_stamina = self._detect_stamina(
                current_text[: max(int(len(current_text) * 0.3), 100)]
            )
            if current_stamina in ["normal", "energetic"]:
                recovery_found = any(kw in current_text[:500] for kw in self.RECOVERY_KEYWORDS)
                if not recovery_found:
                    issues.append(
                        f"[回復描写不足] {character_name}: 前話末={prev.stamina_level} → "
                        f"今話={current_stamina} ですが、回復の過程が描写されていません"
                    )
        return issues

    @staticmethod
    def _stamina_to_num(level: str) -> int:
        mapping = {"exhausted": 0, "tired": 1, "normal": 2, "energetic": 3}
        return mapping.get(level, 2)

    def check_stamina_jump(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        """前話→今話で体力が2段階以上ジャンプした場合に警告する。"""
        issues: List[str] = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None:
            return issues

        opening_text = current_text[: max(int(len(current_text) * 0.3), 100)]
        current_stamina = self._detect_stamina(opening_text)

        prev_num = self._stamina_to_num(prev.stamina_level)
        curr_num = self._stamina_to_num(current_stamina)

        if abs(curr_num - prev_num) >= 2:
            issues.append(
                f"[体力急変] {character_name}: {prev.stamina_level}→{current_stamina} "
                f"（2段階以上の変化）。段階的な遷移描写を検討してください"
            )
        return issues

    def check_psych_continuity(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        """前話の心理状態と今話冒頭の心理状態の矛盾を検出する。"""
        issues: List[str] = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None:
            return issues

        opening_text = current_text[: max(int(len(current_text) * 0.3), 100)]
        current_psych = self._detect_psych_state(opening_text)

        allowed = PSYCH_ALLOWED_TRANSITIONS.get(prev.psych_state, PSYCH_STATES)
        if current_psych not in allowed:
            issues.append(
                f"[心理矛盾] {character_name}: 前話末={prev.psych_state} → "
                f"今話冒頭={current_psych} は不自然です（許可遷移: {allowed}）"
            )
        return issues

    PSYCH_TRIGGER_KEYWORDS = {
        "distressed_to_content": ["許される", "受け入れられ", "救われ", "光が差"],
        "euphoric_to_anxious": ["裏切り", "暗雲", "別れ", "失う", "突き落と"],
    }

    def check_psych_trigger(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        """心理状態が大きく変化する場合、トリガーイベントがあるか検証する。"""
        issues: List[str] = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None:
            return issues

        current_psych = self._detect_psych_state(
            current_text[: max(int(len(current_text) * 0.3), 100)]
        )

        if prev.psych_state == "distressed" and current_psych in ["content", "euphoric"]:
            trigger_kws = self.PSYCH_TRIGGER_KEYWORDS.get("distressed_to_content", [])
            if not any(kw in current_text[:800] for kw in trigger_kws):
                issues.append(
                    f"[心理トリガー不足] {character_name}: distressed→{current_psych} の変化にトリガーイベントが見つかりません"
                )

        if prev.psych_state == "euphoric" and current_psych in ["distressed", "anxious"]:
            trigger_kws = self.PSYCH_TRIGGER_KEYWORDS.get("euphoric_to_anxious", [])
            if not any(kw in current_text[:800] for kw in trigger_kws):
                issues.append(
                    f"[心理トリガー不足] {character_name}: euphoric→{current_psych} の変化にトリガーイベントが見つかりません"
                )

        return issues

    @staticmethod
    def _psych_to_num(state: str) -> int:
        mapping = {"distressed": 0, "anxious": 1, "neutral": 2, "content": 3, "euphoric": 4}
        return mapping.get(state, 2)

    def check_psych_jump(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        """前話→今話で心理状態が2段階以上ジャンプした場合に警告する。"""
        issues: List[str] = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None:
            return issues

        opening_text = current_text[: max(int(len(current_text) * 0.3), 100)]
        current_psych = self._detect_psych_state(opening_text)

        prev_num = self._psych_to_num(prev.psych_state)
        curr_num = self._psych_to_num(current_psych)

        if abs(curr_num - prev_num) >= 2:
            issues.append(
                f"[心理急変] {character_name}: {prev.psych_state}→{current_psych} "
                f"（2段階以上の変化）。心理変化のプロセス描写を検討してください"
            )
        return issues

    TIME_PASSAGE_KEYWORDS = ["翌朝", "翌日", "数日後", "一週間後", "次の日", "夜が明け", "日が昇"]

    def _has_time_passage(self, text: str) -> bool:
        opening = text[:300]
        return any(kw in opening for kw in self.TIME_PASSAGE_KEYWORDS)

    def check_clothing_continuity(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        from src.agents.erotic.filter import EroticIntegrityChecker
        """前話末の衣服状態が今話冒頭で矛盾していないか検証する。"""
        issues: List[str] = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None:
            return issues

        opening_text = current_text[:500]

        if prev.clothing_state in ["partially_undressed", "fully_undressed"]:
            if self._has_time_passage(opening_text):
                return issues
            dress_found = any(kw in opening_text for kw in EroticIntegrityChecker.DRESS_VERBS)
            dress_kw_found = any(kw in opening_text for kw in EroticIntegrityChecker.DRESS_KEYWORDS)
            if not dress_found and not dress_kw_found:
                issues.append(
                    f"[衣服引き継ぎ矛盾] {character_name}: 前話末={prev.clothing_state} ですが、"
                    f"今話冒頭に着衣の描写がありません"
                )
        return issues

    @staticmethod
    def _intimacy_to_num(level: str) -> int:
        mapping = {"stranger": 0, "acquaintance": 1, "close": 2, "intimate": 3, "bonded": 4}
        return mapping.get(level, 1)

    def check_intimacy_regression(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        issues: List[str] = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None:
            return issues

        current_intimacy = self._detect_intimacy(current_text)
        prev_num = self._intimacy_to_num(prev.intimacy_level)
        curr_num = self._intimacy_to_num(current_intimacy)

        if prev_num - curr_num >= 2:
            issues.append(
                f"[親密度後退] {character_name}: {prev.intimacy_level}→{current_intimacy} "
                f"（2段階以上の後退）。関係性の変化にイベント描写が必要です"
            )
        return issues

    def check_intimacy_rush(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        issues: List[str] = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None:
            return issues

        current_intimacy = self._detect_intimacy(current_text)
        prev_num = self._intimacy_to_num(prev.intimacy_level)
        curr_num = self._intimacy_to_num(current_intimacy)

        if curr_num - prev_num >= 2:
            issues.append(
                f"[親密度急進] {character_name}: {prev.intimacy_level}→{current_intimacy} "
                f"（2段階以上の急進）。関係性発展のプロセス描写を検討してください"
            )
        return issues

    EROTIC_SCENE_MARKERS = ["【Peak", "【peak", "肌を重ね", "身を委ね", "口づけ", "抱きしめ"]

    def check_intimacy_vs_erotic_level(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        issues: List[str] = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None:
            return issues

        has_erotic = any(kw in current_text for kw in self.EROTIC_SCENE_MARKERS)
        if has_erotic and prev.intimacy_level in ["stranger", "acquaintance"]:
            issues.append(
                f"[親密度不足] {character_name}: 親密度={prev.intimacy_level} ですが、"
                f"高強度の官能シーンが検出されました。関係性の発展を先行して描写してください"
            )
        return issues

    def check_location_continuity(
        self, current_ep: int, character_name: str, current_text: str
    ) -> List[str]:
        issues: List[str] = []
        prev = self.get_previous_snapshot(current_ep, character_name)
        if prev is None or prev.location == "unknown":
            return issues

        opening_text = current_text[:500]
        current_location = self._detect_location(opening_text)

        if current_location != "unknown" and current_location != prev.location:
            has_transition = any(kw in opening_text for kw in LOCATION_TRANSITION_KW)
            has_time = self._has_time_passage(opening_text)
            if not has_transition and not has_time:
                issues.append(
                    f"[場所矛盾] {character_name}: 前話末={prev.location} → "
                    f"今話冒頭={current_location} ですが、移動・時間経過の描写がありません"
                )
        return issues

    WEATHER_KEYWORDS = ["雨", "雪", "晴", "曇", "嵐", "風", "霧", "月明かり", "星"]

    def check_environment_consistency(self, prev_text: str, current_text: str) -> List[str]:
        issues: List[str] = []
        prev_end = prev_text[max(0, len(prev_text) - 300) :]
        curr_start = current_text[:300]

        prev_weather = [kw for kw in self.WEATHER_KEYWORDS if kw in prev_end]
        curr_weather = [kw for kw in self.WEATHER_KEYWORDS if kw in curr_start]

        contradictions = [("雨", "晴"), ("雪", "晴"), ("嵐", "晴")]
        for w1, w2 in contradictions:
            if w1 in prev_weather and w2 in curr_weather:
                if not self._has_time_passage(curr_start):
                    issues.append(
                        f"[環境矛盾] 前話末に'{w1}'描写 → 今話冒頭に'{w2}'描写。時間経過の描写がありません"
                    )
        return issues


