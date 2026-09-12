# P2: プラグインアーキテクチャ導入 - 実装計画書

## 概要
`SkillAgent.discover_skills()` の動的インポート、`LLMProviderFactory` / `ImageProviderFactory` / `VectorStoreFactory` のリテラル列挙を、**エントリーポイントベースのプラグインシステム**に置換。外部パッケージからもプラグイン登録可能にする。

---

## Step 1: プラグインプロトコルの定義（コアインターフェース）

**作業**: `src/plugins/` ディレクトリ作成と基底プロトコル定義

```bash
mkdir -p src/plugins
```

**ファイル**: `src/plugins/protocols.py`

```python
"""Plugin Protocols - すべてのプラグインタイプの基底インターフェース。"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Plugin(Protocol):
    """すべてのプラグインが実装する最小プロトコル。"""

    name: str
    version: str
    plugin_type: str  # "skill" | "llm_provider" | "vector_store" | "image_provider" | "formatter" | "custom"

    @abstractmethod
    def create(self, **kwargs: Any) -> Any:
        """プラグインインスタンスを生成するファクトリーメソッド。"""
        ...


@runtime_checkable
class SkillPlugin(Plugin, Protocol):
    """スキルプラグイン固有プロトコル。"""

    plugin_type: str = "skill"

    @abstractmethod
    def create(self, repo: Any = None, llm: Any = None, **kwargs: Any) -> Any:
        """SkillAgent互換インスタンスを生成。"""
        ...


@runtime_checkable
class LLMProviderPlugin(Plugin, Protocol):
    """LLMプロバイダプラグイン固有プロトコル。"""

    plugin_type: str = "llm_provider"

    @abstractmethod
    def create(self, api_key: str = "", model: str = "", **kwargs: Any) -> Any:
        """ILLMProvider互換インスタンスを生成。"""
        ...


@runtime_checkable
class VectorStorePlugin(Plugin, Protocol):
    """ベクトルストアプラグイン固有プロトコル。"""

    plugin_type: str = "vector_store"

    @abstractmethod
    def create(self, **kwargs: Any) -> Any:
        """IVectorStoreProvider互換インスタンスを生成。"""
        ...


@runtime_checkable
class ImageProviderPlugin(Plugin, Protocol):
    """画像生成プロバイダプラグイン固有プロトコル。"""

    plugin_type: str = "image_provider"

    @abstractmethod
    def create(self, **kwargs: Any) -> Any:
        """IImageProvider互換インスタンスを生成。"""
        ...


@runtime_checkable
class FormatterPlugin(Plugin, Protocol):
    """フォーマッタプラグイン固有プロトコル。"""

    plugin_type: str = "formatter"

    @abstractmethod
    def create(self, **kwargs: Any) -> Any:
        """PlatformFormatter互換インスタンスを生成。"""
        ...


# ユニオン型（型チェック用）
PluginType = SkillPlugin | LLMProviderPlugin | VectorStorePlugin | ImageProviderPlugin | FormatterPlugin | Plugin
```

**確認**: `python -c "from src.plugins.protocols import Plugin, SkillPlugin; print('OK')"`

---

## Step 2: プラグインレジストリの実装

**作業**: `src/plugins/registry.py` - 登録・解決・エントリーポイント読み込み

