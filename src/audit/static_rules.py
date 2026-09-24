"""
Static rule auditor for fast format checking.
Consolidates existing format check rules including character limits, forbidden patterns,
and formatting requirements.
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Issue:
    """Represents a format issue found by static rules."""
    type: str  # Issue category (e.g., "length_exceeded", "forbidden_pattern")
    message: str  # Human-readable description
    location: Optional[Tuple[int, int]]  # (start_index, end_index) or None if location unknown
    suggestion: Optional[str] = None  # Optional suggestion for fixing the issue


class StaticRuleAuditor:
    """高速静的ルールオーディター - 文字数・禁則・フォーマット等の形式チェックを実行"""
    
    def __init__(self):
        # Load platform-independent default limits
        # These could be made configurable via config files
        self.default_max_chapter_chars = 5000  # Default max chars per chapter
        self.default_max_title_chars = 100     # Default max title chars
        self.default_min_paragraphs = 1        # Minimum paragraphs
        
        # Forbidden patterns (basic implementation)
        self.forbidden_patterns = [
            # Add common forbidden patterns here
            # For now, we'll rely on existing validation in compliance_validator
        ]
        
    def audit(self, text: str) -> List[Issue]:
        """
        テキストに対して静的ルールベースの形式チェックを実行
        
        Args:
            text: 検査対象のテキスト
            
        Returns:
            List[Issue]: 検出された問題のリスト
        """
        issues = []
        
        # 1. 文字数チェック (基本的な実装)
        # 実際の実装では、プラットフォーム固有の制限を適用すべき
        # ここではデフォルト制限を使用
        if len(text) > self.default_max_chapter_chars:
            issues.append(Issue(
                type="length_exceeded",
                message=f"文字数が上限を超えています（{len(text)}文字 > {self.default_max_chapter_chars}文字）",
                location=(0, len(text)),
                suggestion=f"文字数を{self.default_max_chapter_chars}文字以内に収めてください"
            ))
        
        # 2. 章タイトルフォーマットチェック
        # 簡易実装：最初の行が章タイトルだと仮定
        lines = text.split('\n')
        if lines and len(lines[0]) > self.default_max_title_chars:
            issues.append(Issue(
                type="title_length_exceeded",
                message=f"章タイトルが長すぎます（{len(lines[0])}文字 > {self.default_max_title_chars}文字）",
                location=(0, len(lines[0])),
                suggestion=f"章タイトルを{self.default_max_title_chars}文字以内に収めてください"
            ))
        
        # 3. 段落数チェック
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) < self.default_min_paragraphs:
            issues.append(Issue(
                type="paragraph_count_insufficient",
                message=f"段落数が不足しています（{len(paragraphs)}段落 < {self.default_min_paragraphs}段落）",
                location=None,  # Location unclear for entire text
                suggestion=f"少なくとも{self.default_min_paragraphs}段落を含めてください"
            ))
        
        # 4. 禁則チェック (基本的な実装)
        # 約物禁則処理など
        # ここでは簡易的なパターンマッチングを行う
        for pattern in self.forbidden_patterns:
            matches = list(re.finditer(pattern, text))
            for match in matches:
                issues.append(Issue(
                    type="forbidden_pattern",
                    message=f"禁則パターンが検出されました: {match.group()}",
                    location=(match.start(), match.end()),
                    suggestion="禁則パターンを修正してください"
                ))
        
        # 5. 行頭禁則チェック (行頭に閉じ括弧や句読点がないか)
        # Japanese line-start kinsoku characters
        line_start_forbidden = '、。・：；？！」「』】〕〉》」』】〕〉》'
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if line and line[0] in line_start_forbidden:
                # Calculate approximate position in original text
                pos = sum(len(l) + 1 for l in lines[:i])  # +1 for newline
                issues.append(Issue(
                    type="line_start_forbidden_punct",
                    message=f"行頭に禁則文字があります: '{line[0]}'",
                    location=(pos, pos + 1),
                    suggestion="行頭の禁則文字を削除または文頭に移動してください"
                ))
         
        return issues