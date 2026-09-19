"""Novel output splitter for isolating novel prose and co-generated metadata."""

import json
import logging
import re
from typing import Tuple, Optional

from src.models.writing_metadata import WritingMetadata

logger = logging.getLogger(__name__)

# Matches [METADATA_JSON] ... [/METADATA_JSON]
METADATA_TAG_PATTERN = re.compile(
    r"\[METADATA_JSON\]\s*(?:```(?:json)?\s*)?(.*?)(?:```\s*)?\[/METADATA_JSON\]",
    re.DOTALL | re.IGNORECASE,
)

# Secondary fallback: looking for trailing markdown json block at end of response
TRAILING_JSON_BLOCK_PATTERN = re.compile(
    r"```json\s*(\{\s*\"episode_number\".*?\})\s*```\s*$",
    re.DOTALL | re.IGNORECASE,
)


class NovelOutputSplitter:
    """Splits raw LLM output into clean prose and WritingMetadata."""

    @staticmethod
    def split_novel_output(raw_output: str) -> Tuple[str, Optional[WritingMetadata]]:
        """
        Splits LLM generated text into novel prose and WritingMetadata.

        Args:
            raw_output: Full text output from LLM

        Returns:
            Tuple of (clean_prose, metadata)
        """
        if not raw_output:
            return "", None

        prose = raw_output
        json_str: Optional[str] = None

        # 1. Look for [METADATA_JSON] ... [/METADATA_JSON]
        match = METADATA_TAG_PATTERN.search(raw_output)
        if match:
            json_str = match.group(1).strip()
            # Remove metadata block from prose
            prose = raw_output[: match.start()] + raw_output[match.end() :]
        else:
            # Fallback: check trailing json block
            fallback_match = TRAILING_JSON_BLOCK_PATTERN.search(raw_output)
            if fallback_match:
                json_str = fallback_match.group(1).strip()
                prose = raw_output[: fallback_match.start()]

        # Clean prose (strip trailing separators, whitespace)
        clean_prose = re.sub(r"-{3,}\s*$", "", prose.strip()).strip()

        # Parse JSON into WritingMetadata
        metadata: Optional[WritingMetadata] = None
        if json_str:
            try:
                # Remove any remaining triple backticks inside tag
                cleaned_json = re.sub(r"^```(?:json)?\s*", "", json_str).rstrip("` \n")
                data = json.loads(cleaned_json)
                metadata = WritingMetadata.model_validate(data)
            except Exception as e:
                logger.warning(
                    f"Failed to parse WritingMetadata from LLM output: {e}. Raw json snippet: {json_str[:200]}"
                )
                metadata = None

        return clean_prose, metadata
