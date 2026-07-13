from typing import List

from pydantic import BaseModel, Field


class NarrativeMetricScore(BaseModel):
    """
    シーンごとの単一指標のスコアと根拠
    """
    metric_name: str = Field(..., description="指標名 (例: tension, satisfaction, mystery)")
    score: int = Field(..., ge=0, le=100, description="0-100のスコア")
    reasoning: str = Field(..., description="そのスコアを付けた具体的な根拠と分析")

class NarrativeSceneEvaluation(BaseModel):
    """
    1つのシーンに対する複数指標の評価結果
    """
    scene_num: int = Field(..., description="評価対象のシーン番号")
    metrics: List[NarrativeMetricScore] = Field(..., description="各指標のスコアリスト")
