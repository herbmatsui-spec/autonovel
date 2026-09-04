# スキル駆動型エージェントアーキテクチャ & BookScore メトリクス 実装ガイド

## 概要

フェーズ1（短期・高影響度）として実装された2つの主要機能：

1. **スキル駆動型エージェントアーキテクチャ** - ゼロコードで新しい専門エージェントを追加可能
2. **BookScore 統一100点尺度メトリクス** - 客観的な品質評価基盤

---

## 1. スキル駆動型エージェントアーキテクチャ

### アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Skill Registry│  │Manifest Parser│ │Execution Order│      │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ PlanningSkill │   │ BibleSkill    │   │ContextBuilder │
│ (PlanningAgent)│  │ (BibleAgent)  │   │Skill          │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ WritingSkill  │   │ AuditSkill    │   │Illustration   │
│ (WritingAgent)│  │ (AuditAgent)  │   │Skill          │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 主要コンポーネント

#### SkillAgent 基底クラス (`src/agents/skill_base.py`)
```python
class SkillAgent(BaseAgent):
    version: str = "1.0"
    
    @abstractmethod
    async def execute(self, ctx: AgentContext) -> AgentResult:
        pass
    
    @classmethod
    def discover_skills(cls, package_path: str) -> List[Type["SkillAgent"]]:
        """パッケージから自動検出"""
    
    @staticmethod
    def load_manifest(manifest_path: str) -> List[dict]:
        """YAMLマニフェスト読み込み"""
```

#### スキルマニフェスト (`src/agents/skills/manifest.yaml`)
```yaml
skills:
  - name: PlanningSkill
    class: src.agents.skills.planning_skill.PlanningSkill
    depends_on: []
    runs_after: []
    runs_before: [BibleSkill]
    config:
      enabled: true
```

### 新しいスキルの追加手順

1. **スキルクラス作成** (`src/agents/skills/your_skill.py`)
```python
from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult

class YourSkill(SkillAgent):
    async def execute(self, ctx: AgentContext) -> AgentResult:
        # 実装
        return AgentResult(next_agent=None, artifacts={"result": "ok"})
```

2. **マニフェストに登録** (`src/agents/skills/manifest.yaml`)
```yaml
  - name: YourSkill
    class: src.agents.skills.your_skill.YourSkill
    depends_on: [ContextBuilderSkill]
    runs_after: [ContextBuilderSkill]
    runs_before: [AuditSkill]
    config:
      enabled: true
```

3. **自動登録確認**
```python
from src.agents.skill_base import SkillAgent
skills = SkillAgent.discover_skills('src.agents.skills')
# YourSkill が含まれる
```

### ホットスワップ・バージョニング
```python
from src.agents.orchestrator import Orchestrator
orch = Orchestrator(nodes={})
orch.replace_skill('planning', NewPlanningSkill)  # 実行中に置換可能

# バージョン確認
print(PlanningSkill.version)  # "1.0"
```

### メトリクス取得
```python
from src.agents.skill_base import SkillAgent
metrics = SkillAgent.get_metrics()
# {
#   "PlanningSkill": {"success_count": 10, "error_count": 0, "avg_duration_sec": 0.123}
# }
```

---

## 2. BookScore 統一100点尺度メトリクス

### スコア構成

| 次元 | 重み | 説明 |
|------|------|------|
| 構造 | 25% | プロット論理、章構成バランス、テンポ |
| 一貫性 | 25% | キャラ口調、世界観ルール、タイムライン |
| 事実性 | 20% | GraphRAG整合性、歴史文化的正確性、用語 |
| 視覚×テキスト | 15% | 挿絵プロンプトと本文の情報量・焦点・感情 |
| 読者体験 | 15% | 冒頭フック、末尾クリフハンガー、感情曲線 |

### 設定 (`config/book_score_weights.yaml`)
```yaml
default:
  structure: 25
  coherency: 25
  factual_grounding: 20
  visual_textual_synergy: 15
  reader_experience: 15

genre_overrides:
  literary:
    structure: 30
    reader_experience: 25

phase_overrides:
  planning:
    structure: 35
    reader_experience: 40
```

### 使用方法

#### スコア計算
```python
from src.services.book_score_service import BookScoreCalculator
from src.backend.database.repositories.book_score import BookScoreRepository
from sqlalchemy.ext.asyncio import AsyncSession

repo = BookScoreRepository(session)
calculator = BookScoreCalculator(repository=repo)

score = await calculator.calculate(
    book_id=1,
    chapter_number=3,
    genre="literary",
    phase="writing"
)

print(score.overall_score)      # 85.5
print(score.structure_score)    # 90.0
print(score.reader_experience_score)  # 88.0
```

