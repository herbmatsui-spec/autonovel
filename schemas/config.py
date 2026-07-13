"""
schemas/config.py — SSOT: グローバル設定モデル

このファイルが設定モデルの単一真実源（SSOT）です。
以下のファイルに重複定義されていた GlobalConfigModel をここに統合しました：
  - config/settings.py (削除済み)
  - config/project_context.py (削除済み)

デフォルト値は本番運用値（旧 project_context.py 由来）を採用しています。
"""
from __future__ import annotations

import logging
import os
import typing
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GlobalConfigModel(BaseModel):
    """グローバル設定モデル — 全設定の単一真実源（SSOT）"""

    # ===================== モデル設定 =====================
    model_writing: str = "gemma-4-31b-it"
    model_planning: str = "gemini-3.1-flash-lite"
    model_plot_expansion: str = "gemma-4-31b-it"
    model_climax: str = "gemma-4-31b-it"
    model_stable_fallback: str = "gemma-4-31b-it"
    model_ultra_stable: str = "gemma-4-31b-it"
    model_embedding: str = "text-embedding-004"

    # ===================== データベース設定 =====================
    database_url: Optional[str] = None  # 例: "postgresql://..." 環境変数 DATABASE_URL で上書き可

    # ===================== Redis キャッシュ設定 =====================
    redis_url: Optional[str] = None  # 例: "redis://localhost:6379/0" 環境変数 REDIS_URL で上書き可
    redis_max_connections: int = 10
    redis_default_ttl: int = 3600  # 1時間
    redis_namespace: str = "kaku:cache"

    # ===================== プロンプトキャッシュ設定 =====================
    prompt_cache_max_size: int = 100

    # ===================== コンテキストウィンドウ最適化設定 =====================
    context_window_target_ratio: float = 0.85  # コンテキストウィンドウ使用率目標 (85%)
    context_window_min_reserve: int = 2000  # 最小予約トークン数
    context_trimming_enabled: bool = True  # コンテキスト長超過時にトリミングを有効化
    prefetch_enabled: bool = True  # プロンプトプリフェッチを有効化
    prefetch_episode_count: int = 3  # プリフェッチ対象の後続エピソード数
    hybrid_search_alpha: float = 0.5  # ハイブリッド検索のベクトル重み (0.5=均等)

    # ===================== システムパラメータ =====================
    stress_catharsis_threshold: int = 85
    stress_filler_threshold: int = 35
    stress_climax_bonus: int = 50
    stress_hate_gain_base: int = 2
    max_history_len: int = 30
    auto_backup: bool = True
    safe_append_mode: str = "auto"
    cooldown_base: float = 0.0
    cooldown_min: float = 0.0
    cooldown_max: float = 90.0
    max_concurrency: int = 0
    optimized_prompt_patch: str = ""  # AIによる自己最適化パッチ