```python
"""Plugin Registry - プラグインの登録・解決・動的読み込み。"""

from __future__ import annotations

import importlib.metadata
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Type

from src.plugins.protocols import Plugin, PluginType

logger = logging.getLogger(__name__)


class PluginRegistry:
    """プラグインタイプ別の登録・解決を管理。"""

    def __init__(self) -> None:
        self._plugins: Dict[str, Dict[str, Plugin]] = defaultdict(dict)  # plugin_type -> name -> plugin
        self._factories: Dict[str, Dict[str, Callable[..., Any]]] = defaultdict(dict)
        self._loaded_entry_points: bool = False

    def register(self, plugin_type: str, name: str, plugin: PluginType) -> None:
        """プラグインインスタンスを直接登録。"""
        if plugin_type not in self._plugins:
            self._plugins[plugin_type] = {}
        self._plugins[plugin_type][name] = plugin
        logger.debug(f"Registered plugin: {plugin_type}.{name} ({plugin.version})")

    def register_factory(self, plugin_type: str, name: str, factory: Callable[..., Any]) -> None:
        """ファクトリー関数を登録（遅延生成用）。"""
        self._factories[plugin_type][name] = factory
        logger.debug(f"Registered factory: {plugin_type}.{name}")

    def resolve(self, plugin_type: str, name: str, **kwargs: Any) -> Any:
        """名前でプラグインを解決しインスタンスを生成。"""
        # 1. 直接登録済みプラグイン
        if plugin_type in self._plugins and name in self._plugins[plugin_type]:
            plugin = self._plugins[plugin_type][name]
            return plugin.create(**kwargs)

        # 2. ファクトリー登録済み
        if plugin_type in self._factories and name in self._factories[plugin_type]:
            factory = self._factories[plugin_type][name]
            return factory(**kwargs)

        # 3. エントリーポイントから遅延読み込み
        if not self._loaded_entry_points:
            self._load_entry_points()
            return self.resolve(plugin_type, name, **kwargs)  # 再試行

        raise KeyError(f"Plugin not found: {plugin_type}.{name}")

    def list_plugins(self, plugin_type: str) -> List[str]:
        """指定タイプの登録済みプラグイン名一覧。"""
        self._ensure_loaded()
        return list(self._plugins.get(plugin_type, {}).keys())

    def list_all(self) -> Dict[str, List[str]]:
        """全タイプのプラグイン名一覧。"""
        self._ensure_loaded()
        return {pt: list(plugins.keys()) for pt, plugins in self._plugins.items()}

    def _ensure_loaded(self) -> None:
        if not self._loaded_entry_points:
            self._load_entry_points()

    def _load_entry_points(self) -> None:
        """pyproject.toml [project.entry-points] からプラグインを読み込み。"""
        try:
            for entry_point in importlib.metadata.entry_points(group="autonovel.plugins"):
                try:
                    plugin_class = entry_point.load()
                    plugin_instance = plugin_class()
                    self.register(plugin_instance.plugin_type, entry_point.name, plugin_instance)
                    logger.info(f"Loaded plugin from entry_point: {entry_point.name} ({plugin_instance.plugin_type})")
                except Exception as e:
                    logger.warning(f"Failed to load plugin {entry_point.name}: {e}")
        except Exception as e:
            logger.warning(f"Entry point loading failed: {e}")
        self._loaded_entry_points = True


# グローバルレジストリインスタンス
plugin_registry = PluginRegistry()
```

**確認**: `python -c "from src.plugins.registry import plugin_registry; print(plugin_registry.list_all())"`

---

## Step 3: 既存LLMプロバイダのプラグイン化

**作業**: `src/plugins/llm_providers.py` - 既存アダプタをプラグインクラス化

```python
"""LLM Provider Plugins - 既存アダプタのプラグインラッパー。"""

from __future__ import annotations

from typing import Any

from src.core.spi.llm.interface import ILLMProvider
from src.core.spi.llm.gemini_adapter import GeminiLLMProvider
from src.core.spi.llm.mock_adapter import MockLLMProvider
from src.core.spi.llm.openai_adapter import OpenAILLMProvider
from src.core.spi.llm.claude_adapter import ClaudeLLMProvider
from src.core.spi.llm.ollama_adapter import OllamaLLMProvider
from src.core.spi.llm.vllm_adapter import VLLMLLMProvider
from src.plugins.protocols import LLMProviderPlugin


class _LLMProviderPluginBase:
    """LLMプロバイダプラグイン基底クラス。"""

    plugin_type: str = "llm_provider"

    def __init__(self, name: str, version: str, provider_class: Type[ILLMProvider]):
        self.name = name
        self.version = version
        self._provider_class = provider_class

    def create(self, api_key: str = "", model: str = "", **kwargs: Any) -> ILLMProvider:
        return self._provider_class(api_key=api_key, model=model, **kwargs)


class GeminiPlugin(_LLMProviderPluginBase):
    def __init__(self):
        super().__init__("gemini", "1.0.0", GeminiLLMProvider)


class MockLLMPlugin(_LLMProviderPluginBase):
    def __init__(self):
        super().__init__("mock", "1.0.0", MockLLMProvider)


class OpenAIPlugin(_LLMProviderPluginBase):
    def __init__(self):
        super().__init__("openai", "1.0.0", OpenAILLMProvider)


class ClaudePlugin(_LLMProviderPluginBase):
    def __init__(self):
        super().__init__("claude", "1.0.0", ClaudeLLMProvider)


class OllamaPlugin(_LLMProviderPluginBase):
    def __init__(self):
        super().__init__("ollama", "1.0.0", OllamaLLMProvider)


class VLLMPlugin(_LLMProviderPluginBase):
    def __init__(self):
        super().__init__("vllm", "1.0.0", VLLMLLMProvider)


# インスタンス生成関数（レジストリ登録用）
def create_gemini_plugin() -> LLMProviderPlugin:
    return GeminiPlugin()


def create_mock_llm_plugin() -> LLMProviderPlugin:
    return MockLLMPlugin()


def create_openai_plugin() -> LLMProviderPlugin:
    return OpenAIPlugin()


def create_claude_plugin() -> LLMProviderPlugin:
    return ClaudePlugin()


def create_ollama_plugin() -> LLMProviderPlugin:
    return OllamaPlugin()


def create_vllm_plugin() -> LLMProviderPlugin:
    return VLLMPlugin()
```

