"""
メディアミックス出力
小説を漫画・音声ドラマ・動画用台本に変換
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

from src.easy_mode.pipeline import EpisodeResult, SeriesResult

logger = logging.getLogger(__name__)


class MediaFormat(str, Enum):
    """メディアフォーマット"""

    MANGA = "manga"  # 漫画用台本（コマ割り・セリフ・ト書き）
    AUDIO_DRAMA = "audio_drama"  # 音声ドラマ台本（効果音・BGM・セリフ・ナレーション）
    VIDEO = "video"  # 動画台本（カット・アングル・演出指示・字幕）
    LIGHT_NOVEL = "light_novel"  # ラノベ形式（挿絵指示込み）
    WEBTOON = "webtoon"  # 縦スクロール漫画


@dataclass
class Panel:
    """漫画コマ"""

    number: int
    description: str  # コマの内容説明
    dialogue: List[str] = field(default_factory=list)  # セリフ
    narration: str = ""  # ナレーション/ト書き
    sfx: List[str] = field(default_factory=list)  # 効果音
    camera_angle: str = "medium"  # カメラアングル
    characters: List[str] = field(default_factory=list)  # 登場キャラ
    background: str = ""  # 背景指定
    mood: str = "neutral"  # 雰囲気

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "description": self.description,
            "dialogue": self.dialogue,
            "narration": self.narration,
            "sfx": self.sfx,
            "camera_angle": self.camera_angle,
            "characters": self.characters,
            "background": self.background,
            "mood": self.mood,
        }


@dataclass
class AudioCue:
    """音声キュー"""

    type: str  # "bgm", "sfx", "voice", "silence"
    name: str
    description: str
    duration: float = 0.0  # 秒
    volume: float = 1.0
    fade_in: float = 0.0
    fade_out: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "name": self.name,
            "description": self.description,
            "duration": self.duration,
            "volume": self.volume,
            "fade_in": self.fade_in,
            "fade_out": self.fade_out,
        }


@dataclass
class VoiceLine:
    """セリフ行（音声ドラマ用）"""

    character: str
    text: str
    emotion: str = "neutral"
    direction: str = ""  # 演出指示
    audio_cues_before: List[AudioCue] = field(default_factory=list)
    audio_cues_after: List[AudioCue] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character": self.character,
            "text": self.text,
            "emotion": self.emotion,
            "direction": self.direction,
            "audio_cues_before": [c.to_dict() for c in self.audio_cues_before],
            "audio_cues_after": [c.to_dict() for c in self.audio_cues_after],
        }


@dataclass
class VideoShot:
    """動画ショット"""

    number: int
    duration: float  # 秒
    visual_description: str
    dialogue: List[str] = field(default_factory=list)
    narration: str = ""
    camera_movement: str = "static"
    angle: str = "eye_level"
    lighting: str = "natural"
    bgm: str = ""
    sfx: List[str] = field(default_factory=list)
    transition: str = "cut"
    subtitle: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "duration": self.duration,
            "visual_description": self.visual_description,
            "dialogue": self.dialogue,
            "narration": self.narration,
            "camera_movement": self.camera_movement,
            "angle": self.angle,
            "lighting": self.lighting,
            "bgm": self.bgm,
            "sfx": self.sfx,
            "transition": self.transition,
            "subtitle": self.subtitle,
        }


@dataclass
class MediaScript:
    """メディア台本"""

    format: MediaFormat
    title: str
    episode_num: int
    source_content: str
    panels: List[Panel] = field(default_factory=list)  # 漫画
    voice_lines: List[VoiceLine] = field(default_factory=list)  # 音声ドラマ
    shots: List[VideoShot] = field(default_factory=list)  # 動画
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "format": self.format.value,
            "title": self.title,
            "episode_num": self.episode_num,
            "source_content": self.source_content,
            "panels": [p.to_dict() for p in self.panels],
            "voice_lines": [v.to_dict() for v in self.voice_lines],
            "shots": [s.to_dict() for s in self.shots],
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class MangaScriptGenerator:
    """漫画台本生成器"""

    def __init__(self, genre: str, preset: Dict[str, Any]):
        self.genre = genre
        self.preset = preset
        self.style_guide = preset.get("style", {})
        self.characters = preset.get("characters", {}).get("archetypes", {})

    def generate(self, episode: EpisodeResult, series: SeriesResult) -> MediaScript:
        """漫画台本生成"""
        panels = self._split_into_panels(episode.content, episode)

        return MediaScript(
            format=MediaFormat.MANGA,
            title=f"{series.title} 第{episode.episode_num}話",
            episode_num=episode.episode_num,
            source_content=episode.content,
            panels=panels,
            metadata={
                "genre": self.genre,
                "total_panels": len(panels),
                "estimated_pages": max(1, len(panels) // 4),
                "style_notes": self.style_guide.get("manga_notes", ""),
            },
        )

    def _split_into_panels(self, content: str, episode: EpisodeResult) -> List[Panel]:
        """本文をコマに分割"""
        panels = []

        # 段落・シーン単位で分割
        scenes = self._extract_scenes(content)

        panel_num = 1
        for scene in scenes:
            scene_panels = self._scene_to_panels(scene, panel_num, episode)
            panels.extend(scene_panels)
            panel_num += len(scene_panels)

        return panels

    def _extract_scenes(self, content: str) -> List[Dict[str, Any]]:
        """シーン抽出"""
        scenes = []

        # 改行2つ以上でシーン区切り
        raw_scenes = re.split(r"\n\s*\n", content)

        for i, scene_text in enumerate(raw_scenes):
            scene_text = scene_text.strip()
            if not scene_text:
                continue

            # シーンタイプ判定
            scene_type = self._classify_scene(scene_text)
            characters = self._extract_characters(scene_text)

            scenes.append(
                {
                    "index": i,
                    "text": scene_text,
                    "type": scene_type,
                    "characters": characters,
                    "word_count": len(scene_text),
                }
            )

        return scenes

    def _classify_scene(self, text: str) -> str:
        """シーンタイプ分類"""
        text_lower = text.lower()

        # 会話重視
        dialogue_ratio = len(re.findall(r'「[^」]*」|『[^』]*』|"[^"]*"', text)) / max(
            1, len(text) / 100
        )
        if dialogue_ratio > 0.3:
            return "dialogue"

        # アクション
        action_keywords = ["走", "跳", "斬", "撃", "魔法", "スキル", "能力", "発動", "爆発", "衝突"]
        if any(kw in text for kw in action_keywords):
            return "action"

        # 感情・内面
        emotion_keywords = ["思", "感", "胸", "心", "涙", "怒", "喜", "悲", "恐", "覚悟", "決意"]
        if any(kw in text for kw in emotion_keywords):
            return "emotion"

        # 説明・世界観
        if len(text) > 500:
            return "exposition"

        return "normal"

    def _extract_characters(self, text: str) -> List[str]:
        """登場キャラ抽出"""
        characters = []
        archetypes = self.characters

        for archetype_name, archetype_data in archetypes.items():
            name_pattern = archetype_data.get("name_pattern", "")
            if name_pattern:
                # パターンから名前を抽出
                names = re.findall(rf"{re.escape(name_pattern.split('（')[0])}[^」」\s]*", text)
                characters.extend(names)

        # セリフから話者推定
        speakers = re.findall(r"([^「\n]{1,10})「", text)
        characters.extend([s.strip() for s in speakers if len(s.strip()) <= 10])

        return list(set(characters))

    def _scene_to_panels(
        self, scene: Dict[str, Any], start_num: int, episode: EpisodeResult
    ) -> List[Panel]:
        """シーンをコマに変換"""
        panels = []
        text = scene["text"]
        scene_type = scene["type"]
        characters = scene["characters"]

        # 文字数に基づいてコマ数決定
        word_count = len(text)
        if scene_type == "dialogue":
            panel_count = max(2, word_count // 150)
        elif scene_type == "action":
            panel_count = max(3, word_count // 100)
        elif scene_type == "emotion":
            panel_count = max(2, word_count // 200)
        else:
            panel_count = max(1, word_count // 300)

        panel_count = min(panel_count, 8)  # 最大8コマ

        # テキストを分割
        text_chunks = self._split_text_for_panels(text, panel_count)

        for i, chunk in enumerate(text_chunks):
            panel = Panel(
                number=start_num + i,
                description=self._generate_panel_description(chunk, scene_type, characters),
                dialogue=self._extract_dialogue(chunk),
                narration=self._extract_narration(chunk),
                sfx=self._generate_sfx(scene_type, chunk),
                camera_angle=self._determine_camera_angle(scene_type, i, panel_count),
                characters=characters,
                background=self._determine_background(scene_type, chunk),
                mood=self._determine_mood(scene_type, chunk),
            )
            panels.append(panel)

        return panels

    def _split_text_for_panels(self, text: str, count: int) -> List[str]:
        """テキストをコマ数分に分割"""
        if count <= 1:
            return [text]

        # 文単位で分割
        sentences = re.split(r"(?<=。|！|？)\s*", text)
        sentences = [s for s in sentences if s]

        if len(sentences) <= count:
            return sentences + [""] * (count - len(sentences))

        # 均等分配
        chunk_size = len(sentences) // count
        chunks = []
        for i in range(count):
            start = i * chunk_size
            end = start + chunk_size if i < count - 1 else len(sentences)
            chunks.append("".join(sentences[start:end]))

        return chunks

    def _generate_panel_description(self, text: str, scene_type: str, characters: List[str]) -> str:
        """コマ説明生成"""
        desc_parts = []

        if scene_type == "dialogue":
            desc_parts.append(f"会話シーン: {', '.join(characters[:3])}が会話")
        elif scene_type == "action":
            desc_parts.append(f"アクション: {', '.join(characters[:2])}が戦闘/行動")
        elif scene_type == "emotion":
            desc_parts.append(f"心理描写: {characters[0] if characters else '主人公'}の内面")
        else:
            desc_parts.append("説明/展開: 物語の進行")

        # 重要キーワード抽出
        keywords = re.findall(r"[一-龯]{2,}", text)[:3]
        if keywords:
            desc_parts.append(f"キーワード: {', '.join(keywords)}")

        return " | ".join(desc_parts)

    def _extract_dialogue(self, text: str) -> List[str]:
        """セリフ抽出"""
        return re.findall(r'「([^」]*)」|『([^』]*)』|"([^"]*)"', text)

    def _extract_narration(self, text: str) -> str:
        """ナレーション/ト書き抽出"""
        # セリフを除いた部分
        narration = re.sub(r'「[^」]*」|『[^』]*』|"[^"]*"', "", text)
        narration = re.sub(r"\s+", " ", narration).strip()
        return narration[:200]  # 最大200文字

    def _generate_sfx(self, scene_type: str, text: str) -> List[str]:
        """効果音生成"""
        sfx = []

        if scene_type == "action":
            if any(kw in text for kw in ["斬", "切", "剣"]):
                sfx.append("SE: 剣の閃光音")
            if any(kw in text for kw in ["魔法", "発動", "詠唱"]):
                sfx.append("SE: 魔法発動音")
            if any(kw in text for kw in ["爆発", "破裂", "衝突"]):
                sfx.append("SE: 爆発音")
            if any(kw in text for kw in ["走", "駆", "跳"]):
                sfx.append("SE: 足音・疾走音")
        elif scene_type == "emotion":
            if any(kw in text for kw in ["涙", "泣"]):
                sfx.append("SE: 涙の音・すすり泣き")
            if any(kw in text for kw in ["心臓", "鼓動", "ドキ"]):
                sfx.append("SE: 心拍音")

        # 汎用
        if "「" in text:
            sfx.append("SE: ページめくり・場面転換")

        return sfx[:3]  # 最大3つ

    def _determine_camera_angle(self, scene_type: str, index: int, total: int) -> str:
        """カメラアングル決定"""
        if scene_type == "action":
            if index == 0:
                return "wide"  # 全体見せ
            elif index == total - 1:
                return "close_up"  # 決めコマ
            return "dynamic"
        elif scene_type == "emotion":
            return "close_up"
        elif scene_type == "dialogue":
            if index == 0:
                return "medium"
            return "over_shoulder"
        return "medium"

    def _determine_background(self, scene_type: str, text: str) -> str:
        """背景決定"""
        # 場所キーワード検索
        locations = {
            "城": ["城", "王宮", "玉座", "ホール"],
            "森": ["森", "木々", "木立", "草原"],
            "街": ["街", "町", "路地", "市場", "広場"],
            "部屋": ["部屋", "寝室", "書斎", "リビング"],
            "ダンジョン": ["ダンジョン", "洞窟", "地下", "迷宮"],
            "学校": ["学校", "教室", "校庭", "体育館"],
            "現代": ["ビル", "オフィス", "電車", "コンビニ", "マンション"],
        }

        for bg, keywords in locations.items():
            if any(kw in text for kw in keywords):
                return bg

        return "汎用背景"

    def _determine_mood(self, scene_type: str, text: str) -> str:
        """ムード決定"""
        if scene_type == "action":
            return "tense"
        elif scene_type == "emotion":
            if any(kw in text for kw in ["悲", "泣", "涙", "苦"]):
                return "sad"
            elif any(kw in text for kw in ["喜", "笑", "幸", "安心"]):
                return "happy"
            elif any(kw in text for kw in ["怒", "憤", "激昂"]):
                return "angry"
            return "emotional"
        elif scene_type == "dialogue":
            return "conversational"
        return "neutral"


class AudioDramaScriptGenerator:
    """音声ドラマ台本生成器"""

    def __init__(self, genre: str, preset: Dict[str, Any]):
        self.genre = genre
        self.preset = preset
        self.characters = preset.get("characters", {}).get("archetypes", {})
        self.erotic_rules = preset.get("erotic", {})

    def generate(self, episode: EpisodeResult, series: SeriesResult) -> MediaScript:
        """音声ドラマ台本生成"""
        voice_lines = self._convert_to_voice_lines(episode.content, episode)

        # BGM・効果音プラン生成
        bgm_plan = self._generate_bgm_plan(episode, series)
        sfx_plan = self._generate_sfx_plan(episode)

        return MediaScript(
            format=MediaFormat.AUDIO_DRAMA,
            title=f"{series.title} 第{episode.episode_num}話【音声ドラマ版】",
            episode_num=episode.episode_num,
            source_content=episode.content,
            voice_lines=voice_lines,
            metadata={
                "genre": self.genre,
                "total_lines": len(voice_lines),
                "estimated_duration_min": len(voice_lines) * 15 / 60,  # 1行15秒換算
                "bgm_plan": bgm_plan,
                "sfx_plan": sfx_plan,
                "cast_requirements": self._get_cast_requirements(voice_lines),
            },
        )

    def _convert_to_voice_lines(self, content: str, episode: EpisodeResult) -> List[VoiceLine]:
        """本文をセリフ行に変換"""
        lines = []

        # シーン分割
        scenes = re.split(r"\n\s*\n", content)

        for scene in scenes:
            scene = scene.strip()
            if not scene:
                continue

            scene_lines = self._scene_to_voice_lines(scene)
            lines.extend(scene_lines)

            # シーン間の無音/転換
            lines.append(
                VoiceLine(
                    character="ナレーション",
                    text="",  # 無音キュー用
                    emotion="neutral",
                    direction="[シーン転換・無音2秒]",
                    audio_cues_after=[
                        AudioCue(
                            type="silence",
                            name="scene_transition",
                            description="シーン転換の無音",
                            duration=2.0,
                        )
                    ],
                )
            )

        return lines

    def _scene_to_voice_lines(self, scene: str) -> List[VoiceLine]:
        """シーンをセリフ行に分解"""
        lines = []

        # セリフパターンで分割
        # 「セリフ」や「ナレーション」を分離
        parts = re.split(r'(「[^」]*」|『[^』]*』|"[^"]*")', scene)

        current_narration = ""

        for part in parts:
            if not part:
                continue

            # セリフ判定
            if part.startswith(("「", "『", '"')):
                # 前のナレーションがあれば先に処理
                if current_narration.strip():
                    lines.append(
                        VoiceLine(
                            character="ナレーション",
                            text=current_narration.strip(),
                            emotion="neutral",
                            direction="[落ち着いた語り口で]",
                        )
                    )
                    current_narration = ""

                # セリフ処理
                dialogue = part[1:-1]  # 括弧除去
                speaker = self._guess_speaker(dialogue, scene)
                emotion = self._guess_emotion(dialogue)
                direction = self._generate_direction(dialogue, emotion)

                lines.append(
                    VoiceLine(
                        character=speaker,
                        text=dialogue,
                        emotion=emotion,
                        direction=direction,
                        audio_cues_before=self._get_pre_audio_cues(dialogue),
                        audio_cues_after=self._get_post_audio_cues(dialogue),
                    )
                )
            else:
                # ナレーション蓄積
                current_narration += part

        # 残りのナレーション
        if current_narration.strip():
            lines.append(
                VoiceLine(
                    character="ナレーション",
                    text=current_narration.strip(),
                    emotion="neutral",
                    direction="[落ち着いた語り口で]",
                )
            )

        return lines

    def _guess_speaker(self, dialogue: str, context: str) -> str:
        """話者推定"""
        # 文末・一人称から推定
        archetypes = self.characters

        for archetype_name, archetype_data in archetypes.items():
            speech = archetype_data.get("speech_patterns", {})
            first_person = speech.get("first_person", "")
            if first_person and first_person in dialogue:
                return archetype_data.get("name_pattern", "").split("（")[0]

            forbidden = speech.get("forbidden_words", [])
            if any(w in dialogue for w in forbidden):
                # 禁句を使うキャラではない
                continue

        # デフォルト
        if "私" in dialogue or "わたし" in dialogue:
            return "主人公"
        elif "俺" in dialogue:
            return "主人公(男性口調)"
        elif "僕" in dialogue:
            return "主人公(少年口調)"

        return "キャラクター"

    def _guess_emotion(self, dialogue: str) -> str:
        """感情推定"""
        if any(kw in dialogue for kw in ["！", "ッ", "！"]):
            if any(kw in dialogue for kw in ["死", "殺", "許さ", "絶対", "覚悟"]):
                return "anger"
            return "excited"
        elif "？" in dialogue:
            return "questioning"
        elif any(kw in dialogue for kw in ["…", "。。", "ふう", "はぁ"]):
            return "sad"
        elif any(kw in dialogue for kw in ["笑", "わはは", "くくく", "フフ"]):
            return "amused"
        return "neutral"

    def _generate_direction(self, dialogue: str, emotion: str) -> str:
        """演出指示生成"""
        directions = {
            "anger": "[激昂・声量大・早口]",
            "excited": "[高揚・明るく・早め]",
            "questioning": "[疑問・やや上ずり]",
            "sad": "[静か・低め・間を置く]",
            "amused": "[余裕・楽しげ・ゆったり]",
            "neutral": "[自然体・標準]",
        }
        return directions.get(emotion, "[自然体]")

    def _get_pre_audio_cues(self, dialogue: str) -> List[AudioCue]:
        """セリフ前の音声キュー"""
        cues = []
        if "…" in dialogue:
            cues.append(
                AudioCue(type="sfx", name="pause", description="間・ためらい", duration=0.5)
            )
        return cues

    def _get_post_audio_cues(self, dialogue: str) -> List[AudioCue]:
        """セリフ後の音声キュー"""
        cues = []
        if "！" in dialogue or "ッ" in dialogue:
            cues.append(
                AudioCue(
                    type="sfx", name="impact", description="セリフの余韻・インパクト", duration=0.3
                )
            )
        return cues

    def _generate_bgm_plan(
        self, episode: EpisodeResult, series: SeriesResult
    ) -> List[Dict[str, Any]]:
        """BGMプラン生成"""
        return [
            {"scene": "opening", "track": "main_theme", "mood": "epic"},
            {"scene": "daily", "track": "peaceful_daily", "mood": "calm"},
            {"scene": "tension", "track": "tension_rising", "mood": "tense"},
            {"scene": "climax", "track": "battle_climax", "mood": "intense"},
            {"scene": "resolution", "track": "ending_theme", "mood": "peaceful"},
        ]

    def _generate_sfx_plan(self, episode: EpisodeResult) -> List[Dict[str, Any]]:
        """効果音プラン生成"""
        return [
            {"trigger": "scene_change", "sound": "whoosh", "timing": "transition"},
            {"trigger": "magic", "sound": "magic_charge", "timing": "on_cast"},
            {"trigger": "combat_hit", "sound": "sword_clash", "timing": "on_impact"},
            {"trigger": "emotional", "sound": "heartbeat", "timing": "on_reveal"},
            {"trigger": "comedy", "sound": "boing", "timing": "on_punchline"},
        ]

    def _get_cast_requirements(self, lines: List[VoiceLine]) -> Dict[str, Any]:
        """キャスト要件"""
        characters = set()
        emotions = set()

        for line in lines:
            if line.character != "ナレーション":
                characters.add(line.character)
                emotions.add(line.emotion)

        return {
            "characters": list(characters),
            "required_emotions": list(emotions),
            "narrator_needed": any(l.character == "ナレーション" for l in lines),
            "total_voice_actors": len(characters)
            + (1 if any(l.character == "ナレーション" for l in lines) else 0),
        }


class VideoScriptGenerator:
    """動画台本生成器"""

    def __init__(self, genre: str, preset: Dict[str, Any]):
        self.genre = genre
        self.preset = preset

    def generate(self, episode: EpisodeResult, series: SeriesResult) -> MediaScript:
        """動画台本生成"""
        shots = self._convert_to_shots(episode.content, episode)

        return MediaScript(
            format=MediaFormat.VIDEO,
            title=f"{series.title} 第{episode.episode_num}話【動画版】",
            episode_num=episode.episode_num,
            source_content=episode.content,
            shots=shots,
            metadata={
                "genre": self.genre,
                "total_shots": len(shots),
                "estimated_duration_min": sum(s.duration for s in shots) / 60,
                "aspect_ratio": "16:9",
                "resolution": "1920x1080",
                "style_notes": self._get_style_notes(),
            },
        )

    def _convert_to_shots(self, content: str, episode: EpisodeResult) -> List[VideoShot]:
        """本文をショットに変換"""
        shots = []

        # シーン分割
        scenes = re.split(r"\n\s*\n", content)

        shot_num = 1
        for scene in scenes:
            scene = scene.strip()
            if not scene:
                continue

            scene_shots = self._scene_to_shots(scene, shot_num, episode)
            shots.extend(scene_shots)
            shot_num += len(scene_shots)

        return shots

    def _scene_to_shots(
        self, scene: str, start_num: int, episode: EpisodeResult
    ) -> List[VideoShot]:
        """シーンをショットに分解"""
        shots = []

        # 文単位で分割
        sentences = re.split(r"(?<=。|！|？)\s*", scene)
        sentences = [s for s in sentences if s.strip()]

        # 動画は1ショット3-5秒目安
        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue

            shot_type = self._classify_shot_type(sentence)
            duration = self._estimate_duration(sentence, shot_type)

            shot = VideoShot(
                number=start_num + i,
                duration=duration,
                visual_description=self._generate_visual_description(sentence, shot_type),
                dialogue=self._extract_dialogue_for_shot(sentence),
                narration=self._extract_narration_for_shot(sentence),
                camera_movement=self._get_camera_movement(shot_type, i, len(sentences)),
                angle=self._get_camera_angle(shot_type),
                lighting=self._get_lighting(shot_type, sentence),
                bgm=self._get_bgm_for_shot(shot_type),
                sfx=self._get_sfx_for_shot(shot_type, sentence),
                transition=self._get_transition(i, len(sentences)),
                subtitle=self._generate_subtitle(sentence),
            )
            shots.append(shot)

        return shots

    def _classify_shot_type(self, text: str) -> str:
        """ショットタイプ分類"""
        if "「" in text or "『" in text:
            return "dialogue"
        elif any(kw in text for kw in ["走", "斬", "撃", "魔法", "発動", "跳", "飛"]):
            return "action"
        elif any(kw in text for kw in ["思", "感", "胸", "心", "涙", "決意"]):
            return "emotion"
        elif len(text) > 100:
            return "exposition"
        return "normal"

    def _estimate_duration(self, text: str, shot_type: str) -> float:
        """ショット長推定"""
        base = {"dialogue": 4.0, "action": 3.0, "emotion": 5.0, "exposition": 6.0, "normal": 4.0}
        char_factor = min(len(text) / 50, 2.0)
        return base.get(shot_type, 4.0) + char_factor

    def _generate_visual_description(self, text: str, shot_type: str) -> str:
        """視覚描写生成"""
        desc = f"[{shot_type.upper()}] "

        # キャラ・動作抽出
        chars = re.findall(r"([一-龯]{1,5})[はがをにへとで]", text)[:2]
        if chars:
            desc += f"{', '.join(chars)}が"

        # 動作
        actions = re.findall(r"(走|斬|撃|跳|飛|見|聞|考|思い|感じ|叫|笑|泣)", text)
        if actions:
            desc += f"{', '.join(actions[:3])}する"

        # 場所
        locations = ["城", "森", "街", "部屋", "ダンジョン", "学校", "広場"]
        for loc in locations:
            if loc in text:
                desc += f" 場所:{loc}"
                break

        return desc.strip()

    def _extract_dialogue_for_shot(self, text: str) -> List[str]:
        return [
            m[0] or m[1] or m[2] for m in re.findall(r'「([^」]*)」|『([^』]*)』|"([^"]*)"', text)
        ]

    def _extract_narration_for_shot(self, text: str) -> str:
        narration = re.sub(r'「[^」]*」|『[^』]*』|"[^"]*"', "", text)
        return narration.strip()[:100]

    def _get_camera_movement(self, shot_type: str, index: int, total: int) -> str:
        movements = {
            "dialogue": "static",
            "action": "tracking" if index < total - 1 else "static",
            "emotion": "slow_zoom_in",
            "exposition": "pan",
            "normal": "static",
        }
        return movements.get(shot_type, "static")

    def _get_camera_angle(self, shot_type: str) -> str:
        angles = {
            "dialogue": "over_shoulder",
            "action": "low_angle",
            "emotion": "close_up",
            "exposition": "wide",
            "normal": "eye_level",
        }
        return angles.get(shot_type, "eye_level")

    def _get_lighting(self, shot_type: str, text: str) -> str:
        if shot_type == "emotion" and any(kw in text for kw in ["悲", "暗", "夜", "影"]):
            return "low_key"
        elif shot_type == "action":
            return "high_contrast"
        elif shot_type == "exposition":
            return "natural"
        return "three_point"

    def _get_bgm_for_shot(self, shot_type: str) -> str:
        bgm = {
            "dialogue": "bgm_dialogue",
            "action": "bgm_battle",
            "emotion": "bgm_emotional",
            "exposition": "bgm_exposition",
            "normal": "bgm_ambient",
        }
        return bgm.get(shot_type, "bgm_ambient")

    def _get_sfx_for_shot(self, shot_type: str, text: str) -> List[str]:
        sfx = []
        if shot_type == "action":
            sfx.extend(["sfx_sword", "sfx_magic", "sfx_impact"])
        elif shot_type == "emotion":
            sfx.append("sfx_heartbeat")
        if "ドア" in text or "扉" in text:
            sfx.append("sfx_door")
        return sfx[:2]

    def _get_transition(self, index: int, total: int) -> str:
        if index == total - 1:
            return "fade_out"
        return "cut"

    def _generate_subtitle(self, text: str) -> str:
        # 字幕用に短縮
        clean = re.sub(r'「[^」]*」|『[^』]*』|"[^"]*"', "", text)
        return clean[:50] + ("..." if len(clean) > 50 else "")

    def _get_style_notes(self) -> str:
        return f"Genre: {self.genre} | Target: 16:9 1080p | Color grading: {self.genre}_palette"


class MediaMixExporter:
    """メディアミックス一括エクスポーター"""

    def __init__(self, genre: str, preset: Dict[str, Any]):
        self.genre = genre
        self.preset = preset
        self.manga_gen = MangaScriptGenerator(genre, preset)
        self.audio_gen = AudioDramaScriptGenerator(genre, preset)
        self.video_gen = VideoScriptGenerator(genre, preset)

    def export_all(
        self, episode: EpisodeResult, series: SeriesResult, formats: List[MediaFormat] = None
    ) -> Dict[MediaFormat, MediaScript]:
        """全フォーマット出力"""
        if formats is None:
            formats = [MediaFormat.MANGA, MediaFormat.AUDIO_DRAMA, MediaFormat.VIDEO]

        results = {}
        for fmt in formats:
            if fmt == MediaFormat.MANGA:
                results[fmt] = self.manga_gen.generate(episode, series)
            elif fmt == MediaFormat.AUDIO_DRAMA:
                results[fmt] = self.audio_gen.generate(episode, series)
            elif fmt == MediaFormat.VIDEO:
                results[fmt] = self.video_gen.generate(episode, series)
            else:
                logger.warning(f"Unsupported format: {fmt}")

        return results

    def save_all(
        self, scripts: Dict[MediaFormat, MediaScript], output_dir: Path
    ) -> Dict[MediaFormat, Path]:
        """全台本保存"""
        output_dir.mkdir(parents=True, exist_ok=True)
        saved = {}

        for fmt, script in scripts.items():
            filename = f"ep{script.episode_num:03d}_{fmt.value}.json"
            path = output_dir / filename
            path.write_text(script.to_json(), encoding="utf-8")
            saved[fmt] = path
            logger.info(f"Saved {fmt.value} script to {path}")

        return saved


def create_media_mix_exporter(genre: str, preset: Dict[str, Any]) -> MediaMixExporter:
    """メディアミックスエクスポーター作成"""
    return MediaMixExporter(genre, preset)
