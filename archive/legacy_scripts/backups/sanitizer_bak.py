"""
sanitizer.py - AI蜃ｺ蜉帑ｿｮ蠕ｩ繝ｻ讀懆ｨｼ繝｢繧ｸ繝･繝ｼ繝ｫ
AI縺瑚ｿ斐☆螢翫ｌ縺櫟SON縺ｮ菫ｮ蠕ｩ縲√Γ繧ｿ繝・・繧ｿ豁｣隕丞喧縲・繝・く繧ｹ繝亥刀雉ｪ讀懆ｨｼ・郁ｦ也せ繝ｻ繝ｪ繧ｺ繝繝ｻ蜿｣隱ｿ・峨ｒ諡・≧縲・"""
from __future__ import annotations
import json
import re
import logging
from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, List, Optional, Tuple

from models import CharacterRegistry

logger = logging.getLogger(__name__)

CONTENT_SEPARATOR = "### NOVEL CONTENT ###"

# ==========================================
# TonePerfector・亥哨隱ｿ蠑ｷ蛻ｶ陬懈ｭ｣・・# ==========================================
class TonePerfector:
    """繧ｭ繝｣繝ｩ繧ｯ繧ｿ繝ｼ縺ｮ蜿｣隱ｿ繝ｻ荳莠ｺ遘ｰ繝ｻ莠御ｺｺ遘ｰ繧奪B險ｭ螳壹↓蝓ｺ縺･縺榊ｼｷ蛻ｶ鄂ｮ謠帙☆繧・""
    
    @staticmethod
    def enforce_tone(text: str, characters: List[CharacterRegistry]) -> str:
        for char in characters:
            if not char.name: continue
            
            # 蜿ｰ隧槫・縺ｮ莠ｺ遘ｰ鄂ｮ謠帙Ο繧ｸ繝・け
            def replace_pronouns(match):
                dialogue = match.group(0)
                # 荳莠ｺ遘ｰ縺ｮ蠑ｷ蛻ｶ鄂ｮ謠幢ｼ・I縺碁俣驕輔∴繧・☆縺・◆繧・ｼ・                if char.first_person:
                    dialogue = re.sub(r'(遘－蜒怖菫ｺ|縺ゅ◆縺慾閾ｪ蛻・(?=[縲√ゑｼ・ｼ溘％縺ｨ縲ゅｒ縺ｫ縺後江)', char.first_person, dialogue)
                # 莠御ｺｺ遘ｰ縺ｮ蠑ｷ蛻ｶ鄂ｮ謠・                if char.second_person:
                    dialogue = re.sub(r'(蜷斈縺ゅ↑縺毫縺雁燕|雋ｴ讒・(?=[縲√ゑｼ・ｼ溘ｒ縺ｫ縺後江)', char.second_person, dialogue)
                
                # 隱槫ｰｾ縺ｮ邁｡譏楢｣懈ｭ｣・井ｾ具ｼ壹↑縺ｮ縺縲√□繧上√〒縺吶ｏ遲会ｼ・                if char.suffix_style:
                    # 譁・忰縺ｮ縲後□縲ゅ阪後ゅ阪鯉ｼ√咲ｭ峨ｒ讀懃衍縺励※隱槫ｰｾ繧剃ｻ倅ｸ弱☆繧狗ｰ｡譏鍋噪縺ｪ莉慕ｵ・∩
                    # 螳滄圀縺ｫ縺ｯ繧医ｊ鬮伜ｺｦ縺ｪ蠖｢諷狗ｴ隗｣譫舌′蠢・ｦ√□縺後√％縺薙〒縺ｯAI縺ｮ陬懷ｮ後→縺励※蜍穂ｽ・                    if "縲・ in char.suffix_style:
                        suffix = char.suffix_style.replace("縲・, "")
                        dialogue = re.sub(r'([縲ゑｼ滂ｼ‐)(?=縲・', f"{suffix}\\1", dialogue)
                
                return dialogue

            # 莨夊ｩｱ譁・ｼ医後榊・・峨ｒ謚ｽ蜃ｺ縺励※鄂ｮ謠帙ｒ驕ｩ逕ｨ
            text = re.sub(r'縲・*?縲・, replace_pronouns, text, flags=re.DOTALL)
            
        return text

# OutputSanitizer・・SON菫ｮ蠕ｩ繝ｻ繝｡繧ｿ繝・・繧ｿ豁｣隕丞喧・・# ==========================================
class OutputSanitizer:
    """AI蜃ｺ蜉帙・菫ｮ蠕ｩ繝ｻ豁｣隕丞喧繧呈球縺・撕逧・Θ繝ｼ繝・ぅ繝ｪ繝・ぅ繧ｯ繝ｩ繧ｹ"""

    @staticmethod
    def parse_llm_json(text: str) -> Dict[str, Any]:
        """
        LLM縺ｮ蜃ｺ蜉帙°繧雨SON驛ｨ蛻・ｒ謚ｽ蜃ｺ縺励∽ｿｮ蠕ｩ縺励※繝代・繧ｹ縺吶ｋ縲・        """
        if not text:
            return {}
        # 譛繧ょ､門・縺ｮ豕｢諡ｬ蠑ｧ繧呈歓蜃ｺ・・LM縺悟燕蠕後↓繝・く繧ｹ繝医ｒ莉倥￠縺ｦ繧ょｯｾ蠢懶ｼ・        json_match = re.search(r'(\{.*\})', text.strip(), re.DOTALL)
        if not json_match:
            return {}
            
        try:
            raw_json = OutputSanitizer.fix_json(json_match.group(0))
            return json.loads(raw_json)
        except Exception as e:
            logger.error(f"JSON Parse Error: {e}")
            return {}

    @staticmethod
    def extract_content_and_metadata(text: str) -> Tuple[Dict[str, Any], str]:
        """
        譛ｬ譁・→繝｡繧ｿ繝・・繧ｿJSON繧貞ｮ牙・縺ｫ蛻・屬縺励※霑斐☆縲・        繧ｻ繝代Ξ繝ｼ繧ｿ繝ｼ蠖｢蠑・竊・JSON譛ｫ蟆ｾ謚ｽ蜃ｺ 竊・繝励Ξ繝ｼ繝ｳ繝・く繧ｹ繝・縺ｮ鬆・〒繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ縲・        """
        if not text:
            return {}, ""

        # 1. 繧ｻ繝代Ξ繝ｼ繧ｿ繝ｼ蠖｢蠑擾ｼ域怙蜆ｪ蜈茨ｼ・        if CONTENT_SEPARATOR in text:
            parts = text.split(CONTENT_SEPARATOR)
            if len(parts) >= 3:
                story_content = parts[1].strip()
                metadata = OutputSanitizer.parse_llm_json(parts[2])
                if metadata:
                    return OutputSanitizer.normalize_metadata(metadata), OutputSanitizer._clean_story(story_content)

        # 2. JSON譛ｫ蟆ｾ謚ｽ蜃ｺ
        metadata = OutputSanitizer.parse_llm_json(text)
        if metadata:
            # 譁・ｭ怜・縺ｮ譛蠕後↓縺ゅｋJSON繧峨＠縺埼Κ蛻・ｒ迚ｹ螳・            json_match = re.search(r'(\{.*\})(?:\s|`|#)*$', text.strip(), re.DOTALL)
            if json_match:
                story_content = (text[:json_match.start()] + text[json_match.end():]).strip()
                # [thought_process] 遲峨・繝悶Ο繝・け繧貞ｺ・ｯ・峇縺ｫ髯､蜴ｻ
                story_content = re.sub(r'\[(thought_process|DIRECTOR_NOTE|METADATA_JSON|CONTENT_SEPARATOR|SCENE|BEAT)\].*?(\n\n|\Z)', '', story_content, flags=re.DOTALL | re.IGNORECASE).strip()
                if len(story_content) < 50:
                    story_content = metadata.get("final_content") or metadata.get("script_content") or ""
                return OutputSanitizer.normalize_metadata(metadata), OutputSanitizer._clean_story(story_content)

        # 3. 繝励Ξ繝ｼ繝ｳ繝・く繧ｹ繝医ヵ繧ｩ繝ｼ繝ｫ繝舌ャ繧ｯ
        return {}, OutputSanitizer._clean_story(text)

    @staticmethod
    def _clean_story(text: str) -> str:
        """AI縺ｮ繝｡繧ｿ逋ｺ險繝ｻ菴呵ｨ医↑荳險繧貞炎髯､"""
        # 陦碁ｭ縺ｮ螳壼梛蜿･縺ｮ縺ｿ繧貞炎髯､縺励∵枚荳ｭ縺ｮ險闡峨・谿九☆
        meta_patterns = [
            r'^(?:JSON蠖｢蠑上〒蜃ｺ蜉帙＠縺ｾ縺處莠・ｧ｣縺励∪縺励◆|莉･荳九・繝励Ο繝・ヨ縺ｧ縺處謇ｿ遏･縺励∪縺励◆|莉･荳九↓蝓ｷ遲・＠縺ｾ縺處縺薙■繧峨′譛ｬ譁・〒縺處繝上う縲∝万繧薙〒|縺九＠縺薙∪繧翫∪縺励◆|閠・∴縺ｾ縺励◆|菫ｮ豁｣縺励∪縺励◆|謠蝉ｾ帙＆繧後◆.*?縺ｫ蝓ｺ縺･縺・※|縺九＠縺薙∪繧翫∪縺励◆縲・.*?$',
            r'^(隨ｬ.*隧ｱ|繧ｨ繝斐た繝ｼ繝・*|繧ｵ繝悶ち繧､繝医Ν.*)[:・咯.*$', # 驥崎､・☆繧九し繝悶ち繧､繝医Ν陦後ｒ髯､蜴ｻ
            r'^(?:\[METADATA_JSON\].*?)$',
            r'^(?:\[thought_process\].*?)$'
        ]
        for pat in meta_patterns:
            text = re.sub(pat, '', text, flags=re.MULTILINE | re.IGNORECASE)

        text = re.sub(r'\[(DIRECTOR_NOTE|thought_process)\].*?(?=' + re.escape(CONTENT_SEPARATOR) + r'|\[|\Z)', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = text.replace("[NOVEL_CONTENT]", "").replace("[METADATA_JSON]", "")
        text = text.replace(CONTENT_SEPARATOR, "")
        text = re.sub(r'\[RESERVE_DESCRIPTION:.*?\]', '', text) # 谿狗蕗縺励◆謠丞・莠育ｴ・ち繧ｰ繧貞炎髯､
        
        # 蜀・Κ讒矩繧ｿ繧ｰ・・SCENE X]遲会ｼ峨・髯､蜴ｻ縲ゅ◆縺縺励檎ｬｬ1隧ｱ縲阪↑縺ｩ縺ｮ繧ｿ繧､繝医Ν陦後・縲∝ｾ後↓譛ｬ譁・→縺励※菴ｿ縺・庄閭ｽ諤ｧ縺後≠繧九◆繧√・        # 譏弱ｉ縺九↓繝｡繧ｿ繝・・繧ｿ逧・↑險倩ｿｰ・・SCENE...]・峨・縺ｿ繧偵ち繝ｼ繧ｲ繝・ヨ縺ｫ縺吶ｋ
        text = re.sub(r'^[#\s\*]*\[(SCENE|Scene|繧ｷ繝ｼ繝ｳ|BEAT|Beat|繝薙・繝・\s*[\d荳莠御ｸ牙屁莠泌・荳・・荵晏香]+\]?[:・喀s\*]*.*$', '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        # 蝓ｷ遲・ヵ繧ｧ繝ｼ繧ｺ遲峨・繝悶Ο繝・け繧ｿ繧ｰ髯､蜴ｻ
        text = re.sub(r'\[(DIRECTOR_NOTE|METADATA_JSON|NOVEL_CONTENT|SCRIPT|PLOT|BEAT|ANALYSIS|REFINE)\].*$', '', text, flags=re.IGNORECASE | re.MULTILINE)

        # 蟄､遶九＠縺溘ヶ繝ｩ繧ｱ繝・ヨ繧ｿ繧ｰ [ ... ] 縺ｮ髯､蜴ｻ・・I縺ｮ蜀・Κ繝｡繝｢蟇ｾ遲厄ｼ・        text = re.sub(r'\[[^\]]{1,100}\]', '', text)

        # Markdown陬・｣ｾ險伜捷縺ｮ髯､蜴ｻ・亥ｰ剰ｪｬ譛ｬ譁・↓縺ｯ荳崎ｦ√↑繝懊・繝ｫ繝峨√う繧ｿ繝ｪ繝・け縲∵遠縺｡豸医＠邱夲ｼ・        text = re.sub(r'(\*\*|__|\*|_|~~)', '', text)
        
        # 蛹ｺ蛻・ｊ邱夲ｼ域ｰｴ蟷ｳ邱夲ｼ峨・髯､蜴ｻ
        text = re.sub(r'^\s*[-*#=_]{3,}\s*$', '', text, flags=re.MULTILINE)
            
        return re.sub(r'\n{4,}', '\n\n', text).strip()

    @staticmethod
    def normalize_metadata(data: Any, key_name: Optional[str] = None, is_root: bool = True) -> Any:
        """AI縺檎函謌舌☆繧九Γ繧ｿ繝・・繧ｿ讒矩縺ｮ謠ｺ繧鯉ｼ医ロ繧ｹ繝医・繧ｭ繝ｼ蜷搾ｼ峨ｒ蜷ｸ蜿弱＠縺ｦ豁｣隕丞喧縺吶ｋ"""
        if data is None or data == "":
            return {} if is_root else data

        # 繝ｫ繝ｼ繝郁ｦ∫ｴ縺瑚ｾ樊嶌縺ｧ縺ｪ縺・ｴ蜷医・謨第ｸ亥・逅・ｼ・str' object has no attribute 'get' 蟇ｾ遲厄ｼ・        if is_root and not isinstance(data, dict):
            return {"raw_data": data}

        if isinstance(data, list):
            normalized = [OutputSanitizer.normalize_metadata(item, key_name, is_root=False) for item in data]
            
            # 繝ｪ繧ｹ繝亥・縺ｮ隕∫ｴ縺梧枚蟄怜・縺ｮ蝣ｴ蜷医∵悄蠕・＆繧後ｋ霎樊嶌讒矩縺ｸ蠑ｷ蛻ｶ螟画鋤
            if key_name == "scenes":
                normalized = [{"action": x} if isinstance(x, str) else x for x in normalized]
            
            # 譁・ｭ怜・繝ｪ繧ｹ繝医ｒ繧ｪ繝悶ず繧ｧ繧ｯ繝医Μ繧ｹ繝医∈蠑ｷ蛻ｶ螟画鋤・・ydantic ValidationError 蟇ｾ遲厄ｼ・            if key_name == "climax_scenes":
                normalized = [{"event": x} if isinstance(x, str) else x for x in normalized]
            elif key_name == "foreshadowing_map":
                normalized = [{"description": x} if isinstance(x, str) else x for x in normalized]
            elif key_name == "scenes":
                normalized = [{"action": x} if isinstance(x, str) else x for x in normalized]
            elif key_name == "beats":
                normalized = [{"action_description": x} if isinstance(x, str) else x for x in normalized]
            elif key_name == "recovered_items":
                # 譁・ｭ怜・縺梧擂縺溷ｴ蜷医・ foreshadowing_id 縺ｨ縺励※謇ｱ縺・                normalized = [{"foreshadowing_id": x} if isinstance(x, str) else x for x in normalized]
            elif key_name == "missing_items":
                # 繧ｪ繝悶ず繧ｧ繧ｯ繝医′譚･縺溷ｴ蜷医・隱ｬ譏取枚繧呈歓蜃ｺ縺吶ｋ縺区枚蟄怜・蛹悶☆繧・                normalized = [x.get("description", str(x)) if isinstance(x, dict) else str(x) for x in normalized]
            elif key_name == "story_threads":
                normalized = [x if isinstance(x, dict) else {"description": str(x), "status": "Active", "setup_episode": 0} for x in normalized]
            
            # 繝ｭ繝ｼ繝峨・繝・・遲峨・繝ｪ繧ｹ繝医〒隧ｱ謨ｰ(ep_num)縺梧ｬ關ｽ縺励※縺・ｋ蝣ｴ蜷医・閾ｪ蜍戊｣懷ｮ・            if key_name in ["full_story_roadmap", "roadmap", "arc_roadmap", "plots"]:
                for i, item in enumerate(normalized):
                    if isinstance(item, dict) and "ep_num" not in item:
                        item["ep_num"] = i + 1

            if key_name == "scenes":
                for i, item in enumerate(normalized):
                    if isinstance(item, dict) and "scene_number" not in item:
                        item["scene_number"] = item.get("id") or item.get("no") or (i + 1)
            if key_name == "beats":
                # beat_type 縺ｮ豁｣隕丞喧・・A:迥ｶ豕・ -> "迥ｶ豕・ 縺ｪ縺ｩ・・                valid_types = ["蟆主・", "螻暮幕", "邨先忰", "迥ｶ豕・, "蜀・擇闡幄陸", "蜈ｷ菴鍋噪陦悟虚", "菴咎渊"]
                for item in normalized:
                    if isinstance(item, dict) and "beat_type" in item:
                        bt = str(item["beat_type"])
                        for vt in valid_types:
                            if vt in bt:
                                item["beat_type"] = vt
                                break
                    # 繧ｭ繝ｼ繝ｯ繝ｼ繝蛾｡槭′譁・ｭ怜・縺ｧ譚･縺溷ｴ蜷医・繝ｪ繧ｹ繝亥喧
                    for kw_field in ["sensory_keywords", "psychology_keywords"]:
                        if isinstance(item, dict) and kw_field in item:
                            val = item[kw_field]
                            if isinstance(val, str):
                                item[kw_field] = [x.strip() for x in re.split(r'[,縲‐', val) if x.strip()]

            return normalized
        if not isinstance(data, dict):
            return {} if is_root else data

        # NOTE: 蛟句挨縺ｮ繧ｭ繝ｼ蜷阪お繧､繝ｪ繧｢繧ｹ・・onsistent -> is_consistent 遲会ｼ峨・
        # models.py 縺ｮ AliasChoices 縺ｧ蜃ｦ逅・☆繧九◆繧√√％縺薙〒縺ｯ讒矩縺ｮ豁｣隕丞喧縺ｮ縺ｿ繧定｡後≧縲・
        # 譁・ｭ怜・蠑ｷ蛻ｶ螟画鋤
        force_str_keys = [
            "detailed_blueprint", "script_content", "final_content", "title", "one_line_summary",
            "magic_cost_and_taboo", "social_hierarchy_and_discrimination", 
            "geopolitics_and_economy", "religious_dogma_and_heresy", "rewrite_suggestion",
            "personality", "ability", "background", "tone", "iron_constraint", "summary", "keywords",
            "thought_process"
        ]
        for str_key in force_str_keys:
            if str_key in data:
                val = data[str_key]
                if val is None:
                    data[str_key] = ""
                elif isinstance(val, list):
                    # AI縺後Μ繧ｹ繝亥ｽ｢蠑上〒霑斐＠縺ｦ縺阪◆蝣ｴ蜷医・←蛻・↑蛹ｺ蛻・ｊ譁・ｭ励〒譁・ｭ怜・縺ｫ螟画鋤
                    sep = "\n\n" if any(x in str_key for x in ["content", "blueprint", "script"]) else ", "
                    data[str_key] = sep.join([str(x) for x in val])
                elif not isinstance(val, str):
                    data[str_key] = json.dumps(val, ensure_ascii=False)

        # next_hook 縺梧枚蟄怜・縺ｧ霑斐▲縺ｦ縺阪◆蝣ｴ蜷医・菫ｮ蠕ｩ
        if "next_hook" in data and isinstance(data["next_hook"], str):
            try:
                data["next_hook"] = json.loads(data["next_hook"])
            except:
                data["next_hook"] = {
                    "type": "New Crisis",
                    "description": data["next_hook"]
                }
        elif "next_hook" in data and data["next_hook"] is None:
            data["next_hook"] = {"type": "Quiet Foreshadowing", "description": "邯壹￥"}


        # 谿ｵ髫守噪繝阪せ繝郁ｧ｣髯､
        wrapper_keys = (
            "metadata", "response", "data", "plot", "episode_data", "plot_episode",
            "episode", "results", "output", "content", "roadmap", "arc_roadmap", "chapter"
        )
        for _ in range(10):
            if not isinstance(data, dict):
                break
            unwrapped = False
            if len(data) == 1:
                k = list(data.keys())[0]
                if k.lower() in wrapper_keys and isinstance(data[k], dict):
                    data = data[k]
                    unwrapped = True
            else:
                for wk in wrapper_keys:
                    if wk in data and isinstance(data[wk], dict):
                        inner = data.pop(wk)
                        for ik, iv in inner.items():
                            if ik not in data:
                                data[ik] = iv
                        unwrapped = True
                        break
            if not unwrapped:
                break

        # ep_num 繧ｨ繧､繝ｪ繧｢繧ｹ隗｣豎ｺ
        if "ep_num" not in data:
            for alias in ["episode_num", "episode_number", "episode", "ep_no", "ep", "no", "number", "chapter"]:
                if alias in data:
                    try:
                        val = data[alias]
                        data["ep_num"] = int(val) if isinstance(val, (int, float)) else int(re.search(r'\d+', str(val)).group())
                        break
                    except Exception:
                        pass

        # scene_number 繧ｨ繧､繝ｪ繧｢繧ｹ隗｣豎ｺ
        if "scene_number" not in data:
            for alias in ["scene_id", "id", "scene_no", "index", "sceneNumber"]:
                if alias in data:
                    try:
                        val = data[alias]
                        data["scene_number"] = int(val) if isinstance(val, (int, float)) else int(re.search(r'\d+', str(val)).group())
                        break
                    except Exception:
                        pass

        # severity 繧ｨ繧､繝ｪ繧｢繧ｹ繝ｻ豁｣隕丞喧 (Literal["Minor", "Major", "Critical"] 蟇ｾ遲・
        if "severity" in data:
            sev = str(data["severity"]).lower()
            if any(x in sev for x in ["critical", "閾ｴ蜻ｽ逧・, "high", "讌ｵ繧√※驥阪＞"]):
                data["severity"] = "Critical"
            elif any(x in sev for x in ["major", "驥榊､ｧ", "medium", "驥阪＞"]):
                data["severity"] = "Major"
            elif any(x in sev for x in ["minor", "霆ｽ蠕ｮ", "low", "霆ｽ縺・]):
                data["severity"] = "Minor"
            else:
                data["severity"] = "Minor"

        # 謨ｰ蛟､繧ｭ繝｣繧ｹ繝・        for num_key in ["stress_delta", "love_delta", "tension"]:
            if num_key in data and not isinstance(data[num_key], int):
                try:
                    data[num_key] = int(re.search(r'-?\d+', str(data[num_key])).group())
                except Exception:
                    data[num_key] = 0

        # detailed_blueprint 繧ｨ繧､繝ｪ繧｢繧ｹ
        if "detailed_blueprint" not in data:
            for alias in ["outline", "summary", "synopsis", "description", "body", "story"]:
                if alias in data and isinstance(data[alias], str) and len(data[alias]) > 50:
                    data["detailed_blueprint"] = data[alias]
                    break

        # final_content 繧ｨ繧､繝ｪ繧｢繧ｹ
        if "final_content" not in data:
            for alias in ["script_content", "story", "manuscript", "text", "body", "content"]:
                if alias in data and isinstance(data[alias], str) and len(data[alias]) > 100:
                    data["final_content"] = data[alias]
                    break

        # burned_cost_or_loot / antagonist_status 繝・ヵ繧ｩ繝ｫ繝・        is_story_obj = is_root or "one_line_summary" in data or "detailed_blueprint" in data
        if is_story_obj:
            if "burned_cost_or_loot" not in data:
                data["burned_cost_or_loot"] = "迚ｹ縺ｫ縺ｪ縺・
            if "antagonist_status" not in data:
                data["antagonist_status"] = "迴ｾ迥ｶ邯ｭ謖・

        # 蜀榊ｸｰ蜃ｦ逅・        for k, v in data.items():
            # current_chain_phase 縺ｮ豁｣隕丞喧
            if k == "current_chain_phase":
                val = str(v).lower()
                if any(x in val for x in ["hate", "stress", "邨ｶ譛・, "隧ｦ邱ｴ"]): data[k] = "Hate"
                elif any(x in val for x in ["prep", "ready", "貅門ｙ"]): data[k] = "Prep"
                elif any(x in val for x in ["payoff", "climax", "縺悶∪縺・, "辷・匱"]): data[k] = "Payoff"

            if isinstance(v, (dict, list)):
                data[k] = OutputSanitizer.normalize_metadata(v, key_name=k, is_root=False)

        return data

    @staticmethod
    def fix_json(text: str) -> str:
        """螢翫ｌ縺櫟SON譁・ｭ怜・繧貞庄閭ｽ縺ｪ髯舌ｊ菫ｮ蠕ｩ縺吶ｋ"""
        if not text: return "{}"
        
        # JSON繧貞峇繧繝・く繧ｹ繝医・髯､蜴ｻ繧貞ｼｷ蛹・        text = text.strip()
        # 譛蛻昴↓隕九▽縺九▲縺・'{' 縺九ｉ 譛蠕後↓隕九▽縺九▲縺・'}' 縺ｾ縺ｧ繧呈歓蜃ｺ
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            text = match.group(1)
        
        # JSON蜀・・繧ｳ繝｡繝ｳ繝茨ｼ・/ 縺ｾ縺溘・ /* */・峨ｒ遒ｺ螳溘↓髯､蜴ｻ
        text = re.sub(r'//.*?\n', '\n', text)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

        start = text.find('{')
        if start == -1:
            return "{}"

        # Brace counting to find the exact end of the JSON object
        count = 0
        end = -1
        for i in range(start, len(text)):
            if text[i] == '{':
                count += 1
            elif text[i] == '}':
                count -= 1
                if count == 0:
                    end = i
                    break

        if end != -1:
            text = text[start:end + 1]
        else:
            # Fallback if braces are not balanced
            end_fallback = text.rfind('}')
            if end_fallback != -1:
                text = text[start:end_fallback + 1]
            else:
                return "{}"

        # Python蠖｢蠑上け繧ｩ繝ｼ繝医・菫ｮ豁｣
        text = re.sub(r"([{,]\s*)\'([a-zA-Z0-9_.]+)\'\s*:", r'\1"\2":', text)
        text = re.sub(r"([{,]\s*)([a-zA-Z0-9_]+)\s*:",      r'\1"\2":', text)
        text = re.sub(r':\s*\'(.*?)\'(?=\s*[,}\]])', r': "\1"', text, flags=re.DOTALL)
        # 譛ｫ蟆ｾ繧ｫ繝ｳ繝橸ｼ医Μ繧ｹ繝医ｄ霎樊嶌縺ｮ譛蠕鯉ｼ峨ｒ蜑企勁
        text = re.sub(r',\s*([}\]])', r'\1', text)

        # 諡ｬ蠑ｧ縺ｮ閾ｪ蜍戊｣懷ｮ・        stack = []
        for ch in text:
            if ch == '{':   stack.append('}')
            elif ch == '[': stack.append(']')
            elif ch in ('}', ']') and stack and stack[-1] == ch:
                stack.pop()
        text += "".join(reversed(stack))

        try:
            json.loads(text)
        except json.JSONDecodeError:
            if text and text[-1] not in ('}', ']'):
                text += '}'

        return text

    @staticmethod
    def format_validation_error(ve) -> str:
        """Pydantic縺ｮValidationError繧但I縺檎炊隗｣縺励ｄ縺吶＞譌･譛ｬ隱槭↓螟画鋤縺吶ｋ"""
        type_map = {
            "missing":     "縺御ｸ崎ｶｳ縺励※縺・∪縺吶ょｿ・★蜷ｫ繧√※縺上□縺輔＞縲・,
            "string_type": "縺ｯ譁・ｭ怜・縺ｧ縺ゅｋ蠢・ｦ√′縺ゅｊ縺ｾ縺吶・,
            "int_type":    "縺ｯ謨ｴ謨ｰ縺ｧ縺ゅｋ蠢・ｦ√′縺ゅｊ縺ｾ縺吶・,
            "enum":        "縺ｯ謖・ｮ壹＆繧後◆驕ｸ謚櫁い縺九ｉ驕ｸ縺ｶ蠢・ｦ√′縺ゅｊ縺ｾ縺吶・,
        }
        msgs = []
        for err in ve.errors():
            loc  = ".".join(str(x) for x in err["loc"])
            msg  = type_map.get(err["type"], f"縺ｫ繧ｨ繝ｩ繝ｼ縺後≠繧翫∪縺呻ｼ亥次蝗: {err['msg']}・・)
            msgs.append(f"繝ｻ鬆・岼 '{loc}' {msg}")
        return "\n".join(msgs)


# ==========================================
# ContentValidator・医ユ繧ｭ繧ｹ繝亥刀雉ｪ讀懆ｨｼ・・# ==========================================
class ContentValidator:
    """逕滓・縺輔ｌ縺溘ユ繧ｭ繧ｹ繝医・隕也せ繝ｻ繝ｪ繧ｺ繝繝ｻ蝠・･ｭ逧・ｼｷ蠎ｦ繧呈､懆ｨｼ縺吶ｋ"""

    @staticmethod
    def check_rhythm(text: str) -> List[str]:
        errors = []
        sentences = [s.strip() for s in re.split(r'[縲ゑｼ滂ｼ‐', text) if s.strip()]
        if len(sentences) < 5:
            return errors

        lengths = [len(s) for s in sentences]
        avg     = sum(lengths) / len(lengths)
        std_dev = (sum((x - avg) ** 2 for x in lengths) / len(lengths)) ** 0.5

        if std_dev < 8.0:
            errors.append(f"繝ｪ繧ｺ繝隴ｦ蜻・ 譁・ｫ縺ｮ髟ｷ縺輔′蝮・ｸ縺吶℃縺ｾ縺呻ｼ亥￥蟾ｮ:{std_dev:.1f}・峨る聞遏ｭ繧呈ｷｷ縺懊※縺上□縺輔＞縲・)

        endings = [s[-2:] if len(s) >= 2 else s[-1:] for s in sentences]
        count   = 1
        for i in range(1, len(endings)):
            if endings[i] == endings[i - 1]:
                count += 1
                if count >= 3:
                    errors.append(f"繝ｪ繧ｺ繝隴ｦ蜻・ 隱槫ｰｾ縲鶏endings[i]}縲阪′3蝗樔ｻ･荳企｣邯壹＠縺ｦ縺・∪縺吶・)
                    break
            else:
                count = 1
        return errors

    @staticmethod
    def check_catharsis_reservation(text: str, ep_num: int) -> List[str]:
        """隨ｬ1隧ｱ縺ｫ縺翫＞縺ｦ縲∝ｰ・擂逧・↑騾・ｻ｢・郁ｧ｣豎ｺ縺ｮ莠域─・峨′謠千､ｺ縺輔ｌ縺ｦ縺・ｋ縺区､懆ｨｼ縺吶ｋ"""
        errors = []
        if ep_num == 1:
            keywords = ["縺・▽縺・, "蠢・★", "莠域─", "蜈・＠", "蠕ｩ隶・, "騾・ｻ｢", "譛ｬ蠖薙・蜉・, "迚・ｱ・]
            if not any(k in text for k in keywords):
                errors.append("蝠・畑隴ｦ蜻・ 隨ｬ1隧ｱ縺ｫ縲弱き繧ｿ繝ｫ繧ｷ繧ｹ縺ｮ莠育ｴ・ｼ郁ｧ｣豎ｺ縺ｮ莠域─・峨上′荳崎ｶｳ縺励※縺・∪縺吶りｪｭ閠・′谺｡繧定ｪｭ縺ｿ縺溘￥縺ｪ繧九主渚謦・・蜈・＠縲上ｒ蠑ｷ隱ｿ縺励※縺上□縺輔＞縲・)
        return errors

    @staticmethod
    def auto_correct_rhythm(text: str, target_std: float = 12.0) -> str:
        """豁｣隕剰｡ｨ迴ｾ繝吶・繧ｹ縺ｮ繝ｪ繧ｺ繝閾ｪ蜍戊｣懈ｭ｣・・udachiPy荳榊惠譎ゅ・繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ・・""
        return ContentValidator._regex_auto_correct_rhythm(text, target_std)

    @staticmethod
    def _regex_auto_correct_rhythm(text: str, target_std: float = 12.0) -> str:
        """豁｣隕剰｡ｨ迴ｾ繝吶・繧ｹ縺ｮ繝ｪ繧ｺ繝陬懈ｭ｣螳溯｣・ｼ・udachiPy荳榊惠譎ゅ・繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ・・""
        parts     = re.split(r'([縲ゑｼ滂ｼ―n])', text)
        sentences: List[Dict] = []
        temp      = ""
        for p in parts:
            if p in "縲ゑｼ滂ｼ―n":
                if temp.strip():
                    sentences.append({"text": temp.strip(), "punct": p})
                elif p == "\n":
                    sentences.append({"text": "", "punct": "\n"})
                temp = ""
            else:
                temp += p

        if len(sentences) < 5:
            return text

        def get_std(s_list):
            lengths = [len(s["text"]) for s in s_list if s["text"]]
            if not lengths:
                return 0
            avg = sum(lengths) / len(lengths)
            return (sum((x - avg) ** 2 for x in lengths) / len(lengths)) ** 0.5

        for _ in range(3):
            if get_std(sentences) >= target_std:
                break
            new_sentences: List[Dict] = []
            i = 0
            while i < len(sentences):
                s = sentences[i]
                if len(s["text"]) > 40 and "縲・ in s["text"]:
                    m = s["text"].split("縲・, 1)
                    new_sentences.append({"text": m[0], "punct": "縲・})
                    new_sentences.append({"text": m[1], "punct": s["punct"]})
                    i += 1
                elif i + 1 < len(sentences) and len(s["text"]) < 20 and sentences[i + 1]["text"]:
                    ns = sentences[i + 1]
                    new_sentences.append({"text": s["text"] + "縲・ + ns["text"], "punct": ns["punct"]})
                    i += 2
                else:
                    new_sentences.append(s)
                    i += 1
            sentences = new_sentences

        return "".join(s["text"] + s["punct"] for s in sentences)

    @staticmethod
    def analyze_word_heaviness(text: str) -> Dict[str, Any]:
        """
        譁・ｫ縺ｮ縲碁㍾縺輔阪ｒ貍｢蟄礼紫縺ｨ髮｣隱ｭ隱槭°繧牙愛螳夲ｼ・PI繧ｳ繧ｹ繝・・・        """
        if not text:
            return {"kanji_rate": 0, "is_heavy": False}
        
        kanji_count = len(re.findall(r'[\u4E00-\u9FFF]', text))
        total_count = len(text)
        rate = (kanji_count / total_count) * 100 if total_count > 0 else 0
        
        # 繧ｫ繧ｯ繝ｨ繝繝ｻ縺ｪ繧阪≧縺ｮ鮟・≡豈斐・ 20%縲・0%縲・5%繧定ｶ・∴繧九→縲碁㍾縺・阪→蛻､螳壹・        return {
            "kanji_rate": round(rate, 1),
            "is_heavy": rate > 35,
            "advice": "貍｢蟄励′螟壹☆縺弱∪縺吶ゅ・繧峨′縺ｪ繧貞｢励ｄ縺励※縲守區縺上上☆繧九→隱ｭ縺ｿ繧・☆縺上↑繧翫∪縺吶・ if rate > 35 else "驕ｩ蛻・↑蟇・ｺｦ縺ｧ縺吶・
        }


# ==========================================
# SeriousnessFilter・医ヨ繝ｼ繝ｳ隱ｿ謨ｴ繝輔ぅ繝ｫ繧ｿ・・# ==========================================
class SeriousnessFilter:
    """譁・ц縺ｮ繧ｷ繝ｪ繧｢繧ｹ蠎ｦ繧貞愛螳壹＠縲∬ｨ伜捷繧・ｪ槫ｽ吶・譛邨ら噪縺ｪ蠕ｮ隱ｿ謨ｴ繧定｡後≧"""
    def filter(self, text: str, is_light: bool = True) -> str:
        if is_light:
            return text
        
        # 繧ｷ繝ｪ繧｢繧ｹ縺ｪ譁・ｽ薙・蝣ｴ蜷医∵─蝌・ｬｦ縺ｨ逍大撫隨ｦ縺ｮ邨・∩蜷医ｏ縺帙ｒ關ｽ縺｡逹縺・◆陦ｨ迴ｾ縺ｫ鄂ｮ謠・        text = text.replace("・・ｼ・, "縲・).replace("・・ｼ・, "縲・)
        # 荳臥せ繝ｪ繝ｼ繝繝ｼ縺ｮ驕主臆縺ｪ騾｣邯壹ｒ謚大宛
        text = re.sub(r'窶ｦ{4,}', '窶ｦ窶ｦ', text)
        return text


# ==========================================
# TextFormatter・医き繧ｯ繝ｨ繝蠖｢蠑乗紛蠖｢・・# ==========================================
class TextFormatter:
    @staticmethod
    def remove_ai_isms(text: str) -> str:
        """AI迚ｹ譛峨・螳壼梛蜿･・・I-isms・峨ｒ閾ｪ辟ｶ縺ｪ陦ｨ迴ｾ縺ｫ鄂ｮ謠帙∪縺溘・蜑企勁縺吶ｋ"""
        ai_isms = [
            (r'險縺・∪縺ｧ繧ゅ↑縺Ъ縺後°]?縲・', ''),
            (r'迚ｹ遲・☆縺ｹ縺阪・縲・, ''),
            (r'縺昴・譎ゅ□縺｣縺溘・', ''),
            (r'隱ｰ縺ｮ逶ｮ縺ｫ繧よ・繧峨°縺縺｣縺溘・', ''),
            (r'諱ｯ繧貞荘[繧繧転縺縲・', '險闡峨ｒ螟ｱ縺｣縺溘・),
            (r'逶ｮ繧剃ｸｸ縺上＠縺溘・', '迸ｬ縺阪ｒ蠢倥ｌ縺溘・),
            (r'鬩壹″繧帝國縺帙↑縺九▲縺溘・', '邨ｶ蜿･縺励◆縲・),
            (r'髱吝ｯゅ′謾ｯ驟阪＠縺溘・', '豌ｴ繧呈遠縺｣縺溘ｈ縺・↑髱吶￠縺輔′關ｽ縺｡縺溘・),
            (r'險縺・∪縺ｧ繧ゅ↑縺・・, ''),
        ]
        for pattern, replacement in ai_isms:
            text = re.sub(pattern, replacement, text)
        return text

    @staticmethod
    def enforce_cliffhanger(text: str) -> str:
        """繧ｨ繝斐た繝ｼ繝画忰蟆ｾ縺ｮ縲悟ｼ輔″・医け繝ｪ繝輔ワ繝ｳ繧ｬ繝ｼ・峨阪ｒ隕冶ｦ夂噪縺ｫ蠑ｷ隱ｿ縺吶ｋ"""
        text = text.strip()
        if not text:
            return text
        
        # 繝・ヰ繝・げ・壻ｺ碁㍾莉倅ｸ弱ｒ髦ｲ縺弱▽縺､縲∬ｪｭ閠・′縲梧ｬ｡繧定ｪｭ縺ｿ縺溘￥縺ｪ繧九堺ｽ咎渊繧貞ｼｷ蛻ｶ
        text = text.rstrip('縲・)
        if not text.endswith('窶補・) and not text.endswith('窶ｦ窶ｦ'):
            text += '窶補・

        # 譛蠕後・譁・ｒ隕冶ｦ夂噪縺ｫ蛻・屬縺励※菴咎渊繧呈戟縺溘○繧・        # 譛蠕後・謾ｹ陦御ｻ･髯阪ｒ蜿門ｾ・        parts = text.rsplit('\n\n', 1)
        if len(parts) == 2:
            main_text, last_para = parts
            return f"{main_text}\n\n縲窶補府last_para.strip()}"
        return text

    @staticmethod
    def format_for_kakuyomu(text: str) -> str:
        """繧ｫ繧ｯ繝ｨ繝蠖｢蠑上∈縺ｮ螳悟・謨ｴ蠖｢・壽ｮｵ關ｽ縺ｮ縲檎區縺輔榊宛蠕｡繧貞ｼｷ蛹・""
        if not text:
            return ""

        # AI-isms縺ｮ髯､蜴ｻ・域隼蝟・｡・・・        text = TextFormatter.remove_ai_isms(text)

        # 繧ｷ繝ｪ繧｢繧ｹ蠎ｦ讀懃衍縺ｨ繧ｮ繝｣繧ｰ陬懈ｭ｣縺ｮ驕ｩ逕ｨ
        s_filter = SeriousnessFilter()
        text = s_filter.filter(text)

        # AI蜑咲ｽｮ縺阪・繧ｳ繝ｼ繝峨ヶ繝ｭ繝・け髯､蜴ｻ (FixedTextFormatter縺ｮ謾ｹ蝟・ｒ邨ｱ蜷・
        text = re.sub(
            r'^(縺ｯ縺л謇ｿ遏･|莠・ｧ｣|莉･荳弓縺薙ｌ|Here|Sure|JSON蠖｢蠑上〒蜃ｺ蜉帙＠縺ｾ縺處莠・ｧ｣縺励∪縺励◆).*?(\n|$)',
            '', text, flags=re.IGNORECASE | re.MULTILINE
        ).strip()
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)

        # 讒矩繧ｿ繧ｰ繝ｻ繝｡繧ｿ繧ｿ繧ｰ縺ｮ譛邨る勁蜴ｻ・亥・欧縺ｪ繝代う繝励Λ繧､繝ｳ縺ｮ譛邨ゅご繝ｼ繝茨ｼ・        struct_tags = r'(SCENE|Scene|繧ｷ繝ｼ繝ｳ|CHAPTER|Chapter|隨ｬ\d+隧ｱ|EPISODE|Episode|繧ｨ繝斐た繝ｼ繝・'
        text = re.sub(r'^[#\s\*]*\[?' + struct_tags + r'\s*[\d荳莠御ｸ牙屁莠泌・荳・・荵晏香]+\]?[:・喀s\*]*.*$', '', text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'\[.*?\]', '', text) 

        # 蜿ｰ譛ｬ蠖｢蠑上・髯､蜴ｻ繝ｭ繧ｸ繝・け繧偵ｈ繧企ｫ倬溘↑蜊倅ｸ繝代せ縺ｮ鄂ｮ謠帙∈邨ｱ蜷・        def _process_dialogue_line(match):
            notes = re.findall(r'[・・](.*?)[・・]', match.group(1))
            if notes: return "縲・.join(notes) + "縲・n" + match.group(2)
            return match.group(1).strip() + "\n" + match.group(2)

        # 縲後そ繝ｪ繝輔阪∪縺溘・縲弱そ繝ｪ繝輔上・蜑阪↓菴輔°縺後≠繧玖｡後ｒ蟇ｾ雎｡
        # DOTALL繝輔Λ繧ｰ縺ｯ荳崎ｦ√｀ULTILINE縺ｧ蜷・｡後・蜈磯ｭ繧耽縺ｧ繝槭ャ繝・        text = re.sub(r'^([^縲後蚕n]+)([縲後讃.*?[縲阪従)', _process_dialogue_line, text, flags=re.MULTILINE)

        # 險伜捷縺ｮ邨ｱ荳
        text = re.sub(r'\.{3,}', '窶ｦ窶ｦ', text)
        text = re.sub(r'[窶ｦ繝ｻ]{1,}', '窶ｦ窶ｦ', text)
        text = text.replace("縲ゅ・, "縲・)
        text = re.sub(r'([・滂ｼ‐)(?![\s縲縲阪従)', r'\1縲', text)

        # --- 縲檎區縺輔阪・蜍慕噪蛻ｶ蠕｡ (Category A: Implementation) ---
        analysis = ContentValidator.analyze_word_heaviness(text)
        kanji_rate = analysis["kanji_rate"]

        # 隕・ｨｩWeb蟆剰ｪｬ縺ｮ鮟・≡豈費ｼ壽ｼ｢蟄礼紫20-30%縲・        # 30%繧定ｶ・∴繧九→繧ｹ繝槭・縺ｧ縺ｯ縲碁ｻ偵＞蝪翫阪↓隕九∴繧九◆繧√∝ｼｷ蛻ｶ逧・↓謾ｹ陦悟ｼｷ蠎ｦ繧剃ｸ翫￡繧九・        is_dense = kanji_rate > 30
        max_lines_per_para = 1 if is_dense else 2
        max_chars_per_line = 35 if kanji_rate > 35 else 45
        force_break_at_period = kanji_rate > 33

        lines         = [l.strip() for l in text.split('\n')]
        new_lines     = []
        narrative_cnt = 0

        for line in lines:
            if not line:
                if new_lines and new_lines[-1] != "":
                    new_lines.append("")
                narrative_cnt = 0
                continue
            # 蜈ｨ隗偵う繝ｳ繝・Φ繝医・閾ｪ蜍穂ｻ倅ｸ趣ｼ育音螳壹・險伜捷莉･螟厄ｼ・            if line[0] not in ['縲・, '縲・, '・・, '<', '縲・, '・ｻ', '縲・, '縲・, '縲・]:
                line = '縲' + line
            
            is_dialogue = line.strip().startswith(('縲・, '縲・, '・・))
            
            if is_dialogue:
                # 莨夊ｩｱ譁・・蜑阪↓縺ｯ遨ｺ陦後ｒ遒ｺ菫・                if new_lines and new_lines[-1] != "":
                    new_lines.append("")
                new_lines.append(line)
                # 莨夊ｩｱ譁・・蠕後・蠢・★謾ｹ谿ｵ・育ｩｺ陦鯉ｼ・                new_lines.append("")
                narrative_cnt = 0
            else:
                # 蝨ｰ縺ｮ譁・・蜃ｦ逅・                new_lines.append(line)
                narrative_cnt += 1
                
                # 貍｢蟄怜ｯ・ｺｦ縺碁ｫ倥＞蝣ｴ蜷医√∪縺溘・蜿･轤ｹ縺ｫ驕斐＠縺溷ｴ蜷医・蜍慕噪謾ｹ陦・                should_break = False
                if force_break_at_period and "縲・ in line:
                    should_break = True
                elif narrative_cnt >= max_lines_per_para or len(line) > max_chars_per_line:
                    should_break = True

                if should_break:
                    new_lines.append("")
                    narrative_cnt = 0

        result = "\n".join(new_lines).strip()
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        # 謾ｹ蝟・｡・: 縲悟ｼ輔″・医け繝ｪ繝輔ワ繝ｳ繧ｬ繝ｼ・峨阪・隕冶ｦ夂噪蠑ｷ隱ｿ
        return TextFormatter.enforce_cliffhanger(result)


# ==========================================
# AtmosphereGenerator・育腸蠅・ｼ泌・陬懷勧・・# ==========================================
class AtmosphereGenerator:
    @staticmethod
    def get_prompt(season: str = "譏･", weather: str = "譎ｴ螟ｩ") -> str:
        return f"縲千腸蠅・ｼ泌・謖・ｻ､縲醍樟蝨ｨ縺ｮ闊槫床閭梧勹: {season}/{weather}縲よ緒蜀吶↓蟄｣遽諢溘→遨ｺ豌玲─繧貞性繧√ｈ縲・

    @staticmethod
    def get_sensory_anchors(season: str, weather: str, location: str) -> List[str]:
        anchors = []
        if season == "螟・:
            anchors.append("閧後ｒ辟ｼ縺上ｈ縺・↑辭ｱ豌・)
        if season == "蜀ｬ":
            anchors.append("閧ｺ縺ｮ螂･縺ｾ縺ｧ蜃阪※縺､縺丞・豌・)
        if weather == "髮ｨ":
            anchors.append("蝨ｰ髱｢繧貞娼縺乗ｿ縺励＞髮ｨ髻ｳ")
        if weather == "譎ｴ螟ｩ":
            anchors.append("逶ｮ繧堤ｴｰ繧√ｋ繧医≧縺ｪ蠑ｷ縺・區蜈・)
        return anchors

