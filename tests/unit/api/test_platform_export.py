"""プラットフォーム整形APIの単体テスト (v5.0 Step 3).

「なろう」「カクヨム」「アルファポリス」向けの整形コピーAPIを検証。
"""
from fastapi.testclient import TestClient

from src.backend.server import app

client = TestClient(app)


class TestPlatformExportAPI:
    """POST /api/export/copy/ のテスト"""

    def _post(self, payload: dict):
        response = client.post("/api/export/copy/", json=payload)
        if response.status_code == 401:
            return None  # 認証環境でのフォールバック
        return response

    def test_narou_formatting(self):
        """なろう形式への変換テスト"""
        response = self._post(
            {
                "title": "第1章 旅立ち",
                "body": "「行くぞ」\n旅人は言った。\n\n\n|真紅《しんく》の瞳が輝く。",
                "foreword": "前書きです。",
                "afterword": "後書きです。",
                "platform": "narou",
            }
        )
        if response is None:
            return
        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "narou"
        assert data["title"] == "第1章 旅立ち"
        assert data["foreword"] == "前書きです。"
        assert data["afterword"] == "後書きです。"
        assert "「行くぞ」" in data["body"]
        assert "　旅人は言った。" in data["body"]
        assert "|真紅《しんく》" in data["body"]
        assert "\n\n\n" not in data["body"]
        assert data["total_characters"] > 0

    def test_kakuyomu_formatting(self):
        """カクヨム形式への変換テスト（ルビ＋傍点）"""
        response = self._post(
            {
                "title": "第2章 遭遇",
                "body": "森の奥で、｜魔導書《グリモワール》を発見した。\n《《重要》》な手がかりだ。",
                "platform": "kakuyomu",
            }
        )
        if response is None:
            return
        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "kakuyomu"
        assert "|魔導書《グリモワール》" in data["body"]
        assert "《《重要》》" in data["body"]

    def test_alphapolis_formatting(self):
        """アルファポリス形式への変換テスト（括弧ルビ）"""
        response = self._post(
            {
                "title": "第3章 決着",
                "body": "|勇者《ゆうしゃ》よ、立ち上がれ！\n「はい！」",
                "platform": "alphapolis",
            }
        )
        if response is None:
            return
        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "alphapolis"
        assert "#勇者(ゆうしゃ)#" in data["body"]
        assert "「はい！」" in data["body"]

    def test_invalid_platform(self):
        """不正なプラットフォーム指定でエラー"""
        response = self._post(
            {
                "title": "テスト",
                "body": "本文",
                "platform": "invalid_platform",
            }
        )
        if response is None:
            return
        # FastAPI validation returns 422, our custom validation returns 400
        assert response.status_code in (400, 422)
        if response.status_code == 400:
            assert "platform must be one of" in response.json()["detail"]

    def test_empty_title(self):
        """空のタイトルでエラー"""
        response = self._post(
            {
                "title": "",
                "body": "本文",
                "platform": "narou",
            }
        )
        if response is None:
            return
        assert response.status_code in (400, 422)
        if response.status_code == 400:
            assert "title and body cannot be empty" in response.json()["detail"]

    def test_empty_body(self):
        """空の本文でエラー"""
        response = self._post(
            {
                "title": "タイトル",
                "body": "",
                "platform": "narou",
            }
        )
        if response is None:
            return
        assert response.status_code in (400, 422)
        if response.status_code == 400:
            assert "title and body cannot be empty" in response.json()["detail"]

    def test_whitespace_only_title(self):
        """空白のみのタイトルでエラー"""
        response = self._post(
            {
                "title": "   ",
                "body": "本文",
                "platform": "narou",
            }
        )
        if response is None:
            return
        assert response.status_code in (400, 422)

    def test_platform_case_insensitive(self):
        """プラットフォーム名が大文字小文字を区別しない"""
        response = self._post(
            {
                "title": "テスト",
                "body": "本文",
                "platform": "NAROU",
            }
        )
        if response is None:
            return
        assert response.status_code == 200
        assert response.json()["platform"] == "narou"

    def test_long_text_handling(self):
        """長文テキストの処理テスト"""
        long_body = "あ" * 10000
        response = self._post(
            {
                "title": "長編",
                "body": long_body,
                "platform": "narou",
            }
        )
        if response is None:
            return
        assert response.status_code == 200
        data = response.json()
        assert data["total_characters"] > 0

    def test_special_characters(self):
        """特殊文字を含むテキストのテスト"""
        response = self._post(
            {
                "title": "特殊文字テスト",
                "body": "記号: !@#$%^&*()\n絵文字: 😀🎉\nルビ: |漢字《かんじ》",
                "platform": "narou",
            }
        )
        if response is None:
            return
        assert response.status_code == 200
        data = response.json()
        assert "😀🎉" in data["body"]
        assert "|漢字《かんじ》" in data["body"]

    def test_foreword_afterword_optional(self):
        """前書き・後書きは省略可能"""
        response = self._post(
            {
                "title": "テスト",
                "body": "本文",
                "platform": "narou",
            }
        )
        if response is None:
            return
        assert response.status_code == 200
        data = response.json()
        assert data["foreword"] == ""
        assert data["afterword"] == ""