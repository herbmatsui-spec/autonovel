"""
Paragraph indexer for splitting prose into indexed blocks.
"""

from typing import List, Dict
import re

class ParagraphIndexer:
    """
    Splits text into paragraphs and assigns each a stable index.
    """

    def __init__(self, min_chars: int = 100, max_chars: int = 300):
        """
        Initialize the indexer with target character range per paragraph.
        Args:
            min_chars: Minimum characters per paragraph (before merging).
            max_chars: Maximum characters per paragraph (before splitting).
        """
        self.min_chars = min_chars
        self.max_chars = max_chars

    def index_paragraphs(self, text: str) -> List[Dict[str, any]]:
        """
        Split text into paragraphs, assign indices, and return list of dicts.
        Each dict contains: index, text, and optionally start/end positions.
        Args:
            text: The full text to index.
        Returns:
            List of paragraph dictionaries with keys: 'index', 'text'.
        """
        # Split by blank lines (multiple newlines) and remove empty lines
        raw_paragraphs = re.split(r'\n\s*\n', text.strip())
        paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]

        # Adjust paragraph boundaries to target size (optional, for now we keep as split)
        # For simplicity, we'll just use the split paragraphs and assign indices.
        indexed = []
        for i, para in enumerate(paragraphs):
            indexed.append({
                'index': i,
                'text': para,
                # We could also store character offsets if needed for in-place replacement
                # 'start': start_pos,
                # 'end': end_pos,
            })
        return indexed
