# AutoNovel v5.0 実装計画書 A2: Relational Memory & Foreshadowing (全24ステップ)

**対象ピラー**: Pillar 2 (Relational Simplicity & Foreshadowing State Machine)  
**目的**: 複雑骨折の温床となっていた Apache AGE（openCypher / グラフDB）および NetworkX フォールバックを完全撤廃し、標準的な PostgreSQL / SQLite リレーショナルテーブルによる「伏線ステートマシン」と「3層ローリング記憶」を完全実装する。  
**前提条件**: 各ステップは完全自己完結コード、変更対象ファイル、検証コマンド、期待結果を含む。

---

## 📋 ステップ一覧マトリクス

| ステップ | レイヤー | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | ORM | `src/backend/database/models_foreshadowing.py` | [NEW] ForeshadowingModel SQLAlchemy定義 |
| **Step 2** | Enum | `src/models/foreshadowing_status.py` | [NEW] ForeshadowingStatus Enum定義 |
| **Step 3** | Migration | `src/backend/migrations/versions/0020_foreshadowing_table.py` | [NEW] Alembic マイグレーションスクリプト |
| **Step 4** | Repo | `src/infrastructure/repositories/foreshadowing_repo.py` | [NEW] ForeshadowingRepository (CRUD & 未回収検索) |
| **Step 5** | Test | `tests/unit/database/test_foreshadowing_repo.py` | [NEW] 伏線リポジトリ単体テスト |
| **Step 6** | ORM | `src/backend/database/models_relation.py` | [NEW] CharacterRelationModel リレーショナル定義 |
| **Step 7** | Pipeline | `src/agents/context_builder_agent.py` | [MODIFY] 執筆プロンプトへの未回収伏線自動注入 |
| **Step 8** | Parser | `src/services/foreshadowing_parser.py` | [NEW] 本文中の伏線言及・回収検出パーサー |
| **Step 9** | Service | `src/services/foreshadowing_service.py` | [NEW] 伏線回収ステータス自動更新ロジック |
| **Step 10** | Auditor | `src/services/auditors/foreshadowing_auditor.py` | [NEW] 伏線回収の因果律・整合性チェック |
| **Step 11** | Test | `tests/unit/services/test_foreshadowing_pipeline.py` | [NEW] 伏線自動注入〜回収〜整合性単体テスト |
| **Step 12** | Pipeline | `src/backend/workflows/writing_langgraph.py` | [MODIFY] 伏線ステータス更新を章完了トランザクションに統合 |
| **Step 13** | ORM | `src/backend/database/models_digest.py` | [NEW] EpisodeDigestModel (100字事実ダイジェスト保存) |
| **Step 14** | Service | `src/services/context_compression/digest_service.py` | [NEW] 章完了時の自動100字事実要約生成 |
| **Step 15** | Memory | `src/services/context_compression/rolling_memory.py` | [NEW] 3層ローリング記憶ビルダーの実装 |
| **Step 16** | Memory | `src/services/context_compression/rolling_memory.py` | [MODIFY] トークン長上限ガード（ウィンドウ制御） |
| **Step 17** | Test | `tests/unit/services/test_rolling_context.py` | [NEW] 3層ローリング記憶の単体テスト |
| **Step 18** | Benchmark | `tests/perf/test_long_form_token_stability.py` | [NEW] 20話連続執筆時のコンテキスト長不変性テスト |
| **Step 19** | Audit | `src/services/age_client.py` | [INVESTIGATE] 呼び出し箇所の完全特定と置換 |
| **Step 20** | Cleanup | `src/services/age_client.py` | [DELETE] age_client.py の物理削除 (`git rm`) |
| **Step 21** | Cleanup | `src/services/graph/cypher_translator.py` | [DELETE] openCypherトランスレーターの削除 |
| **Step 22** | Cleanup | `src/services/graph_pipeline.py` | [MODIFY] NetworkXフォールバック排除とリレーショナル化 |
| **Step 23** | Infra | `docker-compose.yml` | [MODIFY] Apache AGE設定を削除し標準Postgres16へ一本化 |
| **Step 24** | Verify | CI / 全テスト実行 | 全単体・結合テストALL GREEN検証 |

