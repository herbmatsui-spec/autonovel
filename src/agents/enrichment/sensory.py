# src/agents/enrichment/sensory.py
"""感覚拡充モジュール: 抽象的感情描写を五感ベースの具体描写に変換"""
from __future__ import annotations

import re
from typing import Any
from dataclasses import dataclass


@dataclass
class EmotionSpan:
    """検出された抽象的感情フレーズ"""
    start: int
    end: int
    emotion: str
    intensity: float
    abstract_phrase: str


# 感情→感覚マッピング（6基本感情 × 5感覚）
EMOTION_TO_SENSORY_MAP = {
    "sadness": {
        "visual": ["涙がこぼれる", "視界が滲む", "世界が灰色に見える", "俯いた顔", "震える肩"],
        "auditory": ["静寂が耳に痛い", "遠くの音がかすかに聞こえる", "自分の鼓動だけが響く", "嗚咽が漏れる"],
        "tactile": ["頬を伝う冷たい涙", "指先が冷たくなる", "胸が締め付けられる", "体が重く沈む", "手のひらの汗"],
        "olfactory": ["雨の匂い", "古い紙の匂い", "病院の消毒液の匂い", "焚き火の残り香"],
        "gustatory": ["口の中の塩味", "苦い渋み", "渇いた喉", "鉄の味"],
    },
    "anger": {
        "visual": ["視界が赤く染まる", "拳が白くなるまで握りしめる", "相手を睨みつける", "血管が浮き出る"],
        "auditory": ["低く唸る声", "歯ぎしりの音", "拳で壁を叩く音", "荒い呼吸音", "静寂を裂く怒号"],
        "tactile": ["熱が顔に上る", "掌に爪が食い込む痛み", "体中が震える", "血管が脈打つ感覚", "汗が滲む"],
        "olfactory": ["鉄の匂い", "火薬の匂い", "汗の酸っぱい匂い", "燃えるような匂い"],
        "gustatory": ["口の中の銅の味", "噛み締めた歯の痛み", "苦い唾液"],
    },
    "fear": {
        "visual": ["瞳孔が開く", "周囲が歪んで見える", "影が怪物に見える", "逃げ場を探す視線"],
        "auditory": ["耳鳴りがする", "自分の心音がうるさい", "足音が近づく", "喉が鳴る音", "静寂の中の異音"],
        "tactile": ["冷や汗が背中を伝う", "手足が冷たくなる", "体が強ばる", "呼吸が浅くなる", "膝が笑う"],
        "olfactory": ["乾いた土の匂い", "錆びた鉄の匂い", "古い埃の匂い", "自分の汗の匂い"],
        "gustatory": ["口が渇く", "酸っぱい唾液", "砂を噛んだような感覚"],
    },
    "joy": {
        "visual": ["頬が緩む", "目尻が下がる", "世界が輝いて見える", "光が舞うように見える"],
        "auditory": ["心弾む足取り", "笑い声が響く", "心地よい風の音", "好きな曲が聞こえる"],
        "tactile": ["温かい陽射し", "軽やかな体", "握りしめた手の温もり", "風が頬を撫でる"],
        "olfactory": ["花の香り", "青空の匂い", "焼きたてのパンの香り", "雨上がりの土の香り"],
        "gustatory": ["甘い果実の味", "冷たい水の美味しさ", "幸せの味"],
    },
    "surprise": {
        "visual": ["目を見開く", "息を呑む", "時間が止まったように見える", "予想外の光景"],
        "auditory": ["心臓が一瞬止まる", "静寂が訪れる", "予期せぬ音", "自分の声が裏返る"],
        "tactile": ["電流が走る", "鳥肌が立つ", "体が弾む", "手が勝手に動く"],
        "olfactory": ["突風が運ぶ匂い", "オゾンの匂い", "突然の香り"],
        "gustatory": ["息を呑んだ瞬間の味", "乾いた喉"],
    },
    "disgust": {
        "visual": ["眉をひそめる", "顔を背ける", "汚いものを見る目", "唇を歪める"],
        "auditory": ["吐き気を催す音", "不快な湿った音", "耳を塞ぎたくなる音"],
        "tactile": ["鳥肌が立つ", "汚れが触れた感覚", "ねばつく感触", "体が強ばる"],
        "olfactory": ["腐敗臭", "化学薬品の匂い", "生ゴミの匂い", "カビの匂い"],
        "gustatory": ["吐き気", "苦い液が込み上げる", "舌が痺れる", "最悪の味"],
    },
}