# ===================== 実行制御フラグ =====================
    fail_fast_mode: bool = False
    enable_dogfeeding: bool = True
    enable_heavy_audit: bool = True

    # ===================== エッジ保全設定 =====================
    similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    enable_semantic_edge_preservation: bool = Field(default=True)

    # ===================== AI挙動設定 =====================
    draft_polish_enabled: bool = True
    polishing_min_content_ratio: float = 0.5
    actor_critic_enabled: bool = True
    actor_critic_max_iterations: int = 2
    actor_critic_severity_threshold: str = "Major"
    specialized_amplifier_enabled: bool = True

    # ===================== NSFW/セーフティ設定 =====================
    enable_nsfw: bool = False
    safety_filter_level: str = "BLOCK_ONLY_HIGH"  # BLOCK_NONE, BLOCK_ONLY_HIGH, etc.

    # ===================== 拡張設定（ファイル由来） =====================
    domain_profiles: Optional[Dict[str, Any]] = None
    interaction_matrix: Optional[Dict[str, Any]] = None
    tropes: Optional[Dict[str, Any]] = None
    system_plugins: Optional[Dict[str, Any]] = None

    # ===================== カタルシス自動最適化 =====================
    catharsis_threshold: int = 65
    catharsis_reset_value: int = 0
    wave_pattern_ratio: Dict[str, float] = Field(
        default={"small": 0.7, "medium": 0.15, "large": 0.15},
        description="カタルシスパターンの割合設定"
    )
    catharsis_density_range: Dict[str, int] = Field(
        default={"min": 2, "max": 5},
        description="カタルシス密度スライダー設定"
    )
    min_immersion_score: float = Field(default=0.0, description="没入スコアの最低閾値 (0.0-100.0)")

    # ===================== Pydantic V2 設定 =====================
    model_config = {"protected_namespaces": ()}

    # ===================== 環境変数オーバーライド (明示的マージ) =====================
    # SSOT (settings.toml) を上書きできる環境変数を厳密にホワイトリスト化。
    # プレフィックスなしの既知の変数 (DATABASE_URL, REDIS_URL) と、
    # 明示的な KAKU_ プレフィックス変数のみが許可される。
    ENV_OVERRIDE_PREFIX: str = "KAKU_"
    ENV_OVERRIDE_MAP: ClassVar[Dict[str, str]] = {
        # 既知の標準環境変数 (プレフィックスなし)
        "DATABASE_URL": "database_url",
        "REDIS_URL": "redis_url",
        # 明示的な KAKU_ プレフィックス上書き
        "KAKU_MODEL_WRITING": "model_writing",
        "KAKU_MODEL_PLANNING": "model_planning",
        "KAKU_MODEL_PLOT_EXPANSION": "model_plot_expansion",
        "KAKU_MODEL_CLIMAX": "model_climax",
        "KAKU_MODEL_STABLE_FALLBACK": "model_stable_fallback",
        "KAKU_MODEL_ULTRA_STABLE": "model_ultra_stable",
        "KAKU_MODEL_EMBEDDING": "model_embedding",
        "KAKU_REDIS_MAX_CONNECTIONS": "redis_max_connections",
        "KAKU_REDIS_DEFAULT_TTL": "redis_default_ttl",
        "KAKU_REDIS_NAMESPACE": "redis_namespace",
        "KAKU_PROMPT_CACHE_MAX_SIZE": "prompt_cache_max_size",
        "KAKU_CONTEXT_WINDOW_TARGET_RATIO": "context_window_target_ratio",
        "KAKU_CONTEXT_WINDOW_MIN_RESERVE": "context_window_min_reserve",
        "KAKU_CONTEXT_TRIMMING_ENABLED": "context_trimming_enabled",
        "KAKU_PREFETCH_ENABLED": "prefetch_enabled",
        "KAKU_PREFETCH_EPISODE_COUNT": "prefetch_episode_count",
        "KAKU_HYBRID_SEARCH_ALPHA": "hybrid_search_alpha",
        "KAKU_STRESS_CATHARSIS_THRESHOLD": "stress_catharsis_threshold",
        "KAKU_STRESS_FILLER_THRESHOLD": "stress_filler_threshold",
        "KAKU_STRESS_CLIMAX_BONUS": "stress_climax_bonus",
        "KAKU_STRESS_HATE_GAIN_BASE": "stress_hate_gain_base",
        "KAKU_MAX_HISTORY_LEN": "max_history_len",
        "KAKU_AUTO_BACKUP": "auto_backup",
        "KAKU_SAFE_APPEND_MODE": "safe_append_mode",
        "KAKU_COOLDOWN_BASE": "cooldown_base",
        "KAKU_COOLDOWN_MIN": "cooldown_min",
        "KAKU_COOLDOWN_MAX": "cooldown_max",
        "KAKU_MAX_CONCURRENCY": "max_concurrency",
        "KAKU_OPTIMIZED_PROMPT_PATCH": "optimized_prompt_patch",
        "KAKU_FAIL_FAST_MODE": "fail_fast_mode",
        "KAKU_ENABLE_DOGFEEDING": "enable_dogfeeding",
        "KAKU_ENABLE_HEAVY_AUDIT": "enable_heavy_audit",
        "KAKU_DRAFT_POLISH_ENABLED": "draft_polish_enabled",
        "KAKU_POLISHING_MIN_CONTENT_RATIO": "polishing_min_content_ratio",
        "KAKU_ACTOR_CRITIC_ENABLED": "actor_critic_enabled",
        "KAKU_ACTOR_CRITIC_MAX_ITERATIONS": "actor_critic_max_iterations",
        "KAKU_ACTOR_CRITIC_SEVERITY_THRESHOLD": "actor_critic_severity_threshold",
        "KAKU_SPECIALIZED_AMPLIFIER_ENABLED": "specialized_amplifier_enabled",
        "KAKU_ENABLE_NSFW": "enable_nsfw",
        "KAKU_SAFETY_FILTER_LEVEL": "safety_filter_level",
    }

    # ===================== ファクトリメソッド =====================

    @staticmethod
    def _coerce_env_value(raw: str, annotation: Any) -> Any:
        """
        文字列の環境変数値を、対象フィールドの型に変換する。
        Optional[...] / Union の場合は非 None 側の型を採用する。
        """
        origin = typing.get_origin(annotation)
        args = typing.get_args(annotation)
        if origin is Union:
            non_none = [a for a in args if a is not type(None)]
            if non_none:
                annotation = non_none[0]
        if annotation is bool:
            return raw.strip().lower() in ("1", "true", "yes", "on", "enabled")
        if annotation is int:
            return int(raw)
        if annotation is float:
            return float(raw)
        return raw

    @classmethod
    def apply_env_overrides(cls, config: "GlobalConfigModel") -> "GlobalConfigModel":
        """
        明示的マッピング (ENV_OVERRIDE_MAP) に基づき、許可された環境変数で
        設定を上書きする。マッピング外の環境変数は無視される (SSOT統制)。
        """
        overrides: Dict[str, Any] = {}
        # ENV_OVERRIDE_MAP is defined as a class attribute, so access via cls
        for env_var, field_name in cls.ENV_OVERRIDE_MAP.items():
            if env_var in os.environ:
                raw = os.environ[env_var]
                field = cls.model_fields[field_name]
                overrides[field_name] = cls._coerce_env_value(raw, field.annotation)
                logger.info(
                    f"[CONFIG] 環境変数 {env_var} で設定を上書き: "
                    f"{field_name}={overrides[field_name]!r}"
                )
        if not overrides:
            return config
        return config.model_copy(update=overrides)

    def validate_consistency(self) -> List[str]:
        """
        設定値同士の論理整合性を検証する。戻り値はエラーメッセージのリスト
        (空なら整合性OK)。Pydantic の型検証は通った後のセマンティクス検証用。
        """
        errors: List[str] = []
        if self.cooldown_min > self.cooldown_max:
            errors.append(
                f"cooldown_min ({self.cooldown_min}) > cooldown_max ({self.cooldown_max}) です"
            )
        if not (0.0 <= self.context_window_target_ratio <= 1.0):
            errors.append(
                f"context_window_target_ratio は 0.0-1.0 の範囲です: {self.context_window_target_ratio}"
            )
        if self.max_concurrency < 0:
            errors.append(f"max_concurrency は 0 以上である必要があります: {self.max_concurrency}")
        if self.prefetch_episode_count < 0:
            errors.append(
                f"prefetch_episode_count は 0 以上である必要があります: {self.prefetch_episode_count}"
            )
        return errors

    @classmethod
    def from_toml(cls, path: Path) -> GlobalConfigModel:
        """
        TOML ファイルから設定を読み込む（非推奨）
        
        Deprecated: ConfigValidator.validate_all() を使用してください。
        このメソッドは後方互換性のために残されていますが、拡張設定（domain_profiles,
        interaction_matrix, tropes, system_plugins）は読み込まれません。
        """
        logger = __import__("logging").getLogger(__name__)
        logger.warning("[DEPRECATED] GlobalConfigModel.from_toml() が呼ばれました。ConfigValidator.validate_all() を使用してください。")
        logger.debug(f"[LOAD] GlobalConfigModel.from_toml() called: path={path}")
        import tomllib
        if not path.exists():
            logger.debug("[LOAD] from_toml: path not found, returning default")
            return cls.default()
        with open(path, "rb") as f:
            data = tomllib.load(f)
        flat_data = {}
        for section in data.values():
            if isinstance(section, dict):
                flat_data.update(section)
        logger.debug(f"[LOAD] from_toml: loaded {len(flat_data)} keys")
        return cls(**flat_data)

    @classmethod
    def load(cls) -> GlobalConfigModel:
        """
        ConfigValidator.validate_all() に委譲して設定を読み込む（SSOT）。
        
        このメソッドは後方互換性のためのラッパーです。
        内部では ConfigValidator.validate_all() を呼び、全設定ファイルを
        バリデーション・マージした GlobalConfigModel を返します。
        """
        logger = __import__("logging").getLogger(__name__)
        logger.debug("[LOAD] ===== GlobalConfigModel.load() called (delegating to ConfigValidator) ====")
        import traceback
        logger.debug(f"[LOAD] Call stack: {''.join(traceback.format_stack()[:-1])}")

        from config.validator import ConfigValidator
        validated = ConfigValidator.validate_all()
        result = validated["settings"]

        logger.debug("[LOAD] GlobalConfigModel.load() delegation completed")
        return result


    @classmethod
    def default(cls) -> GlobalConfigModel:
        """デフォルト値でインスタンス化"""
        return cls()

    @staticmethod
    def get_auto_concurrency() -> int:
        """CPU コア数から自動並行処理数を算出"""
        return min(8, (os.cpu_count() or 1) * 2)


