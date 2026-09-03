from __future__ import annotations

from typing import Any

from src.services.pipeline_base import WorkflowContext
from src.models.writing import FullAutoWorkflowResult


def map_fullauto_kwargs_to_context(kwargs: dict[str, Any]) -> WorkflowContext:
    """FullAutoWorkflow の kwargs を WorkflowContext に変換"""
    return WorkflowContext(
        genre=kwargs["genre"],
        keywords=", ".join(kwargs["keywords"])
        if isinstance(kwargs["keywords"], list)
        else kwargs["keywords"],
        archetype_key=kwargs["archetype_key"],
        target_eps=kwargs["target_eps"],
        initial_limit=kwargs["initial_limit"],
        word_count=kwargs["word_count"],
        concept=kwargs.get("concept", ""),
        tone_vibe=kwargs.get("tone_vibe", 0.6),
        user_prompt=kwargs.get("user_prompt", ""),
        enable_illustration=bool(
            kwargs.get("illustration_settings", {}).get("enableIllustration", False)
        ),
        illustration_settings=kwargs.get("illustration_settings", {}),
        enable_spice_guard=kwargs.get("enable_spice_guard", False),
        enable_catharsis_analysis=True,
        enable_marketing=True,
        max_retries=1,
        is_easy_mode=False,
    )


def map_easymode_kwargs_to_context(
    genre: str,
    keywords: list[str] | None,
    protagonist_type: str,
    target_episodes: int,
    words_per_episode: int,
    enable_audit: bool,
    max_rewrites: int,
    **kwargs: Any,
) -> WorkflowContext:
    """EasyModeWorkflow の kwargs を WorkflowContext に変換"""
    return WorkflowContext(
        genre=genre,
        keywords=", ".join(keywords) if keywords else "",
        archetype_key=protagonist_type,
        target_eps=target_episodes,
        initial_limit=3,
        word_count=words_per_episode,
        concept=kwargs.get("concept", ""),
        tone_vibe=kwargs.get("tone_vibe", 0.6),
        user_prompt=kwargs.get("user_prompt", ""),
        enable_spice_guard=enable_audit,
        max_rewrite_iterations=max_rewrites,
        target_audit_score=95.0,
        enable_illustration=False,
        enable_catharsis_analysis=False,
        enable_marketing=True,
        max_retries=0,
        is_easy_mode=True,
        preset_name=kwargs.get("preset_name", ""),
    )


def map_context_to_fullauto_result(
    ctx: WorkflowContext, result: FullAutoWorkflowResult
) -> dict[str, Any]:
    """WorkflowContext と FullAutoWorkflowResult を既存インターフェース互換の dict に変換"""
    return {
        "book_id": result.book_id,
        "title": result.title,
        "chars_count": result.chars_count,
        "failed_episodes": result.failed_episodes,
        "zip_data": result.zip_data,
        "zip_filename": result.zip_filename,
        "illustrations": result.illustrations,
        "status": result.status,
        "easy_parameters": result.easy_parameters,
        "average_audit_score": result.average_audit_score,
        "episodes_detail": result.episodes_detail,
    }


def map_context_to_easymode_result(
    ctx: WorkflowContext, result: FullAutoWorkflowResult
) -> dict[str, Any]:
    """WorkflowContext と FullAutoWorkflowResult を EasyMode 互換の dict に変換"""
    episodes_list: list[dict[str, Any]] = []
    for ep in result.episodes_detail:
        episodes_list.append(
            {
                "episode_num": ep.get("episode_num", 0),
                "title": ep.get("title", f"第{ep.get('episode_num', 0)}話"),
                "word_count": ep.get("word_count", 0),
                "audit_score": ep.get("audit_score", 0.0),
                "audit_passed": ep.get("audit_passed", False),
                "rewrite_count": ep.get("rewrite_count", 0),
                "needs_human_review": ep.get("needs_human_review", False),
            }
        )

    return {
        "title": result.title,
        "concept": result.easy_parameters.get("concept", "") if result.easy_parameters else "",
        "total_episodes": result.easy_parameters.get("target_eps", ctx.target_eps)
        if result.easy_parameters
        else ctx.target_eps,
        "total_words": result.chars_count,
        "average_audit_score": result.average_audit_score,
        "genre": ctx.genre,
        "episodes": episodes_list,
        "status": result.status,
    }
