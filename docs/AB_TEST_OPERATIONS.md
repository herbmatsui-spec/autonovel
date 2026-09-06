# A/B Test Operations Manual

## Overview

This document describes the operational procedures for the AutoNovel audit weight A/B testing framework.

**System Components:**
- `src/config/weight_variants.py` - Weight variant registry (13+ built-in variants)
- `src/services/experiment_allocator.py` - Deterministic traffic allocation (MD5 hash)
- `src/services/analyze_ab_test.py` - Weekly statistical analysis script
- `src/agents/specialists/adapter.py` - Pipeline integration with variant selection
- `src/services/audit_aggregator.py` - Metrics emission for analysis

## Variant Naming Convention

```
{genre}_{version}_{description}
```

Examples:
- `literary_v1` - Production baseline for literary genre
- `literary_v2_consistency_up` - Experiment: increased consistency weight
- `entertainment_v2_hook_up` - Experiment: increased reader_hook weight
- `default_v1` - Fallback for unknown genres

## Traffic Allocation

### Default Configuration
- **Experiment traffic**: 1% (`traffic_fraction=0.01`)
- **Allocation method**: Deterministic MD5 hash of `book_id:genre`
- **Consistency**: Same book always gets same variant

### Adjusting Traffic Fraction

```python
# In adapter initialization
node = AuditAggregatorNode(traffic_fraction=0.05)  # 5% experiment traffic

# Or via environment
export AUDIT_TRAFFIC_FRACTION=0.05
```

### Phased Rollout Schedule

| Week | Traffic | Purpose |
|------|---------|---------|
| 1-2 | 1% | Smoke test, monitor error rates |
| 3-4 | 5% | Early signal detection |
| 5-8 | 20% | Statistical power for weekly analysis |
| 9+ | 50% | Near-full experiment, prepare promotion |

## Adding New Variants

### 1. Define Variant in `weight_variants.py`

```python
# In WEIGHT_VARIANTS dict or via register_variant()
register_variant("romance_v2_emotion_up", {
    "consistency": 0.10,
    "creativity": 0.10,
    "reader_hook": 0.10,
    "emotion_curve": 0.35,  # Increased from 0.25
    "style": 0.10,
    "factual": 0.10,
    "structure": 0.10,
    "multimodal": 0.05,
}, overwrite=False)
```

### 2. Validation Requirements

All variants must:
- Include all 8 specialists (no missing keys)
- Sum to exactly 1.0 (±1e-6 tolerance)
- Use valid specialist names

### 3. Deploy & Monitor

```bash
# Deploy code
git push origin main

# Monitor for 24h - check:
# - Error rates in audit.specialist.completed events
# - Fallback rates (<20% threshold)
# - Score distributions not shifted dramatically
```

## Weekly Analysis

### Running Analysis

```bash
# Production (queries real DB)
python scripts/analyze_ab_test.py --since-days 7 --output-json results/week_$(date +%Y%m%d).json

# Development (mock data)
python scripts/analyze_ab_test.py --mock --since-days 7
```

### Analysis Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--since-days` | 7 | Lookback window |
| `--min-samples` | 30 | Minimum samples per variant |
| `--p-threshold` | 0.05 | Statistical significance (Welch + Mann-Whitney) |
| `--effect-threshold` | 0.2 | Cliff's delta minimum |
| `--min-improvement` | 1.0 | Minimum 1% relative improvement |

### Interpreting Results

```
RECOMMENDATION: PROMOTE
Reason: Statistically significant improvement (+3.2%), p=0.0034, Cliff's delta=0.312
Action: Merge variant to production (update v1 baseline)

RECOMMENDATION: REJECT
Reason: Statistically significant degradation (-2.1%), p=0.012
Action: Disable variant, investigate cause

RECOMMENDATION: INCONCLUSIVE
Reason: Significant but effect size too small (Cliff's delta=0.098 < 0.2)
Action: Continue experiment, increase traffic or duration

RECOMMENDATION: NO_DECISION
Reason: Not statistically significant (p=0.34) or insufficient improvement
Action: Continue experiment
```

### Statistical Rigor

- **Primary test**: Welch's t-test (unequal variance)
- **Confirmatory**: Mann-Whitney U test (non-parametric)
- **Effect size**: Cliff's delta (distribution-free, robust)
- **Multiple comparison**: No formal correction (max ~5 concurrent experiments)

