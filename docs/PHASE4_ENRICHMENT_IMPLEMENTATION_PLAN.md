# Phase 4: Multimodal Enrichment Integration - Detailed Implementation Plan (72 Steps)

---

## Category A: Foundation & Config (Steps 1-6)

### Step 1: Create Enrichment Config File
- **File**: `config/enrichment.yaml`
- **Changes**: Create new config with feature flag, weights, thresholds
- **Spec**:
```yaml
enrichment:
  enabled: false  # Feature flag for safe rollout
  trivia_insertion:
    enabled: true
    max_insertions_per_chapter: 5
    relevance_threshold: 0.7
    sources: ["world_bible", "historical_facts", "cultural_trivia"]
  citation_attachment:
    enabled: true
    style: "footnote"  # footnote, bracket, endnote
    max_citations_per_chapter: 10
    source_priority: ["world_bible", "canon_material", "historical_records"]
  sensory_expansion:
    enabled: true
    target_emotions: ["sadness", "anger", "fear", "joy", "surprise", "disgust"]
    expansion_ratio: 2.5  # multiplier for abstract→concrete
    show_dont_tell: true
  multimedia_scenarios:
    enabled: true
    formats: ["manga_script", "radio_drama", "anime_storyboard", "live_action_shots"]
    trigger_scenes: ["climax", "battle", "emotional_peak", "revelation", "romance"]
  token_budget:
    max_enrichment_tokens: 1500
    reserve_for_audit: 500
```
- **Test**: `python -c "import yaml; yaml.safe_load(open('config/enrichment.yaml'))"`

### Step 2: Create Prompt Templates Directory
- **File**: `prompts/enrichment/__init__.py`
- **Changes**: Create package init
- **Spec**: Empty file with `__all__ = []`

### Step 3: Create Trivia Insertion Prompt
- **File**: `prompts/enrichment/trivia_insertion.py`
- **Changes**: Create prompt template for trivia filtering & insertion
- **Spec**:
```python
TRIVIA_INSERTION_PROMPT = """
以下の本文に、世界観設定から関連性の高い雑学・トリビアを自然に組み込んでください。

【本文】
{original_text}

【候補トリビア一覧】
{trivia_candidates}

【制約】
- 最大 {max_insertions} 箇所まで挿入
- 文体・視点・時制を完全に維持
- 会話文中なら会話として、地の文ならナレーションとして自然に
- 「歴史的には…」等の説明調にならないよう注意
- 関連度 {relevance_threshold} 以上のみ採用

【出力形式】JSON:
{{
  "enriched_text": "組み込み済み本文",
  "insertions": [
    {{"position": 123, "original": "...", "enriched": "...", "trivia_source": "..."}}
  ]
}}
"""
```
- **Test**: `python -c "from prompts.enrichment.trivia_insertion import TRIVIA_INSERTION_PROMPT; print(len(TRIVIA_INSERTION_PROMPT))"`

### Step 4: Create Citation Attachment Prompt
- **File**: `prompts/enrichment/citation_attachment.py`
- **Changes**: Create prompt for source citation generation
- **Spec**: Similar structure, outputs footnote markers and bibliography

### Step 5: Create Sensory Expansion Prompt
- **File**: `prompts/enrichment/sensory_expansion.py`
- **Changes**: Create prompt for Show-Don't-Tell sensory rewriting
- **Spec**: Detects abstract emotions, expands to 5-sense concrete details

### Step 6: Create Multimedia Scenario Prompt
- **File**: `prompts/enrichment/multimedia_scenarios.py`
- **Changes**: Create prompt for derivative format generation
- **Spec**: Outputs structured JSON for manga/radio/anime formats

---

## Category B: EnrichmentAgent Core (Steps 7-12)

### Step 7: Create EnrichmentAgent Base Class
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: New file, `EnrichmentAgent(SkillAgent)` with `__init__`, dependencies
- **Spec**:
```python
class EnrichmentAgent(SkillAgent):
    def __init__(self, repo=None, llm=None, style_rag=None, rag_prefetch=None,
                 rag_service=None, prompt_manager=None, event_bus=None):
        super().__init__(repo=repo, llm=llm, style_rag=style_rag, 
                         rag_prefetch=rag_prefetch, event_bus=event_bus)
        self.rag_service = rag_service
        self.prompt_manager = prompt_manager
```
- **Test**: `python -c "from src.agents.enrichment_agent import EnrichmentAgent; print('OK')"`

