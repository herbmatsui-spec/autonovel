# Phase 4: Multimodal Enrichment Integration - Meta Plan

## 1. Phase 4 Objective
Implement the **EnrichmentAgent** as a new skill-driven agent that sits between WritingAgent and AuditAgent in the pipeline, enriching generated text with:
1. Contextual trivia insertion (world-building facts)
2. Citation/reference attachment (World Bible sources)
3. Sensory detail expansion (Show, Don't Tell automation)
4. Multimedia scenario generation (manga scripts, radio drama, anime storyboards)

## 2. Preconditions (Must be completed in Phase 1-3)
- ✅ Skill-driven architecture (`SkillAgent` base class, Orchestrator, manifest.yaml)
- ✅ EventBus with async/sync publish
- ✅ GraphRAGService for hybrid context retrieval
- ✅ WritingAgent produces `drafted_text` artifact
- ✅ AuditAgent consumes `drafted_text` artifact
- ✅ BibleAgent maintains World Bible in GraphRAG

## 3. Architectural Changes

### 3.1 New Components
| Component | Path | Purpose |
|-----------|------|---------|
| `EnrichmentAgent` | `src/agents/enrichment_agent.py` | Core enrichment logic (SkillAgent subclass) |
| `EnrichmentSkill` (v1) | `src/agents/skills/v1/enrichment_skill.py` | Skill wrapper for v1 |
| `EnrichmentSkill` (v2) | `src/agents/skills/v2/enrichment_skill.py` | Skill wrapper for v2 (future A/B) |
| Config | `config/enrichment.yaml` | Weights, thresholds, feature flags |
| Prompts | `prompts/enrichment/` | 4 prompt templates for each enrichment type |

### 3.2 Pipeline Modification
```
Current:  WritingAgent → AuditAgent → IllustrationAgent
New:      WritingAgent → EnrichmentAgent → AuditAgent → IllustrationAgent
```

### 3.3 Manifest Update
Add `EnrichmentSkill` between `WritingSkill` and `AuditSkill` in `manifest.yaml`

### 3.4 Artifact Flow
| Stage | Input Artifacts | Output Artifacts |
|-------|----------------|------------------|
| WritingAgent | prompt, context | `drafted_text`, `word_count` |
| **EnrichmentAgent** | `drafted_text`, `writing_context` | `enriched_text`, `enrichment_metadata` (trivia_inserted, citations_added, sensory_expanded, multimedia_scenarios) |
| AuditAgent | `enriched_text` (or `drafted_text` fallback) | audit_report |

## 4. 72-Step Decomposition Strategy

### Classification Rules
Each step MUST be:
- **Atomic**: Single file change or single logical operation
- **Testable**: Has explicit verification criteria
- **Independent**: Can be executed by lightweight LLM without context loss
- **Ordered**: Explicit dependency on prior steps

### Categories (12 categories × 6 steps = 72 steps)
| Category | Steps | Focus |
|----------|-------|-------|
| A: Foundation & Config | 1-6 | Config, prompts, data structures |
| B: EnrichmentAgent Core | 7-12 | Base class, execute(), artifact I/O |
| C: Trivia Insertion | 13-18 | GraphRAG query, LLM filtering, text insertion |
| D: Citation Attachment | 19-24 | Source mapping, footnote generation, style consistency |
| E: Sensory Expansion | 25-30 | Emotion detection, sensory rewriting, Show-Don't-Tell |
| F: Multimedia Scenarios | 31-36 | Scene detection, template rendering, output formats |
| G: Skill Wrappers | 37-42 | v1/v2 skill classes, registration |
| H: Manifest Integration | 43-48 | manifest.yaml update, dependency ordering |
| I: Orchestrator Wiring | 49-54 | Node registration, artifact passing |
| J: EventBus Integration | 55-60 | Event emission, blind review compatibility |
| K: Testing & Verification | 61-66 | Unit tests, integration tests, E2E flow |
| L: Observability & Ops | 67-72 | Metrics, feature flags, admin API, docs |

### Check Criteria for Each Step
1. **File exists** at specified path after step
2. **Syntax valid** (Python imports, YAML parses)
3. **Interface matches** SkillAgent/AgentResult contracts
4. **Tests pass** (new + existing regression)
5. **No circular deps** in manifest
6. **Backward compatible** (feature flag default OFF)

## 5. Risk Mitigation
- **Feature flag `ENRICHMENT_ENABLED`** default `false` for safe rollout
- **Fallback**: If EnrichmentAgent fails, pass original `drafted_text` to AuditAgent
- **Token budget**: Enrichment respects `context_compression.yaml` limits
- **A/B ready**: v1/v2 structure from Day 1