---

## 🛠️ 各ステップの詳細手順（1〜24）

### Step 1: ForeshadowingModel SQLAlchemy定義
- **対象ファイル**: `src/backend/database/models_foreshadowing.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from src.infrastructure.database.models.base_orm import Base

class ForeshadowingModel(Base):
    __tablename__ = "foreshadowings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    planted_episode = Column(Integer, nullable=False)      # 設置話数
    target_episode = Column(Integer, nullable=True)        # 回収目標話数
    resolved_episode = Column(Integer, nullable=True)      # 実際の回収話数
    status = Column(String(20), default="planted", index=True) # planted, resolved, abandoned
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```
- **検証コマンド**:
```bash
python -c "from src.backend.database.models_foreshadowing import ForeshadowingModel; print(ForeshadowingModel.__tablename__)"
```
- **期待結果**: `foreshadowings`

---

### Step 2: ForeshadowingStatus Enum定義
- **対象ファイル**: `src/models/foreshadowing_status.py` (新規作成)
- **実装コード**:
```python
from enum import Enum

class ForeshadowingStatus(str, Enum):
    PLANTED = "planted"       # 伏線設置済み（未回収）
    PROGRESSED = "progressed" # 進展・匂わせ中
    RESOLVED = "resolved"     # 回収完了
    ABANDONED = "abandoned"   # 回収破棄
```

---

### Step 3: Alembic マイグレーションスクリプト
- **対象ファイル**: `src/backend/migrations/versions/0020_foreshadowing_table.py` (新規作成)
- **実装コード**:
```python
"""create foreshadowings table

Revision ID: 0020_foreshadowing
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'foreshadowings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('planted_episode', sa.Integer(), nullable=False),
        sa.Column('target_episode', sa.Integer(), nullable=True),
        sa.Column('resolved_episode', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='planted'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_foreshadowings_book_id', 'foreshadowings', ['book_id'])
    op.create_index('ix_foreshadowings_status', 'foreshadowings', ['status'])

def downgrade():
    op.drop_table('foreshadowings')
```

---

### Step 4: ForeshadowingRepository (CRUD & 未回収検索)
- **対象ファイル**: `src/infrastructure/repositories/foreshadowing_repo.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.database.models_foreshadowing import ForeshadowingModel

class ForeshadowingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_unresolved(self, book_id: int) -> List[ForeshadowingModel]:
        """指定作品の未回収伏線を全件取得"""
        stmt = select(ForeshadowingModel).where(
            ForeshadowingModel.book_id == book_id,
            ForeshadowingModel.status.in_(["planted", "progressed"])
        ).order_by(ForeshadowingModel.planted_episode)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def resolve(self, foreshadowing_id: int, episode_num: int) -> bool:
        """伏線を回収済みに更新"""
        stmt = update(ForeshadowingModel).where(
            ForeshadowingModel.id == foreshadowing_id
        ).values(status="resolved", resolved_episode=episode_num)
        res = await self.db.execute(stmt)
        return res.rowcount > 0
```

---

### Step 5: 伏線リポジトリ単体テスト
- **対象ファイル**: `tests/unit/database/test_foreshadowing_repo.py` (新規作成)
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.infrastructure.repositories.foreshadowing_repo import ForeshadowingRepository

@pytest.mark.asyncio
async def test_foreshadowing_repo_unresolved():
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [
        MagicMock(id=1, title="謎の剣", status="planted")
    ]
    mock_db.execute.return_value = mock_res
    repo = ForeshadowingRepository(mock_db)
    items = await repo.get_unresolved(book_id=1)
    assert len(items) == 1
    assert items[0].title == "謎の剣"
