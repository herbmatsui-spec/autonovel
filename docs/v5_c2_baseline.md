# AutoNovel v5.2.0 - C2 Baseline Record
- 採取日時: 2026-09-26 11:51 JST
- 基準コミット: C1完了後

## Part 1: 現状調査

### Step 1-2: `detailed_blueprint` の利用状況
- `src/backend/routers/plots.py:277`: ウィザードの伏線メモを格納（誤用・混同の元）
- `src/infrastructure/repositories/plot.py:145`: 各話の設計図本文を格納（本来の用途）
- 誤用は `plots.py:277` の1件のみと確定。

### Step 3: 既存データの汚染度
- `autonovel.db` の `foreshadowings` テーブル: 0件
- 既存DBの汚染は実質なし。

### Step 4: `DbForeshadowingRepository` の未定義スコープ
- `foreshadowing_repo.py` において `ForeshadowingScope` が未 import。呼び出し時に NameError の状態。

### Step 5: `UnitOfWork` の伏線リポジトリ
- `UnitOfWork.foreshadowings` プロパティの配線状況: 現在配線完了済み。

### Step 6: 関連テストのベースライン
- `tests/unit/test_v5_foreshadowing_promotion_sync.py`: 1 passed
- `tests/unit/services/test_foreshadowing_contract_service.py`: 4 passed