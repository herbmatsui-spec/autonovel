# 監視クエリ強化による運用改善计划書

## 概要

現行運用を継続しつつ、監視クエリを追加することで以下の目的を達成する：

1. 未解決伏線・成長フェーズ・メモリ境界を「見える化」する
2. 伏線解決漏れ・成長矛盾を定期バッチで自動検出する
3. 専用 API エンドポイントですぐに使える状態にする

## 前提条件

- 既存の `src/backend/routers/` のパターンを踏襲
- DB アクセスは `UnitOfWork` + SQLAlchemy ORM
- レスポンスは `api_success` ヘルパーを使用
- 新規ファイル追加のみで既存コードを変更しない

---

## ステップ 1: 新規 Router ファイルの作成

**ファイル**: `src/backend/routers/monitoring.py`

```python
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])
```

**理由**: 既存ルータと同じパターンに従うことで、低い性能の LLM でも確実に実装できる。

---

## ステップ 2: レスポンスモデルの定義

**追加するクラス**:

```python
class ForeshadowingRow(BaseModel):
    id: int
    book_id: int
    ep_num: int
    type: str
    description: str
    location: Optional[str]
    payoff_ep: Optional[int]
    fulfilled: bool

class ForeshadowingListResponse(BaseModel):
    total: int
    unresolved: List[ForeshadowingRow]
    resolved: List[ForeshadowingRow]
```

**理由**: レスポンスの型を明示することで、後のステップで迷わない。

---

## ステップ 3: 伏線一覧取得 API エンドポイントの実装

```python
@router.get("/{book_id}/foreshadowing")
async def get_foreshadowing_list(book_id: int):
    async with UnitOfWork(AppContainer.db()) as uow:
        rows = await uow.session.execute(
            "SELECT id, book_id, ep_num, type, description, location, payoff_ep, fulfilled "
            "FROM foreshadowing WHERE book_id = :book_id ORDER BY ep_num",
            {"book_id": book_id}
        )
        all_rows = rows.fetchall()

    unresolved = []
    resolved = []
    for r in all_rows:
        row = ForeshadowingRow(
            id=r.id, book_id=r.book_id, ep_num=r.ep_num,
            type=r.type, description=r.description,
            location=r.location, payoff_ep=r.payoff_ep,
            fulfilled=r.fulfilled
        )
        if r.fulfilled:
            resolved.append(row)
        else:
            unresolved.append(row)

    return api_success({
        "total": len(all_rows),
        "unresolved": [m.model_dump() for m in unresolved],
        "resolved": [m.model_dump() for m in resolved],
    }, "伏線一覧を取得しました")
```

---

## ステップ 4: 成長フェーズ取得レスポンスモデルの定義

```python
class CharacterArcRow(BaseModel):
    id: int
    character_id: int
    character_name: str
    arc_name: str
    current_stage_index: int
    total_stages: int
    is_completed: bool

class GrowthPlanListResponse(BaseModel):
    total: int
    arcs: List[CharacterArcRow]
```

---

## ステップ 5: 成長フェーズ取得 API エンドポイントの実装

```python
@router.get("/{book_id}/growth")
async def get_growth_plan(book_id: int):
    async with UnitOfWork(AppContainer.db()) as uow:
        rows = await uow.session.execute(
            """SELECT ca.id, ca.character_id, c.name as character_name,
                      ca.arc_name, ca.current_stage_index, ca.is_completed,
                      json_array_length(ca.arc_stages) as total_stages
               FROM character_arcs ca
               JOIN characters c ON c.id = ca.character_id
               WHERE ca.book_id = :book_id""",
            {"book_id": book_id}
        )
        all_rows = rows.fetchall()

    arcs = []
    for r in all_rows:
        arcs.append(CharacterArcRow(
            id=r.id,
            character_id=r.character_id,
            character_name=r.character_name,
            arc_name=r.arc_name,
            current_stage_index=r.current_stage_index,
            total_stages=r.total_stages or 1,
            is_completed=r.is_completed
        ))

    return api_success({
        "total": len(arcs),
        "arcs": [a.model_dump() for a in arcs],
    }, "成長フェーズ一覧を取得しました")
```

---

## ステップ 6: メモリ境界確認レスポンスモデルの定義

```python
class MemoryBoundaryResponse(BaseModel):
    short_term_window: int
    short_term_ep_count: int
    mid_term_arc_size: int
    latest_ep_num: int
    message: str
```

**理由**: メモリ境界の実効値を数値で見える化する。

---

## ステップ 7: メモリ境界確認 API エンドポイントの実装

```python
@router.get("/{book_id}/memory-boundary")
async def get_memory_boundary(book_id: int):
    async with UnitOfWork(AppContainer.db()) as uow:
        max_ep_row = await uow.session.execute(
            "SELECT MAX(ep_num) as latest_ep FROM chapters WHERE book_id = :book_id",
            {"book_id": book_id}
        )
        max_ep = max_ep_row.scalar() or 0

    short_term_window = 8  # 短期メモリ窓（固定値）
    mid_term_arc_size = 4  # 中期アークサイズ（固定値）

    async with UnitOfWork(AppContainer.db()) as uow:
        count_row = await uow.session.execute(
            "SELECT COUNT(*) FROM chapters "
            "WHERE book_id = :book_id AND ep_num > :threshold",
            {"book_id": book_id, "threshold": max_ep - short_term_window}
        )
        short_term_count = count_row.scalar() or 0

    return api_success(MemoryBoundaryResponse(
        short_term_window=short_term_window,
        short_term_ep_count=short_term_count,
        mid_term_arc_size=mid_term_arc_size,
        latest_ep_num=max_ep,
        message=f"直近{short_term_window}話中{short_term_count}話が短期メモリに存在"
    ).model_dump(), "メモリ境界を取得しました")
```