class ModelRegistryModel(BaseModel):
    """モデルレジストリ（config/models.yaml 用）"""
    planning: str = "gemini-3.1-flash-lite"
    plot_expansion: str = "gemma-4-31b-it"
    writing: str = "gemma-4-31b-it"
    climax: str = "gemma-4-31b-it"
    fallback: str = "gemma-4-31b-it"
    ultra_stable: str = "gemma-4-31b-it"


class SystemPluginsModel(BaseModel):
    """システムプラグイン設定（config/system_plugins.yaml 用）"""
    debate_agent: Dict[str, str] = Field(
        default_factory=lambda: {"module": "src.agents.debate", "class": "NullDebateAgent"}
    )
    audit_service: Dict[str, str] = Field(
        default_factory=lambda: {"module": "src.services.audit_service", "class": "ProducerAuditService"}
    )


class TropesModel(BaseModel):
    """トロープ設定（config/tropes.json 用）"""
    tropes: List[str] = Field(default_factory=lambda: [
        "ざまぁ", "断罪", "成り上がり", "無自覚無双", "圧倒的報復", "追放ざまぁ",
        "ヤンデレヒロイン", "実は有能な従者", "狂信的な配下", "不遇な天才", "共依存",
        "戦わない最強", "復讐しない追放者", "善人すぎる悪役", "官能", "誘惑"
    ])
    title_patterns: List[str] = Field(default_factory=lambda: [
        "追放された最強の〜", "実は〜だった件"
    ])
    forbidden_words_replacements: Dict[str, str] = Field(default_factory=lambda: {
        "蹂躙": "「蹂躙」という言葉を直接使わず、代わりにそれを想起させる具体的な破壊現象（例：踏み潰される土、引き裂かれる旗、崩落する壁、悲鳴を上げる鉄、砕け散る瓦礫）を3話以上描写せよ。",
        "驚愕": "「驚愕」や「驚きを隠せない」といった抽象語を使わず、喉の鳴る音、震える指先、呼吸の停止、産毛の逆立ち等の生理現象で描写せよ。",
        "絶望": "「絶望」を使わず、色彩を失う視界、胃の腑に沈む鉛の重さ、肺を圧迫する空気、凍りつく思考等の物理的感覚で描写せよ。",
        "静寂": "「静寂」を使わず、風の音だけが響く感覚、自分の心臓の音だけが耳元でうるさいほどの無音、肌にまとわりつく空気の重さ等で描写せよ。",
        "圧倒": "「圧倒的」「圧倒された」を使わず、相手との体格差、魔圧による重圧、逃げ場のない包囲感、あるいは「蛇に睨まれた蛙」のような身体的硬直を描写せよ。",
        "歓喜": "「歓喜」「喜びに震える」を使わず、顔の筋肉が勝手に緩む感覚、心臓が跳ねるような鼓動、視界が急激に明るく開ける主観的変化で描写せよ。"
    })


