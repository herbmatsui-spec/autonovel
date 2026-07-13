from __future__ import annotations

# [Update: 2026-05-15 17:29 - Force Reload]
from typing import Any, Dict, List, Literal, Optional

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

from src.models.base import MODEL_CONFIG_DEFAULTS, extract_int


class PromptPatch(BaseModel):
    """プロンプトへの具体的修正パッチ"""
    target_prompt: str = Field(..., description="修正対象のプロンプト名 (e.g. 'writing_director', 'plot_expansion')")
    patch_content: str = Field(..., description="追加・修正すべき具体的なプロンプトテキスト")
    reasoning:     str = Field(..., description="このパッチが必要な理由・分析結果")

    model_config = MODEL_CONFIG_DEFAULTS

class GapAnalysisReport(BaseModel):
    """プロットと本文の乖離分析レポート"""
    habits:               str             = Field(default="", description="AIのサボり癖パターンの分析")
    style_gap:            str             = Field(default="", description="文体DNAの乖離レポート")
    config_patch:         Dict[str, Any]  = Field(default_factory=dict, description="config.pyへの修正案")
    prompt_patches:       List[PromptPatch] = Field(default_factory=list, description="プロンプトへの具体的修正パッチのリスト")
    refactor_instruction: str             = Field(..., description="コーディングAIへのエンジン改造指示", validation_alias=AliasChoices("refactor_instruction", "coding_ai_instruction", "refactor_instructions", "instructions"))
    scores:               Dict[str, int]  = Field(default_factory=dict, description="各種スコア")
    style_radar:          Dict[str, Any]  = Field(default_factory=dict, description="文体レーダー解析データ")
    persona_reviews:      List[Dict[str, Any]] = Field(default_factory=list, description="ペルソナ監査結果")

    @model_validator(mode="before")
    @classmethod
    def unwrap_gap_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "report", "result"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break

            # 数値を含む可能性のあるスコア辞書の正規化
            if "scores" in data and isinstance(data["scores"], dict):
                for k, v in data["scores"].items():
                    if isinstance(v, str):
                        data["scores"][k] = extract_int(v)
        return data

    model_config = MODEL_CONFIG_DEFAULTS

class DogfeedingReport(BaseModel):
    """エンジンの自己解析・自己進化レポート"""
    critique_report:       str             = Field(default="", description="AIの執筆上の手癖や指示無視、企画との乖離の分析")
    habits:                str             = Field(default="", description="AIのサボり癖パターンの具体的分析")
    bias_direction:        str             = Field(default="", description="現在の作風がどの方向に振れすぎているか（例: シリアスすぎ、描写が淡白すぎ等）")
    phenomenon_logic_map:  List[Dict[str, str]] = Field(default_factory=list, description="現象（症状）と原因（ロジック）の対応マップ。{'symptom': '...', 'cause_logic': '...', 'patch_target': '...'} ")
    prompt_patches:        List[PromptPatch] = Field(default_factory=list, description="プロンプトへの具体的修正パッチのリスト")
    prompt_patch:          str             = Field(default="", description="[Legacy] 次回の執筆プロンプトに追加すべき修正指示")
    coding_ai_instruction: str             = Field(default="", description="[Legacy] コーディングAIへのエンジン改造指示", validation_alias=AliasChoices("coding_ai_instruction", "refactor_instruction"))
    engine_code_patch:     str             = Field(default="", description="コアエンジンのロジック修正案（状態管理、整合性チェック等）")
    narrative_config_patch: str             = Field(default="", description="作品ドメイン固有の修正案（世界観設定、プロンプト定義、因果応報ロジック等）")
    scores:                Dict[str, int]  = Field(default_factory=dict, description="全体的な品質スコア")
    genre_profile_scores:  Dict[str, float] = Field(default_factory=dict, description="ジャンル別・多次元スコアリング（0.0-1.0）")
    taboo_list:            List[str]       = Field(default_factory=list, description="今後禁止すべき表現・設定のリスト")
    style_radar:           Dict[str, Any]  = Field(default_factory=dict, description="文体レーダー解析データ")
    persona_reviews:       List[Dict[str, Any]] = Field(default_factory=list, description="ペルソナ監査結果")
    patch_validation:      Dict[str, Any]  = Field(default_factory=dict, description="パッチの検証結果（ABテスト結果含む）")
    improvement_milestones: List[str]       = Field(default_factory=list, description="中長期的なエンジン進化のロードマップ")

    @model_validator(mode="before")
    @classmethod
    def unwrap_report_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "report", "result"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break

            # 数値を含む可能性のあるスコア辞書の正規化
            if "scores" in data and isinstance(data["scores"], dict):
                for k, v in data["scores"].items():
                    if isinstance(v, str):
                        data["scores"][k] = extract_int(v)
        return data

    model_config = MODEL_CONFIG_DEFAULTS

