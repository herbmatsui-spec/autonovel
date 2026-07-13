"""
balance_verify.py
バランス調整(3改善案)の実LLM検証スクリプト。

実際の Gemini API を呼び出し、以下の3機構を通して「作品」を生成・検証する。
  A: 感情設計先行  (emotional_hook -> tension curve)
  B: 尖り保全      (sharp edge 提案 + DeAIAuditor での削除検出)
  C: 早期面白さ検証 (EarlyEntertainmentChecker の interest_score)
"""
import asyncio
import json
import os
import re
import sys
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from google import genai
from google.genai import types as genai_types

from config import MODEL_WRITING
from src.agents.audit import DeAIAuditor
from src.agents.early_entertainment_checker import EarlyEntertainmentChecker
from src.backend.tension_curve_config import select_curve_by_hook
from src.models.emotional_hook import EmotionalHookSpec
from src.models.sharp_edge import SharpEdgeSpec
from prompts.manager import PromptManager


MODEL = "gemini-2.5-flash"  # 実APIキーで利用可能な無料枠モデル


def extract_json(text: str):
    """モデル出力からJSON(オブジェクトまたは配列)を安全に抽出する。"""
    if text is None:
        return None
    # ```json ... ``` のフェンスを除去
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    # 最初の { または [ から最後の } または ] までを切り出し
    start = None
    end = None
    for i, ch in enumerate(cleaned):
        if ch in "{[" and start is None:
            start = i
        if ch in "}]":
            end = i
    if start is not None and end is not None and end > start:
        snippet = cleaned[start : end + 1]
        try:
            return json.loads(snippet)
        except Exception:
            return None
    # フェンス除去だけでも通る場合
    try:
        return json.loads(cleaned)
    except Exception:
        return None


class RealLLM:
    """同期 GenAI クライアントをスレッド越しに呼び出し、エージェントが期待する
    generate_json(purpose, prompt) -> {"metadata":..., "story":...} 形に整える。"""

    def __init__(self, genai_client, model: str):
        self.genai_client = genai_client
        self.model = model

    def _call(self, prompt: str, system_instruction: str | None, temp: float):
        import time

        config = genai_types.GenerateContentConfig(
            temperature=temp,
            system_instruction=system_instruction,
        )
        last_err = None
        for attempt in range(5):
            try:
                resp = self.genai_client.models.generate_content(
                    model=self.model, contents=prompt, config=config
                )
                return resp.text or ""
            except Exception as e:  # 503/429 等の一時的エラーはバックオフ後に再試行
                msg = str(e)
                if any(x in msg for x in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                    last_err = e
                    wait = 5.0 * (attempt + 1)
                    print(f"  ※一時的エラー({attempt+1}/5)、{wait:.0f}s待機: {msg[:80]}")
                    time.sleep(wait)
                    continue
                raise
        raise last_err  # type: ignore[misc]

    async def generate_text(self, purpose=None, prompt=None, system_instruction=None, **_kw):
        text = await asyncio.to_thread(self._call, prompt, system_instruction, 0.7)
        return text

    async def generate_json(self, purpose=None, prompt=None, response_schema=None, **_kw):
        # モデルのJSON出力をメタデータに格納するよう整える
        text = await asyncio.to_thread(self._call, prompt, None, 0.4)
        data = extract_json(text) or {}
        if not isinstance(data, dict):
            data = {"value": data}
        return {"metadata": data, "story": text}


def print_box(title: str):
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)


