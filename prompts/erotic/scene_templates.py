"""
prompts/erotic/scene_templates.py
官能シーンの3フェーズ（build→peak→afterglow）プロンプトテンプレート。
"""

SCENE_TEMPLATE_BUILD = """
【官能シーン: 溜め（Build）フェーズ】
desire_level: {desire_level}/100
sensory_focus: {sensory_focus}
consent_state: {consent_state}

以下のルールに従って「溜め」の描写を生成してください:
- 視線の交差、肌の接近、空気の変化を中心に描写する
- 直接的な身体接触はまだ行わない
- キャラクターの内心の葛藤・期待・緊張を心理描写で表現する
- 環境の温度、光の加減、衣擦れの音などの五感情報を挿入する
"""

SCENE_TEMPLATE_PEAK = """
【官能シーン: 頂点（Peak）フェーズ】
desire_level: {desire_level}/100
sensory_focus: {sensory_focus}
consent_state: {consent_state}

以下のルールに従って「頂点」の描写を生成してください:
- 触覚 > 嗅覚 ≒ 聴覚 > 視覚 > 味覚の優先順位で感覚を描写する
- 心理的な「解放」を比喩的に表現する（例: 波が引くように、光が溢れるように）
- 直接的な生殖器名称は使用せず、感覚と温度の変化で表現する
- 呼吸のリズム変化を文のテンポに反映させる
"""

SCENE_TEMPLATE_AFTERGLOW = """
【官能シーン: 余韻（Afterglow）フェーズ】
desire_level: {desire_level}/100
sensory_focus: {sensory_focus}
consent_state: {consent_state}

以下のルールに従って「余韻」の描写を生成してください:
- 感情の沈降と身体的な弛緩を描写すること（最低2段落、合計400字以上）
- 二人の距離感の再確認（心理的・物理的）を含めること
- 最低1つ以上の次話への伏線を含めること
- 感情のキーワード（沈静、余韻、温もり、安らぎ、静まる等）を必ず使用すること
"""

def get_template_for_phase(phase: str) -> str:
    """フェーズ名からテンプレート文字列を返す。"""
    templates = {
        "build": SCENE_TEMPLATE_BUILD,
        "peak": SCENE_TEMPLATE_PEAK,
        "afterglow": SCENE_TEMPLATE_AFTERGLOW,
    }
    return templates.get(phase, SCENE_TEMPLATE_BUILD)