#### 自動保存・取得
```python
# 計算時に自動保存（repository 指定時）
await calculator.save_score(book_id=1, chapter_number=3, score)

# 最新スコア取得
latest = await calculator.get_latest_score(1, 3)
```

#### 再生成トリガー連携 (`WritingService`)
```python
from src.backend.writing_service import WritingService

service = WritingService(
    writer=writer,
    book_score_calculator=calculator,
    score_threshold=70.0,  # これ未満で再生成トリガー
)

result = await service.calculate_book_score(book_id=1, chapter_number=1)
if result["regeneration_triggered"]:
    print("低スコア次元:", result["low_dimensions"])
    # ["structure", "visual_textual_synergy"]
```

### API エンドポイント

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/novel/books/{book_id}/chapters/{chapter_number}/score` | GET | 章の BookScore 取得 |
| `/api/system/admin/book_score/recalc` | POST | 全章スコア再計算（管理者） |

### Prometheus メトリクス
```prometheus
# 総合スコア分布
book_score_overall{genre="literary",phase="writing"}

# 次元別スコア
book_score_dimensions{dimension="structure"}
book_score_dimensions{dimension="coherency"}

# 再生成トリガー回数
book_score_regeneration_triggered_total{dimension="structure"}
```

---

## 3. サンプルスキル実装

### CulturalComplianceChecker (`src/agents/skills/cultural_compliance.py`)
地域別の文化的適切性（差別用語等）をチェック

### HistoricalAccuracyChecker (`src/agents/skills/historical_accuracy.py`)
時代考証・アナクロニズム検出

### MarketingCopySkill (`src/agents/skills/marketing_copy.py`)
キャッチコピー・あらすじ・タグライン・ブラーブ自動生成

---

## 4. 開発・運用コマンド

### 依存インストール
```bash
pip install -e ".[dev]"
```

### マイグレーション実行
```bash
cd src/backend && alembic upgrade head
```

### テスト実行
```bash
# ユニットテスト
pytest tests/unit -v

# 統合テスト
pytest tests/integration -v

# カバレッジ付き
pytest --cov=src --cov-report=html
```

### 開発環境セットアップ
```bash
./scripts/setup_dev.sh  # 作成予定
```

---

## 5. スキルバージョン管理・A/Bテスト

### バージョン管理 (`src/agents/skills/v1/`, `v2/`)

スキルはバージョン別にディレクトリで管理されます：

```
src/agents/skills/
├── v1/                 # 現在の安定版
│   ├── planning_skill.py
│   ├── bible_skill.py
│   └── ...
├── v2/                 # 実験版・次期版
│   └── (開発中)
└── manifest.yaml       # 共通マニフェスト（クラスパスでバージョン指定）
```

### バージョン切替

#### Python API
```python
from src.agents.orchestrator import Orchestrator

orch = Orchestrator(nodes={})
orch.register_discovered_skills('src.agents.skills.v1')

# バージョン確認
print(orch.get_active_version())  # "v1"

# バージョン切替（ホットスワップ）
orch.set_skill_version('v2')
print(orch.get_active_version())  # "v2"
```

#### API エンドポイント
```bash
# 現在のバージョン取得
curl -X GET /api/system/admin/skills/version

# バージョン切替
curl -X POST /api/system/admin/skills/switch_version \
  -H "Content-Type: application/json" \
  -d '{"version": "v2"}'
```

### A/B テスト

同一入力で複数バージョンを並列実行し、メトリクス比較：

```python
from src.agents.orchestrator import Orchestrator
from src.agents.skill_base import SkillAgent

orch = Orchestrator(nodes={})

# 両バージョンのスキルクラスを取得
v1_skill = SkillAgent.discover_skills('src.agents.skills.v1')
v2_skill = SkillAgent.discover_skills('src.agents.skills.v2')

# A/B テスト実行
results = orch.run_ab_test(
    skill_name='planning',
    version_a='v1',
    version_b='v2',
    ctx_list=[ctx1, ctx2, ctx3, ...]  # 同一入力コンテキストリスト
)

# 結果比較
# results = {
#   'v1': {'success_count': 10, 'avg_duration_sec': 1.23, ...},
#   'v2': {'success_count': 10, 'avg_duration_sec': 1.15, ...},
# }
```

### Prometheus メトリクス

```prometheus
# アクティブなスキルバージョン (1=v1, 2=v2)
skill_version_active{skill_name="planning"}

# BookScore トレンド
book_score_trend{book_id="1",metric="avg_overall"}
book_score_trend{book_id="1",metric="slope"}

# BookScore 昇格判定
book_score_promotion_eligible_total{book_id="1"}

