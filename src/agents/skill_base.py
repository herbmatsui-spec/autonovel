# agents/skill_base.py
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING, List, Type

if TYPE_CHECKING:
    from src.agents.orchestrator import AgentContext, AgentResult

from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class SkillAgent(BaseAgent):
    """スキル駆動型エージェントの基底クラス"""

    version: str = "1.0"
    _skill_cache: dict[str, List[Type["SkillAgent"]]] = {}

    # クラスレベルのメトリクス
    _metrics: dict[str, dict] = {}

    def __init__(
        self, repo: Any = None, llm: Any = None, style_rag: Any = None, rag_prefetch: Any = None
    ):
        # BaseAgentの初期化を呼び出す
        super().__init__(repo=repo, llm=llm, style_rag=style_rag, rag_prefetch=rag_prefetch)
        self._skill_name = self.__class__.__name__

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
        except Exception as e:
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
        """マニフェストYAMLファイルを読み込んでパースする"""
        import yaml
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data.get("skills", [])
        except Exception as e:
            logger.error(f"Failed to load manifest from {manifest_path}: {e}")
            return []