"""
FastAPI Router for Writer Subtext Management (PLAN_Y1 Step 23, PLAN_Y2 Step 20, PLAN_Y3 Step 20).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import yaml

from src.narrative.subtext_engine.engine import SubtextEngine
from src.narrative.subtext_engine.models import DialogueBlock, RewriteRuleModel, SubtextContext
from src.narrative.subtext_engine.rules import RegexRule
from src.narrative.subtext_templates.loader import TemplateLoader
from src.narrative.subtext_templates.renderer import TemplateRenderer
from src.narrative.subtext_tokens.expander import TokenExpander
from src.narrative.subtext_tokens.formatter import DialogueFormatter
from src.pipeline.generation import GenerationPipeline

logger = logging.getLogger("backend.routers.subtext")

router = APIRouter(prefix="/subtext", tags=["subtext"])

# Singleton instances for API
engine_instance = SubtextEngine.create_default()
template_loader = TemplateLoader()
template_renderer = TemplateRenderer(loader=template_loader)
token_expander = TokenExpander()
formatter_instance = DialogueFormatter(expander=token_expander)
pipeline_instance = GenerationPipeline(
    engine=engine_instance,
    renderer=template_renderer,
    formatter=formatter_instance,
)


class ProcessRequest(BaseModel):
    text: str = Field(..., description="Dialogue text to process")
    mode: str = Field(default="hybrid", description="rule, template, token, hybrid, off")
    context: Optional[SubtextContext] = None
    seed: Optional[int] = None


class ProcessResponse(BaseModel):
    original: str
    processed: str
    mode: str


# ==============================================================================
# 1. Rules API (PLAN_Y1 Step 23)
# ==============================================================================

@router.get("/rules", response_model=List[RewriteRuleModel])
async def list_rules() -> List[RewriteRuleModel]:
    rules = engine_instance.registry.list_rules()
    return [r.to_model() for r in rules]


@router.post("/rules", response_model=RewriteRuleModel, status_code=status.HTTP_201_CREATED)
async def create_or_update_rule(rule_model: RewriteRuleModel) -> RewriteRuleModel:
    new_rule = RegexRule(
        rule_id=rule_model.id,
        pattern=rule_model.pattern,
        replacement=rule_model.replacement,
        name=rule_model.name,
        priority=rule_model.priority,
        final=rule_model.final,
        skip_if_matched=rule_model.skip_if_matched,
        enabled=rule_model.enabled,
        tags=rule_model.tags,
        description=rule_model.description,
    )
    engine_instance.registry.register(new_rule, overwrite=True)
    return new_rule.to_model()


# ==============================================================================
# 2. Templates API (PLAN_Y2 Step 20)
# ==============================================================================

class TemplateCreateRequest(BaseModel):
    id: str
    category: str = "general"
    content: str
    weight: int = 100
    tags: List[str] = Field(default_factory=list)


@router.get("/templates")
async def list_templates() -> Dict[str, Any]:
    templates = template_loader.load_all()
    return {
        "count": len(templates),
        "templates": [
            {
                "id": c.id,
                "category": c.metadata.category,
                "weight": c.metadata.weight,
                "tags": c.metadata.tags,
            }
            for c in templates.values()
        ],
    }


@router.post("/templates", status_code=status.HTTP_201_CREATED)
async def create_template(req: TemplateCreateRequest) -> Dict[str, Any]:
    cat_dir = template_loader.template_dir / req.category
    cat_dir.mkdir(parents=True, exist_ok=True)
    target_file = cat_dir / f"{req.id.split('.')[-1]}.j2"

    frontmatter = f"""---
id: {req.id}
category: {req.category}
tags: {req.tags}
weight: {req.weight}
---
{req.content}
"""
    target_file.write_text(frontmatter, encoding="utf-8")
    template_loader.load_all(force_reload=True)
    return {"status": "created", "id": req.id, "path": str(target_file)}


# ==============================================================================
# 3. Tokens API (PLAN_Y3 Step 20)
# ==============================================================================

class TokenPreviewRequest(BaseModel):
    text: str
    context: Optional[SubtextContext] = None
    seed: Optional[int] = 42


@router.get("/tokens")
async def get_token_dictionary() -> Dict[str, Any]:
    token_expander.load_dictionary()
    return token_expander._dict


@router.put("/tokens")
async def update_token_dictionary(content: Dict[str, Any]) -> Dict[str, Any]:
    token_expander._dict = content
    try:
        token_expander.dict_path.write_text(
            yaml.dump(content, allow_unicode=True), encoding="utf-8"
        )
    except Exception as e:
        logger.warning(f"Failed to persist token dictionary: {e}")
    return {"status": "updated"}


@router.post("/tokens/preview")
async def preview_token_expansion(req: TokenPreviewRequest) -> Dict[str, Any]:
    expanded = token_expander.expand(req.text, context=req.context, seed=req.seed)
    return {"raw": req.text, "expanded": expanded}


# ==============================================================================
# 4. Master Process Endpoint
# ==============================================================================

@router.post("/process", response_model=ProcessResponse)
async def process_dialogue(req: ProcessRequest) -> ProcessResponse:
    pipeline_instance.set_mode(req.mode)
    res = pipeline_instance.process_text(req.text, context=req.context, seed=req.seed)
    return ProcessResponse(original=req.text, processed=res, mode=req.mode)
