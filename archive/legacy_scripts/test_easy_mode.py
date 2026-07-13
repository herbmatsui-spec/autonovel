import asyncio
import logging
import os

from backend.background import StatusReporter
from backend.database import DataRepository
from backend.engine import UltimateHegemonyEngine
from engine_service import HegemonyService

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

class DummyReporter(StatusReporter):
    def __init__(self):
        super().__init__()
        from backend.background import ProgressState
        self.state = ProgressState()

    def report(self, message: str, status: str = "info"):
        try:
            print(f"[{status}] {message}")
        except UnicodeEncodeError:
            print(f"[{status}] " + message.encode('cp932', errors='replace').decode('cp932'))

async def test_easy_mode():
    api_key = os.getenv("GEMINI_API_KEY", "AIzaSyD5vwqaRbquOO554oX7pfESV7Rv5ooleR4")
    os.environ["CHROMA_DB_PATH"] = "kaku_hegemony_test_chroma_db"
    from backend.database.core import DatabaseManager, set_db_manager
    test_db_path = "kaku_hegemony_test.db"
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass
    import shutil
    if os.path.exists("kaku_hegemony_test_chroma_db"):
        try:
            shutil.rmtree("kaku_hegemony_test_chroma_db")
        except Exception:
            pass
    db = DatabaseManager(test_db_path)
    db.start()
    set_db_manager(db)
    repo = DataRepository(db)

    engine = UltimateHegemonyEngine(api_key=api_key)
    service = HegemonyService(engine)
    reporter = DummyReporter()

    print("Testing Easy Mode Workflow...")
    try:
        result = await service.full_auto_workflow(
            genre="ファンタジー",
            keywords="剣と魔法",
            archetype_key="カスタム",
            target_eps=1,
            initial_limit=1,
            word_count=500,
            reporter=reporter,
            concept="追放された最強の剣士"
        )
        print(f"Success! Result: {result}")
    except Exception as e:
        print(f"Error during easy mode: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_easy_mode())

