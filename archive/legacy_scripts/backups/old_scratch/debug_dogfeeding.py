import asyncio
import sys
from pathlib import Path

root = Path(r"i:\claude2")
sys.path.insert(0, str(root))

from backend.engine import UltimateHegemonyEngine
from models import PlotDbModel


async def test_dogfeeding_errors():
    engine = UltimateHegemonyEngine(api_key="dummy")

    # Mock database repository
    class MockRepo:
        async def get_book(self, id):
            from models.db import BookDbModel
            return BookDbModel(id=id, title="Test", genre="fantasy", style_dna='{"mode": "default"}')
        async def get_plot(self, b_id, ep):
            return PlotDbModel(book_id=1, branch_id=b_id, ep_num=ep, detailed_blueprint="Test")
        async def get_latest_bible(self, id):
            from models.bible import WorldBible
            return WorldBible(title="Test")
        async def get_all_characters(self, id):
            return []
        async def get_chapters_before(self, b_id, ep):
            return []
        async def get_relevant_past_logs(self, b_id, ep, query_text=""):
            return ""

    engine.repo = MockRepo()

    print("Testing ContextManager.get_optimal_context_split call (WITHOUT narrative_controller)...")
    try:
        book_id, branch_id, ep_num = 1, 1, 1
        book = await engine.repo.get_book(book_id)
        plot = await engine.repo.get_plot(branch_id, ep_num)
        chars = await engine.repo.get_all_characters(book_id)

        # This now works without the 6th argument
        res = await engine.ctx_mgr.get_optimal_context_split(book_id, branch_id, ep_num, plot, chars)
        print("Call successful (Optional argument verified)!")
    except Exception as e:
        print(f"Call failed: {e}")

    print("\nTesting BookDbModel.style_key...")
    try:
        book = await engine.repo.get_book(1)
        print(f"Book style_key: {book.style_key}")
    except Exception as e:
        print(f"Book.style_key failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_dogfeeding_errors())

