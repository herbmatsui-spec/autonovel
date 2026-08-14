# タスクキュー（Huey + Redis）とベクトルストア（ChromaDB）の微調整実装計画書

## 概要
低性能なLLMでも実装可能なよう、12の小さなステップに分割。各ステップは独立してテスト可能で、前のステップの成果物を前提としない設計。

---

## Step 1: 優先度キュー用の Huey 設定追加
**目的**: タスクに優先度を持たせる

### 作業
1. `src/backend/tasks.py` に `PriorityHuey` クラスを作成
2. `huey = PriorityHuey(...)` に差し替え
3. タスクデコレータに `priority` 引数を追加

### 確認
```bash
python -c "from src.backend.tasks import huey; print(type(huey))"
```

---

## Step 2: タスク投入時に優先度を指定するヘルパー関数作成
**目的**: 呼び出し側から優先度を指定しやすくする

### 作業
1. `src/backend/task_helpers.py` に `enqueue_with_priority(task_func, *args, priority=0, **kwargs)` を追加
2. 内部で `task_func.schedule(args=args, kwargs=kwargs, priority=priority)` を呼ぶ

### 確認
```bash
python -c "from src.backend.task_helpers import enqueue_with_priority; help(enqueue_with_priority)"
```

---

## Step 3: デッドレターキュー（DLQ）用の失敗タスクテーブル作成
**目的**: 失敗タスクを永続化して後で調査可能にする

### 作業
1. `alembic` でマイグレーション作成: `alembic revision --autogenerate -m "add dead_letter_queue table"`
2. `src/backend/models.py` に `DeadLetterQueue` モデル追加（id, task_name, payload, error, retry_count, created_at）
3. `alembic upgrade head` 実行

### 確認
```bash
alembic current
python -c "from src.backend.models import DeadLetterQueue; print(DeadLetterQueue.__tablename__)"
```

---

## Step 4: タスク失敗時の DLQ 登録フック実装
**目的**: 自動的に失敗タスクを DLQ に保存

### 作業
1. `src/backend/tasks.py` に `on_failure` シグナルハンドラ追加
2. ハンドラ内で `DeadLetterQueue.create(...)` を実行
3. リトライ回数を `task.retries` から取得して記録

### 確認
```bash
python -c "
from src.backend.tasks import huey
from src.backend.models import DeadLetterQueue
print('signals registered:', huey.signal_names)
"
```

---

## Step 5: DLQ 管理用 CLI コマンド作成
**目的**: 失敗タスクを一覧・再投入・削除できるようにする

### 作業
1. `src/backend/scripts/manage_dlq.py` 作成
2. コマンド: `list`, `retry <id>`, `delete <id>`, `clear`
3. `retry` は元のタスクを再度 `enqueue_with_priority` で投入

### 確認
```bash
python -m src.backend.scripts.manage_dlq list
```

---

## Step 6: タスクタイムアウト監視スクリプト作成
**目的**: 長時間実行タスクを検知して強制終了

### 作業
1. `src/backend/scripts/watchdog.py` 作成
2. Huey の `result(store=True)` で実行時間を監視
3. 閾値（環境変数 `TASK_TIMEOUT_SECONDS`、デフォルト 300 秒）超過で `task.revoke()` 呼び出し
4. 失敗時は DLQ に記録

### 確認
```bash
TASK_TIMEOUT_SECONDS=10 python -m src.backend.scripts.watchdog --once
```

---

## Step 7: Prometheus メトリクスにキュー待ち時間・処理時間を追加
**目的**: ボトルネックを可視化

### 作業
1. `src/backend/metrics.py` に `huey_queue_wait_seconds`, `huey_task_duration_seconds` ヒストグラム追加
2. `task_helpers.py` の `enqueue_with_priority` で投入時刻を記録
3. `on_start` / `on_finish` シグナルで待ち時間・処理時間を計測してメトリクスに記録

### 確認
```bash
curl -s http://localhost:8200/metrics | grep huey_
```

---

## Step 8: 開発環境用インメモリ Huey バックエンド切り替え
**目的**: Redis 不要でローカル開発可能にする

