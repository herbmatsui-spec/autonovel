import asyncio
import os
import sys

# Add srcディレクトリをパスに追加してインポート可能にする
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import config
import config.base
from src.core.container import AppContainer
from src.backend.workflows.full_auto_workflow import FullAutoWorkflow
from src.backend.background import StatusReporter

class CLIStatusReporter(StatusReporter):
    def report(self, message: str, status: str = "info"):
        prefix = "[ERROR]" if status == "error" else "[WARN]" if status == "warning" else "[INFO]"
        # すべての UTF-8 文字列を cp932 でエンコードできない文字を置換して出力
        safe_message = message.encode('cp932', errors='replace').decode('cp932')
        print(f"{prefix} {safe_message}")

    def update_progress(self, current: int, total: int, step_name: str = "", *args, **kwargs):
        print(f"\nProgress: [{current}/{total}] {step_name}")

async def main():
    print("==================================================")
    print("Hegemony Novel Engine v3.0 - Task Generation")
    print("==================================================\n")

    # APIキーの設定
    api_key = "AIzaSyD5vwqaRbquOO554oX7pfESV7Rv5ooleR4"
    if not api_key:
        return print("API key is missing. Please provide one.")

    print("\nInitializing database and container...")
    db_url = "sqlite+aiosqlite:///task_hegemony.db"
    config.DATABASE_URL = db_url
    config.base.DATABASE_URL = db_url
    
    # DIコンテナを使用してエンジンを解決
    # これにより、UltimateHegemonyEngineに必要なすべてのエージェントが自動的に注入される
    container = AppContainer(api_key=api_key)
    engine = container.engine()
    
    workflow = FullAutoWorkflow(engine)
    reporter = CLIStatusReporter()

    # タスク設定
    # 1話3000字、合計10話
    settings = {
        "genre": "ファンタジー",
        "keywords": "追放, チート, ざまぁ, 領地経営",
        "archetype_key": "王道ざまぁ（爽快感最大）",
        "target_eps": 10,
        "initial_limit": 10, # 10話分を一気にプランニング
        "word_count": 3000,
        "concept": "元王宮魔導師が辺境に最強の魔法都市を築き上げる物語"
    }

    print("\n--- Generation Settings ---")
    for k, v in settings.items():
        print(f" {k}: {v}")
    print("---------------------------\n")

    print("\nStarting Full Auto Generation...\n")

    try:
        result = await workflow.execute(
            reporter=reporter,
            **settings
        )
        
        print("\n==================================================")
        print("Generation Completed Successfully!")
        print("==================================================")
        print(f"Book ID: {result.get('book_id')}")
        print(f"Title: {result.get('title')}")
        print(f"Total Estimated Characters: {result.get('chars_count')} characters")
        if result.get("failed_episodes"):
            print(f"Failed Episodes: {len(result['failed_episodes'])} episodes")
            
        # 結果をファイルに保存して後で検証できるようにする
        with open("generation_result.txt", "w", encoding="utf-8") as f:
            f.write(str(result))

    except Exception as e:
        print(f"\n[Critical Error] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
