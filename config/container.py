"""
config/container.py - 後方互換ラッパー（遅延インポート版）

新規コードでは src.core.container.AppContainer を使用すること。
"""

def _get_app_container():
    # 遅延インポートで循環を防ぐ
    from src.core.container import AppContainer
    return AppContainer

class _ContainerProxy:
    """属性アクセス時に実際の AppContainer を解決するプロキシ"""
    def __getattr__(self, name):
        return getattr(_get_app_container(), name)

# 後方互換のためのエイリアス
Container = _ContainerProxy()

def get_container():
    """後方互換用: AppContainer クラス (またはそのシングルトン) を返す"""
    return _get_app_container()