---

## ステップ 8: 整合性チェックレスポンスモデルの定義

```python
class ConsistencyIssue(BaseModel):
    issue_type: str
    description: str
    ep_num: Optional[int]
    related_ep: Optional[int]

class ConsistencyCheckResponse(BaseModel):
    issues_found: int
    issues: List[ConsistencyIssue]
```

---

## ステップ 9: 整合性チェック API エンドポイントの実装

```python
@router.get("/{book_id}/consistency")
async def check_consistency(book_id: int):
    issues = []

    async with UnitOfWork(AppContainer.db()) as uow:
        # 伏線解決漏れチェック
        rows = await uow.session.execute(
            """SELECT id, ep_num, description, payoff_ep
               FROM foreshadowing
               WHERE book_id = :book_id
                 AND payoff_ep IS NOT NULL
                 AND payoff_ep <= ep_num
                 AND fulfilled = 0""",
            {"book_id": book_id}
        )
        for r in rows:
            issues.append(ConsistencyIssue(
                issue_type="foreshadowing_unresolved",
                description=f"解決チャプター（{r.payoff_ep}）が導入（{r.ep_num}）以前",
                ep_num=r.ep_num,
                related_ep=r.payoff_ep
            ))

    return api_success(ConsistencyCheckResponse(
        issues_found=len(issues),
        issues=issues
    ).model_dump(), "整合性チェックが完了しました")
```

---

## ステップ 10: ルータをアプリに登録

**ファイル**: `src/backend/routers/__init__.py`（または `main.py` / `app.py`）

```python
from .monitoring import router as monitoring_router
```

**追加場所**（FastAPI アプリ構造に合わせる）:

```python
app.include_router(monitoring_router)
```

**確認方法**: `uvicorn` 起動後 `GET /api/monitoring/1/foreshadowing` が 200 を返すことを確認。

---

## ステップ 11: 定期バッチ用スクリプトの作成（任意）

**ファイル**: `scripts/monitoring_check.py`

```python
import asyncio
import logging
from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_all_books():
    async with UnitOfWork(AppContainer.db()) as uow:
        books = await uow.session.execute("SELECT id FROM books")
        book_ids = [r.id for r in books]

    for book_id in book_ids:
        async with UnitOfWork(AppContainer.db()) as uow:
            issues = await uow.session.execute(
                """SELECT id, ep_num, description, payoff_ep
                   FROM foreshadowing
                   WHERE book_id = :book_id
                     AND payoff_ep IS NOT NULL
                     AND payoff_ep <= ep_num
                     AND fulfilled = 0""",
                {"book_id": book_id}
            )
            problem_rows = issues.fetchall()

        if problem_rows:
            logger.warning(f"Book {book_id}: {len(problem_rows)} 件の伏線解決漏れ")

if __name__ == "__main__":
    asyncio.run(check_all_books())
```

**実行方法**: `python scripts/monitoring_check.py`

---

## ステップ 12: ドキュメント更新

**ファイル**: `docs/monitoring_endpoints.md`（新規作成）

```markdown
# 監視エンドポイント

## 概要

運用監視用の専用 API エンドポイント群。

## エンドポイント一覧

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/monitoring/{book_id}/foreshadowing` | 伏線一覧（未解決/解決済み） |
| GET | `/api/monitoring/{book_id}/growth` | 成長フェーズ一覧 |
| GET | `/api/monitoring/{book_id}/memory-boundary` | メモリ境界確認 |
| GET | `/api/monitoring/{book_id}/consistency` | 整合性チェック（伏線解決漏れ等） |

## 定期バッチ

```bash
python scripts/monitoring_check.py
```

- 毎日深夜実行を想定
- 問題がある場合は WARNING レベルでログ出力
```

---

## テスト確認項目

| ステップ | 確認内容 | 期待結果 |
|----------|----------|----------|
| 3 | `GET /api/monitoring/1/foreshadowing` | 200 + JSON（total, unresolved, resolved） |
| 5 | `GET /api/monitoring/1/growth` | 200 + JSON（total, arcs） |
| 7 | `GET /api/monitoring/1/memory-boundary` | 200 + JSON（short_term_window, short_term_ep_count） |
| 9 | `GET /api/monitoring/1/consistency` | 200 + JSON（issues_found, issues） |
| 11 | `python scripts/monitoring_check.py` | ログ出力（問題なければ INFO、あれば WARNING） |

---

## ファイル一覧

| ファイルパス | ステップ |
|-------------|----------|
| `src/backend/routers/monitoring.py` | 1-9 |
| `scripts/monitoring_check.py` | 11 |
| `docs/monitoring_endpoints.md` | 12 |

**既存ファイルの変更**: なし（ステップ 10 の router 登録のみ、コメント追加程度）

---

## 工期見積もり

- ステップ 1-9: 各 15〜30 分（合計 2〜3 時間）
- ステップ 10: 15 分
- ステップ 11: 30 分
- ステップ 12: 30 分
- テスト確認: 1 時間

**合計**: 約 5〜6 時間（1 人日以内）
