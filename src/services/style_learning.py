"""services/style_learning.py - 章本文から文体特徴を抽出し、STYLE_LEARNED.md を更新"""

import re
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List

from src.filesystem_memory import paths as _paths_mod
from src.filesystem_memory.writer import read_file_safe, update_section


def split_sentences(text: str) -> List[str]:
    """Sentence split for Japanese and full-width punctuation.
    Splits on 。！？!? and newline, removes empty strings.
    """
    # Normalize newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Split by 。！？!? and newline
    # We treat any of these as delimiters
    sentences = re.split(r"[。！？!?\n]+", text)
    # Strip and remove empty
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


def count_particles(text: str) -> Dict[str, int]:
    """Count occurrences of Japanese particles: は, が, を, に, で, へ, と, も, ば."""
    # Define particle pattern (single characters)
    particles = ["は", "が", "を", "に", "で", "へ", "と", "も", "ば"]
    # Use regex to find all particles (as they are single chars, we can just iterate)
    # But to be safe, we use findall with a character class
    found = re.findall(r"[はがをにてへともば]", text)
    counts = Counter(found)
    # Return dict with all particles (even zero)
    return {p: counts.get(p, 0) for p in particles}


def top_words(text: str, n: int = 15) -> List[str]:
    """Extract top n words (2+ kana/kanji) by frequency.
    Words are defined as sequences of 2+ Kanji or Hiragana/Katakana.
    """
    # Pattern for 2+ Kanji or Kana (excluding punctuation and single chars)
    # Note: This will also pick up repeated characters like ああ, which is acceptable.
    words = re.findall(r"[一-龠々]{2,}|[ァ-ヶー]{2,}", text)
    # Count frequencies
    counter = Counter(words)
    # Return top n words (just the word, not the count)
    return [word for word, _ in counter.most_common(n)]


def avg_sentence_length(sentences: List[str]) -> float:
    """Average sentence length in characters."""
    if not sentences:
        return 0.0
    total_len = sum(len(s) for s in sentences)
    return total_len / len(sentences)


def detect_banned(text: str, banned: List[str]) -> List[str]:
    """Return list of banned terms found in text."""
    found = []
    for term in banned:
        if term in text:
            found.append(term)
    return found


def read_banned_from_soul(book_id: int, branch_id: int = 1) -> List[str]:
    """Read the 禁則事項 section from SOUL.md and return a list of banned terms.
    Each line that starts with a hyphen is considered a banned term.
    """
    soul_path = _paths_mod.get_workspace_path(book_id, branch_id) / "SOUL.md"
    content = read_file_safe(soul_path)
    if not content:
        return []
    # Find the section ## 禁則事項
    # We'll look for the line and then collect until next ## or end
    lines = content.splitlines()
    in_section = False
    banned_terms = []
    for line in lines:
        if line.strip() == "## 禁則事項":
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                # Next section
                break
            if line.strip().startswith("-"):
                # Remove the hyphen and any surrounding whitespace
                term = line.strip()[1:].strip()
                if term:
                    banned_terms.append(term)
    return banned_terms


def analyze_style(content: str, book_id: int, branch_id: int = 1) -> Dict:
    """Analyze style of content and return a dict of features.
    Features: top_words (list), avg_len (float), particles (dict), banned_hits (list)
    """
    sentences = split_sentences(content)
    top_words_list = top_words(content, n=15)
    particles_dict = count_particles(content)
    avg_len = avg_sentence_length(sentences)
    banned_list = read_banned_from_soul(book_id, branch_id)
    banned_hits = detect_banned(content, banned_list)
    return {
        "top_words": top_words_list,
        "avg_len": avg_len,
        "particles": particles_dict,
        "banned_hits": banned_hits,
    }


def update_style_learned(book_id: int, ep_num: int, content: str, branch_id: int = 1) -> Path:
    """Update STYLE_LEARNED.md with analysis results for the given chapter.
    Returns the path to the updated file.
    """
    # Get workspace path
    base = _paths_mod.get_workspace_path(book_id, branch_id)
    # Ensure directories (memory/chapters etc.) exist via ensure_workspace_dirs in caller if needed
    # But we are only updating a file, so we ensure the parent of the file exists.
    style_path = base / "STYLE_LEARNED.md"
    style_path.parent.mkdir(parents=True, exist_ok=True)

    # Analyze style
    style = analyze_style(content, book_id, branch_id)

    # Prepare section content
    # We'll update each section with the latest analysis
    # For simplicity, we replace the entire section content with the new analysis.
    # In the future, we might want to keep a running log, but for now we replace.

    # Format top words as a comma-separated list
    top_words_line = ", ".join(style["top_words"]) if style["top_words"] else "(なし)"
    # Format average length
    avg_len_line = f"{style['avg_len']:.1f} 文字"
    # Format particles as a list of particle:count
    particles_line = ", ".join(
        [f"{p}:{c}" for p, c in style["particles"].items() if c > 0]
    ) or "(なし)"
    # Format banned hits
    banned_hits_line = ", ".join(style["banned_hits"]) if style["banned_hits"] else "(なし)"
    # Sample sentence: first sentence if available, else empty
    sentences = split_sentences(content)
    sample_line = sentences[0] if sentences else "(本文なし)"

    # Update each section
    update_section(style_path, "頻出語（上位N）", top_words_line)
    update_section(style_path, "平均文長", avg_len_line)
    update_section(style_path, "助詞傾向", particles_line)
    update_section(style_path, "禁則語（検出履歴）", banned_hits_line)
    update_section(style_path, "直近サンプル文", sample_line)

    return style_path


