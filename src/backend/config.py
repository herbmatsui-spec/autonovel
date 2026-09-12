"""AutoNovel アプリケーション設定モジュール。

Pydantic BaseSettings により環境変数のバリデーションと一元管理を行う。
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# プロジェクトのルートディレクトリ
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = ROOT_DIR / "storage"

# storage ディレクトリが存在しない場合は自動作成
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """アプリケーション設定クラス。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # サーバー基本設定
    APP_NAME: str = "AutoNovel"
    APP_VERSION: str = "4.9.0"
    APP_ENV: Literal["development", "production", "testing", "local", "staging"] = "development"
    PORT: int = 8200
    HOST: str = "0.0.0.0"

    # データベース設定
    DATABASE_URL: str = Field(default_factory=lambda: f"sqlite:///{STORAGE_DIR / 'autonovel.db'}")

    # Huey / Redis 設定
    HUEY_BACKEND: Literal["sqlite", "redis"] = "sqlite"
    HUEY_SQLITE_PATH: str = Field(default_factory=lambda: str(STORAGE_DIR / "huey.db"))
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS設定
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://localhost:8080,http://127.0.0.1:5173,http://127.0.0.1:8080"
    )
    CORS_ALLOW_HEADERS: str = "Content-Type,Authorization,X-API-Key,Accept,Origin,X-Requested-With"

    # 認証設定
    AUTH_DISABLED: bool = False
    ALLOWED_API_KEYS: str = ""

    # ロギング設定
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console", "text"] = "console"

    # LLM設定 (5プロバイダ対応)
    # 実装済み: openai, gemini, mock, claude, ollama, vllm
    LLM_PROVIDER: Literal["openai", "gemini", "mock", "claude", "ollama", "vllm", "vertex"] = "mock"

    # OpenAI 互換設定
    OPENAI_API_KEY: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "OPENAI_KEY"),
    )
    OPENAI_BASE_URL: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Google Gemini 設定 (Step 37)
    GEMINI_API_KEY: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_GENAI_API_KEY", "GOOGLE_API_KEY"),
    )
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Anthropic Claude 設定 (Step 42)
    ANTHROPIC_API_KEY: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "CLAUDE_API_KEY"),
    )
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # OpenRouter 設定 (統一LLMゲートウェイ)
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_MODEL: str = "google/gemini-2.0-flash"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    # タスク別モデルルーティング (OpenRouter時に使用)
    OPENROUTER_ROUTING: dict[str, str] = {
        "planning": "google/gemini-2.0-flash",
        "plot_expansion": "google/gemini-2.0-flash",
        "writing": "anthropic/claude-3-5-sonnet-20241022",
        "climax": "anthropic/claude-3-5-sonnet-20241022",
        "audit": "google/gemini-2.0-flash",
        "marketing": "google/gemini-2.0-flash",
    }

    # Ollama 設定 (デフォルト: localhost:11434)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"

    # vLLM 設定 (デフォルト: localhost:8000)
    VLLM_BASE_URL: str = "http://localhost:8000"
    VLLM_MODEL: str = "meta-llama/Llama-3.1-8B-Instruct"

    # Embedding / GraphRAG (pgvector + Apache AGE) 設定
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_MODEL_FALLBACK: str = "text-embedding-3-small"
    AGE_GRAPH_NAME: str = "autonovel_graph"
    ENABLE_GRAPHRAG: bool = True

    # Vector / RAG (Phase: ハード依存化 Opt-in) 設定
    REQUIRE_PG: bool = False
    REQUIRE_CHROMA: bool = False
    RAG_FALLBACK_MODE: Literal["memory", "error"] = "memory"
    RAG_BATCH_SIZE: int = 64
    RERANKER_BACKEND: Literal["none", "simple", "cross_encoder"] = "none"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    CHROMA_DB_PATH: str = Field(default_factory=lambda: str(STORAGE_DIR / "chroma_db"))
    CHROMA_HOST: str = ""
    CHROMA_PORT: int = 8000
    AUTONOVEL_RAG_MODE: Literal["auto", "chroma", "memory"] = "auto"

    # マルチメディア展開 (Phase 7: Asset Pack / Media Mix / IF Routes / eBook)
    ENABLE_MULTIMEDIA: bool = False
    ENABLE_AUDIO_SYNTH: bool = False
    VOICEVOX_URL: str = "http://localhost:50021"
    VOICEVOX_DEFAULT_SPEAKER_ID: int = 3
    VOICEVOX_TIMEOUT_SECONDS: float = 30.0
    MULTIMEDIA_OUTPUT_DIR: str = Field(default_factory=lambda: str(STORAGE_DIR / "multimedia"))

    # 画像生成プロバイダ設定 (DALL-E 3 / Stable Diffusion WebUI / ComfyUI / Mock)
    IMAGE_PROVIDER: Literal["mock", "dalle3", "sd_webui", "comfyui"] = "mock"
    DALL_E_API_KEY: str | None = None
    SD_WEBUI_URL: str | None = None
    COMFYUI_URL: str | None = None

    # Phase 4: Enrichment Agent
    ENRICHMENT_ENABLED: bool = False

    # Phase 2: Feature Flags
    BLIND_REVIEW_ENABLED: bool = True
    MULTI_LAYER_AUDIT_ENABLED: bool = True
    RAG_REFLECTION_ENABLED: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins をリスト形式で取得する。"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def cors_allow_headers_list(self) -> list[str]:
        """許可する CORS ヘッダーをリスト形式で取得する。"""
        return [header.strip() for header in self.CORS_ALLOW_HEADERS.split(",") if header.strip()]

    def get_gemini_api_key(self) -> str:
        """GEMINI_API_KEY または GOOGLE_GENAI_API_KEY を安全・一元的に解決して返す (Step 38)."""
        import os
        return self.GEMINI_API_KEY or os.environ.get("GOOGLE_GENAI_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""


# グローバルな設定インスタンス
settings = Settings()

__all__ = ["Settings", "settings", "STORAGE_DIR", "ROOT_DIR"]
