from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, TypeVar

from pydantic import BaseModel

# 入出力データの型を定義するためのTypeVar
T_input = TypeVar("T_input", bound=BaseModel)
T_output = TypeVar("T_output", bound=BaseModel)

class KernelState(BaseModel):
    """
    各カーネルの現在の強度や状態を保持するベクトルデータ。
    """
    resonance: float = 0.0
    hegemony: float = 0.0
    conflict: float = 0.0
    serenity: float = 0.0

class KernelContext(BaseModel):
    """
    すべてのカーネル間で共有される標準的なコンテキスト。
    trace_idなどの共通メタデータと、カーネル固有のデータを保持する。
    """
    trace_id: str
    narrative_state: Optional[Any] = None  # 現在の物語状態 (NarrativeState)
    narrative_node: Optional[Any] = None  # 現在の状態ノード (NarrativeStateNode)
    global_state: Dict[str, Any] = {}
    # システム全体で共有する状態
    local_state: Dict[str, Any] = {}       # 現在のカーネル処理内での一時的な状態
    metadata: Dict[str, Any] = {}           # 実行オプションや設定
    config: Optional[Any] = None            # GlobalConfigModel への参照

class KernelBase(ABC, Generic[T_input, T_output]):
    """
    すべてのエンジン/カーネルが継承すべき抽象基底クラス。
    ポリモーフィズムを実現し、カーネル間の直接的な依存を排除する。
    """

    def __init__(self, kernel_id: str):
        self.kernel_id = kernel_id

    @abstractmethod
    async def execute(self, input_data: T_input, context: KernelContext) -> T_output:
        """
        カーネルのメインロジックを実行し、結果を返す。
        """
        pass

    def validate(self, input_data: T_input) -> bool:
        """
        入力データの整合性を検証する。必要に応じてオーバーライドして詳細なバリデーションを実装。
        """
        return True

    def initialize(self, config: Dict[str, Any]):
        """
        カーネルの初期設定を行う。
        """
        pass

