"""Density scorer for purple prose detection.

Provides paragraph-level scoring to determine when to activate
more intensive refinement based on multiple density metrics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class DensityScore:
    """Density metrics for a text segment.
    
    Attributes:
        aggressive_density: Aggressive reactions per 1000 characters
        metaphor_density: Metaphorical expressions per 1000 characters
        sensory_overload: Ratio of dominant sensory modality (0-1)
        verb_strength: Verb diversity ratio (0-1)
    """
    aggressive_density: float = 0.0
    metaphor_density: float = 0.0
    sensory_overload: float = 0.0
    verb_strength: float = 0.0


class DensityScorer:
    """Scores text density to detect purple prose tendencies.
    
    Analyzes multiple dimensions:
    1. Aggressive physical reaction density
    2. Metaphorical expression density  
    3. Sensory language bias (over-reliance on one sense)
    4. Verb strength/diversity (lack of verb variety indicates weak writing)
    """
    
    # Sensory lexicons for detecting over-reliance on specific modalities
    SENSORY_LEXICON: Dict[str, set[str]] = {
        "visual": {
            "視線", "瞳", "目", "見る", "眺める", "光", "影", "色", 
            "輝く", "きらめく", "暗い", "明るい", "赤", "青", "緑", "黄", 
            "白", "黒", "輝き", "glow", "sparkle", "gleam"
        },
        "auditory": {
            "音", "声", "響き", "静寂", "囁き", "叫び", "騒音", 
            "音楽", "歌う", "ささやく", "怒鳴る", "泣く", "笑う",
            "騒がしい", "静かな", "響渡る", "耳鳴り"
        },
        "tactile": {
            "冷た", "熱", "痛", "触れ", "肌", "指先", "震え", 
            "ざらざら", "つるつる", "ぬるぬる", "こわばる", "しびれ",
            "感触", "手触り", "肌ざわり", "温度", "体温"
        },
        "visceral": {
            "胃", "心臓", "血", "息", "吐き気", "めまい", "脳", 
            "腸", "肝臓", "腎臓", "嘔吐", "下痢", "便秘",
            "動悸", "息切れ", "立ち眩み", "ふらつき"
        }
    }
    
    # Aggressive physical reaction patterns
    AGGRESSIVE_LEXICON: set[str] = {
        "歯を食いしば", "舌打ち", "拳を握り", "胃を痛め", 
        "血の気が引", "激痛が脳", "奥歯を軋ませ", "目を剥き",
        "声を荒げ", "眉をひそめ", "肩をすくめ", "足をすくめ"
    }
    
    # Metaphor markers
    METAPHOR_MARKERS: set[str] = {
        "まるで", "ように", "かのよう", "似ている", "似た", 
        " analogously", "likewise", "as if", "as though"
    }

    @classmethod
    def score_paragraph(cls, paragraph: str) -> DensityScore:
        """Score a paragraph for purple prose tendencies.
        
        Args:
            paragraph: Text paragraph to score
            
        Returns:
            DensityScore object with four density metrics
        """
        if not paragraph or not paragraph.strip():
            return DensityScore()
        
        chars = len(paragraph)
        if chars == 0:
            return DensityScore()
        
        # Calculate aggressive reaction density
        aggressive_count = sum(
            1 for term in cls.AGGRESSIVE_LEXICON 
            if term in paragraph
        )
        aggressive_density = (aggressive_count * 1000) / chars
        
        # Calculate metaphor density
        metaphor_count = sum(
            1 for marker in cls.METAPHOR_MARKERS 
            if marker in paragraph
        )
        # Also count simile/metaphor patterns
        metaphor_pattern_count = len(re.findall(r"(まるで|のように|かのよう)", paragraph))
        metaphor_count = max(metaphor_count, metaphor_pattern_count)
        metaphor_density = (metaphor_count * 1000) / chars
        
        # Calculate sensory overload (dominance of one sensory modality)
        sensory_counts: Dict[str, int] = {}
        total_sensory = 0
        
        for modality, lexicon in cls.SENSORY_LEXICON.items():
            count = sum(1 for term in lexicon if term in paragraph)
            sensory_counts[modality] = count
            total_sensory += count
        
        if total_sensory > 0:
            # Calculate how much one sense dominates (0 = evenly distributed, 1 = one sense only)
            max_count = max(sensory_counts.values()) if sensory_counts else 0
            sensory_overload = max_count / total_sensory
            # Normalize: 0.33 (even distribution) -> 0.0, 1.0 (one sense) -> 1.0
            sensory_overload = max(0.0, min(1.0, (sensory_overload - 0.33) * 1.5))
        else:
            sensory_overload = 0.0
        
        # Calculate verb strength (diversity of verb usage)
        # Find verb-like patterns (simplified: words ending in common Japanese verb endings)
        verb_patterns = [
            r"[あ-ん]+た", r"[あ-ん]+だ", r"[あ-ん]+て", r"[あ-ん]+る",
            r"[あ-ん]+よう", r"[あ-ん]+そう", r"[あ-ん]+たい", r"[あ-ん]+ない"
        ]
        
        verbs_found: List[str] = []
        for pattern in verb_patterns:
            verbs_found.extend(re.findall(pattern, paragraph))
        
        if verbs_found:
            # Higher diversity = better verb strength (more varied vocabulary)
            unique_verbs = len(set(verbs_found))
            total_verbs = len(verbs_found)
            verb_strength = unique_verbs / total_verbs if total_verbs > 0 else 0.0
        else:
            verb_strength = 0.0  # No verbs found = very weak
            
        return DensityScore(
            aggressive_density=aggressive_density,
            metaphor_density=metaphor_density,
            sensory_overload=sensory_overload,
            verb_strength=verb_strength
        )
    
    @classmethod
    def should_simplify(
        cls, 
        score: DensityScore, 
        aggressive_threshold: float = 2.0,
        metaphor_threshold: float = 3.0,
        sensory_threshold: float = 0.5,
        verb_strength_threshold: float = 0.3
    ) -> bool:
        """Determine if text should be simplified based on density scores.
        
        Args:
            score: DensityScore to evaluate
            aggressive_threshold: Max aggressive reactions per 1000 chars
            metaphor_threshold: Max metaphors per 1000 chars
            sensory_threshold: Max sensory overload ratio (0-1)
            verb_strength_threshold: Min verb diversity ratio (0-1)
            
        Returns:
            True if text exceeds thresholds and should be simplified
        """
        return (
            score.aggressive_density > aggressive_threshold or
            score.metaphor_density > metaphor_threshold or
            score.sensory_overload > sensory_threshold or
            score.verb_strength < verb_strength_threshold
        )
    
    @classmethod
    def get_density_category(cls, score: DensityScore) -> str:
        """Get a human-readable category for the density score.
        
        Args:
            score: DensityScore to categorize
            
        Returns:
            String category: "clean", "moderate", "elevated", or "high"
        """
        risk_factors = 0
        
        if score.aggressive_density > 1.0:
            risk_factors += 1
        if score.metaphor_density > 1.5:
            risk_factors += 1
        if score.sensory_overload > 0.3:
            risk_factors += 1
        if score.verb_strength < 0.5:
            risk_factors += 1
            
        if risk_factors == 0:
            return "clean"
        elif risk_factors == 1:
            return "moderate"
        elif risk_factors == 2:
            return "elevated"
        else:
            return "high"