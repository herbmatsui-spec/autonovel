# Easy Mode Suite 改善 実装計画書

> 対象: AutoNovel v4.0.0（`E:\ssssda`）
> 作成日: 2026-09-01
> 対応レビュー: 2026-09-01 コードレビュー報告書
> 想定モデル性能: 低性能 LLM でも実装可能な粒度に分割（1 ステップ ≈ 1 ファイル単位）

このドキュメントは、コードレビューで指摘された問題を **30 ステップ** に分解した実装計画書です。各ステップは「1 つの PR / 1 つのコミット」として完結できる粒度にしてあります。順番に進めることで情報の損失を防ぎ、途中で中断しても再開しやすくなっています。

---

## 凡例

| 記号 | 意味 |
|:--|:--|
| 🔴 critical | サービス運用に致命的な問題（即修正） |
| 🟠 high | アーキテクチャ・保守性に重大な影響 |
| 🟡 medium | 計画的に対応 |
| 🟢 low | 改善・将来対応 |
| 🏷️ | 影響を受ける Easy Mode Suite 機能名 |
| 📂 | 対象ファイル・新規作成ファイル |
| ✅ | 完了条件（テスト・lint・手動確認のチェックリスト） |
| ⚠️ | 注意点・後方互換性 |

---

## 全体ロードマップ

```
Phase 1（即時・1〜2日）       Step 1〜5    Easy Mode Suite 命名 + ドキュメント整備
Phase 2（critical 修正）     Step 6〜10   _BOOK_STORE / _GACHA_CACHE 永続化、health check 実体化
Phase 3（high 修正）         Step 11〜17  レイヤ依存整理、Book テーブル mode カラム、re-export 整理
Phase 4（テスト強化）        Step 18〜22  test_illustration_agent 強化、conftest 整備
Phase 5（medium / low 改善） Step 23〜28  typo 修正、警告ログ整理、依存ピニング
Phase 6（リファクタ）        Step 29〜30  erotic_integrity.py 分割
```

各ステップの想定所要時間: **30〜90 分**。低性能 LLM でもこなせる粒度。

---

# Phase 1: 命名・ドキュメント整備（即時・1〜2日）

## Step 1. Easy Mode Suite 命名表を `docs/term-mapping.md` に作成 🏷️ 全機能

**目的**: コード上の旧名と機能名（機能 ID）を一対一で対応付ける内部ドキュメントを作成し、以降のステップで参照する。

📂 新規: `docs/term-mapping.md`
📂 参照: `docs/easy_mode_suite.md`

やること:
1. `docs/term-mapping.md` を新規作成
2. 機能名 → 旧コード名 → クラス接頭辞 → ログタグ → タスクタイトル例の 5 列マトリクスを記述
3. 機能名 ↔ 機能 ID の対応表を 1 対 1 で定義（機能 ID は `interactive_writer` / `full_auto` / `gacha_pitch` / `quick_digest` / `producer_handoff` のスネークケース）

✅ 完了条件:
- `docs/term-mapping.md` が `docs/easy_mode_suite.md` からリンクされている
- 機能名 5 つすべてに ID が振られている

⚠️ 注意点: 機能 ID は後続ステップでクラス名・ログタグ・タスクタイトルに使うので、命名を途中で変更しない

---

## Step 2. `src/services/gacha_service.py` のロガータグ更新 🏷️ Gacha Pitch

**目的**: 機能名でログを絞り込めるようにする。

📂 編集: `src/services/gacha_service.py`

やること:
1. 1 行目に「Gacha Pitch」のロガータグを付与（`logger = logging.getLogger("gacha_pitch")`）
2. 既存の `logger.info` / `logger.warning` のメッセージ先頭に `[gacha-pitch]` を付ける（または logger 名でフィルタ可能にする）
3. 既存テスト `tests/unit/test_digest_service.py` 等が影響を受けないか確認

✅ 完了条件:
- `gacha_pitch` ロガーを経由したログが `[gacha-pitch]` プレフィックス付きで出力される
- `python -c "import src.services.gacha_service"` でインポートできる

