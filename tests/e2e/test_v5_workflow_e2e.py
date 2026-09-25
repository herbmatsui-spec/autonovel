"""tests/e2e/test_v5_workflow_e2e.py - v5系E2Eフルワークフローリグレッション防止テスト.

かんたんモード企画（ガチャ） ──► 逆算プロット ──► 本文生成 ──► Studio昇格 ──►
エディタ編集同期 ──► ワンクリック納品ZIPパッケージ生成
の一連の商用ワークフローがエラーなく完走することを検証する。
"""

from __future__ import annotations

import io
import json
import zipfile
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.backend.server import app
from src.domain.entities.easy_mode import (
    GachaPlan,
    GachaPlanType,
    GachaResponse,
    PromotionResponse,
)


from src.backend import database


@pytest.fixture
def api_client(real_db_manager):
    app.dependency_overrides[database.get_db] = lambda: real_db_manager
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(database.get_db, None)


@pytest.mark.asyncio
async def test_full_creation_to_zip_delivery_flow(api_client, real_db_manager):
    """企画から納品ZIPまでの全自動〜Studio協調E2Eシークエンステスト."""
    headers = {
        "X-API-Key": "v5-e2e-test-key",
        "Authorization": "Bearer dev-test-token",
    }

    # ==========================================
    # 1. 企画ガチャ (Pitch Gacha)
    # ==========================================
    mock_gacha_resp = GachaResponse(
        request_id="req_gacha_123",
        plans=[
            GachaPlan(
                plan_id="plan_royal",
                plan_type=GachaPlanType.ROYAL,
                title="追放された付与魔術師の逆転無双",
                logline="無能と罵られ追放された青年が、世界最強の付与魔術師として名を馳せる。",
                protagonist_summary="アルト: 謙虚だが底知れぬ魔術適性を持つ。",
                charm_point="徹底した爽快ざまぁと圧倒的無双カタルシス",
                is_recommended=True,
            ),
            GachaPlan(
                plan_id="plan_curveball",
                plan_type=GachaPlanType.CURVEBALL,
                title="ダンジョン農園のスローライフ",
                logline="最深部で野菜を育てることになった少年の物語。",
                protagonist_summary="ロア: 平穏を好む元勇者。",
                charm_point="ほのぼの日常と最強設定のギャップ",
            ),
            GachaPlan(
                plan_id="plan_dark",
                plan_type=GachaPlanType.DARK,
                title="冥府の復讐者",
                logline="裏切られた死霊術師が全てを奪い返すダークファンタジー。",
                protagonist_summary="クロウ: 冷徹な復讐鬼。",
                charm_point="緻密な策略と冷徹な復讐劇",
            ),
        ],
        recommended_plan_id="plan_royal",
    )

    with patch("src.services.gacha_service.GachaService.generate_plans", new_callable=AsyncMock) as mock_gacha:
        mock_gacha.return_value = mock_gacha_resp
        gacha_req = {
            "genre": "ハイファンタジー (R15)",
            "keywords": ["追放", "ざまぁ", "チート"],
            "temperature": 0.7,
        }
        res_gacha = api_client.post("/easy_mode/gacha", json=gacha_req, headers=headers)
        assert res_gacha.status_code == 200
        gacha_data = res_gacha.json()
        assert len(gacha_data["plans"]) == 3
        selected_plan = gacha_data["plans"][0]
        assert selected_plan["plan_id"] == "plan_royal"

    # ==========================================
    # 2. 逆算プロット生成 (Reverse Plot Builder)
    # ==========================================
    mock_reverse_result = {
        "title": selected_plan["title"],
        "arcs": [
            {
                "arc_num": 1,
                "start_ep": 1,
                "end_ep": 10,
                "title": "追放と覚醒編",
                "summary": "パーティ追放から真の力の発現まで",
                "conflictType": "betrayal_and_awakening",
            }
        ],
        "episodes": [
            {
                "ep_num": 1,
                "title": "第1話 無能宣告の果てに",
                "one_line_summary": "勇者パーティから追放を言い渡されるアルト。",
                "tension": 40,
                "catharsis": 10,
                "is_catharsis": False,
                "thematic_milestone": "理不尽な追放",
                "burned_cost_or_loot": "剥奪されたパーティバッジ",
                "antagonist_status": "傲慢な勇者",
                "resolution_style": "Focus_Drama",
            },
            {
                "ep_num": 2,
                "title": "第2話 覚醒の刻印",
                "one_line_summary": "単身潜った危険ダンジョンで秘められた付与術が暴走・覚醒する。",
                "tension": 85,
                "catharsis": 80,
                "is_catharsis": True,
                "thematic_milestone": "真の力の覚醒",
                "burned_cost_or_loot": "古代神具『神速の腕輪』",
                "antagonist_status": "圧倒的実力差",
                "resolution_style": "Cheat",
            },
        ],
    }

    with patch(
        "src.backend.workflows.reverse_plot_workflow.ReversePlotGenerationWorkflow.execute",
        new_callable=AsyncMock,
    ) as mock_rev:
        mock_rev.return_value = mock_reverse_result
        reverse_req = {
            "answers": {
                "emotionalGoal": "triumph",
                "sacrifice": "status",
                "coreConflict": "self_vs_society",
                "openingHook": "isekai_awakening",
            },
            "targetEpisodes": 10,
            "genre": "ハイファンタジー (R15)",
        }
        res_rev = api_client.post("/easy_mode/reverse-generate", json=reverse_req, headers=headers)
        assert res_rev.status_code == 200
        rev_data = res_rev.json()
        assert len(rev_data["episodes"]) >= 2
        episodes_blueprint = rev_data["episodes"]

    # ==========================================
    # 3. Studio への昇格 (Producer Promotion)
    # ==========================================
    mock_promote_resp = PromotionResponse(
        success=True,
        redirect_url="/studio/101",
        state_token="state_token_v5_e2e_valid",
    )

    with patch.object(
        PromotionResponse,
        "__init__",
        return_value=None,
    ) if False else patch(
        "src.services.promotion_service.PromotionService.promote_book",
        new_callable=AsyncMock,
    ) as mock_promote:
        mock_promote.return_value = mock_promote_resp
        promote_req = {"book_id": "101"}
        res_promote = api_client.post("/api/wizard/promote", json=promote_req, headers=headers)
        assert res_promote.status_code == 200
        promote_data = res_promote.json()
        assert promote_data["success"] is True
        assert promote_data["redirect_url"] == "/studio/101"
        assert promote_data["state_token"] == "state_token_v5_e2e_valid"

    # ==========================================
    # 4. 本文加筆・編集同期 & ワンクリック納品 ZIP エクスポート
    # ==========================================
    edited_text = (
        "「お前の役目はもう終わったんだよ」\n"
        "勇者は冷笑を浮かべ、アルトの胸からギルドプレートを引きちぎった。\n"
        "雨が降りしきる王都の裏路地。アルトは泥水の中に膝をつく。\n"
        "だが、少年の瞳の奥底で、かつてない青い燐光が灯っていた。\n"
        "（これですべて終わったわけじゃない。ここからが僕の本当の物語だ――）\n"
    )

    export_payload = {
        "title": selected_plan["title"],
        "genre": "ハイファンタジー (R15)",
        "current_text": edited_text,
        "character": {
            "name": "アルト",
            "role": "主人公",
            "personality": "温厚だが芯が強い",
            "ability": "神速付与術",
        },
        "plots": episodes_blueprint,
    }

    res_export = api_client.post(
        "/easy_mode/export-with-data?book_id=101",
        json=export_payload,
        headers=headers,
    )
    assert res_export.status_code == 200
    assert res_export.headers.get("content-type") == "application/zip"

    # ==========================================
    # 5. ZIP パッケージの整合性・BOM・ファイル内容の完全検証
    # ==========================================
    zip_bytes = res_export.content
    assert len(zip_bytes) > 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        names = z.namelist()
        assert "01_本文.txt" in names
        assert "02_キャラクター・世界観設定集.txt" in names
        assert "03_プロット概要.txt" in names
        assert "04_データダンプ.json" in names

        # 01_本文.txt 検証
        honbun_bytes = z.read("01_本文.txt")
        assert honbun_bytes.startswith(b"\xef\xbb\xbf"), "Windowsメモ帳互換のUTF-8 BOMが必須"
        honbun_str = honbun_bytes.decode("utf-8-sig")
        assert selected_plan["title"] in honbun_str
        assert "勇者は冷笑を浮かべ" in honbun_str
        assert "\r\n" in honbun_str, "Windows互換のCRLF改行が必須"

        # 02_キャラクター設定集 検証
        settings_bytes = z.read("02_キャラクター・世界観設定集.txt")
        assert settings_bytes.startswith(b"\xef\xbb\xbf")
        settings_str = settings_bytes.decode("utf-8-sig")
        assert "アルト" in settings_str
        assert "神速付与術" in settings_str

        # 03_プロット概要 検証
        plot_bytes = z.read("03_プロット概要.txt")
        assert plot_bytes.startswith(b"\xef\xbb\xbf")
        plot_str = plot_bytes.decode("utf-8-sig")
        assert "無能宣告の果てに" in plot_str
        assert "覚醒の刻印" in plot_str

        # 04_データダンプ (JSON) 検証
        dump_bytes = z.read("04_データダンプ.json")
        dump_obj = json.loads(dump_bytes.decode("utf-8"))
        assert dump_obj["title"] == selected_plan["title"]
        assert len(dump_obj["plots"]) == 2
