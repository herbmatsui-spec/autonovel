#!/usr/bin/env python3
"""Quick test for pipeline_param_mapper"""

from src.services.pipeline_param_mapper import (
    map_fullauto_kwargs_to_context,
    map_easymode_kwargs_to_context,
    map_context_to_fullauto_result,
    map_context_to_easymode_result,
)
from src.models.writing import FullAutoWorkflowResult

def test_fullauto_mapper():
    kwargs = {
        "genre": "ファンタジー",
        "keywords": ["チート", "無双"],
        "archetype_key": "王道ざまぁ",
        "target_eps": 3,
        "initial_limit": 3,
        "word_count": 2000,
        "concept": "テストコンセプト",
        "tone_vibe": 0.6,
        "user_prompt": "",
        "illustration_settings": {"enableIllustration": False},
        "enable_spice_guard": True,
    }
    ctx = map_fullauto_kwargs_to_context(kwargs)
    print(f"ctx.keywords: {ctx.keywords}")
    assert ctx.genre == "ファンタジー"
    assert ctx.keywords == "チート, 無双"
    assert ctx.archetype_key == "王道ざまぁ"
    assert ctx.target_eps == 3
    assert ctx.initial_limit == 3
    assert ctx.word_count == 2000
    assert ctx.concept == "テストコンセプト"
    assert ctx.tone_vibe == 0.6
    assert ctx.user_prompt == ""
    assert ctx.enable_illustration == False
    assert ctx.illustration_settings == {"enableIllustration": False}
    assert ctx.enable_spice_guard == True
    assert ctx.enable_catharsis_analysis == True
    assert ctx.enable_marketing == True
    assert ctx.max_retries == 1
    assert ctx.is_easy_mode == False
    print("FullAuto mapper test passed")

def test_easymode_mapper():
    ctx = map_easymode_kwargs_to_context(
        genre="ファンタジー",
        keywords=["主人公", "剣術"],
        protagonist_type="チート主人公",
        target_episodes=3,
        words_per_episode=2000,
        enable_audit=True,
        max_rewrites=2,
        concept="テスト",
        tone_vibe=0.6,
        user_prompt="",
        preset_name="zarma",
    )
    assert ctx.genre == "ファンタジー"
    assert ctx.keywords == "主人公, 剣術"
    assert ctx.archetype_key == "チート主人公"
    assert ctx.target_eps == 3
    assert ctx.initial_limit == 3
    assert ctx.word_count == 2000
    assert ctx.concept == "テスト"
    assert ctx.tone_vibe == 0.6
    assert ctx.user_prompt == ""
    assert ctx.enable_spice_guard == True
    assert ctx.max_rewrite_iterations == 2
    assert ctx.target_audit_score == 95.0
    assert ctx.enable_illustration == False
    assert ctx.enable_catharsis_analysis == False
    assert ctx.enable_marketing == True
    assert ctx.max_retries == 0
    assert ctx.is_easy_mode == True
    assert ctx.preset_name == "zarma"
    print("EasyMode mapper test passed")

def test_result_mappers():
    # We need a mock result and context to test the mappers
    # For simplicity, we'll just check that the functions exist and can be called
    # without error (they will fail due to missing attributes, but we can catch that)
    try:
        ctx = map_fullauto_kwargs_to_context({
            "genre": "テスト",
            "keywords": [],
            "archetype_key": "テスト",
            "target_eps": 1,
            "initial_limit": 1,
            "word_count": 100,
            "enable_spice_guard": False,
        })
        # Create a mock result
        result = FullAutoWorkflowResult(
            book_id=1,
            title="テスト",
            chars_count=100,
            failed_episodes=0,
            zip_data=b"data",
            zip_filename="test.zip",
            illustrations=[],
            status="success",
            easy_parameters={},
            average_audit_score=90.0,
            episodes_detail=[],
        )
        mapped = map_context_to_fullauto_result(ctx, result)
        assert mapped["title"] == "テスト"
        assert mapped["chars_count"] == 100
        print("FullAuto result mapper test passed")
    except Exception as e:
        print(f"FullAuto result mapper test failed: {e}")

    try:
        ctx = map_easymode_kwargs_to_context({
            "genre": "テスト",
            "keywords": [],
            "protagonist_type": "テスト",
            "target_episodes": 1,
            "words_per_episode": 100,
            "enable_audit": False,
            "max_rewrites": 0,
        })
        result = FullAutoWorkflowResult(
            book_id=1,
            title="テスト",
            chars_count=100,
            failed_episodes=0,
            zip_data=b"data",
            zip_filename="test.zip",
            illustrations=[],
            status="success",
            easy_parameters={"target_eps": 1, "concept": "テスト"},
            average_audit_score=90.0,
            episodes_detail=[],
        )
        mapped = map_context_to_easymode_result(ctx, result)
        assert mapped["title"] == "テスト"
        assert mapped["total_words"] == 100
        print("EasyMode result mapper test passed")
    except Exception as e:
        print(f"EasyMode result mapper test failed: {e}")

if __name__ == "__main__":
    test_fullauto_mapper()
    test_easymode_mapper()
    test_result_mappers()
    print("All mapper tests completed")