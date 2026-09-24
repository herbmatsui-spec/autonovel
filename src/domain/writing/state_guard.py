"""StateGuard - 事前検証とコンテキスト整合性チェック."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """検証結果"""
    is_valid: bool
    errors: list[str]
    warnings: list[str]


class StateGuard:
    """プロジェクトコンテキストとチャプターシーケンスの事前検証."""

    def __init__(self, repo: Any = None) -> None:
        self.repo = repo

    def validate_project_context(self, project_ctx: Any) -> ValidationResult:
        """
        プロジェクトコンテキストの妥当性を検証する。
        
        Args:
            project_ctx: プロジェクトコンテキストオブジェクト
            
        Returns:
            ValidationResult: 検証結果
        """
        errors = []
        warnings = []

        if project_ctx is None:
            errors.append("プロジェクトコンテキストがNoneです")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # 必須フィールドのチェック
        required_fields = ["book_id", "title", "genre"]
        for field in required_fields:
            if not hasattr(project_ctx, field) or getattr(project_ctx, field) is None:
                errors.append(f"必須フィールド '{field}' が設定されていません")

        # 文字数制限チェック
        if hasattr(project_ctx, "title") and project_ctx.title:
            if len(project_ctx.title) > 200:
                warnings.append("タイトルが200文字を超えています")

        # ジャンルの妥当性チェック
        valid_genres = ["fantasy", "sf", "romance", "mystery", "horror", "historical", "modern"]
        if hasattr(project_ctx, "genre") and project_ctx.genre:
            if project_ctx.genre not in valid_genres:
                warnings.append(f"未知のジャンル: {project_ctx.genre}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    async def ensure_chapter_sequence(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
    ) -> bool:
        """
        チャプターシーケンスの整合性を確保する。
        
        Args:
            book_id: 書籍ID
            start_ep: 開始エピソード番号
            end_ep: 終了エピソード番号
            
        Returns:
            bool: 整合性が取れていればTrue
        """
        if self.repo is None:
            logger.warning("リポジトリが設定されていないため、チャプターシーケンス検証をスキップします")
            return True

        try:
            # 既存チャプターの取得
            existing_chapters = await self.repo.get_chapters(book_id)
            existing_numbers = {ch.episode_number for ch in existing_chapters}

            # 範囲チェック
            if start_ep < 1:
                logger.error(f"開始エピソード番号が無効です: {start_ep}")
                return False

            if end_ep < start_ep:
                logger.error(f"終了エピソード番号が開始より小さいです: {end_ep} < {start_ep}")
                return False

            # 重複チェック（上書きでない場合）
            for ep in range(start_ep, end_ep + 1):
                if ep in existing_numbers:
                    logger.warning(f"エピソード {ep} は既に存在します（上書きされます）")

            # 連番チェック（ギャップがある場合は警告）
            if existing_numbers:
                max_existing = max(existing_numbers)
                if start_ep > max_existing + 1:
                    logger.warning(
                        f"チャプターにギャップがあります: 既存最大={max_existing}, 次={start_ep}"
                    )

            return True

        except Exception as e:
            logger.error(f"チャプターシーケンス検証中にエラー: {e}")
            return False

    def validate_writing_context(self, ctx: dict[str, Any]) -> ValidationResult:
        """
        執筆コンテキストの妥当性を検証する。
        
        Args:
            ctx: 執筆コンテキスト辞書
            
        Returns:
            ValidationResult: 検証結果
        """
        errors = []
        warnings = []

        if not ctx:
            errors.append("執筆コンテキストが空です")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # 必須キーのチェック
        required_keys = ["book_id", "ep_num", "plot"]
        for key in required_keys:
            if key not in ctx or ctx[key] is None:
                errors.append(f"執筆コンテキストに必須キー '{key}' がありません")

        # プロットの内容チェック
        if "plot" in ctx and ctx["plot"] is not None:
            if isinstance(ctx["plot"], dict):
                if not ctx["plot"].get("summary"):
                    warnings.append("プロットサマリーが空です")
            elif isinstance(ctx["plot"], str):
                if not ctx["plot"].strip():
                    warnings.append("プロットが空文字列です")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )