"""
kernels/interaction_formatter.py - インタラクションフォーマッタ
"""



class InteractionFormatter:
    """
    インタラクション出力のフォーマット
    """

    def __init__(self):
        self.templates = {
            "default": "{content}",
            "marketing": "[Marketing] {content}",
            "analytical": "[Analysis] {content}",
        }

    def format(self, content: str, category: str = "default") -> str:
        """コンテンツをフォーマット"""
        template = self.templates.get(category, self.templates["default"])
        return template.format(content=content)

    def format_batch(self, contents: list[str], category: str = "default") -> list[str]:
        """複数コンテンツを一括フォーマット"""
        return [self.format(c, category) for c in contents]


class InteractionFormatterFactory:
    """フォーマッタファクトリ"""

    @staticmethod
    def create_formatter(format_type: str = "default") -> InteractionFormatter:
        """フォーマッタを作成"""
        return InteractionFormatter()