⚠️ 注意点: 既存の log メッセージには `Plan generation failed` のような機能横断の文言が含まれるので、**既存のテスト用 assertion**（`caplog.records` の message 一致）があれば壊さない

---

## Step 3. `src/services/digest_service.py` のロガータグ更新 🏷️ Quick Digest

📂 編集: `src/services/digest_service.py`

やること:
1. ロガーを `logging.getLogger("quick_digest")` に変更
2. エラーログ（line 127: `Digest generation failed`）に `[quick-digest]` をプレフィックス化
3. `tests/unit/test_digest_service.py` を実行して挙動が変わっていないか確認

✅ 完了条件: `pytest tests/unit/test_digest_service.py` が緑

---

## Step 4. `src/services/promotion_service.py` のロガータグ更新 🏷️ Producer Handoff

📂 編集: `src/services/promotion_service.py`

やること:
1. ロガーを `logging.getLogger("producer_handoff")` に変更
2. 警告ログ（line 22）に `[producer-handoff]` をプレフィックス化
3. docstring に機能名 `Producer Handoff` を明記

✅ 完了条件: `python -c "import src.services.promotion_service"` でインポート成功

---

## Step 5. `src/backend/routers/easy_mode.py` のエンドポイント docstring に機能名追加 🏷️ 全機能

📂 編集: `src/backend/routers/easy_mode.py`

やること:
1. 各エンドポイント関数（`gacha_endpoint` / `digest_endpoint` / `promote_endpoint` / `generate_content`）の docstring 1 行目に機能名を追加
   - `"""3 案ガチャ企画生成 [Gacha Pitch]"""`
   - `"""ダイジェスト生成 [Quick Digest]"""`
   - `"""上級者モード昇格 [Producer Handoff]"""`
   - `"""章単位の対話型自動生成 [Interactive Writer]"""`
2. 既存の `tests/unit/test_easy_mode_router.py` が docstring を参照していないか確認

✅ 完了条件:
- `grep -n "\[.*Pitch\]\|\[.*Digest\]\|\[.*Handoff\]\|\[.*Writer\]" src/backend/routers/easy_mode.py` で 4 件ヒット

---

# Phase 2: critical バグ修正（2〜3日）

## Step 6. `Book` テーブルに `mode` カラム追加（マイグレーション） 🔴 🏷️ Producer Handoff

**目的**: `Producer Handoff` の本実装で必要。上級者モードへの昇格状態を永続化する先を作る。

📂 編集: `src/backend/database/models.py`
📂 新規: `alembic/versions/xxxx_add_book_mode.py`（Alembic マイグレーション）

やること:
1. `Book` モデルに `mode = Column(String(20), default="easy", nullable=False)` を追加（`models.py:38` 付近）
2. Alembic でマイグレーションを生成
3. `init_db()` で `Base.metadata.create_all()` する経路（テスト）では新カラムが自動追加されることを確認

✅ 完了条件:
- `pytest tests/test_health.py` が緑
- `alembic upgrade head` がエラーなく完了
- 既存テスト `tests/test_easy_mode_api.py` が緑

⚠️ 注意点:
- 既存データの `mode` は **NULL → 'easy'** にバックフィルする
- `models.py` の他のテーブルと同様に `server_default` を使う

---

## Step 7. `EasyModeDraft` テーブル新設（gacha/digest の永続化先） 🔴 🏷️ Gacha Pitch / Quick Digest

**目的**: `_GACHA_CACHE` / `_BOOK_STORE` のリプレース先。ガチャ結果と中間生成物を DB に保存する。

📂 編集: `src/backend/database/models.py`

やること:
1. 以下のモデル `EasyModeDraft` を `models.py` に追加:
   ```python
   class EasyModeDraft(Base):
       __tablename__ = "easy_mode_drafts"
       id = Column(Integer, primary_key=True, autoincrement=True)
       draft_id = Column(String(64), unique=True, nullable=False, index=True)
       kind = Column(String(20), nullable=False)  # "gacha" | "digest"
       payload_json = Column(Text, nullable=False, default="{}")
       parent_draft_id = Column(String(64), nullable=True, index=True)
       book_id = Column(String(64), nullable=True, index=True)
       created_at = Column(DateTime, server_default=func.now())
       updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
   ```
