# P1: DDDレイヤー分離強化 - 実装計画書

## 概要
現状の `src/agents/`, `src/services/`, `src/backend/` に混在するドメインロジック・インフラ・APIを、DDDの4層アーキテクチャへ再編成する。

**依存方向の厳守**: `interfaces → application → domain ← infrastructure`

---

## Step 1: 新ディレクトリ構造の作成（空ファイル配置のみ）

**目的**: 物理的な層境界を作る。コード移動は後続ステップで行う。

```bash
mkdir -p src/domain/{entities,value_objects,domain_services,repositories}
mkdir -p src/application/{use_cases,dtos,ports}
mkdir -p src/infrastructure/{persistence,external,queue,config}
mkdir -p src/interfaces/{api,cli,graphql}
```

**成果物**: 空の `__init__.py` を各ディレクトリに配置
**確認**: `find src/domain src/application src/infrastructure src/interfaces -name "*.py" | head -20`

---

## Step 2: ドメイン層 - エンティティ・値オブジェクトの定義（リポジトリインターフェースなし）

**対象ファイル**: `src/backend/database/models.py` からドメインモデルを抽出

**作業**:
1. `src/domain/entities/` に以下を新規作成:
   - `novel.py` - Novel, Chapter, Episode, Volume エンティティ
   - `character.py` - Character エンティティ
   - `world_bible.py` - WorldBible, Setting, Lore エンティティ
   - `plot.py` - Plot, PlotPoint, Arc エンティティ
   - `branch.py` - Branch, BranchPlay エンティティ
   - `audit.py` - AuditResult, AuditFinding エンティティ

2. `src/domain/value_objects/` に以下を新規作成:
   - `ids.py` - NovelId, ChapterId, EpisodeId, CharacterId (UUIDラッパー)
   - `text.py` - TextContent, MarkdownText, PlainText
   - `scores.py` - QualityScore, BookScore, TensionScore
   - `metadata.py` - NovelMetadata, PublishMetadata

**ルール**:
- SQLAlchemyモデル (`models.py`) は **参照しない**。純粋なPythonクラス（dataclass/pydantic）のみ
- リポジトリIFはこのステップでは作らない
- 既存コードは一切変更しない

**確認**: `python -c "from src.domain.entities.novel import Novel; print('OK')"`

---

## Step 3: ドメイン層 - リポジトリインターフェース（Port）の定義

**対象**: `src/backend/database/repo_protocols.py` を参考に純粋なインターフェース化

**作業**: `src/domain/repositories/` に以下を新規作成:
- `novel_repository.py` - `INovelRepository` (Protocol/ABC)
- `chapter_repository.py` - `IChapterRepository`
- `character_repository.py` - `ICharacterRepository`
- `world_bible_repository.py` - `IWorldBibleRepository`
- `plot_repository.py` - `IPlotRepository`
- `branch_repository.py` - `IBranchRepository`
- `audit_repository.py` - `IAuditRepository`
- `unit_of_work.py` - `IUnitOfWork` (トランザクション境界)

**インターフェース例**:
```python
# src/domain/repositories/novel_repository.py
from typing import Protocol, Optional, List
from src.domain.entities.novel import Novel
from src.domain.value_objects.ids import NovelId

class INovelRepository(Protocol):
    async def get_by_id(self, novel_id: NovelId) -> Optional[Novel]: ...
    async def save(self, novel: Novel) -> Novel: ...
    async def list_all(self, limit: int, offset: int) -> List[Novel]: ...
    async def delete(self, novel_id: NovelId) -> bool: ...
```

**確認**: `python -c "from src.domain.repositories.novel_repository import INovelRepository; print('OK')"`

---

## Step 4: ドメイン層 - ドメインサービスの定義（純粋なビジネスロジックのみ）

**対象**: `src/services/plot_service.py`, `src/services/bible_service.py` 等からビジネスルール抽出

**作業**: `src/domain/domain_services/` に以下を新規作成:
- `plot_domain_service.py` - プロット整合性チェック、構造検証ロジック
- `bible_domain_service.py` - 世界観整合性、設定衝突検出
- `character_domain_service.py` - キャラクター整合性、関係性検証
- `quality_domain_service.py` - 品質スコア計算ロジック（BookScoreCalculatorの純粋ロジック部分）