**確認**: 
```python
from src.plugins.llm_providers import create_gemini_plugin
from src.plugins.registry import plugin_registry
plugin_registry.register_factory("llm_provider", "gemini", create_gemini_plugin)
llm = plugin_registry.resolve("llm_provider", "gemini", api_key="test", model="gemini-1.5-flash")
print(type(llm))
```

---

## Step 4: 既存ベクトルストア・画像プロバイダ・フォーマッタのプラグイン化

**作業**: 
- `src/plugins/vector_stores.py` - Chroma, pgvector, Mock
- `src/plugins/image_providers.py` - GenAI (Imagen), DALL-E 3, SD WebUI, ComfyUI, Mock
- `src/plugins/formatters.py` - PlatformFormatter (Narou, Kakuyomu, Kindle, Kobo, AlphaPolis)

```python
# src/plugins/vector_stores.py
from src.core.spi.vector_store.chroma_adapter import ChromaVectorProvider
from src.core.spi.vector_store.mock_adapter import MockVectorProvider
from src.core.spi.vector_store.pgvector_adapter import PgVectorProvider  # 要実装
from src.plugins.protocols import VectorStorePlugin

class ChromaVectorStorePlugin:
    plugin_type = "vector_store"
    name = "chroma"
    version = "1.0.0"
    def create(self, **kwargs): return ChromaVectorProvider(**kwargs)

# ... 同様に他プロバイダ
```

**確認**: 各プラグインタイプで `plugin_registry.resolve()` が動作すること

---

## Step 5: スキルプラグインの実装（SkillAgent互換）

**作業**: `src/plugins/skills.py` - 既存SkillAgentサブクラスをプラグイン化

```python
"""Skill Plugins - SkillAgentサブクラスをプラグインとして登録。"""

from __future__ import annotations

import importlib
import inspect
from typing import Any, Callable, List, Type

from src.agents.skill_base import SkillAgent, SkillManifestItem, load_skill_from_spec
from src.plugins.protocols import SkillPlugin


class SkillPluginWrapper:
    """既存SkillAgentクラスをプラグインプロトコルでラップ。"""

    plugin_type: str = "skill"

    def __init__(self, name: str, version: str, skill_class_path: str, default_config: dict = None):
        self.name = name
        self.version = version
        self._skill_class_path = skill_class_path
        self._default_config = default_config or {}

    def create(self, repo: Any = None, llm: Any = None, **kwargs: Any) -> SkillAgent:
        """マニフェスト仕様からスキルインスタンスを生成。"""
        spec = SkillManifestItem(
            name=self.name,
            skill_class=self._skill_class_path,
            config={**self._default_config, **kwargs},
        )
        return load_skill_from_spec(spec, repo=repo, llm=llm, **kwargs)


def discover_and_wrap_skills(package_path: str = "src.agents.skills") -> List[SkillPluginWrapper]:
    """既存のdiscover_skillsを利用してプラグインラッパーを一括生成。"""
    skills = SkillAgent.discover_skills(package_path)
    plugins = []
    for skill_cls in skills:
        # クラス名からプラグイン名を生成 (PlanningSkill -> planning)
        plugin_name = skill_cls.__name__.replace("Skill", "").replace("Agent", "").lower()
        plugins.append(SkillPluginWrapper(
            name=plugin_name,
            version=getattr(skill_cls, "version", "1.0"),
            skill_class_path=f"{skill_cls.__module__}.{skill_cls.__name__}",
        ))
    return plugins


# 手動登録用の既知スキル（マニフェストYAMLと対応）
KNOWN_SKILLS = {
    "planning": ("src.agents.skills.v2.planning_skill.PlanningSkill", {}),
    "writing": ("src.agents.skills.v2.writing_skill.WritingSkill", {}),
    "bible": ("src.agents.skills.v2.bible_skill.BibleSkill", {}),
    "context_builder": ("src.agents.skills.v2.context_builder_skill.ContextBuilderSkill", {}),
    "audit": ("src.agents.skills.v2.audit_skill.AuditSkill", {}),
    "marketing_copy": ("src.agents.skills.v2.marketing_copy_skill.MarketingCopySkill", {}),
    "illustration": ("src.agents.skills.v2.illustration_skill.IllustrationSkill", {}),
    "enrichment": ("src.agents.skills.v2.enrichment_skill.EnrichmentSkill", {}),
    "historical_accuracy": ("src.agents.skills.v2.historical_accuracy_skill.HistoricalAccuracySkill", {}),
    "cultural_compliance": ("src.agents.skills.v2.cultural_compliance_skill.CulturalComplianceSkill", {}),
}
```

