
from pydantic import BaseModel, Field


class PlanningConfig(BaseModel):
    genre: str = Field(..., description="ジャンル名（例：王道ファンタジー）")
    keywords: str = Field(..., description="キーワード")
    style_key: str = Field(..., description="文体スタイルキー")
    concept: str = Field(..., description="作品コンセプト")
    title: str = Field(..., description="作品タイトル")
    cheat_scale: int = Field(default=4, description="チートスケール (1-10)")
    growth_curve: str = Field(default="最初からカンスト(無双)", description="成長曲線")
    system_assist: int = Field(default=70, description="システムアシスト値 (0-100)")
    cost_severity: int = Field(default=2, description="代償の深刻度 (1-10)")
    target_eps: int = Field(default=5, description="目標話数")
    initial_plot_limit: int = Field(default=1, description="初期プロット生成数")
    tension_threshold: int = Field(default=85, description="緊張（テンション）閾値。")
    tension_gain: float = Field(default=1.0, description="緊張蓄積倍率")
    engine_key: str = Field(default="conflict", description="エンジンキー（conflict / comfort / enigma / zamaa 等）")

    def __init__(self, **data):
        super().__init__(**data)
        # ざまぁエンジン使用時は、カタルシスを早期に誘発させるため閾値を自動的に下げる
        if self.engine_key == "zamaa":
            self.tension_threshold = 80
    run_debate: bool = Field(default=False, description="ディベートを実行するかどうか")
    ultra_fast: bool = Field(default=False, description="超高速モードを使用するかどうか")

    model_config = {
        "protected_namespaces": ()
    }
