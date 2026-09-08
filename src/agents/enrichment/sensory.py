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
    sentence_start: int = 0
    sentence_end: int = 0
    sentence_text: str = ""
    trailing_conjunction: str = ""


# 接続助詞パターン（Step 26: 感情語直後の文脈接続保護）
CONJUNCTION_PATTERNS = [
    r"^(?:だが|けれど(?:も)?|ものの|なので|ので|だから|から|ため|ながら|でも|が、|が)",
]


def extract_sentence_span(text: str, match_start: int, match_end: int) -> tuple[int, int, str]:
    """感情語を含む文全体の開始位置、終了位置、文テキストを抽出する（Step 25）"""
    # 直前の句読点または文頭を探す
    start = 0
    for delim in ["。", "！", "？", "\n"]:
        pos = text.rfind(delim, 0, match_start)
        if pos != -1 and (pos + 1) > start:
            start = pos + 1

    # 直後の句読点または文末を探す
    end = len(text)
    for delim in ["。", "！", "？", "\n"]:
        pos = text.find(delim, match_end)
        if pos != -1 and (pos + 1) < end:
            end = pos + 1

    sentence = text[start:end].strip()
    return start, end, sentence


def detect_trailing_conjunction(text: str, match_end: int) -> str:
    """感情語の直後に続く接続助詞を検知する（Step 26）"""
    trailing_sub = text[match_end:match_end + 15]
    for pat in CONJUNCTION_PATTERNS:
        m = re.search(pat, trailing_sub)
        if m:
            return m.group(0)
    return ""


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
        r"悲し(?:い|み|かった|みたい|く)", r"哀し(?:い|み|かった|く)", r"泣きたい", r"涙が出(?:る|た)", r"胸が締め付けられ",
        r"心が痛(?:い|む|んだ)", r"虚し(?:い|さ|く)", r"絶望", r"失望", r"嘆き", r"落ち込(?:み|んだ)",
    ],
    "anger": [
        r"怒り", r"腹が立(?:つ|った)", r"ムカつ(?:く|いた)", r"イライラ", r"激怒", r"憤慨",
        r"堪えられな(?:い)", r"許せな(?:い)", r"腹の虫が治らない", r"カッとな(?:る|った)",
        r"悔し(?:い|さ|かった|く)",
    ],
    "fear": [
        r"恐ろし(?:い|さ|く|かった)", r"怖(?:い|がった|く|さ)", r"恐怖", r"戦慄", r"怯え", r"おびえ",
        r"背筋が凍る", r"血の気が引く", r"逃げ出した(?:い)", r"震えが止まらな(?:い)",
    ],
    "joy": [
        r"嬉し(?:い|さ|く|かった)", r"喜び", r"幸せ", r"歓喜", r"至福", r"笑顔", r"喜ん(?:だ|で)",
        r"心が弾(?:む|んだ)", r"最高", r"夢のよう", r"感激",
    ],
    "surprise": [
        r"驚(?:き|いた)", r"衝撃", r"呆然", r"目を見開", r"息を呑", r"信じられな(?:い)",
        r"予想外", r"意外", r"まさか", r"吃驚",
    ],
    "disgust": [
        r"嫌悪", r"吐き気", r"不快", r"気持ち悪(?:い|さ|く|かった)", r"ぞっとする", r"鳥肌",
        r"受け付けな(?:い)", r"生理的に無理", r"吐きそう",
    ],
}


def is_inside_dialogue(text: str, pos: int) -> bool:
    """指定された位置が会話文（「」または『』の中）にあるかを判定（Step 32）"""
    open_count = 0
    double_open_count = 0
    for char in text[:pos]:
        if char == "「":
            open_count += 1
        elif char == "」":
            open_count = max(0, open_count - 1)
        elif char == "『":
            double_open_count += 1
        elif char == "』":
            double_open_count = max(0, double_open_count - 1)
    return open_count > 0 or double_open_count > 0


def detect_abstract_emotions(text: str, skip_dialogue: bool = True) -> list[EmotionSpan]:
    """テキストから抽象的感情フレーズを検出（Step 32: 会話文内部保護ガード対応）"""
    spans = []
    
    for emotion, patterns in ABSTRACT_EMOTION_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                match_start = match.start()
                match_end = match.end()
                
                # Step 32: セリフ内の感情表現を地の文の五感描写に置換しないようスキップ
                if skip_dialogue and is_inside_dialogue(text, match_start):
                    continue
                
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
                    s_start, s_end, s_text = extract_sentence_span(text, match_start, match_end)
                    conj = detect_trailing_conjunction(text, match_end)
                    spans.append(EmotionSpan(
                        start=match_start,
                        end=match_end,
                        emotion=emotion,
                        intensity=0.7,  # デフォルト強度
                        abstract_phrase=phrase,
                        sentence_start=s_start,
                        sentence_end=s_end,
                        sentence_text=s_text,
                        trailing_conjunction=conj,
                    ))
    
    # 位置でソート
    spans.sort(key=lambda x: x.start)
    return spans


