"""
src/services/publishers/credentials.py - 認証情報管理（CredentialStore）

環境変数・キーリング・暗号化ファイルからの認証情報読み込み・管理。
"""

from __future__ import annotations

import os
import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

from cryptography.fernet import Fernet

from src.services.publishers.base import PublisherCredentials
from src.services.publishers.narou import NarouCredentials
from src.services.publishers.kakuyomu import KakuyomuCredentials
from src.services.publishers.kobo import KoboCredentials
from src.services.publishers.kindle import KindleCredentials

logger = logging.getLogger(__name__)


@dataclass
class CredentialConfig:
    """認証情報ストア設定"""

    use_keyring: bool = True
    use_env: bool = True
    use_encrypted_file: bool = True
    encrypted_file_path: str = "~/.autonovel/credentials.enc"
    key_file_path: str = "~/.autonovel/credential.key"


class CredentialStore:
    """
    プラットフォーム別認証情報を統合管理するストア。

    優先順位:
    1. 環境変数（最優先・上書き可能）
    2. キーリング（OS標準の安全なストレージ）
    3. 暗号化ファイル（永続化用）
    """

    # 環境変数マッピング
    ENV_MAPPING = {
        "narou": {
            "email": "NAROU_EMAIL",
            "password": "NAROU_PASSWORD",
        },
        "kakuyomu": {
            "api_token": "KAKUYOMU_API_TOKEN",
            "user_id": "KAKUYOMU_USER_ID",
        },
        "kobo": {
            "client_id": "KOBO_CLIENT_ID",
            "client_secret": "KOBO_CLIENT_SECRET",
            "access_token": "KOBO_ACCESS_TOKEN",
            "refresh_token": "KOBO_REFRESH_TOKEN",
            "publisher_id": "KOBO_PUBLISHER_ID",
        },
        "kindle": {
            "client_id": "KINDLE_CLIENT_ID",
            "client_secret": "KINDLE_CLIENT_SECRET",
            "refresh_token": "KINDLE_REFRESH_TOKEN",
            "marketplace_id": "KINDLE_MARKETPLACE_ID",
        },
    }

    def __init__(self, config: Optional[CredentialConfig] = None):
        self.config = config or CredentialConfig()
        self._keyring = None
        self._fernet = None
        self._init_keyring()
        self._init_encryption()

    def _init_keyring(self):
        """キーリング初期化"""
        if not self.config.use_keyring:
            return
        try:
            import keyring

            self._keyring = keyring
            logger.debug("キーリング初期化完了")
        except ImportError:
            logger.warning(
                "keyringライブラリが見つかりません。pip install keyring でインストール可能です。"
            )
            self.config.use_keyring = False

    def _init_encryption(self):
        """暗号化初期化（Fernet）"""
        if not self.config.use_encrypted_file:
            return

        key_path = Path(self.config.key_file_path).expanduser()
        key_path.parent.mkdir(parents=True, exist_ok=True)

        if key_path.exists():
            with open(key_path, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_path, "wb") as f:
                f.write(key)
            # パーミッション制限
            key_path.chmod(0o600)

        self._fernet = Fernet(key)
        logger.debug("暗号化初期化完了")

    def _get_keyring_key(self, platform: str, field: str) -> str:
        """キーリング用キー生成"""
        return f"autonovel_{platform}_{field}"

    def _load_from_env(self, platform: str) -> dict[str, Any]:
        """環境変数から認証情報読み込み"""
        if not self.config.use_env:
            return {}

        mapping = self.ENV_MAPPING.get(platform, {})
        creds = {}
        for field, env_var in mapping.items():
            value = os.environ.get(env_var)
            if value:
                creds[field] = value
        return creds

    def _load_from_keyring(self, platform: str) -> dict[str, Any]:
        """キーリングから認証情報読み込み"""
        if not self._keyring:
            return {}

        mapping = self.ENV_MAPPING.get(platform, {})
        creds = {}
        for field in mapping.keys():
            try:
                value = self._keyring.get_password(
                    "autonovel", self._get_keyring_key(platform, field)
                )
                if value:
                    creds[field] = value
            except Exception as e:
                logger.debug(f"キーリング読み込みエラー ({platform}.{field}): {e}")
        return creds

    def _load_from_encrypted_file(self, platform: str) -> dict[str, Any]:
        """暗号化ファイルから認証情報読み込み"""
        if not self._fernet:
            return {}

        file_path = Path(self.config.encrypted_file_path).expanduser()
        if not file_path.exists():
            return {}

        try:
            with open(file_path, "rb") as f:
                encrypted_data = f.read()

            decrypted = self._fernet.decrypt(encrypted_data)
            all_creds = json.loads(decrypted.decode())
            return all_creds.get(platform, {})
        except Exception as e:
            logger.warning(f"暗号化ファイル読み込みエラー: {e}")
            return {}

    def _save_to_keyring(self, platform: str, creds: dict[str, Any]):
        """キーリングへ認証情報保存"""
        if not self._keyring:
            return

        for field, value in creds.items():
            if value:
                try:
                    self._keyring.set_password(
                        "autonovel", self._get_keyring_key(platform, field), value
                    )
                except Exception as e:
                    logger.warning(f"キーリング保存エラー ({platform}.{field}): {e}")

    def _save_to_encrypted_file(self, platform: str, creds: dict[str, Any]):
        """暗号化ファイルへ認証情報保存"""
        if not self._fernet:
            return

        file_path = Path(self.config.encrypted_file_path).expanduser()
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 既存データ読み込み
        all_creds = {}
        if file_path.exists():
            try:
                with open(file_path, "rb") as f:
                    encrypted_data = f.read()
                decrypted = self._fernet.decrypt(encrypted_data)
                all_creds = json.loads(decrypted.decode())
            except Exception:
                all_creds = {}

        # 更新
        all_creds[platform] = creds

        # 暗号化保存
        try:
            encrypted = self._fernet.encrypt(json.dumps(all_creds).encode())
            with open(file_path, "wb") as f:
                f.write(encrypted)
            file_path.chmod(0o600)
        except Exception as e:
            logger.error(f"暗号化ファイル保存エラー: {e}")

    def get(self, platform: str) -> PublisherCredentials:
        """
        認証情報を取得（優先順位: 環境変数 > キーリング > 暗号化ファイル）

        Args:
            platform: プラットフォーム名

        Returns:
            該当プラットフォームの認証情報オブジェクト
        """
        # 1. 環境変数（最優先）
        env_creds = self._load_from_env(platform)

        # 2. キーリング
        keyring_creds = self._load_from_keyring(platform)

        # 3. 暗号化ファイル
        file_creds = self._load_from_encrypted_file(platform)

        # マージ（環境変数が優先）
        merged = {**file_creds, **keyring_creds, **env_creds}

        # 認証情報クラスでインスタンス化
        creds_class = _get_credentials_class(platform)
        return creds_class(**merged)

    def set(self, platform: str, credentials: PublisherCredentials):
        """
        認証情報を保存（キーリング + 暗号化ファイル）

        Args:
            platform: プラットフォーム名
            credentials: 保存する認証情報オブジェクト
        """
        # dataclassをdictに変換（platform, extraは除外）
        creds_dict = {
            k: v
            for k, v in asdict(credentials).items()
            if k not in ("platform", "extra") and v is not None and v != ""
        }

        self._save_to_keyring(platform, creds_dict)
        self._save_to_encrypted_file(platform, creds_dict)

        logger.info(f"認証情報保存完了: {platform}")

    def validate(self, platform: str) -> bool:
        """
        認証情報が有効か検証（必須フィールドの存在確認）

        Args:
            platform: プラットフォーム名

        Returns:
            有効ならTrue
        """
        creds = self.get(platform)

        required_fields = {
            "narou": ["email", "password"],
            "kakuyomu": ["api_token"],
            "kobo": ["client_id", "client_secret"],
            "kindle": ["client_id", "client_secret", "refresh_token"],
        }

        required = required_fields.get(platform, [])
        for field in required:
            value = getattr(creds, field, None)
            if not value:
                logger.warning(f"必須フィールド不足: {platform}.{field}")
                return False

        return True

    def delete(self, platform: str):
        """認証情報を削除"""
        if self._keyring:
            mapping = self.ENV_MAPPING.get(platform, {})
            for field in mapping.keys():
                try:
                    self._keyring.delete_password(
                        "autonovel", self._get_keyring_key(platform, field)
                    )
                except Exception:
                    pass

        # 暗号化ファイルからも削除
        if self._fernet:
            file_path = Path(self.config.encrypted_file_path).expanduser()
            if file_path.exists():
                try:
                    with open(file_path, "rb") as f:
                        encrypted_data = f.read()
                    decrypted = self._fernet.decrypt(encrypted_data)
                    all_creds = json.loads(decrypted.decode())
                    if platform in all_creds:
                        del all_creds[platform]
                        encrypted = self._fernet.encrypt(json.dumps(all_creds).encode())
                        with open(file_path, "wb") as f:
                            f.write(encrypted)
                except Exception as e:
                    logger.warning(f"暗号化ファイル削除エラー: {e}")

        logger.info(f"認証情報削除完了: {platform}")

    def list_configured(self) -> list[str]:
        """設定済みプラットフォーム一覧"""
        configured = []
        for platform in self.ENV_MAPPING.keys():
            if self.validate(platform):
                configured.append(platform)
        return configured

    def get_env_template(self) -> str:
        """.env.template 用の環境変数定義を生成"""
        lines = ["# AutoNovel Publisher Credentials", ""]
        for platform, fields in self.ENV_MAPPING.items():
            lines.append(f"# {platform.upper()}")
            for field, env_var in fields.items():
                lines.append(f"{env_var}=")
            lines.append("")
        return "\n".join(lines)


# 認証情報クラスマッピング（循環インポート回避のためローカル定義）
_CREDENTIALS_CLASSES = {
    "narou": NarouCredentials,
    "kakuyomu": KakuyomuCredentials,
    "kobo": KoboCredentials,
    "kindle": KindleCredentials,
}


def _get_credentials_class(platform: str) -> type[PublisherCredentials]:
    """プラットフォーム名から認証情報クラスを取得"""
    cls = _CREDENTIALS_CLASSES.get(platform)
    if not cls:
        raise ValueError(f"Unknown credentials class for: {platform}")
    return cls


# グローバルインスタンス
_credential_store: Optional[CredentialStore] = None


def get_credential_store(config: Optional[CredentialConfig] = None) -> CredentialStore:
    """グローバルCredentialStoreインスタンス取得"""
    global _credential_store
    if _credential_store is None:
        _credential_store = CredentialStore(config)
    return _credential_store


def create_env_file(path: str = ".env.example"):
    """環境変数テンプレートファイル生成"""
    store = get_credential_store()
    content = store.get_env_template()
    with open(path, "w") as f:
        f.write(content)
    logger.info(f"環境変数テンプレート生成: {path}")
