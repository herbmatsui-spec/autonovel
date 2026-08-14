"""
erotic/vocabulary.py - 官能・シーン分類用語��バンク
"""

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

# 戦闘シーンキー��ード
COMBAT_KEYWORDS = [
    "攻撃",
    "��撃",
    "魔法",
    "��",
    "��",
    "戦い",
    "戦闘",
    "��",
    "ダメージ",
    "負傷",
    "血",
    "切り��く",
    "撃破",
    "死闘",
    "激突",
]

# 会話シーンキー��ード
CONVERSATION_KEYWORDS = [
    "話す",
    "語る",
    "対話",
    "議論",
    "��く",
    "問う",
    "答える",
    "口調",
    "態度",
    "表情",
    "納得",
    "反論",
    "説得",
]

# ��索シーンキー��ード
EXPLORATION_KEYWORDS = [
    "調べる",
    "発見",
    "探索",
    "見つける",
    "��し",
    "����",
    "����",
    "手がかり",
    "地��",
    "路地",
    "��入",
    "��回",
]

# 移動シーンキー��ード
TRAVEL_KEYWORDS = [
    "向かう",
    "旅",
    "移動",
    "��り着く",
    "街道",
    "馬車",
    "徒歩",
    "船",
]

# 休息シーンキー��ード
REST_KEYWORDS = [
    "休む",
    "��る",
    "��る",
    "仮��",
    "休��",
    "宿",
    "ベッド",
    "布団",
    "夜",
    "朝",
    "目覚める",
]

# 独白シーンキー��ード
MONOLOGUE_KEYWORDS = [
    "思う",
    "考える",
    "振り返る",
    "自問",
    "独り言",
    "心中",
    "内心",
    "��中",
    "記��",
    "回想",
]

# ��線シーンキー��ード
FORESHADOW_KEYWORDS = [
    "予感",
    "不気味",
    "違和感",
    "何かが起こる",
    "��候",
    "前��",
    "暗示",
    "��線",
    "��",
    "不可解",
]

# 時間帯キー��ード
TIME_KEYWORDS = [
    "朝",
    "��",
    "夕方",
    "夜",
    "深夜",
    "深夜",
    "明け方",
    "時",
    "分",
    "秒",
    "時間",
    "経つ",
    "過ぎる",
]

# アイテムキー��ード
ITEM_KEYWORDS = [
    "手に入れる",
    "得る",
    "��う",
    "受け取る",
    "装備",
    "道具",
    "アイテム",
    "���",
    "書",
    "巻物",
    "��",
    "武器",
    "防具",
    "アクセサリ",
]

# 同意確認キー��ード（明示的）
EXPLICIT_CONSENT_KEYWORDS = [
    "はい",
    "お願いします",
    "欲しい",
    "もっと",
    "はい",
    "うん",
    "いいよ",
    "どうぞ",
    "受け入れる",
    "許可",
    "承諾",
    "合意",
    "了承",
    "��成",
]

# 同意確認キー��ード（暗黙的）
IMPLICIT_CONSENT_KEYWORDS = [
    "身を委ね",
    "任せ",
    "抗わない",
    "��まない",
    "受け入れ",
    "応える",
    "応じる",
    "迎える",
    "求める",
    "望む",
    "��望",
    "熱望",
    "切望",
    "身体が",
    "体が",
    "勝手に",
    "自然と",
    "無意��に",
]

# ��否・不同意キー��ード
REFUSAL_KEYWORDS = [
    "いや",
    "だめ",
    "止めて",
    "やめて",
    "��む",
    "��否",
    "嫌だ",
    "無理",
    "怖い",
    "痛い",
    "苦しい",
    "逃げ",
    "離れる",
    "放して",
    "許さない",
    "許せない",
]

# 双方向同意キー��ード
MUTUAL_CONSENT_KEYWORDS = [
    "互いに",
    "ともに",
    "お互い",
    "二人で",
    "共に",
    "分かち合",
    "共有",
    "シンクロ",
    "同調",
    "呼吸を合わせ",
    "心を通わせ",
    "��を重ね",
]

# 簡易双方向同意: 両者共通の同意表現（方向ではなく存在チェック用）
SIMPLE_MUTUAL_CONSENT_KEYWORDS = [
    "一��に",
    "共に",
    "二人で",
    "互いに",
]

# 官能品質スコアリング用キー��ード
EROTIC_QUALITY_KEYWORDS = {
    "sensory": [
        "熱",
        "温もり",
        "冷たさ",
        "��らか",
        "��さ",
        "��らか",
        "ざらつき",
        "��り",
        "��き",
        "��い",
        "香り",
        "味",
        "��",
        "��",
        "��",
        "指先",
        "��",
        "��",
        "息",
        "��息",
        "��動",
        "��",
        "震え",
        "��れ",
        "電流",
        "火照り",
        "��",
        "��",
        "����",
        "体��",
    ],
    "emotional": [
        "愛おしい",
        "愛しい",
        "切ない",
        "��しい",
        "��しい",
        "幸せ",
        "恐ろしい",
        "不安",
        "安心",
        "信頼",
        "裏切り",
        "����",
        "独占欲",
        "��着",
        "��身",
        "����",
        "許し",
        "受容",
        "共感",
        "同情",
        "��れ",
        "��敬",
        "����",
    ],
    "psychological": [
        "支配",
        "服従",
        "従��",
        "反抗",
        "��服",
        "解放",
        "束��",
        "自由",
        "罪悪感",
        "背徳",
        "禁��",
        "����",
        "��れ",
        "清らか",
        "��ら",
        "恥��",
        "��り",
        "プライド",
        "自��心",
        "自我",
        "自我����",
        "自我��失",
        "自我統合",
    ],
}

# 比��密度スコア自動調整用: シーン長����
SCENE_LENGTH_THRESHOLDS = {
    "short": 500,
    "medium": 1500,
    "long": 3000,
}

# テンション曲線段階的スコアリング用: フェーズ区切りマーカ
CURVE_PHASE_MARKERS = {
    "setup": ["始まり", "出会い", "導入", "序章", "前��"],
    "buildup": ["高まり", "��る", "熱を帯び", "近づく", "��る"],
    "climax": ["��点", "絶��", "��み", "ピーク", "爆発", "到達"],
    "afterglow": ["余��", "余熱", "静��", "��やか", "安��", "余裕", "満足", "充足"],
}

# フェーズ別スコア
PHASE_SCORES = {
    "setup": 1.0,
    "buildup": 1.5,
    "climax": 2.0,
    "afterglow": 0.8,
}

# Continuity Tracker 用定数
CONTINUITY_SCENE_TYPES = [
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

CONTINUITY_COMBAT_KEYWORDS = COMBAT_KEYWORDS
CONTINUITY_CONVERSATION_KEYWORDS = CONVERSATION_KEYWORDS
CONTINUITY_EXPLORATION_KEYWORDS = EXPLORATION_KEYWORDS
CONTINUITY_TRAVEL_KEYWORDS = TRAVEL_KEYWORDS
CONTINUITY_REST_KEYWORDS = REST_KEYWORDS
CONTINUITY_MONOLOGUE_KEYWORDS = MONOLOGUE_KEYWORDS
CONTINUITY_FORESHADOW_KEYWORDS = FORESHADOW_KEYWORDS
CONTINUITY_TIME_KEYWORDS = TIME_KEYWORDS
CONTINUITY_ITEM_KEYWORDS = ITEM_KEYWORDS
