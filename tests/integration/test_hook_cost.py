"""
tests/integration/test_hook_cost.py

機能2（フック診断）と機能3（コスト分析）の統合テスト。
実 SQLite UnitOfWork に対して、各サービス・リポジトリの操作を検証する。
"""
import pytest

from src.services.cost_analytics import check_budget_alert, estimate_cost_usd
from src.services.hook_diagnoser import HOOK_THRESHOLD, HookDiagnoser


@pytest.mark.asyncio
async def test_hook_diagnoser_flags_weak_chapters(real_uow):
    """フックスコアが閾値未満の章を弱いと判定する。"""
    chapters = [
        {"ep_num": 1, "title": "A", "content": "ただ平坦に物語が進んだ。特に問題はなかった。" * 20},
        {"ep_num": 2, "title": "B", "content": "彼は去っていった。一体なぜだろうか？ 本当に終わったのだろうか？ " + ("物語はまだ続く。" * 20)},
    ]
    diag = await HookDiagnoser().diagnose(chapters)
    assert diag[0]["is_weak"] is True
    assert diag[1]["is_weak"] is False
    assert HOOK_THRESHOLD > 0


@pytest.mark.asyncio
async def test_cost_estimate_and_budget(real_uow):
    """トークンから推定コストを算出し、予算超過を検知する。"""
    cost = estimate_cost_usd("writing", 1_000_000, 500_000)
    assert cost > 0
    alert = check_budget_alert(cost, 0.01)
    assert alert["exceeded"] is True
    alert2 = check_budget_alert(cost, 100.0)
    assert alert2["exceeded"] is False


@pytest.mark.asyncio
async def test_cost_repository_persist_and_aggregate(real_uow):
    """CostRepository が記録を保存し、集計する。"""
    from src.services.cost_analytics import estimate_cost_usd

    async with real_uow as uow:
        book_id = await uow.books.create_book("T", "G", "C", "S", 10, {}, {})
        est = estimate_cost_usd("writing", 1_000_000, 500_000)
        await uow.cost.add(
            book_id=book_id, branch_id=1, task_type="writing",
            input_tokens=1_000_000, output_tokens=500_000,
            total_tokens=1_500_000, est_cost_usd=est, ep_num=1,
        )
        await uow.cost.add(
            book_id=book_id, branch_id=1, task_type="planning",
            input_tokens=100_000, output_tokens=50_000,
            total_tokens=150_000, est_cost_usd=0.0, ep_num=None,
        )
        agg = await uow.cost.aggregate(book_id)
        assert agg["record_count"] == 2
        assert agg["total_tokens"] == 1_650_000
        assert "writing" in agg["by_task"]
        assert len(agg["timeseries"]) == 2