### Step 8: Implement execute() Main Entry Point
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: Add `async def execute(self, ctx: AgentContext) -> AgentResult`
- **Spec**: 
  - Input: `ctx.artifacts["drafted_text"]`, `ctx.artifacts["writing_context"]`
  - Output: `enriched_text`, `enrichment_metadata`
  - Calls 4 sub-methods in sequence
  - Emits `enrichment.started` / `enrichment.completed` events
- **Test**: Unit test with mocked LLM returning enriched text

### Step 9: Implement _enrich_with_trivia() Method
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: Private method for trivia insertion
- **Spec**:
  - Query GraphRAG for scene-relevant entities/facts
  - Filter via LLM with `TRIVIA_INSERTION_PROMPT`
  - Insert at natural positions (paragraph boundaries)
  - Return `(enriched_text, insertion_metadata)`
- **Test**: Mock GraphRAG + LLM, verify insertions count ≤ config

### Step 10: Implement _attach_citations() Method
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: Private method for citation attachment
- **Spec**:
  - Map factual claims in text to World Bible sources
  - Generate footnote markers `[^1]` and bibliography
  - Maintain `citation_map: {marker: source_info}`
- **Test**: Verify footnote count, marker positions valid

### Step 11: Implement _expand_sensory_details() Method
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: Private method for sensory expansion
- **Spec**:
  - Detect abstract emotion phrases (regex + LLM)
  - For each, generate 5-sense concrete rewrite
  - Replace in text preserving flow
- **Test**: Input "彼は悲しかった" → output contains tear/temperature/sound/touch/smell

### Step 12: Implement _generate_multimedia_scenarios() Method
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: Private method for multimedia scenario generation
- **Spec**:
  - Identify trigger scenes (climax, battle, etc.) via keywords/structure
  - For each, render manga script / radio drama / storyboard JSON
  - Store in `enrichment_metadata["multimedia"]`
- **Test**: Verify all 4 formats present for trigger scene

---

## Category C: Trivia Insertion (Steps 13-18)

### Step 13: Add GraphRAG Query Helper for Trivia
- **File**: `src/services/rag_service.py`
- **Changes**: Add `async def query_trivia_candidates(self, session, scene_context, entities, limit=20)`
- **Spec**: Hybrid search for "trivia-worthy" facts (history, culture, item lore)
- **Test**: Returns list of `{fact, source, relevance_score}`

### Step 14: Implement Trivia Relevance Scoring
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: Add `_score_trivia_relevance(trivia, scene_context)` method
- **Spec**: Cosine similarity + keyword overlap + entity match
- **Test**: Known relevant trivia scores > 0.7, irrelevant < 0.3

### Step 15: Implement Natural Insertion Point Detection
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: Add `_find_insertion_points(text, max_points)` method
- **Spec**: Paragraph breaks, scene transitions, dialogue pauses
- **Test**: Returns list of character indices, count ≤ max_points

### Step 16: Implement Trivia-to-Text Rewriting
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: Add `_rewrite_trivia_for_context(trivia, surrounding_text, pov)` method
- **Spec**: LLM call with context window ±200 chars, preserves POV/tense
- **Test**: Output passes style consistency check

### Step 17: Add Trivia Insertion Metadata Tracking
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: Structure `enrichment_metadata["trivia"] = [{"source", "position", "original", "enriched", "relevance"}]`
- **Spec**: Full audit trail for each insertion
- **Test**: Metadata length matches insertion count

### Step 18: Add Trivia Token Budget Enforcement
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: Check `_estimate_tokens(enriched_text) - _estimate_tokens(original) ≤ budget`
- **Spec**: Truncate lowest-relevance insertions if over budget
- **Test**: Token delta within `config.enrichment.token_budget.max_enrichment_tokens`

---

## Category D: Citation Attachment (Steps 19-24)

### Step 19: Add World Bible Source Indexing
- **File**: `src/services/rag_service.py`
- **Changes**: Add `async def index_bible_sources(self, session, book_id)` 
- **Spec**: Creates searchable map: `claim_pattern → source_ref`
- **Test**: Query returns correct source for known facts

### Step 20: Implement Factual Claim Extraction
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: Add `_extract_factual_claims(text)` method
- **Spec**: LLM + regex to find verifiable statements (dates, names, rules, mechanics)
- **Test**: Extracts ≥80% of manually annotated claims in test corpus