class ProducerPlanCandidate(BaseModel):
    plan_name: str = Field(..., description="プランの名前")
    plan_type: Literal["Trope", "Hybrid", "Anti-Trope"] = Field(..., description="プランの種類")
    refined_keywords: str = Field(default="", description="提案された覇権キーワード")
    refined_concept: str = Field(default="", description="ブラッシュアップされたコンセプト")
    refined_mc_suggestion: str = Field(default="", description="読者に刺さる主人公像の提案")
    refined_villain_suggestion: str = Field(default="", description="ヘイトを高める敵対者像の提案")
    recommended_tropes: List[str] = Field(default_factory=list, description="推奨トロープのリスト")
    anti_tropes: List[str] = Field(default_factory=list, description="アンチトロープ・逆張りの要素リスト")
    hybrid_idea: str = Field(default="", description="異ジャンルハイブリッドのアイデア")

    model_config = MODEL_CONFIG_DEFAULTS

class HegemonyAuditResult(BaseModel):
    is_consistent:       bool      = Field(default=True, description="整合性チェック結果")
    conflict_report:     str       = Field(default="", description="矛盾点の指摘内容")
    refined_keywords:    str       = Field(default="", description="[Legacy] 提案された覇権キーワード")
    refined_concept:     str       = Field(default="", description="[Legacy] ブラッシュアップされたコンセプト")
    refined_mc_suggestion: str     = Field(default="", description="[Legacy] 読者に刺さる主人公像の提案")
    refined_villain_suggestion: str = Field(default="", description="[Legacy] ヘイトを高める敵対者像の提案")
    recommended_tropes:  List[str] = Field(default_factory=list, description="[Legacy] 推奨トロープのリスト")
    candidates:          List[ProducerPlanCandidate] = Field(default_factory=list, description="A/B/Cの3パターンの提案")

    @model_validator(mode="before")
    @classmethod
    def unwrap_audit_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "audit", "result"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break
        return data

    model_config = MODEL_CONFIG_DEFAULTS

class LogicalAuditResult(BaseModel):
    is_consistent:    bool                    = Field(default=True, description="過去の事実と矛盾がないか", validation_alias=AliasChoices("is_consistent", "consistent", "isConsistent", "consistency"))
    conflict_points:  List[str]               = Field(default_factory=list)
    severity:         Literal["Minor", "Major", "Critical"] = Field(default="Minor")
    audit_type:       Literal["Full", "Lightweight"] = Field(default="Full", validation_alias=AliasChoices("audit_type", "auditType", "audit_mode", "mode", "type"))
    rewrite_suggestion: str                   = Field(default="")

    @model_validator(mode="before")
    @classmethod
    def unwrap_audit_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "audit", "result"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break

            # Boolean/Literal fields fallback
            if "is_consistent" not in data and not any(a in data for a in ["consistent", "isConsistent", "consistency"]):
                data["is_consistent"] = True
            if "audit_type" not in data and not any(a in data for a in ["auditType", "audit_mode", "mode", "type"]):
                data["audit_type"] = "Full"
        return data

    @field_validator("audit_type", mode="before")
    @classmethod
    def coerce_audit_type(cls, v: Any) -> str:
        if not v: return "Full"
        s = str(v).lower()
        if any(x in s for x in ["light", "軽量", "簡易", "quick", "fast"]):
            return "Lightweight"
        return "Full"

    model_config = MODEL_CONFIG_DEFAULTS

