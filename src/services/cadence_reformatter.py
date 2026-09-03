"""Cadence & Rhythm Reformatter Service
小説本文の音律・リズム・文末連続（〜た・〜だ）を検知し、
自然なドライブ感とスマホ読書に最適化されたテンポへ自動整形するポストプロセッサ。
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class CadenceStats:
    """文章の音律・ケイデンス統計情報"""

    total_sentences: int
    repeated_endings_fixed: int
    avg_sentence_length: float
    paragraph_count: int


class CadenceReformatter:
    """音律・文末リズム自動補正器"""

    # 過去形・断定文末パターン
    TA_ENDINGS = ("た。", "いた。", "った。", "れた。", "せた。", "だ。")

    def reformat_novel_text(self, text: str) -> tuple[str, CadenceStats]:
        """小説本文のリズム・文末連続・改行を整形"""
        if not text or not text.strip():
            return text, CadenceStats(0, 0, 0.0, 0)

        paragraphs = text.split("\n")
        fixed_paragraphs: list[str] = []
        total_fixes = 0
        total_sentences = 0
        sentence_lengths: list[int] = []

        for p in paragraphs:
            trimmed = p.strip()
            if not trimmed:
                fixed_paragraphs.append("")
                continue

            # 会話文（「...」）は原則として役者の口調を尊重してそのまま保持
            if trimmed.startswith("「") or trimmed.startswith("『"):
                fixed_paragraphs.append(trimmed)
                continue

            # 地の文の文末リズム補正
            repaired_p, fixes, s_count, lengths = self._reformat_paragraph(trimmed)
            fixed_paragraphs.append(repaired_p)
            total_fixes += fixes
            total_sentences += s_count
            sentence_lengths.extend(lengths)

        result_text = "\n".join(fixed_paragraphs)
        # 空行の多重連続を2行（1空行）に正規化
        result_text = re.sub(r"\n{3,}", "\n\n", result_text)

        avg_len = sum(sentence_lengths) / max(len(sentence_lengths), 1)
        stats = CadenceStats(
            total_sentences=total_sentences,
            repeated_endings_fixed=total_fixes,
            avg_sentence_length=round(avg_len, 1),
            paragraph_count=len(paragraphs),
        )

        return result_text, stats

    def _reformat_paragraph(self, paragraph: str) -> tuple[str, int, int, list[int]]:
        """1段落内の文末連続を検知して補正"""
        # 句点で分割（句点自体を保持）
        raw_sentences = re.split(r"(?<=[。！？!?])", paragraph)
        sentences = [s for s in raw_sentences if s.strip()]
        if not sentences:
            return paragraph, 0, 0, []

        consecutive_ta_count = 0
        fixes = 0
        repaired: list[str] = []
        lengths: list[int] = []

        for i, s in enumerate(sentences):
            s_clean = s.strip()
            lengths.append(len(s_clean))

            is_ta = any(s_clean.endswith(end) for end in self.TA_ENDINGS)
            if is_ta:
                consecutive_ta_count += 1
            else:
                consecutive_ta_count = 0

            # 「〜た」が3連続した場合、3つ目を体言止めや接続形、またはニュアンス変換
            if consecutive_ta_count >= 3:
                fixed_s = self._break_ta_ending(s_clean)
                if fixed_s != s_clean:
                    repaired.append(fixed_s)
                    fixes += 1
                    consecutive_ta_count = 0
                    continue

            repaired.append(s_clean)

        return "".join(repaired), fixes, len(sentences), lengths

    def _break_ta_ending(self, sentence: str) -> str:
        """〜た。で終わる文を体言止めや躍動感のある文末へ変換"""
        s = sentence

        # パターン1: 「〜ていた。」 -> 「〜ている。」または「〜ていた――」
        if s.endswith("ていた。"):
            return s[:-4] + "ていた――。"
        if s.endswith("思っていた。"):
            return s[:-6] + "思う。"
        if s.endswith("感じていた。"):
            return s[:-6] + "感じる。"

        # パターン2: 「〜だった。」 -> 「〜だ。」または「〜である。」
        if s.endswith("だった。"):
            return s[:-4] + "である。"
        if s.endswith("のだった。"):
            return s[:-5] + "のだ。"

        # パターン3: 「〜した。」 -> 「〜する。」または省略
        if s.endswith("確信した。"):
            return s[:-5] + "確信――。"
        if s.endswith("決意した。"):
            return s[:-5] + "決意を固める。"
        if s.endswith("見つめていた。"):
            return s[:-7] + "見つめる。"
        if s.endswith("息を呑んだ。"):
            return s[:-6] + "息を呑む。"

        # パターン4: 「〜に満ちていた。」 -> 「〜に満ちる。」
        if s.endswith("満ちていた。"):
            return s[:-6] + "満ちていたのだ。"

        # パターン5: 一般的な「〜した。」を動詞終止形へ
        if s.endswith("した。") and len(s) > 4:
            return s[:-3] + "する。"

        return sentence


cadence_reformatter = CadenceReformatter()