**ルール**:
- インフラ依存（DB, LLM, 外部API）を持たない
- リポジトリインターフェース（`INovelRepository`等）のみに依存
- 既存サービスクラスはそのまま残す（後でアダプタ化）

**確認**: 各サービスが単体でimport可能かテスト

---

## Step 5: アプリケーション層 - DTO（データ転送オブジェクト）の定義

**対象**: `src/backend/schemas/` からAPIスキーマを流用せず、ユースケース専用DTOを定義

**作業**: `src/application/dtos/` に以下を新規作成:
- `novel_dto.py` - `CreateNovelDTO`, `UpdateNovelDTO`, `NovelResponseDTO`, `NovelListItemDTO`
- `chapter_dto.py` - `CreateChapterDTO`, `ChapterResponseDTO`
- `episode_dto.py` - `WriteEpisodeDTO`, `EpisodeResponseDTO`, `EpisodeDraftDTO`
- `plot_dto.py` - `GeneratePlotDTO`, `PlotResponseDTO`, `PlotExpansionDTO`
- `bible_dto.py` - `GenerateBibleDTO`, `BibleResponseDTO`, `SettingDTO`
- `audit_dto.py` - `AuditRequestDTO`, `AuditResponseDTO`, `AuditFindingDTO`
- `common.py` - `PaginationDTO`, `ErrorResponseDTO`, `SuccessResponseDTO`

**ルール**:
- pydantic BaseModel を使用
- ドメインエンティティと1:1でマッピングしない（ユースケース最適化）
- バリデーションはDTO側で完結

**確認**: `python -c "from src.application.dtos.novel_dto import CreateNovelDTO; print('OK')"`

---

## Step 6: アプリケーション層 - ユースケース（アプリケーションサービス）の実装

**対象**: 既存のオーケストレーター・エンジン・ワークフローからユースケース抽出

**作業**: `src/application/use_cases/` に以下を新規作成:
- `novel_use_cases.py` - `CreateNovelUseCase`, `GetNovelUseCase`, `ListNovelsUseCase`, `UpdateNovelUseCase`, `DeleteNovelUseCase`
- `chapter_use_cases.py` - `CreateChapterUseCase`, `GetChapterUseCase`, `ReorderChaptersUseCase`
- `writing_use_cases.py` - `WriteEpisodeUseCase`, `RewriteEpisodeUseCase`, `ExpandPlotUseCase`, `GenerateBibleUseCase`
- `audit_use_cases.py` - `RunLogicalAuditUseCase`, `RunStyleAuditUseCase`, `GetAuditHistoryUseCase`
- `branch_use_cases.py` - `CreateBranchUseCase`, `MergeBranchUseCase`, `ListBranchPlaysUseCase`
- `illustration_use_cases.py` - `GenerateIllustrationUseCase`, `ListIllustrationsUseCase`

**実装パターン（全ユースケース共通）**:
```python
# src/application/use_cases/novel_use_cases.py
from dataclasses import dataclass
from src.domain.repositories.novel_repository import INovelRepository
from src.domain.repositories.unit_of_work import IUnitOfWork
from src.application.dtos.novel_dto import CreateNovelDTO, NovelResponseDTO
from src.domain.entities.novel import Novel
from src.domain.value_objects.ids import NovelId

@dataclass
class CreateNovelUseCase:
    novel_repo: INovelRepository
    uow: IUnitOfWork

    async def execute(self, dto: CreateNovelDTO) -> NovelResponseDTO:
        async with self.uow:
            novel = Novel.create(title=dto.title, author_id=dto.author_id, ...)
            saved = await self.novel_repo.save(novel)
            await self.uow.commit()
        return NovelResponseDTO.from_entity(saved)
```

**ルール**:
- コンストラクタインジェクションでリポジトリIFを受け取る
- トランザクション境界は `IUnitOfWork` で管理
- ドメインサービスを協調させるのみ（ロジックを持たない）
- 非同期メソッド名は統一して `execute()`

**確認**: 各ユースケースがimport可能かテスト

---

## Step 7: アプリケーション層 - ポート（出力ポート）の定義

**目的**: インフラ層への依存をインターフェースで抽象化

