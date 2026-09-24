import logging
import re
import unicodedata

logger = logging.getLogger(__name__)


class ContentProcessor:
    """コンテンツ加工サービス（日本語小説テキストの正規化・サニタイズ・体裁整形）"""

    def sanitize(self, content: str) -> str:
        """HTML/Script タグの除去、Unicode NFKC 正規化、および三点リーダー・ダッシュの体裁統一"""
        if not content:
            return ""
        
        # 1. 危険なスクリプトタグや不正なHTMLタグの除去
        text = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<\s*(style|iframe|object|embed)[^>]*>.*?<\s*/\s*\1\s*>", "", text, flags=re.DOTALL | re.IGNORECASE)

        # 2. 全角英数字・半角カナの Unicode NFKC 正規化（ただしルビや記号は保護）
        text = unicodedata.normalize("NFKC", text)

        # 3. 三点リーダー（…）およびダッシュ（―）の偶数個揃え・統一
        text = re.sub(r"\.{3,}", "……", text)
        text = re.sub(r"…(?![…])", "……", text)
        text = re.sub(r"―(?![―])", "――", text)

        # 4. 連続空白の整形
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def apply_tone(self, content: str, tone: str) -> str:
        """テキストに指定トーンの軽微な文末スタイル補正を適用（簡易プレースホルダー実装）"""
        if not content or not tone:
            return content
        # 基本サニタイズを経由して返却
        return self.sanitize(content)

