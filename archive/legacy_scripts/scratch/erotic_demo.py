import asyncio
import os
import sys

# パス追加
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.agents.writing import WritingAgent
from src.core.container import make_container


async def main():
    print("==================================================")
    print("🔞 官能A サブエージェント動作確認・生成デモ (R15相当)")
    print("==================================================")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("エラー: 環境変数 GEMINI_API_KEY が設定されていません。")
        return

    # DIコンテナと依存関係のセットアップ
    container = make_container(api_key)

    # 簡易的に LLM サービスとプロンプトマネージャを準備
    llm_service = container.llm()
    prompt_manager = container.pm()

    # WritingAgent の準備
    agent = WritingAgent(
        llm=llm_service,
        prompt_manager=prompt_manager,
    )

    # 官能Aを有効化した設定コンテキスト
    context = {
        "nsfw_enabled": True,
        "erotic_intensity": 3,  # R15相当 (0:なし, 3:R15, 5:過激)
        "platform_preset": "nocturn_novel",  # ノクターン向け（適度な比喩と伏字化）
        "target_word_count": 800,
        "character_info": "主人公: 青年剣士セシル (ぶっきらぼうだが一途)\nヒロイン: 聖女エミリア (セシルを密かに慕っている)",
        "scene_setting": "戦いの夜、傷を負ったセシルを手当てする二人だけの静かな天幕の中。",
        "plot": {
            "title": "天幕の中の温もり",
            "summary": "冷え切った夜、天幕の中で傷の手当てをするうちに、二人の距離が急接近する。"
        }
    }

    print("\n[INFO] 「官能A」を使ってエピソードの執筆を開始します...")
    try:
        # 執筆開始
        result = await agent.write_episode(
            book_id=999,
            ep_num=1,
            context=context
        )

        print("\n==================================================")
        print("🎉 執筆完了！生成されたテキスト:")
        print("==================================================\n")
        print(result)
        print("\n==================================================")

        # 伏字フィルタもテスト適用してみる
        from formatters.erotic_censor import apply_censorship
        print("\n📱 出力プラットフォーム (カクヨム恋愛向け) での伏字フィルタ後:")
        print("--------------------------------------------------\n")
        censored = apply_censorship(result, "kakuyomu_romance")
        print(censored)
        print("\n==================================================")

    except Exception as e:
        print(f"\n🚨 エラー発生: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
