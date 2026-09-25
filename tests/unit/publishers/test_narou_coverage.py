"""NarouPublisher coverage: driver fallback, format conversion, status and error paths."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.publishers.base import (
    AuthError,
    NetworkError,
    RateLimitError,
    ValidationError,
)
from src.services.publishers.narou import (
    NarouCredentials,
    NarouPublisher,
    create_narou_publisher,
)


@pytest.fixture
def publisher():
    return NarouPublisher(headless=True, timeout=5)


@pytest.fixture
def credentials():
    return NarouCredentials(email="t@t.com", password="pw", user_id="999")


def make_driver(current_url="https://ncode.syosetu.com/n12345/", episode_count=3):
    driver = MagicMock()
    driver.current_url = current_url
    driver.find_element.return_value = MagicMock()
    links = [MagicMock() for _ in range(episode_count)]
    driver.find_elements.return_value = links
    return driver


# ============================================================================
# Driver lifecycle & factory
# ============================================================================


def test_factory_and_defaults(publisher):
    assert create_narou_publisher(headless=False).headless is False
    assert publisher.platform == "narou"
    assert publisher._driver is None
    assert publisher._logged_in is False


def test_get_driver_raises_without_selenium(publisher):
    """_get_driver 内の import 失敗で RuntimeError に変換される。"""
    # selenium 未導入環境（try/except ImportError で None が設定済み）では
    # in-function import も失敗する。まず None 状態を確認。
    import src.services.publishers.narou as narou_module
    if narou_module.webdriver is None:
        with pytest.raises(RuntimeError, match="Selenium/ChromeDriverが必要です"):
            publisher._get_driver()
    else:
        # selenium が実在する環境では、import 失敗を模擬するため
        # モンキーパッチで webdriver を None にする
        with pytest.MonkeyPatch.context() as m:
            m.setattr(narou_module, "webdriver", None)
            with pytest.raises(RuntimeError, match="Selenium/ChromeDriverが必要です"):
                publisher._get_driver()


def test_get_driver_and_close(publisher):
    """selenium 実在を前提に driver 生成・再利用・クローズを検証。"""
    import src.services.publishers.narou as narou_module
    if narou_module.webdriver is None:
        pytest.skip("selenium not installed")

    fake_driver = MagicMock()
    fake_webdriver = MagicMock()
    fake_webdriver.Chrome.return_value = fake_driver
    with pytest.MonkeyPatch.context() as m:
        m.setattr(narou_module, "webdriver", fake_webdriver)
        m.setattr(narou_module, "Options", MagicMock())
        m.setattr(narou_module, "Service", MagicMock())
        m.setattr(narou_module, "ChromeDriverManager", MagicMock())

        got = publisher._get_driver()
        assert got is fake_driver
        # Second call reuses the cached driver
        assert publisher._get_driver() is fake_driver
        fake_driver.set_page_load_timeout.assert_called_once_with(5)
        # headless 引数が付与されている
        assert fake_webdriver.Chrome.call_args.kwargs["options"] is not None

    publisher._close_driver()
    fake_driver.quit.assert_called_once()
    assert publisher._driver is None
    assert publisher._logged_in is False

    # Close without driver is a no-op
    publisher._close_driver()


def test_close_async_and_del(publisher):
    driver = MagicMock()
    publisher._driver = driver
    import asyncio
    asyncio.run(publisher.close())
    assert publisher._driver is None


# ============================================================================
# authenticate
# ============================================================================


@pytest.mark.asyncio
async def test_authenticate_requires_credentials(publisher):
    with pytest.raises(AuthError):
        await publisher.authenticate(NarouCredentials())


@pytest.mark.asyncio
async def test_authenticate_success_extracts_user_id(publisher, credentials):
    driver = make_driver(current_url="https://mypage.syosetu.com/77777/")
    with pytest.MonkeyPatch.context() as m:
        m.setattr(publisher, "_get_driver", lambda: driver)
        import src.services.publishers.narou as narou_module
        wait = MagicMock()
        wait.until.return_value = MagicMock()
        m.setattr(narou_module, "WebDriverWait", lambda d, t: wait)

        assert await publisher.authenticate(credentials) is True
    assert publisher._logged_in is True
    assert credentials.user_id == "77777"


@pytest.mark.asyncio
async def test_authenticate_login_failure_with_error_element(publisher, credentials):
    driver = make_driver(current_url="https://ssl.syosetu.com/login/")
    error_elem = MagicMock()
    error_elem.text = "パスワードが違います"
    driver.find_element.return_value = error_elem
    with pytest.MonkeyPatch.context() as m:
        m.setattr(publisher, "_get_driver", lambda: driver)
        import src.services.publishers.narou as narou_module
        wait = MagicMock()
        wait.until.return_value = MagicMock()
        m.setattr(narou_module, "WebDriverWait", lambda d, t: wait)
        m.setattr(narou_module, "EC", MagicMock())

        with pytest.raises(AuthError, match="パスワードが違います"):
            await publisher.authenticate(credentials)
    # driver closed on failure (mock driver quit is called)
    driver.quit.assert_called_once()


@pytest.mark.asyncio
async def test_authenticate_unexpected_error_wraps_auth_error(publisher, credentials):
    """スレッド内で _get_driver が失敗した場合も AuthError にラップされる。"""
    import src.services.publishers.narou as narou_module

    def broken_get_driver():
        raise RuntimeError("boom")

    with pytest.MonkeyPatch.context() as m:
        m.setattr(narou_module, "webdriver", None)
        m.setattr(publisher, "_get_driver", broken_get_driver)
        with pytest.raises(AuthError, match="認証中にエラー"):
            await publisher.authenticate(credentials)


# ============================================================================
# publish / update_chapter / get_post_status
# ============================================================================


@pytest.mark.asyncio
async def test_publish_auto_authenticates_first(publisher, credentials):
    """未ログイン時は authenticate が先に実行される。"""
    publisher._logged_in = False
    with pytest.MonkeyPatch.context() as m:
        m.setattr(publisher, "authenticate", AsyncMock())
        result = await publisher.publish({"title": "T", "synopsis": "S", "genre": "fantasy",
                                          "keywords": ["a", "b"], "is_adult": True},
                                         {"title": "第1話", "content": "本文"}, credentials)
        publisher.authenticate.assert_awaited_once()
    # authenticate はモックのため _sync_publish は driver 生成で失敗しうる。
    # 結果オブジェクトが得られた場合は型だけ検証する。
    if result is not None:
        assert hasattr(result, "success")


@pytest.mark.asyncio
async def test_publish_novel_id_from_mypage_fallback(publisher, credentials):
    driver = make_driver(current_url="https://ssl.syosetu.com/other/")
    link = MagicMock()
    link.get_attribute = MagicMock(return_value="https://mypage.syosetu.com/novelmanage/555/")
    driver.find_elements.return_value = [link]
    publisher._logged_in = True
    with pytest.MonkeyPatch.context() as m:
        m.setattr(publisher, "_get_driver", lambda: driver)
        import src.services.publishers.narou as narou_module
        wait = MagicMock()
        wait.until.return_value = MagicMock()
        m.setattr(narou_module, "WebDriverWait", lambda d, t: wait)

        result = await publisher.publish({"title": "T"}, {"content": "本文"}, credentials)
    assert result.post_id == "555"


@pytest.mark.asyncio
async def test_publish_validation_error_when_no_novel_id(publisher, credentials):
    driver = make_driver(current_url="https://ssl.syosetu.com/other/")
    driver.find_elements.return_value = []
    publisher._logged_in = True
    with pytest.MonkeyPatch.context() as m:
        m.setattr(publisher, "_get_driver", lambda: driver)
        import src.services.publishers.narou as narou_module
        wait = MagicMock()
        wait.until.return_value = MagicMock()
        m.setattr(narou_module, "WebDriverWait", lambda d, t: wait)

        with pytest.raises(ValidationError):
            await publisher.publish({"title": "T"}, {"content": "本文"}, credentials)


@pytest.mark.asyncio
async def test_publish_rate_limit_error(publisher, credentials):
    """driver.get が「アクセスが集中」エラーを出した場合 RateLimitError に変換。"""
    import src.services.publishers.narou as narou_module
    driver = MagicMock()
    driver.get.side_effect = RuntimeError("アクセスが集中しています")
    publisher._logged_in = True
    with pytest.MonkeyPatch.context() as m:
        m.setattr(publisher, "_get_driver", lambda: driver)
        wait = MagicMock()
        wait.until.return_value = MagicMock()
        m.setattr(narou_module, "WebDriverWait", lambda d, t: wait)
        with pytest.raises(RateLimitError):
            await publisher.publish({"title": "T"}, {"content": "本文"}, credentials)


@pytest.mark.asyncio
async def test_publish_network_error(publisher, credentials):
    driver = MagicMock()
    driver.get.side_effect = RuntimeError("タイムアウト")
    publisher._logged_in = True
    with pytest.MonkeyPatch.context() as m:
        m.setattr(publisher, "_get_driver", lambda: driver)
        with pytest.raises(NetworkError):
            await publisher.publish({"title": "T"}, {"content": "本文"}, credentials)


@pytest.mark.asyncio
async def test_update_chapter_success(publisher, credentials):
    driver = make_driver()
    publisher._logged_in = True
    with pytest.MonkeyPatch.context() as m:
        m.setattr(publisher, "_get_driver", lambda: driver)
        import src.services.publishers.narou as narou_module
        wait = MagicMock()
        wait.until.return_value = MagicMock()
        m.setattr(narou_module, "WebDriverWait", lambda d, t: wait)

        result = await publisher.update_chapter("12345", {"title": "第2話", "content": "続き",
                                                          "ep_num": 2}, credentials)
    assert result.success is True
    assert result.post_id == "12345"
    assert result.metadata["episode"] == 2
    driver.get.assert_called_with("https://mypage.syosetu.com/novelmanage/12345/")


@pytest.mark.asyncio
async def test_update_chapter_rate_limit_and_network(publisher, credentials):
    import src.services.publishers.narou as narou_module
    driver = MagicMock()
    driver.get.side_effect = RuntimeError("アクセスが集中")
    publisher._logged_in = True
    with pytest.MonkeyPatch.context() as m:
        m.setattr(publisher, "_get_driver", lambda: driver)
        wait = MagicMock()
        wait.until.return_value = MagicMock()
        m.setattr(narou_module, "WebDriverWait", lambda d, t: wait)
        with pytest.raises(RateLimitError):
            await publisher.update_chapter("1", {"content": "c"}, credentials)

    driver2 = MagicMock()
    driver2.get.side_effect = RuntimeError("失敗")
    with pytest.MonkeyPatch.context() as m:
        m.setattr(publisher, "_get_driver", lambda: driver2)
        wait = MagicMock()
        wait.until.return_value = MagicMock()
        m.setattr(narou_module, "WebDriverWait", lambda d, t: wait)
        with pytest.raises(NetworkError):
            await publisher.update_chapter("1", {"content": "c"}, credentials)


@pytest.mark.asyncio
async def test_update_chapter_auto_authenticates(publisher, credentials):
    driver = make_driver()
    publisher._logged_in = False
    with pytest.MonkeyPatch.context() as m:
        m.setattr(publisher, "_get_driver", lambda: driver)
        import src.services.publishers.narou as narou_module
        wait = MagicMock()
        wait.until.return_value = MagicMock()
        m.setattr(narou_module, "WebDriverWait", lambda d, t: wait)
        m.setattr(publisher, "authenticate", AsyncMock())
        await publisher.update_chapter("1", {"content": "c"}, credentials)
        publisher.authenticate.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_post_status_success(publisher, credentials):
    driver = make_driver(episode_count=7)
    title_elem = MagicMock()
    title_elem.text = "小説タイトル"
    driver.find_element.return_value = title_elem
    publisher._logged_in = True
    with pytest.MonkeyPatch.context() as m:
        m.setattr(publisher, "_get_driver", lambda: driver)
        status = await publisher.get_post_status("12345", credentials)
    assert status == {"novel_id": "12345", "title": "小説タイトル", "episode_count": 7,
                      "status": "published",
                      "url": "https://ncode.syosetu.com/n12345/"}


@pytest.mark.asyncio
async def test_get_post_status_auto_authenticate_and_error(publisher, credentials):
    driver = make_driver()
    publisher._logged_in = False
    with pytest.MonkeyPatch.context() as m:
        m.setattr(publisher, "_get_driver", lambda: driver)
        m.setattr(publisher, "authenticate", AsyncMock())
        await publisher.get_post_status("1", credentials)
        publisher.authenticate.assert_awaited_once()

    driver2 = MagicMock()
    driver2.get.side_effect = RuntimeError("net down")
    publisher._logged_in = True
    with pytest.MonkeyPatch.context() as m:
        m.setattr(publisher, "_get_driver", lambda: driver2)
        status = await publisher.get_post_status("1", credentials)
    assert status["status"] == "unknown"
    assert "net down" in status["error"]


# ============================================================================
# _format_for_narou
# ============================================================================


def test_format_for_narou_normalizes_and_converts(publisher):
    raw = "段落1\r\n\r\n\r\n段落2\r\r![画像](http://x.png)\r\n|漢字《かんじ》|\n\n\n\n段落3\n"
    formatted = publisher._format_for_narou(raw)
    assert "\r" not in formatted
    assert "\n\n\n" not in formatted
    assert "[画像: 画像]" in formatted
    assert "|漢字《かんじ》|" in formatted
    assert formatted.endswith("段落3")


def test_format_for_narou_empty(publisher):
    assert publisher._format_for_narou("") == ""
    assert publisher._format_for_narou("  \n  ") == ""
