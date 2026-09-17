"""
erotic/diversity_scorer.py - 官能シーンの多様性スコアリング
"""

from __future__ import annotations



class EroticDiversityScorer:
    """官能描写の多様性をスコアリングする。"""

    # 表現カテゴリごとのキーワード
    EXPRESSION_CATEGORIES = {
        "physical_actions": [
            "抱きしめ", "撫で", "触れ", "愛撫", "キス", "口づけ", "舐め",
            "吸い", "噛み", "揉み", "擦り", "入れ", "抜き", "突き",
        ],
        "verbal_expressions": [
            "囁き", "呟き", "喘ぎ", "吐息", "悲鳴", "懇願", "命令",
            "誘い", "拒み", "許し", "告白", "罵り",
        ],
        "emotional_states": [
            "快感", "絶頂", "悦び", "恍惚", "焦燥", "羞恥", "恐怖",
            "安堵", "渇望", "満足", "虚脱", "余韻",
        ],
        "body_parts": [
            "唇", "舌", "歯", "首", "肩", "胸", "乳首", "腹",
            "背中", "腰", "尻", "太腿", "膝", "足", "指",
            "髪", "耳", "目", "鼻", "頬", "顎",
        ],
    }

    def calculate_diversity(self, text: str) -> float:
        """
        テキストの表現多様性スコアを計算する。

        Args:
            text: 評価対象のテキスト

        Returns:
            0.0〜1.0 の多様性スコア
        """
        if not text or not text.strip():
            return 0.0

        # 各カテゴリで使用されているユニークキーワード数をカウント
        category_counts = {}
        total_unique = 0

        for category, keywords in self.EXPRESSION_CATEGORIES.items():
            found = set()
            for kw in keywords:
                if kw in text:
                    found.add(kw)
            category_counts[category] = len(found)
            total_unique += len(found)

        # 全キーワード総数
        total_keywords = sum(len(kw) for kw in self.EXPRESSION_CATEGORIES.values())

        if total_keywords == 0:
            return 0.0

        # カテゴリごとの多様性（使用されたカテゴリ数 / 全カテゴリ数）
        used_categories = sum(1 for count in category_counts.values() if count > 0)
        category_diversity = used_categories / len(self.EXPRESSION_CATEGORIES)

        # キーワードレベルの多様性（ユニークキーワード数 / 全キーワード数）
        keyword_diversity = min(total_unique / max(total_keywords * 0.1, 1), 1.0)

        # 重み付き平均
        score = (category_diversity * 0.6) + (keyword_diversity * 0.4)

        return min(max(score, 0.0), 1.0)