**確認**: 
```python
from src.plugins.skills import discover_and_wrap_skills
plugins = discover_and_wrap_skills()
for p in plugins:
    print(p.name, p._skill_class_path)
```

---

## Step 6: エントリーポイント設定（pyproject.toml）

**作業**: `pyproject.toml` に `[project.entry-points]` 追加

```toml
[project.entry-points."autonovel.plugins"]
# LLM Providers
gemini = "src.plugins.llm_providers:create_gemini_plugin"
mock = "src.plugins.llm_providers:create_mock_llm_plugin"
openai = "src.plugins.llm_providers:create_openai_plugin"
claude = "src.plugins.llm_providers:create_claude_plugin"
ollama = "src.plugins.llm_providers:create_ollama_plugin"
vllm = "src.plugins.llm_providers:create_vllm_plugin"

# Vector Stores
chroma = "src.plugins.vector_stores:create_chroma_plugin"
pgvector = "src.plugins.vector_stores:create_pgvector_plugin"
mock_vector = "src.plugins.vector_stores:create_mock_vector_plugin"

# Image Providers
genai = "src.plugins.image_providers:create_genai_plugin"
dalle3 = "src.plugins.image_providers:create_dalle3_plugin"
sd_webui = "src.plugins.image_providers:create_sd_webui_plugin"
comfyui = "src.plugins.image_providers:create_comfyui_plugin"
mock_image = "src.plugins.image_providers:create_mock_image_plugin"

# Formatters
narou = "src.plugins.formatters:create_narou_formatter"
kakuyomu = "src.plugins.formatters:create_kakuyomu_formatter"
kindle = "src.plugins.formatters:create_kindle_formatter"
kobo = "src.plugins.formatters:create_kobo_formatter"
alphapolis = "src.plugins.formatters:create_alphapolis_formatter"

# Skills (代表的なもののみ、動的検出も併用)
planning = "src.plugins.skills:create_planning_skill_plugin"
writing = "src.plugins.skills:create_writing_skill_plugin"
bible = "src.plugins.skills:create_bible_skill_plugin"
```

**確認**: `pip install -e .` 後、`python -c "import importlib.metadata; print([ep.name for ep in importlib.metadata.entry_points(group='autonovel.plugins')])"`

---

## Step 7: YAMLマニフェスト駆動のプラグイン有効化設定

**作業**: `config/plugins.yaml` - プラグイン有効/無効・優先度・設定を一元管理

