import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from src.backend.server import app
from src.backend.config import settings

# テスト用に認証を無効化
settings.AUTH_DISABLED = True

# ルーターを事前に含める
from src.backend.routers.plots import router
app.include_router(router)


@pytest.mark.asyncio
async def test_expand_commercial_beats_success():
    """商業ビート生成APIの正常系テスト"""
    transport = ASGITransport(app=app)

    # LLMゲートウェイをモック
    with patch("src.backend.routers.plots.LLMGateway") as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm_class.return_value = mock_llm
        
        # LLMの応答をモック（有効なJSON）
        mock_response = MagicMock()
        mock_response.story_content = '''[
            {"episode": 1, "title": "日常の崩壊", "outline": "主人公の平穏な日常が崩れる", "cliffhanger_type": "New Crisis", "sensory_focus": ["visual", "auditory"], "foreshadowing_notes": "不穏な予兆"},
            {"episode": 2, "title": "運命の告知", "outline": "使命が課せられる", "cliffhanger_type": "Shocking Truth", "sensory_focus": ["tactile", "metaphor"], "foreshadowing_notes": "古い予言"},
            {"episode": 3, "title": "覚悟の決意", "outline": "立ち向かうことを決意", "cliffhanger_type": "Quiet Foreshadowing", "sensory_focus": ["visual", "gustatory"], "foreshadowing_notes": "師匠の言葉"},
            {"episode": 4, "title": "最初の試練", "outline": "強敵と遭遇", "cliffhanger_type": "New Crisis", "sensory_focus": ["auditory", "olfactory"], "foreshadowing_notes": "敵の弱点"},
            {"episode": 5, "title": "力の代償", "outline": "肉体・精神に負荷", "cliffhanger_type": "Shocking Truth", "sensory_focus": ["tactile", "metaphor"], "foreshadowing_notes": "禁忌の存在"},
            {"episode": 6, "title": "仲間との絆", "outline": "拠点を確保", "cliffhanger_type": "Quiet Foreshadowing", "sensory_focus": ["visual", "auditory"], "foreshadowing_notes": "仲間の秘密"},
            {"episode": 7, "title": "無双の快進撃", "outline": "次々と強敵を薙ぎ倒す", "cliffhanger_type": "New Crisis", "sensory_focus": ["visual", "gustatory"], "foreshadowing_notes": "影の黒幕"},
            {"episode": 8, "title": "中間地点の真実", "outline": "衝撃の事実が判明", "cliffhanger_type": "Shocking Truth", "sensory_focus": ["olfactory", "metaphor"], "foreshadowing_notes": "世界の秘密"},
            {"episode": 9, "title": "追い詰められる", "outline": "逆襲が始まる", "cliffhanger_type": "New Crisis", "sensory_focus": ["auditory", "tactile"], "foreshadowing_notes": "最後の切り札"},
            {"episode": 10, "title": "全てを失って", "outline": "奈落の底へ", "cliffhanger_type": "Quiet Foreshadowing", "sensory_focus": ["visual", "metaphor"], "foreshadowing_notes": "過去の伏線回収"},
            {"episode": 11, "title": "闇夜の決意", "outline": "真の強さに目覚める", "cliffhanger_type": "Shocking Truth", "sensory_focus": ["tactile", "gustatory"], "foreshadowing_notes": "真の敵"},
            {"episode": 12, "title": "決戦の夜明け", "outline": "クライマックスへ", "cliffhanger_type": "Quiet Foreshadowing", "sensory_focus": ["visual", "auditory", "metaphor"], "foreshadowing_notes": "エピローグへ"}
        ]'''
        mock_llm.generate_text.return_value = mock_response

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/plots/expand-beats",
                json={
                    "title": "テスト作品",
                    "genre": "fantasy",
                    "synopsis": "テストあらすじ",
                    "target_chapters": 20,
                    "cheat_scale": 4,
                    "growth_curve": "最初からカンスト(無双)",
                    "system_assist": 70,
                    "cost_severity": 2,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) == 12
            assert data[0]["episode"] == 1
            assert data[0]["title"] == "日常の崩壊"
            assert data[0]["cliffhanger_type"] == "New Crisis"
            assert "visual" in data[0]["sensory_focus"]


