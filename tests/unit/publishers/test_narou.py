"""
tests/unit/publishers/test_narou.py - なろうPublisherテスト
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from src.services.publishers.narou import NarouPublisher, NarouCredentials
from src.services.publishers.base import PublishResult, AuthError, RateLimitError, NetworkError


class TestNarouPublisher:
    """NarouPublisherテスト"""
    
    @pytest.fixture
    def publisher(self):
        """Publisherフィクスチャ"""
        with patch("webdriver_manager.chrome.ChromeDriverManager"):
            pub = NarouPublisher(headless=True)
            yield pub
            pub._close_driver()
    
    @pytest.fixture
    def credentials(self):
        """認証情報フィクスチャ"""
        return NarouCredentials(email="test@test.com", password="password123")
    
    def test_publisher_initialization(self, publisher):
        """初期化テスト"""
        assert publisher.platform == "narou"
        assert publisher.description == "小説家になろう（Seleniumブラウザ自動化）"
        assert publisher.rate_limit_per_minute == 10
        assert publisher.rate_limit_per_hour == 100
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, publisher, credentials):
        """認証成功テスト"""
        mock_driver = MagicMock()
        mock_driver.current_url = "https://mypage.syosetu.com/12345/"
        
        # WebDriver関連をモック
        with patch.object(publisher, "_get_driver", return_value=mock_driver):
            with patch("src.services.publishers.narou.WebDriverWait") as mock_wait:
                mock_email = MagicMock()
                mock_password = MagicMock()
                mock_btn = MagicMock()
                
                mock_wait.return_value.until.return_value = mock_email
                mock_driver.find_element.return_value = mock_password
                mock_driver.find_element.return_value = mock_btn  # 2回目の呼び出し
                
                result = await publisher.authenticate(credentials)
        
        assert result is True
        assert publisher._logged_in is True
        assert credentials.user_id == "12345"
    
    @pytest.mark.asyncio
    async def test_authenticate_missing_credentials(self, publisher):
        """認証情報不足テスト"""
        creds = NarouCredentials()  # email/passwordなし
        
        with pytest.raises(AuthError) as exc_info:
            await publisher.authenticate(creds)
        
        assert "メールアドレスとパスワードが必要です" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_authenticate_failed_redirect(self, publisher, credentials):
        """ログイン失敗（リダイレクトされない）テスト"""
        mock_driver = MagicMock()
        mock_driver.current_url = "https://ssl.syosetu.com/login/"  # ログインページのまま
        
        with patch.object(publisher, "_get_driver", return_value=mock_driver):
            with patch("src.services.publishers.narou.WebDriverWait") as mock_wait:
                mock_email = MagicMock()
                mock_password = MagicMock()
                mock_btn = MagicMock()
                
                mock_wait.return_value.until.return_value = mock_email
                mock_driver.find_element.return_value = mock_password
                
                with pytest.raises(AuthError) as exc_info:
                    await publisher.authenticate(credentials)
        
        assert "リダイレクトされませんでした" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_publish_first_episode(self, publisher, credentials):
        """第1話投稿テスト"""
        publisher._logged_in = True
        
        mock_driver = MagicMock()
        mock_driver.current_url = "https://mypage.syosetu.com/novelmanage/67890/"
        
        novel = {"title": "テスト小説", "synopsis": "あらすじ", "genre": "fantasy"}
        chapter = {"ep_num": 1, "title": "第1話", "content": "本文テスト"}
        
        with patch.object(publisher, "_get_driver", return_value=mock_driver):
            with patch("src.services.publishers.narou.WebDriverWait") as mock_wait:
                # 各要素のモック
                mock_elements = {
                    "title": MagicMock(),
                    "story": MagicMock(),
                    "genre": MagicMock(),
                    "keyword": MagicMock(),
                    "episodetitle1": MagicMock(),
                    "episodebody1": MagicMock(),
                    "confirm_btn": MagicMock(),
                    "register_btn": MagicMock(),
                }
                
                def find_element_side_effect(*args, **kwargs):
                    selector = args[1] if len(args) > 1 else kwargs.get("value", "")
                    for key, elem in mock_elements.items():
                        if key in selector or key in str(args):
                            return elem
                    return MagicMock()
                
                mock_driver.find_element.side_effect = find_element_side_effect
                mock_wait.return_value.until.return_value = mock_elements["title"]
                
                result = await publisher.publish(novel, chapter, credentials)
        
        assert result.success is True
        assert result.platform == "narou"
        assert result.post_id == "67890"
        assert "ncode.syosetu.com" in result.url
    
    @pytest.mark.asyncio
    async def test_update_chapter(self, publisher, credentials):
        """第2話以降追加テスト"""
        publisher._logged_in = True
        
        mock_driver = MagicMock()
        mock_driver.current_url = "https://mypage.syosetu.com/novelmanage/67890/"
        
        chapter = {"ep_num": 2, "title": "第2話", "content": "第2話本文"}
        
        with patch.object(publisher, "_get_driver", return_value=mock_driver):
            with patch("src.services.publishers.narou.WebDriverWait") as mock_wait:
                mock_elements = {
                    "add_btn": MagicMock(),
                    "episodetitle2": MagicMock(),
                    "episodebody2": MagicMock(),
                    "confirm_btn": MagicMock(),
                    "register_btn": MagicMock(),
                }
                
                def find_element_side_effect(*args, **kwargs):
                    selector = str(args)
                    for key, elem in mock_elements.items():
                        if key in selector:
                            return elem
                    return MagicMock()
                
                mock_driver.find_element.side_effect = find_element_side_effect
                mock_wait.return_value.until.return_value = mock_elements["add_btn"]
                
                result = await publisher.update_chapter("67890", chapter, credentials)
        
        assert result.success is True
        assert result.post_id == "67890"
        assert result.metadata["episode"] == 2
    
    @pytest.mark.asyncio
    async def test_get_post_status(self, publisher, credentials):
        """ステータス取得テスト"""
        publisher._logged_in = True
        credentials.user_id = "12345"
        
        mock_driver = MagicMock()
        mock_driver.current_url = "https://ncode.syosetu.com/n67890/"
        
        mock_title = MagicMock()
        mock_title.text = "テスト小説"
        mock_episodes = [MagicMock(), MagicMock()]  # 2話分
        
        with patch.object(publisher, "_get_driver", return_value=mock_driver):
            mock_driver.find_element.return_value = mock_title
            mock_driver.find_elements.return_value = mock_episodes
            
            status = await publisher.get_post_status("67890", credentials)
        
        assert status["novel_id"] == "67890"
        assert status["title"] == "テスト小説"
        assert status["episode_count"] == 2
        assert status["status"] == "published"
    
    def test_format_for_narou(self, publisher):
        """なろう用フォーマット変換テスト"""
        content = "第1行\r\n第2行\r第3行\n\n\n第4行"
        formatted = publisher._format_for_narou(content)
        
        assert "\r" not in formatted
        # 3つ以上の連続改行が2つに制限される
        assert "\n\n\n" not in formatted
        
        # 画像プレースホルダ変換
        content_with_image = "テスト ![画像](http://example.com/img.png) 続き"
        formatted = publisher._format_for_narou(content_with_image)
        assert "[画像: 画像]" in formatted
    
    def test_format_preserves_ruby(self, publisher):
        """ルビ記法保持テスト"""
        content = "漢字《かんじ》と|難読《なんどく》|"
        formatted = publisher._format_for_narou(content)
        assert "漢字《かんじ》" in formatted
        assert "|難読《なんどく》|" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])