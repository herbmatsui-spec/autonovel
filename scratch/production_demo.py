import asyncio
import os
import sys
import io

# 標準出力のエンコーディング問題を回避するため、UTF-8で固定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# .envファイルから環境変数を読み込む
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# パス追加
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.agents.writing import WritingAgent
from src.core.container import AppContainer

async def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        with open("generated_work_for_report.txt", "w", encoding="utf-8") as f:
            f.write("エラー: GEMINI_API_KEYが設定されていません。")
        return

    # DIコンテナと依存関係のセットアップ
    container = AppContainer(api_key=api_key)

    # LLM サービスとプロンプトマネージャを準備
    llm_service = container.llm()
    prompt_manager = container.pm()

    # WritingAgent の準備
    agent = WritingAgent(
        llm=llm_service,
        prompt_manager=prompt_manager,
    )

    # 設定コンテキスト
    context = {
        "nsfw_enabled": True,
        "erotic_intensity": 3,  # R15相当
        "platform_preset": "nocturn_novel",
        "target_word_count": 1200,
        "character_info": "主人公: カイ (元エリート騎士。ある陰謀で全てを失い、絶望の中で生きる孤独な男)\nヒロイン: リリア (没落貴族の娘。カイの正体を知りながら、彼を精神的に救おうとする芯の強い女性)",
        "scene_setting": "激しい雨が降りしきる夜、古びた教会の中。カイが一人で雨に打たれながら絶望しているところに、リリアが傘を差し出す。",
        "plot": {
            "title": "雨の聖域と孤独な魂",
            "summary": "絶望に染まったカイが、リリアの献身的なアプローチによって、凍りついた心と身体を溶かしていく一夜の物語。精神的な救済から、抑えていた情動の爆発へと繋がる。",
        }
    }

    try:
        # 執筆開始
        result = await agent.write_episode(
            book_id=1001,
            ep_num=1,
            context=context
        )

        output_file = "generated_work_for_report.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result)

    except Exception as e:
        with open("generated_work_for_report.txt", "w", encoding="utf-8") as f:
            f.write(f"エラー発生: {str(e)}\n")
        import traceback
        with open("generated_work_for_report.txt", "a", encoding="utf-8") as f:
            traceback.print_exc(file=f)

if __name__ == "__main__":
    asyncio.run(main())