class InteractionMatrixModel(BaseModel):
    """インタラクションマトリクス（config/interaction_matrix.yaml 用）"""
    resonance: Dict[str, float] = Field(
        default_factory=lambda: {"resonance": 0.05, "hegemony": -0.2, "conflict": -0.1, "serenity": 0.2}
    )
    hegemony: Dict[str, float] = Field(
        default_factory=lambda: {"resonance": -0.1, "hegemony": 0.05, "conflict": 0.1, "serenity": -0.1}
    )
    conflict: Dict[str, float] = Field(
        default_factory=lambda: {"resonance": -0.1, "hegemony": 0.2, "conflict": 0.05, "serenity": -0.2}
    )
    serenity: Dict[str, float] = Field(
        default_factory=lambda: {"resonance": 0.1, "hegemony": -0.2, "conflict": -0.3, "serenity": 0.05}
    )
    decay_rate: float = 0.98
    min_value: float = 0.0
    max_value: float = 100.0


class DomainProfileModel(BaseModel):
    """ドメインプロファイル（config/domain_profiles/*.json 用）"""
    DISABLE_CATHARSIS_ENGINE: bool = False
    STRESS_CATHARSIS_THRESHOLD: int = 85
    STRESS_FILLER_THRESHOLD: int = 35
    STRESS_CLIMAX_BONUS: int = 50
    STRESS_HATE_GAIN_BASE: int = 20
    SPECULATIVE_BRANCH_CATHARSIS_NAME: str = "Catharsis"
    SPECULATIVE_INSTRUCTION_CATHARSIS: str = (
        "【⚠️分岐プロット（カタルシス強め）】\n"
        "このエピソードは読者のカタルシスを最大化する構成（ざまぁ・圧倒的勝利等）に特化させてください。"
    )
    AUDIT_TRIGGER_KEYWORDS: List[str] = Field(default_factory=lambda: [
        "魔法", "スキル", "能力", "加護", "呪い", "代償", "コスト", "禁忌", "制約", "ルール",
        "死", "殺", "滅", "敗北", "勝利", "決戦", "戦闘", "激闘", "王", "皇帝", "神", "教義",
        "因果", "運命", "伏線", "真実", "正体", "裏切り", "契約", "誓約", "儀式"
    ])
    AUDIT_WORDS_CATHARSIS: List[str] = Field(
        default_factory=lambda: ["ざまぁ", "圧倒的勝利", "破滅", "ヘイト", "屈服"]
    )
    DE_AI_MODE: str = "strict"
    AUDITOR_PERSONA: str = "覇権プロデューサー"
    AUDITOR_INSTRUCTIONS: str = (
        "「バズるキーワードを追加しろ」「カタルシスが足りない」と指摘する敏腕プロデューサー。"
        "商用出版でランキング1位を狙える具体的な修正案を出力せよ。"
    )
    WEIGHT_EMOTIONAL_RESONANCE: float = 1.0
    WEIGHT_THEMATIC_DEPTH: float = 0.5
    WEIGHT_LITERARY_BEAUTY: float = 0.5
    WEIGHT_BASE_ENGAGEMENT: float = 4.0

