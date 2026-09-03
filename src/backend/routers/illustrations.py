from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.dependencies import get_illustration_workflow
from src.models.illustration import (
    IllustrationModel,
    IllustrationRequest,
    IllustrationType,
    SafetyLevel,
)

router = APIRouter()


class _ReporterShim:
    """StatusReporter Protocol の軽量実装 (API 用ダミー)。"""

    def __init__(self, id: str):
        self.id = id

    def report(self, message: str, level: str = "info") -> None:
        pass

    def update_progress(
        self, current: int, total: int, message: str = "", sub_message: str = ""
    ) -> None:
        pass

    @property
    def state(self):
        class _S:
            def should_stop(self) -> bool:
                return False

        return _S()


@router.post("/generate")
async def generate_illustration(
    request: dict[str, Any], workflow=Depends(get_illustration_workflow)
):
    """単一の挿絵を生成する"""
    try:
        # リクエストのパース
        ill_request = IllustrationRequest(
            book_id=request["book_id"],
            illustration_type=IllustrationType(request["illustration_type"]),
            episode_number=request.get("episode_number"),
            model=IllustrationModel(request.get("model", "auto")),
            safety_level=SafetyLevel.R15_CONTENT
            if request.get("enable_r15")
            else SafetyLevel.BLOCK_SOME,
        )

        # 簡易的なレポート (Protocol なのでダミー化)
        _ = _ReporterShim(id="api_gen")

        # Agentを直接呼んで生成
        res = await workflow.illustration_agent.run(request=ill_request)

        if res["status"] == "error":
            raise HTTPException(status_code=500, detail=res["message"])

        return res["result"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/yonkoma")
async def generate_yonkoma(
    request: dict[str, Any], workflow=Depends(get_illustration_workflow)
):
    """1話分の流れを 6 コマ (デフォルト) で要約した漫画プロンプト+画像を生成する。

    Request:
        {
            "book_id": int,
            "episode_text": str,        # 1話分の本文
            "panels": int = 6,          # 3〜6 (省略時 6)
            "model": str = "auto",      # fast/quality/ultra/auto
            "enable_r15": bool = false,
            "book_context": dict = {}   # title/genre/character_name 等
        }

    Response: IllustrationResult 互換の dict
    """
    try:
        book_id = int(request["book_id"])
        episode_text = str(request.get("episode_text") or "")
        panels = max(3, min(int(request.get("panels") or 6), 6))
        model = request.get("model", "auto")
        enable_r15 = bool(request.get("enable_r15"))
        book_context = dict(request.get("book_context") or {})

        ill_request = IllustrationRequest(
            book_id=book_id,
            illustration_type=IllustrationType.YONKOMA,
            episode_number=request.get("episode_number"),
            scene_text=episode_text,
            book_context=book_context,
            model=IllustrationModel(model),
            safety_level=(
                SafetyLevel.R15_CONTENT if enable_r15 else SafetyLevel.BLOCK_SOME
            ),
            panels=panels,
        )

        # オフ設定でも、UI がプレビュー目的で叩く可能性があるため常にプロンプトは返す。
        # 画像生成は settings.yonkoma_enabled=False ならスキップする (呼び出し側で分岐)。
        yonkoma_enabled = bool(request.get("yonkoma_enabled", True))
        if not yonkoma_enabled:
            res = await workflow.illustration_agent.generate_prompt_only(request=ill_request)
        else:
            res = await workflow.illustration_agent.generate_episode_yonkoma(
                episode_text=episode_text, request=ill_request, panels=panels
            )
            # 既存 run() の戻り値形式に揃える
            res = {"status": "success", "result": res, "prompt": res.prompt}

        if res.get("status") == "error":
            raise HTTPException(status_code=500, detail=res.get("message"))

        return res["result"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch")
async def batch_generate_illustrations(
    params: dict[str, Any], workflow=Depends(get_illustration_workflow)
):
    """バッチで挿絵を生成する (Huey タスクキューに投入)。

    レスポンスは即座に ``{task_id, status: "queued"}`` を返し、
    進捗・結果は ``GET /api/illustrations/status/{task_id}`` で取得する。
    """
    import uuid

    from src.backend.tasks.illustration_tasks import illustrate_batch_task

    try:
        book_id = params["book_id"]
        settings = params.get("settings", {})
        task_id = f"illust_{uuid.uuid4().hex[:8]}"

        # タスクをキューに投入 (immediate=False のためワーカー側で実行)
        illustrate_batch_task(book_id=book_id, settings=settings)

        return {"task_id": task_id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}")
async def get_illustration_status(task_id: str):
    """Huey タスクのステータス・結果を取得する。"""
    from src.backend import database
    from src.backend.database.repository import BookRepository

    session = database.SessionLocal()
    try:
        repo = BookRepository(session)
        task = repo.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"task {task_id} not found")
        result = None
        if task.status == "completed" and task.result:
            try:
                import json as _json

                result = _json.loads(task.result)
            except Exception:  # noqa: BLE001
                result = task.result
        return {
            "task_id": task_id,
            "status": task.status,
            "result": result,
        }
    finally:
        session.close()
