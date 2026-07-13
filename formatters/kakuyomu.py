from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.backend.sanitizer import ContentValidator, SeriousnessFilter

from .base import BaseFormatter


class KakuyomuFormatter(BaseFormatter):
    """カクヨム形式テキストフォーマッタ"""

    def remove_ai_isms(self, text: str) -> str:
        """AI特有の定型句（AI-isms）を自然な表現に置換または削除する"""
        ai_isms = [
            (r'言うまでもない[がか]?、?', ''),
            (r'特筆すべきは、', ''),
            (r'その時だった。?', ''),
            (r'誰の目にも明らかだった。?', ''),
            (r'息を呑[むん]だ。?', '言葉を失った。'),
            (r'目を丸くした。?', '瞬きを忘れた。'),
            (r'驚きを隠せなかった。?', '絶句した。'),
            (r'静寂が支配した。?', '水を打ったような静けさが落ちた。'),
            (r'言うまでもない。', ''),
        ]
        for pattern, replacement in ai_isms:
            text = re.sub(pattern, replacement, text)
        return text

    def enforce_cliffhanger(self, text: str) -> str:
        """エピソード末尾の「引き（クリフハンガー）」を視覚的に強調する"""
        text = text.strip()
        if not text:
            return text

        # デバッグ：二重付与を防ぎつつ、読者が「次を読みたくなる」余韻を強制
        text = text.rstrip('。')
        if not text.endswith('――') and not text.endswith('……'):
            text += '――'

        # 最後の文を視覚的に分離して余韻を持たせる
        parts = text.rsplit('\n\n', 1)
        if len(parts) == 2:
            main_text, last_para = parts
            return f"{main_text}\n\n　――{last_para.strip()}"
        return text

    def format(
        self,
        text: str,
        genre: str = "default",
        thinning_rate: float = 0.0,
        characters: Optional[List[Any]] = None,
        sanitizer_policy: Optional[Dict[str, Any]] = None,
        intensity: float = 0.5,
        archetypes: Optional[List[str]] = None,
        location_map: Optional[Dict[str, str]] = None,
        is_catharsis: bool = False,
        tension: int = 50,
        tension_delta: int = 0,
        **kwargs
    ) -> str:
        """カクヨム形式への完全整形：段落の「白さ」制御を強化"""
        if not text:
            return ""

        # AI-ismsの除去
        text = self.remove_ai_isms(text)

        # シリアス度検知とギャグ補正の適用
        s_filter = SeriousnessFilter()
        text = s_filter.filter(text)

        # AI前置き・コードブロック除去
        text = re.sub(
            r'^(はい|承知|了解|以下|これ|Here|Sure|JSON形式で出力します|了解しました).*?(\n|$)',
            '', text, flags=re.IGNORECASE | re.MULTILINE
        ).strip()
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)

        # 構造タグ・メタタグの最終除去
        struct_tags = r'(SCENE|Scene|シーン|CHAPTER|Chapter|第\d+話|EPISODE|Episode|エピソード)'
        text = re.sub(r'^[#\s\*]*\[?' + struct_tags + r'\s*[\d一二三四五六七八九十]+\]?[:：\s\*]*.*$', '', text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'\[.*?\]', '', text)

        # 台本形式の除去ロジックをより高速な単一パスの置換へ統合
        def _process_dialogue_line(match):
            notes = re.findall(r'[（(](.*?)[）)]', match.group(1))
            if notes: return "。".join(notes) + "。\n" + match.group(2)
            return match.group(1).strip() + "\n" + match.group(2)

        text = re.sub(r'^([^「『\n]+)([「『].*?[」』])', _process_dialogue_line, text, flags=re.MULTILINE)

        # 記号の統一
        text = re.sub(r'\.{3,}', '……', text)
        text = re.sub(r'[…・]{1,}', '……', text)
        text = text.replace("。。", "。")
        text = re.sub(r'([？！])(?![\s　」』])', r'\1　', text)

        # --- 「白さ」の動的制御 ---
        analysis = ContentValidator.analyze_word_heaviness(text)
        kanji_rate = analysis["kanji_rate"]

        is_dense = kanji_rate > 30
        max_lines_per_para = 1 if is_dense else 2
        max_chars_per_line = 35 if kanji_rate > 35 else 45
        force_break_at_period = kanji_rate > 33

        lines         = [l.strip() for l in text.split('\n')]
        new_lines     = []
        narrative_cnt = 0

        for line in lines:
            if not line:
                if new_lines and new_lines[-1] != "":
                    new_lines.append("")
                narrative_cnt = 0
                continue

            # 全角インデントの自動付与（特定の記号以外）
            if line[0] not in ['「', '『', '（', '<', '【', '［', '〔', '〈', '《']:
                line = '　' + line

            is_dialogue = line.strip().startswith(('「', '『', '（'))

            if is_dialogue:
                if new_lines and new_lines[-1] != "":
                    new_lines.append("")
                new_lines.append(line)
                new_lines.append("")
                narrative_cnt = 0
            else:
                new_lines.append(line)
                narrative_cnt += 1

                should_break = False
                if force_break_at_period and "。" in line:
                    should_break = True
                elif narrative_cnt >= max_lines_per_para or len(line) > max_chars_per_line:
                    should_break = True

                if should_break:
                    new_lines.append("")
                    narrative_cnt = 0

        result = "\n".join(new_lines).strip()
        result = re.sub(r'\n{3,}', '\n\n', result)

        return self.enforce_cliffhanger(result)

