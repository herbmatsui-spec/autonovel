from typing import List, Dict, Any

import yaml

from src.llm.fallback_policy import DEFAULT_FALLBACK_CHAINS


class AuditorModelRouter:
    """モデルルーター - 8専門オーディター用の適切なLLMクライアント/プロバイダを解決する。"""

    def __init__(self, config_path: str = "config/audit_models.yaml", fallback_chains: Dict[str, List[str]] | None = None) -> None:
        """初期化。

        Args:
            config_path: 設定ファイルへのパス（auditor_models マッピング用）
            fallback_chains: 主プロバイダからフォールバック先プロバイダへのチェーンの辞書。
                None の場合はデフォルトチェーンを使用。
        """
        # フォールバックチェーンの読み込み（設定ファイルまたはデフォルト）
        self.fallback_chains = fallback_chains or DEFAULT_FALLBACK_CHAINS
        # モデル・マッピング: プロバイダ → モデル名
        self._model_mappings: Dict[str, str] = {
            "openai": "openai/gpt-4o",
            "claude": "anthropic/claude-3-5-sonnet-20241022",
            "gemini": "google/gemini-1.5-flash",
            "mock": "mock/model",
        }
        # プロバイダIDからクライアントインスタンスへのマッピング（実際のプロバイダで設定）
        self._client_registry: Dict[str, Any] = {}
        # 設定ファイルからオーディター→モデルマッピングを読み込み
        self._auditor_model_mapping: Dict[str, str] = self._load_auditor_model_config(config_path)
        # プロバイダ別のオーディター辞書（ホットリロード用）
        self._provider_auditors: Dict[str, list[str]] = {}
        self._rebuild_provider_auditors()

    def _load_auditor_model_config(self, config_path: str) -> Dict[str, str]:
        """config/audit_models.yaml から auditor→モデル名 マッピングを読み込む。"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            auditor_models = config.get("auditor_models", {})
            if isinstance(auditor_models, dict):
                return auditor_models
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to load auditor model config from {config_path}: {e}")
        # フォールバック: 設計時のデフォルトマッピング
        return {
            "factual": "google/gemini-1.5-flash",
            "consistency": "google/gemini-1.5-flash",
            "style": "google/gemini-1.5-flash",
            "multimodal": "google/gemini-1.5-flash",
            "creativity": "anthropic/claude-3-5-sonnet-20241022",
            "reader_hook": "openai/gpt-4o",
            "emotion_curve": "anthropic/claude-3-5-sonnet-20241022",
            "structure": "openai/gpt-4o",
        }

    def _rebuild_provider_auditors(self) -> None:
        """プロバイダ別オーディター一覧を再構築（ホットリロード用）。"""
        self._provider_auditors = {}
        for auditor, model_name in self._auditor_model_mapping.items():
            provider = self._model_name_to_provider(model_name)
            if provider not in self._provider_auditors:
                self._provider_auditors[provider] = []
            if auditor not in self._provider_auditors[provider]:
                self._provider_auditors[provider].append(auditor)

    def register_client(self, provider: str, client: Any) -> None:
        """プロバイダへのLLMクライアントを登録する。

        Args:
            provider: プロバイダID（openai、claudeなど）
            client: LLMクライアントインスタンス
        """
        self._client_registry[provider] = client

    def get_llm_for_auditor(self, auditor_name: str) -> Any | None:
        """オーディター名を受け取り、割り当てられたプロバイダを取得し、対応するクライアントを返す。"""
        # 1. オーディター特性に基づいて優先プロバイダを解決
        primary_provider = self._resolve_primary_provider_for_auditor(auditor_name)

        # 2. プロバイダ解決（フォールバックチェーンを使用）
        candidates = [primary_provider] + self.fallback_chains.get(primary_provider, [])

        # 3. 各候補を検索し、クライアントを返す
        for candidate in candidates:
            if candidate in self._client_registry:
                return self._client_registry[candidate]

        return None

    def _resolve_primary_provider_for_auditor(self, auditor_name: str) -> str:
        """オーディター特性に基づいて優先プロバイダを返す。

        この方法はconfig/audit_models.yamlと同期する必要がある。
        """
        # 設定ファイルからモデル名を取得、プロバイダへマッピング
        model_name = self._auditor_model_mapping.get(auditor_name)
        if model_name:
            return self._model_name_to_provider(model_name)

        # 設計マッピングに従う: 軽量タスク → gemini、高負荷タスク → claude/medium → openai
        if auditor_name in ("factual", "consistency", "style", "multimodal"):
            return "gemini"
        elif auditor_name in ("creativity", "emotion_curve"):
            return "claude"
        elif auditor_name == "reader_hook":
            return "openai"
        elif auditor_name == "structure":
            return "openai"
        else:
            # デフォルト（フォールバック含む）
            return "mock"

    def get_provider_for_auditor(self, auditor_name: str) -> str:
        """オーディターに割り当てられたプロバイダを取得する（クライアントのみの場合に便利）。"""
        primary = self._resolve_primary_provider_for_auditor(auditor_name)
        return primary

    def list_configured_auditors(self) -> list[str]:
        """設定で定義されたすべてのオーディターを返す。"""
        return list(self._auditor_model_mapping.keys())

    def refresh_from_config(self, config_path: str = "config/audit_models.yaml") -> None:
        """設定ファイルを再読み込み、チェーンを更新する（ホットリロード）。"""
        try:
            import logging
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            chains = config.get("auditor_models", {})
            # {"factual": "openai/gpt-4o-mini", ...} を {provider: [fallback1, fallback2]} に変換
            # 単純な実装: モデル名からプロバイダを抽出（anthropic/claude-3-5-sonnet-20241022 → claude）
            provider_chains: Dict[str, List[str]] = {}
            for auditor, model_name in chains.items():
                provider = self._model_name_to_provider(model_name)
                if provider not in provider_chains:
                    provider_chains[provider] = []
                # 他のオーディターもそのプロバイダを使用する場合は、重複しない
                for other in chains:
                    if other != auditor and self._model_name_to_provider(chains[other]) == provider:
                        provider_chains[provider].append(other)
            # プロバイダ自己自身を追加
            for provider in provider_chains:
                if provider not in provider_chains[provider]:
                    provider_chains[provider].insert(0, provider)
            self.fallback_chains = provider_chains
            # プロバイダ別一覧を再構築
            self._rebuild_provider_auditors()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to refresh from config: {e}")

    def _model_name_to_provider(self, model_name: str) -> str:
        """モデル名からプロバイダを抽出する。"""
        if "openai" in model_name.lower():
            return "openai"
        elif "claude" in model_name.lower() or "anthropic" in model_name.lower():
            return "claude"
        elif "gemini" in model_name.lower() or "google" in model_name.lower():
            return "gemini"
        elif "mock" in model_name.lower():
            return "mock"
        else:
            return "mock"