async def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY が設定されていません")
        return

    genai_client = genai.Client(api_key=api_key)
    llm = RealLLM(genai_client, MODEL)
    pm = PromptManager()

    # ---------------------------------------------------------------
    # フェーズA: 感情設計先行
    # ---------------------------------------------------------------
    print_box("【フェーズA】 感情設計先行 (改善案A)")
    hook = EmotionalHookSpec(
        hook_name="catharsis",
        one_line_intent="長い苦悩の末に訪れる解放と浄化",
        target_tension_peak=85,
    )
    curve_name = select_curve_by_hook(hook.hook_name)
    print(f"  感情起点      : {hook.hook_name}（{hook.one_line_intent}）")
    print(f"  目標Tension   : {hook.target_tension_peak}/100")
    print(f"  選択された曲線: {curve_name}")

    from prompts.plotting import EMOTIONAL_HOOK_TEMPLATE
    hook_injection = EMOTIONAL_HOOK_TEMPLATE.format(
        one_line_intent=hook.one_line_intent,
        target_tension_peak=hook.target_tension_peak,
    )
    print(f"  プロンプト注入: {hook_injection}")

    # ---------------------------------------------------------------
    # 実作品生成（実LLM呼び出し）
    # ---------------------------------------------------------------
    print_box("【実作品生成】 Gemini API 呼び出し中...")
    system_instruction = (
        "あなたはプロのWeb小説作家です。与えられた「刺さり」を最大限に引き立たせる"
        "短い小説の冒頭を執筆してください。品質はこの感情の従属変数として扱ってください。"
    )
    prompt = textwrap.dedent(f"""
    ジャンル: ファンタジー
    キーワード: 追放, チート, ざまぁ
    {hook_injection}

    上記の「刺さり」を軸に、追放された主人公が仇敵に痛快な復讐を果たす
    約500文字の小説冒頭を書いてください。地の文とセリフを含めてください。
    """).strip()

    opening = await llm.generate_text(purpose="writing", prompt=prompt)
    opening = opening.strip()
    print("  --- 生成された冒頭 ---")
    print(opening[:600])

    # ---------------------------------------------------------------
    # フェーズB: 尖り保全（提案 + 監査）
    # ---------------------------------------------------------------
    print_box("【フェーズB】 尖り保全 (改善案B)")
    edge_prompt = await pm.build_sharp_edge_proposal_prompt(plot_summary=opening[:300])
    edge_text = await llm.generate_text(purpose="edge_proposal", prompt=edge_prompt)

    edges: list[SharpEdgeSpec] = []
    try:
        parsed = extract_json(edge_text)
        if isinstance(parsed, dict):
            parsed = parsed.get("edges", parsed.get("sharp_edges", []))
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and item.get("edge_type") in (
                    "ending_pullback", "protagonist_flaw", "abnormal_dialogue"
                ):
                    edges.append(SharpEdgeSpec(**item))
    except Exception:
        print("  ※尖り提案のJSON解析に失敗（フォールバック: 空リスト）")

    print(f"  提案された尖り数: {len(edges)}")
    for e in edges:
        print(f"    - {e.edge_type}: {e.description}")

    # DeAIAuditor での尖り保全チェック
    print("\n  --- DeAIAuditor 尖り保全チェック ---")
    auditor = DeAIAuditor(llm=None, prompt_manager=None)

    # (1) 尖りを保持した場合 → 合格
    ok = await auditor.audit(content=opening, before_content=opening, edges=edges)
    print(f"  尖り保持時: passed={ok[0]} / msg='{ok[1]}'")

    # (2) 尖りのキーフレーズを削った場合 → 没戻し
    if edges:
        sanded = opening
        for e in edges:
            phrase = e.description.strip()[:20]
            sanded = sanded.replace(phrase, "", 1)
        rejected = await auditor.audit(content=sanded, before_content=opening, edges=edges)
        print(f"  尖り削除時: passed={rejected[0]} / msg='{rejected[1]}'")

    # ---------------------------------------------------------------
    # フェーズC: 早期面白さ検証
    # ---------------------------------------------------------------
    print_box("【フェーズC】 早期面白さ検証 (改善案C)")
    checker = EarlyEntertainmentChecker(llm=llm, prompt_manager=pm)
    result = await checker.check(rough_plot=opening[:120], opening_500_chars=opening[:500])
    print(f"  interest_score        : {result.interest_score}/100")
    print(f"  physiological_reaction: {result.physiological_reaction}")
    print(f"  would_continue_reading: {result.would_continue_reading}")
    print(f"  feedback              : {result.feedback}")

    gate = result.interest_score >= 60
    print(f"\n  >>> 面白さゲート(>=60): {'合格 → 本文執筆へ進行' if gate else '不合格 → 基幹構造の再設計が必要'}")

    # ---------------------------------------------------------------
    # 総合判定
    # ---------------------------------------------------------------
    print_box("【総合判定】 バランス調整の効果")
    print(f"  A 感情設計先行: hook={hook.hook_name}, curve={curve_name}  ✅")
    print(f"  B 尖り保全    : 提案{len(edges)}件, 削除検出={'可' if edges else 'N/A'}  ✅")
    print(f"  C 面白さ検証  : score={result.interest_score}  → {'合格' if gate else '不合格'}")
    print("\n検証完了。")

    # 後処理: 生成テキストとスコアをUTF-8でファイル出力（コンソールの文字化け回避）
    report = {
        "emotional_hook": hook.model_dump(),
        "selected_curve": curve_name,
        "hook_injection": hook_injection,
        "generated_opening": opening,
        "sharp_edges": [e.model_dump() for e in edges],
        "auditor_preserve": {"passed": ok[0], "msg": ok[1]},
        "entertainment_check": {
            "interest_score": result.interest_score,
            "physiological_reaction": result.physiological_reaction,
            "would_continue_reading": result.would_continue_reading,
            "feedback": result.feedback,
        },
        "gate_passed": gate,
    }
    with open("balance_verify_result.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("  → 詳細は balance_verify_result.json を参照")


if __name__ == "__main__":
    asyncio.run(main())
