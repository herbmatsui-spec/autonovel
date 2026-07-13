from typing import Dict, Any, List, Optional
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ZamaaAuditResult(BaseModel):
    is_valid: bool
    score: int  # 0-100
    issues: List[str]
    suggestion: str

class ZamaaStressCatharsisValidator:
    """
    ざまぁ作品における「ストレス蓄積」と「カタルシス（解放）」の構造を検証するバリデータ。
    
    検証基準:
    1. ストレス蓄積相: 主人公が不当な扱いを受け、読者の怒りを煽っているか。
    2. トリガー: 解放への転換点（覚醒、正体露見、助っ人の登場など）が明確か。
    3. カタルシス相: 蓄積されたストレスに見合う十分な報復・快感があるか。
    4. ドミナンス: 最終的に主人公が完全な優位に立ち、状況を支配しているか。
    """

    def __init__(self, stress_threshold: int = 70, catharsis_threshold: int = 80):
        self.stress_threshold = stress_threshold
        self.catharsis_threshold = catharsis_threshold

    async def validate_plot_arc(self, plot_data: Dict[str, Any], engine_key: str) -> ZamaaAuditResult:
        if engine_key != "zamaa":
            return ZamaaAuditResult(is_valid=True, score=100, issues=[], suggestion="Not a Zamaa project, skipping specialized validation.")

        scenes = plot_data.get("scenes", [])
        if not scenes:
            return ZamaaAuditResult(is_valid=False, score=0, issues=["No scenes found in plot data."], suggestion="Please generate scenes first.")

        issues = []
        
        # 1. ストレス蓄積の確認 (前半部分)
        stress_detected = False
        early_scenes = scenes[:len(scenes)//2]
        for scene in early_scenes:
            # 簡易的なキーワード判定（実際にはLLMによる判定を想定し、ここでは構造的な整合性をチェック）
            action = str(scene.get("action", "")).lower()
            if any(word in action for word in ["humiliation", "unfair", "betrayal", "abuse", "軽視", "追放", "不当"]):
                stress_detected = True
                break
        
        if not stress_detected:
            issues.append("Stress accumulation phase is weak or missing. Readers may not feel the need for retribution.")

        # 2. カタルシスの確認 (後半部分)
        catharsis_detected = False
        late_scenes = scenes[len(scenes)//2:]
        for scene in late_scenes:
            action = str(scene.get("action", "")).lower()
            if any(word in action for word in ["retribution", "catharsis", "dominance", "regret", "ざまぁ", "報復", "絶望", "後悔"]):
                catharsis_detected = True
                break
        
        if not catharsis_detected:
            issues.append("Catharsis phase is missing. The tension is built up but never released.")

        # 3. 転換点 (Trigger) の確認
        has_trigger = False
        for scene in scenes:
            action = str(scene.get("action", "")).lower()
            if any(word in action for word in ["trigger", "awakening", "reveal", "覚醒", "露見", "転換"]):
                has_trigger = True
                break
        
        if not has_trigger:
            issues.append("Clear trigger for retribution is missing. The transition from stress to catharsis is too abrupt or vague.")

        # スコアリング
        score = 100 - (len(issues) * 25)
        score = max(0, score)
        
        is_valid = len(issues) == 0 or score >= 60
        
        suggestion = "Ensure a clear 4-act structure: Humiliation -> Trigger -> Retribution -> Dominance."
        if not stress_detected:
            suggestion = "Increase the 'unfairness' in the first half to amplify the eventual catharsis."
        elif not catharsis_detected:
            suggestion = "Make the retribution more explicit and satisfying."

        return ZamaaAuditResult(is_valid=is_valid, score=score, issues=issues, suggestion=suggestion)