```yaml
# config/plugins.yaml
plugins:
  # LLM Providers (優先度順、最初に見つかったものを使用)
  llm_provider:
    enabled: [gemini, openai, claude, ollama, vllm, mock]
    default: gemini
    config:
      gemini:
        model: "gemini-1.5-flash"
      openai:
        model: "gpt-4o-mini"
      claude:
        model: "claude-3-5-sonnet-20241022"

  # Vector Stores
  vector_store:
    enabled: [chroma, pgvector, mock]
    default: chroma
    config:
      chroma:
        db_path: "./chroma_db"

  # Image Providers
  image_provider:
    enabled: [genai, dalle3, sd_webui, comfyui, mock]
    default: mock
    config:
      genai:
        model: "imagen-3.0"

  # Formatters (プラットフォーム別)
  formatter:
    enabled: [narou, kakuyomu, kindle, kobo, alphapolis]
    default: narou

  # Skills (有効化するスキルのみ列挙、順序=実行順序)
  skill:
    enabled:
      - planning
      - bible
      - context_builder
      - writing
      - audit
      - enrichment
      - illustration
    config:
      writing:
        temperature: 0.8
        max_tokens: 4000
      audit:
        strict_mode: true
```

**ローダー**: `src/plugins/config_loader.py`

```python
"""Plugin Configuration Loader - YAMLからプラグイン設定を読み込み。"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.plugins.registry import plugin_registry


class PluginConfigLoader:
    def __init__(self, config_path: str = "config/plugins.yaml"):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        return self._config

    def get_enabled_plugins(self, plugin_type: str) -> List[str]:
        return self._config.get("plugins", {}).get(plugin_type, {}).get("enabled", [])

    def get_default_plugin(self, plugin_type: str) -> Optional[str]:
        return self._config.get("plugins", {}).get(plugin_type, {}).get("default")

    def get_plugin_config(self, plugin_type: str, plugin_name: str) -> Dict[str, Any]:
        return self._config.get("plugins", {}).get(plugin_type, {}).get("config", {}).get(plugin_name, {})

    def apply_to_registry(self) -> None:
        """設定に基づきレジストリへデフォルトファクトリーを登録。"""
        for plugin_type in ["llm_provider", "vector_store", "image_provider", "formatter", "skill"]:
            enabled = self.get_enabled_plugins(plugin_type)
            default = self.get_default_plugin(plugin_type)
            
            for name in enabled:
                config = self.get_plugin_config(plugin_type, name)
                
                # ファクトリー登録（設定をデフォルト引数にバインド）
                def make_factory(n=name, c=config):
                    def factory(**kwargs):
                        merged = {**c, **kwargs}
                        return plugin_registry.resolve(plugin_type, n, **merged)
                    return factory
                
                plugin_registry.register_factory(plugin_type, name, make_factory())
            
            # デフォルト別名登録
            if default and default in enabled:
                plugin_registry.register_factory(plugin_type, "default", 
                    lambda **kw, d=default: plugin_registry.resolve(plugin_type, d, **kw))
```

**確認**: 
```python
from src.plugins.config_loader import PluginConfigLoader
loader = PluginConfigLoader()
loader.load()
loader.apply_to_registry()
print(plugin_registry.list_all())
llm = plugin_registry.resolve("llm_provider", "default")
print(type(llm))
```

---

## Step 8: 既存ファクトリークラスのプラグイン対応化（アダプタパターン）

**作業**: 既存 `LLMProviderFactory`, `ImageProviderFactory`, `VectorStoreFactory` を薄いラッパー化

```python
# src/core/spi/llm/provider_factory.py (修正)
"""LLM Provider Factory - プラグインレジストリ対応版。"""

from __future__ import annotations

from typing import Any, Optional

from src.core.spi.llm.interface import ILLMProvider
from src.plugins.registry import plugin_registry
from src.plugins.config_loader import PluginConfigLoader


class LLMProviderFactory:
    """PluginRegistryを内部で使用するファクトリーアダプタ。"""

    def __init__(self, config_loader: Optional[PluginConfigLoader] = None, **kwargs: Any) -> None:
        self.default_kwargs = kwargs
        self._config_loader = config_loader
        if config_loader:
            config_loader.apply_to_registry()

    def create(self, provider_type: str = "default", **kwargs: Any) -> ILLMProvider:
        merged_kwargs = {**self.default_kwargs, **kwargs}
        return plugin_registry.resolve("llm_provider", provider_type, **merged_kwargs)

    def list_available(self) -> list[str]:
        return plugin_registry.list_plugins("llm_provider")


# 同様に ImageProviderFactory, VectorStoreFactory も修正
```

**確認**: 既存コード `factory.create("gemini")` が変更なしで動作すること

---