## Promotion Workflow

### Automated (Future)
1. Weekly script outputs `PROMOTE` recommendations
2. CI/CD picks up, creates PR updating `*_v1` baselines
3. Team reviews, merges
4. Deploy

### Manual (Current)
1. Review weekly JSON report
2. For each `PROMOTE`:
   ```bash
   # Update baseline in weight_variants.py
   # e.g., literary_v1 <- literary_v2_consistency_up weights
   register_variant("literary_v1", NEW_WEIGHTS, overwrite=True)
   ```
3. Create PR with changelog
4. Code review + merge
5. Deploy

### Rollback Procedure

If promoted variant causes issues:
1. Revert `weight_variants.py` to previous `*_v1` weights
2. Deploy hotfix
3. Document in `EXPERIMENT_HISTORY.md`

## Monitoring & Alerts

### Key Metrics (Grafana/Prometheus)

| Metric | Alert Threshold | Action |
|--------|----------------|--------|
| `audit_fallback_rate` | >20% | Investigate LLM availability |
| `audit_score_variance` | >25 (within genre) | Check cross-specialist consistency |
| `audit_llm_cost_per_chapter` | >$0.10 | Optimize prompts/temperature |
| `experiment_traffic_fraction` | != expected | Config drift detection |

### Weekly Checklist

- [ ] Run `analyze_ab_test.py` and review output
- [ ] Check fallback rates per specialist (<20%)
- [ ] Verify score distributions per variant (no drift)
- [ ] Update `EXPERIMENT_HISTORY.md` with results
- [ ] Create promotion PRs if applicable
- [ ] Adjust traffic fraction per schedule

## Experiment History Template

Record in `docs/EXPERIMENT_HISTORY.md`:

```markdown
## 2026-09-08: literary_v2_consistency_up

**Variant**: literary_v2_consistency_up (consistency: 0.20→0.25)
**Traffic**: 5% (weeks 3-4), 20% (weeks 5-8)
**Duration**: 6 weeks
**Samples**: control=1,247, treatment=312
**Results**:
- Overall: +2.8% (p=0.008, Cliff's delta=0.28)
- Consistency specialist: +5.1% (p=0.001)
- Regeneration rate: -0.3% (ns)
**Decision**: PROMOTED
**Promoted to**: literary_v1 (2026-09-15)
**Notes**: Consistent improvement across chapters, no adverse effects on other specialists.
```

## Troubleshooting

### High Fallback Rate
```
Symptom: >20% audits degraded
Causes: LLM API errors, timeout, malformed JSON
Fix: Check LLM provider status, increase timeout, validate prompts
```

### Score Distribution Shift
```
Symptom: All variants shift down/up together
Causes: Prompt change, model update, data drift
Fix: Compare against pre-change baseline, revert prompts if needed
```

### No Statistical Significance
```
Symptom: Weeks of NO_DECISION
Causes: Effect too small, high variance, insufficient traffic
Fix: Increase traffic_fraction, extend duration, or accept null result
```

### Variant Collision
```
Symptom: Multiple experiments assigning different variants to same book
Causes: Different seeds but overlapping traffic
Fix: Use MultiExperimentAllocator with coordinated seeds
```

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUDIT_TRAFFIC_FRACTION` | 0.01 | Experiment traffic % |
| `AUDIT_LLM_SAMPLES` | 1 | Multi-sampling count |
| `AUDIT_LLM_MAX_STDEV` | 15.0 | Max score stdev across samples |
| `PROJECT_ROOT` | . | Path for config loading |

### Key Files

| File | Purpose |
|------|---------|
| `config/weight_variants.py` | Variant definitions |
| `config/llm_bias_correction.yaml` | Bias correction factors |
| `config/audit_weights.yaml` | Legacy weights (deprecated) |
| `scripts/analyze_ab_test.py` | Weekly analysis |
| `docs/EXPERIMENT_HISTORY.md` | Historical record |

## Contacts

- **On-call**: Platform team (PagerDuty: autonovel-audit)
- **ML/AI queries**: AI Engineering team
- **Database**: Data Platform team

---

*Last updated: 2026-09-06*
*Version: 1.0*