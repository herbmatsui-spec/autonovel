"""上級者エディタ（Studio Mode）用データモデルモジュール。

インラインAI五感拡張、GraphRAG専属AI編集者、Next Beats 3分岐生成のリクエスト・レスポンススキーマを定義。
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ==========================================
# 1. インライン AI & 五感・Show Don't Tell 拡張
# ==========================================


class SensoryType(StrEnum):
    """五感・描写拡張タイプ"""

    VISUAL = "visual"  # 視覚（色彩、光影、微細な動作）
    AUDITORY = "auditory"  # 聴覚（環境音、声色、静寂）
    OLFACTORY = "olfactory"  # 嗅覚（香り、匂い、大気の質感）
    TACTILE = "tactile"  # 触覚（温度、肌触り、痛み、重み）
    GUSTATORY = "gustatory"  # 味覚（風味、舌触り）
    METAPHOR = "metaphor"  # 比喩（詩的表現、文学的レトリック）


class ToneType(StrEnum):
    """トーン書き換えタイプ"""

    TENSION = "tension"  # 緊迫感・サスペンス向上
    EROTIC = "erotic"  # 艶やかさ・官能的ニュアンス
    FAST_PACED = "fast_paced"  # テンポ加速・切れ味ある文章
    FORMAL = "formal"  # 重厚・古典・格調高い文体
    LYRICAL = "lyrical"  # 情緒的・叙情的な文体


class AssistAction(StrEnum):
    """アシスト操作種別"""

    DESCRIBE = "describe"  # 五感描写拡張
    SHOW_DONT_TELL = "show_dont_tell"  # 行動・情景による感情提示
    REWRITE = "rewrite"  # トーン書き換え
    EXPAND = "expand"  # 続きの展開・肉付け


class AssistRequest(BaseModel):
    """インラインAIアシストリクエスト"""

    text: str = Field(..., min_length=1, description="選択・編集対象の本文テキスト")
    action: AssistAction = Field(default=AssistAction.DESCRIBE, description="実行するアクション")
    sensory_type: SensoryType | None = Field(
        default=None, description="五感拡張の種別（action=describe時）"
    )
    tone_type: ToneType | None = Field(
        default=None, description="書き換えトーン種別（action=rewrite時）"
    )
    genre: str = Field(default="ハイファンタジー (R15)", description="作品ジャンル")
    context_before: str = Field(default="", description="選択箇所の直前の文脈")
    context_after: str = Field(default="", description="選択箇所の直後の文脈")
    custom_instruction: str = Field(default="", description="ユーザー独自の追加指示")


class AssistResponse(BaseModel):
    """インラインAIアシストレスポンス"""

    original_text: str = Field(..., description="元のテキスト")
    result_text: str = Field(..., description="AIによって生成・拡張されたテキスト")
    action: AssistAction = Field(..., description="実行されたアクション")
    diff_summary: str = Field(default="", description="変更内容の要約")


# ==========================================
# 2. GraphRAG 専属 AI 編集者 (Ask Bible & 矛盾診断)
# ==========================================


class GraphEvidenceNode(BaseModel):
    """回答の根拠となったナレッジグラフのノード・事実情報"""

    id: str = Field(..., description="ノードIDまたはエンティティ名")
    label: str = Field(
        default="Entity", description="ノードラベル (Character, Location, Item, Event)"
    )
    properties: dict[str, Any] = Field(default_factory=dict, description="ノード属性情報")
    source_reference: str = Field(default="", description="出展情報 (例: 第1章, 世界観バイブル)")


class AskBibleRequest(BaseModel):
    """世界観バイブル・過去章 Q&A リクエスト"""

    book_id: int = Field(default=1, description="作品ID")
    query: str = Field(..., min_length=1, description="質問内容")
    current_chapter: int | None = Field(default=None, description="現在の執筆中話数")


class AskBibleResponse(BaseModel):
    """世界観バイブル・過去章 Q&A レスポンス"""

    answer: str = Field(..., description="AI編集者からの回答")
    evidence_nodes: list[GraphEvidenceNode] = Field(
        default_factory=list, description="回答の根拠となったグラフノード群"
    )
    related_characters: list[str] = Field(
        default_factory=list, description="関連キャラクター名一覧"
    )


class ConsistencyIssue(BaseModel):
    """設定矛盾・不整合の検出項目"""

    issue_type: str = Field(
        ..., description="矛盾の種類 (attribute, relationship, timeline, death_status, location)"
    )
    severity: str = Field(default="warning", description="重要度 (error, warning, info)")
    description: str = Field(..., description="矛盾内容の解説")
    conflicting_text: str = Field(default="", description="本文中の該当箇所")
    suggested_fix: str = Field(default="", description="修正の提案")


class ConsistencyAuditRequest(BaseModel):
    """リアルタイム設定矛盾診断リクエスト"""

    book_id: int = Field(default=1, description="作品ID")
    content: str = Field(..., min_length=1, description="診断対象の本文")
    current_chapter: int = Field(default=1, description="現在の話数")


class ConsistencyAuditResponse(BaseModel):
    """リアルタイム設定矛盾診断レスポンス"""

    has_issues: bool = Field(default=False, description="矛盾が検出されたかどうか")
    issues: list[ConsistencyIssue] = Field(default_factory=list, description="検出された矛盾リスト")
    confidence_score: float = Field(default=1.0, description="診断の信頼度 (0.0 - 1.0)")


# ==========================================
# 3. Next Beats 3バリエーション分岐生成
# ==========================================


class BranchType(StrEnum):
    """展開分岐タイプ"""

    ROYAL = "royal"  # 王道・カタルシス・主人公の活躍
    TWIST = "twist"  # サスペンス・急展開・どんでん返し
    PSYCHOLOGY = "psychology"  # 日常・心情深化・キャラクターの掛け合い


class BeatCard(BaseModel):
    """1つの展開バリエーションカード"""

    card_id: str = Field(..., description="カード識別ID (card_a, card_b, card_c)")
    branch_type: BranchType = Field(..., description="分岐タイプ")
    title: str = Field(..., description="展開タイトル")
    summary: str = Field(..., description="展開のあらすじ・要約")
    content: str = Field(..., description="生成された次シーンの本文抜粋 (300-600文字)")
    hook_text: str = Field(default="", description="次のエピソードへの引き・クリフハンガー")


class NextBeatsRequest(BaseModel):
    """Next Beats 3バリエーション生成リクエスト"""

    book_id: int = Field(default=1, description="作品ID")
    current_text: str = Field(..., min_length=1, description="執筆済みの直前本文")
    genre: str = Field(default="ハイファンタジー (R15)", description="ジャンル")
    character_context: str = Field(default="", description="主人公や登場人物の現在の状況")
    temperature: float = Field(default=0.8, description="生成の多様性パラメータ")


class NextBeatsResponse(BaseModel):
    """Next Beats 3バリエーション生成レスポンス"""

    beats: list[BeatCard] = Field(default_factory=list, description="3つの展開カード")
    original_tail: str = Field(default="", description="参照した直前本文の末尾抜粋")
