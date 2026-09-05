"""src/backend/bible_service.py - 聖書サービス（後方互換性エイリアス）

実際の実装は src/services/bible_service.py に集約されています。
"""

from __future__ import annotations

from src.services.bible_service import WorldBibleGenerator

__all__ = ["WorldBibleGenerator"]