**作業**: `src/application/ports/` に以下を新規作成:
- `llm_port.py` - `ILLMProvider` (generate, generate_json, embed)
- `vector_store_port.py` - `IVectorStore` (upsert, search, delete)
- `image_generation_port.py` - `IImageGenerator` (generate, edit)
- `cache_port.py` - `ICache` (get, set, delete, exists)
- `event_bus_port.py` - `IEventBus` (publish, subscribe)
- `file_storage_port.py` - `IFileStorage` (upload, download, delete)
- `metrics_port.py` - `IMetricsCollector` (increment, histogram, gauge)

**確認**: 各ポートがimport可能かテスト

---

## Step 8: インフラストラクチャ層 - リポジトリ実装（アダプタ）

**対象**: `src/backend/database/repositories/` 既存実装をラップ

**作業**: `src/infrastructure/persistence/` に以下を新規作成:
- `sqlalchemy_novel_repository.py` - `SQLAlchemyNovelRepository(INovelRepository)`
- `sqlalchemy_chapter_repository.py` - `SQLAlchemyChapterRepository(IChapterRepository)`
- `sqlalchemy_character_repository.py` - ...
- `sqlalchemy_world_bible_repository.py` - ...
- `sqlalchemy_plot_repository.py` - ...
- `sqlalchemy_branch_repository.py` - ...
- `sqlalchemy_audit_repository.py` - ...
- `sqlalchemy_unit_of_work.py` - `SQLAlchemyUnitOfWork(IUnitOfWork)`

**実装パターン**:
```python
# src/infrastructure/persistence/sqlalchemy_novel_repository.py
from src.domain.repositories.novel_repository import INovelRepository
from src.domain.entities.novel import Novel
from src.domain.value_objects.ids import NovelId
from src.backend.database.models import NovelModel
from src.backend.database.core import DatabaseManager

class SQLAlchemyNovelRepository(INovelRepository):
    def __init__(self, db: DatabaseManager):
        self._db = db

    async def get_by_id(self, novel_id: NovelId) -> Optional[Novel]:
        async with self._db.session() as session:
            model = await session.get(NovelModel, novel_id.value)
            return self._to_entity(model) if model else None

    def _to_entity(self, model: NovelModel) -> Novel:
        return Novel(
            id=NovelId(model.id),
            title=model.title,
            # ... マッピング
        )
```

**ルール**:
- 既存 `repository.py`, `repositories/` のコードを **変更せず** 新規クラスでラップ
- マッピングロジック（Model↔Entity）はリポジトリ実装内に閉じ込める

**確認**: 各リポジトリがインターフェースを満たすか `isinstance(repo, INovelRepository)` でテスト

---

## Step 9: インフラストラクチャ層 - 外部サービスアダプタ実装

**対象**: `src/core/llm_gateway.py`, `src/services/vector_store/`, `src/services/image_service.py` 等

**作業**: `src/infrastructure/external/` に以下を新規作成:
- `gemini_llm_adapter.py` - `GeminiLLMAdapter(ILLMProvider)`
- `openai_llm_adapter.py` - `OpenAILLMAdapter(ILLMProvider)`
- `claude_llm_adapter.py` - `ClaudeLLMAdapter(ILLMProvider)`
- `ollama_llm_adapter.py` - `OllamaLLMAdapter(ILLMProvider)`
- `chroma_vector_store_adapter.py` - `ChromaVectorStoreAdapter(IVectorStore)`
- `pgvector_vector_store_adapter.py` - `PgVectorVectorStoreAdapter(IVectorStore)`
- `dalle_image_adapter.py` - `DalleImageAdapter(IImageGenerator)`
- `sd_webui_image_adapter.py` - `SdWebUIImageAdapter(IImageGenerator)`
- `redis_cache_adapter.py` - `RedisCacheAdapter(ICache)`
- `huey_event_bus_adapter.py` - `HueyEventBusAdapter(IEventBus)`

**ルール**:
- 既存ゲートウェイ・サービスクラスを **変更せず** アダプタでラップ
- ポートインターフェース（Step 7）を実装する

**確認**: 各アダプタがポートインターフェースを満たすかテスト

---

## Step 10: インフラストラクチャ層 - 設定・DIコンテナの分離

**対象**: `src/core/container/app.py`, `src/core/container/infra.py`, `src/backend/config.py`

