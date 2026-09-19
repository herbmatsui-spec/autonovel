"""Emotion polarity classification from verbs and context."""
from __future__ import annotations

from typing import Tuple

from spacy.tokens import Token

from src.pipeline.emotion_config import EmotionLexicon
from src.pipeline.emotional_residue import EmotionType


def classify_emotion(
    verb_token: Token,
    sent_text: str,
    lexicon: EmotionLexicon,
) -> Tuple[str, float]:
    """動詞・文から感情タイプと極性値を判定
    
    Returns:
        (emotion_type, value) - valueは-1.0~1.0
    """
    lemma = verb_token.lemma_.lower()
    text = sent_text.lower()
    
    # 全感情タイプをチェック
    best_emotion = "neutral"
    best_score = 0.0
    
    for emo_type in [
        "affection", "tension", "fear", "trust", "intimacy",
        "jealousy", "anger", "sadness", "surprise", "disgust"
    ]:
        pos_words = lexicon.get_positive_words(emo_type)
        neg_words = lexicon.get_negative_words(emo_type)
        
        pos_count = sum(1 for w in pos_words if w in text)
        neg_count = sum(1 for w in neg_words if w in text)
        
        # 動詞レマ自体もチェック
        if lemma in pos_words:
            pos_count += 2
        if lemma in neg_words:
            neg_count += 2
        
        if pos_count > neg_count:
            # 正の感情
            diff = pos_count - neg_count
            score = min(1.0, 0.3 + 0.2 * diff)
            if score > best_score:
                best_score = score
                best_emotion = emo_type
        elif neg_count > pos_count:
            # 負の感情（逆極性）
            diff = neg_count - pos_count
            score = -min(1.0, 0.3 + 0.2 * diff)
            if abs(score) > abs(best_score):
                best_score = score
                best_emotion = emo_type
    
    # 極性反転チェック（裏切る等）
    if lemma in lexicon.polarity_flip_verbs:
        # 好感度→嫌悪、信頼→不信 等の反転
        if best_emotion in ("affection", "trust", "intimacy"):
            best_score = -abs(best_score)
            if best_emotion == "affection":
                best_emotion = "disgust"
            elif best_emotion == "trust":
                best_emotion = "anger"  # 不信感として怒りに近い
    
    return best_emotion, best_score


__all__ = ["classify_emotion"]