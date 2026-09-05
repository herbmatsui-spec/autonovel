"""src/backend/plot_service.py - プロット生成サービス（後方互換性エイリアス）

実際の実装は src/services/plot_service.py に集約されています。
"""

from __future__ import annotations

from src.services.plot_service import PlotService

__all__ = ["PlotService"]