## Step 9: SkillAgent.discover_skills() のプラグイン対応化

**作業**: `src/agents/skill_base.py` の `discover_skills` を拡張（後方互換維持）

```python
# src/agents/skill_base.py に追加（既存メソッドは残す）

@classmethod
def discover_skills_from_registry(cls, plugin_type: str = "skill") -> List[Type["SkillAgent"]]:
    """PluginRegistryからスキルプラグインを検出してクラスリストを返す。"""
    from src.plugins.registry import plugin_registry
    from src.plugins.config_loader import PluginConfigLoader
    
    # 設定適用（初回のみ）
    if not hasattr(cls, "_registry_configured"):
        loader = PluginConfigLoader()
        loader.load()
        loader.apply_to_registry()
        cls._registry_configured = True

    skill_names = plugin_registry.list_plugins(plugin_type)
    skills = []
    for name in skill_names:
        try:
            # ファクトリーからインスタンス生成してクラスを取得
            instance = plugin_registry.resolve(plugin_type, name, repo=None, llm=None)
            skills.append(instance.__class__)
        except Exception as e:
            logger.warning(f"Failed to load skill plugin {name}: {e}")
    return skills


@classmethod
def create_skill_from_registry(cls, skill_name: str, **dependencies: Any) -> "SkillAgent":
    """レジストリからスキルを生成（マニフェスト不要）。"""
    from src.plugins.registry import plugin_registry
    return plugin_registry.resolve("skill", skill_name, **dependencies)
```

**確認**: 
```python
from src.agents.skill_base import SkillAgent
skills = SkillAgent.discover_skills_from_registry()
print([s.__name__ for s in skills])
```

---

## Step 10: DIコンテナへの統合（AppContainer/InfraContainer修正）

**作業**: `src/core/container/infra.py` - ファクトリーをプラグイン対応版に置換

```python
# src/core/container/infra.py (修正)

from src.plugins.config_loader import PluginConfigLoader
from src.core.spi.llm.provider_factory import LLMProviderFactory
from src.core.spi.vector_store.provider_factory import VectorStoreFactory
from src.core.spi.image.provider_factory import ImageProviderFactory


class InfraContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["src", "src.kernels", "prompts"])

    config: providers.Singleton = providers.Singleton(GlobalConfigModel.load)
    global_config: providers.Singleton = providers.Singleton(GlobalConfig)

    # Plugin Config Loader (最初に初期化)
    plugin_config_loader: providers.Singleton = providers.Singleton(PluginConfigLoader)

    # Factories now use PluginConfigLoader
    llm_provider_factory: providers.Singleton = providers.Singleton(
        LLMProviderFactory,
        config_loader=plugin_config_loader,
    )
    vector_store_provider_factory: providers.Singleton = providers.Singleton(
        VectorStoreFactory,
        config_loader=plugin_config_loader,
    )
    image_provider_factory: providers.Singleton = providers.Singleton(
        ImageProviderFactory,
        config_loader=plugin_config_loader,
    )
    
    # ... 既存の db, chroma 等はそのまま
```

**確認**: `python -c "from src.core.container.infra import InfraContainer; c=InfraContainer(); print(c.llm_provider_factory().list_available())"`

---

## Step 11: 外部パッケージからのプラグイン追加ガイド・サンプル作成

**作業**: 
1. `docs/plugin_development.md` - プラグイン開発ガイド
2. `examples/custom_plugin/` - サンプル外部プラグインパッケージ

**サンプル構造**:
```
examples/custom_plugin/
├── pyproject.toml          # entry_points 定義
├── src/
│   └── my_plugin/
│       ├── __init__.py
│       ├── llm.py          # カスタムLLMプロバイダ
│       └── skill.py        # カスタムスキル
└── README.md
```

**pyproject.toml 例**:
```toml
[project]
name = "autonovel-custom-llm"
version = "0.1.0"
dependencies = ["autonovel>=4.8.5"]

[project.entry-points."autonovel.plugins"]
my_custom_llm = "my_plugin.llm:create_custom_llm_plugin"
my_custom_skill = "my_plugin.skill:create_custom_skill_plugin"
```

**確認**: `pip install examples/custom_plugin` 後、本体で `plugin_registry.list_plugins("llm_provider")` に `my_custom_llm` が表示されること

---

## Step 12: テスト・検証・ドキュメント化

