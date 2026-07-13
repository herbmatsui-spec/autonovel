import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Callable

logger = logging.getLogger(__name__)

class ExecutorManager:
    """
    役割別に最適化されたThreadPoolExecutorを管理するシングルトンクラス。
    asyncio.to_thread (デフォルトプール) への依存を減らし、
    I/Oバウンド処理とCPUバウンド処理を分離して効率化する。
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExecutorManager, cls).__new__(cls)
            # I/Oバウンド処理用: 待機時間が長いため、多めのスレッドを確保
            cls._instance.io_executor = ThreadPoolExecutor(
                max_workers=32,
                thread_name_prefix="LLM_IO_Pool"
            )
            # CPUバウンド処理用: 計算負荷が高いため、コア数に近い数に制限してコンテキストスイッチを抑制
            # (Embedding計算などの重い処理用)
            cls._instance.cpu_executor = ThreadPoolExecutor(
                max_workers=8,
                thread_name_prefix="LLM_CPU_Pool"
            )
            logger.info("ExecutorManager initialized with IO and CPU pools.")
        return cls._instance

    async def run_io(self, func: Callable, *args, **kwargs) -> Any:
        """I/Oバウンドな処理をIOプールで実行する"""
        loop = asyncio.get_running_loop()
        # partialを使用してkwargsを関数にバインド
        p_func = partial(func, *args, **kwargs)
        return await loop.run_in_executor(self.io_executor, p_func)

    async def run_cpu(self, func: Callable, *args, **kwargs) -> Any:
        """CPUバウンドな処理をCPUプールで実行する"""
        loop = asyncio.get_running_loop()
        p_func = partial(func, *args, **kwargs)
        return await loop.run_in_executor(self.cpu_executor, p_func)

    def shutdown(self):
        """プールのシャットダウン"""
        self.io_executor.shutdown(wait=True)
        self.cpu_executor.shutdown(wait=True)
        logger.info("ExecutorManager pools shutdown complete.")

# シングルトンインスタンスを提供
executor_manager = ExecutorManager()
