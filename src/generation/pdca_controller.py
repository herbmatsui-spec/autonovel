"""
PDCAサイクルコントローラー - 全文再生成禁止と局所パッチ制限を実装
"""

from dataclasses import dataclass, field


@dataclass
class PDCAController:
    """PDCAサイクルを制御するクラス - 全文再生成禁止と局所パッチ制限"""
    
    # 全文再生成の最大許容回数（0で禁止）
    max_regenerations: int = 0
    # 局所パッチの最大許容回数（デフォルト1回）
    max_local_patches: int = 1
    
    # 内部状態の追跡
    _regeneration_count: int = field(default=0, init=False)
    _local_patch_count: int = field(default=0, init=False)

    @property
    def regeneration_count(self) -> int:
        return self._regeneration_count

    @property
    def local_patch_count(self) -> int:
        return self._local_patch_count
    
    def should_regenerate_full_text(self) -> bool:
        """
        全文再生成が許可されているかを判定
        
        Returns:
            bool: 全文再生成を許可する場合True
        """
        return self._regeneration_count < self.max_regenerations
    
    def can_do_local_patch(self) -> bool:
        """
        局所パッチが許可されているかを判定
        
        Returns:
            bool: 局所パッチを許可する場合True
        """
        return self._local_patch_count < self.max_local_patches
    
    def record_full_regeneration(self) -> None:
        """
        全文再生成が実行されたことを記録
        """
        self._regeneration_count += 1
    
    def record_local_patch(self) -> None:
        """
        局所パッチが実行されたことを記録
        """
        self._local_patch_count += 1
        
    def reset_counts(self) -> None:
        """
        カウントをリセット（新しいドキュメント処理の開始時に使用）
        """
        self._regeneration_count = 0
        self._local_patch_count = 0