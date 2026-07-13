import asyncio
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import config
import config.base
from src.backend.background import StatusReporter
from src.backend.database.core import DatabaseManager, init_db
from src.backend.engine import UltimateHegemonyEngine
from src.backend.workflows.full_auto_workflow import FullAutoWorkflow


class CLIStatusReporter(StatusReporter):
    def report(self, message: str, status: str = "info"):
        prefix = "🚨 " if status == "error" else "⚠️ " if status == "warning" else "ℹ️ "
        print(f"{prefix}[{status.upper()}] {message}")

    def update_progress(self, current: int, total: int, step_name: str = "", *args, **kwargs):
        print(f"\n🔄 進捗: [{current}/{total}] {step_name}")

async def main():
    print("==================================================")
    print("⚔️ 覇権小説エンジン v3.0 - 動作確認用デモ")
    print("==================================================\n")

    api_key = os.getenv("GEMINI_API_KEY") or input("Gemini API Keyを入力してください: ").strip()
    if not api_key:
        return print("APIキーが入力されなかったため終了します。")

    print("\nデータベースを初期化しています...")
    db_url = "sqlite+aiosqlite:///demo_hegemony.db"
    config.DATABASE_URL = db_url
    config.base.DATABASE_URL = db_url
    init_db("demo_hegemony.db")
    db_manager = DatabaseManager(db_url)

    engine = UltimateHegemonyEngine(api_key=api_key, db_manager=db_manager)
    workflow = FullAutoWorkflow(engine)
    reporter = CLIStatusReporter()

    print("\n--- デモ実行設定 ---\n・ジャンル: ファンタジー\n・キーワード: 追放, チート, ざまぁ\n・アーキタイプ: 王道ざまぁ（爽快感最大）\n・エピソード数: 1話\n・目標文字数: 500字\n--------------------\n")
    # input("Enterキーを押すと全自動執筆を開始します...")
    print("\n🚀 実行を開始します...\n")

    try:
        result = await workflow.execute(
            reporter=reporter, genre="ファンタジー", keywords="追放, チート, ざまぁ",
            archetype_key="王道ざまぁ（爽快感最大）", target_eps=1, initial_limit=1,
            word_count=500, concept="動作確認用デモプロット"
        )
        print("\n==================================================")
        print("🎉 デモ実行が完了しました！\n==================================================")
        print(f"Book ID: {result.get('book_id')}\nタイトル: {result.get('title')}\n生成文字数目安: {result.get('chars_count')} 文字")
        if result.get("failed_episodes"): print(f"失敗エピソード: {len(result['failed_episodes'])} 件")
    except Exception as e:
        print(f"\n🚨 [エラー発生] {e}")

if __name__ == "__main__":
    asyncio.run(main())

