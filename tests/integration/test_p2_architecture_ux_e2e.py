"""P2 Architecture & UX Refinement E2E Integration Tests (Steps 67-70).

Tests the complete integrated capabilities:
1. Unified LLM Client writing & 8 Specialist Auditors without reflection (Step 68)
2. Real-time WebSocket pipeline events & score update stream (Step 69)
3. Publishing platform formatter & zip export for Narou and Kakuyomu (Step 70)
"""

from __future__ import annotations

import asyncio
import io
import json
import zipfile
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Core Unified LLM
from src.core.llm.types import LLMRequest, LLMResponse, LLMUsage
from src.core.llm.adapters.mock_unified_client import UnifiedMockLLMClient
from src.agents.specialist_auditor_base import SpecialistAuditor, SpecialistAuditResult

# WebSocket & Pipeline Events
from src.backend.schemas.pipeline_events import PipelineEvent
from src.backend.websocket.pipeline_hub import PipelineEventHub
from src.backend.routers.pipeline_stream import router as pipeline_router

# Publishing Formatters
from src.services.formatters.ruby_transpiler import PublishPlatform, RubyTranspiler
from src.services.formatters.platform_formatter import PlatformFormatter
from src.backend.routers.publishing import router as publishing_router


# ==============================================================================
# Step 68: E2E 1 - Unified LLM Writing & Multi-Auditor Pipeline
# ==============================================================================
@pytest.mark.asyncio
async def test_unified_llm_writing_and_audit_flow_e2e():
    """E2E Test 1: Verify writing and audit pipeline with unified LLM client."""
    from src.agents.specialists.consistency_auditor import ConsistencyAuditor

    audit_json = {
        "score": 88.0,
        "critique": "テンポが良く伏線も効果的に提示されている。",
        "suggestions": ["戦闘シーンの擬音をより具体的に"],
        "confidence": 0.95,
        "reasoning": "全体の構成と文体が基準を満たしている",
        "actionable_diffs": [
            {
                "location": "p.1",
                "original_quote": "剣を振った。",
                "improved_suggestion": "鋭い風切り音とともに白銀の刃を一閃させた。",
                "rationale": "臨場感を高める描写への具体化",
            }
        ],
    }

    mock_llm = UnifiedMockLLMClient(response_text=json.dumps(audit_json))
    auditor = ConsistencyAuditor(llm=mock_llm)

    draft_ctx = {
        "draft_text": "勇者は剣を抜いて魔王と対峙した。静寂が支配する。",
        "world_bible_snapshot": {
            "characters": [{"name": "勇者", "status": "健康"}],
            "terms": [],
            "rules": [],
        },
    }
    result = await auditor.audit(draft_ctx)

    assert isinstance(result, SpecialistAuditResult)
    assert result.specialist_name == "consistency"
    assert result.score == 88.0
    assert len(result.actionable_diffs) == 1
    assert "白銀の刃" in result.actionable_diffs[0].improved_suggestion


