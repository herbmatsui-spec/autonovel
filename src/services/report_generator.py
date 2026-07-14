"""
src/services/report_generator.py — レポート生成サービス
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import os

from src.models.report import (
    EpisodeSummary,
    ProductionReport,
    QualityMetricsReport,
    TokenUsageReport
)
from src.services.quality_scorer import QualityScorer
from src.services.token_tracker import TokenTracker


class ReportGenerator:
    """制作レポートを生成するサービス"""

    def __init__(self, output_dir: str = "output"):
        """初期化
        
        Args:
            output_dir: レポート出力ディレクトリ
        """
        self.output_dir = output_dir
        self.quality_scorer = QualityScorer()
        os.makedirs(output_dir, exist_ok=True)

    def generate_production_report(
        self,
        title: str,
        genre: str,
        token_tracker: TokenTracker,
        episodes: List[Dict[str, Any]]
    ) -> ProductionReport:
        """制作レポートを生成
        
        Args:
            title: 作品タイトル
            genre: ジャンル
            token_tracker: トークントラッカー
            episodes: エピソードリスト
            
        Returns:
            ProductionReport: 制作レポート
        """
        # エピソードサマリー生成
        episode_summaries = []
        for ep in episodes:
            summary_text = ep.get("text", "")[:200] if ep.get("text") else ""
            episode_summaries.append(EpisodeSummary(
                ep_num=ep.get("ep_num", 0),
                title=ep.get("title", f"第{ep.get('ep_num', 0)}話"),
                word_count=len(ep.get("text", "")),
                summary=summary_text + "..." if len(summary_text) == 200 else summary_text,
                quality_score=ep.get("quality_score", 0.0)
            ))
        
        return ProductionReport(
            title=title,
            genre=genre,
            target_word_count=3000,
            token_usage=token_tracker.get_report(),
            episode_summaries=episode_summaries,
            total_generation_time=token_tracker.get_report().generation_time_seconds,
            created_at=datetime.now()
        )

    def add_quality_metrics(
        self,
        report: ProductionReport,
        text: str
    ) -> ProductionReport:
        """レポートに品質メトリクスを追加
        
        Args:
            report: 制作レポート
            text: 評価対象テキスト
            
        Returns:
            ProductionReport: 品質メトリクスが追加されたレポート
        """
        import asyncio
        quality_metrics = asyncio.run(self.quality_scorer.score_all(text))
        report.quality_metrics = quality_metrics
        return report

    def to_markdown(self, report: ProductionReport) -> str:
        """レポートをMarkdown形式で出力
        
        Args:
            report: 制作レポート
            
        Returns:
            str: Markdown形式のレポート文字列
        """
        lines = [
            f"# 制作レポート: {report.title}",
            "",
            f"**ジャンル**: {report.genre}",
            f"**生成日時**: {report.created_at.isoformat()}",
            "",
            "## トークン使用量",
            ""
        ]
        
        if report.token_usage:
            tu = report.token_usage
            lines.extend([
                f"- **総トークン数**: {tu.total_tokens:,}",
                f"- **入力トークン数**: {tu.input_tokens:,}",
                f"- **出力トークン数**: {tu.output_tokens:,}",
                f"- **生成エピソード数**: {tu.episode_count}",
                f"- **生成所要時間**: {tu.generation_time_seconds:.1f}秒",
                ""
            ])
        
        if report.quality_metrics:
            qm = report.quality_metrics
            lines.extend([
                "## 品質メトリクス",
                "",
                f"- **物語整合性**: {qm.coherence_score:.2f}",
                f"- **キャラクター一貫性**: {qm.character_consistency:.2f}",
                f"- **ペーシング**: {qm.pacing_score:.2f}",
                f"- **フック保持率**: {qm.hook_retention:.2f}",
                f"- **感情共鳴度**: {qm.emotional_resonance:.2f}",
                f"- **商業的ポテンシャル**: {qm.commercial_viability:.2f}",
                ""
            ])
        
        lines.extend([
            "## エピソード一覧",
            ""
        ])
        
        for ep in report.episode_summaries:
            lines.extend([
                f"### 第{ep.ep_num}話: {ep.title}",
                f"- 文字数: {ep.word_count}",
                f"- 品質スコア: {ep.quality_score:.2f}",
                f"- 要約: {ep.summary[:100]}..." if len(ep.summary) > 100 else f"- 要約: {ep.summary}",
                ""
            ])
        
        return "\n".join(lines)

    def to_html(self, report: ProductionReport) -> str:
        """レポートをHTML形式で出力
        
        Args:
            report: 制作レポート
            
        Returns:
            str: HTML形式のレポート文字列
        """
        markdown = self.to_markdown(report)
        # 簡易Markdown to HTML変換
        html = markdown.replace('# ', '<h1>').replace('\n', '</h1>\n', 1)
        html = html.replace('## ', '<h2>').replace('\n', '</h2>\n')
        html = html.replace('### ', '<h3>').replace('\n', '</h3>\n')
        html = html.replace('**', '<strong>').replace('**', '</strong>')
        html = html.replace('- ', '<li>').replace('\n', '</li>\n')
        html = f"<html><body>{html}</body></html>"
        return html

    def save_report(self, report: ProductionReport, filename: Optional[str] = None) -> str:
        """レポートをファイルに保存
        
        Args:
            report: 制作レポート
            filename: 出力ファイル名（Noneの場合は自動生成）
            
        Returns:
            str: 保存されたファイルパス
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"production_report_{timestamp}.md"
        
        filepath = os.path.join(self.output_dir, filename)
        
        markdown = self.to_markdown(report)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        return filepath

    def extract_episode_summary(self, text: str, max_length: int = 100) -> str:
        """エピソードの要約を抽出
        
        Args:
            text: エピソード全文
            max_length: 最大要約長
            
        Returns:
            str: 要約文字列
        """
        # 最初の200文字を概要として使用
        summary = text[:200].strip()
        
        # 句点で終わるように調整
        for i in range(len(summary) - 1, -1, -1):
            if summary[i] in '。！？':
                summary = summary[:i+1]
                break
        
        return summary