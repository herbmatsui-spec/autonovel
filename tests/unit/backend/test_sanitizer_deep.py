from __future__ import annotations

import json
import pytest
from pydantic import BaseModel, Field, ValidationError

from src.backend.sanitizer import (
    CONTENT_SEPARATOR,
    NormalizationFlow,
    OutputSanitizer,
    TonePerfector,
)
from src.models import CharacterRegistry


def test_normalization_flow_unwrap_nested_metadata():
    flow = NormalizationFlow()
    nested = {"metadata": {"title": "Test Title", "ep_num": 1}}
    unwrapped = flow.unwrap_nested_metadata(nested)
    assert unwrapped == {"title": "Test Title", "ep_num": 1}

    multi_nested = {"response": {"data": {"content": {"ep_num": 5}}}}
    unwrapped_multi = flow.unwrap_nested_metadata(multi_nested)
    assert unwrapped_multi == {"ep_num": 5}

    assert flow.unwrap_nested_metadata("plain_string") == "plain_string"


def test_normalization_flow_resolve_aliases():
    flow = NormalizationFlow()

    d1 = {"episode_number": "第3話"}
    resolved = flow.resolve_aliases(d1)
    assert resolved["ep_num"] == 3

    d2 = {"scene_no": "scene_4"}
    resolved = flow.resolve_aliases(d2)
    assert resolved["scene_number"] == 4

    d3 = {"severity": "致命的なエラー"}
    resolved = flow.resolve_aliases(d3)
    assert resolved["severity"] == "Critical"

    d4 = {"severity": "軽い警告"}
    resolved = flow.resolve_aliases(d4)
    assert resolved["severity"] == "Minor"

    d5 = {"char_list": ["勇者", "魔王"]}
    resolved = flow.resolve_aliases(d5)
    assert resolved["characters"] == ["勇者", "魔王"]

    d6 = {"synopsis": "これは十分に長いあらすじテキストです。" * 5}
    resolved = flow.resolve_aliases(d6)
    assert "detailed_blueprint" in resolved


def test_normalization_flow_coerce_types():
    flow = NormalizationFlow()

    d1 = {
        "title": None,
        "detailed_blueprint": ["章1", "章2"],
        "keywords": ["tag1", "tag2"],
        "stress_delta": "+15",
    }
    coerced = flow.coerce_types(d1)
    assert coerced["title"] == ""
    assert "章1\n\n章2" in coerced["detailed_blueprint"]
    assert "tag1, tag2" in coerced["keywords"]
    assert coerced["stress_delta"] == 15

    d2 = {"next_hook": "危機が迫る"}
    coerced2 = flow.coerce_types(d2)
    assert isinstance(coerced2["next_hook"], dict)
    assert coerced2["next_hook"]["type"] == "New Crisis"
    assert coerced2["next_hook"]["description"] == "危機が迫る"

    d3 = {"next_hook": None}
    coerced3 = flow.coerce_types(d3)
    assert coerced3["next_hook"]["type"] == "Quiet Foreshadowing"


def test_normalization_flow_normalize_lists():
    flow = NormalizationFlow()

    raw_scenes = ["勇者が立ち上がる", {"scene_number": 2, "action": "剣を抜く"}]
    norm_scenes = flow.normalize_lists(raw_scenes, "scenes")
    assert norm_scenes[0]["action"] == "勇者が立ち上がる"
    assert norm_scenes[0]["scene_number"] == 1
    assert norm_scenes[1]["scene_number"] == 2

    raw_beats = [
        "導入部分",
        {
            "beat_type": "感情の展開",
            "sensory_keywords": "光, 風、香り",
            "psychology_keywords": "期待、 不安",
        },
    ]
    norm_beats = flow.normalize_lists(raw_beats, "beats")
    assert norm_beats[0]["action_description"] == "導入部分"
    assert norm_beats[1]["beat_type"] == "展開"
    assert norm_beats[1]["sensory_keywords"] == ["光", "風", "香り"]
    assert norm_beats[1]["psychology_keywords"] == ["期待", "不安"]


def test_normalization_flow_normalize_metadata_full():
    flow = NormalizationFlow()
    raw = {
        "metadata": {
            "episode_number": "1",
            "current_chain_phase": "ざまぁ爆発",
            "scenes": ["シーン1", "シーン2"],
        }
    }
    normalized = flow.normalize_metadata(raw)
    assert normalized["ep_num"] == 1
    assert normalized["current_chain_phase"] == "Payoff"
    assert len(normalized["scenes"]) == 2


def test_output_sanitizer_parse_llm_json():
    raw_with_garbage = "思考過程: 以下の通り出力します。\n{\"result\": true, \"count\": 10}\n以上です。"
    parsed = OutputSanitizer.parse_llm_json(raw_with_garbage)
    assert parsed.get("result") is True
    assert parsed.get("count") == 10

    # 空文字列や無効な文字列
    assert OutputSanitizer.parse_llm_json("") == {}
    assert OutputSanitizer.parse_llm_json("no json here") == {}


def test_output_sanitizer_extract_content_and_metadata():
    text = f"{CONTENT_SEPARATOR}\n本文第一段落\n\n本文第二段落\n{CONTENT_SEPARATOR}\n{{\"title\": \"エピソード1\"}}"
    metadata, content = OutputSanitizer.extract_content_and_metadata(text)
    assert "本文第一段落" in content
    assert metadata.get("title") == "エピソード1"


def test_output_sanitizer_format_validation_error():
    class SampleModel(BaseModel):
        name: str
        age: int = Field(gt=0)

    try:
        SampleModel(name="test", age=-5)
    except ValidationError as ve:
        formatted = OutputSanitizer.format_validation_error(ve)
        assert "age" in formatted
        assert isinstance(formatted, str)


def test_tone_perfector_enforce_tone():
    char = CharacterRegistry(
        name="アリス",
        first_person="私",
        second_person="あなた",
        suffix_style="〜わ。",
    )
    dialogue = "「僕はお前を許さない！」と彼女は叫んだ。"
    adjusted = TonePerfector.enforce_tone(dialogue, [char])
    assert isinstance(adjusted, str)
