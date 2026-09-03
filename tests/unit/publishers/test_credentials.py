"""
tests/unit/publishers/test_credentials.py - CredentialStoreテスト
"""

from __future__ import annotations

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from src.services.publishers.credentials import (
    CredentialStore,
    CredentialConfig,
    get_credential_store,
    create_env_file,
)
from src.services.publishers import (
    NarouCredentials,
    KakuyomuCredentials,
    KoboCredentials,
    KindleCredentials,
)


class TestCredentialStore:
    """CredentialStoreテスト"""
    
    @pytest.fixture
    def config(self):
        """テスト用設定"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield CredentialConfig(
                use_keyring=False,
                use_env=True,
                use_encrypted_file=True,
                encrypted_file_path=str(Path(tmpdir) / "credentials.enc"),
                key_file_path=str(Path(tmpdir) / "credential.key"),
            )
    
    @pytest.fixture
    def store(self, config):
        """CredentialStoreインスタンス"""
        return CredentialStore(config)
    
    def test_load_from_env(self, store):
        """環境変数から読み込みテスト"""
        with patch.dict(os.environ, {
            "NAROU_EMAIL": "test@test.com",
            "NAROU_PASSWORD": "password123",
            "KAKUYOMU_API_TOKEN": "token456",
        }):
            narou_creds = store._load_from_env("narou")
            assert narou_creds["email"] == "test@test.com"
            assert narou_creds["password"] == "password123"
            
            kakuyomu_creds = store._load_from_env("kakuyomu")
            assert kakuyomu_creds["api_token"] == "token456"
    
    def test_get_credentials(self, store):
        """認証情報取得テスト"""
        with patch.dict(os.environ, {
            "NAROU_EMAIL": "env@test.com",
            "NAROU_PASSWORD": "env_pass",
        }):
            creds = store.get("narou")
            assert isinstance(creds, NarouCredentials)
            assert creds.email == "env@test.com"
            assert creds.password == "env_pass"
    
    def test_set_and_get_credentials(self, store):
        """認証情報設定・取得テスト"""
        creds = NarouCredentials(email="set@test.com", password="set_pass")
        store.set("narou", creds)
        
        # 環境変数なしで取得
        with patch.dict(os.environ, {}, clear=True):
            retrieved = store.get("narou")
            assert retrieved.email == "set@test.com"
            assert retrieved.password == "set_pass"
    
    def test_validate_success(self, store):
        """バリデーション成功テスト"""
        with patch.dict(os.environ, {
            "NAROU_EMAIL": "test@test.com",
            "NAROU_PASSWORD": "password",
            "KAKUYOMU_API_TOKEN": "token",
            "KOBO_CLIENT_ID": "id",
            "KOBO_CLIENT_SECRET": "secret",
            "KINDLE_CLIENT_ID": "id",
            "KINDLE_CLIENT_SECRET": "secret",
            "KINDLE_REFRESH_TOKEN": "refresh",
        }):
            assert store.validate("narou") is True
            assert store.validate("kakuyomu") is True
            assert store.validate("kobo") is True
            assert store.validate("kindle") is True
    
    def test_validate_failure(self, store):
        """バリデーション失敗テスト"""
        with patch.dict(os.environ, {}, clear=True):
            assert store.validate("narou") is False  # email/password不足
            assert store.validate("kakuyomu") is False  # token不足
            assert store.validate("kobo") is False  # client_id/secret不足
            assert store.validate("kindle") is False  # refresh_token不足
    
    def test_delete_credentials(self, store):
        """認証情報削除テスト"""
        creds = NarouCredentials(email="del@test.com", password="del_pass")
        store.set("narou", creds)
        
        # 存在確認
        with patch.dict(os.environ, {}, clear=True):
            retrieved = store.get("narou")
            assert retrieved.email == "del@test.com"
        
        # 削除
        store.delete("narou")
        
        # 削除確認
        with patch.dict(os.environ, {}, clear=True):
            retrieved = store.get("narou")
            assert retrieved.email == ""
            assert retrieved.password == ""
    
    def test_list_configured(self, store):
        """設定済みプラットフォーム一覧テスト"""
        with patch.dict(os.environ, {
            "NAROU_EMAIL": "test@test.com",
            "NAROU_PASSWORD": "password",
            "KAKUYOMU_API_TOKEN": "token",
        }):
            configured = store.list_configured()
            assert "narou" in configured
            assert "kakuyomu" in configured
            assert "kobo" not in configured
            assert "kindle" not in configured
    
    def test_get_env_template(self, store):
        """環境変数テンプレート生成テスト"""
        template = store.get_env_template()
        
        assert "NAROU_EMAIL=" in template
        assert "NAROU_PASSWORD=" in template
        assert "KAKUYOMU_API_TOKEN=" in template
        assert "KOBO_CLIENT_ID=" in template
        assert "KOBO_CLIENT_SECRET=" in template
        assert "KINDLE_CLIENT_ID=" in template
        assert "KINDLE_CLIENT_SECRET=" in template
        assert "KINDLE_REFRESH_TOKEN=" in template
    
    def test_create_env_file(self, store):
        """環境変数ファイル作成テスト"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            temp_path = f.name
        
        try:
            create_env_file(temp_path)
            
            with open(temp_path) as f:
                content = f.read()
            
            assert "NAROU_EMAIL=" in content
            assert "KAKUYOMU_API_TOKEN=" in content
        finally:
            os.unlink(temp_path)
    
    def test_encrypted_file_persistence(self, store):
        """暗号化ファイル永続化テスト"""
        creds = NarouCredentials(email="enc@test.com", password="enc_pass")
        store.set("narou", creds)
        
        # 新しいstoreインスタンスで読み込み（同じキーファイル使用）
        new_store = CredentialStore(store.config)
        
        with patch.dict(os.environ, {}, clear=True):
            retrieved = new_store.get("narou")
            assert retrieved.email == "enc@test.com"
            assert retrieved.password == "enc_pass"


class TestCredentialConfig:
    """CredentialConfigテスト"""
    
    def test_default_config(self):
        """デフォルト設定テスト"""
        config = CredentialConfig()
        assert config.use_keyring is True
        assert config.use_env is True
        assert config.use_encrypted_file is True
        assert "credentials.enc" in config.encrypted_file_path
        assert "credential.key" in config.key_file_path


class TestGlobalFunctions:
    """グローバル関数テスト"""
    
    def test_get_credential_store_singleton(self):
        """シングルトン取得テスト"""
        store1 = get_credential_store()
        store2 = get_credential_store()
        assert store1 is store2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])