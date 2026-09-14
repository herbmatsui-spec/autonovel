# agents/skill_base.py
import logging
import time
from abc import abstractmethod
from typing import Any, TYPE_CHECKING, List, Type, Optional
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.agents.orchestrator import AgentContext, AgentResult
    from src.agents.event_bus import EventBus

from src.agents.base import BaseAgent
from src.agents.event_bus import AgentEvent

logger = logging.getLogger(__name__)


class SkillAgent(BaseAgent):
    """スキル駆動型エージェントの基底クラス"""

    version: str = "1.0"
    _skill_cache: dict[str, List[Type["SkillAgent"]]] = {}

    # クラスレベルのメトリクス
    _metrics: dict[str, dict] = {}

    def __init__(
        self,
        repo: Any = None,
        llm: Any = None,
        style_rag: Any = None,
        rag_prefetch: Any = None,
        event_bus: Optional["EventBus"] = None,
        enabled: bool = True,
        **kwargs: Any,
    ):
        # BaseAgentの初期化を呼び出す
        super().__init__(repo=repo, llm=llm, style_rag=style_rag, rag_prefetch=rag_prefetch)
        self._skill_name = self.__class__.__name__
        self.event_bus = event_bus
        self.enabled = enabled
        self.extra_config = kwargs
        self.ab_test_variant: Optional[str] = None  # A/Bテスト用バリアント ("a" or "b")

    def emit_event(self, event_name: str, payload: dict[str, Any]) -> None:
        """イベント発行ヘルパー（EventBus が設定されている場合のみ発行・非同期）"""
        if self.event_bus:
            event = AgentEvent(
                agent=self._skill_name,
                payload={"event": event_name, **payload},
                correlation_id=payload.get("correlation_id", self._skill_name),
            )
            self.event_bus.publish_async(event)

    async def emit_event_sync(self, event_name: str, payload: dict[str, Any]) -> None:
        """イベント発行ヘルパー（EventBus が設定されている場合のみ発行・同期・全ハンドラ完了を待つ）"""
        if self.event_bus:
            event = AgentEvent(
                agent=self._skill_name,
                payload={"event": event_name, **payload},
                correlation_id=payload.get("correlation_id", self._skill_name),
            )
            await self.event_bus.publish_sync(event)

    @abstractmethod
    async def execute(self, ctx: "AgentContext") -> "AgentResult":
        """スキル固有のメインロジック。サブクラスで実装する。"""
        pass

    async def run(self, ctx: "AgentContext") -> "AgentResult":
        """Orchestrator 用エントリーポイント。execute をラップし、メトリクスを記録する。"""
        start_time = time.perf_counter()
        try:
            result = await self.execute(ctx)
            self._record_metric("success", time.perf_counter() - start_time)
            return result
        except Exception:
            self._record_metric("error", time.perf_counter() - start_time)
            raise

    def _record_metric(self, status: str, duration: float):
        """実行メトリクスを記録"""
        if self._skill_name not in self._metrics:
            self._metrics[self._skill_name] = {"success": 0, "error": 0, "total_time": 0.0, "count": 0}
        self._metrics[self._skill_name][status] = self._metrics[self._skill_name].get(status, 0) + 1
        self._metrics[self._skill_name]["total_time"] += duration
        self._metrics[self._skill_name]["count"] += 1
        logger.debug(f"Skill {self._skill_name}: {status} in {duration:.3f}s")

    @classmethod
    def get_metrics(cls) -> dict:
        """全スキルのメトリクスを取得"""
        result = {}
        for name, metrics in cls._metrics.items():
            avg_time = metrics["total_time"] / max(1, metrics["count"])
            result[name] = {
                "success_count": metrics.get("success", 0),
                "error_count": metrics.get("error", 0),
                "total_executions": metrics["count"],
                "avg_duration_sec": round(avg_time, 3),
            }
        return result

    @classmethod
    def reset_metrics(cls):
        """メトリクスをリセット（テスト用）"""
        cls._metrics.clear()

    # BaseAgentから継承されるユーティリティメソッドをそのまま利用
    # _safe_get_dict, _safe_get_list, _get_book_branch

    @classmethod
    def discover_skills(cls, package_path: str) -> List[Type["SkillAgent"]]:
        """指定されたパッケージパスからSkillAgentのサブクラスを検出して返す"""
        if package_path in cls._skill_cache:
            return cls._skill_cache[package_path]

        import importlib
        import pkgutil

        skills = []
        package = importlib.import_module(package_path)
        for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            if is_pkg:
                # サブパッケージは再帰的に探索
                skills.extend(cls.discover_skills(module_name))
            else:
                module = importlib.import_module(module_name)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, SkillAgent)
                        and attr is not SkillAgent
                    ):
                        skills.append(attr)
        cls._skill_cache[package_path] = skills
        return skills

    @staticmethod
    def load_manifest(manifest_path: str) -> List[dict]:
        """マニフェストYAMLファイルを読み込んでパースし、辞書リストを返す（互換性用）"""
        import yaml
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            manifest = validate_manifest(data)
            return [item.model_dump(by_alias=True) for item in manifest.skills]
        except Exception as e:
            logger.error(f"Failed to load manifest from {manifest_path}: {e}")
            raise