### Step 21: Implement Source Matching
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: Add `_match_claims_to_sources(claims, bible_index)` method
- **Spec**: Semantic similarity + entity matching, threshold 0.75
- **Test**: Known claim-source pairs matched correctly

### Step 22: Implement Footnote Marker Insertion
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: Add `_insert_footnote_markers(text, claim_source_pairs)` method
- **Spec**: Insert `[^n]` after claim sentence, collect bibliography
- **Test**: Markers don't break sentence structure, bibliography complete

### Step 23: Implement Citation Style Formatting
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: Add `_format_citations(bibliography, style)` method
- **Spec**: Supports `footnote`/`bracket`/`endnote` per config
- **Test**: Each style renders correctly

### Step 24: Add Citation Metadata Tracking
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: Structure `enrichment_metadata["citations"] = [{"marker", "claim", "source", "style"}]`
- **Test**: Round-trip: text + metadata → original claims recoverable

---

## Category E: Sensory Expansion (Steps 25-30)

### Step 25: Create Emotion Detection Module
- **File**: `src/agents/enrichment/sensory.py` (new file)
- **Changes**: New module with `detect_abstract_emotions(text) → List[EmotionSpan]`
- **Spec**: `EmotionSpan = {start, end, emotion, intensity, abstract_phrase}`
- **Test**: Detects "悲しかった", "怒りが込み上げた", "恐怖で震えた" etc.

### Step 26: Implement Sensory Mapping Tables
- **File**: `src/agents/enrichment/sensory.py`
- **Changes**: Add `EMOTION_TO_SENSORY_MAP` dict with 6 emotions × 5 senses
- **Spec**: E.g., sadness → visual(tears), auditory(silence), tactile(cold), olfactory(rain), gustatory(salt)
- **Test**: Map covers all 6 target emotions × 5 senses

### Step 27: Implement Context-Aware Sensory Generation
- **File**: `src/agents/enrichment/sensory.py`
- **Changes**: Add `generate_sensory_details(emotion_span, scene_context, pov)` 
- **Spec**: LLM prompt with scene context, outputs 3-5 concrete sensory sentences
- **Test**: Output contains ≥3 distinct sensory modalities

### Step 28: Implement Text Replacement with Flow Preservation
- **File**: `src/agents/enrichment/sensory.py`
- **Changes**: Add `replace_with_sensory_expansion(text, emotion_spans, sensory_details)`
- **Spec**: Replaces abstract phrase with expanded version, maintains paragraph flow
- **Test**: Text length increases ~2.5x, no broken sentences

### Step 29: Integrate Sensory Module into EnrichmentAgent
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: Import and call sensory module in `_expand_sensory_details()`
- **Spec**: Uses shared LLM instance, respects token budget
- **Test**: End-to-end enrichment produces sensory-expanded text

### Step 30: Add Sensory Expansion Metadata
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: `enrichment_metadata["sensory"] = [{"original_phrase", "expanded_text", "emotion", "senses_covered"}]`
- **Test**: Metadata complete for each expansion

---

## Category F: Multimedia Scenarios (Steps 31-36)

### Step 31: Create Scene Type Classifier
- **File**: `src/agents/enrichment/scene_classifier.py` (new file)
- **Changes**: `classify_scene_type(text, writing_context) → List[SceneSegment]`
- **Spec**: `SceneSegment = {type, start, end, characters, tension_level}`
- **Types**: climax, battle, emotional_peak, revelation, romance, daily_life, transition

### Step 32: Create Manga Script Template
- **File**: `prompts/enrichment/templates/manga_script.j2`
- **Changes**: Jinja2 template for manga format
- **Spec**: Panels, dialogue, sound effects, camera directions

### Step 33: Create Radio Drama Template
- **File**: `prompts/enrichment/templates/radio_drama.j2`
- **Changes**: Jinja2 template for radio format
- **Spec**: Sound cues, voice direction, narration, dialogue

### Step 34: Create Anime Storyboard Template
- **File**: `prompts/enrichment/templates/anime_storyboard.j2`
- **Changes**: Jinja2 template for anime format
- **Spec**: Shot numbers, duration, camera, action, dialogue, BG