2. Alembic でマイグレーションを生成
3. `init_db()` でテーブルが作成されることを確認

✅ 完了条件:
- `python -c "from src.backend.database.models import EasyModeDraft; print(EasyModeDraft.__tablename__)"` で `easy_mode_drafts` が出力
- `tests/test_health.py` が緑

---

## Step 8. `EasyModeDraftRepository` 実装 🔴 🏷️ Gacha Pitch / Quick Digest / Producer Handoff

📂 新規: `src/backend/database/repositories/easy_mode_draft_repository.py`

やること:
1. クラス `EasyModeDraftRepository` を作成
2. メソッド:
   - `async def save_gacha_plans(self, request_id: str, plans_json: dict) -> None`
   - `async def load_gacha_plans(self, request_id: str) -> dict | None`
   - `async def save_digest(self, book_id: str, parent_request_id: str, digest_json: dict) -> None`
   - `async def load_digest(self, book_id: str) -> dict | None`
3. 内部で `DatabaseManager.get_session()` を使い、`session.begin()` でトランザクション管理
4. 例外時は `None` または raise（呼び出し側に任せる）

✅ 完了条件:
- `tests/unit/test_repository.py` の新テスト 5 件（save/load/round-trip/None ケース）が緑
- `pytest --cov=src/backend/database/repositories --cov-fail-under=80` が緑

⚠️ 注意点: 既存 `BookRepository` のスタイル（`session` 引数を取る / 取らない）に合わせる

---

## Step 9. `GachaService` の `_GACHA_CACHE` → DB 永続化への置換 🔴 🏷️ Gacha Pitch

📂 編集: `src/services/gacha_service.py`
📂 編集: `src/backend/database/repositories/__init__.py`（エクスポート追加）

やること:
1. `GachaService.__init__` に `repo: EasyModeDraftRepository | None = None` パラメータ追加
2. `_GACHA_CACHE[request_id] = ...` を `await self.repo.save_gacha_plans(request_id, response.model_dump())` に置換
3. 既存テスト `tests/unit/test_digest_service.py` 等が `_GACHA_CACHE` を直接参照していないか確認（参照していたら `repo` 引数経由に変更）
4. `from src.backend.database.repositories.easy_mode_draft_repository import EasyModeDraftRepository` を遅延 import（循環 import 回避）

✅ 完了条件:
- ガチャ生成 → `easy_mode_drafts` テーブルに行ができる（手動確認手順を docstring に残す）
- 既存テスト全件緑

⚠️ 注意点: `_GACHA_CACHE` を **完全削除** せず、非推奨の薄いラッパー（`DeprecationWarning`）として残すと安全

---

## Step 10. `DigestService` / `PromotionService` の永続化対応 🔴 🏷️ Quick Digest / Producer Handoff

📂 編集: `src/services/digest_service.py`
📂 編集: `src/services/promotion_service.py`

やること:
1. `DigestService.__init__` に `repo: EasyModeDraftRepository | None = None` 追加
2. `_BOOK_STORE[book_id] = ...` を `await self.repo.save_digest(book_id, request_id, response.model_dump())` に置換
3. `PromotionService.promote_book` を `async` のまま、DB 永続化版に書き換え:
   - 存在しない `book_id` を受け取ったら `ValueError` を raise（404 相当を router で処理）
   - 存在する場合は `Book.mode = "advanced"` に更新（Step 6 で追加したカラム）
4. router 側（`src/backend/routers/easy_mode.py:289-293`）で `try/except ValueError` を追加し 404 を返す

✅ 完了条件:
- `/easy_mode/promote` に存在しない `book_id` を渡すと **404** が返る
- 正常系で `books.mode` が `easy → advanced` に更新される（DB で目視確認手順を docstring に残す）
- 既存テスト `tests/test_easy_mode_api.py` が緑