**作業**:

1. **単体テスト** `tests/unit/test_plugin_system.py`:
```python
def test_plugin_registry_basic():
    from src.plugins.registry import PluginRegistry
    from src.plugins.protocols import LLMProviderPlugin
    
    registry = PluginRegistry()
    
    class TestPlugin:
        plugin_type = "llm_provider"
        name = "test"
        version = "1.0"
        def create(self, **kw): return "instance"
    
    registry.register("llm_provider", "test", TestPlugin())
    assert registry.resolve("llm_provider", "test") == "instance"

def test_entry_point_loading(monkeypatch):
    # entry_points モックで外部プラグイン読み込みテスト
    pass

def test_yaml_config_driven():
    from src.plugins.config_loader import PluginConfigLoader
    loader = PluginConfigLoader("config/test_plugins.yaml")
    loader.load()
    assert "gemini" in loader.get_enabled_plugins("llm_provider")
```

2. **統合テスト** `tests/integration/test_plugin_integration.py`:
   - 設定ファイル経由でデフォルトプロバイダが解決されるか
   - 無効化したプラグインが解決できないか
   - 外部パッケージインストール後に自動検出されるか

3. **依存方向検証**: `scripts/check_plugin_dependencies.py`
   - プラグインプロトコルが `src/plugins/protocols.py` のみに依存
   - 具象実装がプロトコルにのみ依存（逆依存なし）

4. **ドキュメント**: `docs/plugin_development.md`, `docs/architecture/plugin_architecture.md`

**確認**:
- `pytest tests/unit/test_plugin_system.py -v` 全パス
- `pytest tests/integration/test_plugin_integration.py -v` 全パス
- `python scripts/check_plugin_dependencies.py` 違反0件

---

## 実装順序の依存関係

```
Step 1 (プロトコル定義) ← 独立
    ↓
Step 2 (レジストリ実装) ← Step 1
    ↓
Step 3 (LLMプラグイン化) ← Step 1, 2
    ↓
Step 4 (他プロバイダ/フォーマッタ) ← Step 1, 2
    ↓
Step 5 (スキルプラグイン化) ← Step 1, 2, 既存SkillAgent
    ↓
Step 6 (エントリーポイント定義) ← Step 3, 4, 5
    ↓
Step 7 (YAML設定ローダー) ← Step 2
    ↓
Step 8 (既存ファクトリーアダプタ化) ← Step 2, 7
    ↓
Step 9 (SkillAgent拡張) ← Step 2, 5, 7
    ↓
Step 10 (DIコンテナ統合) ← Step 8
    ↓
Step 11 (外部プラグインサンプル) ← Step 6
    ↓
Step 12 (テスト・検証・文書化) ← 全Step
```

---

## 移行戦略（既存コードとの共存）

| 既存コード | 移行方針 |
|-----------|---------|
| `LLMProviderFactory.create("gemini")` | Step 8で内部的に `plugin_registry.resolve()` へ委譲（互換維持） |
| `SkillAgent.discover_skills("src.agents.skills")` | 既存メソッド残し、新メソッド `discover_skills_from_registry()` 追加 |
| `config/settings.py` の `LLM_PROVIDER` リテラル | Step 7のYAMLで置換、Settingsは非推奨化せず併存 |
| マニフェストYAML (`skills.yaml`) | Step 5で `load_skill_from_spec` 継続使用、プラグイン側で読込 |

---

## 完了基準

- [ ] `src/plugins/protocols.py` に全プラグインタイプの `@runtime_checkable Protocol` 定義
- [ ] `src/plugins/registry.py` に `register/resolve/list` + `importlib.metadata.entry_points` 読み込み
- [ ] 既存LLM/ベクトルストア/画像/フォーマッタがプラグイン化済み
- [ ] `SkillAgent` サブクラスがプラグインラッパーで登録可能
- [ ] `pyproject.toml` に `[project.entry-points."autonovel.plugins"]` 定義
- [ ] `config/plugins.yaml` で有効化/優先度/設定を管理
- [ ] 既存 `LLMProviderFactory` 等がプラグインレジストリ経由で動作（破壊的変更なし）
- [ ] 外部パッケージ `pip install` だけでプラグインが自動検出・使用可能
- [ ] 単体・統合テスト全パス、依存方向チェック違反0件