**作業**:
1. `src/infrastructure/config/` に以下を新規作成:
   - `settings.py` - 環境変数読み込み（pydantic-settings）
   - `database_config.py` - DB接続設定
   - `llm_config.py` - LLMプロバイダー設定
   - `container.py` - **新しいDIコンテナ定義**

2. 新コンテナ設計 (`src/infrastructure/config/container.py`):
```python
from dependency_injector import containers, providers
from src.infrastructure.config.settings import Settings

class InfrastructureContainer(containers.DeclarativeContainer):
    config = providers.Singleton(Settings)
    
    # DB
    db = providers.Singleton(DatabaseManager, db_url=config.provided.DATABASE_URL)
    
    # Repositories (Domain → Infrastructure)
    novel_repo = providers.Factory(SQLAlchemyNovelRepository, db=db)
    chapter_repo = providers.Factory(SQLAlchemyChapterRepository, db=db)
    # ... 他リポジトリ
    
    uow = providers.Factory(SQLAlchemyUnitOfWork, db=db)
    
    # External Services (Ports → Adapters)
    llm_provider = providers.Singleton(
        GeminiLLMAdapter, api_key=config.provided.GEMINI_API_KEY
    )  # 設定で切替可能に
    
    vector_store = providers.Singleton(ChromaVectorStoreAdapter, ...)
    image_generator = providers.Singleton(DalleImageAdapter, ...)
    cache = providers.Singleton(RedisCacheAdapter, ...)
    event_bus = providers.Singleton(HueyEventBusAdapter, ...)

class ApplicationContainer(containers.DeclarativeContainer):
    infrastructure = providers.DependenciesContainer()
    
    # Domain Services (pure)
    plot_domain_service = providers.Factory(PlotDomainService)
    bible_domain_service = providers.Factory(BibleDomainService)
    # ...
    
    # Use Cases (Application)
    create_novel_use_case = providers.Factory(
        CreateNovelUseCase,
        novel_repo=infrastructure.novel_repo,
        uow=infrastructure.uow,
    )
    write_episode_use_case = providers.Factory(
        WriteEpisodeUseCase,
        novel_repo=infrastructure.novel_repo,
        chapter_repo=infrastructure.chapter_repo,
        llm_provider=infrastructure.llm_provider,
        vector_store=infrastructure.vector_store,
        uow=infrastructure.uow,
    )
    # ... 他ユースケース

class InterfaceContainer(containers.DeclarativeContainer):
    application = providers.DependenciesContainer()
    
    # FastAPI routers will use application.use_cases
```

3. 既存 `AppContainer` は **Deprecated** 扱いにし、段階的に移行

**確認**: 新コンテナで全ユースケースが解決可能か `container.application.create_novel_use_case()` でテスト

---

## Step 11: インターフェース層 - FastAPIルーターの書き換え（薄いアダプタ化）

**対象**: `src/backend/routers/` 既存ルーター

**作業**: `src/interfaces/api/` に新規ルーター作成（既存は残す）:
- `novel_router.py` - `POST /novels`, `GET /novels/{id}`, `GET /novels`, `PATCH /novels/{id}`, `DELETE /novels/{id}`
- `chapter_router.py` - ...
- `writing_router.py` - `POST /episodes/write`, `POST /episodes/rewrite`, `POST /plots/expand`, `POST /bible/generate`
- `audit_router.py` - `POST /audit/logical`, `POST /audit/style`, `GET /audit/history`
- `branch_router.py` - ...
- `illustration_router.py` - ...

**実装パターン**:
```python
# src/interfaces/api/novel_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from src.application.use_cases.novel_use_cases import (
    CreateNovelUseCase, GetNovelUseCase, ListNovelsUseCase, UpdateNovelUseCase, DeleteNovelUseCase
)
from src.application.dtos.novel_dto import (
    CreateNovelDTO, UpdateNovelDTO, NovelResponseDTO, NovelListItemDTO
)
from src.infrastructure.config.container import ApplicationContainer

router = APIRouter(prefix="/novels", tags=["novels"])

# DIからユースケース取得（本番ではDependsで注入）
def get_create_use_case() -> CreateNovelUseCase:
    return ApplicationContainer().create_novel_use_case()

@router.post("", response_model=NovelResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_novel(dto: CreateNovelDTO, use_case: CreateNovelUseCase = Depends(get_create_use_case)):
    return await use_case.execute(dto)

@router.get("/{novel_id}", response_model=NovelResponseDTO)
async def get_novel(novel_id: str, use_case: GetNovelUseCase = Depends(get_get_use_case)):
    result = await use_case.execute(novel_id)
    if not result:
        raise HTTPException(status_code=404, detail="Novel not found")
    return result
```

