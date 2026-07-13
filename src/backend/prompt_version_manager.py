import logging
from typing import Any, Dict, Optional

from src.backend.database.core import DatabaseManager
from src.backend.database.uow import UnitOfWork

logger = logging.getLogger(__name__)

class PromptVersionManager:
    """プロンプトのバージョン管理、A/Bテスト比較、自動ロールバックを制御するマネージャー"""

    MAX_HISTORY = 10

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def save_new_version(
        self, book_id: int, prompt_key: str, content: str,
        score_before: Optional[float] = None, ab_test_metrics: Optional[Dict[str, Any]] = None
    ) -> int:
        """新しいプロンプトバージョンを非アクティブ状態で保存。古いバージョンはMAX_HISTORY件に制限する。"""
        async with UnitOfWork(self.db) as uow:
            # 1. バージョンタグの決定 (v1, v2, v3, ...)
            versions = await uow.prompt_versions.get_prompt_versions(book_id, limit=100)
            key_versions = [v for v in versions if v["prompt_key"] == prompt_key]
            next_num = len(key_versions) + 1
            version_tag = f"v{next_num}"

            # 2. 作成
            new_ver = await uow.prompt_versions.create_prompt_version(
                book_id=book_id,
                prompt_key=prompt_key,
                version_tag=version_tag,
                content=content,
                score_before=score_before,
                score_after=None,
                ab_test_metrics=ab_test_metrics or {},
                is_active=False
            )

            # 3. 古い無効なバージョンを掃除（最大MAX_HISTORY件）
            if len(key_versions) >= self.MAX_HISTORY:
                # 日付順で古い順に取得し、上限を超える分を削除
                sorted_versions = sorted(key_versions, key=lambda x: x["created_at"])
                to_delete = sorted_versions[:(len(key_versions) - self.MAX_HISTORY + 1)]
                for old_v in to_delete:
                    # アクティブなものは削除しない
                    if not old_v["is_active"]:
                        from sqlalchemy import delete

                        from src.backend.database.models import PromptVersion
                        await uow.session.execute(
                            delete(PromptVersion).where(PromptVersion.id == old_v["id"])
                        )

            return new_ver.id

    async def activate_version(self, book_id: int, prompt_key: str, version_id: int) -> None:
        """指定したプロンプトバージョンをアクティブ化し、グローバル設定などと同期する"""
        async with UnitOfWork(self.db) as uow:
            await uow.prompt_versions.set_active_prompt_version(book_id, prompt_key, version_id)
            # 現在のプロンプトパッチをGlobalConfigに反映させるため、
            # contentをGlobalConfig("optimized_prompt_patch")に同期
            ver = await uow.prompt_versions.get_prompt_version(version_id)
            if ver:
                from config.project_context import GlobalConfig
                GlobalConfig().set("optimized_prompt_patch", ver["content"])
                logger.info(f"Activated prompt version {ver['version_tag']} for key {prompt_key}")

    async def evaluate_and_rollback_if_needed(
        self, book_id: int, prompt_key: str, version_id: int, score_after: float
    ) -> bool:
        """適用後のスコアを記録し、基準を下回った場合は自動ロールバックを実行。
        戻り値: ロールバックが発生した場合は True、発生しなかった場合は False
        """
        async with UnitOfWork(self.db) as uow:
            ver = await uow.prompt_versions.get_prompt_version(version_id)
            if not ver:
                logger.warning(f"Prompt version {version_id} not found.")
                return False

            # スコア更新
            await uow.prompt_versions.update_score_after(version_id, score_after)

            score_before = ver["score_before"]
            if score_before is not None:
                # 劣化（スコアが5%以上または10ポイント以上低下）しているかチェック
                degradation_threshold = 5.0
                if score_after < (score_before - degradation_threshold):
                    # ロールバック理由
                    reason = f"自動ロールバック: スコアが {score_before:.1f} から {score_after:.1f} へ劣化しました。"
                    logger.warning(f"🚨 Prompt performance degraded for version {ver['version_tag']} ({score_before} -> {score_after}). Rolling back...")

                    # このバージョンを非アクティブにしてロールバック理由を記録
                    await uow.prompt_versions.record_rollback(version_id, reason)

                    # 1つ前の有効なアクティブバージョンを探してアクティブ化する
                    versions = await uow.prompt_versions.get_prompt_versions(book_id, limit=20)
                    previous_candidates = [
                        v for v in versions
                        if v["prompt_key"] == prompt_key
                        and v["id"] != version_id
                        and not v["rollback_reason"]
                    ]

                    if previous_candidates:
                        # 直近のロールバックされていない正常なバージョンをアクティブにする
                        fallback_ver = previous_candidates[0]
                        await uow.prompt_versions.set_active_prompt_version(book_id, prompt_key, fallback_ver["id"])
                        from config.project_context import GlobalConfig
                        GlobalConfig().set("optimized_prompt_patch", fallback_ver["content"])
                        logger.info(f"Successfully rolled back to version {fallback_ver['version_tag']}")
                    else:
                        # 候補がない場合はデフォルト（空文字列）に戻す
                        from config.project_context import GlobalConfig
                        GlobalConfig().set("optimized_prompt_patch", "")
                        logger.info("No fallback prompt version found. Reverted to default empty prompt.")

                    return True
            return False

