"""
src/services/safe_replace.py
複数パターンの置換を1パスで安全に実行する置換器。
順次 str.replace() による二重置換問題を解消する。
"""
import re
from typing import Dict, List, Tuple


class SafeReplacer:
    """
    複数の置換ルールを1パスで適用する安全な置換器。
    
    順次 str.replace() を行うと、1回目の置換結果が2回目のキーと
    衝突して意図しない二重置換が発生する。このクラスは正規表現の
    1パス置換（re.sub）を用いて、各パターンの最初のマッチのみを
    置換し、置換済みテキストが再マッチしないことを保証する。
    """

    def __init__(self, mappings: Dict[str, str]) -> None:
        """
        Args:
            mappings: {置換前文字列: 置換後文字列} の辞書
        """
        self._mappings = mappings
        # プレースホルダ方式: 各マッピングに固有のプレースホルダを割り当て
        self._placeholders: List[Tuple[str, str, str]] = []
        for idx, (src, dst) in enumerate(mappings.items()):
            placeholder = f"\x00PLACEHOLDER_{idx}\x00"
            self._placeholders.append((src, placeholder, dst))
        # 全パターンの正規表現を構築
        patterns = [re.escape(src) for src, _, _ in self._placeholders]
        if patterns:
            self._combined_pattern = re.compile("|".join(patterns))
        else:
            self._combined_pattern = None

    def replace(self, text: str) -> str:
        """
        全マッピングを1パスで安全に置換する。
        
        Args:
            text: 置換対象テキスト
        
        Returns:
            置換後テキスト
        """
        if self._combined_pattern is None:
            return text

        # マッピングの逆引き辞書（元文字列→プレースホルダ）
        src_to_placeholder = {src: ph for src, ph, _ in self._placeholders}

        def _replacer(match: re.Match) -> str:
            matched_text = match.group(0)
            return src_to_placeholder.get(matched_text, matched_text)

        # Step 1: 全マッチをプレースホルダに置換
        intermediate = self._combined_pattern.sub(_replacer, text)

        # Step 2: プレースホルダを最終値に置換
        for _, placeholder, dst in self._placeholders:
            intermediate = intermediate.replace(placeholder, dst)

        return intermediate