async def _call_llm_async(llm: Any, prompt: str) -> str:
    """同期・非同期の各種LLMインターフェース（generate, ainvoke, agenerate, call）を統一して非同期実行"""
    import inspect
    if hasattr(llm, "generate"):
        res = llm.generate(prompt)
        if inspect.isawaitable(res):
            res = await res
        return getattr(res, "content", res) if not isinstance(res, str) else res
    elif hasattr(llm, "ainvoke"):
        res = llm.ainvoke(prompt)
        if inspect.isawaitable(res):
            res = await res
        return getattr(res, "content", res) if not isinstance(res, str) else res
    elif hasattr(llm, "agenerate"):
        res = llm.agenerate(prompt)
        if inspect.isawaitable(res):
            res = await res
        return getattr(res, "content", res) if not isinstance(res, str) else res
    elif callable(llm):
        res = llm(prompt)
        if inspect.isawaitable(res):
            res = await res
        return getattr(res, "content", res) if not isinstance(res, str) else res
    else:
        raise TypeError(f"Unsupported LLM object type: {type(llm)}")


def _fallback_sensory_details(
    emotion_span: EmotionSpan,
    selected_senses: list[str],
    sensory_map: dict[str, list[str]],
) -> list[str]:
    """辞書ベースの感覚描写生成（フォールバック用: Step 21）"""
    sensory_details = []
    for sense in selected_senses:
        options = sensory_map.get(sense, [])
        if options:
            detail = options[0]
            sensory_details.append(f"[{sense}] {detail}")
    return sensory_details


