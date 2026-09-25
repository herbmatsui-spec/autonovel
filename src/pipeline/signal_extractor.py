"""Dependency-based emotional signal extractor."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from spacy.tokens import Doc, Token

from src.pipeline.emotional_residue import EmotionalSignal, EmotionType
from src.pipeline.emotion_config import EmotionLexicon
from src.pipeline.character_extractor import CharacterMention


@dataclass
class DependencyPattern:
    """依存構造パターン"""
    subj_dep: str
    obj_dep: str
    emotion_type: str
    weight: float


class SignalExtractor:
    """依存構造から感情シグナルを抽出"""
    
    def __init__(
        self,
        lexicon: EmotionLexicon,
        patterns: Optional[list[DependencyPattern]] = None,
    ):
        self.lexicon = lexicon
        self.patterns = patterns or self._default_patterns()
        
        # 極性反転動詞・修飾語
        self.flip_verbs = set(lexicon.polarity_flip_verbs)
        self.intensifiers = set(lexicon.intensifiers)
        self.attenuators = set(lexicon.attenuators)

    def _default_patterns(self) -> list[DependencyPattern]:
        """デフォルトパターン（設定から読み込み）"""
        from src.pipeline.emotion_config import load_dependency_patterns
        raw_patterns = load_dependency_patterns()
        return [
            DependencyPattern(p[0], p[1], p[2], p[3])
            for p in raw_patterns
        ]

    def extract_signals(
        self,
        doc: Doc,
        characters: list[CharacterMention],
        episode_id: str,
    ) -> list[EmotionalSignal]:
        """ドキュメントから感情シグナル抽出"""
        signals = []
        
        # キャラ名→トークン位置マップ作成
        char_tokens = self._build_char_token_map(doc, characters)
        
        # 各文を処理
        for sent in doc.sents:
            sent_signals = self._extract_from_sentence(sent, char_tokens, episode_id)
            signals.extend(sent_signals)
        
        return signals

    def _build_char_token_map(
        self, doc: Doc, characters: list[CharacterMention]
    ) -> dict[int, str]:
        """トークンインデックス→キャラ名マップ"""
        char_map = {}
        for char in characters:
            for i in range(char.token_start, char.token_end):
                if i < len(doc):
                    char_map[i] = char.normalized_name or char.text
        return char_map

    def _extract_from_sentence(
        self,
        sent,
        char_tokens: dict[int, str],
        episode_id: str,
    ) -> list[EmotionalSignal]:
        """単一文からシグナル抽出"""
        signals = []
        
        # ROOT動詞を探す
        root_verbs = [t for t in sent if t.dep_ == "ROOT" and t.pos_ == "VERB"]
        if not root_verbs:
            # 動詞がない場合は形容詞もチェック
            root_verbs = [t for t in sent if t.dep_ == "ROOT" and t.pos_ in ("ADJ", "ADJ_SAT")]
        
        for root in root_verbs:
            # 主語と目的語を取得
            subjs = self._get_subjects(root, char_tokens)
            objs = self._get_objects(root, char_tokens)
            
            for subj_token, subj_name in subjs:
                for obj_token, obj_name in objs:
                    if subj_name == obj_name:
                        continue  # 自分自身への感情はスキップ
                    
                    # 感情判定
                    emotion_type, value = self._classify_emotion(root, sent.text)
                    if value == 0.0:
                        continue
                    
                    # 信頼度計算
                    confidence = self._calculate_confidence(root, sent.text, subj_token, obj_token)
                    
                    # 原因抽出（動詞のレマ＋主要引数）
                    cause = self._extract_cause(root, subj_name, obj_name)
                    
                    signal = EmotionalSignal(
                        source=subj_name,
                        target=obj_name,
                        emotion_type=EmotionType(emotion_type),
                        value=value,
                        confidence=confidence,
                        evidence_span=sent.text.strip(),
                        episode_id=episode_id,
                        cause=cause,
                    )
                    signals.append(signal)
        
        return signals

    def _get_subjects(self, root: Token, char_tokens: dict[int, str]) -> list[tuple[Token, str]]:
        """主語（nsubj, nsubj:pass等）を取得"""
        subjects = []
        for child in root.children:
            if child.dep_.startswith("nsubj") and child.i in char_tokens:
                subjects.append((child, char_tokens[child.i]))
        return subjects

    def _get_objects(self, root: Token, char_tokens: dict[int, str]) -> list[tuple[Token, str]]:
        """目的語（dobj, iobj, obl等）を取得"""
        objects = []
        for child in root.children:
            if child.dep_ in ("dobj", "iobj", "obl") and child.i in char_tokens:
                objects.append((child, char_tokens[child.i]))
            # 「に」格も目的語として扱う（恐怖・信頼等）
            elif child.dep_ == "case" and child.text == "に" and child.head.i in char_tokens:
                objects.append((child.head, char_tokens[child.head.i]))
        return objects

    def _classify_emotion(self, verb: Token, sent_text: str) -> tuple[str, float]:
        """動詞・文から感情タイプと値を判定"""
        from src.pipeline.polarity import classify_emotion
        return classify_emotion(verb, sent_text, self.lexicon)

    def _calculate_confidence(
        self, verb: Token, sent_text: str, subj: Token, obj: Token
    ) -> float:
        """信頼度計算（0.0-1.0）"""
        base_conf = 0.5
        
        # 依存関係が明確なら加点
        if subj.dep_ == "nsubj" and obj.dep_ in ("dobj", "iobj"):
            base_conf += 0.2
        elif subj.dep_ == "nsubj" and obj.dep_ == "obl":
            base_conf += 0.1
        
        # 極性反転動詞ならやや減点（解釈が難しいため）
        if verb.lemma_ in self.flip_verbs:
            base_conf -= 0.1
        
        # 修飾語による調整
        sent_lower = sent_text.lower()
        for intensifier in self.intensifiers:
            if intensifier in sent_lower:
                base_conf += 0.1
                break
        for attenuator in self.attenuators:
            if attenuator in sent_lower:
                base_conf -= 0.1
                break
        
        return max(0.1, min(1.0, base_conf))

    def _extract_cause(self, verb: Token, subj: str, obj: str) -> str:
        """原因テキスト抽出（簡易）"""
        # 動詞のレマ＋主要な子要素
        parts = [verb.lemma_]
        for child in verb.children:
            if child.dep_ in ("dobj", "iobj", "obl", "advmod", "compound"):
                parts.append(child.text)
        return f"{subj}が{obj}に{''.join(parts)}"


__all__ = ["SignalExtractor", "DependencyPattern"]