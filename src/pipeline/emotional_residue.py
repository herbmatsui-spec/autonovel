"""Emotional residue data structures for cross-episode emotional continuity."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EmotionType(str, Enum):
    """感情タイプの列挙"""
    AFFECTION = "affection"       # 好感度・愛着
    TENSION = "tension"           # 緊張度・警戒心
    FEAR = "fear"                 # 恐怖・戦慄
    TRUST = "trust"               # 信頼・安心感
    INTIMACY = "intimacy"         # 親密度・共有秘密
    JEALOUSY = "jealousy"         # 嫉妬・独占欲
    ANGER = "anger"               # 怒り・敵意
    SADNESS = "sadness"           # 悲しみ・喪失感
    SURPRISE = "surprise"         # 驚き・衝撃
    DISGUST = "disgust"           # 嫌悪・軽蔑


@dataclass
class EmotionalSignal:
    """単一の感情シグナル（抽出された生データ）"""
    source: str                    # 感情の主体（誰が感じているか）
    target: str                    # 感情の対象（誰に対してか）
    emotion_type: EmotionType      # 感情の種類
    value: float                   # 感情値 (-1.0 ~ 1.0)
    confidence: float              # 信頼度 (0.0 ~ 1.0)
    evidence_span: str             # 根拠となった脚本スパン
    episode_id: str                # エピソードID
    cause: Optional[str] = None    # 原因イベント（任意）
    hidden: bool = False           # 表向き/内心の区別

    def __post_init__(self):
        # 値のクランプ
        self.value = max(-1.0, min(1.0, self.value))
        self.confidence = max(0.0, min(1.0, self.confidence))

    @property
    def pair_key(self) -> tuple[str, str]:
        return (self.source, self.target)

    @property
    def full_key(self) -> tuple[str, str, EmotionType]:
        return (self.source, self.target, self.emotion_type)


@dataclass
class EmotionalVector:
    """エピソード単位の感情ベクトル（集約済み）"""
    episode_id: str
    signals: dict[tuple[str, str, EmotionType], float] = field(default_factory=dict)
    confidences: dict[tuple[str, str, EmotionType], float] = field(default_factory=dict)
    causes: dict[tuple[str, str, EmotionType], str] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def set_signal(self, signal: EmotionalSignal) -> None:
        """シグナルを追加・更新（重み付き平均でマージ）"""
        key = signal.full_key
        existing_value = self.signals.get(key, 0.0)
        existing_conf = self.confidences.get(key, 0.0)
        
        # 信頼度加重平均でマージ
        total_conf = existing_conf + signal.confidence
        if total_conf > 0:
            self.signals[key] = (
                existing_value * existing_conf + signal.value * signal.confidence
            ) / total_conf
            self.confidences[key] = min(1.0, total_conf)
        else:
            self.signals[key] = signal.value
            self.confidences[key] = signal.confidence
        
        # 原因は新しい方を採用（上書き）
        if signal.cause:
            self.causes[key] = signal.cause

    def get_value(self, source: str, target: str, emotion: EmotionType) -> float:
        """感情値を取得（存在しない場合は0.0）"""
        return self.signals.get((source, target, emotion), 0.0)

    def get_confidence(self, source: str, target: str, emotion: EmotionType) -> float:
        """信頼度を取得"""
        return self.confidences.get((source, target, emotion), 0.0)

    def get_cause(self, source: str, target: str, emotion: EmotionType) -> Optional[str]:
        """原因を取得"""
        return self.causes.get((source, target, emotion))

    def get_pair_emotions(self, source: str, target: str) -> dict[EmotionType, float]:
        """特定ペアの全感情を取得"""
        return {
            emo: val for (s, t, emo), val in self.signals.items()
            if s == source and t == target
        }

    def get_top_pairs(self, limit: int = 5) -> list[tuple[tuple[str, str], dict[EmotionType, float]]]:
        """主要ペアを強度順で取得"""
        pair_scores = {}
        for (s, t, emo), val in self.signals.items():
            key = (s, t)
            if key not in pair_scores:
                pair_scores[key] = 0.0
            pair_scores[key] += abs(val)
        
        sorted_pairs = sorted(pair_scores.items(), key=lambda x: x[1], reverse=True)
        return [
            (pair, self.get_pair_emotions(pair[0], pair[1]))
            for pair, _ in sorted_pairs[:limit]
        ]

    def to_dict(self) -> dict:
        """シリアライズ用辞書変換"""
        return {
            "episode_id": self.episode_id,
            "signals": {
                f"{s}->{t}:{emo.value}": val
                for (s, t, emo), val in self.signals.items()
            },
            "confidences": {
                f"{s}->{t}:{emo.value}": conf
                for (s, t, emo), conf in self.confidences.items()
            },
            "causes": {
                f"{s}->{t}:{emo.value}": cause
                for (s, t, emo), cause in self.causes.items()
            },
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> EmotionalVector:
        """辞書から復元"""
        vec = cls(episode_id=data["episode_id"])
        for key_str, val in data.get("signals", {}).items():
            s, rest = key_str.split("->", 1)
            t, emo_str = rest.rsplit(":", 1)
            emo = EmotionType(emo_str)
            vec.signals[(s, t, emo)] = val
        for key_str, conf in data.get("confidences", {}).items():
            s, rest = key_str.split("->", 1)
            t, emo_str = rest.rsplit(":", 1)
            emo = EmotionType(emo_str)
            vec.confidences[(s, t, emo)] = conf
        for key_str, cause in data.get("causes", {}).items():
            s, rest = key_str.split("->", 1)
            t, emo_str = rest.rsplit(":", 1)
            emo = EmotionType(emo_str)
            vec.causes[(s, t, emo)] = cause
        vec.metadata = data.get("metadata", {})
        return vec


__all__ = ["EmotionType", "EmotionalSignal", "EmotionalVector", "EmotionalResidueExtractor"]


class EmotionalResidueExtractor:
    """エピソード終了時の感情残基抽出・永続化メインクラス"""
    
    def __init__(
        self,
        vector_store,
        character_dict: set[str],
        nlp_model: str = "ja_ginza",
    ):
        self.vector_store = vector_store
        self.character_dict = character_dict
        
        # 遅延初期化（循環インポート回避）
        self._nlp = None
        self._nlp_model = nlp_model
        self._char_extractor = None
        self._signal_extractor = None
        self._lexicon = None
    
    @property
    def nlp(self):
        if self._nlp is None:
            from src.pipeline.nlp_init import get_nlp
            self._nlp = get_nlp(self._nlp_model)
        return self._nlp
    
    @property
    def char_extractor(self):
        if self._char_extractor is None:
            from src.pipeline.character_extractor import CharacterExtractor
            self._char_extractor = CharacterExtractor(self.character_dict)
        return self._char_extractor
    
    @property
    def signal_extractor(self):
        if self._signal_extractor is None:
            from src.pipeline.signal_extractor import SignalExtractor
            from src.pipeline.emotion_config import load_emotion_lexicon
            self._lexicon = load_emotion_lexicon()
            self._signal_extractor = SignalExtractor(self._lexicon)
        return self._signal_extractor
    
    def extract_and_persist(self, episode_id: str, script: str) -> EmotionalVector:
        """脚本から感情ベクトル抽出・永続化
        
        Args:
            episode_id: エピソード識別子 (例: "ep14")
            script: 脚本テキスト
            
        Returns:
            抽出された感情ベクトル
        """
        # NLP処理
        doc = self.nlp(script)
        
        # キャラクター抽出
        characters = self.char_extractor.extract(doc, self.character_dict)
        
        # 感情シグナル抽出
        signals = self.signal_extractor.extract_signals(doc, characters, episode_id)
        
        # 集約
        from src.pipeline.aggregator import aggregate_signals
        vector = aggregate_signals(signals)
        vector.episode_id = episode_id
        
        # 永続化（ネームスペース: "pipeline"）
        if self.vector_store:
            # キー形式: ep{episode_id}:{source}->{target}
            # ペアごとに個別保存も可能だが、ここではエピソード単位で1キーにまとめる
            key = f"{episode_id}"
            self.vector_store.upsert("pipeline", key, vector)
        
        return vector