⚠️ 注意点: `PromotionResponse` の `redirect_url` / `state_token` の生成ロジックは維持

---

# Phase 3: ヘルスチェック・高優先度修正（3〜5日）

## Step 11. `health.py` の `check_database` 実 ping 化 🟠 🔴

📂 編集: `src/backend/observability/health.py`

やること:
1. `check_database()` を以下のように変更:
   ```python
   async def check_database() -> dict:
       try:
           from src.backend.database.core import DatabaseManager
           mgr = DatabaseManager(os.environ.get("DATABASE_URL", ""))
           async with mgr.get_session() as s:
               await s.execute(text("SELECT 1"))
           return {"status": "ok", "type": "sqlite"}
       except Exception as e:
           return {"status": "error", "code": "DB_UNAVAILABLE"}
   ```
2. `build_health_payload()` を `async def` に変更し、`await check_database()` / `await check_huey()` を使う
3. 呼び出し側（router 想定）を `asyncio.run` またはバックグラウンドタスクに切り替え
4. タイムアウト 5 秒を設定（`asyncio.wait_for`）

✅ 完了条件:
- DB を停止した状態で `GET /health` が `status: degraded` を返す
- 通常状態で `status: ok`
- `tests/test_health.py` が新仕様に合わせて緑

⚠️ 注意点: `e.str(e)` をレスポンスに含めない（情報漏洩防止）

---

## Step 12. `check_huey` 実 ping 化 🟠 🔴

📂 編集: `src/backend/observability/health.py`

やること:
1. `check_huey()` を Huey ワーカーへの生存確認付きに変更
2. ワーカーが起動していない場合は `status: error, code: HUEY_DOWN` を返す
3. ハングしないように `asyncio.wait_for(huey.ping(), timeout=3.0)` でラップ

✅ 完了条件: Step 11 と同じテスト方針（停止/正常系）

---

## Step 13. `Book.mode` を活用した `PromotionService` の本実装 🟠 🏷️ Producer Handoff

📂 編集: `src/services/promotion_service.py`

やること:
1. Step 10 で仮実装した PromotionService を `Book` テーブル永続化版に完全移行
2. `redirect_url` を `f"/advanced/{book.id}"` （`book.id` は int 主キー）に変更
3. `state_token` の生成を `secrets.token_urlsafe(16)` に変更（UUID よりも短く安全なランダム）
4. `_BOOK_STORE` の参照を完全削除

✅ 完了条件:
- `tests/unit/test_easy_mode_router.py` の `/promote` テストが緑
- 旧 `_BOOK_STORE` への参照がコードベースから 0 件

---

## Step 14. `src/models/book.py` の re-export 解消 🟠

📂 削除: `src/models/book.py`
📂 編集: `src/models/__init__.py`

やること:
1. `src/models/book.py` の削除
2. `src/models/__init__.py:8` の `from src.models.book import *` を削除
3. コードベース内で `from src.models.book import` を `from src.backend.database.models import` に置換（grep 検索 → 全置換）

✅ 完了条件:
- `grep -rn "from src.models.book" src tests` が 0 件
- `pytest tests/` が緑

⚠️ 注意点: 外部ユーザーが import している可能性を考慮し、CHANGELOG に breaking change を明記

---

## Step 15. `src/models/chunk.py` の re-export 解消 🟠

📂 削除: `src/models/chunk.py`
📂 編集: `src/models/__init__.py`

やること:
1. `src/models/chunk.py` の削除
2. `src/models/__init__.py:10` の `from src.models.chunk import *` を削除
3. コードベース内で `from src.models.chunk import` を `from src.infrastructure.database.models.chunk import` に置換

✅ 完了条件: Step 14 と同じ

---

## Step 16. `src/models/__init__.py` の `import *` 解消 🟠

📂 編集: `src/models/__init__.py`

やること:
1. `import *` を全て明示的 import に置換（22 ファイル）
2. `__all__` を各モジュールに明記（既にある場合は尊重）
3. `mypy` で `disallow_untyped_defs = true` を一時的に有効化してチェック

