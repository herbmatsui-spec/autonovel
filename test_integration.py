import asyncio
import os
import sys
from engine import UltimateHegemonyEngine
from engine_service import HegemonyService
from background import StatusReporter, ProgressState

class TerminalReporter:
    """CLI環境用のステータスレポーター"""
    def __init__(self):
        self.state = ProgressState()

    def report(self, message: str, level: str = "info"):
        prefix = {"info": "ℹ️", "warning": "⚠️", "error": "🚨"}.get(level, "ℹ️")
        print(f"{prefix} {message}")

    def update_progress(self, current: int, total: int, text: str, sub_text: str = ""):
        pct = (current / total) * 100 if total > 0 else 0
        print(f"📊 [{pct:3.0f}%] {text} | {sub_text}")

async def main():
    # 1. APIキーの取得
    api_key = os.getenv("GEMINI_API_KEY", "AIzaSyD5vwqaRbquOO554oX7pfESV7Rv5ooleR4")
    if not api_key:
        print("❌ エラー: 環境変数 'GEMINI_API_KEY' が設定されていません。")
        return

    print("🚀 覇権小説エンジン 統合テスト開始...")
    
    # 2. エンジンとサービスの初期化
    engine = UltimateHegemonyEngine(api_key=api_key)
    service = HegemonyService(engine)
    reporter = TerminalReporter()

    # 3. かんたんモードの全自動ワークフローをテスト実行
    try:
        print("\n--- シナリオ: かんたんモード (全自動執筆テスト) ---")
        result = await service.full_auto_workflow(
            genre="ファンタジー",
            keywords="追放, 最強, 復讐",
            archetype_key="王道ざまぁ（爽快感最大）",
            target_eps=2,
            initial_limit=2,
            word_count=1500,
            reporter=reporter
        )
        print("\n✅ テスト成功!")
        print(f"📖 生成された作品ID: {result['book_id']}")
        print(f"✍️ 総執筆文字数: {result['chars_count']}文字")
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")

if __name__ == "__main__":
    asyncio.run(main())