```
- **検証コマンド**:
```bash
.venv\Scripts\pytest tests/unit/database/test_foreshadowing_repo.py -v
```
- **期待結果**: `1 passed`

---

### Step 6: CharacterRelationModel リレーショナル定義
- **対象ファイル**: `src/backend/database/models_relation.py` (新規作成)
- **目的**: グラフDBのEdgeを、単純な `(source_char_id, target_char_id, relation_type)` テーブルに置換。
- **実装コード**:
```python
from sqlalchemy import Column, Integer, String, ForeignKey
from src.infrastructure.database.models.base_orm import Base

class CharacterRelationModel(Base):
    __tablename__ = "character_relations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, nullable=False, index=True)
    source_char_id = Column(Integer, nullable=False)
    target_char_id = Column(Integer, nullable=False)
    relation_type = Column(String(50), nullable=False)  # 例: 宿敵, 師弟, 信頼, 片思い
```

---

### Step 7: 執筆プロンプトへの未回収伏線自動注入
- **対象ファイル**: `src/agents/context_builder_agent.py` (編集)
- **目的**: プロンプト作成時に、未回収伏線一覧をテキストとしてプロンプトへ注入。
- **実装コード**:
```python
    def format_unresolved_foreshadowings(self, foreshadowings: list[Any]) -> str:
        if not foreshadowings:
            return "なし"
        lines = []
        for f in foreshadowings:
            lines.append(f"- 【伏線: {f.title}】(設置: 第{f.planted_episode}話) 要約: {f.description}")
        return "\n".join(lines)
```

---

### Step 8: 本文中の伏線言及・回収検出パーサー
- **対象ファイル**: `src/services/foreshadowing_parser.py` (新規作成)
- **目的**: 生成された本文中に伏線のキーワードや回収描写が含まれているかを簡易検出。
- **実装コード**:
```python
def detect_foreshadowing_mentions(text: str, foreshadowing_titles: list[str]) -> list[str]:
    """本文中に登場した伏線タイトルのリストを返す"""
    return [title for title in foreshadowing_titles if title in text]
```

---

### Step 9: 伏線回収ステータス自動更新ロジック
- **対象ファイル**: `src/services/foreshadowing_service.py` (新規作成)
- **目的**: 執筆完了時に、回収された伏線をDB上で自動的に `resolved` に更新する。
- **実装コード**:
```python
class ForeshadowingService:
    def __init__(self, repo: ForeshadowingRepository):
        self.repo = repo

    async def check_and_resolve(self, book_id: int, episode_num: int, draft_text: str) -> list[str]:
        unresolved = await self.repo.get_unresolved(book_id)
        resolved_titles = []
        for f in unresolved:
            if f.title in draft_text and (f.target_episode is None or episode_num >= f.target_episode):
                await self.repo.resolve(f.id, episode_num)
                resolved_titles.append(f.title)
        return resolved_titles
```

---

### Step 10: 伏線回収の因果律・整合性チェック
- **対象ファイル**: `src/services/auditors/foreshadowing_auditor.py` (新規作成)
- **目的**: 設置前の話数で「回収」されていないか、順序の矛盾を0msでチェック。
- **実装コード**:
```python
def validate_foreshadowing_order(planted_ep: int, resolved_ep: int) -> bool:
    """伏線設置話数 <= 回収話数 であることを検証"""
    return planted_ep <= resolved_ep
```

---

### Step 11: 伏線自動注入〜回収〜整合性単体テスト
- **対象ファイル**: `tests/unit/services/test_foreshadowing_pipeline.py` (新規作成)
- **検証コマンド**:
```bash
.venv\Scripts\pytest tests/unit/services/test_foreshadowing_pipeline.py -v
```

---

### Step 12: 伏線ステータス更新を章完了トランザクションに統合
- **対象ファイル**: `src/backend/workflows/writing_langgraph.py` (編集)
- **目的**: 章の永続化コミット時に `ForeshadowingService.check_and_resolve` を一括トランザクションで呼び出す。

---

### Step 13: EpisodeDigestModel (100字事実ダイジェスト保存)
- **対象ファイル**: `src/backend/database/models_digest.py` (新規作成)
- **実装コード**:
```python
from sqlalchemy import Column, Integer, Text, ForeignKey
from src.infrastructure.database.models.base_orm import Base

