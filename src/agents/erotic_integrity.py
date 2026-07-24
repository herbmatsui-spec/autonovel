"""
src/agents/erotic_integrity.py
官能・シーン整合性チェックのエージェント。
Version: 3.3 (Extended Continuity Tracking)
"""

import logging
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, model_validator

logger = logging.getLogger(__name__)

# シーン種別定数
SCENE_TYPES = [
    "erotic",
    "combat",
    "conversation",
    "exploration",
    "travel",
    "rest",
    "monologue",
    "foreshadow",
    "time",
    "item",
]

# シーン種別定数
SCENE_TYPES = [
    "erotic",
    "combat",
    "conversation",
    "exploration",
    "travel",
    "rest",
    "monologue",
    "foreshadow",
    "time",
    "item",
]

# 戦闘シーンキーワード
COMBAT_KEYWORDS = [
    "攻撃",
    "斬撃",
    "魔法",
    "剣",
    "盾",
    "戦い",
    "戦闘",
    "敵",
    "ダメージ",
    "負傷",
    "血",
    "切り裂く",
    "撃破",
    "死闘",
    "激突",
]
# 会話シーンキーワード
CONVERSATION_KEYWORDS = [
    "話す",
    "語る",
    "対話",
    "議論",
    "囁く",
    "問う",
    "答える",
    "口調",
    "態度",
    "表情",
    "納得",
    "反論",
    "説得",
]
# 探索シーンキーワード
EXPLORATION_KEYWORDS = [
    "調べる",
    "発見",
    "探索",
    "見つける",
    "隠し",
    "洞窟",
    "遺跡",
    "手がかり",
    "地図",
    "路地",
    "潜入",
    "巡回",
]
# 移動シーンキーワード
TRAVEL_KEYWORDS = [
    "向かう",
    "旅",
    "移動",
    "辿り着く",
    "街道",
    "馬車",
    "徒歩",
    "船",
    "距離",
    "到着",
    "出発",
    "移動",
]
# 休息シーンキーワード
REST_KEYWORDS = [
    "眠る",
    "休息",
    "休む",
    "キャンプ",
    "宿屋",
    "回復",
    "まどろむ",
    "夜明",
    "休息時間",
    "リラックス",
]
# 独白シーンキーワード
MONOLOGUE_KEYWORDS = [
    "思う",
    "感じる",
    "心の中で",
    "独白",
    "自問",
    "回想",
    "記憶",
    "呟く",
    "考え込む",
]
# 伏線シーンキーワード
FORESHADOW_KEYWORDS = [
    "予感",
    "違和感",
    "意味深",
    "伏線",
    "暗示",
    "不吉",
    "兆候",
    "鍵となる",
    "後でわかる",
]
# 時間帯キーワード
TIME_KEYWORDS = {
    "morning": ["朝", "暁", "午前", "夜が明けて"],
    "day": ["昼", "正午", "日中"],
    "evening": ["夕方", "黄昏", "午後"],
    "night": ["夜", "深夜", "夜更け"],
}
# アイテムキーワード
ITEM_KEYWORDS = [
    "持つ",
    "所持",
    "アイテム",
    "道具",
    "武器",
    "装備",
    "拾う",
    "失う",
    "鍵",
    "薬",
    "宝箱",
]

# 同意確認キーワード（明示的）
CONSENT_EXPLICIT_KEYWORDS = ["同意", "了承", "承諾", "OK", "いいよ", "求めて", "欲しい", "させて"]
# 同意確認キーワード（暗黙的）
CONSENT_IMPLICIT_KEYWORDS = [
    "促す",
    "引き寄せる",
    "唇が触れる",
    "近づく",
    "体が触れる",
    "手を伸ばす",
]
# 拒否・不同意キーワード
CONSENT_REFUSAL_KEYWORDS = ["嫌", "やだ", "断る", "拒否", "抗拒", "逃げる", "拒む"]

# 双方向同意キーワード
CONSENT_A_TO_B_KEYWORDS = ["いいよ", "求めて", "欲しい", "させて", "同意", "了承", "承諾", "OK"]
CONSENT_B_TO_A_KEYWORDS = [
    "構わない",
    "いいわ",
    "いいわよ",
    "お願い",
    "返事",
    "誘導",
    "促す",
    "引き寄せる",
    "応じる",
    "受け入れる",
    "任せて",
    "いいな",
    "どうぞ",
    "近づく",
    "唇が触れる",
    "体が触れる",
    "手を伸ばす",
    "身を寄せる",
]

# 簡易双方向同意: 両者共通の同意表現（方向ではなく存在チェック用）
CONSENT_ALL_CHARACTERS_KEYWORDS = [
    "いいよ",
    "いいわ",
    "いいな",
    "求めて",
    "欲しい",
    "させて",
    "OK",
    "同意",
    "了承",
    "承諾",
    "構わない",
    "受け入れる",
    "応じる",
    "任せて",
    "どうぞ",
    "お願い",
]
CONSENT_CONTINUATION_KEYWORDS = ["そのまま", "ながらも", "それでも", "しかし", "しかしながら"]
CONSENT_DISTANCE_THRESHOLD = 500

# 官能品質スコアリング用キーワード
SENSORY_TOUCH_KEYWORDS = [
    "触れる",
    "触覚",
    "感触",
    "肌",
    "温度",
    "熱",
    "冷た",
    "温もり",
    "柔らか",
    "ざら",
    "滑らか",
    "指先",
    "掌",
    "撫で",
    "震え",
    "脈",
]
SENSORY_SMELL_KEYWORDS = ["香り", "匂い", "嗅覚", "芳香", "薫る", "馨しい", "麝香", "甘い香り"]
SENSORY_SOUND_KEYWORDS = [
    "吐息",
    "呼吸",
    "囁き",
    "衣擦れ",
    "鼓動",
    "心音",
    "喘ぎ",
    "静寂",
    "響く",
    "音",
]
SENSORY_SIGHT_KEYWORDS = ["視線", "瞳", "眼差し", "光", "陰影", "照らす", "映る", "煌めき"]
SENSORY_TASTE_KEYWORDS = ["味覚", "味わう", "甘い", "苦い", "唇", "舌"]

METAPHOR_KEYWORDS = [
    "ように",
    "まるで",
    "かのような",
    "彷彿",
    "～めく",
    "～じみる",
    "如く",
    "波のように",
    "光のように",
    "溶けるように",
    "ほどけて",
]

# 比喩密度スコア自動調整用: シーン長閾値


