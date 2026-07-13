import json
import random
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from jinja2 import Environment
import streamlit as st
import re
from config import (
    RULE_SET_A_RULES, RULE_SET_B_RULES, RULE_SET_C_RULES, RULE_SET_D_RULES,
    STYLE_DEFINITIONS, VILLAIN_STRATEGIES, FORBIDDEN_WORD_REPLACEMENTS, CONTENT_SEPARATOR, STYLE_REFINEMENT_DIRECTIONS
)
from models import CharacterRegistry, CharacterRelationship, PlotDbModel, PlotEpisode

@st.cache_resource
def _get_rule_sets() -> Dict[str, str]:
    return {"RULE_SET_A": RULE_SET_A_RULES, "RULE_SET_B": RULE_SET_B_RULES, "RULE_SET_C": RULE_SET_C_RULES, "RULE_SET_D": RULE_SET_D_RULES}

def get_rule_set(key: str) -> str:
    return _get_rule_sets().get(key, RULE_SET_A_RULES)

class PromptManager:
    """繝励Ο繝ｳ繝励ヨ讒狗ｯ峨Ο繧ｸ繝・け繧剃ｸ諡ｬ邂｡逅・""
    def __init__(self, jinja_env: Environment):
        self.jinja_env = jinja_env

    def get_style_instruction(self, style_key: str) -> str:
        style_def = STYLE_DEFINITIONS.get(style_key, STYLE_DEFINITIONS["style_web_standard"])
        dna_correction = (
            "\n\n縲先枚菴鍋噪DNA遏ｯ豁｣・育ｵｶ蟇ｾ驕ｵ螳茨ｼ峨曾n"
            f"1. 讒区枚繝ｻ繝ｪ繧ｺ繝: {style_def.get('syntax_rhythm', '')}\n"
            f"2. 蝗ｺ譛画ｯ泌湊繝ｻ諢溯ｦ夊ｾ樊嶌: {style_def.get('metaphor_dna', '')}\n"
            f"3. 諤晁・ヮ繧､繧ｺ繝ｻ逕溽炊蜿榊ｿ・ {style_def.get('noise_dna', '')}\n"
            "4. 譁・忰縺ｮ螟壽ｧ俶ｧ: 蜷後§譁・忰縺ｮ3騾｣邯壹ｒ遖∵ｭ｢縲ゆｽ楢ｨ豁｢繧√∝堤ｽｮ豕輔ｒ蠕ｹ蠎輔○繧医・n"
            "5. 莠疲─縺ｮ繝弱Ν繝・ 驥崎ｦ√す繝ｼ繝ｳ縺ｧ縺ｯ隕冶ｦ壻ｻ･螟悶・莠疲─繧堤ｩ肴･ｵ逧・↓蜷ｫ繧√ｈ縲・n"
        )
        template = self.jinja_env.get_template("style_instruction.j2")
        return template.render(
            style_name=style_def["name"],
            dialogue_ratio=style_def.get("dialogue_ratio", "50%"),
            instruction=style_def["instruction"],
            dna_correction=dna_correction,
        )

    def get_villain_instruction(self, genre: str) -> str:
        for key, strategy in VILLAIN_STRATEGIES.items():
            if key in genre: return strategy
        return VILLAIN_STRATEGIES["default"]

    def build_refinement_prompt(self, content: str, style_key: str, is_light: bool, target_word_count: int) -> str:
        style_def = STYLE_DEFINITIONS.get(style_key, STYLE_DEFINITIONS["style_web_standard"])
        direction = STYLE_REFINEMENT_DIRECTIONS["light" if is_light else "heavy"]

        return (
            f"縺ゅ↑縺溘・縲瑚ｪｭ閠・ｒ迚ｩ隱槭・荳ｭ豈偵↓縺輔○繧九榊､ｩ謇堺ｽ懷ｮｶ縺ｧ縺吶・n{direction}\n"
            f"蟇ｾ雎｡繧ｹ繧ｿ繧､繝ｫ: {style_def['name']}\n逶ｮ讓呎枚蟄玲焚: {target_word_count}\n\n"
            f"縲蝉ｿｮ豁｣謖・・縲曾n1. AI螳壼梛蜿･縺ｮ謚ｹ谿ｺ縲・. 莠疲─謠丞・繧定ｧ｣蜒丞ｺｦ150%縺ｫ蠑輔″荳翫￡縲・. 髮｢閼ｱ髦ｲ豁｢縺ｮ繝輔ャ繧ｯ縲・n\n"
            f"縲占拷遞ｿ縲曾n{content}"
        )

    def get_plot_common_rules(self) -> str:
        return """