### Step 35: Create Live Action Shot List Template
- **File**: `prompts/enrichment/templates/live_action_shots.j2`
- **Changes**: Jinja2 template for live action format
- **Spec**: Scene slug, shot type, lens, movement, actors, VFX notes

### Step 36: Implement Multimedia Generator
- **File**: `src/agents/enrichment/multimedia.py` (new file)
- **Changes**: `generate_scenarios(scene_segments, text, templates) → Dict[format, str]`
- **Spec**: Renders all 4 templates for each trigger scene
- **Test**: All 4 formats valid JSON/structured output for sample climax scene

---

## Category G: Skill Wrappers (Steps 37-42)

### Step 37: Create v1 EnrichmentSkill Wrapper
- **File**: `src/agents/skills/v1/enrichment_skill.py`
- **Changes**: New file, mirrors `WritingSkill` pattern
- **Spec**:
```python
from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.enrichment_agent import EnrichmentAgent

class EnrichmentSkill(SkillAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = EnrichmentAgent(*args, **kwargs)
    
    async def execute(self, ctx: AgentContext) -> AgentResult:
        return await self._agent.execute(ctx)
```

### Step 38: Create v2 EnrichmentSkill Wrapper
- **File**: `src/agents/skills/v2/enrichment_skill.py`
- **Changes**: Identical to v1 but imports from v2 path (future A/B)
- **Test**: Both import without error

### Step 39: Register v1 Skill in Discovery
- **File**: `src/agents/skills/v1/__init__.py`
- **Changes**: Add `from .enrichment_skill import EnrichmentSkill` to `__all__`
- **Test**: `SkillAgent.discover_skills("src.agents.skills.v1")` includes EnrichmentSkill

### Step 40: Register v2 Skill in Discovery
- **File**: `src/agents/skills/v2/__init__.py`
- **Changes**: Same for v2
- **Test**: Discovery works for v2

### Step 41: Add EnrichmentAgent to Skills Package Exports
- **File**: `src/agents/__init__.py`
- **Changes**: Add `from .enrichment_agent import EnrichmentAgent` to exports
- **Test**: `from src.agents import EnrichmentAgent` works

### Step 42: Add EnrichmentAgent to Writing Package (Optional Alias)
- **File**: `src/agents/writing/__init__.py`
- **Changes**: Optional convenience import
- **Test**: Import works

---

## Category H: Manifest Integration (Steps 43-48)

### Step 43: Update manifest.yaml - Add EnrichmentSkill Entry
- **File**: `src/agents/skills/manifest.yaml`
- **Changes**: Insert new skill between WritingSkill and AuditSkill
- **Spec**:
```yaml
  - name: EnrichmentSkill
    class: src.agents.skills.v1.enrichment_skill.EnrichmentSkill
    depends_on: [WritingSkill]
    runs_after: [WritingSkill]
    runs_before: [AuditSkill]
    config:
      enabled: true
      trivia_enabled: true
      citation_enabled: true
      sensory_enabled: true
      multimedia_enabled: true
```

### Step 44: Update WritingSkill Dependencies
- **File**: `src/agents/skills/manifest.yaml`
- **Changes**: Modify WritingSkill `runs_before: [EnrichmentSkill]` (was AuditSkill)
- **Test**: Topological sort produces correct order

### Step 45: Update AuditSkill Dependencies
- **File**: `src/agents/skills/manifest.yaml`
- **Changes**: Modify AuditSkill `depends_on: [EnrichmentSkill]`, `runs_after: [EnrichmentSkill]`
- **Test**: No circular dependency

### Step 46: Update IllustrationSkill Dependencies
- **File**: `src/agents/skills/manifest.yaml`
- **Changes**: IllustrationSkill `depends_on: [AuditSkill]` unchanged (still after Audit)
- **Test**: Full order: Planning→Bible→ContextBuilder→Writing→Enrichment→Audit→Illustration

### Step 47: Add Manifest Validation Test
- **File**: `tests/unit/test_manifest_phase4.py` (new)
- **Changes**: Test that manifest loads, sorts correctly, no cycles
- **Test**: `pytest tests/unit/test_manifest_phase4.py -v`

### Step 48: Verify Orchestrator Build Order
- **File**: `tests/integration/test_enrichment_pipeline_order.py` (new)
- **Changes**: Integration test verifying orchestrator builds correct execution order
- **Test**: Run with both v1 and v2 skill packages

---