class EpisodeDigestModel(Base):
    __tablename__ = "episode_digests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, nullable=False, index=True)
    episode_num = Column(Integer, nullable=False)
    digest_text = Column(Text, nullable=False)  # 最大150文字の確定事実
```

---

### Step 14: 章完了時の自動100字事実要約生成
- **対象ファイル**: `src/services/context_compression/digest_service.py` (新規作成)
- **実装コード**:
```python
async def generate_episode_digest(llm, draft_text: str, ep_num: int) -> str:
    """エピソード本文から確定した事実のみを100字以内で要約抽出"""
    prompt = f"第{ep_num}話の本文から、後続話に影響する「起きた客観的事実」のみを100文字以内で箇条書き要約してください:\n{draft_text[:2500]}"
    res = await llm.generate(prompt=prompt, temperature=0.1)
    return res.strip()[:150]
```

---

### Step 15: 3層ローリング記憶ビルダーの実装
- **対象ファイル**: `src/services/context_compression/rolling_memory.py` (新規作成)
- **実装コード**:
```python
class RollingMemoryBuilder:
    def build_context(self, bible_summary: str, past_digests: list[str], prev_episode_text: str) -> str:
        """3層ローリング記憶を結合してプロンプト用コンテキストを構築"""
        digests_str = "\n".join(past_digests) if past_digests else "なし"
        return f"""\
【設定・世界観バイブル】
{bible_summary}

【過去話の確定事実タイムライン】
{digests_str}

【直前エピソード本文】
{prev_episode_text}
"""
```

---

### Step 16: トークン長上限ガード（ウィンドウ制御）
- **対象ファイル**: `src/services/context_compression/rolling_memory.py` (追記)
- **目的**: 過去ダイジェストが100話分蓄積しても、直近30話分＋主要イベントのみにウィンドウ制限してトークン溢れを防止。

---

### Step 17: 3層ローリング記憶の単体テスト
- **対象ファイル**: `tests/unit/services/test_rolling_context.py` (新規作成)
- **検証コマンド**:
```bash
.venv\Scripts\pytest tests/unit/services/test_rolling_context.py -v
```

---

### Step 18: 20話連続執筆時のコンテキスト長不変性テスト
- **対象ファイル**: `tests/perf/test_long_form_token_stability.py` (新規作成)
- **目的**: 1話目と20話目でプロンプトのトークン消費増加が許容範囲（+20%以内）に収まることを検証。

---

### Step 19: 呼び出し箇所の完全特定と置換
- **対象**: `git grep "age_client"` を実行し、全参照箇所を `ForeshadowingRepository` に置換。

---

### Step 20: age_client.py の物理削除
- **コマンド**:
```bash
git rm -f src/services/age_client.py
```

---

### Step 21: openCypherトランスレーターの削除
- **コマンド**:
```bash
git rm -f src/services/graph/cypher_translator.py
```

---

### Step 22: NetworkXフォールバック排除とリレーショナル化
- **対象ファイル**: `src/services/graph_pipeline.py` (編集)
- **目的**: NetworkXグラフ生成コードを全廃し、単純なリレーショナル検索に置き換え。

---

### Step 23: docker-compose.yml から Apache AGE 設定を削除
- **対象ファイル**: `docker-compose.yml`, `docker-compose.prod.yml` (編集)
- **目的**: 標準公式 `postgres:16-alpine` に一本化し、コンテナ起動速度を短縮。

---

### Step 24: 全テスト実行 & グラフDB完全排除の検証
- **検証コマンド**:
```bash
.venv\Scripts\pytest tests/unit/database tests/unit/services -v
```
- **期待結果**: 全テスト合格、AGE依存ゼロ。