✅ 完了条件:
- `ruff check src/models/__init__.py` が緑
- `grep "^from .* import \\*" src/models/__init__.py` が 0 件

---

## Step 17. `src/models/easy_mode_schemas.py` の循環 import 解消 🟠

📂 編集: `src/services/digest_service.py`
📂 編集: `src/services/gacha_service.py`
📂 編集: `src/services/promotion_service.py`
📂 削除 or 縮小: `src/models/easy_mode_schemas.py`

やること:
1. サービス層 3 ファイル内の `from src.models.easy_mode_schemas import ...` を `from src.domain.entities.easy_mode import ...` に置換
2. `src/models/easy_mode_schemas.py` を `from src.domain.entities.easy_mode import *` の中継だけにしているなら削除
3. `src/models/__init__.py:6` 周辺の該当 import があれば `domain` 側に変更

✅ 完了条件:
- `grep -rn "from src.models.easy_mode_schemas" src tests` が 0 件、または deprecation コメント付きのみ
- `pytest tests/` 全件緑

---

# Phase 4: テスト強化（2〜3日）

## Step 18. `tests/conftest.py` の DB フィクスチャ拡張 🟠

📂 編集: `tests/conftest.py`

やること:
1. `real_db_manager` フィクスチャに `EasyModeDraft` テーブルの自動クリーンアップを追加（`yield` 後に `DELETE FROM easy_mode_drafts`）
2. `metrics` フィクスチャを新規追加（`autouse=True` で `health.metrics.reset_for_testing()`）
3. `llm_mock` フィクスチャを `tests/fixtures/llm_verbose_fixture.py` から取り込み

✅ 完了条件:
- `pytest tests/test_health.py` が緑（フィクスチャの相互作用確認）
- 並列実行 (`pytest -n 4`) でメトリクスが漏れない

---

## Step 19. `tests/test_illustration_agent.py` のアサーション強化 🟠

📂 編集: `tests/test_illustration_agent.py`

やること:
1. 3 つのテストすべてに `mock_service.generate.assert_called_once()` を追加
2. `mock_llm.generate` の呼び出し引数（`prompt` フィールド）を `assert_called_once_with(...)` で検証
3. `SafetyLevel.R15_CONTENT` のテストで `prompt.lower()` に `"r15"` が **含まれる** ことを直接 assert（弱い `any(...)` を排除）
4. `test_illustration_agent_auto_model_resolves` で `result["result"].model_used` の値を完全一致 assert

✅ 完了条件:
- `pytest tests/test_illustration_agent.py` が緑
- いずれかの assertion を壊すように意図的に `IllustrationAgent` を変更すると、テストが赤くなる（手動確認）

---

## Step 20. `tests/unit/test_digest_service.py` のリポジトリ注入対応 🟠

📂 編集: `tests/unit/test_digest_service.py`
📂 新規: `tests/unit/test_quick_digest_service.py`（必要に応じて）

やること:
1. Step 9-10 の永続化対応後、`process_chapter` / `generate_suggestions` 以外の関数（`DigestService.generate_digest`）のテストを追加
2. `EasyModeDraftRepository` のモックを使った「DB 失敗時の挙動」テストを追加
3. `asyncio.gather` の例外発生時に `EasyModeDraft` に行が **作られる** ことを確認

✅ 完了条件:
- `pytest tests/unit/test_digest_service.py tests/unit/test_quick_digest_service.py` が緑
- 新規テストのカバレッジが `DigestService` クラスの 80% 以上

---

## Step 21. `tests/test_health.py` の実体化 🟠

📂 編集: `tests/test_health.py`

やること:
1. Step 11-12 で実装した実 ping に合わせてテストを更新
2. 「DB 停止状態」を `monkeypatch` で再現（`DatabaseManager.get_session` を `AsyncMock(side_effect=Exception)`）
3. 「Huey 停止状態」も同様に再現
4. タイムアウト境界値テスト（2.9 秒、3.1 秒）を追加

✅ 完了条件:
- `pytest tests/test_health.py -v` で全ケース緑
- カバレッジ 100%

