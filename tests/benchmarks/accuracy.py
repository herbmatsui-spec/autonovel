"""Accuracy metrics for scene-type trimming evaluation."""
from __future__ import annotations

import hashlib
from typing import Dict, List, Set, Any
from tests.benchmarks.annotations import SCENE_ANNOTATIONS


def _simple_embedding(text: str, dim: int = 128) -> List[float]:
    """
    Simple deterministic pseudo-embedding for testing.
    Uses hash-based projection for reproducibility without external deps.
    """
    # Create a simple hash-based embedding
    vec = [0.0] * dim
    words = text.split()
    for i, word in enumerate(words):
        # Hash each word to multiple dimensions
        h = hashlib.md5(word.encode()).hexdigest()
        for j in range(0, min(len(h), 32), 2):
            idx = int(h[j:j+2], 16) % dim
            val = (int(h[j:j+2], 16) / 255.0) - 0.5
            vec[idx] += val
    # Normalize
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def narrative_coherence(
    original_text: str,
    compressed_text: str,
    embedder: Any = None,
) -> float:
    """
    Calculate narrative coherence score using embedding similarity.
    
    Args:
        original_text: Original uncompressed text
        compressed_text: Compressed context text
        embedder: Optional embedder with .encode() method (uses simple hash if None)
    
    Returns:
        Coherence score 0.0 to 1.0 (higher = more coherent)
    """
    if not original_text or not compressed_text:
        return 0.0
    
    if embedder and hasattr(embedder, 'encode'):
        orig_vec = embedder.encode(original_text)
        comp_vec = embedder.encode(compressed_text)
    else:
        orig_vec = _simple_embedding(original_text)
        comp_vec = _simple_embedding(compressed_text)
    
    sim = cosine_similarity(orig_vec, comp_vec)
    # Map from [-1, 1] to [0, 1]
    return max(0.0, min(1.0, (sim + 1.0) / 2.0))


def category_preservation_rate(
    expected_categories: List[str],
    actual_categories: List[str],
) -> float:
    """
    Calculate category preservation rate.
    
    Args:
        expected_categories: List of category names that should be preserved
        actual_categories: List of category names actually present in compressed output
    
    Returns:
        Ratio of expected categories found in actual (0.0 to 1.0)
    """
    if not expected_categories:
        return 1.0
    
    expected_set = set(expected_categories)
    actual_set = set(actual_categories)
    
    found = expected_set & actual_set
    return len(found) / len(expected_set)


def key_entity_retention(
    expected_entities: List[str],
    actual_text: str,
    case_sensitive: bool = False,
) -> float:
    """
    Calculate key entity retention rate.
    
    Args:
        expected_entities: List of entity names that should be retained
        actual_text: Compressed context text
        case_sensitive: Whether matching is case sensitive
    
    Returns:
        Ratio of expected entities found in actual text (0.0 to 1.0)
    """
    if not expected_entities:
        return 1.0
    
    text = actual_text if case_sensitive else actual_text.lower()
    entities = [e if case_sensitive else e.lower() for e in expected_entities]
    
    found = sum(1 for e in entities if e in text)
    return found / len(entities)


def scene_type_accuracy(
    scene_type: str,
    compressed_result: Dict[str, Any],
    annotations: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Evaluate compression accuracy for a specific scene type.
    
    Args:
        scene_type: The scene type (combat, daily, psychological, political, general)
        compressed_result: Result dict from compressor (with final_text, layer3_categories, etc.)
        annotations: Optional custom annotations (uses defaults if not provided)
    
    Returns:
        Dict with accuracy metrics
    """
    if annotations is None:
        annotations = SCENE_ANNOTATIONS
    
    if scene_type not in annotations:
        return {"error": f"Unknown scene type: {scene_type}"}
    
    ann = annotations[scene_type]
    required_cats = ann["required_categories"]
    required_entities = ann.get("required_entities", [])
    
    # Get actual categories from layer 3 output
    actual_categories = compressed_result.get("layer3_categories", [])
    
    # Get compressed text
    compressed_text = compressed_result.get("final_text", "")
    
    # Calculate metrics
    cat_preservation = category_preservation_rate(required_cats, actual_categories)
    entity_retention = key_entity_retention(required_entities, compressed_text)
    
    # Check thresholds
    min_cat = ann.get("min_category_preservation_rate", 0.8)
    min_ent = ann.get("min_entity_retention_rate", 0.8)
    
    return {
        "scene_type": scene_type,
        "category_preservation_rate": cat_preservation,
        "entity_retention_rate": entity_retention,
        "required_categories": required_cats,
        "actual_categories": actual_categories,
        "required_entities": required_entities,
        "passed_category": cat_preservation >= min_cat,
        "passed_entity": entity_retention >= min_ent,
        "overall_passed": cat_preservation >= min_cat and entity_retention >= min_ent,
        "thresholds": {
            "min_category_preservation": min_cat,
            "min_entity_retention": min_ent,
        },
    }


def evaluate_test_case(
    test_case: Dict[str, Any],
    compressed_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate a single accuracy test case.
    
    Args:
        test_case: Test case dict with expected_categories, expected_entities
        compressed_result: Compression result dict
    
    Returns:
        Evaluation metrics
    """
    expected_cats = test_case.get("expected_categories", [])
    expected_ents = test_case.get("expected_entities", [])
    min_pres = test_case.get("min_preservation", 0.8)
    
    actual_cats = compressed_result.get("layer3_categories", [])
    compressed_text = compressed_result.get("final_text", "")
    
    cat_rate = category_preservation_rate(expected_cats, actual_cats)
    ent_rate = key_entity_retention(expected_ents, compressed_text)
    
    return {
        "test_name": test_case.get("name", "unknown"),
        "scene_type": test_case.get("scene_type", "general"),
        "category_preservation_rate": cat_rate,
        "entity_retention_rate": ent_rate,
        "expected_categories": expected_cats,
        "actual_categories": actual_cats,
        "expected_entities": expected_ents,
        "passed_category": cat_rate >= min_pres,
        "passed_entity": ent_rate >= min_pres,
        "overall_passed": cat_rate >= min_pres and ent_rate >= min_pres,
    }


__all__ = [
    "category_preservation_rate",
    "key_entity_retention",
    "scene_type_accuracy",
    "evaluate_test_case",
]