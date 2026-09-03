"""学習データサービス - ネガティブサンプル蓄積と監査精度向上"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class LearningDataService:
    """ユーザーの却下・修正から学習データを蓄積し、将来の監査精度を向上させるサービス"""

    def __init__(self, repo=None, chroma_client=None):
        self.repo = repo
        self.chroma_client = chroma_client

    async def record_negative_sample(
        self,
        patch_review_id: int,
        resolution: str,  # "rejected" | "modified" | "approved"
        reviewer_id: str | None = None,
        comment: str = "",
    ) -> int | None:
        """レビュー結果からネガティブ/ポジティブサンプルを記録

        Args:
            patch_review_id: PatchReview ID
            resolution: ユーザーの判断 (rejected, modified, approved)
            reviewer_id: レビュー担当者ID
            comment: レビューコメント

        Returns:
            記録された学習データのID (将来的に learning_samples テーブル追加時)
        """
        if self.repo is None:
            return None

        review = await self.repo.misc.get_patch_review(patch_review_id)
        if not review:
            logger.warning(f"PatchReview {patch_review_id} not found")
            return None

        _ = review.get("audit_issue_ids", [])
        learning_metadata = review.get("learning_metadata", {})

        # ネガティブサンプル候補を取得
        negative_candidates = learning_metadata.get("negative_sample_candidates", [])

        samples_recorded = 0
        for audit_type in negative_candidates:
            # 却下された場合: このタイプの指摘は「誤り」として記録
            # 承認された場合: 正例として記録
            # 修正された場合: 差分を正例、元提案を負例として両方記録
            is_negative = resolution == "rejected"
            _ = resolution in ("approved", "modified")

            sample_data = {
                "patch_review_id": patch_review_id,
                "audit_type": audit_type,
                "label": "negative" if is_negative else "positive",
                "resolution": resolution,
                "reviewer_id": reviewer_id,
                "comment": comment,
                "original_feedback": review.get("diff_json", {}),
                "created_at": datetime.now().isoformat(),
            }

            # ChromaDB にベクトル保存（類似検索用）
            await self._store_learning_vector(sample_data)

            # PatchReview の learning_metadata を更新
            if "learned_patterns" not in learning_metadata:
                learning_metadata["learned_patterns"] = []

            learning_metadata["learned_patterns"].append(
                {
                    "audit_type": audit_type,
                    "label": "negative" if is_negative else "positive",
                    "resolution": resolution,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            samples_recorded += 1

        # learning_metadata を更新
        from sqlalchemy import update
        from src.backend.database.models import PatchReview

        await self.repo.session.execute(
            update(PatchReview)
            .where(PatchReview.id == patch_review_id)
            .values(learning_metadata=json.dumps(learning_metadata, ensure_ascii=False))
        )

        logger.info(
            f"Recorded {samples_recorded} learning samples from review {patch_review_id} (resolution={resolution})"
        )
        return samples_recorded

    async def _store_learning_vector(self, sample_data: dict[str, Any]) -> None:
        """学習サンプルをベクトルDBに保存"""
        if self.chroma_client is None:
            return

        try:
            collection = self.chroma_client.get_or_create_collection("audit_learning_samples")

            # 検索用テキストを構築
            audit_type = sample_data["audit_type"]
            feedback = sample_data.get("original_feedback", {})
            feedback_text = (
                json.dumps(feedback, ensure_ascii=False)
                if isinstance(feedback, dict)
                else str(feedback)
            )

            search_text = (
                f"audit_type:{audit_type} feedback:{feedback_text} label:{sample_data['label']}"
            )

            import hashlib

            doc_id = hashlib.md5(
                f"{sample_data['patch_review_id']}_{audit_type}_{sample_data['label']}".encode()
            ).hexdigest()

            collection.add(
                documents=[search_text],
                metadatas=[
                    {
                        "patch_review_id": sample_data["patch_review_id"],
                        "audit_type": audit_type,
                        "label": sample_data["label"],
                        "resolution": sample_data["resolution"],
                        "reviewer_id": sample_data.get("reviewer_id"),
                        "created_at": sample_data["created_at"],
                    }
                ],
                ids=[doc_id],
            )
        except Exception as e:
            logger.warning(f"Failed to store learning vector: {e}")

    async def get_negative_patterns(self, audit_type: str, limit: int = 10) -> list[dict[str, Any]]:
        """特定の監査タイプに関連するネガティブパターンを検索"""
        if self.chroma_client is None:
            return []

        try:
            collection = self.chroma_client.get_collection("audit_learning_samples")
            if not collection:
                return []

            results = collection.query(
                query_texts=[f"audit_type:{audit_type} label:negative"],
                n_results=limit,
                where={"audit_type": audit_type, "label": "negative"},
            )

            patterns = []
            if results and results.get("metadatas"):
                for meta in results["metadatas"][0]:
                    patterns.append(meta)

            return patterns
        except Exception as e:
            logger.warning(f"Failed to get negative patterns: {e}")
            return []

    async def get_positive_patterns(self, audit_type: str, limit: int = 10) -> list[dict[str, Any]]:
        """特定の監査タイプに関連するポジティブパターン（正例）を検索"""
        if self.chroma_client is None:
            return []

        try:
            collection = self.chroma_client.get_collection("audit_learning_samples")
            if not collection:
                return []

            results = collection.query(
                query_texts=[f"audit_type:{audit_type} label:positive"],
                n_results=limit,
                where={"audit_type": audit_type, "label": "positive"},
            )

            patterns = []
            if results and results.get("metadatas"):
                for meta in results["metadatas"][0]:
                    patterns.append(meta)

            return patterns
        except Exception as e:
            logger.warning(f"Failed to get positive patterns: {e}")
            return []

    async def get_audit_precision_stats(self, book_id: int | None = None) -> dict[str, Any]:
        """監査精度の統計を取得（ダッシュボード用）"""
        if self.repo is None:
            return {}

        # PatchReview から統計を集計
        # 実装は DB クエリが必要だが、ここではインターフェースのみ定義
        return {
            "total_reviews": 0,
            "approved_count": 0,
            "rejected_count": 0,
            "modified_count": 0,
            "by_audit_type": {},
            "precision_by_type": {},
            "negative_samples_count": 0,
            "positive_samples_count": 0,
        }

    async def should_skip_audit_type(
        self, audit_type: str, field_path: str | None = None
    ) -> tuple[bool, float]:
        """ネガティブサンプルに基づき、特定の監査タイプをスキップ/閾値緩和すべきか判定

        Returns:
            (should_skip, confidence_adjustment)
            - should_skip: True の場合、この監査を warning 扱いにして auto-retry しない
            - confidence_adjustment: 信頼度調整値 (-1.0 ~ 1.0)
        """
        negative_patterns = await self.get_negative_patterns(audit_type, limit=20)

        if not negative_patterns:
            return False, 0.0

        # 同一 field_path のネガティブサンプル数をカウント
        _ = 0
        if field_path:
            for p in negative_patterns:
                # metadata に field_path が含まれていれば照合
                pass  # 実装はメタデータ構造に依存

        total_negative = len(negative_patterns)
        total_positive = len(await self.get_positive_patterns(audit_type, limit=20))

        # ネガティブが圧倒的に多い場合はスキップ推奨
        if total_negative > total_positive * 3 and total_negative >= 5:
            return True, -0.3  # 閾値を緩和

        # ある程度ネガティブがある場合は信頼度を下げる
        if total_negative > total_positive and total_negative >= 3:
            return False, -0.15

        return False, 0.0