class HegemonyOracleResult(BaseModel):
    """未来予測オーラ診断の結果モデル"""
    hegemony_score:    int            = Field(default=0, description="覇権スコア (0-100)")
    metrics:           Dict[str, int] = Field(default_factory=dict, description="詳細メトリクス (retention, catharsis, viral)")
    aura_color:        str            = Field(default="#38bdf8", description="この作品が放つオーラの色 (Hex形式)")
    aura_type:         str            = Field(default="通常", description="オーラの属性タイプ")
    recommended_spice: str            = Field(default="", description="推奨スパイス")
    improvement_to_95: str            = Field(default="", description="95点超えへの具体的改善案")
    future_review:     str            = Field(default="", description="未来の熱狂的読者レビュー")

    @model_validator(mode="before")
    @classmethod
    def unwrap_oracle_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "oracle", "result"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break

            # 数値の正規化
            if "metrics" in data and isinstance(data["metrics"], dict):
                for k, v in data["metrics"].items():
                    if isinstance(v, str):
                        data["metrics"][k] = extract_int(v)
            if isinstance(data.get("hegemony_score"), str):
                data["hegemony_score"] = extract_int(data["hegemony_score"])
        return data

    model_config = MODEL_CONFIG_DEFAULTS

class GlobalLogicRepairResult(BaseModel):
    """企画段階の矛盾を一括修正するためのモデル"""
    synopsis:         str             = Field(..., description="修正されたあらすじ")
    world_rules:      Optional[Dict[str, Any]] = Field(default=None, description="修正された世界設定（変更がある場合のみ）")
    mc_profile:       Optional[Dict[str, Any]] = Field(default=None, description="修正された主人公プロフィール（変更がある場合のみ）")
    repair_summary:   str             = Field(..., description="どのような矛盾をどう修正したかの要約")

    model_config = MODEL_CONFIG_DEFAULTS


class EasyModeInferenceResult(BaseModel):
    """かんたんモードのワンショットプロンプトから推論された設定結果"""
    engine_key: Literal["comfort", "conflict", "enigma"] = Field(..., description="最適な感情エンジン")
    genre_key: str = Field(..., description="最適な世界観ジャンル（例：追放ざまぁファンタジー, 現代ダンジョン配信, 悪役令嬢知略戦, 異世界スローライフ 等、ユーザーの入力に最も近いもの）")
    mc_concept: str = Field(..., description="読者に刺さる主人公像と初期設定案")
    title_idea: str = Field(..., description="最もクリック率が高くなりそうな戦略的タイトル案")
    core_idea: str = Field(..., description="物語のコアコンセプト（100〜200文字程度）")

    @model_validator(mode="before")
    @classmethod
    def unwrap_inference_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "result"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break
        return data

    model_config = MODEL_CONFIG_DEFAULTS


class ImmersionScore(BaseModel):
    """感情没入スコア - 読者がどれだけ物語に没入できているかを定量化"""
    pov_stability: float = Field(default=0.0, ge=0.0, le=1.0, description="視点安定性 (0.0-1.0)")
    empathy_gap: float = Field(default=0.0, ge=0.0, le=1.0, description="共感ギャップ (0.0-1.0, 低い方が良い)")
    curiosity_hook_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="次への期待感・フック率 (0.0-1.0)")
    sensory_density: float = Field(default=0.0, ge=0.0, le=1.0, description="五感描写の密度 (0.0-1.0)")
    total_immersion_score: float = Field(default=0.0, ge=0.0, le=100.0, description="総合没入スコア (0.0-100.0)")
    is_immersive: bool = Field(default=False, description="没入閾値(50.0)を超えているか")

    model_config = MODEL_CONFIG_DEFAULTS

    def calculate_total(self, weights: dict = None) -> float:
        """加重合計でトータルスコアを計算"""
        if weights is None:
            weights = {"pov_stability": 0.25, "empathy_gap": 0.30, 
                       "curiosity_hook_rate": 0.25, "sensory_density": 0.20}
        # empathy_gapは低い方が良いので反転
        inverted_empathy = 1.0 - self.empathy_gap
        self.total_immersion_score = (
            self.pov_stability * weights["pov_stability"] +
            inverted_empathy * weights["empathy_gap"] +
            self.curiosity_hook_rate * weights["curiosity_hook_rate"] +
            self.sensory_density * weights["sensory_density"]
        ) * 100.0
        self.is_immersive = self.total_immersion_score >= 50.0
        return self.total_immersion_score

    @classmethod
    def from_dict(cls, data: Dict) -> "ImmersionScore":
        return cls(**data)


