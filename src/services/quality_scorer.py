"""
src/services/quality_scorer.py — 品質スコア算出サービス
"""
import re
from typing import Any, Dict, List, Optional

from src.models.report import QualityMetricsReport


class QualityScorer:
    """品質スコアを算出するサービス"""

    def __init__(self, llm_client=None):
        """初期化
        
        Args:
            llm_client: LLMクライアント（任意）。Noneの場合はルールベースで評価
        """
        self.llm_client = llm_client

    async def score_coherence(self, text: str) -> float:
        """物語整合性スコアを算出
        
        Args:
            text: 評価対象テキスト
            
        Returns:
            float: 0.0-1.0のスコア
        """
        # 簡易ルールベース評価
        if not text or len(text) < 100:
            return 0.0
        
        # 物語の流れを示すキーワードの密度
        flow_keywords = ['しかし', 'そのため', 'こうして', 'それでも', 'すると', 'だが', 'けれど']
        flow_count = sum(1 for kw in flow_keywords if kw in text)
        flow_score = min(flow_count / 10, 1.0)
        
        # 文の連続性（句点密度）
        sentences = re.split(r'[。！？]', text)
        sentences = [s for s in sentences if s.strip()]
        if len(sentences) < 3:
            return 0.3
        
        # スコア合成
        score = 0.4 + (flow_score * 0.6)
        return min(score, 1.0)

    async def score_character_consistency(self, text: str) -> float:
        """キャラクター一貫性スコアを算出
        
        Args:
            text: 評価対象テキスト
            
        Returns:
            float: 0.0-1.0のスコア
        """
        if not text or len(text) < 100:
            return 0.0
        
        # 名前 упомина频率（キャラクターの主張度）
        names = re.findall(r'[\u4e00-\u9fa5]{2,4}(?:は|が|に|を|と|で)', text)
        unique_names = set(names)
        
        # 多様なキャラクター提及
        if len(unique_names) >= 3:
            return 0.85
        elif len(unique_names) >= 2:
            return 0.75
        else:
            return 0.6

    async def score_pacing(self, text: str) -> float:
        """ペーシングスコアを算出
        
        Args:
            text: 評価対象テキスト
            
        Returns:
            float: 0.0-1.0のスコア
        """
        if not text or len(text) < 100:
            return 0.0
        
        # 文字数に対するシーン転換の適切さ
        length = len(text)
        
        # 展開キーワードの密度
        tension_keywords = ['突然', 'まさか', '猛然', '一瞬', '急速に', '決意', '闘志']
        tension_count = sum(1 for kw in tension_keywords if kw in text)
        
        # 適切なテンポ: 約500-1000文字に1つの転換
        expected_transitions = length / 750
        pacing_score = min(tension_count / max(expected_transitions, 1), 1.0)
        
        return 0.5 + (pacing_score * 0.5)

    async def score_hook_retention(self, text: str) -> float:
        """フック保持率スコアを算出
        
        Args:
            text: 評価対象テキスト
            
        Returns:
            float: 0.0-1.0のスコア
        """
        if not text or len(text) < 100:
            return 0.0
        
        # 疑問文・に反転・未解決の問題の数
        hooks = []
        hooks.extend(re.findall(r'.*か\?', text))
        hooks.extend(re.findall(r'.*だろうか', text))
        hooks.extend(re.findall(r'.*怎么回事', text))
        
        # 結末附近の未解決要素
        last_third = text[len(text)*2//3:]
        unresolved = len(re.findall(r'...\?|怎么了|怎么办', last_third))
        
        if len(hooks) >= 2 and unresolved >= 1:
            return 0.85
        elif len(hooks) >= 1:
            return 0.7
        else:
            return 0.55

    async def score_emotional_resonance(self, text: str) -> float:
        """感情共鳴度スコアを算出
        
        Args:
            text: 評価対象テキスト
            
        Returns:
            float: 0.0-1.0のスコア
        """
        if not text or len(text) < 100:
            return 0.0
        
        # 感情表現の密度
        emotion_words = [
            '喜び', '悲しみ', '怒り', '恐れ', '驚き', '愛情', '憎しみ',
            '緊張', '安堵', '誇り', '恥じ', '羨望', '恐怖', '歓喜',
            '胸が', '心が', '目に', '顔に', 'いだく', ' 느끼다'
        ]
        emotion_count = sum(1 for word in emotion_words if word in text)
        
        # 対比表現（感情の起伏）
        contrast_markers = ['しかし', 'だが', 'ところが', 'それでも']
        contrast_count = sum(1 for marker in contrast_markers if marker in text)
        
        score = min(emotion_count / 5, 1.0) * 0.7 + min(contrast_count / 3, 1.0) * 0.3
        return 0.5 + (score * 0.5)

    async def score_commercial_viability(self, text: str) -> float:
        """商業的ポテンシャルスコアを算出
        
        Args:
            text: 評価対象テキスト
            
        Returns:
            float: 0.0-1.0のスコア
        """
        if not text or len(text) < 100:
            return 0.0
        
        # タイトル候補となりそうなキーワード
        commercial_keywords = ['最強', '覇者', '伝説', '運命', '戦士', '勇者', '魔王', '覚醒']
        keyword_count = sum(1 for kw in commercial_keywords if kw in text)
        
        # 文字数適切さ（3000字近辺が理想）
        length = len(text)
        length_score = 1.0 if 2500 <= length <= 3500 else 0.8 if 2000 <= length <= 4000 else 0.6
        
        score = (min(keyword_count / 3, 1.0) * 0.6) + (length_score * 0.4)
        return 0.5 + (score * 0.5)

    async def score_all(self, text: str) -> QualityMetricsReport:
        """全品質スコアを算出
        
        Args:
            text: 評価対象テキスト
            
        Returns:
            QualityMetricsReport: 品質メトリクスレポート
        """
        coherence = await self.score_coherence(text)
        character = await self.score_character_consistency(text)
        pacing = await self.score_pacing(text)
        hook = await self.score_hook_retention(text)
        emotional = await self.score_emotional_resonance(text)
        commercial = await self.score_commercial_viability(text)
        
        return QualityMetricsReport(
            coherence_score=coherence,
            character_consistency=character,
            pacing_score=pacing,
            hook_retention=hook,
            emotional_resonance=emotional,
            commercial_viability=commercial
        )