class SceneStateSnapshot(BaseModel):
    """一般シーンの状態を保存するためのスナップショット。"""

    character_name: str
    episode_num: int
    scene_type: str
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
            "severe": ["致命的", "瀕死", "意識不明", "血の海", "絶望的", "崩れ落ち"],
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
            "hostile": ["拒絶", "怒り", "罵倒", "軽蔑", "激昂", "憎しみ", "突き放す"],
            "tense": ["緊張", "気まずい", "沈黙", "警戒", "険しい", "冷ややか", "対立"],
            "friendly": ["親密", "信頼", "微笑み", "穏やか", "快諾", "共感", "温かい"],
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
                f"【整合性警告】{character_name}の態度が {prev_attitude} から {current_attitude} へ不自然に変化しています。心理描写やイベントによる変化があるか確認してください。"
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
                    f"【移動断絶】{character_name}が前回出発したにもかかわらず、到着描写がありません。途中経路か到着シーンを追加してください。"
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


class SceneTypeDetector:
    """テキストからシーン種別を判定する。"""

    def detect(self, text: str) -> str:
        """テキストからシーン種別を判定する。"""
        scores = {stype: 0 for stype in SCENE_TYPES}

        # 各種キーワードに基づくスコアリング
        keyword_map = {
            "combat": COMBAT_KEYWORDS,
            "conversation": CONVERSATION_KEYWORDS,
            "exploration": EXPLORATION_KEYWORDS,
            "travel": TRAVEL_KEYWORDS,
            "rest": REST_KEYWORDS,
            "monologue": MONOLOGUE_KEYWORDS,
            "foreshadow": FORESHADOW_KEYWORDS,
            "time": TIME_KEYWORDS,
            "item": ITEM_KEYWORDS,
        }

        for stype, keywords in keyword_map.items():
            for kw in keywords:
                if kw in text:
                    scores[stype] += 1

        # 官能シーンの判定（既存のロジックを簡易的に模倣、またはキーワードで判定）
        # ここでは簡易的に 'erotic' キーワードとして扱うか、他が低ければデフォルトにする
        # 本来は EroticQualityScorer の判定に寄せるべきだが、Detector単体で完結させる
        if any(kw in text for kw in ["官能", "情事", "愛撫", "絶頂"]):
            scores["erotic"] += 5

        # 最もスコアの高いシーン種別を返す。同点の場合は 'erotic' または 'conversation' を優先
        max_score = max(scores.values())
        if max_score == 0:
            return "conversation"  # デフォルト

        best_types = [t for t, s in scores.items() if s == max_score]
        if "erotic" in best_types:
            return "erotic"
        if "conversation" in best_types:
            return "conversation"
        return best_types[0]


METAPHOR_SCENE_SHORT_THRESHOLD = 200
METAPHOR_SCENE_MEDIUM_THRESHOLD = 500
# シーン長別の密度係数（倍率）
METAPHOR_DENSITY_COEFFICIENTS = {"short": 35.0, "medium": 25.0, "long": 18.0}

# テンション曲線段階的スコアリング用: フェーズ区切りマーカ
PHASE_MARKERS = ["【Build", "【Peak", "【Afterglow", "【build", "【peak", "【afterglow"]
# フェーズ別スコア
TENSION_SCORE_U_SHAPE = 85.0  # Build短→Peak長→Afterglow短
TENSION_SCORE_RISING = 60.0  # 上昇のみ
TENSION_SCORE_FALLING = 50.0  # 下降のみ
TENSION_SCORE_FLAT = 20.0  # 平坦
TENSION_BONUS_SMOOTH = 5.0  # 滑らかさボーナス
TENSION_PENALTY_SHARP = 10.0  # 極端な段差ペナルティ
MECHANICAL_KEYWORDS = [
    "次に",
    "続けて",
    "更に",
    "もう一度",
    "繰り返す",
    "そして",
    "それから",
    "第一に",
    "第二に",
    "段階",
]
EMOTION_LAYER_KEYWORDS = [
    "感情",
    "思い",
    "心",
    "胸",
    "感じる",
    "満たされる",
    "溢れる",
    "切な",
    "愛しさ",
]
BODY_LAYER_KEYWORDS = ["身体", "肌", "体温", "震え", "反応", "反る", "熱くなる", "火照る"]
PSYCHOLOGY_LAYER_KEYWORDS = [
    "心理",
    "意識",
    "思考",
    "記憶",
    "過去",
    "未来",
    "意味",
    "理解",
    "気づく",
    "悟る",
]

AFTERGLOW_DEPTH_KEYWORDS = [
    "沈静",
    "余韻",
    "温もり",
    "安らぎ",
    "静まる",
    "距離感",
    "再確認",
    "次話",
    "明日",
    "これから",
    "伏線",
]
EROTICIZED_CONSENT_KEYWORDS = [
    "囁くように",
    "震える声で",
    "熱を帯びた",
    "誘うように",
    "乞うように",
    "縋るように",
    "潤んだ瞳で",
    "甘く",
]

# ===== Continuity Tracker 用定数 =====
STAMINA_LEVELS = ["exhausted", "tired", "normal", "energetic"]
STAMINA_EXHAUSTED_KW = ["疲弊", "倒れ", "限界", "動けない", "気力が尽き", "ぐったり", "意識が遠"]
STAMINA_TIRED_KW = ["疲れ", "だるい", "重い体", "息が荒い", "汗", "消耗"]
STAMINA_ENERGETIC_KW = ["元気", "活力", "力が漲", "意気揚々", "弾む", "軽やか"]

PSYCH_STATES = ["distressed", "anxious", "neutral", "content", "euphoric"]
PSYCH_DISTRESSED_KW = ["絶望", "崩壊", "慟哭", "恐怖", "パニック", "錯乱"]
PSYCH_ANXIOUS_KW = ["不安", "怯え", "緊張", "動揺", "迷い", "警戒"]
PSYCH_CONTENT_KW = ["安心", "充足", "満足", "穏やか", "幸せ", "落ち着"]
PSYCH_EUPHORIC_KW = ["恍惚", "歓喜", "至福", "有頂天", "陶酔", "昂揚"]

INTIMACY_LEVELS = ["stranger", "acquaintance", "close", "intimate", "bonded"]
INTIMACY_STRANGER_KW = ["初対面", "見知らぬ", "他人", "知らない人"]
INTIMACY_CLOSE_KW = ["信頼", "心を開", "打ち解け", "絆", "友人"]
INTIMACY_INTIMATE_KW = ["肌を重ね", "身を委ね", "一つに", "深い関係", "恋人"]
INTIMACY_BONDED_KW = ["運命", "離れられ", "魂", "永遠", "誓い"]

