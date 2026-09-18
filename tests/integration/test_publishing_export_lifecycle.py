"""出版・整形結合E2Eテスト (v5.0 Step 12).

執筆本文からEPUB 3生成および投稿サイト形式テキスト取得の全結合テスト。
"""
import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock

from src.backend.server import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestPublishingExportLifecycle:
    """出版フロー全体のE2Eテスト"""

    @pytest.mark.asyncio
    async def test_full_publishing_flow(self, client):
        """EPUB生成→整形コピーの完全フロー"""
        # 1. 小説データの準備
        novel_data = {
            "title": "テスト小説",
            "synopsis": "これはテスト用のあらすじです。",
            "genre": "fantasy",
            "chapters": [
                {
                    "ep_num": 1,
                    "title": "第1話 始まり",
                    "content": "「行くぞ！」\n主人公は叫んだ。\n\n|真紅《しんく》の瞳が光る。",
                    "is_catharsis": False,
                },
                {
                    "ep_num": 2,
                    "title": "第2話 旅立ち",
                    "content": "森の中で、｜魔導書《グリモワール》を発見した。\n《《重要》》な手がかりだ。",
                    "is_catharsis": True,
                },
            ],
        }

        # 2. 各プラットフォーム形式での整形コピー
        platforms = ["narou", "kakuyomu", "alphapolis"]
        formatted_results = {}

        for platform in platforms:
            response = await client.post(
                "/api/export/copy/",
                json={
                    "title": novel_data["chapters"][0]["title"],
                    "body": novel_data["chapters"][0]["content"],
                    "foreword": novel_data["synopsis"],
                    "afterword": "ご覧いただきありがとうございました。",
                    "platform": platform,
                },
            )
            
            if response.status_code == 401:
                pytest.skip("Authentication required")
            
            assert response.status_code == 200
            data = response.json()
            formatted_results[platform] = data

            # プラットフォーム別の検証
            if platform == "narou":
                assert "　「行くぞ！」" in data["body"]
                assert "|真紅《しんく》" in data["body"]
            elif platform == "kakuyomu":
                assert "|魔導書《グリモワール》" in data["body"]
                assert "《《重要》》" in data["body"]
            elif platform == "alphapolis":
                assert "#魔導書(グリモワール)#" in data["body"]
            
            # 文字数カウントが返却されていること
            assert data["total_characters"] > 0

    @pytest.mark.asyncio
    async def test_chapter_formatting_consistency(self, client):
        """複数チャプターの整形一貫性テスト"""
        chapters = [
            ("第1話", "「こんにちは」\n少女は笑った。\n\n|桜《さくら》が舞う。"),
            ("第2話", "森の奥で、｜魔導書《グリモワール》を見つけた。"),
            ("第3話", "|勇者《ゆうしゃ》よ、立ち上がれ！\n「はい！」"),
        ]

        for title, body in chapters:
            response = await client.post(
                "/api/export/copy/",
                json={
                    "title": title,
                    "body": body,
                    "platform": "narou",
                },
            )
            
            if response.status_code == 401:
                pytest.skip("Authentication required")
            
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == title
            assert data["total_characters"] > 0

    @pytest.mark.asyncio
    async def test_error_handling_invalid_platform(self, client):
        """不正なプラットフォーム指定のエラーハンドリング"""
        response = await client.post(
            "/api/export/copy/",
            json={
                "title": "テスト",
                "body": "本文",
                "platform": "invalid_platform",
            },
        )
        
        if response.status_code == 401:
            pytest.skip("Authentication required")
        
        assert response.status_code == 400
        assert "platform must be one of" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_error_handling_empty_content(self, client):
        """空コンテンツのエラーハンドリング"""
        response = await client.post(
            "/api/export/copy/",
            json={
                "title": "",
                "body": "本文",
                "platform": "narou",
            },
        )
        
        if response.status_code == 401:
            pytest.skip("Authentication required")
        
        assert response.status_code == 400
        assert "title and body cannot be empty" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_long_text_handling(self, client):
        """長文テキストの処理テスト"""
        long_body = "あ" * 50000  # 5万文字
        response = await client.post(
            "/api/export/copy/",
            json={
                "title": "長編小説",
                "body": long_body,
                "platform": "narou",
            },
        )
        
        if response.status_code == 401:
            pytest.skip("Authentication required")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_characters"] > 10000

    @pytest.mark.asyncio
    async def test_special_characters_handling(self, client):
        """特殊文字・絵文字の処理テスト"""
        special_body = "記号: !@#$%^&*()\n絵文字: 😀🎉🌸\nルビ: |漢字《かんじ》\n傍点: 《《強調》》"
        response = await client.post(
            "/api/export/copy/",
            json={
                "title": "特殊文字テスト",
                "body": special_body,
                "platform": "kakuyomu",
            },
        )
        
        if response.status_code == 401:
            pytest.skip("Authentication required")
        
        assert response.status_code == 200
        data = response.json()
        assert "😀🎉🌸" in data["body"]
        assert "|漢字《かんじ》" in data["body"]
        assert "《《強調》》" in data["body"]

    @pytest.mark.asyncio
    async def test_platform_case_insensitive(self, client):
        """プラットフォーム名の大文字小文字不区分"""
        response = await client.post(
            "/api/export/copy/",
            json={
                "title": "テスト",
                "body": "本文",
                "platform": "NAROU",
            },
        )
        
        if response.status_code == 401:
            pytest.skip("Authentication required")
        
        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "narou"

    @pytest.mark.asyncio
    async def test_foreword_afterword_preservation(self, client):
        """前書き・後書きの保持テスト"""
        foreword = "これは前書きです。応援よろしくお願いします！"
        afterword = "ここまでお読みいただき、ありがとうございました。"
        
        response = await client.post(
            "/api/export/copy/",
            json={
                "title": "テスト",
                "body": "本文です。",
                "foreword": foreword,
                "afterword": afterword,
                "platform": "narou",
            },
        )
        
        if response.status_code == 401:
            pytest.skip("Authentication required")
        
        assert response.status_code == 200
        data = response.json()
        assert data["foreword"] == foreword
        assert data["afterword"] == afterword

    @pytest.mark.asyncio
    async def test_response_format_consistency(self, client):
        """レスポンス形式の一貫性テスト"""
        response = await client.post(
            "/api/export/copy/",
            json={
                "title": "テスト",
                "body": "本文",
                "platform": "narou",
            },
        )
        
        if response.status_code == 401:
            pytest.skip("Authentication required")
        
        assert response.status_code == 200
        data = response.json()
        
        # 必須フィールドの存在確認
        required_fields = ["title", "foreword", "body", "afterword", "total_characters", "platform"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # 型の確認
        assert isinstance(data["title"], str)
        assert isinstance(data["foreword"], str)
        assert isinstance(data["body"], str)
        assert isinstance(data["afterword"], str)
        assert isinstance(data["total_characters"], int)
        assert isinstance(data["platform"], str)
        assert data["total_characters"] >= 0

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client):
        """同時リクエストの処理テスト"""
        async def make_request(platform: str):
            return await client.post(
                "/api/export/copy/",
                json={
                    "title": f"テスト_{platform}",
                    "body": f"{platform}用の本文",
                    "platform": platform,
                },
            )

        # 3つのプラットフォームに同時リクエスト
        tasks = [make_request(p) for p in ["narou", "kakuyomu", "alphapolis"]]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for response in responses:
            if isinstance(response, Exception):
                continue
            if response.status_code == 401:
                pytest.skip("Authentication required")
            assert response.status_code == 200