# BookScore 改善優先順位
book_score_improvement_priority{book_id="1",dimension="structure"}
```

---

## 8. BookScore 昇格・改善 API

### 昇格判定取得

```bash
GET /api/novel/books/{book_id}/promotion
```

**レスポンス例**:
```json
{
  "book_id": 1,
  "eligible": true,
  "avg_score": 85.67,
  "trend_slope": 10.0,
  "chapters_evaluated": 3,
  "reason": null
}
```

**判定基準**:
- 直近3章の平均スコア ≥ 80.0
- かつスコア傾向が上昇（最新章 - 3章前 > 0）

### 改善優先順位取得（管理者用）

```bash
GET /api/system/admin/book_score/improvement_priorities?book_id=1
```

**レスポンス例**:
```json
{
  "book_id": 1,
  "priorities": [
    {
      "dimension": "structure",
      "current_score": 65.0,
      "suggested_action": "ContextBuilderAgent: アーク境界・テンポ・因果整合性の強化",
      "expected_gain": "現在 65.0 → 目標 70+ (改善見込み 5pt)",
      "target_agent": "ContextBuilderAgent"
    },
    {
      "dimension": "coherency",
      "current_score": 70.0,
      "suggested_action": "ContextBuilderAgent: キャラ口調・世界観ルール・固有名詞統一の強化",
      "expected_gain": "現在 70.0 → 目標 70+ (改善見込み 0pt)",
      "target_agent": "ContextBuilderAgent"
    }
  ]
}
```

### Prometheus メトリクス（追加）

```prometheus
# 昇格判定カウンター
book_score_promotion_eligible_total{book_id="1"}

# 改善優先順位ゲージ（低いほど高優先度）
book_score_improvement_priority{book_id="1",dimension="structure"}
```

---

## 11. フォールトトレラント・スキル実行メトリクス

### フォールトトレラント実行 (`Orchestrator.run`)

個別スキルの失敗が全体パイプラインを停止させないよう、エラーハンドリングを強化しました。

**動作**:
- スキル実行時の `AgentResult.error` があっても次のスキルへ継続
- 予期しない例外も捕捉し、継続可能
- エラー情報は `artifacts` に `{skill_name}_error` または `{skill_name}_exception` として保存
- イベントバス経由でエラーイベントを発行

**設定例**:
```python
# エラーがあっても継続（デフォルト動作）
orch = Orchestrator(nodes={...})
await orch.run(ctx, start=AgentName.PLANNING)

# エラー情報確認
if "PlanningAgent_error" in ctx.artifacts:
    print("PlanningAgent でエラーが発生:", ctx.artifacts["PlanningAgent_error"])
```

### スキル実行メトリクス取得

```bash
GET /api/system/admin/skills/metrics
```

**レスポンス例**:
```json
{
  "active_version": "v1",
  "registered_skills": ["planning", "bible", "contextbuilder", "writing", "audit", "illustration"],
  "metrics": {
    "PlanningSkill": {
      "success_count": 10,
      "error_count": 0,
      "total_executions": 10,
      "avg_duration_sec": 0.123
    },
    "WritingSkill": {
      "success_count": 8,
      "error_count": 2,
      "total_executions": 10,
      "avg_duration_sec": 2.456
    }
  }
}
```

---

## 12. 今後の拡張ポイント

### スキル側
- `execute()` 内で `ctx.artifacts` 経由で前段スキルの成果物を活用
- `config` でスキル固有パラメータをマニフェストから注入
- 非同期並列実行対応（`asyncio.gather` で独立スキル同時実行）

### BookScore 側
- 各次元の実スコアリングロジック実装（プレースホルダー → 実装）
- 学習データ（人間評価）を用いた重み自動最適化
- 時系列トレンド分析・アラート機能

---

## 13. トラブルシューティング

| 現象 | 原因 | 対処 |
|------|------|------|
| スキルが検出されない | `__init__.py` 不足 / 継承漏れ | `SkillAgent` 継承確認、パッケージ構造確認 |
| マニフェスト循環依存 | `depends_on`/`runs_after` 循環 | `build_execution_order()` で検出される |
| BookScore が保存されない | repository 未指定 | `BookScoreCalculator(repository=repo)` |
| メトリクスが出ない | Prometheus クライアント未インストール | `pip install prometheus-client` |
| スキルバージョン切替失敗 | v2 ディレクトリ不在 | `src/agents/skills/v2/` 作成・スキル配置確認 |
| 昇格判定APIが404 | ルート未登録 | `novel.py` に `/books/{book_id}/promotion` 追加確認 |
| 改善優先順位が空 | スコアデータなし | 該当書籍で `calculate_book_score` 実行済みか確認 |