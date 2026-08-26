"""
config/container.py - 後方互換ラッパー。

新規コードでは src.core.container.AppContainer を使用すること。
"""
from src.core.container import AppContainer

Container = AppContainer


def get_container():
    """後方互換用: AppContainer クラス (またはそのシングルトン) を返す"""
    return AppContainer