---

## Step 22. `tests/test_erotic_workflow.py` の回帰確認 🟡

📂 編集: `tests/test_erotic_workflow.py`

やること:
1. 既存のテストが期待する `SCENE_TYPES` の長さを確認
2. Step 29 のファイル分割後にも既存テストが緑か確認
3. 必要なら fixture で `SCENE_TYPES` を import する形に修正

✅ 完了条件: `pytest tests/test_erotic_workflow.py tests/test_continuity_tracker.py tests/test_scene_continuity_tracker.py` が緑

---

# Phase 5: medium / low 改善（3〜5日）

## Step 23. `DatabaseManager.execute` の DeprecationWarning 整備 🟡

📂 編集: `src/backend/database/core.py`

やること:
1. `execute()` / `fetch_one()` / `fetch_all()` の `isinstance(sql, str)` 警告を **モジュールロード時 1 回** に変更（毎回発火させない）
2. 代わりに `DatabaseManager` クラス内に `__init_subclass__` 風のフラグ `_warned_about_str_sql = False` を追加
3. `logger.warning` レベルを `logger.debug` に降格（本番ログを汚さない）

✅ 完了条件:
- 既存テストの `pytest -W error::DeprecationWarning` モードでも緑
- ログレベル INFO 運用で `DatabaseManager.execute called` が出力されない

⚠️ 注意点: 警告の **完全削除** はしない（呼び出し側が気付けるように）

---

## Step 24. `src/backend/tasks/__init__.py` の outbox ループ堅牢化 🟡

📂 編集: `src/backend/tasks/__init__.py`

やること:
1. 1 イベント失敗時の挙動を `continue` に統一（現状確認）
2. ループ全体を `try/except Exception` で包み、致命的でないエラーは警告ログ
3. メトリクス `outbox_events_processed` / `outbox_events_failed` を追加

✅ 完了条件:
- 1 イベントを意図的に失敗させて `outbox_events_failed` が増えることを確認
- 他のイベントは継続処理される

---

## Step 25. `erotic_integrity.py` のタイポ修正 🟡

📂 編集: `src/agents/erotic_integrity.py`

やること:
1. `check_check_methods` → `check_methods` にリネーム
2. すべての `check_*` メソッドを `SceneContinuityTracker` クラス先頭に移動（IDE 解決性能向上）
3. ログメッセージを `[整合性] {character_name} ep{ep_num}: ...` で統一

✅ 完了条件:
- `grep "check_check_methods" src/` が 0 件
- `pytest tests/test_continuity_tracker.py tests/test_scene_continuity_tracker.py` が緑

---

## Step 26. `erotic_integrity.py` の db_path ハードコード解消 🟡

📂 編集: `src/agents/erotic_integrity.py`

やること:
1. クラス `__init__` の `db_path: str = "storage/db/kaku_hegemony_v2.db"` を **必須引数化**（デフォルト削除）
2. 既存呼び出し箇所を `grep -rn "SceneContinuityTracker(" src tests` で洗い出し、すべて `db_path=...` を明示
3. `db_path` のバリデーション（`Path(db_path).resolve()` が `storage/db/` 配下か確認）を追加

✅ 完了条件:
- `grep "kaku_hegemony_v2" src/` が 0 件
- デフォルト値なしで呼ばれた場合に `TypeError` で気付ける

⚠️ 注意点: `src/agents/erotic_integrity.py:1446` の同名デフォルトも同様に解消

---

## Step 27. `pyproject.toml` の依存ピニング 🟡

📂 編集: `pyproject.toml`

やること:
1. 全依存を `~=` 形式に変更（`fastapi>=0.110` → `fastapi~=0.110`）
2. `psycopg2-binary` を削除（コードベースで未使用、README との整合）
3. `pgvector` を `HAS_PGVECTOR=False` なら依存から除外
4. `pytest-mock` / `freezegun` を dev グループに追加

✅ 完了条件:
- `pip install -e .` がエラーなく完了
- `requirements.lock` を `pip-tools` で生成し、コミット

---

