"""非同期章生成タスク。

Huey ワーカー上で実行される ``generate_chapter_task`` を提供する。
タスクは ``generate_with_llm`` を呼び出して生成結果を取得し、
DB 上の ``Task`` レコードへ結果を永続化する。

また、マルチエージェントオーケストレーション用の ``generate_chapter_orchestrated_task`` も提供する。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from src.backend import database
from src.backend.database.repository import BookRepository
from src.backend.observability.health import metrics
from src.backend.tasks.huey import huey

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    """新規 event loop を作成して coroutine を同期実行する。"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _generate(payload: dict[str, Any]) -> dict[str, Any]:
    """タスク本体。``generate_with_llm`` 遅延 import で循環参照を回避する。"""
    from src.backend.routers.easy_mode import generate_with_llm

    return await generate_with_llm(payload)


async def _generate_orchestrated(payload: dict[str, Any]) -> dict[str, Any]:
    """Orchestrator を使用したマルチエージェント生成タスク本体。"""
    from src.agents import Orchestrator, AgentName, AgentContext
    from src.agents.event_bus import EventBus
    from src.agents.planning import PlanningAgent
    from src.agents.plot import PlotAgent
    from src.agents.bible import BibleAgent
    from src.agents.context_builder_agent import ContextBuilderAgent
    from src.agents.writing import WritingAgent
    from src.agents.audit_agent import AuditAgent
    from src.agents.illustration_agent import IllustrationAgent
    from src.agents.marketing import MarketingAgent
    from src.services.llm.factory import get_llm_adapter
    from src.services.image_service import ImageService
    from src.backend.database.repository import BookRepository

    book_id = payload.get("book_id", 1)
    branch_id = payload.get("branch_id", 1)
    ep_num = payload.get("ep_num", 1)
    title = payload.get("title", "無題")
    synopsis = payload.get("synopsis", "")
    target_eps = payload.get("target_eps", 10)
    concept = payload.get("concept", "")
    genre = payload.get("genre", "fantasy")
    keywords = payload.get("keywords", "")
    target_word_count = payload.get("target_word_count", 3000)
    style_tag = payload.get("style_tag")

    # LLM アダプタ取得
    llm_config = payload.get("llm_config") or {}
    llm_adapter = get_llm_adapter(
        provider=llm_config.get("provider"),
        api_key=llm_config.get("api_key"),
        model_name=llm_config.get("model_name"),
        base_url=llm_config.get("base_url"),
    )

    # ImageService は遅延初期化
    image_service = ImageService()

    # DB セッションとリポジトリ
    session = database.SessionLocal()
    repo = BookRepository(session)

    # 相関ID生成（ログ追跡用）
    correlation_id = f"book_{book_id}_branch_{branch_id}_ep_{ep_num}"

    # EventBus 初期化（環境変数 USE_REDIS_EVENTS=true で Redis 使用）
    use_redis = os.environ.get("USE_REDIS_EVENTS", "false").lower() == "true"
    event_bus = EventBus(use_redis=use_redis)
    if use_redis:
        await event_bus.start_redis()

    try:
        # エージェントノード登録
        nodes = {
            AgentName.PLANNING: PlanningAgent(repo=repo, llm=llm_adapter).run,
            AgentName.PLOT: PlotAgent(repo=repo, llm=llm_adapter).run,
            AgentName.BIBLE: BibleAgent(repo=repo, llm=llm_adapter).run,
            AgentName.CONTEXT_BUILDER: ContextBuilderAgent(repo=repo, llm=llm_adapter).run,
            AgentName.WRITING: WritingAgent(repo=repo, llm=llm_adapter).run,
            AgentName.AUDIT: AuditAgent(repo=repo, llm=llm_adapter).run,
            AgentName.ILLUSTRATION: IllustrationAgent(
                image_service=image_service, repo=repo, llm=llm_adapter
            ).run,
            AgentName.MARKETING: MarketingAgent(repo=repo, llm=llm_adapter).run,
        }

        orchestrator = Orchestrator(nodes, event_bus=event_bus, correlation_id=correlation_id)
        ctx = AgentContext(
            book_id=book_id,
            branch_id=branch_id,
            ep_num=ep_num,
            artifacts={
                "title": title,
                "synopsis": synopsis,
                "target_eps": target_eps,
                "concept": concept,
                "genre": genre,
                "keywords": keywords,
                "target_word_count": target_word_count,
                "style_tag": style_tag,
                "repo": repo,
                "llm": llm_adapter,
            },
        )

        final_ctx = await orchestrator.run(ctx, AgentName.PLANNING)

        # 最終成果物を取得
        zip_data = final_ctx.artifacts.get("zip_data")
        zip_filename = final_ctx.artifacts.get("zip_filename")
        drafted_text = final_ctx.artifacts.get("drafted_text", "")

        return {
            "output": drafted_text,
            "zip_data": zip_data,
            "zip_filename": zip_filename,
            "artifacts": final_ctx.artifacts,
        }
    finally:
        session.close()
        if use_redis:
            await event_bus.stop_redis()


