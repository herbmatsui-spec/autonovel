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

## 5. 今後の拡張ポイント

### スキル側
- `execute()` 内で `ctx.artifacts` 経由で前段スキルの成果物を活用
- `config` でスキル固有パラメータをマニフェストから注入
- 非同期並列実行対応（`asyncio.gather` で独立スキル同時実行）

### BookScore 側
- 各次元の実スコアリングロジック実装（プレースホルダー → 実装）
- 学習データ（人間評価）を用いた重み自動最適化
- 時系列トレンド分析・アラート機能

---

## 6. トラブルシューティング

| 現象 | 原因 | 対処 |
|------|------|------|
| スキルが検出されない | `__init__.py` 不足 / 継承漏れ | `SkillAgent` 継承確認、パッケージ構造確認 |
| マニフェスト循環依存 | `depends_on`/`runs_after` 循環 | `build_execution_order()` で検出される |
| BookScore が保存されない | repository 未指定 | `BookScoreCalculator(repository=repo)` |
| メトリクスが出ない | Prometheus クライアント未インストール | `pip install prometheus-client` |