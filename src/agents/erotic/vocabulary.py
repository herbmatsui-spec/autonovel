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
    "一緒に",
    "共に",
    "二人で",
    "互いに",
]

# 同意確認キーワード（明示的） - from erotic_integrity.py
CONSENT_EXPLICIT_KEYWORDS = ["同意", "了承", "承諾", "OK", "いいよ", "求めて", "欲しい", "させて"]
# 同意確認キーワード（暗黙的） - from erotic_integrity.py
CONSENT_IMPLICIT_KEYWORDS = [
    "促す",
    "引き寄せる",
    "唇が触れる",
    "近づく",
    "体が触れる",
    "手を伸ばす",
]
# 拒否・不同意キーワード - from erotic_integrity.py
CONSENT_REFUSAL_KEYWORDS = ["嫌", "やだ", "断る", "拒否", "抗拒", "逃げる", "拒む"]

# 簡易双方向同意: 両者共通の同意表現（方向ではなく存在チェック用） - from erotic_integrity.py
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
EROTIC_QUALITY_KEYWORDS = {
    "sensory": [
        "熱",
        "温もり",
        "冷たさ",
        "柔らか",
        "硬さ",
        "柔らか",
        "ざらつき",
        "滑り",
        "滑らか",
        "鋭い",
        "香り",
        "味",
        "唇",
        "舌",
        "歯",
        "指先",
        "爪",
        "息",
        "吐息",
        "鼓動",
        "震え",
        "震え",
        "電流",
        "火照り",
        "痺れ",
        "濡れ",
        "疼き",
        "身体",
    ],
    "emotional": [
        "愛おしい",
        "愛しい",
        "切ない",
        "甘い",
        "激しい",
        "幸せ",
        "恐ろしい",
        "不安",
        "安心",
        "信頼",
        "裏切り",
        "悲しみ",
        "独占欲",
        "執着",
        "献身",
        "許し",
        "受容",
        "共感",
        "同情",
        "憧れ",
        "尊敬",
        "永遠",
    ],
"psychological": [
        "支配",
        "服従",
        "従順",
        "反抗",
        "屈服",
        "解放",
        "束縛",
        "自由",
        "罪悪感",
        "背徳",
        "禁忌",
        "狂気",
        "涙",
        "清らか",
        "聖ら",
        "恥じ",
        "悔い",
        "プライド",
        "自尊心",
        "自我",
        "自我崩壊",
        "自我消失",
        "自我統合",
    ],
}

# ===== Continuity Tracker 用定数 =====
STAMINA_LEVELS = ["exhausted", "tired", "normal", "energetic"]
STAMINA_EXHAUSTED_KW = ["疲弊", "倒れ", "限界", "動けない", "気力が尽き", "ぐったり", "意識が遠"]
STAMINA_TIRED_KW = ["疲れ", "だるい", "重い体", "息が荒い", "汗", "消耗"]
STAMINA_ENERGETIC_KW = ["元気", "活力", "力が漲", "意気揚々", "弾む", "軽やか"]

PSYCH_STATES = ["distressed", "anxious", "neutral", "content", "euphoric"]
PSYCH_DISTRESSED_KW = ["絶望", "崩壊", "慟哭", "恐怖", "パニック", "錯乱"]
PSYCH_ANXIOUS_KW = ["不安", "怯え", "緊張", "動揺那些", "迷い", "警戒"]
PSYCH_CONTENT_KW = ["安心", "充足", "満足", "穏やか", "幸せ", "落ち着"]
PSYCH_EUPHORIC_KW = ["恍惚", "歓喜", "至福", "有頂天", "陶酔", "昂揚"]

INTIMACY_LEVELS = ["stranger", "acquaintance", "close", "intimate", "bonded"]
INTIMACY_STRANGER_KW = ["初対面", "見知らぬ", "他人", "知らない人"]
INTIMACY_CLOSE_KW = ["信頼", "心を開", "打ち解け", "絆", "友人"]
INTIMACY_INTIMATE_KW = ["肌を重ね", "身を委ね", "一つに", "深い関係", "恋人"]
INTIMACY_BONDED_KW = ["運命", "離れられ", "魂", "永远", "誓い"]

LOCATION_INDOOR_KW = ["部屋", "室内", "寝室", "浴室", "宿", "屋敷", "館", "家"]
LOCATION_OUTDOOR_KW = ["外", "森", "庭", "野原", "河", "海", "空の下", "屋外"]
LOCATION_TRANSITION_KW = ["移動", "向かう", "戻る", "出る", "入る", "到着"]

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

# 比較密度スコア自動調整用: シーン長閾値
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
