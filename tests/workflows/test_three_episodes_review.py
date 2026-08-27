"""
tests/workflows/test_three_episodes_review.py

3話（target_start_ep=1, target_end_ep=3）のマスター生成パイプラインを走らせ、
実際に発生する LLM API コール数とフェーズの「動き（順序）」を検証する。

パイプライン構成:
  MasterGraph
    └ plot_phase   (PlotGraph: 初期生成 → 評価 → [改善ループ] → 終了)   ※本全体で1回
    └ writing_phase(WritingGraph ×N話: 文脈 → 本文生成 → 自己監査 → [再生成ループ])
    └ review_phase (ReviewGraph ×N話: テンポ分析 → キャラ整合 → 総合合成)

各ノードの API コール種別:
  - PlotGraph
      generate_initial_plot_node : generate_json (planning)        ×1
      evaluate_plot_node         : generate_json (audit)           ×1 (+ループごとに+2)
      refine_plot_node           : generate_json (planning)        ×1 (ループ時のみ)
  - WritingGraph (話ごと)
      build_context_node         : 外部APIなし（DB/RAG取得）        ×0
      generate_draft_node        : generate_text (writing)         ×1 (+ループごとに+1)
      self_audit_node            : generate_json (audit)           ×1 (+ループごとに+1)
  - ReviewGraph (話ごと)
      analyze_pacing_node        : generate_json (audit)           ×1
      check_character_consistency: generate_json (audit)           ×1
      propose_edits_node         : 外部APIなし（集約のみ）          ×0
"""

import re
import unittest
from unittest.mock import AsyncMock, MagicMock

from src.backend.workflows.graphs.master_graph import compile_master_graph
from src.backend.workflows.state import MasterGraphState
from src.core.llm.providers.base import LLMResponse


def _json(content: str, **kw) -> LLMResponse:
    return LLMResponse(content=content, success=True, **kw)


class CountingLLMProvider:
    """generate_json / generate_text の呼び出し回数と順序を記録する疑似プロバイダー。

    json_queue / text_queue に「呼ばれる順」でレスポンスを積んでおき、
    呼ばれるたびにポップして返す。枯渇時は AssertionError になる。
    """

    def __init__(self, json_queue, text_queue):
        self._json_queue = list(json_queue)
        self._text_queue = list(text_queue)
        self.json_calls = 0
        self.text_calls = 0
        self.api_call_count = 0
        self.sequence = []  # 呼び出し順の記録

    async def generate_json(self, model_name, prompt, **kwargs):
        self.json_calls += 1
        self.api_call_count += 1
        resp = self._json_queue.pop(0)
        self.sequence.append({"kind": "json", "model": model_name, "prompt": prompt})
        return resp

    async def generate_text(self, model_name, prompt, **kwargs):
        self.text_calls += 1
        self.api_call_count += 1
        resp = self._text_queue.pop(0)
        self.sequence.append({"kind": "text", "model": model_name, "prompt": prompt})
        return resp

    def assert_exhausted(self):
        assert not self._json_queue, f"unused json responses: {len(self._json_queue)}"
        assert not self._text_queue, f"unused text responses: {len(self._text_queue)}"


# 執筆ノードは本文が MIN_DRAFT_CHARS (1500) 未満だと監査をスキップして再生成ループに入るため、
# モックの本文は現実に即した十分な長さ（>=1500文字）を用意する。
LONG_DRAFT = (
    "静寂を破るように雷鳴が轟いた。主人公の手のひらに未知の光が集い、"
    "世界を変える力が目覚めようとしていた。彼は深呼吸をし、決意を胸に歩み出す。"
) * 25


# ---- レスポンス定型 ----
PLOT_INITIAL_OK = _json(
    '[{"ep_num":1,"title":"覚醒","summary":"能力覚醒","next_hook":"敵の影"},'
    '{"ep_num":2,"title":"邂逅","summary":"仲間と出会う","next_hook":"襲撃"},'
    '{"ep_num":3,"title":"決意","summary":"戦う決意","next_hook":"開戦"}]'
)
PLOT_EVAL_OK = _json('{"is_approved": true, "score": 0.95, "issues": [], "suggestions": []}')
PLOT_EVAL_NG = _json('{"is_approved": false, "score": 0.55, "issues": [{"category":"Pacing","description":"だれる"}], "suggestions": ["テンポを修正"]}')
PLOT_REFINE = _json(
    '[{"ep_num":1,"title":"覚醒(改)","summary":"能力覚醒","next_hook":"敵の影"},'
    '{"ep_num":2,"title":"邂逅(改)","summary":"仲間と出会う","next_hook":"襲撃"},'
    '{"ep_num":3,"title":"決意(改)","summary":"戦う決意","next_hook":"開戦"}]'
)
WRITING_AUDIT_OK = _json('{"is_integrity_ok": true, "is_causal_ok": true, "causal_reason": "ok", "score": 0.90, "failures": []}')
WRITING_AUDIT_NG = _json('{"is_integrity_ok": false, "is_causal_ok": true, "causal_reason": "口調ブレ", "score": 0.60, "failures": [{"category":"Character","description":"口調が崩れている"}]}')
REVIEW_PACING_OK = _json('{"pacing_score": 0.88, "is_pacing_ok": true, "issues": [], "recommendations": []}')
REVIEW_PACING_NG = _json('{"pacing_score": 0.40, "is_pacing_ok": false, "issues": ["テンポが遅い"], "recommendations": ["テンポ改善"]}')
REVIEW_CHAR_OK = _json('{"character_score": 0.92, "is_character_ok": true, "inconsistencies": []}')


