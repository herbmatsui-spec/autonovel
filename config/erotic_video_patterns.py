"""
config/erotic_video_patterns.py
エロ動画の映像パターンを文学技法に変換するマッピング定義。

Fanza等の動画を参考にした「映像パターン → 文学技法」の変換テーブル。
"""
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class VideoPattern:
    """映像パターンの定義。"""

    name: str
    description: str
    literary_technique: str
    example: str
    recommended_intensity: int
    sensory_focus: List[str]
    metaphor_hints: List[str]


VIDEO_PATTERNS: Dict[str, VideoPattern] = {
    "closeup": VideoPattern(
        name="接写",
        description="局部や表情のクローズアップ。カメラが肌に近づく。",
        literary_technique="部分描写の強調・感覚の細部への焦点。身体を部分的に拡大描写し、読者の目を誘導する。",
        example="汗ばむ首筋の起伏、鎖骨の影、髪の一筋が額にかかる様子、耳垂の微かな红潮",
        recommended_intensity=3,
        sensory_focus=["touch", "gaze", "scent"],
        metaphor_hints=[
            "汗の雫が光を反射する表面",
            "肌の纹理が顕微鏡的に見える距離",
            "髪が羽毛のように肌を撫でる感触",
        ],
    ),
    "pov": VideoPattern(
        name="POV視点",
        description="主観視点で相手を見る。，观众が当事人になったような臨場感。",
        literary_technique="「見る」の主体の明確化・視線の流向描写。自己と相手の境界を曖昧にする。",
        example="见上げる視線が天井に突き刺さる、指先が返す锁骨の輪郭をなぞる視線",
        recommended_intensity=3,
        sensory_focus=["gaze", "touch", "breath"],
        metaphor_hints=[
            "視線が触れるだけで肌が焦げる",
            "对方的視線が肌に刻まれる",
            "視線の重さで肌が窪む感覚",
        ],
    ),
    "position_change": VideoPattern(
        name="体位変化",
        description="位置・角度の変化。カメラアングルが変わるたびに二人の関係が再定義される。",
        literary_technique="空間の三次元描写・重心の移動。位置関係を明確にしながら動的な緊張を生み出す。",
        example="浮き上がる腰、変わる重心、崩れる平衡、倒れ込む布団の柔らかさ",
        recommended_intensity=3,
        sensory_focus=["touch", "gaze", "breath"],
        metaphor_hints=[
            "重心が移動するたびに空気が変わる",
            "位置が入れ替わる瞬間の inúmer",
            "体の軸が傾くきの力学",
        ],
    ),
    "rhythm": VideoPattern(
        name="リズム編集",
        description="テンポの変化（速→遅→速）。編集のテンポが官能性を増大させる。",
        literary_technique="文の長さ・テンポの変動。短文と長文を交互させて読解のリズムを制御する。",
        example="短文:「動かないで」/ 長文:「その声は影の形に溶け落ちて、世界の縁をぼやけさせた」",
        recommended_intensity=2,
        sensory_focus=["breath", "sound", "touch"],
        metaphor_hints=[
            "テンポが落ちるたびに空気が重くなる",
            "息が止まるほどの沈黙",
            "节奏が崩れるときの解放感",
        ],
    ),
    "sound_focus": VideoPattern(
        name="音強調",
        description="喘ぎ声や体音の強調。聞こえてくる音に意識が集中する。",
        literary_technique="擬音・擬態語の増量、呼吸の音声化。音韵のリズムで官能性を表現する。",
        example="荒い息が耳に刺さる、肌が擦れる音、汗が滴る音、心臓の鼓動が頭の中で反響する",
        recommended_intensity=2,
        sensory_focus=["sound", "breath", "touch"],
        metaphor_hints=[
            "呼吸が耳の奥で反響する",
            "心跳が鼓膜を揺らす",
            "吐息の温度が耳を焼く",
        ],
    ),
    "tension_release": VideoPattern(
        name="緊張と解放",
        description="溜め→一気放出。最も基本的なエロティシズムの構造。",
        literary_technique="クscale=ド、痛苦の期間の強調。解放の瞬間の感情的な落差を描く。",
        example="抗うことすら忘れてしまう瞬間、意識が白く染まる解放感、一瞬の黑暗中での勝手な行动",
        recommended_intensity=4,
        sensory_focus=["breath", "touch", "sound"],
        metaphor_hints=[
            "堰を切った以上の洪水",
            "張り詰めた弦が切れる瞬間",
            "抗う最後の意思が溶ける",
        ],
    ),
    "multi_angle": VideoPattern(
        name="多角撮影",
        description="複数の視点からの描写。立体的な空間把握が可能になる。",
        literary_technique="三次元空間での位置関係の明確化。視点を切り替えながら空間を描写する。",
        example="二人の影が壁面で重なる角度、窓から差し込む光が二人の輪郭を照らす位置、枕元の-configuration",
        recommended_intensity=2,
        sensory_focus=["gaze", "touch", "scent"],
        metaphor_hints=[
            "影が重なる角度が問題を解く",
            "光と影の境界線が曖昧になる",
            "三次元空間での位置の特定",
        ],
    ),
    "slow_motion": VideoPattern(
        name="スロー再生",
        description="瞬間を長く引き伸ばす。slow motion で情感が增幅される。",
        literary_technique="瞬間描写の多重展開・感覚の拡張。一瞬の出来事を详细に分解して描く。",
        example="触れる指の先が肌に触れる一秒が永遠に広がる、瞳が見開かれる势いの Slow、分析的な思考の停止",
        recommended_intensity=4,
        sensory_focus=["touch", "gaze", "breath"],
        metaphor_hints=[
            "時間が溶け合うほどの濃密",
            "一秒が永遠に膨胀する",
            "瞬間を细分化して描く永遠",
        ],
    ),
    "fade_transition": VideoPattern(
        name="フェード遷移",
        description="場面の切り替わり。時間経過や場所移動を暗示する。",
        literary_technique="場面の省略と暗示。直接的描写を避け读者的想像に委ねる。",
        example="意識が遠のく瞬間、暗転を境にした別の段階、光が戻る頃には変わっていた関係",
        recommended_intensity=2,
        sensory_focus=["gaze", "scent", "touch"],
        metaphor_hints=[
            "意識の境界が曖昧になる",
            "光が戻る頃には别人になっていた",
            "記憶の途切れる箇所がある",
        ],
    ),
    "液体_focus": VideoPattern(
        name="液体focus",
        description="汗・涙・体液の強調。润滑や湿润の視覚的強調。",
        literary_technique="湿潤感の直接的描写。触感描写に水分・体温・润滑の要素を組み込む。",
        example="汗ばむ肌の张り、愛液の润滑、涙の盐け、汗で髪が额に張り付いた风景",
        recommended_intensity=4,
        sensory_focus=["touch", "scent", "breath"],
        metaphor_hints=[
            "汗の薄膜が光を反射する",
            "润滑による润滑らかな滑り",
            "湿った髪が肌に贴着する重さ",
        ],
    ),
    "temperature_focus": VideoPattern(
        name="温度変化",
        description="体温・環境温度の差異の強調。温度 контрастが感覚を鋭くする。",
        literary_technique="温度差の詩的描写。的火照りと冷却、暖和と寒冷の对比を描く。",
        example="火照る肌を冷ます空気が心地よい、互いの体温が混ざり合う热さ、汗の蒸发する冷たさ",
        recommended_intensity=3,
        sensory_focus=["touch", "scent", "breath"],
        metaphor_hints=[
            "体温差が消える融合",
            "火照った肌が冷気に晒される",
            "热の移动が意识に上げる",
        ],
    ),
    "breath_sync": VideoPattern(
        name="呼吸同期",
        description="二人の呼吸が一つになる描写。身体的なSynchronization。",
        literary_technique="呼吸のリズム同步。息遣いのペースが心理状態を反映する。",
        example="相手の呼吸に応えるように自らの息が深くなる、两人的の呼吸が同じリズムになる平衡",
        recommended_intensity=3,
        sensory_focus=["breath", "sound", "touch"],
        metaphor_hints=[
            "呼吸が波のように同期する",
            "息の先が触れ合う距离",
            "呼吸のリズムが一つに溶ける",
        ],
    ),
    "penetration_pointe": VideoPattern(
        name="侵入の瞬間の詩学",
        description="境界の侵犯の象征的描写。化学的な意味ではなく精神的な意味での侵入。",
        literary_technique="境界侵犯のメタファー。的个人空間の侵犯、信頼の突破を描く。",
        example="急ところを開ける感覚、抵抗していた身体が迎える瞬間、可能性の扉が開く感覚",
        recommended_intensity=5,
        sensory_focus=["touch", "breath", "gaze"],
        metaphor_hints=[
            "境界を侵犯する快感",
            "封印されていたものの開放",
            "抵抗の逆説的な解除",
        ],
    ),
    "aftercare_close": VideoPattern(
        name="事後のはどこに寄りそう描写",
        description="行為後の密切的な接触。タオル回し、髪を梳く等活动の描写。",
        literary_technique="日常的な密切行為の诗的描写。行為の前後にある自然な接触を描く。",
        example="髪を梳く指先の温柔、汗を拭うタオルの感触、寄り添う肌の温度",
        recommended_intensity=2,
        sensory_focus=["touch", "gaze", "scent"],
        metaphor_hints=[
            "日常の所作に溶ける官能",
            "行為の後でも続く繋がり",
            "亲密な邻接地帯の描写",
        ],
    ),
    "mirror_scene": VideoPattern(
        name="鏡映描写",
        description="鏡に映る自分の表情や二人の姿。自我の確認と変容のsymbol。",
        literary_technique="鏡像による自我の对象化。自分自身の姿を客观視する瞬間の発見。",
        example="鏡に映る真っ赤な自分の顔、汗ばむ肌に浮かぶ表情、二人の姿が鏡に映る角度",
        recommended_intensity=3,
        sensory_focus=["gaze", "touch"],
        metaphor_hints=[
            "鏡の中の自分が異様に見える",
            "映し出される雰囲 seringkい",
            "自己の_Objectificationによる気まずさ",
        ],
    ),
}


