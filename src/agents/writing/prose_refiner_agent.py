from __future__ import annotations
import time
from typing import Optional
from src.models.prose_refinement import ProseRefineResult, RefinementDetail
from src.services.prose.few_shot_selector import FewShotSelector
from src.services.llm_service import LLMService
import logging

logger = logging.getLogger(__name__)


class ProseRefinerAgent:
    """軽量LLM（Gemini Flash / GPT-4o-mini）を使用した文脈保持型推敲エージェント"""

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        few_shot_selector: Optional[FewShotSelector] = None
    ):
        self.llm_service = llm_service or LLMService()
        self.few_shot_selector = few_shot_selector or FewShotSelector()

    async def refine(
        self,
        draft_text: str,
        genre: str = "fantasy_action",
        style_intensity: str = "balanced",
        scene_type: str | None = None,
    ) -> ProseRefineResult:
        """
        テキストを推敲して文体を向上させる

        Args:
            draft_text: 推敲対象のテキスト
            genre: ジャンル (fantasy_action, villainess_court, dungeon_modern等)
            style_intensity: 推敲強度 (mild, balanced, literary)
            scene_type: シーンタイプ (action, dialogue, internal_monologue等)

        Returns:
            推敲結果
        """
        start_time = time.time()

        # 入力チェック
        if not draft_text or not draft_text.strip():
            return ProseRefineResult(
                refined_text=draft_text,
                total_fixes_count=0,
                latency_ms=0.0
            )

        try:
            # シーンタイプの判定
            detected_scene = scene_type or self._detect_scene_type(draft_text)

            # Few-shot選択
            few_shots = self.few_shot_selector.select_few_shots(
                genre=genre,
                scene_type=detected_scene,
                max_examples=2
            )

            # プロンプト構築
            prompt = self._build_prompt(draft_text, genre, detected_scene, few_shots, style_intensity)

            # LLM呼び出し（軽量モデル使用）
            refined_text = await self._call_lightweight_llm(prompt)

            # 結果のパースと修正箇所の抽出
            modifications = self._extract_modifications(draft_text, refined_text)

            latency_ms = (time.time() - start_time) * 1000

            result = ProseRefineResult(
                refined_text=refined_text,
                modifications=modifications,
                total_fixes_count=len(modifications),
                latency_ms=latency_ms
            )

            logger.info(
                "prose_refinement_completed: len=%d->%d, fixes=%d, genre=%s",
                len(draft_text),
                len(refined_text),
                len(modifications),
                genre,
            )

            return result

        except Exception as e:
            logger.error("prose_refinement_failed: %s, genre=%s", e, genre)
            # エラー時は原文を返す
            return ProseRefineResult(
                refined_text=draft_text,
                total_fixes_count=0,
                latency_ms=(time.time() - start_time) * 1000
            )

    def _detect_scene_type(self, text: str) -> str:
        """テキストからシーンタイプを簡易検出"""
        text_lower = text.lower()

        # アクションシーンのキーワード
        action_keywords = ["走", "撃", "斬", "爆発", "闘", "戦", "攻撃", "防御", "逃げ", "追跡"]
        # 会話シーンのキーワード
        dialogue_keywords = ["言", "話", "会", " conversation", "\"", "？", "！"]
        # 内部独白のキーワード
        internal_keywords = ["感", "思", "考", "思い", "悩", "喜", "怒", "哀", "楽"]

        action_count = sum(1 for k in action_keywords if k in text_lower)
        dialogue_count = sum(1 for k in dialogue_keywords if k in text_lower)
        internal_count = sum(1 for k in internal_keywords if k in text_lower)

        if action_count >= dialogue_count and action_count >= internal_count:
            return "action"
        elif dialogue_count >= internal_count:
            return "dialogue"
        else:
            return "internal_monologue"

    def _build_prompt(
        self,
        draft_text: str,
        genre: str,
        scene_type: str,
        few_shots: list,
        style_intensity: str
    ) -> str:
        """推敲用プロンプトを構築"""
        # 実際の実装ではJinja2テンプレートを使用するが、ここでは簡易版
        intensity_guide = {
            "mild": "軽微な表現の改善にとどめ、原文のトーンを最大限保持してください。",
            "balanced": "バランスの取れた推敲を行い、読みやすさと表現の豊かさを向上させてください。",
            "literary": "文学的な表現へと昇華させ、プロ作家レベルの文体に仕上げてください。"
        }

        few_shots_text = ""
        for i, example in enumerate(few_shots, 1):
            few_shots_text += f"""
例{i}:
修正前: "{example['before']}"
修正後: "{example['after']}"
"""

        prompt = f"""# スマートプロセ精製指示

以下のテキストを、文意とストーリー進行を100%維持したまま、プロ作家級の文体に推敲してください。

## 基本ルール
1. 「〜と感じた」「息を呑んだ」「静寂が支配した」等の定型句を、五感と具体的な身体の動きに直せ。
2. 主語・述語の係り受け、接続詞を絶対に壊すな。
3. 会話文のセリフそのものは改変せず、ト書き（地の文）のテンポを整えよ。
4. 感情の説明ではなく、身体の反応・環境の変化・行動の描写で示せ。
5. {intensity_guide.get(style_intensity, intensity_guide['balanced'])}

## Few-Shot例示（ジャンル: {genre}, シーン: {scene_type}）
{few_shots_text}

## 入力テキスト
{draft_text}

## 出力形式
推敲後のテキストのみを出力してください。説明文やメタデータは一切含めないでください。
"""
        return prompt

    async def _call_lightweight_llm(self, prompt: str) -> str:
        """軽量LLM（Gemini Flash / GPT-4o-mini）を呼び出す"""
        try:
            if hasattr(self.llm_service, "adapter") and self.llm_service.adapter is not None:
                response = await self.llm_service.adapter.generate_text(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=2000,
                )
            elif hasattr(self.llm_service, "generate_text"):
                response = await self.llm_service.generate_text(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=2000,
                )
            elif hasattr(self.llm_service, "generate"):
                response = await self.llm_service.generate(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=2000,
                    model="gemini-2.0-flash"
                )
            else:
                response = prompt

            if hasattr(response, "text"):
                return str(response.text).strip()
            return str(response).strip()
        except Exception as e:
            logger.warning("llm_call_failed: %s", e)
            raise

    def _extract_modifications(
        self,
        original_text: str,
        refined_text: str
    ) -> list[RefinementDetail]:
        """元テキストと推敲テキストから修正箇所を抽出"""
        modifications = []

        # 簡易的な差分検出（実際の実装ではdifflibや専門のライブラリを使用）
        if original_text == refined_text:
            return modifications

        # ここでは非常に簡易的な実装を行う
        # 実際のプロジェクトでは、より精密な差分検出と理由付けが必要

        # 簡単な置換検出（実際はもっと高度に行うべき）
        sentences_orig = [s.strip() for s in original_text.split('。') if s.strip()]
        sentences_refined = [s.strip() for s in refined_text.split('。') if s.strip()]

        # 文数が異なる場合は、全体を一つの修正として扱う
        if len(sentences_orig) != len(sentences_refined):
            modifications.append(RefinementDetail(
                original_phrase=original_text[:100] + ("..." if len(original_text) > 100 else ""),
                refined_phrase=refined_text[:100] + ("..." if len(refined_text) > 100 else ""),
                reason="全体的な文体改善と構成調整"
            ))
        else:
            # 文数が同じ場合は、対応する文を比較
            for i, (orig_sent, refined_sent) in enumerate(zip(sentences_orig, sentences_refined)):
                if orig_sent != refined_sent:
                    modifications.append(RefinementDetail(
                        original_phrase=orig_sent,
                        refined_phrase=refined_sent,
                        reason=f"文{i+1}の表現改善（定型句の五感描写への変換等）"
                    ))

        return modifications