## Step 28. `pyproject.toml` の `addopts` 重複解消 🟢

📂 編集: `pyproject.toml`

やること:
1. `[tool.pytest.ini_options].addopts` から `--cov-fail-under=80` を削除
2. `[tool.coverage.report].fail_under = 80` だけ残す
3. 既存の CI が緑のままか確認

✅ 完了条件:
- `grep "cov-fail-under" pyproject.toml` が 0 件
- `pytest` 実行時の help に `--cov-fail-under` が出ない

---

# Phase 6: 大型リファクタ（5〜7日）

## Step 29. `erotic_integrity.py` の定数重複統合 🟠

📂 編集: `src/agents/erotic_integrity.py`

やること:
1. `SCENE_TYPES` の 5 箇所再定義を 1 箇所に統合（line 15, 29, 999, 1093, 1187, 1281）
2. `COMBAT_KEYWORDS` / `CONVERSATION_KEYWORDS` / `EXPLORATION_KEYWORDS` / `TRAVEL_KEYWORDS` / `REST_KEYWORDS` / `MONOLOGUE_KEYWORDS` を `Final[tuple[str, ...]]` で 1 箇所に統合
3. 統合は **マージせず、最初（line 15-164）の版を採用**（他の定義は削除）

✅ 完了条件:
- `grep "SCENE_TYPES = \\[" src/agents/erotic_integrity.py` が 1 件
- `grep "COMBAT_KEYWORDS = \\[" src/agents/erotic_integrity.py` が 1 件
- 既存テスト全件緑

⚠️ 注意点: 削除前に `tests/test_scene_continuity_tracker.py` でどの版を期待しているか確認

---

## Step 30. `erotic_integrity.py` のファイル分割 🟠

📂 新規: `src/agents/erotic_integrity/__init__.py`
📂 新規: `src/agents/erotic_integrity/constants.py`
📂 新規: `src/agents/erotic_integrity/scene_continuity.py`
📂 新規: `src/agents/erotic_integrity/continuity.py`
📂 新規: `src/agents/erotic_integrity/quality.py`
📂 削除: `src/agents/erotic_integrity.py`

やること:
1. `mkdir src/agents/erotic_integrity`
2. 既存 `erotic_integrity.py` の 1600 行を 4 ファイルに分割
   - `constants.py`: すべての定数（Step 29 の統合版を移植）
   - `scene_continuity.py`: `SceneContinuityTracker` クラス
   - `continuity.py`: `ContinuityTracker` クラス
   - `quality.py`: `EroticQualityScorer` 系
3. `__init__.py` で re-export して後方互換を保つ
4. 元ファイル `erotic_integrity.py` を削除
5. すべての import 経路を `from src.agents.erotic_integrity import ...` に置換

✅ 完了条件:
- `wc -l src/agents/erotic_integrity/*.py` で各ファイル 400 行以下
- 既存テスト全件緑（`pytest tests/test_continuity_tracker.py tests/test_scene_continuity_tracker.py`）
- `grep "from src.agents.erotic_integrity import" src tests` で旧パス参照 0 件

⚠️ 注意点: 段階的移行のため、`__init__.py` 経由の re-export を必ず用意

---

# 進捗トラッキング

各ステップの完了時にこのチェックリストを更新する。

