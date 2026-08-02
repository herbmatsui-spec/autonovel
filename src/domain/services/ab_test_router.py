from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class ABTestConfig:
    """Configuration for A/B testing bucket assignment."""

    bucket_count: int = 100
    rollout_percentage: float = 100.0  # 0-100


class ABTestRouter:
    """Deterministic A/B test router using consistent hashing.
    
    Assigns users/requests to buckets based on hash of identifiers,
    ensuring consistent assignment across sessions.
    """

    def __init__(self, config: ABTestConfig = None):
        self.config = config or ABTestConfig()

    def get_bucket(self, user_id: str, request_id: str = None) -> int:
        """Get bucket number for a user/request combination.
        
        Args:
            user_id: Unique user identifier
            request_id: Optional request identifier for session-level bucketing
            
        Returns:
            Bucket number (0 to bucket_count-1)
        """
        # Combine identifiers for consistent hashing
        combined = f"{user_id}:{request_id or 'default'}"
        hash_value = int(hashlib.sha256(combined.encode()).hexdigest(), 16)
        return hash_value % self.config.bucket_count

    def is_in_rollout(self, user_id: str, request_id: str = None) -> bool:
        """Check if user/request is within the rollout percentage."""
        bucket = self.get_bucket(user_id, request_id)
        rollout_buckets = int(self.config.bucket_count * (self.config.rollout_percentage / 100.0))
        return bucket < rollout_buckets

    def get_version_tag(self, user_id: str, version_tags: list[str], request_id: str = None) -> str:
        """Select a version tag based on user's bucket.
        
        Args:
            user_id: User identifier
            version_tags: List of available version tags (ordered by priority)
            request_id: Optional request identifier
            
        Returns:
            Selected version tag
        """
        if not version_tags:
            raise ValueError("No version tags provided")

        if len(version_tags) == 1:
            return version_tags[0]

        bucket = self.get_bucket(user_id, request_id)
        index = bucket % len(version_tags)
        return version_tags[index]
