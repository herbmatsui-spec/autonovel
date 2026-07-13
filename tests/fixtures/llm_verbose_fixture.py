import json
import random
from pathlib import Path
from typing import List, Optional
from src.models.sharp_edge import SharpEdgeSpec

class LLMVerboseFixture:
    """
    実LLMが生成しがちな冗長な説明文 (Verbose Description) を提供するフィクスチャ。
    リテラル一致に依存しない保全テストに使用する。
    """
    def __init__(self, data_path: str = "tests/fixtures/verbose_edges.json"):
        self.data_path = data_path
        self.samples = self._load_samples()

    def _load_samples(self) -> dict:
        path = Path(self.data_path)
        if not path.exists():
            raise FileNotFoundError(f"Fixture data not found at {self.data_path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_random_description(self, edge_type: str) -> str:
        """指定された edge_type に対応する冗長文をランダムに1つ返す。"""
        samples = self.samples.get(edge_type)
        if not samples:
            # サンプルがない場合は、汎用的な冗長化を試みるか、空文字を返す
            return f"{edge_type} に関する詳細な描写がなされていること。"
        return random.choice(samples)

    def get_description_by_index(self, edge_type: str, index: int) -> str:
        """特定のインデックスのサンプルを返す（決定論的テスト用）。"""
        samples = self.samples.get(edge_type)
        if not samples or index >= len(samples):
            return self.get_random_description(edge_type)
        return samples[index]

    def get_verbose_spec(self, edge_type: str, index: Optional[int] = None) -> SharpEdgeSpec:
        """冗長な説明文を持つ SharpEdgeSpec インスタンスを生成して返す。"""
        if index is not None:
            description = self.get_description_by_index(edge_type, index)
        else:
            description = self.get_random_description(edge_type)
        
        return SharpEdgeSpec(
            edge_type=edge_type,
            description=description
        )

# Singleton instance for easy access in tests
verbose_fixture = LLMVerboseFixture()