### 作業
1. `src/backend/tasks.py` で環境変数 `HUEY_BACKEND` 判定（`redis` | `memory`）
2. `memory` の場合は `huey = MemoryHuey(...)` を使用
3. `.env.example` に `HUEY_BACKEND=memory` 追加

### 確認
```bash
HUEY_BACKEND=memory python -c "from src.backend.tasks import huey; print(type(huey).__name__)"
```

---

## Step 9: ChromaDB コレクションにスキーマバージョンメタデータ追加
**目的**: 将来のスキーマ変更に対応

### 作業
1. `src/backend/vector_store.py` のコレクション作成時に `metadata={"schema_version": "1"}` を指定
2. 既存コレクションには `collection.modify(metadata={"schema_version": "1"})` 実行
3. バージョン定数を `VECTOR_SCHEMA_VERSION = "1"` として定義

### 確認
```bash
python -c "
from src.backend.vector_store import get_collection
c = get_collection()
print(c.metadata)
"
```

---

## Step 10: 埋め込み計算の LRU キャッシュ実装
**目的**: 同一テキストの埋め込み再計算を防止

### 作業
1. `src/backend/embedding_cache.py` 作成
2. `cachetools.LRUCache(maxsize=1000)` を使用
3. キー: `hash(text + model_name)`、値: 埋め込みベクトル
4. `get_embedding(text)` 関数でキャッシュ優先、なければ API 呼び出しして保存

### 確認
```bash
python -c "
from src.backend.embedding_cache import get_embedding
import time
t1 = time.time(); v1 = get_embedding('test'); t2 = time.time()
v2 = get_embedding('test'); t3 = time.time()
print(f'1st: {t2-t1:.3f}s, 2nd: {t3-t2:.3f}s, same: {v1 is v2}')
"
```

---

## Step 11: ChromaDB バッチ upsert ヘルパー実装
**目的**: 書き込みスループット向上

### 作業
1. `src/backend/vector_store.py` に `batch_upsert(documents, metadatas, ids, batch_size=100)` 追加
2. 内部で `chunks = [list[i:i+batch_size]...]` 分割し、ループで `collection.upsert()` 呼び出し
3. 進捗ログ出力（件数/合計）

### 確認
```bash
python -c "
from src.backend.vector_store import batch_upsert
batch_upsert(['a','b','c'], [{}]*3, ['1','2','3'], batch_size=2)
print('done')
"
```

---

## Step 12: ChromaDB バックアップ・リストア手順書作成
**目的**: 災害復旧手順を整備

### 作業
1. `docs/operations/chromadb_backup.md` 作成
2. 手順:
   - バックアップ: `tar -czf chromadb_backup_$(date +%F).tar.gz chroma_db/`
   - リストア: サービス停止 → 解凍 → サービス起動
   - 定期実行: cron または GitHub Actions 例を記載
3. `README.md` の「運用」セクションにリンク追加

### 確認
```bash
ls -la docs/operations/chromadb_backup.md
```

---

## 実装順序の依存関係

```
Step 1 → Step 2 → Step 4 → Step 5
    ↓
Step 3 ──────────────────────→ Step 5
    ↓
Step 6 (独立)
    ↓
Step 7 (Step 1,2 完了後)
    ↓
Step 8 (独立)
    ↓
Step 9 → Step 10 → Step 11 (独立)
    ↓
Step 12 (独立)
```

---

## 進捗管理

| Step | 状態 | 担当 | 備考 |
|------|------|------|------|
| 1 | ☐ 未着手 | | |
| 2 | ☐ 未着手 | | |
| 3 | ☐ 未着手 | | |
| 4 | ☐ 未着手 | | |
| 5 | ☐ 未着手 | | |
| 6 | ☐ 未着手 | | |
| 7 | ☐ 未着手 | | |
| 8 | ☐ 未着手 | | |
| 9 | ☐ 未着手 | | |
| 10 | ☐ 未着手 | | |
| 11 | ☐ 未着手 | | |
| 12 | ☐ 未着手 | | |

---

## 注意事項
- 各ステップは **単一ファイルの変更** または **単一機能の追加** に限定
- テストは各ステップ完了時に手動確認コマンドを実行
- 既存テストが壊れないことを `pytest -x` で確認してから次へ進む