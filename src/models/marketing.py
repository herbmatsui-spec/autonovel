from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel, Field, model_validator

from src.models.base import MODEL_CONFIG_DEFAULTS


class TitleProposal(BaseModel):
    """戦略的タイトル案とその分析"""
    title:            str   = Field(..., description="提案タイトル（長文あらすじ兼用）")
    viral_score:      int   = Field(default=80, description="想定クリック率/拡散性 (0-100)")
    aura_type:        str   = Field(default="Standard", description="このタイトルから漂うオーラのタイプ（例: 覇道, 悠久, 絶望, 渇望）")
    clickbait_level:  int   = Field(default=3, description="引きの強さ (1-5)")
    reasoning:        str   = Field(default="", description="このタイトルがランキング1位を獲れる戦略的理由")

    model_config = MODEL_CONFIG_DEFAULTS

class TitleProposalList(BaseModel):
    """タイトル案のリスト"""
    titles: List[TitleProposal] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def unwrap_titles_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "results", "proposals"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break

            # もしAIが単純な文字列リストを返してしまった場合のパッチ
            if "titles" in data and isinstance(data["titles"], list):
                healed_titles = []
                for item in data["titles"]:
                    if isinstance(item, str):
                        healed_titles.append({
                            "title": item,
                            "viral_score": 85,
                            "aura_type": "覇道",
                            "clickbait_level": 4,
                            "reasoning": "トレンドに合致した引きの強い構成"
                        })
                    else:
                        healed_titles.append(item)
                data["titles"] = healed_titles
        return data

    model_config = MODEL_CONFIG_DEFAULTS
