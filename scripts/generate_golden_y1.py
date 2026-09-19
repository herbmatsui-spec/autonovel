"""
Generate 32 golden samples for SubtextEngine regression tests (Step 17).
"""

import json
from pathlib import Path

GOLDEN_DIR = Path("tests/golden/subtext_before_after")
GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

test_cases = [
    # Explanatory compress (Rule 1)
    {
        "id": "case_01",
        "name": "explanatory_3_lines",
        "speaker": "宰相",
        "before": ["「敵が包囲網を敷いた」", "「兵糧もあと三日分しかない」", "「降伏するしか道はないのだ」"],
        "expected_contains": ["（", "「降伏するしか道はないのだ」"],
        "applied_rules": ["rule_01_explanatory_compress"]
    },
    {
        "id": "case_02",
        "name": "explanatory_4_lines",
        "speaker": "兵士",
        "before": ["「城門が破られました」", "「敵の先鋒が突入しています」", "「防衛線は崩壊しました」", "「もう逃げるしかありません」"],
        "expected_contains": ["（", "「もう逃げるしかありません」"],
        "applied_rules": ["rule_01_explanatory_compress"]
    },
    # Emotion to action (Rule 2)
    {
        "id": "case_03",
        "name": "emotion_sadness",
        "speaker": "リリア",
        "before": ["「私は悲しい」"],
        "expected_contains": ["悲しげな表情で、拳を握りしめ"],
        "applied_rules": ["rule_02_emotion_to_action"]
    },
    {
        "id": "case_04",
        "name": "emotion_anger",
        "speaker": "バルト",
        "before": ["「怒っているんだ」"],
        "expected_contains": ["怒気を孕んだ瞳で、テーブルを叩く"],
        "applied_rules": ["rule_02_emotion_to_action"]
    },
    {
        "id": "case_05",
        "name": "emotion_regret",
        "speaker": "剣士",
        "before": ["「悔しいよ」"],
        "expected_contains": ["奥歯を噛み締め"],
        "applied_rules": ["rule_02_emotion_to_action"]
    },
    {
        "id": "case_06",
        "name": "emotion_lonely",
        "speaker": "少女",
        "before": ["「寂しいんだ」"],
        "expected_contains": ["微かに肩を震わせ"],
        "applied_rules": ["rule_02_emotion_to_action"]
    },
    {
        "id": "case_07",
        "name": "emotion_grudge",
        "speaker": "復讐者",
        "before": ["「恨んでいる」"],
        "expected_contains": ["冷たく目を細め"],
        "applied_rules": ["rule_02_emotion_to_action"]
    },
    # Causal to irony (Rule 3)
    {
        "id": "case_08",
        "name": "causal_nazenara",
        "speaker": "賢者",
        "before": ["「なぜなら真実は闇の中だからだ」"],
        "expected_contains": ["「……"],
        "applied_rules": ["rule_03_causal_to_irony"]
    },
    {
        "id": "case_09",
        "name": "causal_riyuu",
        "speaker": "魔術師",
        "before": ["「理由は君にある」"],
        "expected_contains": ["「……"],
        "applied_rules": ["rule_03_causal_to_irony"]
    },
    # Subjective internalize (Rule 4)
    {
        "id": "case_10",
        "name": "subjective_omou",
        "speaker": "探偵",
        "before": ["「私はそう思う」"],
        "expected_contains": ["（……", "素振りを見せ"],
        "applied_rules": ["rule_04_subjective_internalize"]
    },
    {
        "id": "case_11",
        "name": "subjective_shinjiru",
        "speaker": "騎士",
        "before": ["「俺は勝利を信じている」"],
        "expected_contains": ["（……", "信じてげな素振りを見せ"],
        "applied_rules": ["rule_04_subjective_internalize"]
    },
    # Threat subtext (Rule 5)
    {
        "id": "case_12",
        "name": "threat_kill",
        "speaker": "暗殺者",
        "before": ["「絶対に殺してやる」"],
        "expected_contains": ["——"],
        "applied_rules": ["rule_05_threat_subtext"]
    },
    {
        "id": "case_13",
        "name": "threat_crush",
        "speaker": "巨漢",
        "before": ["「貴様を潰すぞ」"],
        "expected_contains": ["——"],
        "applied_rules": ["rule_05_threat_subtext"]
    },
    {
        "id": "case_14",
        "name": "threat_forgive_not",
        "speaker": "伯爵",
        "before": ["「貴様だけは許さない」"],
        "expected_contains": ["——"],
        "applied_rules": ["rule_05_threat_subtext"]
    },
    # Compliance subvert (Rule 6)
    {
        "id": "case_15",
        "name": "compliance_hai",
        "speaker": "従僕",
        "before": ["「はい」"],
        "expected_any": ["仰せのままに", "無言のまま"],
        "applied_rules": ["rule_06_compliance_subvert"]
    },
    {
        "id": "case_16",
        "name": "compliance_wakarimashita",
        "speaker": "秘書",
        "before": ["「わかりました」"],
        "expected_any": ["仰せのままに", "無言のまま"],
        "applied_rules": ["rule_06_compliance_subvert"]
    },
    {
        "id": "case_17",
        "name": "compliance_shouchi",
        "speaker": "武官",
        "before": ["「承知しました」"],
        "expected_any": ["仰せのままに", "無言のまま"],
        "applied_rules": ["rule_06_compliance_subvert"]
    },
    # Address distance (Rule 7)
    {
        "id": "case_18",
        "name": "address_hostile",
        "speaker": "ライバル",
        "before": ["「お前、覚悟しろ」"],
        "context": {"relationship": "enemy"},
        "expected_contains": ["貴方"],
        "applied_rules": ["rule_07_address_distance"]
    },
    {
        "id": "case_19",
        "name": "address_former_ally",
        "speaker": "裏切り者",
        "before": ["「君、もう終わりだ」"],
        "context": {"relationship": "former_ally"},
        "expected_contains": ["貴方"],
        "applied_rules": ["rule_07_address_distance"]
    },
    # Extension rules (Rules 8-15)
    {
        "id": "case_20",
        "name": "ext_apology_1",
        "speaker": "妹",
        "before": ["「ごめんなさい」"],
        "expected_contains": ["「……謝られても、何も戻らない」"],
        "applied_rules": ["rule_08_apology_deflection"]
    },
    {
        "id": "case_21",
        "name": "ext_apology_2",
        "speaker": "友人",
        "before": ["「申し訳ありません」"],
        "expected_contains": ["「……謝られても、何も戻らない」"],
        "applied_rules": ["rule_08_apology_deflection"]
    },
    {
        "id": "case_22",
        "name": "ext_hesitation_a",
        "speaker": "少年",
        "before": ["「あっ、あっ」"],
        "expected_contains": ["（息を詰まらせ、喉をかすかに震わせる）"],
        "applied_rules": ["rule_09_hesitation_stutter"]
    },
    {
        "id": "case_23",
        "name": "ext_hesitation_e",
        "speaker": "少女",
        "before": ["「えっ、えっ」"],
        "expected_contains": ["（息を詰まらせ、喉をかすかに震わせる）"],
        "applied_rules": ["rule_09_hesitation_stutter"]
    },
    {
        "id": "case_24",
        "name": "ext_secret_whisper",
        "speaker": "情報屋",
        "before": ["「ここだけの話だけど」"],
        "expected_contains": ["「……壁に耳があるわ」"],
        "applied_rules": ["rule_10_secretive_whisper"]
    },
    {
        "id": "case_25",
        "name": "ext_rhetorical_evasion",
        "speaker": "怪盗",
        "before": ["「どうしてそんなことを聞くの？」"],
        "expected_contains": ["「……それを知って、どうするつもり？」"],
        "applied_rules": ["rule_11_rhetorical_evasion"]
    },
    {
        "id": "case_26",
        "name": "ext_condescending_polite",
        "speaker": "貴族令嬢",
        "before": ["「ご親切にどうも」"],
        "expected_contains": ["「……余計なお気遣い、感服いたしますわ」"],
        "applied_rules": ["rule_12_condescending_politeness"]
    },
    {
        "id": "case_27",
        "name": "ext_gaze_aversion",
        "speaker": "ツンデレ",
        "before": ["「見ないでよ！」"],
        "expected_contains": ["（咄嗟に顔を背け、手の甲で表情を隠す）"],
        "applied_rules": ["rule_13_gaze_aversion"]
    },
    {
        "id": "case_28",
        "name": "ext_monologue_cutoff",
        "speaker": "独白キャラ",
        "before": ["「独り言さ」"],
        "expected_contains": ["「……なんでもない。忘れて」"],
        "applied_rules": ["rule_14_monologue_cutoff"]
    },
    {
        "id": "case_29",
        "name": "ext_unspoken_tension",
        "speaker": "用心棒",
        "before": ["「言いたいことはそれだけか？」"],
        "expected_contains": ["「……それ以上は、お互いのためにならない」"],
        "applied_rules": ["rule_15_unspoken_tension"]
    },
    # Unmodified edge cases (Negative cases)
    {
        "id": "case_30",
        "name": "negative_normal_narration",
        "speaker": "",
        "before": ["風が静かに吹き抜けていった。"],
        "expected_contains": ["風が静かに吹き抜けていった。"],
        "applied_rules": []
    },
    {
        "id": "case_31",
        "name": "negative_sadness_negated",
        "speaker": "勇者",
        "before": ["「別に悲しくない」"],
        "expected_contains": ["「別に悲しくない」"],
        "applied_rules": []
    },
    {
        "id": "case_32",
        "name": "negative_short_dialogue",
        "speaker": "通行人",
        "before": ["「こんにちは」", "「良いお天気ですね」"],
        "expected_contains": ["「こんにちは」", "「良いお天気ですね」"],
        "applied_rules": []
    },
]

for tc in test_cases:
    fp = GOLDEN_DIR / f"{tc['id']}.json"
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(tc, f, ensure_ascii=False, indent=2)

print(f"Generated {len(test_cases)} golden samples in {GOLDEN_DIR}")