def get_pattern(name: str) -> Optional[VideoPattern]:
    """指定された名前のパターン情報を返す。"""
    return VIDEO_PATTERNS.get(name)


def get_patterns_for_intensity(intensity: int) -> List[VideoPattern]:
    """指定された強度适用的パターンをすべて返す。"""
    return [p for p in VIDEO_PATTERNS.values() if p.recommended_intensity <= intensity]


def get_patterns_by_sensory_focus(sense: str, min_intensity: int = 0) -> List[VideoPattern]:
    """指定された感覚に関連するパターンを返す。"""
    return [
        p
        for p in VIDEO_PATTERNS.values()
        if sense in p.sensory_focus and p.recommended_intensity >= min_intensity
    ]


def get_literary_instructions_for_pattern(pattern_name: str, params: Optional[Dict] = None) -> str:
    """指定されたパターンの文学的指示を生成する。

    Args:
        pattern_name: パターン名
        params: オプションのパラメータ辞書

    Returns:
        プロンプトに挿入する文学的指示テキスト
    """
    pattern = get_pattern(pattern_name)
    if not pattern:
        return ""

    lines = [
        f"【{pattern.name}】",
        pattern.description,
        "",
        "【文学技法】",
        pattern.literary_technique,
        "",
        "【例】",
        pattern.example,
    ]

    if params and params.get("include_hints", False):
        lines.append("")
        lines.append("【比喩の手がかり】")
        for hint in pattern.metaphor_hints:
            lines.append(f"  - {hint}")

    return "\n".join(lines)


def get_all_pattern_instructions(enabled_patterns: List[str], params: Optional[Dict] = None) -> str:
    """有効なパターンのすべての指示を連結して返す。"""
    if not enabled_patterns:
        return ""

    sections = []
    for pattern_name in enabled_patterns:
        instruction = get_literary_instructions_for_pattern(pattern_name, params)
        if instruction:
            sections.append(instruction)

    return "\n".join([""] + sections + [""])
