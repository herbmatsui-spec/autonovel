"""
config/container.py - 後方互換ラッパー。

新規コードでは src.core.container.AppContainer を使用すること。
"""
import warnings

from dependency_injector import containers

from src.core.container import AppContainer as _AppContainer

warnings.warn(
    "config.container is deprecated. Please use src.core.container.AppContainer instead.",
    DeprecationWarning,
    stacklevel=2,
)


class Container(_AppContainer):
    wiring_config = containers.WiringConfiguration(packages=["src", "src.kernels", "prompts"])


_container_singleton = None


def get_container():
    global _container_singleton
    if _container_singleton is None:
        _container_singleton = Container()
    return _container_singleton

