"""
Unit tests for template structure and loader (PLAN_Y2 Step 1, 2, 3).
"""

from pathlib import Path
import pytest
from src.narrative.subtext_templates.loader import TemplateLoader
from src.narrative.subtext_templates.models import TemplateMetadata


def test_template_structure_and_categories():
    template_dir = Path("templates/subtext")
    assert template_dir.exists()

    expected_categories = ["betrayal", "grief", "power_play", "romance", "comedy", "action", "fallback"]
    for cat in expected_categories:
        cat_dir = template_dir / cat
        assert cat_dir.exists(), f"Category directory {cat} missing"
        j2_files = list(cat_dir.glob("*.j2"))
        assert len(j2_files) > 0, f"No templates found in {cat}"


def test_frontmatter_schema_validation():
    loader = TemplateLoader()
    cand = loader.parse_template_file(Path("templates/subtext/betrayal/cold_acceptance.j2"))
    assert cand is not None
    meta = cand.metadata
    assert meta.id == "betrayal.cold_acceptance"
    assert "betrayal" in meta.tags
    assert meta.weight == 100
    assert "emotion" in meta.context


def test_loader_cache_and_index_generation(tmp_path):
    loader = TemplateLoader(Path("templates/subtext"))
    templates = loader.load_all()
    assert len(templates) >= 23

    index_file = Path("templates/subtext/index.yaml")
    assert index_file.exists()

    # Fast cache retrieval
    cached = loader.load_all()
    assert cached is templates