# ----------------------------------------------------------------------
# External-corpus style learning (opt-in)
# ----------------------------------------------------------------------


def _iter_corpus_text(corpus_dir) -> Iterable[str]:
    """Yield text blocks from a corpus directory.

    The corpus layout is produced by ``scripts/ingest_kakuyomu.py``:

        <corpus_dir>/
            manifest.json
            <work_id>/
                meta.json
                synopsis.txt        (always present, may be empty)
                episode_titles.txt  (always present, may be empty)
                tags.txt            (always present, one tag per line)
    """
    corpus_dir = Path(corpus_dir)
    if not corpus_dir.is_dir():
        return
    # Sort for determinism.
    for work_dir in sorted(corpus_dir.iterdir()):
        if not work_dir.is_dir():
            continue
        for fname in ("synopsis.txt", "episode_titles.txt", "tags.txt"):
            p = work_dir / fname
            if not p.exists():
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except OSError:
                continue
            if text.strip():
                yield text


def learn_from_corpus(corpus_dir, book_id: int, branch_id: int = 1) -> "Path | None":
    """Aggregate style features from an external corpus and write them
    into the workspace's ``STYLE_LEARNED.md`` under a dedicated
    "外部コーパス" section.

    The function is a **no-op** when ``corpus_dir`` does not exist or
    contains no readable text, and is safe to call when the opt-in flag
    is off (the caller is expected to gate the call, but we also gate
    internally as a safety belt).
    """
    from config.settings import ConfigManager  # local import: avoid cycles

    settings = ConfigManager.get_config()
    if not bool(getattr(settings, "kakuyomu_ingest_enabled", False)):
        return None

    corpus_dir = Path(corpus_dir)
    if not corpus_dir.is_dir():
        return None

    text_blocks = list(_iter_corpus_text(corpus_dir))
    if not text_blocks:
        return None

    combined = "\n".join(text_blocks)

    # Re-use the existing primitives so the feature shape is identical.
    sentences = split_sentences(combined)
    top_words_list = top_words(combined, n=20)
    particles_dict = count_particles(combined)
    avg_len = avg_sentence_length(sentences)
    banned_list = read_banned_from_soul(book_id, branch_id)
    banned_hits = detect_banned(combined, banned_list)

    style_path = _paths_mod.get_workspace_path(book_id, branch_id) / "STYLE_LEARNED.md"
    style_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = corpus_dir / "manifest.json"
    source_label = "カクヨムランディング(オプトイン)"
    if manifest.exists():
        try:
            import json as _json
            data = _json.loads(manifest.read_text(encoding="utf-8"))
            ranking = data.get("ranking")
            generated_at = data.get("generated_at")
            count = data.get("count")
            extra = []
            if ranking:
                extra.append(f"ランキング={ranking}")
            if count is not None:
                extra.append(f"作品数={count}")
            if generated_at:
                extra.append(f"生成={generated_at}")
            if extra:
                source_label = f"{source_label} ({', '.join(extra)})"
        except (OSError, ValueError):
            pass

    top_words_line = ", ".join(top_words_list) if top_words_list else "(なし)"
    avg_len_line = f"{avg_len:.1f} 文字"
    particles_line = ", ".join(
        f"{p}:{c}" for p, c in particles_dict.items() if c > 0
    ) or "(なし)"
    banned_hits_line = ", ".join(banned_hits) if banned_hits else "(なし)"

    body = (
        f"## 外部コーパス - 出典\n\n{source_label}\n\n"
        f"## 外部コーパス - 頻出語（上位N）\n\n{top_words_line}\n\n"
        f"## 外部コーパス - 平均文長\n\n{avg_len_line}\n\n"
        f"## 外部コーパス - 助詞傾向\n\n{particles_line}\n\n"
        f"## 外部コーパス - 禁則語（検出履歴）\n\n{banned_hits_line}\n"
    )

    # Append (do not overwrite the locally-learned sections above).
    with style_path.open("a", encoding="utf-8") as fh:
        fh.write("\n" + body)

    return style_path