LOCATION_INDOOR_KW = ["部屋", "室内", "寝室", "浴室", "宿", "屋敷", "館", "家"]
LOCATION_OUTDOOR_KW = ["外", "森", "庭", "野原", "河", "海", "空の下", "屋外"]
LOCATION_TRANSITION_KW = ["移動", "向かう", "戻る", "出る", "入る", "到着"]

# ===== シーン種別定数（汎用 Continuity Tracker 用） =====
SCENE_TYPES = [
    "combat",
    "conversation",
    "exploration",
    "travel",
    "rest",
    "monologue",
    "erotic",
    "unknown",
]

COMBAT_KEYWORDS = [
    "戦う",
    "斬る",
    "打つ",
    "攻撃",
    "防御",
    "魔法",
    "剣",
    "槍",
    "弓",
    "呪文",
    "殺",
    "討つ",
    "防ぐ",
    "避ける",
    "盾",
    "刃",
]
CONVERSATION_KEYWORDS = [
    "言った",
    "答えた",
    "聞いた",
    "問う",
    "語る",
    "話す",
    "囁く",
    "叫ぶ",
    "会話",
    "対話",
    "応える",
    "返す",
]
EXPLORATION_KEYWORDS = [
    "調べる",
    "探索",
    "探す",
    "発見",
    "手がかり",
    "足跡",
    "痕跡",
    "調べ",
    "観察",
    "捜索",
    "見つけ",
]
TRAVEL_KEYWORDS = [
    "向かう",
    "移動",
    "歩く",
    "道を",
    "戻る",
    "出る",
    "入る",
    "到着",
    "出発",
    "旅路",
    "街道",
]
REST_KEYWORDS = [
    "休む",
    "眠る",
    "睡眠",
    "休息",
    "座り込む",
    "横たわる",
    "眠りにつ",
    "宿",
    "野営",
    "仮眠",
]
MONOLOGUE_KEYWORDS = [
    "思う",
    "考える",
    "心に",
    "独白",
    "内心",
    "胸の奥で",
    "～だろうか",
    "問いかける",
    "自問",
]

# ===== シーン種別定数（汎用 Continuity Tracker 用） =====
SCENE_TYPES = [
    "combat",
    "conversation",
    "exploration",
    "travel",
    "rest",
    "monologue",
    "erotic",
    "unknown",
]

COMBAT_KEYWORDS = [
    "戦う",
    "斬る",
    "打つ",
    "攻撃",
    "防御",
    "魔法",
    "剣",
    "槍",
    "弓",
    "呪文",
    "殺",
    "討つ",
    "防ぐ",
    "避ける",
    "盾",
    "刃",
]
CONVERSATION_KEYWORDS = [
    "言った",
    "答えた",
    "聞いた",
    "問う",
    "語る",
    "話す",
    "囁く",
    "叫ぶ",
    "会話",
    "対話",
    "応える",
    "返す",
]
EXPLORATION_KEYWORDS = [
    "調べる",
    "探索",
    "探す",
    "発見",
    "手がかり",
    "足跡",
    "痕跡",
    "調べ",
    "観察",
    "捜索",
    "見つけ",
]
TRAVEL_KEYWORDS = [
    "向かう",
    "移動",
    "歩く",
    "道を",
    "戻る",
    "出る",
    "入る",
    "到着",
    "出発",
    "旅路",
    "街道",
]
REST_KEYWORDS = [
    "休む",
    "眠る",
    "睡眠",
    "休息",
    "座り込む",
    "横たわる",
    "眠りにつ",
    "宿",
    "野営",
    "仮眠",
]
MONOLOGUE_KEYWORDS = [
    "思う",
    "考える",
    "心に",
    "独白",
    "内心",
    "胸の奥で",
    "～だろうか",
    "問いかける",
    "自問",
]

# ===== シーン種別定数（汎用 Continuity Tracker 用） =====
SCENE_TYPES = [
    "combat",
    "conversation",
    "exploration",
    "travel",
    "rest",
    "monologue",
    "erotic",
    "unknown",
]

COMBAT_KEYWORDS = [
    "戦う",
    "斬る",
    "打つ",
    "攻撃",
    "防御",
    "魔法",
    "剣",
    "槍",
    "弓",
    "呪文",
    "殺",
    "討つ",
    "防ぐ",
    "避ける",
    "盾",
    "刃",
]
CONVERSATION_KEYWORDS = [
    "言った",
    "答えた",
    "聞いた",
    "問う",
    "語る",
    "話す",
    "囁く",
    "叫ぶ",
    "会話",
    "対話",
    "応える",
    "返す",
]
EXPLORATION_KEYWORDS = [
    "調べる",
    "探索",
    "探す",
    "発見",
    "手がかり",
    "足跡",
    "痕跡",
    "調べ",
    "観察",
    "捜索",
    "見つけ",
]
TRAVEL_KEYWORDS = [
    "向かう",
    "移動",
    "歩く",
    "道を",
    "戻る",
    "出る",
    "入る",
    "到着",
    "出発",
    "旅路",
    "街道",
]
REST_KEYWORDS = [
    "休む",
    "眠る",
    "睡眠",
    "休息",
    "座り込む",
    "横たわる",
    "眠りにつ",
    "宿",
    "野営",
    "仮眠",
]
MONOLOGUE_KEYWORDS = [
    "思う",
    "考える",
    "心に",
    "独白",
    "内心",
    "胸の奥で",
    "～だろうか",
    "問いかける",
    "自問",
]

# ===== シーン種別定数（汎用 Continuity Tracker 用） =====
SCENE_TYPES = [
    "combat",
    "conversation",
    "exploration",
    "travel",
    "rest",
    "monologue",
    "erotic",
    "unknown",
]

COMBAT_KEYWORDS = [
    "戦う",
    "斬る",
    "打つ",
    "攻撃",
    "防御",
    "魔法",
    "剣",
    "槍",
    "弓",
    "呪文",
    "殺",
    "討つ",
    "防ぐ",
    "避ける",
    "盾",
    "刃",
]
CONVERSATION_KEYWORDS = [
    "言った",
    "答えた",
    "聞いた",
    "問う",
    "語る",
    "話す",
    "囁く",
    "叫ぶ",
    "会話",
    "対話",
    "応える",
    "返す",
]
EXPLORATION_KEYWORDS = [
    "調べる",
    "探索",
    "探す",
    "発見",
    "手がかり",
    "足跡",
    "痕跡",
    "調べ",
    "観察",
    "捜索",
    "見つけ",
]
TRAVEL_KEYWORDS = [
    "向かう",
    "移動",
    "歩く",
    "道を",
    "戻る",
    "出る",
    "入る",
    "到着",
    "出発",
    "旅路",
    "街道",
]
REST_KEYWORDS = [
    "休む",
    "眠る",
    "睡眠",
    "休息",
    "座り込む",
    "横たわる",
    "眠りにつ",
    "宿",
    "野営",
    "仮眠",
]
MONOLOGUE_KEYWORDS = [
    "思う",
    "考える",
    "心に",
    "独白",
    "内心",
    "胸の奥で",
    "～だろうか",
    "問いかける",
    "自問",
]