縲千悄繝ｻ繝励Ο繝・ヨ險ｭ險磯ｻ・≡蠕・10繧ｫ譚｡・育ｵｶ蟇ｾ驕ｵ螳茨ｼ峨・1. [1隧ｱ1繧ｷ繝ｼ繝ｳ縺ｨ鬮倩ｧ｣蜒丞ｺｦ蛹望: 譎る俣繧ｹ繧ｭ繝・・繝ｻ繝繧､繧ｸ繧ｧ繧ｹ繝医ｒ遖√★繧九・2. [Show, Don't Tell]: 諢滓ュ縺ｯ閧我ｽ灘虚菴懊↓鄙ｻ險ｳ縺励∝推繧ｷ繝ｼ繝ｳ縺ｫ3縺､莉･荳翫・蜈ｷ菴鍋噪縺ｪ莠疲─諠・ｱ繧堤ｵ・∩霎ｼ繧√・3. [閭ｽ蜍墓ｧ縺ｨ諢丞ｿ励・轣ｫ]: 遯ｮ蝨ｰ縺ｧ縺ｮ縲悟ｰ上＆縺ｪ謚ｵ謚暦ｼ域э蠢暦ｼ峨阪ｒ蠢・★謠上￠縲・4. [謔ｪ蠖ｹ縺ｮ遏･逡･]: 謨ｵ蟇ｾ閠・ｒ遏･逡･逧・↑蟄伜惠縺ｨ縺励√き繧ｿ繝ｫ繧ｷ繧ｹ蜑崎ｩｱ縺ｧ縺ｯ蟆雁宍繧貞･ｪ縺・√せ繝医Ξ繧ｹ繧呈･ｵ髯舌∪縺ｧ貅懊ａ繧医・5. [隱崎ｭ倥・繧ｺ繝ｬ]: 荳ｻ莠ｺ蜈ｬ縺ｮ諢丞峙縺ｨ蜻ｨ蝗ｲ縺ｮ隗｣驥医・荵夜屬繧堤黄隱槭・謗ｨ騾ｲ蜉帙→縺帙ｈ縲・10. [莨冗ｷ壹・蜈郁｡碁・鄂ｮ]: 騾・ｻ｢縺ｮ謨ｰ陦悟燕縺ｾ縺ｧ縺ｫ莨冗ｷ壹ｒ驟咲ｽｮ縺励√＃驛ｽ蜷井ｸｻ鄒ｩ繧帝亟縺偵・"""

    def _build_quota_section(self, scenes_data: Any, target_word_count: int) -> str:
        if isinstance(scenes_data, str):
            scenes_data = [{"action": scenes_data}]
        if not isinstance(scenes_data, list) or not scenes_data:
            return ""
            
        # 隕∫ｴ縺瑚ｾ樊嶌縺ｧ縺ｪ縺・ｴ蜷医・謨第ｸ茨ｼ医Μ繧ｹ繝亥・縺ｮ譁・ｭ怜・縺ｪ縺ｩ・・        normalized_scenes = [s if isinstance(s, dict) else {"action": str(s)} for s in scenes_data]
        total_impact = sum(s.get('impact_score', 50) for s in normalized_scenes) or 1
        inst = "縲仙濤遲・ヮ繝ｫ繝槭曾n"
        for i, s in enumerate(normalized_scenes):
            impact = s.get('impact_score', 50)
            scene_quota = max(100, int((target_word_count * (impact / total_impact)) * 1.8))
            role = "徴 辷・匱" if impact >= 80 else "搭 蟆主・" if impact <= 30 else "竢ｳ 螻暮幕"
            inst += f"- 繧ｷ繝ｼ繝ｳ{i+1} [{role}]: 逶ｮ讓・{scene_quota} 蟄嶺ｻ･荳翫よ怙菴・5谿ｵ關ｽ莉･荳翫・n"
        return inst

    def _build_show_tell_section(self, scenes_data: Any) -> str:
        if isinstance(scenes_data, str):
            scenes_data = [{"action": scenes_data}]
        if not isinstance(scenes_data, list) or not scenes_data:
            return ""

        # 隕∫ｴ縺瑚ｾ樊嶌縺ｧ縺ｪ縺・ｴ蜷医・謨第ｸ茨ｼ医Μ繧ｹ繝亥・縺ｮ譁・ｭ怜・縺ｪ縺ｩ・・        normalized_scenes = [s if isinstance(s, dict) else {"action": str(s)} for s in scenes_data]
        inst = "縲先緒蜀呎婿驥昴曾n"
        for i, s in enumerate(normalized_scenes):
            impact = s.get('impact_score', 50)
            if impact >= 70:
                inst += f"- 繧ｷ繝ｼ繝ｳ{i+1}: 縲心how蜈ｨ髢九台ｺ疲─繧帝｣ｽ蜥後＆縺帙∫ｭ玖ｉ縺ｮ逞呎肇繧・ｦ也ｷ壹・蜍輔″繧貞濤諡励↓謠丞・縺帙ｈ縲・n"
            elif impact <= 30:
                inst += f"- 繧ｷ繝ｼ繝ｳ{i+1}: 縲慎ell隕∫ｴ・醍憾豕√ｒ邁｡貎斐↓豬√＠縲√ユ繝ｳ繝昴ｒ驥崎ｦ悶○繧医・n"
        return inst

    def _build_forbidden_section(self) -> str:
        word = random.choice(list(FORBIDDEN_WORD_REPLACEMENTS.keys()))
        return (
            f"縲栓泅ｨ遖∝ｿ瑚ｪ槭・蠑ｷ蛻ｶ鄂ｮ謠幤泅ｨ縲曾n縲鶏word}縲阪・菴ｿ逕ｨ繧堤ｦ√★繧九ゆｻ｣繧上ｊ縺ｫ {FORBIDDEN_WORD_REPLACEMENTS[word]} 繧堤畑縺・※蜈ｷ菴灘喧縺嬪y縲・n"
            "迚ｩ隱槭ｒ縲弱≠繧峨☆縺倥上・繧医≧縺ｫ隱槭ｋ縺ｪ縲ゅく繝｣繝ｩ縺ｮ隕也阜縺九ｉ蜃ｺ繧九↑縲・n"
        )

    def _build_hook_strategy_section(self) -> str:
        return (
            "縲舌ム繧､繝翫Α繝・け繝ｻ繝輔ャ繧ｯ謌ｦ逡･縲曾n"
            "1. 蜀帝ｭ3陦・ 隱ｭ閠・′迴ｾ螳溘〒謚ｱ縺医ｋ谺關ｽ・井ｸ・・諢溘∝ｾｩ隶仙ｿ・ｭ会ｼ峨ｒ蜊ｳ蠎ｧ縺ｫ蛻ｺ豼縺吶ｋ荳譁・〒蟋九ａ繧医・n"
            "2. 譛ｫ蟆ｾ5陦・ 莠亥ｮ夊ｪｿ蜥後ｒ遐ｴ螢翫＠縲∬ｪｭ閠・′縲取ｬ｡繧偵け繝ｪ繝・け縺帙＊繧九ｒ蠕励↑縺・丞ｼｷ辜医↑繧ｯ繝ｪ繝輔ワ繝ｳ繧ｬ繝ｼ繧帝・鄂ｮ縺帙ｈ縲・n"
        )

    def _build_assertion_section(self, constraints: List[Any]) -> str:
        if not constraints: return ""
        inst = "縲栓泅ｨ蝗譫懷ｾ九Θ繝九ャ繝医ユ繧ｹ繝茨ｼ夊ｫ也炊蛻ｶ邏・・邨ｶ蟇ｾ驕ｵ螳芋泅ｨ縲曾n"
        for c in constraints:
            if isinstance(c, dict):
                inst += f"- {c.get('subject')}: {c.get('constraint')} (驕募渚縺励◆蝣ｴ蜷医・蜊ｳ蠎ｧ縺ｫ繝ｪ繝ｩ繧､繝亥ｯｾ雎｡縺ｨ縺ｪ繧・\n"
        return inst

    def build_final_writing_prompt(self, ep_num: int, plot_data: Dict[str, Any], script_text: str, target_word_count: int, plot_thought_process: str = "", **kwargs) -> str:
        # 蜷・そ繧ｯ繧ｷ繝ｧ繝ｳ繧偵Δ繧ｸ繝･繝ｼ繝ｫ縺ｨ縺励※讒狗ｯ・        scenes_data = plot_data.get("scenes", [])
        quota_inst = self._build_quota_section(scenes_data, target_word_count)
        show_tell_inst = self._build_show_tell_section(scenes_data)
        forbidden_inst = self._build_forbidden_section()
        hook_inst = self._build_hook_strategy_section()
        
        # 隲也炊蛻ｶ邏・(Category B)
        settings_ctx = kwargs.get('settings_ctx', '{}')
        if isinstance(settings_ctx, str):
            try:
                settings_ctx = json.loads(settings_ctx)
            except:
                settings_ctx = {}
        if not isinstance(settings_ctx, dict):
            settings_ctx = {}

        assertion_inst = self._build_assertion_section(settings_ctx.get('active_constraints', []))
        
        # 隕也せ繝ｻ繝医・繝ｳ
        phase = plot_data.get("current_chain_phase", "Hate")
        tone_inst = f"縲舌ヵ繧ｧ繝ｼ繧ｺ繝医・繝ｳ: {phase}縲曾n"
        if phase == "Hate": tone_inst += "隱ｭ閠・・縲弱＊縺ｾ縺√乗ｬｲ豎ゅｒ譛螟ｧ蛹悶○繧医よ雰縺ｮ蛯ｲ諷｢縺輔→荳榊ｽ薙↑霎ｱ繧√ｒ蝓ｷ諡励↓謠丞・縺帙ｈ縲・n"
        elif phase == "Payoff": tone_inst += "蜻ｨ蝗ｲ縺ｮ縲守ｵｶ譛帙・蠕梧ｔ繝ｻ逡乗悶上・蜿榊ｿ懈緒蜀吶↓譁・ｭ玲焚縺ｮ7蜑ｲ繧貞牡縺代・n"

        # 譛邨ゅユ繝ｳ繝励Ξ繝ｼ繝・        template = self.jinja_env.from_string("""
譛ｬ譁・幕蟋句燕縺ｫ [thought_process] 繧貞・蜉帙○繧・
1. 繧ｷ繝ｼ繝ｳ縺斐→縺ｮ邱ｩ諤･縺ｮ蟲ｻ蛻･ 2. 逶ｮ讓呎枚蟄玲焚驟榊・ 3. 隱ｭ閠・・諠・ｷ偵ｒ遐ｴ螢翫☆繧倶ｸ譁・4. 莠疲─諠・ｱ縺ｮ蜆ｪ蜈磯・ｽ・5. 蜀帝ｭ繝ｻ譛ｫ蟆ｾ縺ｮ繝輔ャ繧ｯ謌ｦ逡･

{{ quota_inst }}
{{ show_tell_inst }}
{{ forbidden_inst }}
{{ hook_inst }}
{{ assertion_inst }}

縲蝉ｽ懷刀譁・ц縲・荳榊､牙ｱ樊ｧ: {{ char_static_ctx }}
蜍慕噪迥ｶ諷・ {{ char_dynamic_ctx }}
譌｢遏･縺ｮ譁・ц: {{ prev_ctx }}

縲先欠莉､縲・笆 蜿ｰ譛ｬ (邨ｶ蟇ｾ驕ｵ螳・: {{ script_text }}
笆 繝励Ο繝・ヨ險ｭ險亥峙: {{ blueprint }}
笆 逶ｮ讓呎枚蟄玲焚: {{ target_word_count }} 蟄嶺ｻ･荳・{{ tone_inst }}
{{ style_sample }}
{{ director_notes }}

--- 蜃ｺ蜉帛ｽ｢蠑・---
[thought_process]
{{ CONTENT_SEPARATOR }}
[NOVEL_CONTENT]
{{ CONTENT_SEPARATOR }}
[METADATA_JSON]
""")

        return template.render(
            quota_inst=quota_inst,
            show_tell_inst=show_tell_inst,
            forbidden_inst=forbidden_inst,
            hook_inst=hook_inst,
            assertion_inst=assertion_inst,
            char_static_ctx=kwargs.get('char_static_ctx', ''),
            char_dynamic_ctx=kwargs.get('char_dynamic_ctx', ''),
            prev_ctx=kwargs.get('prev_ctx', ''),
            script_text=script_text,
            blueprint=plot_data.get('detailed_blueprint', ''),
            target_word_count=target_word_count,
            tone_inst=tone_inst,
            style_sample=f"縲先枚菴鍋ｶ呎価縲曾n{kwargs.get('prose_sample')}" if kwargs.get('prose_sample') else "",
            director_notes=f"縲絶國・丈ｿｮ豁｣謖・､ｺ縲曾n{kwargs.get('director_notes')}" if kwargs.get('director_notes') else "",
            CONTENT_SEPARATOR=CONTENT_SEPARATOR
        )

    def build_producer_audit_prompt(self, genre: str, keywords: str, trend_memo: str) -> str:
        available_tropes = [
            "縺悶∪縺・, "譁ｭ鄂ｪ", "謌舌ｊ荳翫′繧・, "辟｡閾ｪ隕夂┌蜿・, "蝨ｧ蛟堤噪蝣ｱ蠕ｩ", "霑ｽ謾ｾ縺悶∪縺・,
            "繝､繝ｳ繝・Ξ繝偵Ο繧､繝ｳ", "螳溘・譛芽・縺ｪ蠕楢・, "迢ゆｿ｡逧・↑驟堺ｸ・, "荳埼∞縺ｪ螟ｩ謇・, "蜈ｱ萓晏ｭ・,
            "謌ｦ繧上↑縺・怙蠑ｷ", "蠕ｩ隶舌＠縺ｪ縺・ｿｽ謾ｾ閠・, "蝟・ｺｺ縺吶℃繧区が蠖ｹ",
        ]
        template = self.jinja_env.get_template("ai_producer_audit")
        prompt = template.render(genre=genre, keywords=keywords, trend_memo=trend_memo)
        prompt += (
            f"\n\n縲仙ｿ・亥・蜉幃・岼・・SON繧ｭ繝ｼ・峨・
            f"\n1. refined_keywords: 繝悶Λ繝・す繝･繧｢繝・・縺輔ｌ縺溯ｦ・ｨｩ繧ｭ繝ｼ繝ｯ繝ｼ繝会ｼ医き繝ｳ繝槫玄蛻・ｊ・・
            f"\n2. refined_concept: 蝠・･ｭ逧・↓譛驕ｩ蛹悶＆繧後◆迚ｩ隱槭さ繝ｳ繧ｻ繝励ヨ・・00譁・ｭ礼ｨ句ｺｦ・・
            f"\n3. refined_mc_suggestion: 隱ｭ閠・・蜈ｱ諢溘→谺ｲ譛帙ｒ蛻ｺ豼縺吶ｋ荳ｻ莠ｺ蜈ｬ蜒上・蜈ｷ菴鍋噪縺ｪ謠先｡・
            f"\n4. recommended_tropes: 謗ｨ螂ｨ縺輔ｌ繧九ヨ繝ｭ繝ｼ繝励・繝ｪ繧ｹ繝茨ｼ域枚蟄怜・縺ｮ驟榊・・・
            f"\n\n縲先欠莉､縲大膚逕ｨ蜃ｺ迚医〒繝ｩ繝ｳ繧ｭ繝ｳ繧ｰ1菴阪ｒ迢吶∴繧句・菴鍋噪縺ｪ菫ｮ豁｣譯医ｒ縲∽ｸ願ｨ倬・岼繧堤ｶｲ鄒・＠縺櫟SON蠖｢蠑上・縺ｿ縺ｧ蜃ｺ蜉帙＠縺ｦ縺上□縺輔＞縲・
            f"縲宣∈謚槫庄閭ｽ縺ｪ隕∫ｴ繝ｪ繧ｹ繝医・ {', '.join(available_tropes)}"
        )
        return prompt

    def build_logical_audit_prompt(self, past_facts: str, plot_bp: str, script: str) -> str:
        return (
            "縺ゅ↑縺溘・迚ｩ隱槭・謨ｴ蜷域ｧ逶｣譟ｻ螳倥〒縺吶ゆｻ･荳九・驕主悉縺ｮ莠句ｮ溘→莉雁屓縺ｮ繝励Ο繝・ヨ縺ｫ遏帷崟縺後↑縺・°遒ｺ隱阪＠縺ｦ縺上□縺輔＞縲・n\n"
            f"縲宣℃蜴ｻ縺ｮ莠句ｮ溘曾n{past_facts}\n\n縲舌・繝ｭ繝・ヨ縲曾n{plot_bp}\n\n縲仙床譛ｬ縲曾n{script}"
        )

    def build_foreshadowing_audit_prompt(self, f_map: List[Dict[str, Any]], content: str) -> str:
        return (
            f"莨冗ｷ壼屓蜿守屮譟ｻ:\n縲蝉ｺ亥ｮ壹Μ繧ｹ繝医曾n{json.dumps(f_map, ensure_ascii=False)}\n\n"
            f"縲先悽譁・曾n{content[:4000]}"
        )

    def build_misunderstanding_validation_prompt(self, content: str, gap_desc: str) -> str:
        return (
            "莉･荳九・蟆剰ｪｬ譛ｬ譁・ｒ隗｣譫舌＠縲√主鋸驕輔＞・郁ｪ崎ｭ倥・荵夜屬・峨上・逋ｺ逕溘・繝ｭ繧ｻ繧ｹ縺御ｻ･荳九・4繧ｹ繝・ャ繝励ｒ豁｣縺励￥雕上ｓ縺ｧ縺・ｋ縺句愛螳壹○繧医・n\n"
            "縲先､懆ｨｼ繧ｹ繝・ャ繝励曾n"
            "A・井ｺ句ｮ滂ｼ・ 螳｢隕ｳ逧・↑迥ｶ豕√′謠千､ｺ縺輔ｌ縺ｦ縺・ｋ縺欺n"
            "B・育ｵｶ譛幢ｼ・ 隕也せ荳ｻ縲√∪縺溘・蜻ｨ蝗ｲ縺御ｸ譎ら噪縺ｪ邨ｶ譛帙ｄ蜊ｱ讖溘ｒ諢溘§縺ｦ縺・ｋ縺欺n"
            "C・郁ｪ､隱搾ｼ・ 荳ｻ莠ｺ蜈ｬ縺ｮ陦悟虚縺後∽ｺ句ｮ溘→縺ｯ逡ｰ縺ｪ繧区枚閼医〒蜉・噪縺ｫ隱､隗｣縺輔ｌ縺ｦ縺・ｋ縺欺n"
            "D・郁ｦ夐・・・ 縺昴・隱､隗｣縺ｫ繧医ｊ縲∝捉蝗ｲ縺ｮ隧穂ｾ｡縺檎・逋ｺ逧・↓蜷台ｸ奇ｼ医∪縺溘・莠区・縺悟･ｽ霆｢・峨＠縺ｦ縺・ｋ縺欺n\n"
            f"縲先悽譁・・\n{content[:3000]}\n\n"
            f"縲占ｨｭ螳壹＆繧後◆荵夜屬縲・\n{gap_desc}\n\n"
            "Output Schema (JSON):\n"
            '{"passed": bool, "missing_steps": ["A", "B"], "reason": "逅・罰"}'
        )

    def build_marketing_pack_prompt(self, book_title: str, synopsis: str, latest_ep: int) -> str:
        return (
            f"菴懷刀縲施book_title}縲上・螳｣莨昴ヱ繝・け繧堤函謌舌＠縺ｦ縺上□縺輔＞縲・n"
            f"譛譁ｰ隧ｱ: 隨ｬ{latest_ep}隧ｱ\n"
            f"縺ゅｉ縺吶§: {synopsis}\n\n"
            "莉･荳九ｒ逕滓・:\n"
            "1. 繧ｫ繧ｯ繝ｨ繝逕ｨ繧ｭ繝｣繝・メ繧ｳ繝斐・・・5譁・ｭ嶺ｻ･蜀・∽ｽ懷刀縺ｮ譛螟ｧ縺ｮ鬲・鴨縺ｨ繝輔ャ繧ｯ繧堤ｫｯ逧・↓・噂n"
            "2. 繧ｫ繧ｯ繝ｨ繝霑第ｳ√ヮ繝ｼ繝育畑縺ｮ謚慕ｨｿ譁・ｼ・00譁・ｭ礼ｨ句ｺｦ縲√≠繧峨☆縺倥・繝上う繝ｩ繧､繝茨ｼ噂n"
            "3. 謗ｨ螂ｨ繧ｿ繧ｰ・医き繧ｯ繝ｨ繝蜷代￠縲√後＊縺ｾ縺√阪御ｸｻ莠ｺ蜈ｬ譛蠑ｷ縲阪瑚ｿｽ謾ｾ縲阪後メ繝ｼ繝医阪↑縺ｩ莠ｺ豌鈴ｻ蜃ｺ繧ｿ繧ｰ繧呈怙菴・縺､蜷ｫ繧10蛟具ｼ噂n\n"
            "Output Schema (JSON):\n"
            '{"catchphrase": "...", "kakuyomu_notes": "...", "tags": ["..."]}'
        )

    def build_title_generation_prompt(self, genre: str, keywords: str) -> str:
        return (
            f"繧ｸ繝｣繝ｳ繝ｫ: {genre}\n繧ｭ繝ｼ繝ｯ繝ｼ繝・ {keywords}\n\n"
            "繧ｫ繧ｯ繝ｨ繝邱丞粋繝ｩ繝ｳ繧ｭ繝ｳ繧ｰ1菴阪ｒ螂ｪ蜿悶☆繧九◆繧√・縲先姶逡･逧・聞譁・ち繧､繝医Ν縲代ｒ3譯亥・縺帙・n"
            "縲宣延蜑・・. 40-100譁・ｭ励・雜・聞譁・↓縺帙ｈ縲・2. 縲手ｿｽ謾ｾ縺輔ｌ縺滓怙蠑ｷ縺ｮ縲懊上主ｮ溘・縲懊□縺｣縺滉ｻｶ縲上惹ｻ翫＆繧画綾繧後→險繧上ｌ縺ｦ繧ゅ懊冗ｭ峨・繝医Ξ繝ｳ繝牙ｼｷ繝ｯ繝ｼ繝峨ｒ蠢・★蜷ｫ繧√ｈ縲・3. 繧ｿ繧､繝医Ν縺後≠繧峨☆縺倥ｒ蜈ｼ縺ｭ繧九ｈ縺・↓縺帙ｈ縲・n"
            'Output Schema (JSON): {"titles": ["譯・", "譯・", "譯・"]}'
        )

    def build_style_dna_analysis_prompt(self, sample_text: str) -> str:
        return (
            "莉･荳九・蟆剰ｪｬ繧ｵ繝ｳ繝励Ν繧貞・譫舌＠縲√◎縺ｮ譁・ｽ薙・DNA繧呈歓蜃ｺ縺励※縺上□縺輔＞縲・n\n"
            f"縲舌し繝ｳ繝励Ν縲曾n{sample_text[:3000]}\n\n"
            "Output Schema (JSON):\n"
            '{"name": "譁・ｽ灘錐", "instruction": "蝓ｷ遲・欠遉ｺ", "score": 75, "analysis": "蛻・梵繝ｬ繝昴・繝・}'
        )

    def build_world_creation_prompt(self, genre: str, keywords: str, response_schema: BaseModel) -> str:
        return (
            f"縺ゅ↑縺溘・荳也阜讒狗ｯ峨・繝励Ο繝輔ぉ繝・す繝ｧ繝翫Ν縺ｧ縺吶ゅず繝｣繝ｳ繝ｫ: {genre}, 繧ｭ繝ｼ繝ｯ繝ｼ繝・ {keywords} 縺ｫ蝓ｺ縺･縺阪・
            "莉･荳九・2螻､繧定ｩｳ邏ｰ縺ｫ讒狗ｯ峨＠縺ｦ縺上□縺輔＞縲ゅ↑縺翫・*蜃ｺ蜉帛・螳ｹ縺ｯ縺吶∋縺ｦ譌･譛ｬ隱槭〒陦後≧縺薙→縲・*\n"
            "1. 迚ｩ逅・・鬲泌ｰ弱・遉ｾ莨壽ｳ募援縺ｨ蝗譫憺未菫ゑｼ・ausality_map・峨・
            "荳也阜繧定ｦ・≧縲檎炊荳榊ｰｽ縺ｪ繧ｿ繝悶・縲阪ｄ縲悟ｰ・擂蟇ｾ蟲吶☆縺ｹ縺咲ｵｶ蟇ｾ逧・у螽・ｼ医Λ繧ｹ繝懊せ繧・囓霄阪☆繧狗ｵ・ｹ斐・蠖ｱ・峨阪ｒ蠢・★1縺､蝗譫懷ｾ九↓蜷ｫ繧√ｋ縺薙→縲・n"
            "2. 豁ｴ蜿ｲ繝ｻ譁・喧繝ｻ莠疲─蝨ｰ蝗ｳ・・ensory Map・噂n"
            f"Output Schema: {response_schema.model_json_schema()}"
        )

    def build_mc_creation_prompt(self, world_rules_json: str, genre: str, keywords: str, concept: str = "") -> str:
        return (
            "縺ゅ↑縺溘・繧ｭ繝｣繝ｩ繧ｯ繧ｿ繝ｼ騾蠖｢縺ｮ逾槭〒縺ゅｊ縲√き繧ｯ繝ｨ繝縺ｧ隱ｭ閠・・蠢・ｒ謚峨ｊ縲∝濤逹縺輔○繧九守函縺阪◆縲上く繝｣繝ｩ繧ｯ繧ｿ繝ｼ繧堤函縺ｿ蜃ｺ縺吶・繝ｭ縺ｧ縺吶・n"
            f"縲蝉ｼ∫判讎りｦ√代ず繝｣繝ｳ繝ｫ: {genre} / 繧ｭ繝ｼ繝ｯ繝ｼ繝・ {keywords} / 繧ｳ繝ｳ繧ｻ繝励ヨ: {concept}\n"
            f"荳也阜隕ｳ: {world_rules_json}\n"
            "縲先欠莉､・壻ｸｻ莠ｺ蜈ｬ・・C・峨ｒ雜・ｧ｣蜒丞ｺｦ縺ｧ騾蠖｢縺帙ｈ縲曾n"
            f"CharacterRegistry縺ｮ蜈ｨ繝輔ぅ繝ｼ繝ｫ繝峨ｒ縲∽ｻ･荳九・5縺､縺ｮ谺｡蜈・〒豺ｱ謗倥ｊ縺励※蝓九ａ繧医・n"
            f"1. 縲蝉ｸ牙ｱ､讒矩縺ｮ邊ｾ逾槭・ \n"
            f"   - surface_persona (陦ｨ螻､・育､ｾ莨夂噪莉ｮ髱｢・・: 蜻ｨ蝗ｲ縺九ｉ縺ｩ縺・ｦ九ｉ繧後※縺・ｋ縺九ゅ←縺ｮ繧医≧縺ｪ蠖ｹ蜑ｲ繧呈ｼ斐§縺ｦ縺・ｋ縺九・n"
            f"   - inner_conflict (荳ｭ螻､・亥・逧・泝逶ｾ・・: 貍斐§縺ｦ縺・ｋ閾ｪ蛻・→縲∵悽蠖薙・譛帙∩縺ｮ髢薙・蠑輔″陬ゅ°繧後ｋ繧医≧縺ｪ闡幄陸縲・n"
            f"   - core_trauma (豺ｱ螻､・亥次蛻昴・谺關ｽ・・: 驕主悉縺ｮ菴輔′蠖ｼ繧呈ｱｺ螳夂噪縺ｫ螢翫＠縺溘・縺九ゆｽ輔ｒ蝓九ａ繧九◆繧√↓謌ｦ縺｣縺ｦ縺・ｋ縺ｮ縺九・n"
            f"2. 縲舌メ繝ｼ繝医→莉｣蜆溘・蜻ｪ邵帙・ 縺昴・閭ｽ蜉帙・縺ｪ縺懊主ｽｼ縲上↓螳ｿ縺｣縺溘・縺九り・蜉帙ｒ菴ｿ縺・◆縺ｳ縺ｫ蜑翫ｉ繧後ｋ邊ｾ逾樒噪繝ｻ閧我ｽ鍋噪縺ｪ繧ｳ繧ｹ繝医ｒ縲∬ｪｭ閠・′縲檎李縲・＠縺・阪→諢溘§繧九Ξ繝吶Ν縺ｧ險ｭ螳壹○繧医・n"
            f"3. 縲千ｵｶ蟇ｾ驕ｵ螳医・驩・援(Iron Constraint)縲・ 縲梧ｭｻ繧薙〒繧ゅ％繧後□縺代・譖ｲ縺偵↑縺・阪→縺・≧逡ｰ蟶ｸ縺ｪ縺ｾ縺ｧ縺ｮ縺薙□繧上ｊ縲ゅ％繧後′迚ｩ隱槭・譛螟ｧ縺ｮ繝斐Φ繝√ｒ逕溘・蜴溷屏縺ｨ縺ｪ繧九ｈ縺・↓縺帙ｈ縲・n"
            f"4. 縲蝉ｺ疲─縺ｫ蛻ｺ縺輔ｋ謠丞・繝輔ャ繧ｯ(Expansion Hooks)縲・ 蝓ｷ遲・凾縺ｫ謠丞・繧・蛟阪↓閹ｨ繧峨∪縺帙ｋ縺溘ａ縺ｮ蜈ｷ菴鍋噪譚先侭繧・縺､莉･荳願ｨ倩ｿｰ縺帙ｈ縲・n"
            f"   ・井ｾ具ｼ夂音螳壹・蛯ｷ霍｡縺檎名縺乗─隗ｦ縲∵偵▲縺滓凾縺ｫ辟｡諢剰ｭ倥↓蝎帙・蜚・・蜻ｳ縲・ｭ泌鴨謾ｾ蜃ｺ譎ゅ・辟ｦ縺偵◆闃ｱ縺ｮ蛹ゅ＞縲∫音螳壹・髻ｳ讌ｽ繧・浹縺ｫ蟇ｾ縺吶ｋ驕主臆縺ｪ蜿榊ｿ懊↑縺ｩ・噂n"
            f"5. 縲占ｦ・ｨｩ縺ｮ蜿｣隱ｿ縺ｨ迢ｬ逋ｽ繧ｹ繧ｿ繧､繝ｫ縲・ 莉冶・↓隕九○繧句､夜擇縺ｮ繧ｻ繝ｪ繝輔→縲∬┻蜀・〒縺ｮ縲檎憲辜医↓蛟区ｧ逧・〒繧ｷ繝九き繝ｫ縲√≠繧九＞縺ｯ辭ｱ迢ら噪縺ｪ迢ｬ逋ｽ縲阪・蟇ｾ豈斐ｒ譏守｢ｺ縺ｫ縺帙ｈ縲・n\n"
            f"縲仙宛邏・曾n"
            f"- dialogue_samples 縺ｯ縲√◎縺ｮ繧ｭ繝｣繝ｩ縺ｮ縲守音逡ｰ縺ｪ諤晁・屓霍ｯ縲上′貍上ｌ蜃ｺ縺吶ｂ縺ｮ繧・縺､莉･荳翫・n"
            f"- save_the_cat_event (Save the Cat隕∫ｴ)繧偵・℃蜴ｻ縺ｮ邨梧ｭｴ縺ｫ蜈ｷ菴鍋噪縺ｫ邨・∩霎ｼ繧√・n"
            f"- 蜈ｨ縺ｦ縺ｮ蜃ｺ蜉帙・譌･譛ｬ隱槭〒陦後≧縺薙→縲・n"
            f"Output Schema (JSON):\n"
            f"{CharacterRegistry.model_json_schema()}"
        )

    def build_sub_char_creation_prompt(self, world_rules_json: str, mc_data_json: str, causality_map: List[str], mc_name: str) -> str:
        return (
            "縺ゅ↑縺溘・繧ｭ繝｣繝ｩ繧ｯ繧ｿ繝ｼ騾蠖｢縺ｮ逾槭〒縺ゅｊ縲√き繧ｯ繝ｨ繝縺ｧ隱ｭ閠・・蠢・ｒ謚峨ｊ縲∝濤逹縺輔○繧九守函縺阪◆縲上く繝｣繝ｩ繧ｯ繧ｿ繝ｼ繧堤函縺ｿ蜃ｺ縺吶・繝ｭ縺ｧ縺吶・n"
            f"荳也阜隕ｳ: {world_rules_json}\n"
            f"荳ｻ莠ｺ蜈ｬ諠・ｱ: {mc_data_json}\n"
            f"荳也阜縺ｮ蝗譫懷ｾ・ {json.dumps(causality_map, ensure_ascii=False)}\n\n"
            "縲先欠莉､・・蛟阪・隗｣蜒丞ｺｦ縺ｧ3蜷阪ｒ逕滓・縺帙ｈ縲曾n"
            f"CharacterRegistry縺ｮ蜈ｨ繝輔ぅ繝ｼ繝ｫ繝峨ｒ縲∽ｻ･荳九・5縺､縺ｮ繝ｬ繧､繝､繝ｼ繧貞ｮ檎挑縺ｫ讒狗ｯ峨＠縲∝沂繧√◆JSON繧貞・蜉帙○繧医・n"
            f"1. fate_link (驕句多縺ｮ骼・: 荳也阜縺ｮ蝗譫懷ｾ具ｼ・ausality_map・峨・縺ｩ縺ｮ驛ｨ蛻・ｒ菴鍋樟縺励※縺・ｋ縺九ゆｸ也阜縺悟｣翫ｌ縺滄圀縺ｫ蠖ｼ繧峨′菴輔ｒ螟ｱ縺・°縲・n"
            f"2. social_mask_vs_truth (遉ｾ莨夂噪莉ｮ髱｢縺ｨ逕溽炊逧・悄螳・: 陦ｨ蜷代″縺ｮ蝨ｰ菴阪→縲∝､應ｸ莠ｺ縺ｧ縺・ｋ譎ゅ↓隕九○繧九主翁縺榊・縺励・繝医Λ繧ｦ繝槭ｄ豁ｪ縺ｿ縲上・蟇ｾ豈斐・n"
            f"3. relationships (MC縺ｸ縺ｮ驥榊ｱ､逧・↑諢滓ュ): 蜊倥↑繧句袖譁ｹ繝ｻ謨ｵ縺ｧ縺ｯ縺ｪ縺上｀C({mc_name})縺ｫ蟇ｾ縺吶ｋ縲檎ｾｨ譛帙∬ｻｽ阡代∝濤逹縲∵←鄒ｩ縲∵＄諤悶阪′蜈･繧頑ｷｷ縺倥▲縺溯､・尅縺ｪ繝吶け繝医Ν縲ゅ↑縺廴C縺ｫ蜃ｺ莨壹▲縺ｦ縺励∪縺｣縺溘％縺ｨ縺悟ｽｼ繧峨・莠ｺ逕溘・譛螟ｧ邏壹・莠倶ｻｶ縺ｪ縺ｮ縺九・haracterRelationship繝｢繝・Ν縺ｮ繝ｪ繧ｹ繝医→縺励※險倩ｿｰ縺帙ｈ縲・n"
            "4. 縲千ｵｶ蟇ｾ驕ｵ螳医・驩・援(Iron Constraint)縲・ 繧ｭ繝｣繝ｩ縺檎ｵｶ蟇ｾ縺ｫ繧・ｉ縺ｪ縺・％縺ｨ縲√∪縺溘・豁ｻ繧薙〒繧ょｮ医ｋ逡ｰ蟶ｸ縺ｪ縺薙□繧上ｊ・亥濤遲・凾縺ｮ陦悟虚謖・・・峨・n"
            "5. 縲宣ｫ倩ｧ｣蜒丞ｺｦ繝輔ャ繧ｯ(Expansion Hooks)縲・ 蝓ｷ遲・凾縺ｫ謠丞・繧・蛟阪↓閹ｨ繧峨∪縺帙ｋ縺溘ａ縺ｮ蜈ｷ菴鍋噪譚先侭・井ｾ具ｼ夂┬縺｣縺滓凾縺ｫ辷ｪ繧貞剱繧髻ｳ縲∫音螳壹・繝上・繝悶・鬥吶ｊ縺ｸ縺ｮ蝓ｷ逹縲｀C縺ｮ迚ｹ螳壹・莉戊拷縺ｫ蟇ｾ縺吶ｋ逕溽炊逧・ｫ梧が・峨・n\n"
            "縲仙ｿ・亥・蜉幃・岼縲曾n"
            "- registry_data蜀・・ expansion_hooks 縺ｯ譛菴・縺､莉･荳翫∝・菴鍋噪縺九▽繝輔ぉ繝・ぅ繝・す繝･縺ｫ險倩ｿｰ縺帙ｈ縲・n"
            "- dialogue_samples 縺ｯ縲√◎縺ｮ繧ｭ繝｣繝ｩ縺ｮ縲守音逡ｰ縺ｪ諤晁・屓霍ｯ縲上′貍上ｌ蜃ｺ縺吶そ繝ｪ繝輔ｒ3縺､莉･荳翫∽ｸ莠ｺ遘ｰ繝ｻ莠御ｺｺ遘ｰ繧貞宍螳医＠縺ｦ險倩ｿｰ縺帙ｈ縲・n"
            "- relationships 縺ｫ縺ｯ縲｀C縺縺代〒縺ｪ縺冗函謌舌☆繧倶ｻ悶・繧ｵ繝悶く繝｣繝ｩ蜷悟｣ｫ縺ｮ縲守ｧ伜ｯ・・逶ｸ髢｢髢｢菫ゅ上ｒ蜷ｫ繧√ｈ縲・n\n"
            "Output Schema (JSON):\n"
            f'{{"characters": [{CharacterRegistry.model_json_schema()}]}}'
        )

    def build_bible_creation_prompt(self, bible_core_schema: BaseModel, world_rules_json: str, concept: str, target_eps: int) -> str:
        return (
            f"縺ゅ↑縺溘・蝠・畑蜃ｺ迚医〒繝溘Μ繧ｪ繝ｳ繧ｻ繝ｩ繝ｼ繧帝｣逋ｺ縺吶ｋ莨晁ｪｬ縺ｮ繧ｨ繝・ぅ繧ｿ繝ｼ縺ｧ縺吶ょ・{target_eps}隧ｱ縺ｮ莨∫判譖ｸ繧偵∵兜雉・ｮｶ繧貞蛤繧峨○繧九Ξ繝吶Ν縺ｮ縲瑚ｦ・ｨｩ險ｭ險亥峙縲阪→縺励※螳梧・縺輔○縺ｦ縺上□縺輔＞縲・n\n"
            f"縲蝉ｸ也阜險ｭ螳壹・ {world_rules_json}\n"
            f"縲舌さ繝ｳ繧ｻ繝励ヨ縲・ {concept}\n\n"
            "謖・ｻ､:\n"
            "**蜈ｨ縺ｦ縺ｮ鬆・岼・医≠繧峨☆縺倥√さ繝ｳ繧ｻ繝励ヨ遲会ｼ峨ｒ譌･譛ｬ隱槭〒蜃ｺ蜉帙○繧医・*\n"
            "1. 縲宣ｭゅ・謨第ｸ医・繝ｫ繧ｽ繝翫・ 隱ｭ閠・′迴ｾ螳滉ｸ也阜縺ｧ謚ｱ縺医ｋ縺ｩ縺ｮ繧医≧縺ｪ谺關ｽ繧偵√％縺ｮ迚ｩ隱槭′蝓九ａ繧九・縺具ｼ井ｸ・・諢溘∝ｾｩ隶舌∵価隱肴ｬｲ豎ゑｼ峨ｒ邊ｾ逾槫・譫舌Ξ繝吶Ν縺ｧ隧ｳ邏ｰ縺ｫ蛻・梵縺帙ｈ縲・n"
            "2. 縲千黄隱槭・霆｢謠帷せ・磯ｪｨ蟄撰ｼ峨・ 隱ｭ閠・・莠域Φ繧定｣丞・繧翫∬┻豎√′貅｢繧悟・縺吶瑚｡晄茶縺ｮ螻暮幕縲阪ｒ蜈ｷ菴鍋噪縺ｫ3縺､謖・ｮ壹○繧医・n"
            "3. 縲仙・菴薙≠繧峨☆縺倥・ 1隧ｱ縺九ｉ譛邨りｩｱ縺ｾ縺ｧ縺ｮ諢滓ュ縺ｮ襍ｷ莨擾ｼ医せ繝医Ξ繧ｹ縺ｨ繧ｫ繧ｿ繝ｫ繧ｷ繧ｹ・峨ｒ, 霆｢謠帷せ縺梧・遒ｺ縺ｫ縺ｪ繧九ｈ縺・500譁・ｭ嶺ｻ･荳翫〒隧ｳ邏ｰ縺ｫ謠上￠縲ょ・鬆ｭ3陦後・蠑ｷ辜医↑繝輔ャ繧ｯ縺九ｉ蟋九ａ繧九％縺ｨ縲・n"
            "4. 縲仙膚讌ｭ逧・音逡ｰ轤ｹ縲・ 譌｢蟄倥・鬘樔ｼｼ菴懊→菴輔′豎ｺ螳夂噪縺ｫ逡ｰ縺ｪ繧翫∵悽菴懊□縺代・縲後ち繝悶・縲阪ｄ縲梧眠縺励＞鄒主ｭｦ・・SP・峨阪′縺ｩ縺薙↓縺ゅｋ縺九ｒ譏守､ｺ縺帙ｈ縲・n"
            f"Output Schema: {bible_core_schema.model_json_schema()}"
        )

    def build_marketing_ab_test_prompt(self, bible_core_concept: str) -> str:
        return (
            f"繧ｫ繧ｯ繝ｨ繝縺ｧ譛繧ゅけ繝ｪ繝・け縺輔ｌ繧九後ち繧､繝医Ν縲阪→縲後ち繧ｰ縲阪ｒ驕ｸ螳壹＠縺ｦ縺上□縺輔＞縲・*蠢・★譌･譛ｬ隱槭〒蝗樒ｭ斐☆繧九％縺ｨ縲・*\n"
            "繧ｿ繧､繝医Ν縺ｯWeb蟆剰ｪｬ迚ｹ譛峨・縲後≠繧峨☆縺倥ｒ蜈ｼ縺ｭ縺滄聞譁・ち繧､繝医Ν・・0譁・ｭ礼ｨ句ｺｦ・峨阪→縺励∝ｼｷ縺・ｼ輔″・医ヵ繝・け・峨ｒ蜷ｫ繧√ｋ縺薙→縲・n"
            "縲植B繝・せ繝域姶逡･縲台ｻ･荳九・3縺､縺ｮ逡ｰ縺ｪ繧区婿蜷第ｧ縺ｧ繧ｿ繧､繝医Ν譯医ｒ菴懈・縺帙ｈ縲・n"
            "  1. 縺悶∪縺√・繧ｫ繧ｿ繝ｫ繧ｷ繧ｹ迚ｹ蛹厄ｼ郁ｪｭ閠・・蠕ｩ隶仙ｿ・ｒ辣ｽ繧具ｼ噂n"
            "  2. 譌･蟶ｸ繝ｻ繧ｮ繝｣繝・・關後∴迚ｹ蛹厄ｼ育┌閾ｪ隕壽怙蠑ｷ繧・せ繝ｭ繝ｼ繝ｩ繧､繝輔ｒ蠑ｷ隱ｿ・噂n"
            "  3. 邇矩％繝ｻ譛蠑ｷ迚ｹ蛹厄ｼ亥悸蛟堤噪縺ｪ蜉帙→謌舌ｊ荳翫′繧翫ｒ蠑ｷ隱ｿ・噂n"
            "縲舌ち繧ｰ・・EO譛驕ｩ蛹厄ｼ峨大推譯医・繧ｿ繧ｰ縺ｫ縺ｯ縲後＊縺ｾ縺√阪瑚ｿｽ謾ｾ縲阪御ｸｻ莠ｺ蜈ｬ譛蠑ｷ縲阪→縺・▲縺溯ｶ・ｺｺ豌玲､懃ｴ｢繧ｭ繝ｼ繝ｯ繝ｼ繝峨→縲√ル繝・メ縺ｪ螻樊ｧ繧ｿ繧ｰ繧偵ヰ繝ｩ繝ｳ繧ｹ濶ｯ縺・0蛟句性繧√ｋ縺薙→縲・n"
            f"繧ｳ繝ｳ繧ｻ繝励ヨ: {bible_core_concept}\n"
            "Output Schema (JSON):\n"
            '{"ab_test_candidates": [{"title": "...", "tags": ["..."], "ctr_reason": "譬ｹ諡"}], "winning_index": 0}'
        )

    def build_roadmap_prompt(self, bible_core_title: str, bible_core_synopsis: str, target_eps: int, roadmap_list_schema: BaseModel) -> str:
        return (
            f"繧ｿ繧､繝医Ν: {bible_core_title}\n縺ゅｉ縺吶§: {bible_core_synopsis}\n\n"
            f"蜈ｨ{target_eps}隧ｱ縺ｮ螻暮幕繝ｭ繝ｼ繝峨・繝・・繧堤函謌舌○繧医・*繝ｭ繝ｼ繝峨・繝・・縺ｮ蜀・ｮｹ縺ｯ縺吶∋縺ｦ譌･譛ｬ隱槭〒險倩ｿｰ縺吶ｋ縺薙→縲・*\n"
            f"Output Schema: {roadmap_list_schema.model_json_schema()}"
        )

    def build_plot_expansion_prompt(self, book_title: str, ep_num: int, ep_info: Dict[str, Any], past_plots: List[Any], arcs: List[Any], book_genre: str) -> str:
        def safe_dict(obj: Any) -> Dict[str, Any]:
            if isinstance(obj, dict):
                return obj
            if hasattr(obj, 'model_dump'):
                return obj.model_dump()
            if hasattr(obj, 'dict'):
                return obj.dict()
            return {k: getattr(obj, k) for k in ['arc_num', 'title', 'start_ep', 'end_ep', 'one_line_summary', 'resolution_style', 'burned_cost_or_loot', 'thematic_milestone', 'antagonist_status'] if hasattr(obj, k)}

        past_plots_str = "\n".join([f"- 隨ｬ{getattr(p, 'ep_num', '?')}隧ｱ: {getattr(p, 'summary', '譛ｪ螳夂ｾｩ')}" for p in past_plots]) if past_plots else "縺ｪ縺・

        def fmt_arc(a):
            # Pydantic繝｢繝・Ν縺ｪ繧芽ｾ樊嶌縺ｫ螟画鋤縲√◎縺・〒縺ｪ縺代ｌ縺ｰ霎樊嶌縺ｨ縺励※謇ｱ縺・            if hasattr(a, "model_dump") and callable(a.model_dump):
                d = a.model_dump()
            elif hasattr(a, "dict") and callable(a.dict):
                d = a.dict()
            else:
                d = a

            arc_num = d.get('arc_num', '?') if isinstance(d, dict) else getattr(d, 'arc_num', '?')
            title   = d.get('title', '辟｡鬘・) if isinstance(d, dict) else getattr(d, 'title', '辟｡鬘・)
            start   = d.get('start_ep', '?') if isinstance(d, dict) else getattr(d, 'start_ep', '?')
            end     = d.get('end_ep', '?') if isinstance(d, dict) else getattr(d, 'end_ep', '?')
            return f"- Arc {arc_num}: {title} (Ep {start}-{end})"

        arcs_str = "\n".join([fmt_arc(a) for a in arcs]) if arcs else "縺ｪ縺・

        ep_info_dict = safe_dict(ep_info)
        return (
            f"縺ゅ↑縺溘・繧ｫ繧ｯ繝ｨ繝縺ｧ繝ｩ繝ｳ繧ｭ繝ｳ繧ｰ1菴阪ｒ迯ｲ繧九◆繧√・繝励Ο繝・ヨ險ｭ險郁・〒縺吶・n"
            f"菴懷刀繧ｿ繧､繝医Ν: {book_title}\n"
            f"繧ｸ繝｣繝ｳ繝ｫ: {book_genre}\n"
            f"縲千ｬｬ{ep_num}隧ｱ 隧ｳ邏ｰ繝励Ο繝・ヨ險ｭ險医曾n"
            f"縺薙・隧ｱ縺ｮ繝ｭ繝ｼ繝峨・繝・・讎りｦ・ {ep_info_dict.get('one_line_summary', '譛ｪ螳夂ｾｩ')}\n"
            f"隗｣豎ｺ繧ｹ繧ｿ繧､繝ｫ: {ep_info_dict.get('resolution_style', 'Cheat')}\n"
            f"豸郁ｲｻ繧ｳ繧ｹ繝・迯ｲ蠕礼黄: {ep_info_dict.get('burned_cost_or_loot', '縺ｪ縺・)}\n"
            f"繝・・繝樒噪遽逶ｮ: {ep_info_dict.get('thematic_milestone', '縺ｪ縺・)}\n"
            f"謨ｵ蟇ｾ閠・憾豕・ {ep_info_dict.get('antagonist_status', '迴ｾ迥ｶ邯ｭ謖・)}\n\n"
            f"縲宣℃蜴ｻ縺ｮ繝励Ο繝・ヨ縲曾n{past_plots_str}\n\n"
            f"縲舌い繝ｼ繧ｯ讒区・縲曾n{arcs_str}\n\n"
            f"縲先欠莉､縲曾n"
            f"1. [thought_process]: 3繧ｹ繝・ャ繝玲晁・ｼ育泝逶ｾ讀懆ｨｼ縲∝渚險ｼ縲∫ｵｱ蜷育ｵ占ｫ厄ｼ峨ｒ陦後∴縲・n"
            f"2. [title]: 隨ｬ{ep_num}隧ｱ縺ｮ繧ｵ繝悶ち繧､繝医Ν繧定・｡医○繧医・n"
            f"3. [summary]: 隱ｭ閠・・闊亥袖繧貞ｼ輔￥荳陦後≠繧峨☆縺倥ｒ險倩ｿｰ縺帙ｈ縲・n"
            f"4. [detailed_blueprint]: 2000譁・ｭ嶺ｻ･荳翫・雜・ｩｳ邏ｰ縺ｪ繧ｷ繝ｼ繝ｳ險ｭ險亥峙繧剃ｽ懈・縺帙ｈ縲りｵｷ謇ｿ霆｢邨舌・豬√ｌ縲∫憾豕√・螟牙喧縲√く繝｣繝ｩ縺ｮ陦悟虚繧貞・菴鍋噪縺ｫ險倩ｿｰ縺帙ｈ縲・n"
            f"5. [scenes]: detailed_blueprint縺ｫ蝓ｺ縺･縺阪｀asterSceneBlock縺ｮ繝ｪ繧ｹ繝医ｒ逕滓・縺帙ｈ縲ょ推繧ｷ繝ｼ繝ｳ縺ｫ縺ｯ蜈ｷ菴鍋噪縺ｪ陦悟虚(action)縲・㍾隕√↑莨夊ｩｱ縺ｮ隕∫せ(dialogue_point)縲∵─諠・噪邨先忰(emotional_payoff)縲√◎縺励※隧ｳ邏ｰ縺ｪ繝薙・繝・beats)繧貞性繧√ｈ縲・n"
            f"   窶ｻ驥崎ｦ・ [beats] 蜀・・蜷・・岼縺ｯ縲∝ｿ・★ 'beat_type'・亥ｰ主・/螻暮幕/邨先忰/迥ｶ豕・蜀・擇闡幄陸/蜈ｷ菴鍋噪陦悟虚/菴咎渊縺九ｉ驕ｸ謚橸ｼ峨→ 'action_description'・・50譁・ｭ嶺ｻ･荳翫・謠丞・隧ｳ邏ｰ・峨ｒ逵∫払縺帙★縺ｫ蜷ｫ繧√ｋ縺薙→縲・n"
            f"6. [next_hook]: 隱ｭ閠・′蜊ｳ蠎ｧ縺ｫ谺｡繧偵け繝ｪ繝・け縺励◆縺上↑繧句ｼｷ辜医↑繧ｯ繝ｪ繝輔ワ繝ｳ繧ｬ繝ｼ繧剃ｽ懈・縺帙ｈ縲・n"
            f"7. [stress], [catharsis], [is_catharsis], [catharsis_type], [tension], [love_meter]: 迚ｩ隱槭・諢滓ュ譖ｲ邱壹↓豐ｿ縺｣縺ｦ驕ｩ蛻・↑蛟､繧定ｨｭ螳壹○繧医・n"
            f"8. [emotional_payoff]: 縺薙・隧ｱ縺ｧ隱ｭ閠・′蠕励ｋ縺ｹ縺肴─諠・噪縺ｪ蝣ｱ驟ｬ繧定ｨ倩ｿｰ縺帙ｈ縲・n"
            f"9. [misunderstanding_gap]: 繧ゅ＠縲主鋸驕輔＞縲上・隕∫ｴ縺後≠繧句ｴ蜷医√◎縺ｮ荵夜屬蜀・ｮｹ繧定ｨ倩ｿｰ縺帙ｈ縲・n"
            f"10. [lite_model_director_notes]: 逕滓・縺励◆繝励Ο繝・ヨ縺ｮ蠑ｱ轤ｹ繧・∝濤遲・ヵ繧ｧ繝ｼ繧ｺ縺ｸ縺ｮ菫ｮ豁｣謖・､ｺ縺後≠繧後・險倩ｿｰ縺帙ｈ縲・n"
            f"11. [script_content]: detailed_blueprint縺ｫ蝓ｺ縺･縺阪∽ｼ夊ｩｱ縺ｨ陦悟虚謖・､ｺ縺ｮ縺ｿ縺ｮ蜿ｰ譛ｬ譯医ｒ逕滓・縺帙ｈ縲・n"
            f"11. [current_chain_phase]: 縺薙・隧ｱ縺後皐ate縲上傘rep縲上傘ayoff縲上・縺ｩ縺ｮ繝輔ぉ繝ｼ繧ｺ縺ｫ蠖薙◆繧九°謖・ｮ壹○繧医・n"
            f"Output Schema (JSON):\n"
            f"{PlotEpisode.model_json_schema()}"
        )
    def build_rebuild_plot_outline_prompt(self, book_title: str, start_ep: int, new_total_eps: int, book_synopsis: str, keywords: str, trend_memo: str, pending_foreshadowing: List[str]) -> str:
        return (
            f"縺ゅ↑縺溘・縲檎黄隱樊ｧ矩縺ｫ邊ｾ騾壹＠縺溘・繝ｭ縺ｮ邱ｨ髮・・阪〒縺吶・n"
            f"莨∫判縲施book_title}縲上・騾｣霈牙ｻｶ髟ｷ繝ｻ繝・さ蜈･繧後↓莨ｴ縺・・繝ｭ繝・ヨ蜀肴ｧ狗ｯ峨ｒ陦後＞縺ｾ縺吶・n"
            f"縲千ｬｬ{start_ep}隧ｱ縲懃ｬｬ{new_total_eps}隧ｱ縺ｾ縺ｧ縲代・遶・医い繝ｼ繧ｯ・峨ｒ荳諡ｬ縺ｧ菴懈・縺帙ｈ縲・n\n"
            f"縲千樟蝨ｨ縺ｮ縺ゅｉ縺吶§縲・ {book_synopsis}\n"
            f"縲占ｿｽ蜉繧ｭ繝ｼ繝ｯ繝ｼ繝峨・ {keywords}\n"
            f"縲占ｿｽ蜉隕∫ｴ繝ｻ繝医Ξ繝ｳ繝峨・ {trend_memo}\n"
            f"縲先悴蝗槫庶縺ｮ莨冗ｷ壹・ {', '.join(pending_foreshadowing[:5])}\n\n"
            "Output Schema (JSON):\n"
            '{"arcs": [{"arc_num": 1, "start_ep": 1, "end_ep": 10, "title": "...", "summary": "..."}]}'
        )

    def build_amplify_prompt(self, final_content: str, current_target_word_count: int, fix_inst: str = "") -> str:
        return (
            f"縺ゅ↑縺溘・隱ｭ閠・ｒ迚ｩ隱槭↓豐｡蜈･縺輔○繧句､ｩ謇咲噪縺ｪ謗ｨ謨ｲ螳倥〒縺吶ゆｻ･荳九・縲先悽譁・代ｒ縲∝・縺ｮ譁・ｫ縺ｮ譁・ц縺ｨ閾ｪ辟ｶ縺ｫ謗･邯壹＠縲・
            f"縺九▽蠢・炊繝ｻ莠疲─謠丞・繧呈･ｵ髯舌∪縺ｧ鬮倥ａ繧句ｽ｢縺ｧ蜉遲・ｿｮ豁｣縺励※縺上□縺輔＞縲ょ・縺ｮ譁・ｫ繧剃ｸ蛻・炎繧峨★縲・
            f"逶ｮ讓呎枚蟄玲焚 {current_target_word_count} 譁・ｭ励↓驕斐☆繧九∪縺ｧ縲・＆蜥梧─縺ｪ縺乗緒蜀吶ｒ諡｡蠑ｵ縺帙ｈ縲・
            f"{fix_inst}\n\n縲先悽譁・曾n{final_content}"
        )

    def build_analyze_import_chapter_prompt(self, cleaned_content: str, episode_draft_schema: BaseModel) -> str:
        return (
            "莉･荳九・蟆剰ｪｬ譛ｬ譁・ｒ蛻・梵縺励√Γ繧ｿ繝・・繧ｿ繧呈歓蜃ｺ縺帙ｈ縲・n"
            f"譛ｬ譁・ {cleaned_content[:5000]}\n"
            f"Output Schema (JSON): {episode_draft_schema.model_json_schema()}"
        )

    def build_critique_quality_prompt(self, book_title: str, summary_data_json: str) -> str:
        return (
            "縺ゅ↑縺溘・荳也阜譛鬮伜ｳｰ縺ｮ譁・敢隧戊ｫ門ｮｶ縺ｧ縺ゅｊ縲、I繧ｨ繝ｳ繧ｸ繝九い縺ｧ縺吶・n"
            f"菴懷刀繧ｿ繧､繝医Ν: {book_title}\n"
            f"縲千函謌舌ョ繝ｼ繧ｿ縲曾n{summary_data_json}\n\n"
            "莉･荳九・隕ｳ轤ｹ縺ｧ繧ｨ繝ｳ繧ｸ繝ｳ縺ｮ縲手ｨｭ螳壼､縲上ｄ縲弱・繝ｭ繝ｳ繝励ヨ縲上∈縺ｮ謾ｹ蝟・｡医ｒ謠先｡医＠縺ｦ縺上□縺輔＞・喀n"
            "1. 繝励Ο繝・ヨ縺ｮ蜀咲樟諤ｧ・郁ｨｭ險亥峙騾壹ｊ縺ｮ蟇・ｺｦ縺ｧ譖ｸ縺九ｌ縺ｦ縺・ｋ縺具ｼ噂n"
            "2. 諢滓ュ譖ｲ邱壹・螯･蠖捺ｧ・医せ繝医Ξ繧ｹ闢・ｩ阪→繧ｫ繧ｿ繝ｫ繧ｷ繧ｹ縺ｮ繧ｿ繧､繝溘Φ繧ｰ・噂n"
            "3. 隱槫ｽ吶・驥崎､・ｄAI迚ｹ譛峨・逋悶・譛臥┌\n"
            "4. config.py 繧・engine_prompts.py 縺ｧ菫ｮ豁｣縺吶∋縺榊・菴鍋噪縺ｪ繝代Λ繝｡繝ｼ繧ｿ"
        )

    def build_iterative_gap_analysis_prompt(self, book_genre: str, book_title: str, batch_data: str) -> str:
        return (
            "縺ゅ↑縺溘・AI蟆剰ｪｬ繧ｨ繝ｳ繧ｸ繝ｳ縺ｮ繝ｪ繝ｼ繝画怙驕ｩ蛹悶お繝ｳ繧ｸ繝九い縺ｧ縺吶・n"
            f"繧ｸ繝｣繝ｳ繝ｫ縲施book_genre}縲上・菴懷刀縲施book_title}縲上・蜈ｨ繧ｨ繝斐た繝ｼ繝峨↓縺翫￠繧九手ｨｭ險亥峙縺ｨ譛ｬ譁・・荵夜屬縲上ｒ讓ｪ譁ｭ逧・↓蛻・梵縺励√お繝ｳ繧ｸ繝ｳ縺ｮ譬ｹ譛ｬ逧・↑蠑ｱ轤ｹ繧堤音螳壹＠縺ｦ縺上□縺輔＞縲・n\n"
            + batch_data + "\n\n"
            "### 譛邨ゅΞ繝昴・繝郁ｦ∵ｱゆｺ矩・ｼ磯㍾隕・ｼ哽SON繧ｭ繝ｼ蜷阪・蠢・★莉･荳九・闍ｱ蜊倩ｪ槭ｒ邯ｭ謖√＠縲∫ｿｻ險ｳ縺励↑縺・〒縺上□縺輔＞・・###\n"
            "蠢・★莉･荳九・繧ｭ繝ｼ繧呈戟縺､JSON蠖｢蠑上・縺ｿ縺ｧ蜃ｺ蜉帙＠縺ｦ縺上□縺輔＞・医・繝ｼ繧ｯ繝繧ｦ繝ｳ縺ｮ陬・｣ｾ縺ｯ荳崎ｦ√〒縺呻ｼ峨・n"
            "- habits: 蜈ｨ隧ｱ繧帝壹§縺ｦ蜈ｱ騾壹＠縺ｦ隕九ｉ繧後ｋ縲、I縺梧欠遉ｺ繧堤┌隕悶＠縺溘ｊ逵∫払縺励◆繧翫☆繧九ヱ繧ｿ繝ｼ繝ｳ縺ｮ蛻・梵\n"
            "- style_gap: 譁・ｽ泥NA縺ｮ荵夜屬繝ｬ繝昴・繝・n"
            "- config_patch: config.py縺ｸ縺ｮ菫ｮ豁｣譯茨ｼ医く繝ｼ:蛟､ 縺ｮ繝壹い繧定ｨ倩ｿｰ・噂n"
            "- prompt_patch: 蝓ｷ遲・・繝ｭ繝ｳ繝励ヨ縺ｫ霑ｽ蜉縺吶∋縺阪悟ｼｷ蛻ｶ蜉帙・縺ゅｋ荳譁・構n"
            "- refactor_instruction: 繧ｳ繝ｼ繝・ぅ繝ｳ繧ｰAI縺ｸ縺ｮ蜻ｽ莉､譁・ゅお繝ｳ繧ｸ繝ｳ縺ｮ繝ｭ繧ｸ繝・け閾ｪ菴難ｼ・ngine_agents.py繧гanitizer.py遲会ｼ峨ｒ縺ｩ縺・隼騾縺吶∋縺阪°蜈ｷ菴鍋噪縺ｪ謖・､ｺ繧貞・蜉帙○繧医・*驥崎ｦ・ｼ壹％縺ｮ謾ｹ蝟・｡医′縲施book_genre}縲冗音譛峨・諤ｧ雉ｪ縺ｫ蝓ｺ縺･縺丞ｴ蜷医∝・繧ｸ繝｣繝ｳ繝ｫ縺ｫ謔ｪ蠖ｱ髻ｿ縺悟・縺ｪ縺・ｈ縺・∝ｿ・★縲後ず繝｣繝ｳ繝ｫ縺鶏book_genre}縺ｮ蝣ｴ蜷医・縺ｿ驕ｩ逕ｨ縺吶ｋ縲阪→縺・≧譚｡莉ｶ蛻・ｲ撰ｼ・f-else遲会ｼ峨ｒ蜷ｫ繧√◆繧ｳ繝ｼ繝我ｿｮ豁｣譯医↓縺吶ｋ縺薙→縲・*\n"
            "- scores: { \"plot_adherence\": 0-100, \"style_consistency\": 0-100, \"detail_density\": 0-100 }\n"
            "\n萓・ { \"habits\": \"AI縺ｯ蠢・炊謠丞・繧医ｊ繧ら憾豕∬ｪｬ譏弱ｒ蜆ｪ蜈医☆繧句だ蜷代′縺ゅｋ...\", \"scores\": { \"plot_adherence\": 85, ... } }"
        )

    def build_dry_run_prompt(self, ep_num: int, improved_prompt: str, plot_detailed_blueprint: str, plot_script_content: str) -> str:
        return (
            f"縲織RY-RUN TEST縲台ｻ･荳九・霑ｽ蜉謖・､ｺ繧呈怙蜆ｪ蜈医＠縺ｦ縲∫ｬｬ{ep_num}隧ｱ繧貞・蝓ｷ遲・○繧医・n"
            f"霑ｽ蜉謖・､ｺ: {improved_prompt}\n\n"
            f"繝励Ο繝・ヨ險ｭ險亥峙: {plot_detailed_blueprint}\n"
            f"蜿ｰ譛ｬ: {plot_script_content}\n"
        )