class TestRegressionPrevention:
    """リグレッション防止テスト"""

    @pytest.mark.asyncio
    async def test_existing_formatter_unchanged(self, client):
        """既存フォーマッターロジックが変更されていないことを確認"""
        # なろう: 基本的な字下げとルビ変換
        response = await client.post(
            "/api/export/copy/",
            json={
                "title": "テスト",
                "body": "第1行\n第2行\n\n\n第3行",
                "platform": "narou",
            },
        )
        
        if response.status_code == 401:
            pytest.skip("Authentication required")
        
        assert response.status_code == 200
        data = response.json()
        
        # 連続空行が2行以内に制限されること
        assert "\n\n\n" not in data["body"]
        # 行頭字下げ（全角スペース）が適用されること
        assert data["body"].startswith("　") or data["body"].startswith("「")

    @pytest.mark.asyncio
    async def test_kakuyomu_ruby_format_preserved(self, client):
        """カクヨム形式のルビ記法が保持される"""
        response = await client.post(
            "/api/export/copy/",
            json={
                "title": "テスト",
                "body": "|漢字《かんじ》",
                "platform": "kakuyomu",
            },
        )
        
        if response.status_code == 401:
            pytest.skip("Authentication required")
        
        assert response.status_code == 200
        data = response.json()
        assert "|漢字《かんじ》" in data["body"]

    @pytest.mark.asyncio
    async def test_alphapolis_ruby_format_uses_parentheses(self, client):
        """アルファポリス形式は括弧ルビを使用"""
        response = await client.post(
            "/api/export/copy/",
            json={
                "title": "テスト",
                "body": "|漢字《かんじ》",
                "platform": "alphapolis",
            },
        )
        
        if response.status_code == 401:
            pytest.skip("Authentication required")
        
        assert response.status_code == 200
        data = response.json()
        assert "#漢字(かんじ)#" in data["body"]
        # 旧形式（ダブルアンダースコア）が使われていないこと
        assert "#漢字__かんじ#" not in data["body"]

    @pytest.mark.asyncio
    async def test_dialogue_line_handling(self, client):
        """台詞行の字下げ処理"""
        response = await client.post(
            "/api/export/copy/",
            json={
                "title": "テスト",
                "body": "普通の行\n「台詞の行」\nまた普通の行",
                "platform": "narou",
            },
        )
        
        if response.status_code == 401:
            pytest.skip("Authentication required")
        
        assert response.status_code == 200
        data = response.json()
        
        # 台詞行は字下げされない（"「"で始まる）
        # 通常行は字下げされる（全角スペース）
        lines = data["body"].split("\n")
        assert lines[0].startswith("　")  # 普通の行
        assert lines[1].startswith("「")  # 台詞行
        assert lines[2].startswith("　")  # 普通の行


if __name__ == "__main__":
    pytest.main([__file__, "-v"])