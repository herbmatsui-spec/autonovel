"""AutoNovel アプリケーション設定モジュール。

Pydantic BaseSettings により環境変数のバリデーションと一元管理を行う。
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
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
    APP_VERSION: str = "4.0.0"
    APP_ENV: Literal["development", "production", "testing", "local", "staging"] = "development"
    PORT: int = 8200
    HOST: str = "0.0.0.0"

    # データベース設定
    DATABASE_URL: str = Field(
        default_factory=lambda: f"sqlite:///{STORAGE_DIR / 'autonovel.db'}"
    )

    # Huey / Redis 設定
    HUEY_BACKEND: Literal["sqlite", "redis"] = "sqlite"
    HUEY_SQLITE_PATH: str = Field(
        default_factory=lambda: str(STORAGE_DIR / "huey.db")
    )
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS設定
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://localhost:8080,http://127.0.0.1:5173,http://127.0.0.1:8080"
    )

    # 認証設定
    AUTH_DISABLED: bool = False
    ALLOWED_API_KEYS: str = ""

    # ロギング設定
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console", "text"] = "console"

    # LLM設定 (OpenAI / Gemini 互換)
    # 実装済み: openai, gemini, mock
    # Ollama/vLLM/Claude は OpenAI 互換モードで利用可能 (OPENAI_BASE_URL 設定)
    LLM_PROVIDER: Literal["openai", "gemini", "mock"] = "mock"
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None  # LocalLLM, Ollama, vLLM 等の差し替え用
    OPENAI_MODEL: str = "gpt-4o-mini"

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Embedding / GraphRAG (pgvector + Apache AGE) 設定
    EMBEDDING_MODEL: str = "text-embedding-3-small"
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
    MULTIMEDIA_OUTPUT_DIR: str = Field(
        default_factory=lambda: str(STORAGE_DIR / "multimedia")
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins をリスト形式で取得する。"""
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


# グローバルな設定インスタンス
settings = Settings()

__all__ = ["Settings", "settings", "STORAGE_DIR", "ROOT_DIR"]
