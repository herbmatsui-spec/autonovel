import json
import os
from typing import Dict, List, Optional
from functools import lru_cache

class FewShotSelector:
    """ジャンル・シーンタイプに応じて最適なFew-Shotを動的に選択するセレクター"""

    def __init__(self, few_shots_path: Optional[str] = None):
        if few_shots_path is None:
            # デフォルトパス（プロジェクトルートからの相対パス）
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            few_shots_path = os.path.join(base_dir, "data", "genre_few_shots.json")

        self.few_shots_path = few_shots_path
        self._few_shots_data: Optional[Dict] = None
        self._load_few_shots()

    def _load_few_shots(self) -> None:
        """Few-ShotデータをJSONファイルから読み込む"""
        try:
            with open(self.few_shots_path, 'r', encoding='utf-8') as f:
                self._few_shots_data = json.load(f)
        except FileNotFoundError:
            # ファイルが見つからない場合は空の辞書で初期化
            self._few_shots_data = {}
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in few_shots file: {e}")

    @lru_cache(maxsize=128)
    def select_few_shots(self, genre: str, scene_type: str, max_examples: int = 2) -> List[Dict[str, str]]:
        """
        ジャンルとシーンタイプに基づいて最適なFew-Shot例を選択

        Args:
            genre: ジャンル (例: fantasy_action, villainess_court, dungeon_modern)
            scene_type: シーンタイプ (例: action, dialogue, internal_monologue)
            max_examples: 返却する最大例数 (デフォルト: 2)

        Returns:
            選択されたFew-Shot例のリスト
        """
        if not self._few_shots_data:
            return []

        # ジャンルが存在するかチェック
        if genre not in self._few_shots_data:
            # フォールバック: 最初の利用可能なジャンルを使用
            available_genres = list(self._few_shots_data.keys())
            if available_genres:
                genre = available_genres[0]
            else:
                return []

        genre_samples = self._few_shots_data[genre]

        # シーンタイプに基づいてサンプルをフィルタリング（簡易実装）
        # 実際の実装では、より高度なマッチングロジックが必要
        filtered_samples = []
        for sample in genre_samples:
            before_text = sample["before"].lower()
            sample["after"].lower()

            # シーンタイプに基づく簡易マッチング
            if scene_type == "action" and any(keyword in before_text for keyword in ["走", "撃", "斬", "爆発", "闘"]):
                filtered_samples.append(sample)
            elif scene_type == "dialogue" and any(keyword in before_text for keyword in ["言", "話", "会", " conversation"]):
                filtered_samples.append(sample)
            elif scene_type == "internal_monologue" and any(keyword in before_text for keyword in ["感", "思", "考", "思い"]):
                filtered_samples.append(sample)
            else:
                # マッチしない場合も全体から選択（フォールバック）
                filtered_samples.append(sample)

        # 重複を除去し、最大max_examples件まで返却
        unique_samples = []
        seen_before = set()
        for sample in filtered_samples:
            if sample["before"] not in seen_before:
                seen_before.add(sample["before"])
                unique_samples.append(sample)
                if len(unique_samples) >= max_examples:
                    break

        # まだサンプルが足りない場合は、元のリストから追加
        if len(unique_samples) < max_examples:
            for sample in genre_samples:
                if sample["before"] not in seen_before:
                    unique_samples.append(sample)
                    seen_before.add(sample["before"])
                    if len(unique_samples) >= max_examples:
                        break

        return unique_samples[:max_examples]

    def get_available_genres(self) -> List[str]:
        """利用可能なジャンルのリストを取得"""
        if not self._few_shots_data:
            return []
        return list(self._few_shots_data.keys())

    def reload(self) -> None:
        """Few-Shotデータを再読み込み"""
        self._load_few_shots()
        # LRUキャッシュをクリア
        self.select_few_shots.cache_clear()
