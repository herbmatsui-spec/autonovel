"""
Master Integration Test Suite for Narrative Subtext Suite (PLAN_Y1, PLAN_Y2, PLAN_Y3).
Tests GenerationPipeline modes and FastAPI Subtext endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from src.backend.server import app
from src.narrative.subtext_engine.models import SubtextContext
from src.pipeline.generation import GenerationPipeline


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def pipeline():
    return GenerationPipeline()


# ==============================================================================
# Pipeline Mode Switching Tests
# ==============================================================================

def test_pipeline_mode_off(pipeline):
    pipeline.set_mode("off")
    raw = "「私は悲しい」[BEAT:pause:short]"
    res = pipeline.process_text(raw)
    assert res == raw, "Mode 'off' must return exact original text without modifications"


def test_pipeline_mode_token(pipeline):
    pipeline.set_mode("token")
    raw = "「答えてくれ」[BEAT:pause:short]「聞こえないのか？」"
    res = pipeline.process_text(raw)
    assert "[BEAT:pause:short]" not in res
    assert "「答えてくれ」" in res


def test_pipeline_mode_rule(pipeline):
    pipeline.set_mode("rule")
    raw = "「私は悲しい」"
    res = pipeline.process_text(raw)
    assert "悲しげな表情で" in res


def test_pipeline_mode_hybrid(pipeline):
    pipeline.set_mode("hybrid")
    raw = "「私は悲しい」[BEAT:pause:short]「どうして……」"
    res = pipeline.process_text(raw)
    # Both token expansion and rule rewrite should execute
    assert "[BEAT:pause:short]" not in res
    assert "悲しげな表情で" in res


def test_pipeline_render_template(pipeline):
    ctx = SubtextContext(emotion="betrayal", power_dynamic="inferior", relationship="former_ally")
    rendered = pipeline.render_template(template_id_or_auto="auto", context=ctx)
    assert len(rendered.strip()) > 0
    assert "「" in rendered or "——" in rendered or "（" in rendered


def test_pipeline_custom_hook(pipeline):
    pipeline.set_mode("hybrid")
    hook_called = []

    def my_hook(text, ctx):
        hook_called.append(True)
        return text + "\n【HOOK_APPLIED】"

    pipeline.post_process_hooks.append(my_hook)
    res = pipeline.process_text("「テスト」")
    assert hook_called == [True]
    assert "【HOOK_APPLIED】" in res


# ==============================================================================
# FastAPI Subtext Router Tests
# ==============================================================================

def test_api_list_and_create_rule(client):
    # GET /subtext/rules
    resp = client.get("/subtext/rules")
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) >= 7

    # POST /subtext/rules
    new_rule_payload = {
        "id": "rule_api_custom_test",
        "name": "Custom API Test Rule",
        "pattern": "API_TEST_INPUT",
        "replacement": "API_TEST_OUTPUT",
        "priority": 15,
        "final": False,
        "enabled": True,
        "tags": ["test"],
        "description": "Created via API test",
    }
    create_resp = client.post("/subtext/rules", json=new_rule_payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["id"] == "rule_api_custom_test"


def test_api_templates(client):
    # GET /subtext/templates
    resp = client.get("/subtext/templates")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 23
    assert len(data["templates"]) == data["count"]


def test_api_tokens(client):
    # GET /subtext/tokens
    resp = client.get("/subtext/tokens")
    assert resp.status_code == 200
    data = resp.json()
    assert "subtext" in data
    assert "beat" in data

    # POST /subtext/tokens/preview
    preview_payload = {
        "text": "「何の話だ」[BEAT:pause:short]「答えてくれ」",
        "seed": 42,
    }
    prev_resp = client.post("/subtext/tokens/preview", json=preview_payload)
    assert prev_resp.status_code == 200
    res_json = prev_resp.json()
    assert "[BEAT:pause:short]" not in res_json["expanded"]


def test_api_master_process(client):
    payload = {
        "text": "「私は悲しい」[BEAT:pause:short]「行かないで」",
        "mode": "hybrid",
        "seed": 100,
    }
    resp = client.post("/subtext/process", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "hybrid"
    assert "悲しげな表情で" in data["processed"]
    assert "[BEAT:pause:short]" not in data["processed"]
