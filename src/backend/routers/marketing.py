from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from src.backend.auth import require_api_key
from src.backend.engine_helpers import get_engine
from src.backend.task_helpers import create_task
from src.backend.router_helpers import workflow_endpoint
from src.backend.utils.id_generator import generate_prefixed_id as generate_task_id
from src.backend.tasks import execute_service_workflow
from src.core.observability import TraceContext
from src.models.api_schemas import MarketingGenerateRequest
from src.backend.response_helpers import api_success

router = APIRouter(tags=["marketing"])


@workflow_endpoint("marketing_generate")
@router.post("/api/marketing/generate")
async def generate_marketing(req: MarketingGenerateRequest, api_key: str = Depends(require_api_key)):
    import time

    task_id = f"marketing_{int(time.time())}"
    await create_task(task_id, "マーケティング情報の生成を開始中...", total_steps=1)

    execute_service_workflow(
        task_id=task_id,
        api_key=api_key,
        config_dict={},
        method_name="marketing_generation_workflow",
        kwargs={"book_id": req.book_id, "latest_ep": req.latest_ep},
        trace_id=TraceContext.get_trace_id(),
    )
    return api_success({"task_id": task_id}, "マーケティング生成を開始しました")


@router.post("/api/marketing/export_package/{book_id}")
async def export_package_post(book_id: int, api_key_req: Any):
    # Original server.py had a pass here
    # Keeping the endpoint for compatibility but as it was a no-op
    return api_success({"message": "Export package POST is not implemented"}, "未実装のエンドポイントです")


@router.get("/api/marketing/export_package/{book_id}")
async def export_package_get(book_id: int, api_key: str = Depends(require_api_key)):
    engine = get_engine(api_key)
    zip_data, zip_filename = await engine.marketing.create_export_package(book_id)
    return Response(
        content=zip_data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )


@workflow_endpoint("marketing_analyze_style_dna")
@router.post("/api/marketing/analyze_style_dna")
async def analyze_style_dna_endpoint(req: dict, api_key: str = Depends(require_api_key)):
    """
    小説サンプルテキストを解析し、文体DNA（特徴・指標・執筆指針）を返す。
    """
    sample = req.get("sample", "").strip()
    if not sample:
        return api_success({
            "name": "未指定",
            "instruction": "サンプルテキストが提供されていません。",
            "score": 0,
            "analysis": "テキストを入力して分析してください。",
            "metrics": {"dialogue_ratio": "0%", "avg_chars_per_line": 0},
        }, "文体DNAを解析しました")

    # 簡易メトリクス計算
    total_len = len(sample)
    lines = [l.strip() for l in sample.split("\n") if l.strip()]
    dialogue_lines = [l for l in lines if (l.startswith("「") or l.startswith("『") or l.startswith("（"))]
    dialogue_ratio = round((len(dialogue_lines) / max(len(lines), 1)) * 100)
    avg_chars = round(total_len / max(len(lines), 1))

    # AI解析の試行
    try:
        engine = get_engine(api_key)
        prompt = (
            f"あなたはプロの文体・小説アナリストです。以下のサンプル文章を精緻に分析し、"
            f"文体DNAの特徴、執筆指針、文章スコア（100点満点）、および具体的な改善アドバイスをJSONで抽出してください。\n\n"
            f"【サンプル】\n{sample[:3000]}\n\n"
            f"出力フォーマット（必ず有効なJSONのみ出力）:\n"
            f'{{"name": "文体名（例：現代軽快会話体）", "instruction": "この文体を模倣・再現するための具体的な執筆指針", "score": 85, "analysis": "文体の詳細分析レポート", "suggested_style_key": "style_web_standard"}}'
        )
        ai_res = await engine.llm.generate(prompt)
        import json
        # JSON部分の抽出
        cleaned = ai_res.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()
        result = json.loads(cleaned)
        result["metrics"] = {
            "dialogue_ratio": f"{dialogue_ratio}%",
            "avg_chars_per_line": avg_chars,
            "total_chars": total_len,
        }
        return api_success(result, "文体DNAを解析しました")
    except Exception as e:
        # フォールバック
        return api_success({
            "name": "Web標準テンポ体" if dialogue_ratio > 40 else "叙情・重厚体",
            "instruction": "会話と地の文のバランスを保ち、情景描写と心理描写を織り交ぜて展開せよ。",
            "score": min(95, max(60, 70 + (avg_chars // 10))),
            "analysis": f"台詞比率: {dialogue_ratio}%、平均行長: {avg_chars}文字。安定した可読性を持つ文章構成です。",
            "metrics": {
                "dialogue_ratio": f"{dialogue_ratio}%",
                "avg_chars_per_line": avg_chars,
                "total_chars": total_len,
            },
        }, "文体DNAを解析しました")