STAMINA_ALLOWED_TRANSITIONS = {
    "exhausted": ["exhausted", "tired"],
    "tired": ["exhausted", "tired", "normal"],
    "normal": ["exhausted", "tired", "normal", "energetic"],
    "energetic": ["tired", "normal", "energetic"],
}

PSYCH_ALLOWED_TRANSITIONS = {
    "distressed": ["distressed", "anxious"],
    "anxious": ["distressed", "anxious", "neutral"],
    "neutral": ["anxious", "neutral", "content"],
    "content": ["neutral", "content", "euphoric"],
    "euphoric": ["content", "euphoric", "neutral"],
}

# 官能品質の評価次元
EROTIC_QUALITY_DIMENSIONS = {
    "sensory_depth": "五感の深さ（触覚/嗅覚/聴覚/視覚/味覚のカバレッジ）",
    "metaphor_density": "文学的比喩の密度",
    "tension_arc": "テンション曲線（文長変動と緊張の上昇→下降パターン）",
    "emotion_layering": "感情→身体→心理の3層構造",
    "afterglow_depth": "余韻の深さ（意味のあるアフターグロー）",
    "consent_eroticized": "同意表現の官能化",
    "vocabulary_diversity": "語彙の多様性（繰り返し回避）",
    "mechanical_avoidance": "機械的/マニュアル的描写の回避",
}


class EroticQualityReport(BaseModel):
    """官能品質の評価レポート。"""

    quality_score: float
    dimension_scores: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]


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