**ルール**:
- ルーターは **ユースケース呼び出しのみ**（ビジネスロジックゼロ）
- DTOでリクエスト/レスポンスをバリデーション
- 既存 `src/backend/routers/` は並行稼働させ、段階的に切替

**確認**: 新ルーターでAPI叩いて動作確認（既存APIと並行）

---

## Step 12: 依存方向の検証・テスト・ドキュメント化

**作業**:
1. **依存方向チェックスクリプト作成** (`scripts/check_layer_dependencies.py`):
```python
import ast
import sys
from pathlib import Path

LAYER_ORDER = {
    "src.interfaces": 0,
    "src.application": 1,
    "src.domain": 2,
    "src.infrastructure": 3,
}

def check_imports(file_path: Path, layer: str):
    # 同じ層または下位層へのimportのみ許可
    # 上位層へのimportがあればエラー
    pass

# 全.pyファイルを走査し、違反をレポート
```

2. **単体テスト追加** (`tests/unit/test_ddd_layers.py`):
   - ドメイン層: エンティティ・VO・ドメインサービスがインフラ非依存で動くか
   - アプリケーション層: ユースケースがモックリポジトリで動くか
   - インフラ層: アダプタがポートIFを満たすか

3. **統合テスト追加** (`tests/integration/test_ddd_integration.py`):
   - 新コンテナでAPIエンドツーエンドが動くか

4. **アーキテクチャ決定記録 (ADR)** 作成: `docs/adr/001-ddd-layer-separation.md`

5. **移行ガイド** 作成: `docs/migration/ddd-layer-migration-guide.md`

**確認**:
- `python scripts/check_layer_dependencies.py` → 違反0件
- `pytest tests/unit/test_ddd_layers.py -v` → 全パス
- `pytest tests/integration/test_ddd_integration.py -v` → 全パス

---

## 実装順序の依存関係

```
Step 1 (ディレクトリ作成)
    ↓
Step 2 (Entities/VOs) ← 独立
    ↓
Step 3 (Repository IFs) ← Step 2に依存
    ↓
Step 4 (Domain Services) ← Step 2, 3に依存
    ↓
Step 5 (DTOs) ← Step 2に依存
    ↓
Step 6 (Use Cases) ← Step 3, 4, 5に依存
    ↓
Step 7 (Output Ports) ← 独立
    ↓
Step 8 (Repository Impl) ← Step 3, 7に依存
    ↓
Step 9 (External Adapters) ← Step 7に依存
    ↓
Step 10 (DI Container) ← Step 3, 4, 6, 7, 8, 9に依存
    ↓
Step 11 (API Routers) ← Step 5, 6, 10に依存
    ↓
Step 12 (Verification) ← 全Step完了後
```

---

## 移行戦略（既存コードとの共存）

| フェーズ | 対象 | 方針 |
|---------|------|------|
| Phase 1 | 新機能 | 新アーキテクチャで実装 |
| Phase 2 | 既存API | 新ルーター並行稼働、段階的切替 |
| Phase 3 | 既存エージェント | SkillAgent → UseCase + DomainService へリファクタ |
| Phase 4 | 旧コンテナ | `AppContainer` 廃止、全参照を新コンテナへ |

---

## 完了基準

- [ ] `src/domain/` にインフラ依存ゼロの純粋ドメインモデルが存在
- [ ] `src/application/` にユースケースが存在し、モックで単体テスト可能
- [ ] `src/infrastructure/` に全ポートの実装が存在
- [ ] `src/interfaces/api/` に薄いルーターが存在
- [ ] `scripts/check_layer_dependencies.py` で違反0件
- [ ] 既存APIエンドポイントが新アーキテクチャ経由で動作
- [ ] ADR・移行ガイドが文書化済み