# ==============================================================================
# Step 69: E2E 2 - Real-time WebSocket Pipeline Events & Score Updates
# ==============================================================================
def test_websocket_live_progress_stream_e2e():
    """E2E Test 2: Verify real-time event broadcasting over WebSocket."""
    app = FastAPI()
    app.include_router(pipeline_router)

    hub = PipelineEventHub()
    # Temporarily monkeypatch global hub for isolated test
    import src.backend.routers.pipeline_stream as stream_mod
    original_hub = stream_mod.pipeline_event_hub
    stream_mod.pipeline_event_hub = hub

    test_book_id = 777

    client = TestClient(app)

    # Seed initial event before connection
    init_ev = PipelineEvent(
        event_type="task_started",
        book_id=test_book_id,
        task_id="dag_node_draft_1",
        payload={"state": "running", "progress": 10},
    )
    asyncio.run(hub.broadcast(init_ev))

    try:
        with client.websocket_connect(f"/api/ws/pipeline/{test_book_id}") as ws:
            # 1. Verify initial snapshot received upon connection
            snapshot = ws.receive_json()
            assert snapshot["event_type"] == "task_started"
            assert snapshot["task_id"] == "dag_node_draft_1"
            assert snapshot["payload"]["progress"] == 10

            # 2. Broadcast mid-pipeline score improvement event
            score_ev = PipelineEvent(
                event_type="score_updated",
                book_id=test_book_id,
                task_id="pdca_cycle_1",
                payload={
                    "cycle": 1,
                    "score": 84.5,
                    "delta": 6.5,
                    "scores_by_specialist": {"consistency": 85.0, "reader_hook": 84.0},
                },
            )
            asyncio.run(hub.broadcast(score_ev))

            event_msg = ws.receive_json()
            assert event_msg["event_type"] == "score_updated"
            assert event_msg["payload"]["score"] == 84.5
            assert event_msg["payload"]["delta"] == 6.5

            # 3. Test ping / pong
            ws.send_text("ping")
            pong_msg = ws.receive_json()
            assert pong_msg["event_type"] == "pong"
    finally:
        stream_mod.pipeline_event_hub = original_hub


# ==============================================================================
# Step 70: E2E 3 - Multi-Platform Formatting & Packaging (Narou & Kakuyomu)
# ==============================================================================
def test_publishing_export_zip_e2e():
    """E2E Test 3: Export formatted novel archive for Kakuyomu and Narou."""
    title = "異世界転生と聖剣の秘密"
    synopsis = "平凡な高校生が異世界に召喚され、世界を救う旅に出る。"
    episodes = [
        {
            "title": "プロローグ 始まりの朝",
            "content": "彼は｜運命《さだめ》に立ち向かう。《《伝説》》の始まりである。\n「行くぞ、相棒！」",
            "foreword": "本作をお読みいただきありがとうございます。",
            "afterword": "第1話でした。次回更新は明日です！",
        },
        {
            "title": "第2話 旅立ちの街",
            "content": "街の広場は活気に満ちていた。\n\n\n\n商人たちの声が響く……",
        },
    ]

    # Test Narou packaging
    narou_zip_bytes = PlatformFormatter.package_for_platform(
        title=title,
        synopsis=synopsis,
        episodes=episodes,
        platform=PublishPlatform.NAROU,
    )
    assert len(narou_zip_bytes) > 0

    with zipfile.ZipFile(io.BytesIO(narou_zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "00_作品情報・あらすじ.txt" in namelist
        assert "本文/001_プロローグ 始まりの朝.txt" in namelist
        assert "本文/002_第2話 旅立ちの街.txt" in namelist

        ep1_text = zf.read("本文/001_プロローグ 始まりの朝.txt").decode("utf-8")
        # Narou ruby check: |運命《さだめ》
        assert "|運命《さだめ》" in ep1_text
        # Narou bouten check: decomposed ruby |伝《・》|説《・》
        assert "|伝《・》|説《・》" in ep1_text
        # Typography: Dialogue line has no indent
        assert "「行くぞ、相棒！」" in ep1_text

        ep2_text = zf.read("本文/002_第2話 旅立ちの街.txt").decode("utf-8")
        # Typography: 4 blank lines capped to at most 2 blanks
        assert "\n\n\n\n" not in ep2_text

    # Test Kakuyomu packaging
    kakuyomu_zip_bytes = PlatformFormatter.package_for_platform(
        title=title,
        synopsis=synopsis,
        episodes=episodes,
        platform=PublishPlatform.KAKUYOMU,
    )
    with zipfile.ZipFile(io.BytesIO(kakuyomu_zip_bytes), "r") as zf:
        ep1_text = zf.read("本文/001_プロローグ 始まりの朝.txt").decode("utf-8")
        # Kakuyomu retains native 《《伝説》》
        assert "《《伝説》》" in ep1_text
