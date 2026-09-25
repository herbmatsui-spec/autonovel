"""
Patch merger for combining original text with rewritten paragraphs.
"""

import re
from typing import List
from src.models.patch_pdca import PatchRewriteResult


class PatchMerger:
    """
    Merges rewritten paragraphs back into the original text at the correct indices.
    """

    def __init__(self):
        pass

    def merge_patches(self, original_text: str, patches: List[PatchRewriteResult]) -> str:
        """
        Merge the rewritten patches into the original text.
        Args:
            original_text: The original full text.
            patches: A list of PatchRewriteResult objects, each containing an index and the patched text.
        Returns:
            The new text with the patches applied.
        """
        if not original_text or not patches:
            return original_text

        # Split original text into paragraphs by blank lines
        raw_paragraphs = re.split(r'\n\s*\n', original_text.strip())
        paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]

        if not paragraphs:
            return original_text

        # Map patches by index (latest patch wins if duplicates exist)
        patch_map = {p.index: p.patched_text for p in patches if p.patched_text is not None}

        # Apply patches
        for idx, patched_text in patch_map.items():
            if 0 <= idx < len(paragraphs):
                paragraphs[idx] = patched_text

        return "\n\n".join(paragraphs)
