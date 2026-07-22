"""
sanitizer.py - AI出力修復・検証モジュール
AIが返す壊れたJSONの修復、メタデータ正規化、
テキスト品質検証（視点・リズム・口調）を担う。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from src.models import CharacterRegistry

logger = logging.getLogger(__name__)

CONTENT_SEPARATOR = "### NOVEL CONTENT ###"


class NormalizationFlow:
    """normalize_metadata()の責務を4つのレベルに分割したクラス

    1. 入力データ型調整
    2. エイリアス解決
    3. 値変換
        4. デフォルト付与
    """

    def __init__(self) -> None:
        self._wrapper_keys = {
            "metadata", "response", "data", "plot", "episode_data",
            "plot_episode", "episode", "results", "output", "content",
            "roadmap", "arc_roadmap", "chapter"
        }
        self._force_str_keys = [
            "detailed_blueprint", "script_content", "final_content", "title",
            "one_line_summary", "magic_cost_and_taboo", "social_hierarchy_and_discrimination",
            "geopolitics_and_economy", "religious_dogma_and_heresy", "rewrite_suggestion",
            "personality", "ability", "background", "tone", "iron_constraint",
            "summary", "keywords", "thought_process"
        ]
        self._numeric_fields = ["stress_delta", "love_delta", "tension"]
        self._ep_num_aliases = ["episode_num", "episode_number", "episode", "ep_no", "ep", "no", "number", "chapter"]
        self._scene_num_aliases = ["scene_id", "id", "scene_no", "index", "sceneNumber"]
        self._severity_map = {
            "critical": "Critical", "致命的": "Critical", "high": "Critical", "極めて重い": "Critical",
            "major": "Major", "重大": "Major", "medium": "Major", "重い": "Major",
            "minor": "Minor", "軽微": "Minor", "low": "Minor", "軽い": "Minor"
        }
        self._beat_valid_types = ["導入", "展開", "結末", "状況", "内面葛藤", "具体的行動", "余韻"]

    def unwrap_nested_metadata(self, data: Any) -> Any:
        """ネストされたデータ構造をフラット化（10回ループ）"""
        for _ in range(10):
            if not isinstance(data, dict):
                break
            unwrapped = False
            if len(data) == 1:
                k = list(data.keys())[0]
                if k.lower() in self._wrapper_keys and isinstance(data[k], dict):
                    data = data[k]
                    unwrapped = True
            else:
                for wk in self._wrapper_keys:
                    if wk in data and isinstance(data[wk], dict):
                        inner = data.pop(wk)
                        for ik, iv in inner.items():
                            if ik not in data:
                                data[ik] = iv
                        unwrapped = True
                        break
            if not unwrapped:
                break
        return data

    def resolve_aliases(self, data: dict) -> dict:
        """エイリアス解決（ep_num, scene_number, severity, detailed_blueprint, final_content）"""
        if not isinstance(data, dict):
            return data

        if "ep_num" not in data:
            for alias in self._ep_num_aliases:
                if alias in data:
                    try:
                        val = data[alias]
                        data["ep_num"] = int(val) if isinstance(val, (int, float)) else int(re.search(r'\d+', str(val)).group())
                        break
                    except Exception:
                        pass

        if "scene_number" not in data:
            for alias in self._scene_num_aliases:
                if alias in data:
                    try:
                        val = data[alias]
                        data["scene_number"] = int(val) if isinstance(val, (int, float)) else int(re.search(r'-?\d+', str(val)).group())
                        break
                    except Exception:
                        pass

        if "severity" in data:
            sev = str(data["severity"]).lower()
            data["severity"] = "Minor"
            for key, value in self._severity_map.items():
                if key in sev:
                    data["severity"] = value
                    break

        if "detailed_blueprint" not in data:
            for alias in ["outline", "summary", "synopsis", "description", "body", "story"]:
                if alias in data and isinstance(data[alias], str) and len(data[alias]) > 50:
                    data["detailed_blueprint"] = data[alias]
                    break

        if "final_content" not in data:
            for alias in ["script_content", "story", "manuscript", "text", "body", "content"]:
                if alias in data and isinstance(data[alias], str) and len(data[alias]) > 100:
                    data["final_content"] = data[alias]
                    break

        return data

    def coerce_types(self, data: dict) -> dict:
        """型強制変換（文字列強制変換 + next_hook修復 + 数値キャスト）"""
        if not isinstance(data, dict):
            return data

        for str_key in self._force_str_keys:
            if str_key in data:
                val = data[str_key]
                if val is None:
                    data[str_key] = ""
                elif isinstance(val, list):
                    sep = "\n\n" if any(x in str_key for x in ["content", "blueprint", "script"]) else ", "
                    data[str_key] = sep.join([str(x) for x in val])
                elif not isinstance(val, str):
                    data[str_key] = json.dumps(val, ensure_ascii=False)

        if "next_hook" in data:
            if isinstance(data["next_hook"], str):
                try:
                    data["next_hook"] = json.loads(data["next_hook"])
                except Exception:
                    data["next_hook"] = {"type": "New Crisis", "description": data["next_hook"]}
            elif data["next_hook"] is None:
                data["next_hook"] = {"type": "Quiet Foreshadowing", "description": "続く"}

        for num_key in self._numeric_fields:
            if num_key in data and not isinstance(data[num_key], int):
                try:
                    data[num_key] = int(re.search(r'-?\d+', str(data[num_key])).group())
                except Exception:
                    data[num_key] = 0

        return data

    def normalize_lists(self, data: list, key_name: Optional[str]) -> list:
        """リスト構造正規化（scenes/beats/story_threads等）"""
        if key_name == "scenes":
            data = [{"action": x} if isinstance(x, str) else x for x in data]
            for i, item in enumerate(data):
                if isinstance(item, dict) and "scene_number" not in item:
                    item["scene_number"] = item.get("id") or item.get("no") or (i + 1)
        elif key_name == "climax_scenes":
            data = [{"event": x} if isinstance(x, str) else x for x in data]
        elif key_name == "foreshadowing_map":
            data = [{"description": x} if isinstance(x, str) else x for x in data]
        elif key_name == "beats":
            data = [{"action_description": x} if isinstance(x, str) else x for x in data]
            for item in data:
                if isinstance(item, dict):
                    if "beat_type" in item:
                        bt = str(item["beat_type"])
                        for vt in self._beat_valid_types:
                            if vt in bt:
                                item["beat_type"] = vt
                                break
                    for kw_field in ["sensory_keywords", "psychology_keywords"]:
                        if kw_field in item and isinstance(item[kw_field], str):
                            item[kw_field] = [x.strip() for x in re.split(r'[,、]', item[kw_field]) if x.strip()]
        elif key_name == "recovered_items":
            data = [{"foreshadowing_id": x} if isinstance(x, str) else x for x in data]
        elif key_name == "missing_items":
            data = [x.get("description", str(x)) if isinstance(x, dict) else str(x) for x in data]
        elif key_name == "story_threads":
            data = [x if isinstance(x, dict) else {"description": str(x), "status": "Active", "setup_episode": 0} for x in data]

        if key_name in ["full_story_roadmap", "roadmap", "arc_roadmap", "plots"]:
            for i, item in enumerate(data):
                if isinstance(item, dict) and "ep_num" not in item:
                    item["ep_num"] = i + 1

        return data

    def apply_defaults(self, data: dict, is_root: bool) -> dict:
        """デフォルト値付与（burned_cost_or_loot, antagonist_status）"""
        if not isinstance(data, dict):
            return data

        is_story_obj = is_root or "one_line_summary" in data or "detailed_blueprint" in data
        if is_story_obj:
            if "burned_cost_or_loot" not in data:
                data["burned_cost_or_loot"] = "特になし"
            if "antagonist_status" not in data:
                data["antagonist_status"] = "現状維持"

        return data

    def normalize_metadata(self, data: Any, key_name: Optional[str] = None, is_root: bool = True) -> Any:
        """AIが生成するメタデータ構造の揺れ（ネスト・キー名）を吸収して正規化する"""
        if data is None or data == "":
            return {} if is_root else data

        if is_root and not isinstance(data, dict):
            return {"raw_data": data}

        if isinstance(data, list):
            normalized = [self.normalize_metadata(item, key_name, is_root=False) for item in data]
            normalized = self.normalize_lists(normalized, key_name)
            return normalized

        if not isinstance(data, dict):
            return {} if is_root else data

        data = self.unwrap_nested_metadata(data)
        data = self.resolve_aliases(data)
        data = self.coerce_types(data)
        data = self.apply_defaults(data, is_root)

        for k, v in data.items():
            if k == "current_chain_phase":
                val = str(v).lower()
                if any(x in val for x in ["hate", "stress", "絶望", "試練"]):
                    data[k] = "Hate"
                elif any(x in val for x in ["prep", "ready", "準備"]):
                    data[k] = "Prep"
                elif any(x in val for x in ["payoff", "climax", "ざまぁ", "爆発"]):
                    data[k] = "Payoff"

            if isinstance(v, (dict, list)):
                data[k] = self.normalize_metadata(v, key_name=k, is_root=False)

        return data


# ==========================================
# TonePerfector（口調強制補正）
# ==========================================
class TonePerfector:
    """キャラクターの口調・一人称・二人称をDB設定に基づき強制置換する"""

    @staticmethod
    def enforce_tone(text: str, characters: List[CharacterRegistry]) -> str:
        for char in characters:
            if not char.name:
                continue

            # 台詞内の人称置換ロジック
            def replace_pronouns(match):
                dialogue = match.group(0)
                # 一人称の強制置換（AIが間違えやすいため）
                if char.first_person:
                    dialogue = re.sub(r'(私|僕|俺|あたし|自分)(?=[、。！？こと。をにが」])', char.first_person, dialogue)
                # 二人称の強制置換
                if char.second_person:
                    dialogue = re.sub(r'(君|あなた|お前|貴様)(?=[、。！？をにが」])', char.second_person, dialogue)

                # 語尾の簡易補正（例：なのだ、だわ、ですわ等）
                if char.suffix_style:
                    # 文末の「だ。」「。」「！」等を検知して語尾を付与する簡易的な仕組み
                    # 実際にはより高度な形態素解析が必要だが、ここではAIの補完として動作
                    if "〜" in char.suffix_style:
                        suffix = char.suffix_style.replace("〜", "")
                        dialogue = re.sub(r'([。？！])(?=」)', f"{suffix}\\1", dialogue)

                return dialogue

            # 会話文（「」内）を抽出して置換を適用
            text = re.sub(r'「.*?」', replace_pronouns, text, flags=re.DOTALL)

        return text

# OutputSanitizer（JSON修復・メタデータ正規化）
# ==========================================
class OutputSanitizer:
    """AI出力の修復・正規化を担う静的ユーティリティクラス"""
    _normalization_flow = NormalizationFlow()

    @staticmethod
    def parse_llm_json(text: str) -> Dict[str, Any]:
        """
        LLMの出力からJSON部分を抽出し、修復してパースする。
        """
        if not text:
            return {}
        # 最も外側の波括弧を抽出（LLMが前後にテキストを付けても対応）
        json_match = re.search(r'(\{.*\})', text.strip(), re.DOTALL)
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
        本文とメタデータJSONを安全に分離して返す。
        セパレーター形式 → JSON末尾抽出 → プレーンテキスト の順でフォールバック。
        """
        if not text:
            return {}, ""

        # 1. セパレーター形式（最優先）
        if CONTENT_SEPARATOR in text:
            parts = text.split(CONTENT_SEPARATOR)
            if len(parts) >= 3:
                story_content = parts[1].strip()
                metadata = OutputSanitizer.parse_llm_json(parts[2])
                if metadata:
                    return OutputSanitizer.normalize_metadata(metadata), OutputSanitizer._clean_story(story_content)

        # 2. JSON末尾抽出
        metadata = OutputSanitizer.parse_llm_json(text)
        if metadata:
            # 文字列の最後にあるJSONらしき部分を特定
            json_match = re.search(r'(\{.*\})(?:\s|`|#)*$', text.strip(), re.DOTALL)
            if json_match:
                story_content = (text[:json_match.start()] + text[json_match.end():]).strip()
                # [thought_process] 等のブロックを広範囲に除去
                story_content = re.sub(r'\[(thought_process|DIRECTOR_NOTE|METADATA_JSON|CONTENT_SEPARATOR|SCENE|BEAT)\].*?(\n\n|\Z)', '', story_content, flags=re.DOTALL | re.IGNORECASE).strip()
                if len(story_content) < 50:
                    story_content = metadata.get("final_content") or metadata.get("script_content") or ""
                return OutputSanitizer.normalize_metadata(metadata), OutputSanitizer._clean_story(story_content)

        # 3. プレーンテキストフォールバック
        return {}, OutputSanitizer._clean_story(text)

    @staticmethod
    def _clean_story(text: str, **kwargs) -> str:
        """AIのメタ発言・余計な一言を削除"""
        # 行頭の定型句のみを削除し、文中の言葉は残す
        meta_patterns = [
            r'^(?:JSON形式で出力します|了解しました|以下はプロットです|承知しました|以下に執筆します|こちらが本文です|ハイ、喜んで|かしこまりました|考えました|修正しました|提供された.*?に基づいて|かしこまりました。).*?$',
            r'^(第.*話|エピソード.*|サブタイトル.*)[:：].*$', # 重複するサブタイトル行を除去
            r'^(?:\[METADATA_JSON\].*?)$',
            r'^(?:\[thought_process\].*?)$'
        ]
        for pat in meta_patterns:
            text = re.sub(pat, '', text, flags=re.MULTILINE | re.IGNORECASE)

        text = re.sub(r'\[(DIRECTOR_NOTE|thought_process)\].*?(?=' + re.escape(CONTENT_SEPARATOR) + r'|\[|\Z)', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = text.replace("[NOVEL_CONTENT]", "").replace("[METADATA_JSON]", "")
        text = text.replace(CONTENT_SEPARATOR, "")
        text = re.sub(r'\[RESERVE_DESCRIPTION:.*?\]', '', text) # 残留した描写予約タグを削除

        # 内部構造タグ（[SCENE X]等）の除去。ただし「第1話」などのタイトル行は、後に本文として使う可能性があるため、
        # 明らかにメタデータ的な記述（[SCENE...]）のみをターゲットにする
        text = re.sub(r'^[#\s\*]*\[(SCENE|Scene|シーン|BEAT|Beat|ビート)\s*[\d一二三四五六七八九十]+\]?[:：\s\*]*.*$', '', text, flags=re.IGNORECASE | re.MULTILINE)

        # 執筆フェーズ等のブロックタグ除去
        text = re.sub(r'\[(DIRECTOR_NOTE|METADATA_JSON|NOVEL_CONTENT|SCRIPT|PLOT|BEAT|ANALYSIS|REFINE)\].*$', '', text, flags=re.IGNORECASE | re.MULTILINE)

        # 孤立したブラケットタグ [ ... ] の除去（AIの内部メモ対策）
        text = re.sub(r'\[[^\]]{1,100}\]', '', text)

        # Markdown装飾記号の除去（小説本文には不要なボールド、イタリック、打ち消し線）
        text = re.sub(r'(\*\*|__|\*|_|~~)', '', text)

        # 区切り線（水平線）の除去
        text = re.sub(r'^\s*[-*#=_]{3,}\s*$', '', text, flags=re.MULTILINE)

        return re.sub(r'\n{4,}', '\n\n', text).strip()

    @staticmethod
    def normalize_metadata(data: Any, key_name: Optional[str] = None, is_root: bool = True) -> Any:
        """AIが生成するメタデータ構造の揺れ（ネスト・キー名）を吸収して正規化する"""
        return OutputSanitizer._normalization_flow.normalize_metadata(data, key_name, is_root)

    @staticmethod
    def fix_json(text: str) -> str:
        """壊れたJSON文字列を可能な限り修復する"""
        if not text:
            return "{}"

        # JSONを囲むテキストの除去を強化
        text = text.strip()
        # 最初に見つかった '{' から 最後に見つかった '}' までを抽出
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            text = match.group(1)

        # JSON内のコメント（// または /* */）を確実に除去
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

        # Python形式クォートの修正
        text = re.sub(r"([{,]\s*)\'([a-zA-Z0-9_.]+)\'\s*:", r'\1"\2":', text)
        text = re.sub(r"([{,]\s*)([a-zA-Z0-9_]+)\s*:",      r'\1"\2":', text)
        text = re.sub(r':\s*\'(.*?)\'(?=\s*[,}\]])', r': "\1"', text, flags=re.DOTALL)
        # 末尾カンマ（リストや辞書の最後）を削除
        text = re.sub(r',\s*([}\]])', r'\1', text)

        # 括弧の自動補完
        stack = []
        for ch in text:
            if ch == '{':
                stack.append('}')
            elif ch == '[':
                stack.append(']')
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
        """PydanticのValidationErrorをAIが理解しやすい日本語に変換する"""
        type_map = {
            "missing":     "が不足しています。必ず含めてください。",
            "string_type": "は文字列である必要があります。",
            "int_type":    "は整数である必要があります。",
            "enum":        "は指定された選択肢から選ぶ必要があります。",
        }
        msgs = []
        for err in ve.errors():
            loc  = ".".join(str(x) for x in err["loc"])
            msg  = type_map.get(err["type"], f"にエラーがあります（原因: {err['msg']}）")
            msgs.append(f"・項目 '{loc}' {msg}")
        return "\n".join(msgs)


# ==========================================
# ContentValidator（テキスト品質検証）
# ==========================================
class ContentValidator:
    """生成されたテキストの視点・リズム・商業的強度を検証する"""

    @staticmethod
    def check_rhythm(text: str) -> List[str]:
        errors = []
        sentences = [s.strip() for s in re.split(r'[。？！]', text) if s.strip()]
        if len(sentences) < 5:
            return errors

        lengths = [len(s) for s in sentences]
        avg     = sum(lengths) / len(lengths)
        std_dev = (sum((x - avg) ** 2 for x in lengths) / len(lengths)) ** 0.5

        if std_dev < 8.0:
            errors.append(f"リズム警告: 文章の長さが均一すぎます（偏差:{std_dev:.1f}）。長短を混ぜてください。")

        endings = [s[-2:] if len(s) >= 2 else s[-1:] for s in sentences]
        count   = 1
        for i in range(1, len(endings)):
            if endings[i] == endings[i - 1]:
                count += 1
                if count >= 3:
                    errors.append(f"リズム警告: 語尾「{endings[i]}」が3回以上連続しています。")
                    break
            else:
                count = 1
        return errors

    @staticmethod
    def check_catharsis_reservation(text: str, ep_num: int) -> List[str]:
        """第1話において、将来的な逆転（解決の予感）が提示されているか検証する"""
        errors = []
        if ep_num == 1:
            keywords = ["いつか", "必ず", "予感", "兆し", "復讐", "逆転", "本当の力", "片鱗"]
            if not any(k in text for k in keywords):
                errors.append("商用警告: 第1話に『カタルシスの予約（解決の予感）』が不足しています。読者が次を読みたくなる『反撃の兆し』を強調してください。")
        return errors

    @staticmethod
    def auto_correct_rhythm(text: str, target_std: float = 12.0) -> str:
        """正規表現ベースのリズム自動補正（SudachiPy不在時のフォールバック）"""
        return ContentValidator._regex_auto_correct_rhythm(text, target_std)

    @staticmethod
    def _regex_auto_correct_rhythm(text: str, target_std: float = 12.0) -> str:
        """正規表現ベースのリズム補正実装（SudachiPy不在時のフォールバック）"""
        parts     = re.split(r'([。？！\n])', text)
        sentences: List[Dict] = []
        temp      = ""
        for p in parts:
            if p in "。？！\n":
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
                if len(s["text"]) > 40 and "、" in s["text"]:
                    m = s["text"].split("、", 1)
                    new_sentences.append({"text": m[0], "punct": "。"})
                    new_sentences.append({"text": m[1], "punct": s["punct"]})
                    i += 1
                elif i + 1 < len(sentences) and len(s["text"]) < 20 and sentences[i + 1]["text"]:
                    ns = sentences[i + 1]
                    new_sentences.append({"text": s["text"] + "、" + ns["text"], "punct": ns["punct"]})
                    i += 2
                else:
                    new_sentences.append(s)
                    i += 1
            sentences = new_sentences

        return "".join(s["text"] + s["punct"] for s in sentences)

    @staticmethod
    def analyze_word_heaviness(text: str) -> Dict[str, Any]:
        """
        文章の「重さ」を漢字率と難読語から判定（APIコスト0）
        """
        if not text:
            return {"kanji_rate": 0, "is_heavy": False}

        kanji_count = len(re.findall(r'[\u4E00-\u9FFF]', text))
        total_count = len(text)
        rate = (kanji_count / total_count) * 100 if total_count > 0 else 0

        # カクヨム・なろうの黄金比は 20%〜30%。35%を超えると「重い」と判定。
        return {
            "kanji_rate": round(rate, 1),
            "is_heavy": rate > 35,
            "advice": "漢字が多すぎます。ひらがなを増やして『白く』すると読みやすくなります。" if rate > 35 else "適切な密度です。"
        }


# ==========================================
# SeriousnessFilter（トーン調整フィルタ）
# ==========================================
class SeriousnessFilter:
    """文脈のシリアス度を判定し、記号や語彙の最終的な微調整を行う"""
    def filter(self, text: str, is_light: bool = True) -> str:
        if is_light:
            return text

        # シリアスな文体の場合、感嘆符と疑問符の組み合わせを落ち着いた表現に置換
        text = text.replace("！？", "。").replace("！！", "。")
        # 三点リーダーの過剰な連続を抑制
        text = re.sub(r'…{4,}', '……', text)
        return text


# ==========================================
# TextFormatter（カクヨム形式整形）
# ==========================================
class TextFormatter:
    @staticmethod
    def remove_ai_isms(text: str) -> str:
        """AI特有の定型句（AI-isms）を自然な表現に置換または削除する"""
        ai_isms = [
            (r'言うまでもない[がか]?、?', ''),
            (r'特筆すべきは、', ''),
            (r'その時だった。?', ''),
            (r'誰の目にも明らかだった。?', ''),
            (r'息を呑[むん]だ。?', '言葉を失った。'),
            (r'目を丸くした。?', '瞬きを忘れた。'),
            (r'驚きを隠せなかった。?', '絶句した。'),
            (r'静寂が支配した。?', '水を打ったような静けさが落ちた。'),
            (r'言うまでもない。', ''),
        ]
        for pattern, replacement in ai_isms:
            text = re.sub(pattern, replacement, text)
        return text

    @staticmethod
    def enforce_cliffhanger(text: str) -> str:
        """エピソード末尾の「引き（クリフハンガー）」を視覚的に強調する"""
        text = text.strip()
        if not text:
            return text

        # デバッグ：二重付与を防ぎつつ、読者が「次を読みたくなる」余韻を強制
        text = text.rstrip('。')
        if not text.endswith('――') and not text.endswith('……'):
            text += '――'

        # 最後の文を視覚的に分離して余韻を持たせる
        # 最後の改行以降を取得
        parts = text.rsplit('\n\n', 1)
        if len(parts) == 2:
            main_text, last_para = parts
            return f"{main_text}\n\n　――{last_para.strip()}"
        return text

    @staticmethod
    def format_for_kakuyomu(text: str) -> str:
        """カクヨム形式への完全整形：段落の「白さ」制御を強化"""
        if not text:
            return ""

        # AI-ismsの除去（改善案1）
        text = TextFormatter.remove_ai_isms(text)

        # シリアス度検知とギャグ補正の適用
        s_filter = SeriousnessFilter()
        text = s_filter.filter(text)

        # AI前置き・コードブロック除去 (FixedTextFormatterの改善を統合)
        text = re.sub(
            r'^(はい|承知|了解|以下|これ|Here|Sure|JSON形式で出力します|了解しました).*?(\n|$)',
            '', text, flags=re.IGNORECASE | re.MULTILINE
        ).strip()
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)

        # 構造タグ・メタタグの最終除去（堅牢なパイプラインの最終ゲート）
        struct_tags = r'(SCENE|Scene|シーン|CHAPTER|Chapter|第\d+話|EPISODE|Episode|エピソード)'
        text = re.sub(r'^[#\s\*]*\[?' + struct_tags + r'\s*[\d一二三四五六七八九十]+\]?[:：\s\*]*.*$', '', text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'\[.*?\]', '', text)

        # 台本形式の除去ロジックをより高速な単一パスの置換へ統合
        def _process_dialogue_line(match):
            notes = re.findall(r'[（(](.*?)[）)]', match.group(1))
            if notes:
                return "。".join(notes) + "。\n" + match.group(2)
            return match.group(1).strip() + "\n" + match.group(2)

        # 「セリフ」または『セリフ』の前に何かがある行を対象
        # DOTALLフラグは不要、MULTILINEで各行の先頭を^でマッチ
        text = re.sub(r'^([^「『\n]+)([「『].*?[」』])', _process_dialogue_line, text, flags=re.MULTILINE)

        # 記号の統一
        text = re.sub(r'\.{3,}', '……', text)
        text = re.sub(r'[…・]{1,}', '……', text)
        text = text.replace("。。", "。")
        text = re.sub(r'([？！])(?![\s　」』])', r'\1　', text)

        # --- 「白さ」の動的制御 (Category A: Implementation) ---
        analysis = ContentValidator.analyze_word_heaviness(text)
        kanji_rate = analysis["kanji_rate"]

        # 覇権Web小説の黄金比：漢字率20-30%。
        # 30%を超えるとスマホでは「黒い塊」に見えるため、強制的に改行強度を上げる。
        is_dense = kanji_rate > 30
        max_lines_per_para = 1 if is_dense else 2
        max_chars_per_line = 35 if kanji_rate > 35 else 45
        force_break_at_period = kanji_rate > 33

        lines         = [line.strip() for line in text.split('\n')]
        new_lines     = []
        narrative_cnt = 0

        for line in lines:
            if not line:
                if new_lines and new_lines[-1] != "":
                    new_lines.append("")
                narrative_cnt = 0
                continue
            # 全角インデントの自動付与（特定の記号以外）
            if line[0] not in ['「', '『', '（', '<', '【', '［', '〔', '〈', '《']:
                line = '　' + line

            is_dialogue = line.strip().startswith(('「', '『', '（'))

            if is_dialogue:
                # 会話文の前には空行を確保
                if new_lines and new_lines[-1] != "":
                    new_lines.append("")
                new_lines.append(line)
                # 会話文の後は必ず改段（空行）
                new_lines.append("")
                narrative_cnt = 0
            else:
                # 地の文の処理
                new_lines.append(line)
                narrative_cnt += 1

                # 漢字密度が高い場合、または句点に達した場合の動的改行
                should_break = False
                if force_break_at_period and "。" in line:
                    should_break = True
                elif narrative_cnt >= max_lines_per_para or len(line) > max_chars_per_line:
                    should_break = True

                if should_break:
                    new_lines.append("")
                    narrative_cnt = 0

        result = "\n".join(new_lines).strip()
        result = re.sub(r'\n{3,}', '\n\n', result)

        # 改善案5: 「引き（クリフハンガー）」の視覚的強調
        return TextFormatter.enforce_cliffhanger(result)


# ==========================================
# AtmosphereGenerator（環境演出補助）
# ==========================================
class AtmosphereGenerator:
    @staticmethod
    def get_prompt(season: str = "春", weather: str = "晴天") -> str:
        return f"【環境演出指令】現在の舞台背景: {season}/{weather}。描写に季節感と空気感を含めよ。"

    @staticmethod
    def get_sensory_anchors(season: str, weather: str, location: str) -> List[str]:
        anchors = []
        if season == "夏":
            anchors.append("肌を焼くような熱気")
        if season == "冬":
            anchors.append("肺の奥まで凍てつく冷気")
        if weather == "雨":
            anchors.append("地面を叩く激しい雨音")
        if weather == "晴天":
            anchors.append("目を細めるような強い陽光")
        return anchors