# 抽象的感情表現の検出パターン
ABSTRACT_EMOTION_PATTERNS = {
    "sadness": [
        r"悲し(?:い|み|かった|みたい)", r"哀し(?:い|み|かった)", r"泣きたい", r"涙が出(?:る|た)", r"胸が締め付けられ",
        r"心が痛(?:い|む)", r"虚し(?:い|さ)", r"絶望", r"失望", r"嘆き", r"落ち込(?:み|んだ)",
    ],
    "anger": [
        r"怒り", r"腹が立(?:つ|った)", r"ムカつ(?:く|いた)", r"イライラ", r"激怒", r"憤慨",
        r"堪えられな(?:い)", r"許せな(?:い)", r"腹の虫が治らない", r"カッとな(?:る|った)",
    ],
    "fear": [
        r"恐ろし(?:い)", r"怖(?:い|がった)", r"恐怖", r"戦慄", r"怯え", r"おびえ",
        r"背筋が凍る", r"血の気が引く", r"逃げ出した(?:い)", r"震えが止まらな(?:い)",
    ],
    "joy": [
        r"嬉し(?:い)", r"喜び", r"幸せ", r"歓喜", r"至福", r"笑顔", r"喜ん(?:だ|で)",
        r"心が弾(?:む|んだ)", r"最高", r"夢のよう", r"感激",
    ],
    "surprise": [
        r"驚(?:き|いた)", r"衝撃", r"呆然", r"目を見開", r"息を呑", r"信じられな(?:い)",
        r"予想外", r"意外", r"まさか", r"吃驚",
    ],
    "disgust": [
        r"嫌悪", r"吐き気", r"不快", r"気持ち悪(?:い)", r"ぞっとする", r"鳥肌",
        r"受け付けな(?:い)", r"生理的に無理", r"吐きそう",
    ],
}


def detect_abstract_emotions(text: str) -> list[EmotionSpan]:
    """テキストから抽象的感情フレーズを検出"""
    spans = []
    
    for emotion, patterns in ABSTRACT_EMOTION_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                match_start = match.start()
                match_end = match.end()
                
                # 文脈を含めて少し広めに取得（フレーズ用）
                start = max(0, match_start - 10)
                end = min(len(text), match_end + 10)
                phrase = text[start:end].strip()
                
                # 既に検出済みの範囲と重複しないかチェック（マッチ位置ベースで判定）
                overlap = False
                for s in spans:
                    if not (match_end <= s.start or match_start >= s.end):
                        overlap = True
                        break
                
                if not overlap:
                    spans.append(EmotionSpan(
                        start=match_start,
                        end=match_end,
                        emotion=emotion,
                        intensity=0.7,  # デフォルト強度
                        abstract_phrase=phrase,
                    ))
    
    # 位置でソート
    spans.sort(key=lambda x: x.start)
    return spans


