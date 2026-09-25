"""Character mention extractor from text."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from spacy.tokens import Doc, Span


@dataclass
class CharacterMention:
    """キャラクター言及情報"""
    text: str                    # 言及テキスト（名前、代名詞等）
    start_char: int              # 文字列内開始位置
    end_char: int                # 文字列内終了位置
    token_start: int             # トークンインデックス開始
    token_end: int               # トークンインデックス終了
    is_pronoun: bool = False     # 代名詞かどうか
    entity_type: Optional[str] = None  # 固有表現タイプ (PERSON等)
    normalized_name: Optional[str] = None  # 正規化名（辞書マッチ時）


class CharacterExtractor:
    """脚本からキャラクター名・言及を抽出"""
    
    def __init__(self, character_dict: Optional[set[str]] = None):
        self.character_dict = character_dict or set()
        # 一般的な人称代名詞
        self.first_person = {"私", "俺", "僕", "あたし", "わし", "自分", "拙者", "小生"}
        self.second_person = {"あなた", "君", "お前", "貴方", "貴君", "アンタ", "キミ", "お主", "そなた"}
        self.third_person = {"彼", "彼女", "あの人", "その人", "この人"}
        self.all_pronouns = self.first_person | self.second_person | self.third_person

    def extract(self, doc: Doc, character_dict: Optional[set[str]] = None) -> list[CharacterMention]:
        """ドキュメントからキャラクターメンション抽出
        
        優先順位:
        1. 固有表現抽出 (PERSON)
        2. キャラ辞書マッチ
        3. 代名詞検出（簡易）
        """
        dict_to_use = character_dict or self.character_dict
        mentions = []
        seen_spans = set()  # 重複除去用
        
        # 1. 固有表現 (PERSON) 抽出
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "PER", "Character"):
                span_key = (ent.start_char, ent.end_char)
                if span_key not in seen_spans:
                    mentions.append(CharacterMention(
                        text=ent.text,
                        start_char=ent.start_char,
                        end_char=ent.end_char,
                        token_start=ent.start,
                        token_end=ent.end,
                        entity_type=ent.label_,
                        normalized_name=self._normalize_name(ent.text, dict_to_use),
                    ))
                    seen_spans.add(span_key)
        
        # 2. キャラ辞書マッチ（固有表現で取れなかったもの）
        if dict_to_use:
            text = doc.text
            for char_name in dict_to_use:
                # 単純な文字列検索（改善の余地あり）
                start = 0
                while True:
                    idx = text.find(char_name, start)
                    if idx == -1:
                        break
                    end = idx + len(char_name)
                    span_key = (idx, end)
                    if span_key not in seen_spans:
                        # トークン位置を推定
                        token_start = self._char_to_token(doc, idx)
                        token_end = self._char_to_token(doc, end - 1) + 1
                        mentions.append(CharacterMention(
                            text=char_name,
                            start_char=idx,
                            end_char=end,
                            token_start=token_start,
                            token_end=token_end,
                            entity_type="DICT_MATCH",
                            normalized_name=char_name,
                        ))
                        seen_spans.add(span_key)
                    start = end
        
        # 3. 代名詞検出（簡易：トークンベース）
        for token in doc:
            if token.text in self.all_pronouns:
                span_key = (token.idx, token.idx + len(token.text))
                if span_key not in seen_spans:
                    mentions.append(CharacterMention(
                        text=token.text,
                        start_char=token.idx,
                        end_char=token.idx + len(token.text),
                        token_start=token.i,
                        token_end=token.i + 1,
                        is_pronoun=True,
                        entity_type="PRONOUN",
                    ))
                    seen_spans.add(span_key)
        
        # 位置順でソート
        mentions.sort(key=lambda m: m.start_char)
        return mentions

    def _normalize_name(self, name: str, char_dict: set[str]) -> Optional[str]:
        """名前を辞書内の正規名にマッピング"""
        if name in char_dict:
            return name
        # 部分マッチ試行
        for dict_name in char_dict:
            if dict_name in name or name in dict_name:
                return dict_name
        return None

    def _char_to_token(self, doc: Doc, char_idx: int) -> int:
        """文字位置からトークンインデックスを推定"""
        for i, token in enumerate(doc):
            if token.idx <= char_idx < token.idx + len(token.text):
                return i
        return len(doc) - 1 if doc else 0

    def get_speaker_for_span(self, doc: Doc, span_start: int, span_end: int) -> Optional[str]:
        """指定スパンの直前の発言者を推定（簡易ヒューリスティック）"""
        # スパン直前のテキストから発言者を探す
        text = doc.text[:span_start]
        
        # セリフ記号「」で区切って最後の発言者を探す
        import re
        # 「キャラ名「セリフ」」パターンを全て抽出
        pattern = r'([^「\n]+)「[^」]*」'
        matches = list(re.finditer(pattern, text))
        
        if matches:
            last_match = matches[-1]
            speaker = last_match.group(1).strip()
            if speaker in self.character_dict:
                return speaker
        
        return None


__all__ = ["CharacterMention", "CharacterExtractor"]