## Category I: Orchestrator Wiring (Steps 49-54)

### Step 49: Add EnrichmentAgent Node to Orchestrator Setup
- **File**: Wherever orchestrator nodes are configured (search for `nodes = {`)
- **Changes**: Add `AgentName.ENRICHMENT: enrichment_agent.run` to nodes dict
- **Spec**: Requires adding `ENRICHMENT = "enrichment"` to `AgentName` enum
- **Test**: Orchestrator instantiates without error

### Step 50: Add ENRICHMENT to AgentName Enum
- **File**: `src/agents/orchestrator.py`
- **Changes**: Add `ENRICHMENT = "enrichment"` to `AgentName` enum (after WRITING)
- **Test**: Enum accessible, no duplicate values

### Step 51: Update WritingAgent Next Agent
- **File**: `src/agents/writing/agent.py`
- **Changes**: In successful execute(), change `next_agent=AgentName.ENRICHMENT` (was ILLUSTRATION)
- **Test**: WritingAgent returns ENRICHMENT as next

### Step 52: Update EnrichmentAgent Next Agent
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: In successful execute(), return `next_agent=AgentName.AUDIT`
- **Test**: EnrichmentAgent returns AUDIT as next

### Step 53: Update AuditAgent Input Handling
- **File**: `src/agents/audit_agent.py`
- **Changes**: In execute(), check `ctx.artifacts.get("enriched_text")` first, fallback to `drafted_text`
- **Spec**: 
```python
enriched_text = ctx.artifacts.get("enriched_text")
drafted_text = enriched_text or ctx.artifacts.get("drafted_text")
```
- **Test**: AuditAgent works with both enriched and non-enriched input

### Step 54: Add Feature Flag Check in Orchestrator
- **File**: `src/agents/orchestrator.py` or config loader
- **Changes**: If `ENRICHMENT_ENABLED=false`, skip EnrichmentAgent node (wire Writing→Audit directly)
- **Test**: With flag off, pipeline skips enrichment; with on, includes it

---

## Category J: EventBus Integration (Steps 55-60)

### Step 55: Add Enrichment Event Constants
- **File**: `src/agents/event_bus.py`
- **Changes**: Add `ENRICHMENT_STARTED`, `ENRICHMENT_COMPLETED`, `ENRICHMENT_STEP_COMPLETED`
- **Test**: Constants accessible

### Step 56: Emit enrichment.started Event
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: In execute(), emit `enrichment.started` with book_id, ep_num
- **Test**: Event appears in EventBus subscribers

### Step 57: Emit enrichment.step_completed Events
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: After each of 4 sub-tasks, emit `enrichment.step_completed` with step name, stats
- **Test**: 4 step events per enrichment run

### Step 58: Emit enrichment.completed Event
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: On success, emit with `enrichment_metadata` summary
- **Test**: Final event contains all 4 metadata categories

### Step 59: Add Blind Review Compatibility
- **File**: `src/agents/enrichment_agent.py`
- **Changes**: In execute(), check `ctx.artifacts.get("blind_review_mode")` 
- **Spec**: If true, skip trivia/citation that might leak other agents' outputs
- **Test**: With blind_review_mode=true, enrichment_metadata shows skipped steps

### Step 60: Add EventBus Integration Test
- **File**: `tests/integration/test_enrichment_events.py` (new)
- **Changes**: Verify all 6 event types emitted in correct order
- **Test**: `pytest tests/integration/test_enrichment_events.py -v`

---

## Category K: Testing & Verification (Steps 61-66)

### Step 61: Unit Test - Trivia Insertion
- **File**: `tests/unit/test_enrichment_trivia.py` (new)
- **Changes**: Mock GraphRAG + LLM, verify insertions, metadata, token budget
- **Test**: `pytest tests/unit/test_enrichment_trivia.py -v`

### Step 62: Unit Test - Citation Attachment
- **File**: `tests/unit/test_enrichment_citations.py` (new)
- **Changes**: Mock bible index, verify footnote insertion, bibliography format
- **Test**: `pytest tests/unit/test_enrichment_citations.py -v`

### Step 63: Unit Test - Sensory Expansion
- **File**: `tests/unit/test_enrichment_sensory.py` (new)
- **Changes**: Test emotion detection, sensory generation, replacement
- **Test**: `pytest tests/unit/test_enrichment_sensory.py -v`

