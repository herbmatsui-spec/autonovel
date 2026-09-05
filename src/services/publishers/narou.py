"""
src/services/publishers/narou.py - 小説家になろう Publisher

注意: なろうは公式APIを提供していないため、Seleniumベースのブラウザ自動化で実装。
本番環境では専用のヘッドレスChromeコンテナ等での実行を推奨。
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urljoin

from src.services.publishers.base import (
    PublisherAdapter,
    PublisherCredentials,
    PublishResult,
    AuthError,
    RateLimitError,
    ValidationError,
    NetworkError,
    async_retry,
)

logger = logging.getLogger(__name__)


@dataclass
class NarouCredentials(PublisherCredentials):
    """なろう認証情報"""

    email: str = ""
    password: str = ""
    user_id: str = ""  # ログイン後のユーザーID（マイページURLから取得）

    def __post_init__(self):
        self.platform = "narou"


class NarouPublisher(PublisherAdapter):
    """小説家になろう 投稿アダプタ（Seleniumベース）"""

    platform = "narou"
    description = "小説家になろう（Seleniumブラウザ自動化）"

    # なろうのレート制限は厳しめに設定
    rate_limit_per_minute: int = 10
    rate_limit_per_hour: int = 100

    # URL定数
    BASE_URL = "https://syosetu.com"
    LOGIN_URL = "https://ssl.syosetu.com/login/"
    MY_PAGE_URL = "https://mypage.syosetu.com/"
    NOVEL_NEW_URL = "https://mypage.syosetu.com/novelnew/"
    NOVEL_EDIT_URL = "https://mypage.syosetu.com/novelmain/"
    EPISODE_POST_URL = "https://mypage.syosetu.com/novelmanage/"

    def __init__(self, headless: bool = True, timeout: int = 30):
        super().__init__()
        self.headless = headless
        self.timeout = timeout
        self._driver = None
        self._logged_in = False

    def _get_driver(self):
        """Selenium WebDriverを遅延初期化"""
        if self._driver is None:
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
            except ImportError as e:
                raise RuntimeError(
                    "Selenium/ChromeDriverが必要です。"
                    "pip install selenium webdriver-manager を実行してください。"
                ) from e

            options = Options()
            if self.headless:
                options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")

            service = Service(ChromeDriverManager().install())
            self._driver = webdriver.Chrome(service=service, options=options)
            self._driver.set_page_load_timeout(self.timeout)

        return self._driver

    def _close_driver(self):
        """WebDriverをクローズ"""
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None
            self._logged_in = False

    async def authenticate(self, credentials: NarouCredentials) -> bool:
        """なろうにログイン"""
        if not credentials.email or not credentials.password:
            raise AuthError("メールアドレスとパスワードが必要です", self.platform)

        driver = self._get_driver()

        try:
            # ログインページへ
            driver.get(self.LOGIN_URL)
            await asyncio.sleep(1)

            # ログインフォーム入力
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            wait = WebDriverWait(driver, self.timeout)

            email_input = wait.until(EC.presence_of_element_located((By.NAME, "mail")))
            email_input.clear()
            email_input.send_keys(credentials.email)

            password_input = driver.find_element(By.NAME, "password")
            password_input.clear()
            password_input.send_keys(credentials.password)

            # ログインボタンクリック
            login_btn = driver.find_element(
                By.CSS_SELECTOR, "input[type='submit'][value='ログイン']"
            )
            login_btn.click()

            # ログイン完了待機
            await asyncio.sleep(2)

            # マイページにリダイレクトされることを確認
            if "mypage.syosetu.com" not in driver.current_url:
                # エラーメッセージ確認
                try:
                    error_elem = driver.find_element(By.CSS_SELECTOR, ".error, .alert, .warning")
                    raise AuthError(f"ログイン失敗: {error_elem.text}", self.platform)
                except Exception:
                    raise AuthError(
                        "ログインに失敗しました（リダイレクトされませんでした）", self.platform
                    )

            # ユーザーID取得（マイページURLから）
            match = re.search(r"/(\d+)/", driver.current_url)
            if match:
                credentials.user_id = match.group(1)

            self._logged_in = True
            logger.info("なろうログイン成功", extra={"user_id": credentials.user_id})
            return True

        except AuthError:
            raise
        except Exception as e:
            logger.exception("なろう認証エラー")
            self._close_driver()
            raise AuthError(f"認証中にエラーが発生しました: {e}", self.platform)

    @async_retry(max_attempts=3, base_delay=5.0)
    async def publish(
        self, novel: dict[str, Any], chapter: dict[str, Any], credentials: NarouCredentials
    ) -> PublishResult:
        """新規小説投稿（第1話）"""
        if not self._logged_in:
            await self.authenticate(credentials)

        driver = self._get_driver()

        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait, Select
            from selenium.webdriver.support import expected_conditions as EC

            wait = WebDriverWait(driver, self.timeout)

            # 小説新規作成ページへ
            driver.get(self.NOVEL_NEW_URL)
            await asyncio.sleep(1)

            # タイトル入力
            title_input = wait.until(EC.presence_of_element_located((By.NAME, "title")))
            title_input.clear()
            title_input.send_keys(novel.get("title", "無題")[:100])  # なろうは100文字制限

            # あらすじ入力
            synopsis_area = driver.find_element(By.NAME, "story")
            synopsis_area.clear()
            synopsis_area.send_keys(novel.get("synopsis", "")[:2000])  # 2000文字制限

            # ジャンル選択（デフォルト: 一般文芸）
            genre_select = Select(driver.find_element(By.NAME, "genre"))
            genre_map = {
                "fantasy": "101",  # ファンタジー
                "sf": "102",  # SF
                "horror": "103",  # ホラー
                "mystery": "104",  # ミステリー
                "romance": "105",  # 恋愛
                "general": "9901",  # 一般文芸
            }
            genre_value = genre_map.get(novel.get("genre", "general"), "9901")
            genre_select.select_by_value(genre_value)

            # キーワード設定
            if novel.get("keywords"):
                keyword_input = driver.find_element(By.NAME, "keyword")
                keyword_input.send_keys(", ".join(novel["keywords"])[:200])

            # R18設定
            if novel.get("is_adult"):
                try:
                    r18_checkbox = driver.find_element(By.NAME, "isr18")
                    if not r18_checkbox.is_selected():
                        r18_checkbox.click()
                except Exception:
                    pass  # チェックボックスが見つからない場合はスキップ

            # 第1話本文入力
            episode_title_input = driver.find_element(By.NAME, "episodetitle1")
            episode_title_input.clear()
            episode_title_input.send_keys(chapter.get("title", "第1話")[:100])

            episode_body_area = driver.find_element(By.NAME, "episodebody1")
            episode_body_area.clear()
            episode_body_area.send_keys(self._format_for_narou(chapter.get("content", "")))

            # 確認画面へ
            confirm_btn = driver.find_element(
                By.CSS_SELECTOR, "input[type='submit'][value='確認画面へ']"
            )
            confirm_btn.click()
            await asyncio.sleep(1)

            # 確認画面で「登録する」ボタンをクリック
            register_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "input[type='submit'][value='登録する']")
                )
            )
            register_btn.click()
            await asyncio.sleep(2)

            # 投稿完了後のURLから小説IDを抽出
            current_url = driver.current_url
            novel_id_match = re.search(r"/novel/(\d+)/", current_url)

            if not novel_id_match:
                # マイページに戻った場合、最新の小説IDを取得
                driver.get(self.MY_PAGE_URL)
                await asyncio.sleep(1)
                # 「作品管理」リンクから最新作品を探す
                novel_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/novelmanage/']")
                if novel_links:
                    novel_id_match = re.search(
                        r"/novelmanage/(\d+)/", novel_links[0].get_attribute("href")
                    )

            if novel_id_match:
                novel_id = novel_id_match.group(1)
                post_url = f"https://ncode.syosetu.com/n{novel_id}/"
                return PublishResult(
                    success=True,
                    platform=self.platform,
                    post_id=novel_id,
                    url=post_url,
                    metadata={"novel_id": novel_id, "episode": 1},
                )
            else:
                raise ValidationError("投稿後の小説IDを取得できませんでした", self.platform)

        except ValidationError:
            raise
        except Exception as e:
            logger.exception("なろう投稿エラー")
            # レート制限判定
            if "アクセスが集中" in str(e) or "しばらく経ってから" in str(e):
                raise RateLimitError(
                    "アクセス集中のため投稿できません", self.platform, retry_after=300
                )
            raise NetworkError(f"投稿中にエラーが発生しました: {e}", self.platform)

    @async_retry(max_attempts=3, base_delay=5.0)
    async def update_chapter(
        self, post_id: str, chapter: dict[str, Any], credentials: NarouCredentials
    ) -> PublishResult:
        """既存小説に話を追加（第2話以降）"""
        if not self._logged_in:
            await self.authenticate(credentials)

        driver = self._get_driver()

        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            wait = WebDriverWait(driver, self.timeout)

            # 作品管理ページへ
            manage_url = f"{self.EPISODE_POST_URL}{post_id}/"
            driver.get(manage_url)
            await asyncio.sleep(1)

            # 「新しい話を追加」ボタンを探してクリック
            add_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "a[href*='noveladd/'], input[value='新しい話を追加']")
                )
            )
            add_btn.click()
            await asyncio.sleep(1)

            # 話数を特定（既存話数+1）
            episode_num = chapter.get("ep_num", 1)

            # タイトル入力
            title_input = wait.until(
                EC.presence_of_element_located((By.NAME, f"episodetitle{episode_num}"))
            )
            title_input.clear()
            title_input.send_keys(chapter.get("title", f"第{episode_num}話")[:100])

            # 本文入力
            body_area = driver.find_element(By.NAME, f"episodebody{episode_num}")
            body_area.clear()
            body_area.send_keys(self._format_for_narou(chapter.get("content", "")))

            # 確認画面へ
            confirm_btn = driver.find_element(
                By.CSS_SELECTOR, "input[type='submit'][value='確認画面へ']"
            )
            confirm_btn.click()
            await asyncio.sleep(1)

            # 登録
            register_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "input[type='submit'][value='登録する']")
                )
            )
            register_btn.click()
            await asyncio.sleep(2)

            post_url = f"https://ncode.syosetu.com/n{post_id}/{episode_num}/"
            return PublishResult(
                success=True,
                platform=self.platform,
                post_id=post_id,
                url=post_url,
                metadata={"novel_id": post_id, "episode": episode_num},
            )

        except Exception as e:
            logger.exception("なろう話追加エラー")
            if "アクセスが集中" in str(e):
                raise RateLimitError(
                    "アクセス集中のため話追加できません", self.platform, retry_after=300
                )
            raise NetworkError(f"話追加中にエラーが発生しました: {e}", self.platform)

    async def get_post_status(self, post_id: str, credentials: NarouCredentials) -> dict[str, Any]:
        """投稿ステータス取得（公開状態、閲覧数等）"""
        if not self._logged_in:
            await self.authenticate(credentials)

        driver = self._get_driver()

        try:
            driver.get(f"https://ncode.syosetu.com/n{post_id}/")
            await asyncio.sleep(1)

            from selenium.webdriver.common.by import By

            # 基本情報取得
            title_elem = driver.find_element(By.CSS_SELECTOR, ".novel_title, h1")
            title = title_elem.text if title_elem else "不明"

            # 話数取得
            episode_links = driver.find_elements(By.CSS_SELECTOR, ".index_box a[href*='.html']")
            episode_count = len(episode_links)

            # 閲覧数等（マイページから取得する方が確実）
            driver.get(f"{self.MY_PAGE_URL}{credentials.user_id}/novelmanage/{post_id}/")
            await asyncio.sleep(1)

            return {
                "novel_id": post_id,
                "title": title,
                "episode_count": episode_count,
                "status": "published",
                "url": f"https://ncode.syosetu.com/n{post_id}/",
            }

        except Exception as e:
            logger.warning(f"ステータス取得失敗: {e}")
            return {"novel_id": post_id, "status": "unknown", "error": str(e)}

    def _format_for_narou(self, content: str) -> str:
        """なろう用フォーマット変換（既存Exporterのロジックを流用）"""
        # 改行正規化
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        content = re.sub(r"\n{3,}", "\n\n", content)

        # ルビ記法 |漢字《かんじ》| はそのまま（なろう対応済み）
        # 画像プレースホルダを除去
        content = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"[画像: \1]", content)

        return content.strip()

    async def close(self):
        """リソース解放"""
        self._close_driver()

    def __del__(self):
        self._close_driver()


# 同期版メソッドも提供（テスト用）
def create_narou_publisher(headless: bool = True) -> NarouPublisher:
    """ファクトリ関数"""
    return NarouPublisher(headless=headless)
