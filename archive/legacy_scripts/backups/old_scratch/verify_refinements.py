import asyncio
import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.path.abspath("I:/claude2"))

# 環境変数のモック (必要なら)
# os.environ["GOOGLE_API_KEY"] = "..."

from backend.engine import UltimateHegemonyEngine


async def test_backend():
    print("--- Testing Title Generation ---")
    engine = UltimateHegemonyEngine()

    genre = "ファンタジー"
    keywords = "チート, 追放"
    custom_hook = "実は主人公は猫"

    try:
        titles = await engine.marketing.generate_titles(genre, keywords, custom_hook=custom_hook)
        print(f"Titles received: {len(titles)}")
        for t in titles:
            print(f"- {t.get('title')} (Viral: {t.get('viral_score')}%, Aura: {t.get('aura_type')})")

        print("\n--- Testing Aura Diagnosis (Oracle) ---")
        if titles:
            title = titles[0].get('title')
            concept = "猫が最強の魔術師として無双する"

            oracle_res = await engine.critique.predict_hegemony_success(genre, title, concept, custom_hook=custom_hook)
            print(f"Hegemony Score: {oracle_res.get('hegemony_score')}/100")
            print(f"Aura Color: {oracle_res.get('aura_color')}")
            print(f"Aura Type: {oracle_res.get('aura_type')}")
            print(f"Future Review: {oracle_res.get('future_review')[:100]}...")
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_backend())

