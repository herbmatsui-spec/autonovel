"""Style Profile & Style DNA Data Models
作家性DNA・文体パラメータを保持するデータモデル。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SentenceLengthModel(BaseModel):
    """文長分布パラメータ"""

    avg: int = Field(default=40, description="平均文長（文字数）")
    std_dev: int = Field(default=12, description="標準偏差")
    min: int = Field(default=15, description="最小文長")
    max: int = Field(default=80, description="最大文長")
    description: str = Field(default="", description="文長の特徴解説")


class SentenceEndDistribution(BaseModel):
    """文末出現比率"""

    desu_masu: float = Field(default=0.10, description="です・ます調の割合")
    da_dearu: float = Field(default=0.60, description="だ・である調の割合")
    nominal: float = Field(default=0.20, description="体言止めの割合")
    exclamatory: float = Field(default=0.07, description="感嘆符（！）の割合")
    interrogative: float = Field(default=0.03, description="疑問符（？）の割合")
    description: str = Field(default="", description="文末リズムの特徴解説")


class MetaphorFrequency(BaseModel):
    """比喩表現の出現頻度と傾向"""

    per_1000_chars: float = Field(default=3.5, description="1000文字あたりの比喩数")
    types: dict[str, float] = Field(
        default_factory=lambda: {
            "visual": 0.40,
            "tactile": 0.25,
            "auditory": 0.15,
            "kinesthetic": 0.10,
            "abstract": 0.10,
        },
        description="五感比喩の比率",
    )
    description: str = Field(default="", description="比喩表現の特徴解説")


class StyleProfile(BaseModel):
    """作家性DNA（Style DNA）プロファイル"""

    id: str = Field(default="custom", description="スタイルID")
    name: str = Field(default="カスタム文体", description="スタイル表示名")
    genre_hint: str = Field(default="general", description="ジャンルヒント")
    category: str = Field(default="", description="カテゴリ: tempo/heavy/dark/elegant")
    tone_description: str = Field(
        default="臨場感あふれるテンポの良い文体",
        description="語り口・トーンの概要",
    )
    sentence_length: SentenceLengthModel = Field(default_factory=SentenceLengthModel)
    sentence_end_distribution: SentenceEndDistribution = Field(
        default_factory=SentenceEndDistribution
    )
    metaphor_frequency: MetaphorFrequency = Field(default_factory=MetaphorFrequency)
    kerenmi_intensity: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="ケレン味・ハッタリ・誇張表現の強度 (0.0〜1.0)",
    )
    forbidden_patterns: list[str] = Field(
        default_factory=lambda: [
            "〜だった、〜だったの連続",
            "過度に説明的で客観的すぎる地の文",
            "無感情な状況報告",
        ],
        description="避けるべきAI手癖パターン",
    )
    required_patterns: list[str] = Field(
        default_factory=lambda: [
            "感情のフックとなる強い動詞・体言止め",
            "読者の五感を刺激する具体的な感覚描写",
        ],
        description="必須の文体パターン",
    )
    few_shot_sample: str = Field(
        default="",
        description="文体のお手本となる代表的パラグラフ（100〜300文字）",
    )
    raw_sample: str = Field(
        default="",
        description="蒸留元の生サンプルテキスト",
    )

    def to_prompt_instruction(self) -> str:
        """プロンプトへ注入するための指示文を生成"""
        lines = [
            f"■ 作家性DNA（文体バイアス）: 【{self.name}】",
            f"- トーン: {self.tone_description}",
            f"- 文長リズム: 平均{self.sentence_length.avg}文字（短文でテンポを作り、長文で情緒を深める）",
            f"- 文末比率: だ・である({int(self.sentence_end_distribution.da_dearu * 100)}%), 体言止め({int(self.sentence_end_distribution.nominal * 100)}%)",
            f"- ケレン味・演出強度: {self.kerenmi_intensity:.1f}/1.0（状況を控えめに書かず、迫力と感情のフックを強めて描写せよ）",
        ]
        if self.required_patterns:
            req_str = "、".join(self.required_patterns[:3])
            lines.append(f"- 必須表現: {req_str}")
        if self.forbidden_patterns:
            forb_str = "、".join(self.forbidden_patterns[:3])
            lines.append(f"- 禁止表現: {forb_str}")
        if self.few_shot_sample:
            lines.append(
                f"\n【お手本とする文体・リズム（Few-Shot）】:\n{self.few_shot_sample.strip()}"
            )
        return "\n".join(lines)