def generate_sensory_details(
    emotion_span: EmotionSpan,
    scene_context: str,
    pov: str = "third_person",
    llm: Any = None,
    prompt_manager: Any = None,
) -> list[str]:
    """感覚詳細生成（LLM使用時は高品質、未使用時はテンプレートベース）"""
    emotion = emotion_span.emotion
    sensory_map = EMOTION_TO_SENSORY_MAP.get(emotion, {})
    
    # 文脈から感覚を選択（キーワードマッチング）
    selected_senses = []
    context_lower = scene_context.lower()
    
    # シーン文脈に基づく感覚優先度
    sense_priority = []
    if any(kw in context_lower for kw in ["雨", "水", "川", "海", "湖", "濡れ"]):
        sense_priority.extend(["tactile", "auditory", "olfactory"])
    if any(kw in context_lower for kw in ["火", "炎", "焼", "熱", "暑"]):
        sense_priority.extend(["tactile", "visual", "olfactory"])
    if any(kw in context_lower for kw in ["暗", "夜", "影", "闇", "薄暗"]):
        sense_priority.extend(["visual", "auditory", "tactile"])
    if any(kw in context_lower for kw in ["風", "空", "外", "野原", "森"]):
        sense_priority.extend(["tactile", "olfactory", "auditory"])
    if any(kw in context_lower for kw in ["部屋", "室内", "ベッド", "椅子", "机"]):
        sense_priority.extend(["tactile", "visual", "olfactory"])
    
    # デフォルト優先度
    if not sense_priority:
        sense_priority = ["visual", "auditory", "tactile", "olfactory", "gustatory"]
    
    # 重複除去しつつ最大3感覚まで
    seen = set()
    for sense in sense_priority:
        if sense not in seen and sense in sensory_map and sensory_map[sense]:
            seen.add(sense)
            selected_senses.append(sense)
            if len(selected_senses) >= 3:
                break
    
    # 感覚描写生成
    sensory_details = []
    for sense in selected_senses:
        options = sensory_map[sense]
        # 文脈に合いそうなものを選択（簡易: 最初のもの）
        detail = options[0]
        sensory_details.append(f"[{sense}] {detail}")
    
    # LLM がある場合はより文脈に沿った生成を試みる（将来拡張用）
    if llm and prompt_manager:
        pass  # TODO: LLMベース生成
    
    return sensory_details


def replace_with_sensory_expansion(
    text: str,
    emotion_spans: list[EmotionSpan],
    sensory_details_list: list[list[str]],
) -> tuple[str, list[dict]]:
    """抽象フレーズを感覚展開版で置換"""
    if not emotion_spans:
        return text, []
    
    # 後ろから置換（位置ズレ防止）
    sorted_spans = sorted(zip(emotion_spans, sensory_details_list), 
                          key=lambda x: x[0].start, reverse=True)
    
    enriched_text = text
    expansions_meta = []
    
    for span, details in sorted_spans:
        # 元のフレーズ
        original = text[span.start:span.end]
        
        # 感覚詳細を自然な文に組み立て
        if details:
            # 視点に応じた主語調整
            pov_subject = "彼" if "彼" in text[max(0, span.start-20):span.start] else \
                          "彼女" if "彼女" in text[max(0, span.start-20):span.start] else \
                          "私" if "私" in text[max(0, span.start-20):span.start] else "彼"
            
            expanded_parts = []
            for d in details:
                # [visual] 涙がこぼれる -> 視覚: 涙がこぼれる
                sense_tag, desc = d.split("] ", 1) if "] " in d else (d, d)
                sense = sense_tag.strip("[]")
                expanded_parts.append(f"{desc}。")
            
            expanded = "".join(expanded_parts)
        else:
            expanded = original
        
        # 置換実行
        enriched_text = enriched_text[:span.start] + expanded + enriched_text[span.end:]
        
        expansions_meta.append({
            "original_phrase": original,
            "expanded_text": expanded,
            "emotion": span.emotion,
            "senses_covered": [d.split("]")[0].strip("[") for d in details if "]" in d],
            "position": span.start,
        })
    
    # メタデータを元の順序（位置昇順）に戻す
    expansions_meta.reverse()
    
    return enriched_text, expansions_meta


def expand_sensory_details_pipeline(
    text: str,
    scene_context: str = "",
    pov: str = "third_person",
    llm: Any = None,
    prompt_manager: Any = None,
) -> tuple[str, list[dict]]:
    """感覚拡充パイプライン（エントリーポイント）"""
    # 1. 抽象感情検出
    emotion_spans = detect_abstract_emotions(text)
    
    if not emotion_spans:
        return text, []
    
    # 2. 各感情に対する感覚詳細生成
    all_sensory_details = []
    for span in emotion_spans:
        details = generate_sensory_details(span, scene_context, pov, llm, prompt_manager)
        all_sensory_details.append(details)
    
    # 3. 置換実行
    enriched_text, expansions_meta = replace_with_sensory_expansion(
        text, emotion_spans, all_sensory_details
    )
    
    return enriched_text, expansions_meta