class EroticQualityScorer:
    """官能品質をスコアリングするエンハンサー。"""

    def score(self, scene_text: str) -> EroticQualityReport:
        """シーンの官能品質を総合評価する。"""
        dims = {}
        dims["sensory_depth"] = self._score_sensory_depth(scene_text)
        dims["metaphor_density"] = self._score_metaphor_density(scene_text)
        dims["tension_arc"] = self._score_tension_arc(scene_text)
        dims["emotion_layering"] = self._score_emotion_layering(scene_text)
        dims["afterglow_depth"] = self._score_afterglow_depth(scene_text)
        dims["consent_eroticized"] = self._score_consent_eroticized(scene_text)
        dims["vocabulary_diversity"] = self._score_vocabulary_diversity(scene_text)
        dims["mechanical_avoidance"] = self._score_mechanical_avoidance(scene_text)

        quality_score = sum(dims.values()) / len(dims)

        strengths = [EROTIC_QUALITY_DIMENSIONS[k] for k, v in dims.items() if v >= 70.0]
        weaknesses = [EROTIC_QUALITY_DIMENSIONS[k] for k, v in dims.items() if v <= 30.0]
        suggestions = self._generate_suggestions(dims)

        return EroticQualityReport(
            quality_score=quality_score,
            dimension_scores=dims,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
        )

    def _score_sensory_depth(self, scene_text: str) -> float:
        """五感カバレッジをスコアリング。触覚/嗅覚/聴覚/視覚/味覚の5次元。"""
        touch_count = sum(scene_text.count(kw) for kw in SENSORY_TOUCH_KEYWORDS)
        smell_count = sum(scene_text.count(kw) for kw in SENSORY_SMELL_KEYWORDS)
        sound_count = sum(scene_text.count(kw) for kw in SENSORY_SOUND_KEYWORDS)
        sight_count = sum(scene_text.count(kw) for kw in SENSORY_SIGHT_KEYWORDS)
        taste_count = sum(scene_text.count(kw) for kw in SENSORY_TASTE_KEYWORDS)

        counts = [touch_count, smell_count, sound_count, sight_count, taste_count]
        covered = sum(1 for c in counts if c > 0)
        total = sum(counts)

        # 基本スコア: カバレッジ (触覚優先重み)
        coverage_score = (covered / 5.0) * 50.0
        # 密度スコア: 100字あたりの感覚キーワード
        density = total / max(len(scene_text) / 100.0, 1.0)
        density_score = min(density * 10.0, 50.0)

        return coverage_score + density_score

    def _score_metaphor_density(self, scene_text: str) -> float:
        """文学的比喩の密度を評価。シーン長に応じて密度係数を自動調整する。"""
        metaphor_count = sum(scene_text.count(kw) for kw in METAPHOR_KEYWORDS)
        text_len = len(scene_text)
        if text_len == 0:
            return 0.0

        scene_type = self._classify_scene_length(text_len)
        coef = METAPHOR_DENSITY_COEFFICIENTS[scene_type]
        density = metaphor_count / (text_len / 100.0) * coef
        return min(density, 100.0)

    @staticmethod
    def _classify_scene_length(text_len: int) -> str:
        """シーン長を short / medium / long に分類する。"""
        if text_len < METAPHOR_SCENE_SHORT_THRESHOLD:
            return "short"
        elif text_len < METAPHOR_SCENE_MEDIUM_THRESHOLD:
            return "medium"
        return "long"

    def _score_tension_arc(self, scene_text: str) -> float:
        """テンション曲線を評価。フェーズ別文長の段階的スコアリング。"""
        markers = self._detect_phase_markers(scene_text)

        # フェーズマーカーがない場合のみ旧方式にフォールバック
        if not markers:
            return self._score_tension_arc_legacy(scene_text)

        build_s, peak_s, afterglow_s = self._extract_all_phases(scene_text, markers)

        build_avg = self._avg_length(build_s)
        peak_avg = self._avg_length(peak_s)
        afterglow_avg = self._avg_length(afterglow_s)

        # フェーズ別文長からテンション曲線タイプを分類
        # U字: Peak が Build と Afterglow の両方より明確に長い
        PEAK_MARGIN = 1.3
        peak_is_max = (peak_avg >= build_avg * PEAK_MARGIN) and (
            peak_avg >= afterglow_avg * PEAK_MARGIN
        )

        if peak_is_max:
            score = TENSION_SCORE_U_SHAPE
            # 滑らかさボーナス
            if self._is_smooth_arc(build_avg, peak_avg, afterglow_avg):
                score += TENSION_BONUS_SMOOTH
            # 極端な段差ペナルティ
            if self._is_sharp_drop(peak_avg, afterglow_avg):
                score -= TENSION_PENALTY_SHARP
        elif afterglow_avg >= peak_avg:
            # Afterglow が Peak 以上 → 上昇（ピーク以降も維持）
            score = TENSION_SCORE_RISING
        elif build_avg >= peak_avg:
            # Build が Peak 以上 → 下降
            score = TENSION_SCORE_FALLING
        else:
            score = TENSION_SCORE_FLAT

        return max(0.0, min(score, 100.0))

    @staticmethod
    def _detect_phase_markers(scene_text: str) -> List[int]:
        """フェーズ区切りマーカの出現位置（インデックス）を検出する。重複は除去。"""
        positions = []
        for marker in PHASE_MARKERS:
            pos = scene_text.find(marker)
            if pos != -1 and pos not in positions:
                positions.append(pos)
        return sorted(positions)

    def _extract_all_phases(
        self, scene_text: str, markers: List[int]
    ) -> Tuple[List[str], List[str], List[str]]:
        """マーカ位置を使って Build / Peak / Afterglow の文を抽出する。"""
        sections = []
        for i, start in enumerate(markers):
            end = markers[i + 1] if i + 1 < len(markers) else len(scene_text)
            section_text = scene_text[start:end]
            sections.append(self._split_sentences(section_text))

        # markers の順序に従って build/peak/afterglow に対応
        build_s, peak_s, afterglow_s = [], [], []
        for idx, marker in enumerate(markers):
            marker_str = scene_text[marker : marker + 12]
            if "build" in marker_str.lower():
                build_s = sections[idx] if idx < len(sections) else []
            elif "peak" in marker_str.lower():
                peak_s = sections[idx] if idx < len(sections) else []
            elif "afterglow" in marker_str.lower():
                afterglow_s = sections[idx] if idx < len(sections) else []

        return build_s, peak_s, afterglow_s

    @staticmethod
    def _avg_length(sentences: List[str]) -> float:
        """文リストの平均文字長を計算（空なら0）。"""
        if not sentences:
            return 0.0
        return sum(len(s) for s in sentences) / len(sentences)

    @staticmethod
    def _is_smooth_arc(build_avg: float, peak_avg: float, afterglow_avg: float) -> bool:
        """Build→Peak→Afterglow の段差が滑らかか判定。"""
        if peak_avg == 0:
            return False
        return (build_avg / peak_avg > 0.3) and (afterglow_avg / peak_avg > 0.3)

    @staticmethod
    def _is_sharp_drop(peak_avg: float, afterglow_avg: float) -> bool:
        """Peak→Afterglow の下降が極端（1/3以下）か判定。"""
        if peak_avg == 0:
            return False
        return afterglow_avg < peak_avg / 3.0

    def _score_tension_arc_legacy(self, scene_text: str) -> float:
        """従来の分散ベース・テンションスコア（フォールバック用）。"""
        sentences = self._split_sentences(scene_text)
        if len(sentences) < 3:
            return 20.0

        lengths = [len(s) for s in sentences]
        if not lengths:
            return 0.0

        avg_len = sum(lengths) / len(lengths)
        variance = sum((ln - avg_len) ** 2 for ln in lengths) / len(lengths)
        variance_score = min(variance / 50.0, 50.0)

        n = len(lengths)
        first_third = lengths[: n // 3]
        last_third = lengths[2 * n // 3 :]
        if first_third and last_third:
            first_avg = sum(first_third) / len(first_third)
            last_avg = sum(last_third) / len(last_third)
            gradient_score = 20.0 if first_avg > last_avg * 1.2 else 0.0
        else:
            gradient_score = 10.0

        return variance_score + gradient_score + 30.0 if len(sentences) >= 5 else 0.0

    def _score_emotion_layering(self, scene_text: str) -> float:
        """感情→身体→心理の3層構造を評価。"""
        emotion_count = sum(scene_text.count(kw) for kw in EMOTION_LAYER_KEYWORDS)
        body_count = sum(scene_text.count(kw) for kw in BODY_LAYER_KEYWORDS)
        psych_count = sum(scene_text.count(kw) for kw in PSYCHOLOGY_LAYER_KEYWORDS)

        layers_present = sum(1 for c in [emotion_count, body_count, psych_count] if c > 0)
        layer_score = (layers_present / 3.0) * 60.0

        # バランスボーナス（1層だけ突出していないか）
        total = emotion_count + body_count + psych_count
        if total > 0:
            ratios = [emotion_count / total, body_count / total, psych_count / total]
            imbalance = max(ratios) - min(ratios)
            balance_score = max(0.0, (1.0 - imbalance) * 40.0)
        else:
            balance_score = 0.0

        return layer_score + balance_score

    def _score_afterglow_depth(self, scene_text: str) -> float:
        """余韻の深さを評価。"""
        afterglow_count = sum(scene_text.count(kw) for kw in AFTERGLOW_DEPTH_KEYWORDS)
        if afterglow_count >= 4:
            return 90.0
        elif afterglow_count >= 2:
            return 60.0
        elif afterglow_count >= 1:
            return 30.0
        return 0.0

    def _score_consent_eroticized(self, scene_text: str) -> float:
        """同意表現が官能的に描写されているかを評価。"""
        eroticized_count = sum(scene_text.count(kw) for kw in EROTICIZED_CONSENT_KEYWORDS)
        explicit_count = sum(scene_text.count(kw) for kw in CONSENT_EXPLICIT_KEYWORDS)

        if explicit_count == 0:
            return 0.0

        # 官能的同意 / 全同意表現 の比率
        ratio = eroticized_count / max(explicit_count, 1.0)
        return min(ratio * 100.0, 100.0)

    def _score_vocabulary_diversity(self, scene_text: str) -> float:
        """語彙の多様性を評価。キーワードの重複を検出。"""
        all_sensory = (
            SENSORY_TOUCH_KEYWORDS
            + SENSORY_SMELL_KEYWORDS
            + SENSORY_SOUND_KEYWORDS
            + SENSORY_SIGHT_KEYWORDS
            + SENSORY_TASTE_KEYWORDS
        )

        keyword_counts = {}
        for kw in all_sensory:
            c = scene_text.count(kw)
            if c > 0:
                keyword_counts[kw] = c

        if not keyword_counts:
            return 0.0

        max_repeat = max(keyword_counts.values())
        if max_repeat <= 1:
            return 100.0
        elif max_repeat <= 2:
            return 75.0
        elif max_repeat <= 3:
            return 50.0
        elif max_repeat <= 5:
            return 25.0
        return 0.0

    def _score_mechanical_avoidance(self, scene_text: str) -> float:
        """機械的/マニュアル的描写の回避度を評価。"""
        mechanical_count = sum(scene_text.count(kw) for kw in MECHANICAL_KEYWORDS)
        text_len = len(scene_text)
        if text_len == 0:
            return 0.0
        density = mechanical_count / (text_len / 100.0)
        if density == 0:
            return 100.0
        elif density <= 0.5:
            return 80.0
        elif density <= 1.0:
            return 60.0
        elif density <= 2.0:
            return 30.0
        return 0.0

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """句読点で文を分割。"""
        sentences = []
        current = ""
        for char in text:
            current += char
            if char in ["。", "！", "？", "」", "."]:
                sentences.append(current.strip())
                current = ""
        if current.strip():
            sentences.append(current.strip())
        return [s for s in sentences if s]

    @staticmethod
    def _generate_suggestions(dims: Dict[str, float]) -> List[str]:
        """弱点に基づいて具体的な改善提案を生成。"""
        suggestions = []
        threshold = 30.0

        if dims.get("sensory_depth", 100) <= threshold:
            suggestions.append(
                "五感描写を強化: 触覚・嗅覚・聴覚・視覚・味覚のうち不足している感覚を追加してください。特に触覚と嗅覚は官能表現に重要です。"
            )
        if dims.get("metaphor_density", 100) <= threshold:
            suggestions.append(
                "文学的比喩を増やしてください。「〜のように」「まるで〜」などの比喩表現を使い、直接的な描写を避けてください。"
            )
        if dims.get("tension_arc", 100) <= threshold:
            suggestions.append(
                "テンション曲線を強化: 文の長さに変化をつけ、前半→中盤→後半でテンションの上昇→下降パターンを作ってください。"
            )
        if dims.get("emotion_layering", 100) <= threshold:
            suggestions.append(
                "感情→身体反応→心理変化の3層構造を明示的に書いてください。感情描写だけでなく、身体反応と心理的意味づけの両方を入れてください。"
            )
        if dims.get("afterglow_depth", 100) <= threshold:
            suggestions.append(
                "余韻を深くしてください。沈静・距離感の再確認・次話への伏線を含めてください。最低2段落以上が推奨です。"
            )
        if dims.get("consent_eroticized", 100) <= threshold:
            suggestions.append(
                "同意表現を官能的にしてください。「OK」「いいよ」のような事務的同意ではなく、「震える声で」「潤んだ瞳で」など官能的な同意表現を使ってください。"
            )
        if dims.get("vocabulary_diversity", 100) <= threshold:
            suggestions.append(
                "語彙の多様性を高めてください。同じ感覚キーワードの繰り返しを避け、類義語を使って表現の幅を広げてください。"
            )
        if dims.get("mechanical_avoidance", 100) <= threshold:
            suggestions.append(
                "機械的描写を避けてください。「次に」「更に」「そして」のような段階的な手順説明は官能表現を損ないます。流れるような自然な描写を心がけてください。"
            )

        return suggestions


class EroticIntegrityChecker:
    """官能・シーン整合性を管理するチェッカー。"""

    # 服装整合性キーワード
    UNDRESS_KEYWORDS = ["衣を解く", "衣を脱ぐ", "露わになる", "肌を晒す", "裸になる"]
    DRESS_KEYWORDS = ["衣服を整える", "着直す", "衣を纏う", "袖を通す"]

    # 衣服状態追跡用
    UNDRESS_VERBS = ["脱ぐ", "解く", "剥ぐ", "脱がす", "剥がす", "取り除く", "剥き取る"]
    DRESS_VERBS = ["着る", "整える", "纏う", "着直す", "羽織る", "掛ける", "通す"]
    EXCLUDE_KEYWORDS = ["髪を解く", "髪をほどく", "帯を解く", "紐を解く"]

    class ClothingState:
        FULLY_DRESSED = "fully_dressed"
        PARTIALLY_UNDERSESED = "partially_undressed"
        FULLY_UNDERSESED = "fully_undressed"

    class ClothingEvent:
        def __init__(self, event_type: str, position: int, phase: str, text: str):
            self.event_type = event_type
            self.position = position
            self.phase = phase
            self.text = text

    # 強制・暴力検出用パターン
    COERCION_INDICATORS = [
        "無理やり",
        "強制",
        "脅迫",
        "恐怖",
        "怯える",
        "震える",
        "逃げたい",
        "嫌なのに",
        "嫌なのにやめて",
        "やめろと言っているのに",
        "嫌がっているのに",
        "押し倒す",
        "押さえつける",
        "拘束",
        "締め付ける",
        "閉じ込める",
        "無視する",
        "無視した",
        "無視して",
        "耳を塞ぐ",
        "目を背ける",
    ]

    VIOLENCE_INDICATORS = [
        "痛い",
        "痛がる",
        "痛がり",
        "痛み",
        "苦しい",
        "苦しみ",
        "苦しむ",
        "苦しむ",
        "叫ぶ",
        "叫び",
        "叫んだ",
        "悲鳴",
        "泣く",
        "涙",
        "出血",
        "傷",
        "あざ",
        "瘀血",
        "打撲",
        "打ち身",
        "挫傷",
    ]

    POWER_IMBALANCE_INDICATORS = [
        "させる",
        "させられた",
        "してもらう",
        "してもらった",
        "してもらわないと",
        "しなければならない",
        "しなければ駄目",
        "命令",
        "指図",
        "上司",
        "部下",
        "先生",
        "生徒",
        "先輩",
        "後輩",
    ]

    def __init__(self, db_path: str = "storage/db/kaku_hegemony_v2.db"):
        self.clothing_events: List[EroticIntegrityChecker.ClothingEvent] = []
        self.quality_scorer = EroticQualityScorer()
        self.continuity_tracker = ContinuityTracker(db_path=db_path)
        self.scene_continuity_tracker = SceneContinuityTracker(db_path=db_path)

    def check_mutual_consent(self, scene_text: str) -> Tuple[bool, List[str]]:
        """簡易双方向同意チェック。両者それぞれに同意表現があるかを検証する。"""
        issues: List[str] = []

        # 全同意キーワードの出現位置を収集
        consent_positions: List[Tuple[int, str]] = []
        for kw in CONSENT_ALL_CHARACTERS_KEYWORDS:
            pos = 0
            while True:
                pos = scene_text.find(kw, pos)
                if pos == -1:
                    break
                consent_positions.append((pos, kw))
                pos += len(kw)

        if len(consent_positions) == 0:
            issues.append("両者からの同意表現が検出されませんでした")
            return False, issues

        if len(consent_positions) == 1:
            issues.append("片方からの同意表現のみが検出されました（双方向同意が成立していません）")
            return False, issues

        # 2つ以上あるが、同じ位置に密集しているかチェック
        consent_positions.sort()
        spread = (
            consent_positions[-1][0] - consent_positions[0][0] if len(consent_positions) >= 2 else 0
        )

        if spread < 50 and len(consent_positions) >= 2:
            # 同じ発話内での複数キーワード（片方だけの可能性あり）
            # 距離が短い=同じ話者の可能性が高い。少なくとも一方の同意はあるのでOKにする
            pass

        return len(issues) == 0, issues

    def check_clothing_timeline(self, scene_text: str) -> Tuple[bool, List[str]]:
        """衣服状態の時系列整合性をチェックする。"""
        issues: List[str] = []

        self._extract_clothing_events(scene_text)
        self._validate_clothing_states(issues)

        return len(issues) == 0, issues

    def _extract_clothing_events(self, scene_text: str) -> None:
        """文を解析して衣服イベントを抽出する。"""
        self.clothing_events.clear()

        sentences = []
        current_sentence = ""
        for char in scene_text:
            current_sentence += char
            if char in ["。", "！", "？", "）", "」"]:
                sentences.append(current_sentence)
                current_sentence = ""
        if current_sentence:
            sentences.append(current_sentence)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            event_type = self._detect_event_type(sentence)
            if event_type:
                phase = self._detect_phase(sentence)
                pos_in_text = scene_text.find(sentence)

                self.clothing_events.append(
                    self.ClothingEvent(event_type, pos_in_text, phase, sentence)
                )

    def _detect_event_type(self, sentence: str) -> Optional[str]:
        """文から衣服イベントを検出する。"""
        for exclude_kw in self.EXCLUDE_KEYWORDS:
            if exclude_kw in sentence:
                return None

        for verb in self.UNDRESS_VERBS:
            if verb in sentence:
                return "undress"

        for verb in self.DRESS_VERBS:
            if verb in sentence:
                return "dress"

        return None

    def _detect_phase(self, sentence: str) -> str:
        """文からフェーズを検出する。"""
        if "build" in sentence.lower():
            return "build"
        elif "peak" in sentence.lower():
            return "peak"
        elif "afterglow" in sentence.lower():
            return "afterglow"
        return "peak"

    def _validate_clothing_states(self, issues: List[str]) -> None:
        """衣服イベントの状態遷移を検証する。"""
        if len(self.clothing_events) <= 1:
            return

        sorted_events = sorted(self.clothing_events, key=lambda x: x.position)

        for i in range(len(sorted_events) - 1):
            current = sorted_events[i]
            next_event = sorted_events[i + 1]
            self._check_ordering(current, next_event, issues)

    def _check_ordering(
        self,
        current: "EroticIntegrityChecker.ClothingEvent",
        next_event: "EroticIntegrityChecker.ClothingEvent",
        issues: List[str],
    ) -> None:
        """イベント順序を検証する。"""
        if current.event_type == "dress" and next_event.event_type == "dress":
            distance = next_event.position - current.position
            if distance < 1000:
                issues.append(
                    f"着衣イベントが連続しています：'{current.text}' -> '{next_event.text}' "
                    f"({current.position}-{next_event.position})"
                )

        if current.event_type == "undress" and next_event.event_type == "undress":
            issues.append(f"脱衣イベントが連続しています：'{current.text}' -> '{next_event.text}'")

    def check_coercive_context(self, scene_text: str) -> Tuple[bool, List[str]]:
        """文脈理解に基づく強制・暴力検出を実行する。"""
        issues: List[str] = []

        self._detect_coercion_patterns(scene_text, issues)
        self._detect_violence_patterns(scene_text, issues)

        return len(issues) == 0, issues

    def _detect_coercion_patterns(self, scene_text: str, issues: List[str]) -> None:
        """拒否と継続の矛盾を検出する。"""
        refusal_positions = []
        for kw in CONSENT_REFUSAL_KEYWORDS:
            pos = 0
            while True:
                pos = scene_text.find(kw, pos)
                if pos == -1:
                    break
                refusal_positions.append((pos, kw))
                pos += len(kw)

        for pos, kw in refusal_positions:
            start_pos = max(0, pos - 200)
            end_pos = min(len(scene_text), pos + 300)
            context = scene_text[start_pos:end_pos]

            for cont_kw in CONSENT_CONTINUATION_KEYWORDS:
                if cont_kw in context:
                    issues.append(
                        f"強制的状況検出: '{kw}'表現の後に継続を示す'{cont_kw}'が検出されました"
                    )
                    break

    def _detect_violence_patterns(self, scene_text: str, issues: List[str]) -> None:
        """暴力的表現を検出する。"""
        violence_count = 0
        for kw in self.VIOLENCE_INDICATORS:
            violence_count += scene_text.count(kw)

        if violence_count >= 2:
            issues.append(
                f"暴力的表現が{violence_count}箇所検出されました（安全でない描写の可能性）"
            )

    def check_clothing_consistency(self, scene_text: str) -> Tuple[bool, List[str]]:
        """服装の整合性をチェックする。"""
        issues: List[str] = []
        undress_count = sum(scene_text.count(kw) for kw in self.UNDRESS_KEYWORDS)
        dress_count = sum(scene_text.count(kw) for kw in self.DRESS_KEYWORDS)

        if dress_count > undress_count + 1:
            issues.append("服装矛盾: 脱衣より着衣表現が多い整合性が取れません")

        return len(issues) == 0, issues

    def check_consent_state(
        self, scene_text: str, declared_consent: str = "implicit"
    ) -> Tuple[bool, List[str]]:
        """
        シーン内の同意表現是否符合 declared_consent を検証する。
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

    def check_continuity(
        self, current_ep: int, character_name: str, current_text: str, prev_text: str = ""
    ) -> ContinuityReport:
        """全ての話間整合性チェックを実行する。"""
        all_issues: List[str] = []
        checked = []

        # 単一キャラクター名、またはペア（カンマやハイフン、スラッシュ、コロン等で区切られたもの）
        chars_to_check = []
        if "," in character_name:
            chars_to_check = [c.strip() for c in character_name.split(",")]
        elif "-" in character_name:
            chars_to_check = [c.strip() for c in character_name.split("-")]
        elif ":" in character_name:
            chars_to_check = [c.strip() for c in character_name.split(":")]
        else:
            chars_to_check = [character_name]

        for char in chars_to_check:
            # 体力チェック
            all_issues.extend(
                self.continuity_tracker.check_stamina_continuity(current_ep, char, current_text)
            )
            all_issues.extend(
                self.continuity_tracker.check_recovery_description(current_ep, char, current_text)
            )
            all_issues.extend(
                self.continuity_tracker.check_stamina_jump(current_ep, char, current_text)
            )

            # 心理チェック
            all_issues.extend(
                self.continuity_tracker.check_psych_continuity(current_ep, char, current_text)
            )
            all_issues.extend(
                self.continuity_tracker.check_psych_trigger(current_ep, char, current_text)
            )
            all_issues.extend(
                self.continuity_tracker.check_psych_jump(current_ep, char, current_text)
            )

            # 衣服チェック
            all_issues.extend(
                self.continuity_tracker.check_clothing_continuity(current_ep, char, current_text)
            )

            # 場所チェック
            all_issues.extend(
                self.continuity_tracker.check_location_continuity(current_ep, char, current_text)
            )

            # 一般シーン整合性チェック
            all_issues.extend(
                self.scene_continuity_tracker.check_all_continuity(current_ep, char, current_text)
            )

        # ペア関係性チェック（2人以上のキャラクターが指定された場合）
        if len(chars_to_check) >= 2:
            # ペア表記をソートして一意にする
            pair_name = ":".join(sorted(chars_to_check))
            for char in chars_to_check:
                all_issues.extend(
                    self.continuity_tracker.check_intimacy_regression(
                        current_ep, char, current_text
                    )
                )
                all_issues.extend(
                    self.continuity_tracker.check_intimacy_rush(current_ep, char, current_text)
                )
                all_issues.extend(
                    self.continuity_tracker.check_intimacy_vs_erotic_level(
                        current_ep, char, current_text
                    )
                )

            # ペア単位の親密度チェック
            all_issues.extend(
                self.continuity_tracker.check_intimacy_regression(
                    current_ep, pair_name, current_text
                )
            )
            all_issues.extend(
                self.continuity_tracker.check_intimacy_rush(current_ep, pair_name, current_text)
            )
            all_issues.extend(
                self.continuity_tracker.check_intimacy_vs_erotic_level(
                    current_ep, pair_name, current_text
                )
            )
            checked.append("intimacy_pair")
        else:
            # 単一キャラの場合でも自己親密度（あるいはデフォルトペア）のチェックを実行
            all_issues.extend(
                self.continuity_tracker.check_intimacy_regression(
                    current_ep, character_name, current_text
                )
            )
            all_issues.extend(
                self.continuity_tracker.check_intimacy_rush(
                    current_ep, character_name, current_text
                )
            )
            all_issues.extend(
                self.continuity_tracker.check_intimacy_vs_erotic_level(
                    current_ep, character_name, current_text
                )
            )
            checked.append("intimacy_single")

        if prev_text:
            all_issues.extend(
                self.continuity_tracker.check_environment_consistency(prev_text, current_text)
            )

        checked.extend(["stamina", "psychology", "clothing", "location"])

        return ContinuityReport(
            is_consistent=len(all_issues) == 0,
            issues=all_issues,
            checked_dimensions=checked,
            character_name=character_name,
            episode_num=current_ep,
        )

    def finalize_episode(
        self, character_name: str, episode_num: int, scene_text: str
    ) -> CharacterStateSnapshot:
        """エピソード完了時にスナップショットを自動保存する。"""
        # カンマ、ハイフン、コロン等で区切られたペア名対応
        chars_to_save = []
        if "," in character_name:
            chars_to_save = [c.strip() for c in character_name.split(",")]
        elif "-" in character_name:
            chars_to_save = [c.strip() for c in character_name.split("-")]
        elif ":" in character_name:
            chars_to_save = [c.strip() for c in character_name.split(":")]
        else:
            chars_to_save = [character_name]

        last_snap = None
        for char in chars_to_save:
            # 既存のキャラクター状態スナップショットを保存
            snapshot = self.continuity_tracker.extract_snapshot(char, episode_num, scene_text)
            self.continuity_tracker.save_snapshot(snapshot)

            # 一般シーン状態スナップショットを保存
            scene_snap = self.scene_continuity_tracker.extract_snapshot(scene_text)
            # 保存用にメタデータを付与
            scene_snap.character_name = char
            scene_snap.episode_num = episode_num
            # シーン種別の判定
            scene_snap.scene_type = SceneTypeDetector().detect(scene_text)

            self.scene_continuity_tracker.save_snapshot(scene_snap)
            last_snap = snapshot

        # ペア全体としても保存
        if len(chars_to_save) >= 2:
            pair_name = ":".join(sorted(chars_to_save))
            pair_snapshot = self.continuity_tracker.extract_snapshot(
                pair_name, episode_num, scene_text
            )
            self.continuity_tracker.save_snapshot(pair_snapshot)

        return last_snap

    def check_all(
        self,
        scene_text: str,
        consent_state: str = "implicit",
        current_ep: int = 0,
        character_name: str = "",
        prev_text: str = "",
    ) -> Tuple[bool, List[str], Optional[EroticQualityReport], Optional[ContinuityReport]]:
        """
        全整合性チェックを実行し、官能品質と話間整合性も評価する。

        Returns:
            (is_safe, issues, quality_report, continuity_report)
        """
        all_issues: List[str] = []

        _, clothing_issues = self.check_clothing_timeline(scene_text)
        all_issues.extend(clothing_issues)

        _, consent_issues = self.check_consent_state(scene_text, consent_state)
        all_issues.extend(consent_issues)

        _, mutual_issues = self.check_mutual_consent(scene_text)
        all_issues.extend(mutual_issues)

        _, coercive_issues = self.check_coercive_context(scene_text)
        all_issues.extend(coercive_issues)

        quality_report = self.quality_scorer.score(scene_text) if self.quality_scorer else None

        # Continuity check（前話データと現在のエピソード番号/キャラクター名がある場合のみ）
        continuity_report = None
        if current_ep > 0 and character_name:
            continuity_report = self.check_continuity(
                current_ep, character_name, scene_text, prev_text
            )
            if continuity_report and not continuity_report.is_consistent:
                all_issues.extend(continuity_report.issues)

        return len(all_issues) == 0, all_issues, quality_report, continuity_report