async def generate_sensory_details(
    emotion_span: EmotionSpan,
    scene_context: str,
    pov: str = "third_person",
    llm: Any = None,
    prompt_manager: Any = None,
    timeout_seconds: float = 5.0,
) -> list[str]:
    """感覚詳細生成（LLM使用時は高品質、未使用時や障害時はテンプレートベースへフォールバック）"""
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

    # Step 56 / Step 19: LLM を用いた文脈適合感覚描写の生成（タイムアウト保護付き）
    if llm:
        try:
            from pathlib import Path
            from jinja2 import Template

            template_content = None
            if prompt_manager:
                try:
                    t = prompt_manager.get_template("sensory_expansion.jinja2")
                    template_content = getattr(t, "source", None) or str(t)
                except Exception:
                    pass

            if not template_content:
                tpl_path = Path("src/prompts/enrichment/sensory_expansion.jinja2")
                if not tpl_path.exists():
                    tpl_path = Path("prompts/enrichment/sensory_expansion.jinja2")
                if tpl_path.exists():
                    template_content = tpl_path.read_text(encoding="utf-8")

            if template_content:
                tpl = Template(template_content)
                prompt = tpl.render(
                    emotion=emotion,
                    original_phrase=emotion_span.abstract_phrase,
                    original_sentence=emotion_span.sentence_text or emotion_span.abstract_phrase,
                    trailing_conjunction=emotion_span.trailing_conjunction,
                    scene_context=scene_context,
                    pov=pov,
                    preferred_senses=selected_senses,
                )
            else:
                prompt = (
                    f"小説の地の文リライト: 抽象感情「{emotion_span.abstract_phrase}」(感情:{emotion})を、"
                    f"文脈({scene_context})に合わせて五感を用いた自然な地の文(1〜2文)に展開してください。"
                    f"デバッグタグ（[visual]等）は含めず、本文のみ出力してください。"
                )

            import asyncio
            raw_output = await asyncio.wait_for(
                _call_llm_async(llm, prompt),
                timeout=timeout_seconds,
            )

            cleaned = str(raw_output).strip()
            # Step 57: 固定タグ・デバッグ風プレフィックス ([visual]等) の完全撤廃
            cleaned = re.sub(r'\[[a-zA-Z0-9_]+\]\s*', '', cleaned)
            cleaned = cleaned.strip('"\'')
            if len(cleaned) >= 5:
                return [cleaned]
        except asyncio.TimeoutError:
            import logging
            logging.getLogger(__name__).warning(
                "LLM sensory detail generation timed out after %.1fs for phrase: %s",
                timeout_seconds, emotion_span.abstract_phrase
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("LLM sensory detail generation failed: %s", e)
    
    # Step 21: フォールバック処理
    return _fallback_sensory_details(emotion_span, selected_senses, sensory_map)



def sanitize_punctuation(text: str) -> str:
    """不正な句読点並び（。。、。が、等）を自動補正（Step 30）"""
    text = re.sub(r'。+', '。', text)
    text = re.sub(r'、+', '、', text)
    text = re.sub(r'。、', '、', text)
    text = re.sub(r'、。', '。', text)
    # 接続助詞直前の不自然な句点を除去（独立した文頭接続詞「でも、」「だが、」等は保護）
    text = re.sub(r'。(が|ものの|ので|から|ため|ながら)', r'\1', text)
    return text


def validate_rewritten_sentence(rewritten: str, original: str) -> bool:
    """リライト文の健全性を検証。破損時はFalseを返しロールバックを促す（Step 33）"""
    if not rewritten or not isinstance(rewritten, str):
        return False
    stripped = rewritten.strip()
    # 極端に短い（3文字未満）
    if len(stripped) < 3:
        return False
    # 日本語・英数字が1文字も含まれない（記号のみ等）
    if not re.search(r'[一-龯ぁ-んァ-ヴa-zA-Z0-9]', stripped):
        return False
    # エラー文字列や不正なスタブ
    if any(err in stripped for err in ["Error", "None", "undefined", "[object Object]"]):
        return False
    return True


def replace_with_sensory_expansion(
    text: str,
    emotion_spans: list[EmotionSpan],
    sensory_details_list: list[list[str]],
) -> tuple[str, list[dict]]:
    """抽象フレーズを感覚展開版で置換（文置換対応・構文サニタイズ・自動ロールバック付き: Step 29, 30, 33）
    
    Args:
        text: 置換対象の本文テキスト
        emotion_spans: 検出された抽象感情スパンリスト
        sensory_details_list: 各スパンに対応する五感描写リスト
        
    Returns:
        tuple[str, list[dict]]: 展開後テキストと置換メタデータ
    """
    if not emotion_spans:
        return text, []
    
    # 後ろから置換（位置ズレ防止、文単位優先）
    def get_sort_key(item):
        span = item[0]
        return span.sentence_start if span.sentence_end > span.sentence_start else span.start

    sorted_spans = sorted(zip(emotion_spans, sensory_details_list), 
                          key=get_sort_key, reverse=True)
    
    enriched_text = text
    expansions_meta = []
    
    for span, details in sorted_spans:
        is_sentence_level = span.sentence_end > span.sentence_start
        rep_start = span.sentence_start if is_sentence_level else span.start
        rep_end = span.sentence_end if is_sentence_level else span.end
        original_chunk = text[rep_start:rep_end]
        
        if details:
            expanded_parts = []
            for d in details:
                # 万一残存する [sense] タグを確実に除去
                clean_d = re.sub(r'\[[a-zA-Z0-9_]+\]\s*', '', d).strip()
                if clean_d:
                    expanded_parts.append(clean_d)
            
            raw_expansion = "。".join(expanded_parts)
            
            # Step 33: 生成された五感描写自体の文法健全性チェック（破損時は元の文/フレーズにロールバック）
            if not validate_rewritten_sentence(raw_expansion, text[span.start:span.end]):
                import logging
                logging.getLogger(__name__).warning(
                    "Sensory expansion validation failed for '%s' -> rolling back to original.",
                    raw_expansion
                )
                expanded = original_chunk
            else:
                if raw_expansion and not raw_expansion.endswith(("。", "！", "？")):
                    raw_expansion += "。"
                expanded = raw_expansion

                if is_sentence_level:
                    # 感情語の後ろの後続節（例：「〜が耐えた。」の「耐えた。」）
                    after_pos = span.end + len(span.trailing_conjunction)
                    trailing_clause = text[after_pos:span.sentence_end]
                    
                    if span.trailing_conjunction and trailing_clause:
                        # expanded が既に trailing_clause を含んでいない場合は自然に結合
                        if trailing_clause not in expanded:
                            if expanded.endswith("。"):
                                expanded = expanded[:-1]
                            expanded = expanded + span.trailing_conjunction + trailing_clause
        else:
            expanded = original_chunk
        
        # 置換実行
        enriched_text = enriched_text[:rep_start] + expanded + enriched_text[rep_end:]
        
        # メタデータ
        senses = []
        for d in details:
            match = re.search(r'\[([a-zA-Z0-9_]+)\]', d)
            if match:
                senses.append(match.group(1))
        if not senses and details:
            senses = ["sensory"]
            
        expansions_meta.append({
            "original_phrase": span.abstract_phrase,
            "original_sentence": span.sentence_text or text[rep_start:rep_end],
            "expanded_text": expanded,
            "emotion": span.emotion,
            "senses_covered": senses,
            "position": rep_start,
        })
    
    # メタデータを元の順序（位置昇順）に戻す
    expansions_meta.reverse()

    # Step 30: 句読点サニタイズ
    enriched_text = sanitize_punctuation(enriched_text)
    
    return enriched_text, expansions_meta


async def expand_sensory_details_pipeline(
    text: str,
    scene_context: str = "",
    pov: str = "third_person",
    llm: Any = None,
    prompt_manager: Any = None,
    timeout_seconds: float = 5.0,
) -> tuple[str, list[dict]]:
    """感覚拡充パイプライン（非同期エントリーポイント、並列生成対応）"""
    # 1. 抽象感情検出
    emotion_spans = detect_abstract_emotions(text)
    
    if not emotion_spans:
        return text, []
    
    # 2. 各感情に対する感覚詳細生成（Step 20: asyncio.gather 並列化）
    import asyncio
    tasks = [
        generate_sensory_details(
            span, scene_context, pov, llm, prompt_manager, timeout_seconds=timeout_seconds
        )
        for span in emotion_spans
    ]
    all_sensory_details = await asyncio.gather(*tasks)
    
    # 3. 置換実行
    enriched_text, expansions_meta = replace_with_sensory_expansion(
        text, emotion_spans, list(all_sensory_details)
    )
    
    return enriched_text, expansions_meta