def _update_task_in_db(
    task_id: str,
    status: str,
    result_json: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """DB 上の Task レコードおよび作品/章データを安全に更新する (rollback 保証付き)。"""
    session = database.SessionLocal()
    try:
        repo = BookRepository(session)
        if status == "completed" and result_json is not None:
            repo.set_task_result(task_id, result_json)
            # 作品・章データの自動保存
            if payload:
                try:
                    res_dict = json.loads(result_json)
                    output_text = res_dict.get("output", "")
                    char_params = payload.get("character", {})
                    genre = (
                        char_params.get("genre", "ファンタジー (R15)")
                        if isinstance(char_params, dict)
                        else "ファンタジー (R15)"
                    )
                    repo.save_or_update_book_with_chapter(
                        book_id=1,
                        title=f"{char_params.get('name', '主人公')}の冒険譚"
                        if isinstance(char_params, dict) and char_params.get("name")
                        else "R15ファンタジー作品",
                        genre=genre,
                        chapter_text=output_text,
                        character_params=char_params if isinstance(char_params, dict) else None,
                    )
                except Exception as save_err:
                    logger.warning("Auto saving generated book failed: %s", save_err)
        else:
            repo.update_task_status(task_id, status)
    except Exception:
        session.rollback()
        logger.exception("DB update failed for task_id=%s status=%s", task_id, status)
    finally:
        session.close()


@huey.task()
def generate_chapter_task(payload: dict[str, Any]) -> dict[str, Any]:
    """非同期で小説の章を生成する Huey タスク（簡易モード）。

    ワーカー上で ``generate_with_llm`` を実行し、結果を DB に保存する。
    """
    logger.info("Starting generation task (easy): %s", payload)
    task_id = payload.get("task_id")

    try:
        result = _run_async(_generate(payload))
        metrics.increment("tasks_completed")
        logger.info("Generation task completed: task_id=%s", task_id)
        if task_id:
            _update_task_in_db(
                str(task_id),
                "completed",
                json.dumps(result, ensure_ascii=False),
                payload=payload,
            )
        return result
    except Exception as exc:
        logger.exception("Generation task failed: %s", exc)
        metrics.increment("tasks_failed")
        if task_id:
            _update_task_in_db(str(task_id), "failed")
        return {"error": str(exc), "text": "", "time": 0}


@huey.task()
def generate_chapter_orchestrated_task(payload: dict[str, Any]) -> dict[str, Any]:
    """非同期で小説の章を生成する Huey タスク（マルチエージェントオーケストレーション）。

    Orchestrator を使用して 8 エージェントを協調実行し、結果を DB に保存する。
    """
    logger.info("Starting generation task (orchestrated): %s", payload)
    task_id = payload.get("task_id")

    try:
        result = _run_async(_generate_orchestrated(payload))
        metrics.increment("tasks_completed")
        logger.info("Orchestrated generation task completed: task_id=%s", task_id)
        if task_id:
            _update_task_in_db(
                str(task_id),
                "completed",
                json.dumps(result, ensure_ascii=False),
                payload=payload,
            )
        return result
    except Exception as exc:
        logger.exception("Orchestrated generation task failed: %s", exc)
        metrics.increment("tasks_failed")
        if task_id:
            _update_task_in_db(str(task_id), "failed")
        return {"error": str(exc), "text": "", "time": 0}


__all__: list[str] = ["generate_chapter_task", "generate_chapter_orchestrated_task"]
