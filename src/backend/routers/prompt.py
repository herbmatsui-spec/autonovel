from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import random

from src.schemas.axis import PromptContract, Axis, AxisType
from src.services.prompt_compiler import compile_prompt
from src.backend.auth import require_api_key

router = APIRouter(prefix="/api/prompt", tags=["prompt"])


# Preset random values per axis (extend as needed)
RANDOM_PRESETS: Dict[str, List[str]] = {
    "theme": ["冒険", "恋愛", "謎解き", "復讐", "成長", "日常", "SF", "ファンタジー"],
    "genre": ["ファンタジー", "SF", "ミステリー", "ラブコメ", "ホラー", "歴史", "スポーツ", "学園"],
    "worldview": ["現代日本", "中世ヨーロッパ風", "近未来都市", "異世界", "蒸気機関", "サイバーパンク", "ポストアポカリプス"],
    "audience": ["児童", "少年", "青年", "成人", "全年齢"],
    "era": ["古代", "中世", "近世", "現代", "近未来", "遠未来"],
    "ending_style": ["ハッピーエンド", "バッドエンド", "開放的", "悲劇的", "どんでん返し", "輪廻"],
    "narrator": ["一人称", "三人称", "書簡体", "日記体", "語り手不在"],
    "characters": ["主人公単独", "主人公＋相棒", "グループ", "敵対関係", "三角関係"],
    "universal_input": ["なし", "既存テキスト", "画像素材", "ニュース記事"],
    "supplemental_note": ["なし", "伏線重視", "会話多め", "描写重視", "テンポ速め"],
}

class PromptCompileRequest(BaseModel):
    output_mode: str
    axes: Dict[str, Any]  # key: AxisType, value: {value, locked, default}


class PromptCompileResponse(BaseModel):
    compiled: str


@router.post("/compile", response_model=PromptCompileResponse, dependencies=[Depends(require_api_key)])
async def compile_prompt_endpoint(req: PromptCompileRequest):
    # Convert request dict to PromptContract
    axes_dict = {}
    for k, v in req.axes.items():
        try:
            axis_type = AxisType(k)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown axis: {k}")
        axes_dict[axis_type] = Axis(
            axis_type=axis_type,
            value=v.get("value"),
            locked=v.get("locked", False),
            default=v.get("default"),
        )
    contract = PromptContract(output_mode=req.output_mode, axes=axes_dict)
    try:
        compiled = compile_prompt(contract)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template rendering failed: {e}")
    return PromptCompileResponse(compiled=compiled)


@router.get("/randomize/{axis}", dependencies=[Depends(require_api_key)])
async def randomize_axis(axis: str):
    if axis not in RANDOM_PRESETS:
        raise HTTPException(status_code=400, detail=f"No random preset for axis: {axis}")
    value = random.choice(RANDOM_PRESETS[axis])
    return {"axis": axis, "value": value}