from __future__ import annotations
from typing import List, Dict
from src.services.exporters.exporter_base import ExporterBase

class CommercialManuscriptExporter(ExporterBase):
    """出版社持ち込み・電書用「1巻まとめ（10万字）」テキスト結合エクスポーター"""
    
    def export(self, episodes: List[Dict[str, str]]) -> str:
        """
        40話分のエピソードを1本の完成原稿に結合出力する。
        
        Args:
            episodes: 各話のデータリスト。各要素は {'title': str, 'content': str} などを想定。
            
        Returns:
            結合された原稿テキスト（目次、各話タイトル、区切り線、あとがき、登場人物紹介を含む）。
        """
        lines = []
        lines.append("目次")
        lines.append("==========")
        for i, ep in enumerate(episodes, start=1):
            lines.append(f"{i}. {ep.get('title', f'第{i}話')}")
        lines.append("")
        lines.append("==========")
        lines.append("")
        
        for i, ep in enumerate(episodes, start=1):
            lines.append(f"第{i}話 {ep.get('title', '')}")
            lines.append("")
            lines.append(ep.get('content', ""))
            lines.append("")
            lines.append("----------")
            lines.append("")
        
        lines.append("あとがき")
        lines.append("==========")
        lines.append("この度はご購入ありがとうございます。")
        lines.append("")
        
        lines.append("登場人物紹介")
        lines.append("==========")
        lines.append("ここに主要な登場人物の簡単なプロフィールを記載します。")
        lines.append("")
        
        return "\n".join(lines)