"""Step 9: キャッチコピー生成APIの単体テスト。

FastAPI TestClient で POST /api/marketing/catchphrases の正常応答を検証する。
"""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from src.backend.server import app
from src.backend.config import settings
from src.backend.routers.marketing import router

# ルーターを事前に含める
app.include_router(router)


@pytest.fixture(autouse=True)
def _auth_disabled(monkeypatch):
    """認証バイパスをテストスコープに限定（テスト終了後に自動復元）。"""
    monkeypatch.setattr(settings, "AUTH_DISABLED", True)


def _make_llm_response() -> MagicMock:
    """LLMのJSON応答（キャッチコピー候補20件）を模擬する。"""
    mock_response = MagicMock()
    mock_response.story_content = str(
        [
            {
                "catchphrase": "「お前はクビだ」――そう言った元パーティが翌日全滅していた件。",
                "type": "dialogue",
            },
            {
                "catchphrase": "追放された元無能、実は世界で唯一の【錬金術】でした。",
                "type": "reversal",
            },
        ]
        + [
            {
                "catchphrase": f"今更戻ってこい？ もう最強の{i}と暮らしてますが？",
                "type": "confession",
            }
            for i in range(18)
        ]
    )
    return mock_response


@pytest.mark.asyncio
async def test_generate_catchphrases_success():
    """キャッチコピー生成APIの正常系テスト。"""
    transport = ASGITransport(app=app)

    with (
        patch("src.core.container.app.AppContainer") as mock_container_class,
        patch(
            "src.backend.routers.marketing.validate_api_key_or_raise",
            new_callable=AsyncMock,
        ),
    ):
        mock_container = MagicMock()
        mock_agent = MagicMock()
        mock_agent.generate_viral_catchphrases = AsyncMock(
            return_value=[
                {
                    "catchphrase": "「お前はクビだ」――そう言った元パーティが翌日全滅していた件。",
                    "score": 95.0,
                    "char_count": 30,
                    "type": "dialogue",
                },
                {
                    "catchphrase": "追放された元無能、実は世界で唯一の【錬金術】でした。",
                    "score": 85.0,
                    "char_count": 26,
                    "type": "reversal",
                },
            ]
        )
        mock_container.marketing = MagicMock(return_value=mock_agent)
        mock_container_class.return_value = mock_container

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/marketing/catchphrases",
                json={
                    "api_key": "test-key",
                    "project_settings": "ジャンル: 異世界ファンタジー、追放ざまぁ",
                    "candidate_count": 20,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) >= 1
            first = data[0]
            assert "catchphrase" in first
            assert "score" in first
            assert "char_count" in first
            assert "type" in first
            # スコア降順ソートされている
            scores = [item["score"] for item in data]
            assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_generate_catchphrases_with_llm_mock():
    """MarketingAgent経由でLLMモック応答から生成できることを検証。"""
    transport = ASGITransport(app=app)

    with (
        patch("src.backend.routers.marketing.validate_api_key_or_raise", new_callable=AsyncMock),
        patch("src.core.container.app.AppContainer") as mock_container_class,
        patch("prompts.manager.PromptManager") as mock_pm_class,
    ):
        mock_pm = MagicMock()
        mock_pm.build_viral_catchphrase_prompt = AsyncMock(
            return_value="キャッチコピー生成プロンプト"
        )
        mock_pm_class.return_value = mock_pm

        mock_container = MagicMock()
        mock_agent = MagicMock()
        mock_agent.prompt_manager = mock_pm
        mock_agent.generate_viral_catchphrases = AsyncMock(
            return_value=[
                {
                    "catchphrase": "処刑されたはずの元英雄、気ままなスローライフ始めます。",
                    "score": 90.0,
                    "char_count": 26,
                    "type": "confession",
                }
            ]
        )
        mock_container.marketing = MagicMock(return_value=mock_agent)
        mock_container_class.return_value = mock_container

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/marketing/catchphrases",
                json={
                    "api_key": "test-key",
                    "project_settings": "ジャンル: 異世界ファンタジー",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert "スローライフ" in data[0]["catchphrase"]


@pytest.mark.asyncio
async def test_generate_catchphrases_validation_error():
    """必須フィールド欠落時は422バリデーションエラー。"""
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # project_settings 欠落
        resp = await client.post(
            "/api/marketing/catchphrases",
            json={"api_key": "test-key"},
        )
        assert resp.status_code == 422

        # candidate_count が範囲外
        resp = await client.post(
            "/api/marketing/catchphrases",
            json={
                "api_key": "test-key",
                "project_settings": "テスト",
                "candidate_count": 0,
            },
        )
        assert resp.status_code == 422

        resp = await client.post(
            "/api/marketing/catchphrases",
            json={
                "api_key": "test-key",
                "project_settings": "テスト",
                "candidate_count": 101,
            },
        )
        assert resp.status_code == 422
