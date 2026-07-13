import asyncio

from backend.engine import UltimateHegemonyEngine


async def test_oracle():
    engine = UltimateHegemonyEngine()
    print("Testing Oracle Prediction...")
    res = await engine.critique.predict_hegemony_success(
        genre="ファンタジー",
        title="追放された俺、実は世界最強の勇者だった件",
        concept="最強の剣士が不当に追放されるが、真の力を発揮して無双する物語。",
        custom_hook="実は主人公は魔王の息子である。"
    )
    print("Result:", res)

if __name__ == "__main__":
    asyncio.run(test_oracle())

