import logging
from typing import Any, Dict

from config.project_context import ProjectContext

logger = logging.getLogger(__name__)

class RuleABTester:
    """
    ルール変更の影響評価（A/Bテスト）を自動化するモジュール。
    指定されたキーワードを含むテストテキストに対して、
    ルール適用前（A）と適用後（B）のテキストを生成・比較評価します。
    """
    def __init__(self, engine: Any):
        self.engine = engine

    async def run_rule_ab_test(self, target_word: str, instruction: str) -> Dict[str, Any]:
        # 1. テスト用の文脈/段落の生成 (またはデフォルトのサンプル文脈)
        sample_context = "彼はその光景を見て驚愕した。あまりの出来事に、言葉を失って立ち尽くすしかなかった。"
        if target_word.lower() not in sample_context:
            sample_context = f"敵の軍勢が一瞬で城壁を蹂躙した。人々は絶望し、静寂が広がった。その圧倒的な光景に、誰もが驚愕し、あるいは歓喜の声をあげた。キーワード: {target_word}"

        # 2. パターンA (ルール適用前 / 単純なプレーンテキスト)
        # ここでは何もしない
        text_a = sample_context

        # 3. パターンB (新ルール適用 / LLMによるリファイン・プロンプト適用)
        prompt_b = (
            f"あなたは優秀な小説の校正者・編集者です。\n"
            f"以下の小説の段落には、陳腐な表現や禁止されている言葉が含まれています。\n"
            f"指示に従って、文脈やキャラクターの個性を保ちながら、この段落をより豊かで自然な描写にリライトしてください。\n\n"
            f"【禁止ワードと修正指示】:\n- 「{target_word}」: {instruction}\n"
            f"【元の段落】:\n{sample_context}\n\n"
            f"【書き直し後の段落のみを出力してください。余計な挨拶や解説、前後の記号は一切含めないでください】"
        )

        text_b = sample_context
        try:
            res_b = await self.engine._generate_text(ProjectContext.get_setting("model_lightweight"), prompt_b)
            if res_b.success and res_b.story_content:
                text_b = res_b.story_content.strip()
        except Exception as e:
            logger.error(f"Failed to generate Version B for A/B test: {e}")

        # 4. 評価用LLMによる比較・採点
        eval_prompt = (
            f"あなたはプロの文芸評論家・編集者です。\n"
            f"以下の小説の段落A（ルール適用前）と段落B（新ルール適用後）を比較し、客観的に評価してください。\n\n"
            f"【評価基準】:\n"
            f"1. 描写の具体性（Show, Don't Tell に従っているか。抽象的な感情名詞に頼らず、生理反応や情景で表現できているか）\n"
            f"2. 文脈の自然さ・読みやすさ\n"
            f"3. 表現の独創性とバリエーション\n\n"
            f"【評価対象のテキスト】:\n"
            f"■ 元の表現キーワード: {target_word}\n"
            f"■ ルール指示: {instruction}\n\n"
            f"■ 段落A:\n{text_a}\n\n"
            f"■ 段落B:\n{text_b}\n\n"
            f"【出力フォーマット（厳密に以下のJSON形式で返してください。他のテキストは含めないでください）】:\n"
            f"{{\n"
            f"  \"score_a\": 70,\n"
            f"  \"score_b\": 90,\n"
            f"  \"winner\": \"B\",\n"
            f"  \"rationale\": \"段落Bは抽象語を使わず、具体的な情景や生理反応で表現されており、描写の具体性が劇的に向上しているため。\"\n"
            f"}}"
        )

        try:
            from pydantic import BaseModel, Field
            class ABEvalSchema(BaseModel):
                score_a: int = Field(description="段落Aのスコア (0-100)")
                score_b: int = Field(description="段落Bのスコア (0-100)")
                winner: str = Field(description="どちらが優れているか ('A' または 'B')")
                rationale: str = Field(description="評価の理由")

            res_eval = await self.engine.llm.generate_json(ProjectContext.get_setting("model_planning"), eval_prompt, response_schema=ABEvalSchema)
            if res_eval.success and res_eval.metadata:
                eval_data = res_eval.metadata
                return {
                    "text_a": text_a,
                    "text_b": text_b,
                    "score_a": eval_data.get("score_a", 50),
                    "score_b": eval_data.get("score_b", 50),
                    "winner": eval_data.get("winner", "Equal"),
                    "rationale": eval_data.get("rationale", "")
                }
        except Exception as e:
            logger.error(f"Error during A/B test evaluation: {e}")

        # エラー時のフォールバック戻り値
        return {
            "text_a": text_a,
            "text_b": text_b,
            "score_a": 50,
            "score_b": 50,
            "winner": "Equal",
            "rationale": "評価中にエラーが発生しました。"
        }
