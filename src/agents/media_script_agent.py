from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PanelScript(BaseModel):
    panel_number: int
    camera_angle: str = Field(
        ...,
        description="close_up | medium | wide | bird_eye | low_angle"
    )
    visual_description: str = Field(
        ...,
        description="コマ内の情景・人物の表情やポーズ"
    )
    dialogues: list[dict[str, str]] = Field(
        default_factory=list,
        description="[{'speaker': '...', 'text': '...'}]"
    )
    sfx: list[str] = Field(default_factory=list, description="オノマトペ・効果音")
    narration: str = ""


class MangaScriptOutput(BaseModel):
    page_number: int
    panels: list[PanelScript]
    scene_mood: str


class AudioDramaLine(BaseModel):
    character: str
    text: str
    emotion: str = "neutral"
    direction: str = ""
    audio_cues_before: list[dict[str, Any]] = Field(default_factory=list)
    audio_cues_after: list[dict[str, Any]] = Field(default_factory=list)


class AudioDramaScriptOutput(BaseModel):
    episode_title: str
    lines: list[AudioDramaLine]
    bgm_plan: list[dict[str, Any]] = Field(default_factory=list)
    sfx_plan: list[dict[str, Any]] = Field(default_factory=list)
    cast_requirements: dict[str, Any] = Field(default_factory=dict)


class MediaScriptAgent:
    def __init__(self, llm_provider=None, temperature: float = 0.4):
        self.llm = llm_provider
        self.temperature = temperature

    def _clean_json_markdown(self, raw: str) -> dict:
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed, attempting repair: {e}")
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            raise

    def _split_into_scenes(self, text: str, max_chars: int = 1500) -> list[str]:
        if len(text) <= max_chars:
            return [text]
        scenes = []
        paragraphs = re.split(r"\n\s*\n", text)
        current = ""
        for para in paragraphs:
            if len(current) + len(para) > max_chars and current:
                scenes.append(current.strip())
                current = para
            else:
                current += "\n\n" + para if current else para
        if current:
            scenes.append(current.strip())
        return scenes

    def _build_character_context(self, characters: list[dict]) -> str:
        if not characters:
            return "キャラクター情報なし"
        lines = []
        for char in characters:
            name = char.get("name", "不明")
            personality = char.get("personality", "")
            first_person = char.get("first_person", "")
            speech_pattern = char.get("speech_pattern", "")
            lines.append(f"- {name}: 性格={personality}, 一人称={first_person}, 口調={speech_pattern}")
        return "\n".join(lines)

    def _call_llm(self, prompt: str) -> str:
        if self.llm is None:
            raise RuntimeError("LLM provider not configured")
        return self.llm.generate(prompt, temperature=self.temperature)

    def _fallback_manga_script(self, chapter_text: str, characters: list[dict]) -> list[MangaScriptOutput]:
        logger.warning("Using rule-based fallback for manga script generation")
        scenes = self._split_into_scenes(chapter_text)
        results = []
        page_num = 1
        panel_num = 1
        for scene in scenes:
            panels = []
            sentences = re.split(r"(?<=。|！|？)\s*", scene)
            sentences = [s for s in sentences if s.strip()]
            panel_count = min(max(3, len(sentences) // 2), 6)
            for i in range(panel_count):
                chunk = sentences[i] if i < len(sentences) else ""
                panel = PanelScript(
                    panel_number=panel_num,
                    camera_angle="medium",
                    visual_description=chunk[:100] if chunk else "場面展開",
                    dialogues=[],
                    sfx=[],
                    narration=chunk
                )
                panels.append(panel)
                panel_num += 1
            results.append(MangaScriptOutput(
                page_number=page_num,
                panels=panels,
                scene_mood="neutral"
            ))
            page_num += 1
        return results

    def _fallback_audio_script(self, chapter_text: str, characters: list[dict]) -> AudioDramaScriptOutput:
        logger.warning("Using rule-based fallback for audio script generation")
        lines = []
        scenes = re.split(r"\n\s*\n", chapter_text)
        for scene in scenes:
            scene = scene.strip()
            if not scene:
                continue
            parts = re.split(r'(「[^」]*」|『[^』]*』|"[^"]*")', scene)
            current_narration = ""
            for part in parts:
                if not part:
                    continue
                if part.startswith(("「", "『", '"')):
                    if current_narration.strip():
                        lines.append(AudioDramaLine(
                            character="ナレーション",
                            text=current_narration.strip(),
                            emotion="neutral",
                            direction="[落ち着いた語り口で]"
                        ))
                        current_narration = ""
                    dialogue = part[1:-1]
                    speaker = "キャラクター"
                    emotion = "neutral"
                    if "！" in dialogue:
                        emotion = "excited"
                    elif "？" in dialogue:
                        emotion = "questioning"
                    direction = "[自然体]"
                    lines.append(AudioDramaLine(
                        character=speaker,
                        text=dialogue,
                        emotion=emotion,
                        direction=direction
                    ))
                else:
                    current_narration += part
            if current_narration.strip():
                lines.append(AudioDramaLine(
                    character="ナレーション",
                    text=current_narration.strip(),
                    emotion="neutral",
                    direction="[落ち着いた語り口で]"
                ))
        return AudioDramaScriptOutput(
            episode_title="エピソード",
            lines=lines,
            bgm_plan=[],
            sfx_plan=[],
            cast_requirements={}
        )

    def generate_manga_script(self, chapter_text: str, characters: list[dict]) -> list[MangaScriptOutput]:
        try:
            from src.agents.prompts.media_script_prompts import MANGA_ADAPTATION_PROMPT
            character_context = self._build_character_context(characters)
            scenes = self._split_into_scenes(chapter_text)
            all_outputs = []
            page_num = 1
            for scene in scenes:
                prompt = MANGA_ADAPTATION_PROMPT.format(
                    character_context=character_context,
                    chapter_text=scene
                )
                response = self._call_llm(prompt)
                data = self._clean_json_markdown(response)
                data["page_number"] = page_num
                output = MangaScriptOutput(**data)
                all_outputs.append(output)
                page_num += 1
            return all_outputs
        except Exception as e:
            logger.error(f"Manga script generation failed: {e}")
            return self._fallback_manga_script(chapter_text, characters)

    def generate_audio_script(self, chapter_text: str, characters: list[dict]) -> AudioDramaScriptOutput:
        try:
            from src.agents.prompts.media_script_prompts import AUDIO_DRAMA_ADAPTATION_PROMPT
            character_context = self._build_character_context(characters)
            prompt = AUDIO_DRAMA_ADAPTATION_PROMPT.format(
                character_context=character_context,
                chapter_text=chapter_text
            )
            response = self._call_llm(prompt)
            data = self._clean_json_markdown(response)
            return AudioDramaScriptOutput(**data)
        except Exception as e:
            logger.error(f"Audio script generation failed: {e}")
            return self._fallback_audio_script(chapter_text, characters)