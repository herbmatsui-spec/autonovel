"""
tests/integration/test_eventbus_flow.py - ステップ 33: Phase B ドメインイベントバス統合テスト
(WRITTEN publish → 購読更新 → aggregate / EVALUATED → MasterGraph revise判定)
"""

import pytest
from src.backend.workflows.narrative_state import NarrativeState
from src.backend.workflows.graphs.master_graph import should_revise_writing
from src.shared.domain_event_bus import (
    DomainEvent,
    DomainEventBus,
    NarrativeEventType,
)
from src.prototype.adapters import (
    tension_sub,
    affinity_sub,
    continuity_sub,
    narrative_sub,
    erotic_sub,
)
from src.prototype.aggregator import aggregate


@pytest.fixture(autouse=True)
def override_settings():
    """Integration conftest の Docker/Testcontainers を回避"""
    yield


@pytest.mark.asyncio
async def test_domain_event_bus_flow_integration():
    """イベント発行から集約、MasterGraph リバイス判定までの end-to-end フロー検証"""
    bus = DomainEventBus()
    hub = NarrativeState(book_id=1, branch_id=1)

    # 1. 各種サブスクライバの登録
    tension_sub.register(bus, hub)
    affinity_sub.register(bus, hub)
    continuity_sub.register(bus, hub)
    narrative_sub.register(bus, hub)
    erotic_sub.register(bus, hub)

    # EVALUATED イベント捕捉リスナー
    evaluated_list = []

    async def on_evaluated(ev: DomainEvent):
        evaluated_list.append(ev)

    bus.subscribe(NarrativeEventType.EPISODE_EVALUATED, on_evaluated)

    # 2. 第1話執筆完了イベントを発行
    written_ev1 = DomainEvent(
        type=NarrativeEventType.EPISODE_WRITTEN,
        payload={
            "text": "凛とセリアは光の石を護るため回廊へ急いだ。",
            "scene": {"ep": 1, "episode_num": 1, "text": "凛とセリア"},
            "tension": 0.75,
        },
        book_id=1,
        ep=1,
    )
    await aggregate(bus, hub, written_ev1)

    assert len(evaluated_list) == 1
    assert evaluated_list[0].ep == 1
    assert 1 in hub.episodes
    assert hub.episodes[1]["tension"] == 0.75

    # 3. 第2話で連続性違反を含むイベントを発行
    # (例: continuity_violations に違反を追加)
    hub.continuity_violations.append({
        "ep": 2,
        "field": "symbol",
        "msg": "光の石の輝きが消失している矛盾",
    })

    written_ev2 = DomainEvent(
        type=NarrativeEventType.EPISODE_WRITTEN,
        payload={
            "text": "闇結社が光脈を断った。",
            "scene": {"ep": 2, "episode_num": 2, "text": "闇結社"},
            "tension": 0.90,
        },
        book_id=1,
        ep=2,
    )
    await aggregate(bus, hub, written_ev2)

    assert len(evaluated_list) == 2

    # 4. MasterGraph の should_revise_writing で違反エピソードが検出され revise_phase が選ばれるか検証
    state = {
        "revision_budget": 2,
        "needs_revision_eps": [],
        "review_results": {},
        "narrative": hub,
    }

    decision = should_revise_writing(state)
    assert decision == "revise_phase"
    assert 2 in state["needs_revision_eps"]


@pytest.mark.asyncio
async def test_domain_event_bus_concurrency_50_episodes():
    """50話分のイベントを並行発行しても安全に処理・集約されることの負荷・並行性検証 (ステップ 34)"""
    import asyncio
    bus = DomainEventBus()
    hub = NarrativeState(book_id=1, branch_id=1)

    tension_sub.register(bus, hub)
    affinity_sub.register(bus, hub)
    continuity_sub.register(bus, hub)
    narrative_sub.register(bus, hub)
    erotic_sub.register(bus, hub)

    evaluated_events = []

    async def on_eval(ev: DomainEvent):
        evaluated_events.append(ev)

    bus.subscribe(NarrativeEventType.EPISODE_EVALUATED, on_eval)

    async def emit_ep(ep: int):
        ev = DomainEvent(
            type=NarrativeEventType.EPISODE_WRITTEN,
            payload={
                "text": f"第{ep}話の本文テキスト。街の平和を護るため戦った。",
                "scene": {"ep": ep, "episode_num": ep, "text": f"第{ep}話"},
                "tension": 0.5 + (ep % 10) * 0.04,
            },
            book_id=1,
            ep=ep,
        )
        await aggregate(bus, hub, ev)

    # 50話並行発行
    await asyncio.gather(*[emit_ep(ep) for ep in range(1, 51)])

    assert len(evaluated_events) == 50
    assert len(hub.episodes) == 50
    assert len(hub.tension_curve) == 50