def _phase_of(prompt: str) -> str:
    """プロンプト内容からどのノードかを判定し、ラベルを返す。"""
    if "編集部から以下の改善フィードバック" in prompt:
        return "plot_refine"
    if "熟練プロットプランナー" in prompt:
        return "plot_initial"
    if "is_approved" in prompt:
        return "plot_eval"
    if "is_integrity_ok" in prompt:
        return "writing_audit"
    if "pacing_score" in prompt:
        return "review_pacing"
    if "character_score" in prompt:
        return "review_char"
    if "執筆してください" in prompt or "前回の推敲指摘" in prompt:
        return "writing_draft"
    return "unknown"


def _ep_of(prompt: str):
    m = re.search(r"第(\d+)話", prompt)
    return int(m.group(1)) if m else None


class TestThreeEpisodesReview(unittest.IsolatedAsyncioTestCase):

    async def _run(self, provider, mode="full_pipeline"):
        mock_reporter = MagicMock()
        mock_reporter.report = AsyncMock()
        app = compile_master_graph(llm_provider=provider, reporter=mock_reporter)
        initial_state: MasterGraphState = {
            "task_id": "review-task",
            "mode": mode,
            "book_id": 1,
            "branch_id": 1,
            "target_start_ep": 1,
            "target_end_ep": 3,
            "metadata": {"genre": "バトルファンタジー", "theme": "覚醒"},
        }
        return await app.ainvoke(initial_state)

    async def test_best_case_api_call_count_and_order(self):
        """全承認（ループなし）の場合: 3話で API コールは 14 回。"""
        provider = CountingLLMProvider(
            json_queue=[
                PLOT_INITIAL_OK,   # plot_initial
                PLOT_EVAL_OK,      # plot_eval
                WRITING_AUDIT_OK,  # writing ep1 audit
                WRITING_AUDIT_OK,  # writing ep2 audit
                WRITING_AUDIT_OK,  # writing ep3 audit
                REVIEW_PACING_OK,  # review ep1 pacing
                REVIEW_CHAR_OK,    # review ep1 char
                REVIEW_PACING_OK,  # review ep2 pacing
                REVIEW_CHAR_OK,    # review ep2 char
                REVIEW_PACING_OK,  # review ep3 pacing
                REVIEW_CHAR_OK,    # review ep3 char
            ],
            text_queue=[
                _json(LONG_DRAFT),  # writing ep1 draft
                _json(LONG_DRAFT),  # writing ep2 draft
                _json(LONG_DRAFT),  # writing ep3 draft
            ],
        )

        result = await self._run(provider)

        # --- API コール数の検証 ---
        self.assertEqual(provider.json_calls, 11)
        self.assertEqual(provider.text_calls, 3)
        self.assertEqual(provider.api_call_count, 14)
        self.assertEqual(provider.json_calls + provider.text_calls, 14)
        provider.assert_exhausted()

        # --- 結果構造の検証 ---
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["overall_progress"], 1.0)
        self.assertEqual(len(result["writing_results"]), 3)
        self.assertEqual(len(result["review_results"]), 3)
        self.assertIn("bible_state", result)
        self.assertIn("ep_1", result["bible_state"])
        self.assertIn("ep_2", result["bible_state"])
        self.assertIn("ep_3", result["bible_state"])

        # --- 動き（フェーズの順序）の検証 ---
        labels = [(_phase_of(s["prompt"]), _ep_of(s["prompt"])) for s in provider.sequence]
        # 先頭は plot フェーズ（ep なし）
        self.assertIn(labels[0][0], ("plot_initial",))
        self.assertEqual(labels[1][0], "plot_eval")

        # writing は 1→2→3 の順で draft/audit が交互に来る
        writing_labels = [l for l in labels if l[0] in ("writing_draft", "writing_audit")]
        self.assertEqual(
            [(l[0], l[1]) for l in writing_labels],
            [("writing_draft", 1), ("writing_audit", 1),
             ("writing_draft", 2), ("writing_audit", 2),
             ("writing_draft", 3), ("writing_audit", 3)],
        )

        # review は 1→2→3 で pacing→char が交互
        review_labels = [l for l in labels if l[0] in ("review_pacing", "review_char")]
        self.assertEqual(
            [(l[0], l[1]) for l in review_labels],
            [("review_pacing", 1), ("review_char", 1),
             ("review_pacing", 2), ("review_char", 2),
             ("review_pacing", 3), ("review_char", 3)],
        )

    async def test_worst_case_api_call_count(self):
        """全ループ最大化（plot 1回リファイン + writing 各話1回再生成）の場合: 3話で API コールは 22 回。"""
        provider = CountingLLMProvider(
            json_queue=[
                PLOT_INITIAL_OK,   # plot_initial
                PLOT_EVAL_NG,      # plot_eval (不合格 → refine)
                PLOT_REFINE,       # plot_refine
                PLOT_EVAL_OK,      # plot_eval (再評価 → 合格)
                # writing ep1: audit NG → draft → audit OK
                WRITING_AUDIT_NG, WRITING_AUDIT_OK,
                # writing ep2
                WRITING_AUDIT_NG, WRITING_AUDIT_OK,
                # writing ep3
                WRITING_AUDIT_NG, WRITING_AUDIT_OK,
                # review x3
                REVIEW_PACING_OK, REVIEW_CHAR_OK,
                REVIEW_PACING_OK, REVIEW_CHAR_OK,
                REVIEW_PACING_OK, REVIEW_CHAR_OK,
            ],
            text_queue=[
                _json(LONG_DRAFT), _json(LONG_DRAFT),
                _json(LONG_DRAFT), _json(LONG_DRAFT),
                _json(LONG_DRAFT), _json(LONG_DRAFT),
            ],
        )

        result = await self._run(provider)

        # plot: 4, writing: 3話 × 4 (=12), review: 3話 × 2 (=6) → 22
        self.assertEqual(provider.json_calls, 4 + 3 * 2 + 3 * 2)   # 16
        self.assertEqual(provider.text_calls, 3 * 2)                # 6
        self.assertEqual(provider.api_call_count, 22)
        self.assertEqual(provider.json_calls + provider.text_calls, 22)
        provider.assert_exhausted()
        self.assertEqual(result["status"], "completed")

    async def test_revision_loop_triggers_for_flagged_episode(self):
        """第2話のみ Review で要修正と判定された場合:
        基本14コール + 第2話再執筆(draft:1, audit:1) + 第2話再レビュー(pacing:1, char:1) = 18コール。
        """
        provider = CountingLLMProvider(
            json_queue=[
                PLOT_INITIAL_OK,   # plot_initial
                PLOT_EVAL_OK,      # plot_eval
                WRITING_AUDIT_OK,  # writing ep1 audit
                WRITING_AUDIT_OK,  # writing ep2 audit
                WRITING_AUDIT_OK,  # writing ep3 audit
                REVIEW_PACING_OK,  # review ep1 pacing
                REVIEW_CHAR_OK,    # review ep1 char
                REVIEW_PACING_NG,  # review ep2 pacing (要修正フラグ発生)
                REVIEW_CHAR_OK,    # review ep2 char
                REVIEW_PACING_OK,  # review ep3 pacing
                REVIEW_CHAR_OK,    # review ep3 char
                # --- リバイスフェーズ（第2話のみ） ---
                WRITING_AUDIT_OK,  # writing ep2 re-audit
                REVIEW_PACING_OK,  # review ep2 re-pacing (合格)
                REVIEW_CHAR_OK,    # review ep2 re-char (合格)
            ],
            text_queue=[
                _json(LONG_DRAFT),  # writing ep1 draft
                _json(LONG_DRAFT),  # writing ep2 draft
                _json(LONG_DRAFT),  # writing ep3 draft
                # --- リバイスフェーズ（第2話のみ） ---
                _json(LONG_DRAFT),  # writing ep2 re-draft
            ],
        )

        result = await self._run(provider)

        # 14 + 4 = 18 calls
        self.assertEqual(provider.json_calls, 14)
        self.assertEqual(provider.text_calls, 4)
        self.assertEqual(provider.api_call_count, 18)
        provider.assert_exhausted()

        # 結果構造の検証
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["review_summary"]["requires_revision_count"], 0)
        self.assertTrue(result["quality_metrics"].get("revision_converged", False))


if __name__ == "__main__":
    unittest.main()