class SkillManifestItem(BaseModel):
    """マニフェスト内の個別スキル定義モデル"""
    name: str
    skill_class: str = Field(alias="class")
    depends_on: List[str] = Field(default_factory=list)
    runs_after: List[str] = Field(default_factory=list)
    runs_before: List[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }


class SkillManifest(BaseModel):
    """スキルマニフェスト全体モデル"""
    skills: List[SkillManifestItem]


def validate_manifest(data: dict | str) -> SkillManifest:
    """YAMLファイルパスまたは辞書からマニフェストをバリデーションする"""
    import yaml
    if isinstance(data, str):
        with open(data, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)
    elif isinstance(data, dict):
        raw_data = data
    else:
        raise ValueError(f"Invalid manifest data type: {type(data)}")

    if not isinstance(raw_data, dict) or "skills" not in raw_data:
        raise ValueError("Manifest must be a mapping with a top-level 'skills' list")

    return SkillManifest.model_validate(raw_data)


def load_skill_from_spec(spec: SkillManifestItem | dict, **dependencies: Any) -> SkillAgent:
    """マニフェスト定義（または辞書）からスキルクラスを動的インポートしてインスタンス化する。"""
    import importlib
    import inspect

    if isinstance(spec, dict):
        item = SkillManifestItem.model_validate(spec)
    else:
        item = spec

    class_path = item.skill_class
    if "." not in class_path:
        raise ValueError(f"Invalid class path '{class_path}': must be in 'module.ClassName' format")

    module_name, class_name = class_path.rsplit(".", 1)
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise ImportError(f"Could not import module '{module_name}' for skill '{item.name}': {exc}") from exc

    if not hasattr(module, class_name):
        raise AttributeError(f"Module '{module_name}' has no attribute '{class_name}' for skill '{item.name}'")

    skill_cls = getattr(module, class_name)
    if not isinstance(skill_cls, type) or not issubclass(skill_cls, SkillAgent):
        raise TypeError(f"Class '{class_name}' in '{module_name}' is not a subclass of SkillAgent")

    # ラッパースキル（例: PlanningSkill -> PlanningAgent）の場合は内部エージェントのシグネチャも検査
    target_cls = getattr(module, class_name.replace("Skill", "Agent"), skill_cls)
    sig = inspect.signature(target_cls.__init__)
    params = sig.parameters
    has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())

    # 基本の依存性 (repo, llm, event_bus 等)
    kwargs = {}
    for k, v in dependencies.items():
        if k in params or (has_var_keyword and target_cls is skill_cls):
            kwargs[k] = v

    # IllustrationAgent などの特定依存性フォールバック
    if "image_service" in params and "image_service" not in kwargs:
        img_svc = dependencies.get("image_service")
        if not img_svc:
            try:
                import os
                from src.services.image_service import ImageService
                api_key = os.getenv("GOOGLE_GENAI_API_KEY") or os.getenv("GEMINI_API_KEY") or "dummy-key"
                img_svc = ImageService(api_key=api_key)
            except Exception:
                class _DummyImageService:
                    pass
                img_svc = _DummyImageService()
        kwargs["image_service"] = img_svc

    # config 内の設定値：明示的に定義されている名前付き引数のみ注入する
    for k, v in item.config.items():
        if k in params and params[k].kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            kwargs[k] = v

    instance = skill_cls(**kwargs)
    instance._manifest_config = item.config
    instance._skill_name = item.name
    instance.enabled = item.config.get("enabled", True)
    return instance