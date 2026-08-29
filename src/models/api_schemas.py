"""
models/api_schemas.py — フロントエンド/バックエンド共通のAPIデータモデル

このファイルが API スキーマの単一真理源 (SSOT) です。
関連の重複定義が存在していた database/schemas.py は削除済み。
新規スキーマは必ずこのファイルに追加してください。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ==========================================
# 共通ベースモデル
# ==========================================


class BaseResponse(BaseModel):
    """基本レスポンス構造"""

    success: bool = True
    error_message: Optional[str] = None
    error_type: Optional[str] = None


# ==========================================
# ドメインモデル
# ==========================================


class BookSchema(BaseModel):
    """作品情報スキーマ"""

    id: int
    title: str
    genre: str
    concept: Optional[str] = ""
    synopsis: Optional[str] = ""
    target_eps: int = 0
    cumulative_stress: Optional[float] = 0.0
    created_at: Optional[datetime] = None
    axis_lock_flags: Dict[str, bool] = Field(default_factory=dict)


class PlotSchema(BaseModel):
    """プロット情報スキーマ"""

    ep_num: int
    title: str
    summary: str
    detailed_blueprint: Optional[str] = ""
    tension: float = 50.0
    is_catharsis: bool = False
    status: str = "open"  # "open", "closed"
    script_content: Optional[str] = ""


class ChapterSchema(BaseModel):
    """本文（章）情報スキーマ"""

    ep_num: int
    title: str
    content: str
    summary: str
    killer_phrase: Optional[str] = ""
    ai_insight: Optional[str] = ""  # ai_insight
    world_state: Dict[str, Any] = Field(default_factory=dict)
    trinity_review_log: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class BibleSchema(BaseModel):
    """世界観設定（バイブル）スキーマ"""

    id: int
    book_id: int
    settings: Dict[str, Any] = Field(default_factory=dict)
    revealed: Dict[str, Any] = Field(default_factory=dict)
    version: int = 0


class OptimizationReportSchema(BaseModel):
    """最適化レポートスキーマ"""

    id: int
    report_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


# ==========================================
# ワークフロー・タスク関連
# ==========================================


class TaskErrorDetail(BaseModel):
    """構造化エラー情報（フロントエンドのエラーユーザ体験用）"""
    code: str  # エラーコード例: NETWORK_ERROR, API_LIMIT, VALIDATION_ERROR, LLM_ERROR, UNKNOWN
    message: str  # ユーザー向けメッセージ
    detail: Optional[str] = None  # 技術的詳細（スタックトレースや内部情報）
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    retry_after_ms: Optional[int] = None  # レートリミットなどで再試行まで待つ必要がある場合
    recoverable: bool = True  # 再試行・再開が可能か
    context: Dict[str, Any] = Field(default_factory=dict)  # 任意の追加情報

class TaskStatusSchema(BaseModel):
    """タスク進捗スキーマ"""

    task_id: str
    is_running: bool = True
    current_step: int = 0
    total_steps: int = 0
    message: str = ""
    sub_message: str = ""
    trace_id: str = "N/A"
    streaming_text: str = ""
    logs: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    task_error: Optional[TaskErrorDetail] = None
    result_data: Optional[Any] = None
    token_usage: Dict[str, int] = Field(
        default_factory=lambda: {"prompt": 0, "completion": 0, "calls": 0}
    )
    start_time: float = 0.0


# ==========================================
# 共通認証リクエストモデル
# ==========================================


class AuthenticatedRequest(BaseModel):
    """API認証付きリクエストの共通ベース"""

    config: Dict[str, Any] = Field(default_factory=dict)


# ==========================================
# 個別リクエストモデル
# ==========================================


class EasyModeRequest(AuthenticatedRequest):
    """かんたんモード 全自動生成リクエスト"""

    genre: str
    keywords: str
    archetype_key: str
    target_eps: int
    initial_limit: int
    word_count: int
    concept: str = ""
    tone_vibe: float = 0.6
    style_key: Optional[str] = "style_web_standard"
    enable_erotic: bool = False
    erotic_intensity: int = 2


class EpisodeGenerateRequest(AuthenticatedRequest):
    """エピソード生成リクエスト"""

    book_id: int
    write_from: int
    write_to: int
    passion: float
    word_count: int
    do_refine: bool
    env_state: Dict[str, str] = Field(default_factory=dict)
    pipeline_mode: bool = False


class EpisodeGenerateCandidatesRequest(EpisodeGenerateRequest):
    """エピソード候補生成リクエスト"""

    pass


class PlanGenerationRequest(AuthenticatedRequest):
    """企画生成リクエスト"""

    params: Dict[str, Any]


class RetryFailedRequest(AuthenticatedRequest):
    """失敗エピソード再試行リクエスト"""

    book_id: int
    passion: float
    word_count: int


class PlotExpandRequest(AuthenticatedRequest):
    """プロット展開リクエスト"""

    book_id: int
    gen_from: int
    gen_to: int


class PlotExpandCandidatesRequest(PlotExpandRequest):
    """プロット候補展開リクエスト"""

    pass


class PlotRebuildRequest(AuthenticatedRequest):
    """プロット再構築リクエスト"""

    params: Dict[str, Any]


class CritiqueOptimizeRequest(AuthenticatedRequest):
    """品質分析最適化リクエスト"""

    book_id: int


class AuditPlanRequest(BaseModel):
    """プラン監査リクエスト（configなし）"""

    genre: str
    keywords: str
    trend_memo: str
    sanctuary: str = ""
    originality_score: int = 50
    platform: str = "カクヨム/なろう"


class ChapterImportRequest(BaseModel):
    """章インポートリクエスト"""

    book_id: int
    ep_num: int
    import_text: str
    do_refine: bool


class MarketingGenerateRequest(BaseModel):
    """マーケティング生成リクエスト"""

    book_id: int
    latest_ep: int


class RefineEroticRequest(AuthenticatedRequest):
    """官能研磨リクエスト"""

    book_id: int
    ep_num: int
    intensity: int = 2
    platform_preset: str = "kakuyomu_romance"


class PatchActionRequest(BaseModel):
    """パッチアクションリクエスト"""

    notes: Optional[str] = None


class PatchEditRequest(BaseModel):
    """パッチ編集リクエスト"""

    content: str


# ==========================================
# 小説制作パイプライン用リクエストモデル
# ==========================================


class ProduceNovelRequest(BaseModel):
    """作品全話生成リクエスト"""

    title: str = Field(..., description="作品タイトル")
    genre: str = Field(..., description="ジャンル")
    synopsis: str = Field(default="", description="あらすじ")
    keywords: List[str] = Field(default_factory=list, description="キーワード")
    target_episodes: int = Field(default=10, ge=1, le=100, description="目標話数")
    target_word_count: int = Field(default=3000, ge=100, le=50000, description="1話目標文字数")
    style_key: str = Field(default="default", description="スタイルキー")
    engine_key: str = Field(default="standard", description="エンジンキー")


class ProduceNovelResponse(BaseResponse):
    """作品生成レスポンス"""

    project_id: int = Field(..., description="プロジェクトID")
    status: str = Field(default="started", description="ステータス")
    message: str = Field(default="", description="メッセージ")
    token_usage_estimate: Optional[Dict[str, int]] = Field(
        default=None, description="推定トークン使用量"
    )


class NovelStatusResponse(BaseResponse):
    """作品ステータス取得レスポンス"""

    project_id: int
    status: str
    current_episode: int
    total_episodes: int
    progress_percent: float
    message: str
    completed_episodes: List[int] = Field(default_factory=list)


class EpisodeListResponse(BaseResponse):
    """エピソード一覧取得レスポンス"""

    episodes: List[Dict[str, Any]] = Field(default_factory=list)


class NovelReportResponse(BaseResponse):
    """制作レポート取得レスポンス"""

    report: Optional[Dict[str, Any]] = Field(default=None, description="レポートデータ")


class RollbackRequest(BaseModel):
    """プロンプトロールバックリクエスト"""

    version_id: int
    reason: Optional[str] = "手動ロールバック"


class ResolveIssueRequest(BaseModel):
    """課題解決リクエスト"""

    action: str  # 'Auto-Fix', 'Foreshadowing', 'Ignore'


# ==========================================
# ストーリーキャンバス関連
# ==========================================


class StoryNodeSchema(BaseModel):
    """ストーリーキャンバス ノードスキーマ"""

    id: str
    book_id: int
    kind: str  # 'premise' | 'act' | 'episode' | 'scene' | 'character' | 'foreshadow'
    label: str
    ep_num: Optional[int] = None
    character_id: Optional[int] = None
    x: float
    y: float
    data: Dict[str, Any] = Field(default_factory=dict, description="ノード種別別の追加データ")


class StoryEdgeSchema(BaseModel):
    """ストーリーキャンバス エッジスキーマ"""

    id: str
    book_id: int
    source: str
    target: str
    kind: str  # 'flow' | 'part_of' | 'pov' | 'dependency' | 'relationship'
    data: Dict[str, Any] = Field(default_factory=dict, description="エッジ種別別の追加データ（強度、ラベル等）")


class StoryCanvasResponse(BaseModel):
    """ストーリーキャンバス取得レスポンス"""

    nodes: List[StoryNodeSchema] = Field(default_factory=list)
    edges: List[StoryEdgeSchema] = Field(default_factory=list)


class CreateNodeRequest(BaseModel):
    """ノード作成リクエスト"""

    kind: str
    label: str
    ep_num: Optional[int] = None
    character_id: Optional[int] = None
    x: float
    y: float
    data: Dict[str, Any] = Field(default_factory=dict)


class UpdateNodeRequest(BaseModel):
    """ノード更新リクエスト"""

    id: str
    x: Optional[float] = None
    y: Optional[float] = None
    label: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class CreateEdgeRequest(BaseModel):
    """エッジ作成リクエスト"""

    source: str
    target: str
    kind: str
    data: Dict[str, Any] = Field(default_factory=dict)


class SeedCanvasRequest(BaseModel):
    """キャンバス初期化リクエスト（既存データから自動生成）"""

    include_plots: bool = True
    include_characters: bool = True
    include_structure: bool = True


class ErrorResponse(BaseResponse):
    """統一エラーレスポンスモデル"""

    success: bool = False
    error_code: str = "INTERNAL_ERROR"
    error_message: str = ""
    detail: Optional[str] = None


__all__ = [
    "BaseResponse",
    "BookSchema",
    "PlotSchema",
    "ChapterSchema",
    "BibleSchema",
    "OptimizationReportSchema",
    "TaskStatusSchema",
    "AuthenticatedRequest",
    "EasyModeRequest",
    "EpisodeGenerateRequest",
    "EpisodeGenerateCandidatesRequest",
    "PlanGenerationRequest",
    "RetryFailedRequest",
    "PlotExpandRequest",
    "PlotExpandCandidatesRequest",
    "PlotRebuildRequest",
    "CritiqueOptimizeRequest",
    "AuditPlanRequest",
    "ChapterImportRequest",
    "MarketingGenerateRequest",
    "RefineEroticRequest",
    "PatchActionRequest",
    "PatchEditRequest",
    "RollbackRequest",
    "ResolveIssueRequest",
    "StoryNodeSchema",
    "StoryEdgeSchema",
    "StoryCanvasResponse",
    "CreateNodeRequest",
    "UpdateNodeRequest",
    "CreateEdgeRequest",
    "SeedCanvasRequest",
    "ErrorResponse",
]