### Step 64: Unit Test - Multimedia Generation
- **File**: `tests/unit/test_enrichment_multimedia.py` (new)
- **Changes**: Test scene classification, all 4 template renders
- **Test**: `pytest tests/unit/test_enrichment_multimedia.py -v`

### Step 65: Integration Test - Full Enrichment Pipeline
- **File**: `tests/integration/test_enrichment_e2e.py` (new)
- **Changes**: WritingAgent → EnrichmentAgent → AuditAgent with real(ish) components
- **Test**: Enriched text passes audit, metadata complete

### Step 66: Regression Test - Existing Pipeline Unchanged
- **File**: `tests/integration/test_regression_phase4.py` (new)
- **Changes**: Run existing full_pipeline test with ENRICHMENT_ENABLED=false
- **Test**: All Phase 1-3 tests still pass

---

## Category L: Observability & Ops (Steps 67-72)

### Step 67: Add Prometheus Metrics
- **File**: `src/backend/observability/metrics.py`
- **Changes**: Add counters/histograms:
  - `enrichment_duration_seconds`
  - `enrichment_trivia_insertions_total`
  - `enrichment_citations_added_total`
  - `enrichment_sensory_expansions_total`
  - `enrichment_multimedia_scenarios_total`
  - `enrichment_token_usage`
  - `enrichment_errors_total`
- **Test**: Metrics exposed at `/metrics`

### Step 68: Add Feature Flag to Settings
- **File**: `src/backend/config.py` or `config/system_plugins.yaml`
- **Changes**: `ENRICHMENT_ENABLED = os.getenv("ENRICHMENT_ENABLED", "false").lower() == "true"`
- **Test**: Toggle via env var, verify pipeline behavior

### Step 69: Add Admin API Endpoints
- **File**: `src/backend/api/admin.py` (or similar)
- **Changes**: 
  - `GET /admin/enrichment/status` - config, feature flag, stats
  - `POST /admin/enrichment/test` - run enrichment on sample text
  - `GET /admin/enrichment/metrics` - Prometheus metrics snapshot
- **Test**: `curl` endpoints return expected JSON

### Step 70: Add Health Check
- **File**: `src/backend/health.py` or similar
- **Changes**: EnrichmentAgent health check (LLM connectivity, GraphRAG, prompt templates)
- **Test**: `/health` includes enrichment status

### Step 71: Update Documentation
- **File**: `docs/ENRICHMENT_AGENT.md` (new)
- **Changes**: Architecture, config, API, examples, troubleshooting
- **Test**: Doc renders correctly

### Step 72: Final E2E Validation & Sign-off
- **File**: N/A (execution)
- **Changes**: Run full pipeline with ENRICHMENT_ENABLED=true on sample book
- **Verification Checklist**:
  - [ ] WritingAgent → EnrichmentAgent → AuditAgent → IllustrationAgent completes
  - [ ] enriched_text longer than drafted_text (trivia + sensory)
  - [ ] Footnotes present in enriched_text
  - [ ] Multimedia scenarios generated for climax scene
  - [ ] AuditAgent passes on enriched text
  - [ ] Prometheus metrics incremented
  - [ ] Events emitted at each stage
  - [ ] Feature flag OFF reverts to original pipeline
  - [ ] No regression in Phase 1-3 tests
- **Sign-off**: All checks pass → Phase 4 complete

---

## Dependency Graph Summary

```
A1-A6 (Foundation) 
    ↓
B7-B12 (Core Agent) ← depends on A1-A6
    ↓
C13-C18 (Trivia) ← depends on B7-B9, A1, A3
    ↓
D19-D24 (Citations) ← depends on B7-B10, A1, A4
    ↓
E25-E30 (Sensory) ← depends on B7-B11, A1, A5, new sensory module
    ↓
F31-F36 (Multimedia) ← depends on B7-B12, A1, A6, new templates
    ↓
G37-G42 (Wrappers) ← depends on B7, F36
    ↓
H43-H48 (Manifest) ← depends on G37-G40
    ↓
I49-I54 (Orchestrator) ← depends on H43-H46, B8
    ↓
J55-J60 (Events) ← depends on I49-I52, B8
    ↓
K61-K66 (Tests) ← depends on all above
    ↓
L67-L72 (Observability) ← depends on K65-K66
```

**Total: 72 atomic, testable, ordered steps**