@pytest.mark.asyncio
async def test_expand_commercial_beats_fallback():
    """LLM失敗時のフォールバックテスト"""
    transport = ASGITransport(app=app)

    # LLMゲートウェイをモック（例外を投げる）
    with patch("src.backend.routers.plots.LLMGateway") as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm_class.return_value = mock_llm
        mock_llm.generate_text.side_effect = Exception("LLM Error")

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/plots/expand-beats",
                json={
                    "title": "テスト作品",
                    "genre": "fantasy",
                    "synopsis": "テストあらすじ",
                    "target_chapters": 20,
                    "cheat_scale": 4,
                    "growth_curve": "最初からカンスト(無双)",
                    "system_assist": 70,
                    "cost_severity": 2,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) == 12
            assert data[0]["episode"] == 1
            assert "チート能力" in data[3]["outline"]  # cheat_scaleが反映される


@pytest.mark.asyncio
async def test_expand_commercial_beats_invalid_input():
    """不正な入力パラメータのテスト"""
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 必須フィールド欠落
        resp = await client.post(
            "/api/plots/expand-beats",
            json={
                "genre": "fantasy",
            },
        )
        assert resp.status_code == 422  # Validation error

        # チート度が範囲外
        resp = await client.post(
            "/api/plots/expand-beats",
            json={
                "title": "テスト",
                "genre": "fantasy",
                "cheat_scale": 10,  # 範囲外
            },
        )
        assert resp.status_code == 422

        # 成長曲線が空
        resp = await client.post(
            "/api/plots/expand-beats",
            json={
                "title": "テスト",
                "genre": "fantasy",
                "growth_curve": "",
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_expand_commercial_beats_edge_cases():
    """エッジケーステスト（極端な値、空の入力など）"""
    transport = ASGITransport(app=app)

    with patch("src.backend.routers.plots.LLMGateway") as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm_class.return_value = mock_llm
        mock_response = MagicMock()
        mock_response.story_content = '[]'  # 空の配列
        mock_llm.generate_text.return_value = mock_response

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 最小限の入力
            resp = await client.post(
                "/api/plots/expand-beats",
                json={
                    "title": "最小",
                    "genre": "fantasy",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            # フォールバックが使われるため12件返る
            assert len(data) == 12

            # 最大話数
            resp = await client.post(
                "/api/plots/expand-beats",
                json={
                    "title": "最大",
                    "genre": "fantasy",
                    "target_chapters": 100,
                    "cheat_scale": 5,
                    "system_assist": 100,
                    "cost_severity": 5,
                },
            )
            assert resp.status_code == 200


@pytest.mark.asyncio
async def test_expand_commercial_beats_regression():
    """既存のビート生成ロジックに対するリグレッションテスト"""
    transport = ASGITransport(app=app)

    with patch("src.backend.routers.plots.LLMGateway") as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm_class.return_value = mock_llm
        mock_response = MagicMock()
        mock_response.story_content = '''[
            {"episode": 1, "title": "Test", "outline": "Outline", "cliffhanger_type": "New Crisis", "sensory_focus": ["visual"], "foreshadowing_notes": "Note"}
        ]'''
        mock_llm.generate_text.return_value = mock_response

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 既存のエンドポイントが影響を受けないことを確認
            resp = await client.get("/api/plots/1")
            # 404または200（本の所有権チェックで失敗する可能性もあるが、エンドポイント自体は存在する）
            assert resp.status_code in (200, 404, 403)

            # 他のエンドポイントも確認
            resp = await client.post("/api/plots/plan_generation", json={"params": {}})
            # 422: PlanGenerationRequest は api_key 必須のためバリデーションエラーは正常
            assert resp.status_code in (200, 400, 401, 403, 422)