```
Phase 1:
[x] Step 1. docs/term-mapping.md       ✅ (2026-09-01 完了)
[x] Step 2. gacha_service.py ロガータグ  ✅ (2026-09-01 完了)
[x] Step 3. digest_service.py ロガータグ  ✅ (2026-09-01 完了)
[x] Step 4. promotion_service.py ロガータグ ✅ (2026-09-01 完了)
[x] Step 5. routers/easy_mode.py docstring ✅ (2026-09-01 完了)

Phase 2:
[ ] Step 6.  Book.mode カラム追加
[ ] Step 7.  EasyModeDraft テーブル新設
[ ] Step 8.  EasyModeDraftRepository
[ ] Step 9.  GachaService 永続化
[ ] Step 10. DigestService / PromotionService 永続化

Phase 3:
[ ] Step 11. check_database 実 ping
[ ] Step 12. check_huey 実 ping
[ ] Step 13. PromotionService 本実装
[ ] Step 14. src/models/book.py 削除
[ ] Step 15. src/models/chunk.py 削除
[ ] Step 16. import * 解消
[ ] Step 17. easy_mode_schemas.py 循環解消

Phase 4:
[ ] Step 18. conftest.py 拡張
[ ] Step 19. test_illustration_agent 強化
[ ] Step 20. test_digest_service 拡張
[ ] Step 21. test_health 実体化
[ ] Step 22. test_erotic_workflow 回帰

Phase 5:
[ ] Step 23. DeprecationWarning 整備
[ ] Step 24. outbox ループ堅牢化
[ ] Step 25. typo 修正
[ ] Step 26. db_path ハードコード解消
[ ] Step 27. 依存ピニング
[ ] Step 28. addopts 重複解消

Phase 6:
[ ] Step 29. 定数重複統合
[ ] Step 30. ファイル分割
```

---

# 各ステップの所要時間見積もり

| Phase | ステップ数 | 累積時間（推定） |
|:--|:--|:--|
| Phase 1 | 5 | 約 2〜4 時間 |
| Phase 2 | 5 | 約 6〜10 時間（マイグレーション・テスト含む） |
| Phase 3 | 7 | 約 8〜14 時間 |
| Phase 4 | 5 | 約 4〜8 時間 |
| Phase 5 | 6 | 約 4〜8 時間 |
| Phase 6 | 2 | 約 8〜16 時間（リファクタ） |
| **合計** | **30** | **約 32〜60 時間** |

低性能な LLM でも 1 ステップ 30〜90 分で実装可能な粒度。

---

# ブランチ戦略の推奨

各 Phase ごとに 1 つの長期ブランチ、Phase 内のステップは細かくコミットする:

```
main
└── feature/easy-mode-suite-improvements
    ├── phase-1-naming-docs        (Step 1〜5)
    ├── phase-2-critical-fixes     (Step 6〜10)
    ├── phase-3-architecture       (Step 11〜17)
    ├── phase-4-test-strengthen     (Step 18〜22)
    ├── phase-5-medium-low         (Step 23〜28)
    └── phase-6-refactor           (Step 29〜30)
```

各 Phase ブランチで PR を作成 → レビュー → マージ。次の Phase は前の Phase マージ後に切る。

---

# ロールバック戦略

| Phase | ロールバック難易度 | 備考 |
|:--|:--|:--|
| Phase 1 | 极易（doc/log のみ） | 即時リバート可 |
| Phase 2 | 难（DB マイグレーション） | ダウンマイグレーション必須 |
| Phase 3 | 中 | re-export 削除は影響大、段階的に |
| Phase 4 | 极易 | テスト追加のみ |
| Phase 5 | 易 | 独立した修正が多い |
| Phase 6 | 中 | re-export 維持で後方互換 |

Phase 2 と Phase 6 は **フィーチャーフラグ** の併用を推奨:
- Phase 2: `EASY_MODE_DRAFT_DB_ENABLED` env フラグで新旧切替
- Phase 6: `EROTIC_INTEGRITY_LEGACY_PATH=True` で旧ファイル残置

---

# 関連ドキュメント

- [Easy Mode Suite 概要](./easy_mode_suite.md)
- [API リファレンス](./api.md)
- [CHANGELOG](../CHANGELOG.md)
- [README](../README.md)
- コードレビュー報告書（2026-09-01、内部メモ）

---

# 改訂履歴

| 日付 | 版 | 変更内容 |
|:--|:--|:--|
| 2026-09-01 | 1.0.0 | 初版作成。30 ステップに分割。Easy Mode Suite 命名整理と 2026-09-01 コードレビューを反映 |
| 2026-09-01 | 1.1.0 | Phase 1 完了 (Step 1-5)。docs/term-mapping.md 新規作成。gacha/digest/promotion_service のログタグ更新。routers/easy_mode.py docstring に機能名付与 |
