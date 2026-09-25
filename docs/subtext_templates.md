# サブテキスト・テンプレートライブラリ (Subtext Templates) 運用ガイド

## 1. 概要
`subtext_templates` は、作家が編集・拡張可能な Jinja2 テンプレート群を用いて「行間・サブテキストの型」を資産化し、文脈（感情×力関係×関係性×トーン）に基づき決定論的かつ高精度に選択・レンダリングするシステムです。

## 2. テンプレート構造とフロントマター規約
すべてのテンプレートは `templates/subtext/<category>/<template_id>.j2` に配置され、YAMLフロントマターとJinja2テンプレート本文で構成されます。

```jinja2
---
id: betrayal.cold_acceptance
category: betrayal
tags: [betrayal, cold, acceptance, irony]
context:
  emotion: [betrayal, hurt]
  power_dynamic: [inferior, equal]
  relationship: [former_ally, lover, subordinate]
  intensity: [high, medium]
variables:
  - acceptance_phrase: "受け入れの言葉"
  - dry_action: "乾いた動作"
weight: 100
final: false
---
「……{{ acceptance_phrase | default('ええ、お望みの通りに') }}」
——{{ dry_action | default('乾いた笑みをこぼしながら、震える指先をマントの奥へ隠した') }}。
```

## 3. 実装済みカテゴリ（全23種＋フォールバック）
1. **betrayal（裏切り）**: `cold_acceptance`, `masked_rage`, `quiet_threat`, `false_forgiveness`, `calculated_retreat`
2. **grief（悲哀・喪失）**: `denial_through_action`, `suppressed_tears`, `quiet_breakdown`, `stoic_endurance`
3. **power_play（権力闘争・駆け引き）**: `ironic_politeness`, `silence_as_weapon`, `feigned_ignorance`, `conditional_compliance`
4. **romance（親愛・秘めた情愛）**: `masked_longing`, `deflected_confession`, `teasing_as_shield`, `silent_understanding`
5. **comedy（道化・話題逸らし）**: `self_deprecating_deflection`, `absurdist_redirect`, `deadpan_evade`
6. **action（沈黙・無言演出）**: `meaningful_glance`, `symbolic_gesture`, `environmental_interaction`
7. **fallback（フォールバック）**: `generic_subtext`, `minimal_beat`

## 4. 品質ゲート検証・ヒートマップ
- テンプレート品質チェック: `python scripts/validate_templates.py`
- テンプレート使用ヒートマップ生成: `python scripts/generate_template_heatmap.py`
- 黄金サンプル回帰テスト（50件）: `pytest tests/narrative/subtext_templates/test_golden_templates.py`
