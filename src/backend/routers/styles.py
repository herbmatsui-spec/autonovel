"""
src/backend/routers/styles.py - 文体管理・カスタム文体・文体RAG・プリセットAPI
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException

from src.backend.auth import require_api_key
from src.backend.database import UnitOfWork
from src.backend.engine_helpers import get_engine
from src.core.container import AppContainer
from config.styles import (
    STYLE_DEFINITIONS,
    FORBIDDEN_WORD_REPLACEMENTS,
    FORBIDDEN_SUMMARY_PATTERNS,
)

router = APIRouter(prefix="/api/styles", tags=["styles"])


# ==============================================================================
# 1. カスタム文体 (Custom Styles)
# ==============================================================================
@router.get("/custom")
async def get_custom_styles():
    """保存されたカスタム文体の一覧を取得する"""
    async with UnitOfWork(AppContainer.db()) as uow:
        styles = await uow.misc.get_all_custom_styles()
    return [
        {
            "id": s.id if hasattr(s, "id") else s.get("id"),
            "name": s.name if hasattr(s, "name") else s.get("name"),
            "instruction": s.instruction if hasattr(s, "instruction") else s.get("instruction"),
            "score": s.score if hasattr(s, "score") else s.get("score", 80),
            "analysis": s.analysis if hasattr(s, "analysis") else s.get("analysis", ""),
            "created_at": str(s.created_at) if hasattr(s, "created_at") else str(s.get("created_at", "")),
        }
        for s in styles
    ]


@router.post("/custom")
async def save_custom_style(req: Dict[str, Any]):
    """分析結果や手動入力からカスタム文体を保存・更新する"""
    name = req.get("name", "").strip()
    instruction = req.get("instruction", "").strip()
    score = int(req.get("score", 80))
    analysis = req.get("analysis", "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="文体名を入力してください。")
    if not instruction:
        raise HTTPException(status_code=400, detail="執筆指針を入力してください。")

    async with UnitOfWork(AppContainer.db()) as uow:
        await uow.misc.save_custom_style(
            name=name, instruction=instruction, score=score, analysis=analysis
        )
    return {"status": "ok", "message": f"カスタム文体「{name}」を保存しました。"}


@router.delete("/custom/{style_id}")
async def delete_custom_style(style_id: int):
    """指定IDのカスタム文体を削除する"""
    async with UnitOfWork(AppContainer.db()) as uow:
        await uow.misc.delete_custom_style(style_id)
    return {"status": "ok", "message": "カスタム文体を削除しました。"}


# ==============================================================================
# 2. 文体RAG断片 (Style Fragments)
# ==============================================================================
@router.get("/fragments")
async def get_style_fragments(tag: Optional[str] = None):
    """登録済みの文体サンプル断片の一覧を取得する"""
    async with UnitOfWork(AppContainer.db()) as uow:
        fragments = await uow.misc.get_all_style_fragments(tag=tag)
    return [
        {
            "id": f.id if hasattr(f, "id") else f.get("id"),
            "tag": f.tag if hasattr(f, "tag") else f.get("tag"),
            "content": f.content if hasattr(f, "content") else f.get("content"),
            "origin": f.origin if hasattr(f, "origin") else f.get("origin", "Master"),
            "created_at": str(f.created_at) if hasattr(f, "created_at") else str(f.get("created_at", "")),
        }
        for f in fragments
    ]


@router.post("/fragments")
async def add_style_fragment(req: Dict[str, Any], api_key: str = Depends(require_api_key)):
    """文体サンプル断片をRAGに登録する（Embedding自動生成）"""
    tag = req.get("tag", "General").strip()
    content = req.get("content", "").strip()
    origin = req.get("origin", "UserMasterpiece").strip()

    if not content:
        raise HTTPException(status_code=400, detail="サンプルテキストを入力してください。")

    engine = get_engine(api_key)
    success = False
    if hasattr(engine, "style_rag") and engine.style_rag:
        success = await engine.style_rag.add_master_fragment(tag=tag, content=content, origin=origin)
    
    if not success:
        # フォールバック: ダミーEmbeddingでDB登録
        async with UnitOfWork(AppContainer.db()) as uow:
            await uow.misc.add_style_fragment(
                tag=tag, content=content, embedding=[0.0] * 768, origin=origin
            )

    return {"status": "ok", "message": "文体サンプル断片をRAGに登録しました。"}


@router.delete("/fragments/{fragment_id}")
async def delete_style_fragment(fragment_id: int):
    """指定IDの文体サンプル断片を削除する"""
    async with UnitOfWork(AppContainer.db()) as uow:
        await uow.misc.delete_style_fragment(fragment_id)
    return {"status": "ok", "message": "文体サンプル断片を削除しました。"}


# ==============================================================================
# 3. プリセット文体カタログ & ルールセット (Presets Catalog)
# ==============================================================================
@router.get("/presets")
async def get_style_presets():
    """
    組み込みの全文体プリセットおよび執筆ルールセット・禁止語置換定義を返す。
    """
    return {
        "styles": STYLE_DEFINITIONS,
        "forbidden_word_replacements": FORBIDDEN_WORD_REPLACEMENTS,
        "forbidden_summary_patterns": FORBIDDEN_SUMMARY_PATTERNS,
    }