class NarrativeWavePattern(BaseModel):
    """物語のストレス/カタルシスの波パターンを表すモデル"""
    stress_levels: List[int] = Field(default_factory=list, description="各話のストレス値履歴")
    catharsis_indices: List[int] = Field(default_factory=list, description="カタルシス発生話数のインデックス")
    emotional_peaks: List[int] = Field(default_factory=list, description="感情的高揚点の話数インデックス")
    trough_markers: List[int] = Field(default_factory=list, description="感情の谷間（緊張解放後）の話数インデックス")
    wave_score: float = Field(default=0.0, description="波の成熟度スコア (0.0-100.0)")
    is_healthy: bool = Field(default=True, description="健康的な波パターンかどうか")
    issues: List[str] = Field(default_factory=list, description="検出された問題点")

    model_config = MODEL_CONFIG_DEFAULTS


# ============================================================
# Phase 2: 論理監査エージェント独立化 — Issue リスト形式モデル
# ============================================================

class AuditIssue(BaseModel):
    """
    1件の論理矛盾指摘。
    「文章の修正」ではなく「純粋なファクトのバグの指摘」に限定する。
    """
    category: Literal["生死", "所持品", "時系列", "能力", "場所"] = Field(
        ..., description="矛盾のカテゴリ"
    )
    severity: Literal["Critical", "Major", "Minor"] = Field(
        default="Minor", description="深刻度"
    )
    description: str = Field(
        ..., description="矛盾の具体的な説明（どの話で何が起き、今話の何と矛盾するか）"
    )
    evidence_past: str = Field(
        default="", description="過去の事実の根拠となるテキスト"
    )
    evidence_current: str = Field(
        default="", description="今話で矛盾している箇所のテキスト"
    )
    constraint_for_next_ep: str = Field(
        default="",
        description="次話以降の執筆者に渡すべき制約指示（例：剣は折れているため第9話以降は別の武器を使うこと）"
    )

    model_config = MODEL_CONFIG_DEFAULTS


class LogicalAuditIssueList(BaseModel):
    """
    LLMが返す監査結果（Issue リスト形式）。
    rewrite_suggestion（文章修正）は廃止し、純粋な指摘のみを保持する。
    """
    is_consistent: bool = Field(default=True, description="ファクト矛盾がないか")
    issues: List[AuditIssue] = Field(default_factory=list, description="指摘されたIssueのリスト")
    overall_severity: Literal["Critical", "Major", "Minor", "None"] = Field(
        default="None", description="最も深刻なIssueの深刻度"
    )

    @model_validator(mode="before")
    @classmethod
    def unwrap_and_normalize(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "audit", "result"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break
            # issues が空またはなければ整合性OKとする
            if not data.get("issues"):
                data["is_consistent"] = True
                data["overall_severity"] = "None"
        return data

    model_config = MODEL_CONFIG_DEFAULTS


class StoredAuditIssue(BaseModel):
    """
    DBに永続化する監査Issue（ep_num と book_id を持つ）。
    audit_issues テーブルに保存される。
    """
    book_id: int = Field(..., description="作品ID")
    ep_num: int = Field(..., description="対象エピソード番号")
    issue: AuditIssue = Field(..., description="監査指摘内容")
    resolved: bool = Field(default=False, description="解決済みか")
    resolved_note: str = Field(
        default="", description="執筆エージェントがどう解決したか（次話の本文から自動抽出または手動入力）"
    )

    model_config = MODEL_CONFIG_DEFAULTS


class CriticDirective(BaseModel):
    """1件の矛盾に対するCriticの修正指令"""
    issue_category: str  # AuditIssue.category から引き継ぎ (生死/所持品/時系列/能力/場所)
    severity: Literal["Critical", "Major", "Minor"] = "Minor"
    problem_description: str   # 何が矛盾しているか（Criticが要約）
    violating_snippet: str     # 本文中の問題箇所（抜粋）
    correction_instruction: str  # 「〇〇という理由で△△の行動を修正せよ」という具体的指示

    model_config = MODEL_CONFIG_DEFAULTS


class CriticFeedback(BaseModel):
    """Criticエージェントが生成するフィードバック全体"""
    has_critical_issues: bool = False
    overall_assessment: str = ""       # 矛盾の全体像の要約
    directives: List[CriticDirective] = Field(default_factory=list)
    rewrite_guidance: str = ""         # WritingAgentへの一括注入用テキスト

    @model_validator(mode="before")
    @classmethod
    def unwrap_critic_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "critic", "result"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break
        return data

    model_config = MODEL_CONFIG_DEFAULTS

