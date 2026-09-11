# VOICEVOX 標準スピーカーIDマッピング
# 3: ずんだもん(ノーマル), 2: 四国めたん(ノーマル), 8: 春日部つむぎ, 13: 青山龍星(ノーマル), 14: 冥鳴ひまり, 1: 四国めたん(あまあま)

SPEAKER_MAPPING: dict[str, int] = {
    "narration": 3,      # デフォルトナレーション: ずんだもん(ノーマル)
    "female_heroine": 2, # ヒロイン・女性主役: 四国めたん(ノーマル)
    "female_sweet": 1,   # 甘口・妹系: 四国めたん(あまあま)
    "female_energetic": 8,# 元気少女: 春日部つむぎ
    "male_protagonist": 13,# 主人公・男性: 青山龍星(ノーマル)
    "male_deep": 13,     # 重低音・悪役・老人: 青山龍星
    "other": 3,          # その他
}


def assign_speaker_id(
    speaker_name: str,
    gender: str = "female",
    role: str = "heroine",
) -> int:
    """キャラクター属性・性別・役割から最適な VOICEVOX Speaker ID を割り当てる (Step 9)。"""
    if speaker_name == "narration":
        return SPEAKER_MAPPING["narration"]

    g = gender.lower()
    r = role.lower()

    if "男" in g or g == "male":
        return SPEAKER_MAPPING["male_protagonist"]
    elif "女" in g or g == "female":
        if "妹" in r or "sweet" in r:
            return SPEAKER_MAPPING["female_sweet"]
        elif "元気" in r or "energetic" in r:
            return SPEAKER_MAPPING["female_energetic"]
        return SPEAKER_MAPPING["female_heroine"]

    return SPEAKER_MAPPING["other"]
