# Architecture Document: Reversible Compression Pipeline

## Overview

This document describes the architecture of the 4-Layer Context Compression system with reversible abstraction and context-aware scene detection, implemented as part of Story P9.

## Key Components

### 1. Reversible Entity Abstraction (Layer 3)

Instead of losing proper noun information through abstraction, the system preserves both the original entity and its abstracted concept in a dual format:

- **Original Format**: `抜刀・迅雷` (Original proper noun)
- **Abstract Format**: `雷撃系近接スキル` (Abstract concept)  
- **Dual Format**: `抜刀・迅雷 [雷撃系近接スキル]`

This ensures writer intent and detail preservation while maintaining abstraction benefits.

### 2. Context-Aware Scene Detection (Layer 4)

Enhances traditional keyword-based scene classification with:

- **Scene Flow History**: Tracks recent scene transitions to predict likely next scenes using Markov transition weights
- **Episode Goal Awareness**: Adjusts scene classification based on the current episode's narrative purpose
- **Multi-label Classification**: Returns scene type probabilities rather than a single hard classification

### 3. Quantitative Consistency Metrics

Provides objective measurement of compression quality:

- **Character Retention Score**: Percentage of active characters preserved
- **Foreshadowing Retention Score**: Percentage of plot foreshadowing elements preserved  
- **Proper Noun Retention Score**: Percentage of key proper nouns preserved
- **Semantic Density Score**: Information density per token
- **Overall Consistency Score**: Weighted average of all metrics

### 4. Integration Points

- **ContextBuilderAgent**: Now passes scene flow history to the compressor for context-aware scene detection
- **FourLayerCompressor**: Accepts scene_flow parameter and calculates quality metrics
- **Layer Abstractions**: All layers modified to support dual-format entity representation

## Data Flow

1. **Input**: Raw text + ProtectedContext + SceneFlowHistory (optional)
2. **Layer 1**: Keyphrase extraction
3. **Layer 2**: AGE 2-hop subgraph extraction with entity preservation
4. **Layer 3**: Conceptual abstraction with dual-format entity preservation
5. **Layer 4**: Context-aware trimming using scene flow and protected context
6. **Output**: Compressed text + Quality metrics

## Configuration

The system maintains backward compatibility while extending functionality:
- Existing compression pipelines continue to work unchanged
- New features are opt-in via additional parameters
- All new components are exposed via the public API

## Performance Characteristics

- Reversible abstraction adds minimal overhead (string formatting)
- Context-aware scene detection adds O(1) lookup for scene transition weights
- Metrics calculation is O(n) in text length but only runs on compression results
- Caching layers prevent redundant computation

## Extension Points

New taxonomy rules can be added via:
- Static overrides in CONCEPT_TAXONOMY
- Suffix pattern extensions in SUFFIX_TAXONOMY_RULES
- Custom taxonomy engine injection

## Files Modified

- `src/services/compression/models.py`: Added ReversibleEntityFact, CompressionQualityMetrics, SceneFlowHistory
- `src/services/compression/metrics.py`: New calculate_consistency_metrics function
- `src/services/compression/layer3_taxonomy.py`: Added format_dual_concept method
- `src/services/compression/layer3_abstraction.py`: Implemented dual-format for nodes and edges
- `src/services/compression/layer4_trimming.py`: Added SCENE_TRANSITION_MATRIX and detect_scene_context_aware
- `src/services/compression/compressor.py`: Integrated scene_flow and metrics calculation
- `src/services/compression/__init__.py`: Exported new public API
- `src/agents/context_builder_agent.py`: Integrated scene_flow history passing
- `tests/unit/`: Added comprehensive test suites for all new functionality
- `tests/benchmarks/`: Added benchmark_consistency_and_reduction.py
- `docs/architecture/COMPRESSION_REVERSIBLE_PIPELINE.md`: This document