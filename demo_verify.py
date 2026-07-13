"""
demo.py - バランス調整後 実作品生成・検証スクリプト
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import config as app_config

from dependency_injector import containers

from src.backend.database.core import DatabaseManager
from src.backend.engine import UltimateHegemonyEngine
from src.backend.workflows.full_auto_workflow import FullAutoWorkflow
from src.core.container import AppContainer
from src.shared.utils import StatusReporter


class DemoAppContainer(AppContainer):
    """streamlit_app パッケージを配線対象から除外したコンテナ（UI非依存でCLI実行用）"""
    wiring_config = containers.WiringConfiguration(packages=["src"])


class CLIStatusReporter:
    """StatusReporterプロトコル実装: CLI出力用"""
    def report(self, message: str, level: str = "info") -> None:
        prefix = "[ERROR]" if level == "error" else "[WARN]" if level == "warning" else "[INFO]"
        print(f"{prefix} {message}")

    def update_progress(self, current: int, total: int, text: str, sub_text: str = "") -> None:
        bar = "=" * current + "-" * (total - current)
        print(f"\n--- [{current}/{total}] {bar} ---")
        print(f"    {text}")
        if sub_text:
            print(f"    {sub_text}")


async def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY が設定されていません")
        return

    db_url = "sqlite+aiosqlite:///demo_verify_balance.db"
    app_config.DATABASE_URL = db_url
    import config.base
    config.base.DATABASE_URL = db_url

    from src.backend.database.core import init_db
    init_db("demo_verify_balance.db")
    db_manager = DatabaseManager(db_url)

    # streamlit_app 配線エラーを回避するため、エンジンが参照するコンテナを
    # スコープ限定版 (src のみ配線) に差し替える
    import src.backend.engine as engine_module
    engine_module.AppContainer = DemoAppContainer

    engine = UltimateHegemonyEngine(api_key=api_key, db_manager=db_manager)
    workflow = FullAutoWorkflow(engine)
    reporter = CLIStatusReporter()

    print("=" * 60)
    print("  バランス調整後 実作品生成検証")
    print("  Phase 1-3: 感情設計先行 (catharsis → zamaa_heavy)")
    print("  Phase 4-5: 尖り保全 (3種の角を提出)")
    print("  Phase 6-8: 早期面白さ検証 (interest_score >= 60)")
    print("=" * 60)

    try:
        result = await workflow.execute(
            reporter=reporter,
            genre="ファンタジー",
            keywords="追放, チート, ざまぁ",
            archetype_key="王道ざまぁ（爽快感最大）",
            target_eps=1,
            initial_limit=1,
            word_count=500,
            concept="追放された英雄が復讐するカタルシス作品",
            tone_vibe=0.6,
        )

        print("\n" + "=" * 60)
        print("  生成結果")
        print("=" * 60)
        print(f"  Book ID:     {result.get('book_id')}")
        print(f"  Title:       {result.get('title')}")
        print(f"  Chars:       {result.get('chars_count')}")
        print(f"  Failed Eps:  {result.get('failed_episodes')}")

        # 生成された作品内容を表示
        from src.models.db import PlotDbModel
        book_id = result["book_id"]
        plots = await engine.repo.plot.get_all_plots(book_id)
        if plots:
            plot = plots[0]
            print(f"\n  --- Plot #{plot.ep_num} ---")
            content = getattr(plot, "content", None) or getattr(plot, "draft", None) or "（本文未取得）"
            print(f"  Content preview: {str(content)[:500]}")
            print(f"  Target Tension:  {getattr(plot, 'target_tension', 'N/A')}")
            hook_raw = getattr(plot, "emotional_hook_json", None)
            if hook_raw:
                import json
                hook = json.loads(hook_raw)
                print(f"  Emotional Hook: {hook}")
            edges_raw = getattr(plot, "sharp_edges_json", None)
            if edges_raw:
                edges = json.loads(edges_raw)
                print(f"  Sharp Edges:    {[e.get('edge_type') for e in edges]}")

        # 全プロットのリスト表示
        print("\n  --- All Plots ---")
        for p in plots:
            content_preview = (getattr(p, "content", "") or getattr(p, "draft", "") or "")[:80]
            print(f"    Ep#{p.ep_num}: tension={getattr(p, 'target_tension', '?')}, content={content_preview}...")

    except Exception as e:
        import traceback
        print(f"\n[ERROR] 実行中にエラーが発生しました:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())