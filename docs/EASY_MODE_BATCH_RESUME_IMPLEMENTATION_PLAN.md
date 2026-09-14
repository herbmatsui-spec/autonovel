# 簡易モード・バッチ/再開機能 実装計画書

**目的**: `start_ep` / `end_ep` パラメータを追加し、50話・10万字を複数バッチに分割実行・再開可能にする

---

## 前提・制約
- 既存: `EpisodePipeline.run(start_ep, end_ep)` は範囲指定対応済み
- 既存: `ContextCompressionPipeline.compress()` で前話コンテキスト圧縮可能
- 対象ファイル: 4ファイルのみ（Workflow, Router, Repository, Test）
- 低性能LLMでも迷わず実装できるよう、各ステップを「単一ファイル・単一操作」に分割

---

## ステップ一覧（全12ステップ）

### Step 1: EasyModeWorkflow にパラメータ追加
**ファイル**: `src/backend/workflows/easy_mode_workflow.py`  
**操作**: `execute()` メソッドのシグネチャに `start_ep: int = 1`, `end_ep: int | None = None` を追加  
**変更箇所**: 1箇所（メソッド定義行）  
**確認**: 型ヒント込みで正しく追加できているか

```python
# 変更前
async def execute(self, input_data: EasyModeInput) -> EasyModeOutput:

# 変更後
async def execute(self, input_data: EasyModeInput, start_ep: int = 1, end_ep: int | None = None) -> EasyModeOutput:
```

---

### Step 2: EasyModeWorkflow 内でパイプラインへパラメータ転送
**ファイル**: `src/backend/workflows/easy_mode_workflow.py`  
**操作**: `EpisodePipeline.run()` 呼び出し箇所に `start_ep=start_ep, end_ep=end_ep` を追加  
**変更箇所**: 1箇所（`run()` 呼び出し行）  
**確認**: 引数名が合致しているか

```python
# 変更前
result = await pipeline.run(input_data)

# 変更後
result = await pipeline.run(input_data, start_ep=start_ep, end_ep=end_ep)
```

---

### Step 3: EasyModeInput スキーマにフィールド追加
**ファイル**: `src/backend/workflows/easy_mode_workflow.py` （または共通スキーマファイル）  
**操作**: Pydantic モデル `EasyModeInput` に `start_ep: int = Field(default=1, ge=1, le=50)`, `end_ep: int | None = Field(default=None, ge=1, le=50)` を追加  
**変更箇所**: 1箇所（クラス定義内）  
**確認**: バリデーション範囲が `target_episodes` 上限(50)と一致しているか

---

### Step 4: Router エンドポイントにクエリパラメータ追加
**ファイル**: `src/backend/routers/easy_mode.py`  
**操作**: `generate_easy_mode()` 関数の引数に `start_ep: int = Query(1, ge=1, le=50)`, `end_ep: int | None = Query(None, ge=1, le=50)` を追加  
**変更箇所**: 1箇所（関数シグネチャ）  
**確認**: FastAPI の `Query` インポート済みか、未なら追加

---

### Step 5: Router からワークフローへパラメータ渡す
**ファイル**: `src/backend/routers/easy_mode.py`  
**操作**: `workflow.execute()` 呼び出しに `start_ep=start_ep, end_ep=end_ep` を追加  
**変更箇所**: 1箇所（呼び出し行）  
**確認**: キーワード引数で渡しているか

```python
# 変更前
output = await workflow.execute(input_data)

# 変更後
output = await workflow.execute(input_data, start_ep=start_ep, end_ep=end_ep)
```

---

### Step 6: 完了済みエピソード判定ロジック追加
**ファイル**: `src/backend/workflows/easy_mode_workflow.py`  
**操作**: `execute()` 先頭で、DB/ストレージから「既に生成済みの最大エピソード番号」を取得し、`start_ep` が指定されていない場合は `max_completed + 1` をデフォルトにする  
**変更箇所**: 1箇所（メソッド冒頭）  
**確認**: 取得処理が例外安全（レコードなし時は 0 返す）になっているか

```python
# 追加ロジック（擬似コード）
if start_ep == 1:  # デフォルト値の場合のみ自動判定
    max_completed = await self._get_max_completed_episode(input_data.project_id)
    start_ep = max_completed + 1
```

---

### Step 7: チェックポイント保存メソッド実装
**ファイル**: `src/backend/workflows/easy_mode_workflow.py`  
**操作**: クラスに `_save_checkpoint(project_id, last_completed_ep, compressed_context)` メソッド追加  
**内容**: JSON または DB に `{project_id, last_completed_ep, compressed_context, updated_at}` を保存  
**変更箇所**: 1箇所（クラス内に新規メソッド追加）  
**確認**: 非同期メソッド (`async def`) になっているか

---

### Step 8: エピソード生成ループ内でチェックポイント保存呼び出し
**ファイル**: `src/backend/workflows/easy_mode_workflow.py`  
**操作**: `execute()` 内の生成ループ（または `pipeline.run()` 直後）で、完了ごとに `_save_checkpoint()` を呼ぶ  
**変更箇所**: 1箇所（ループ内または結果受け取り直後）  
**確認**: `compressed_context` は `ContextCompressionPipeline.compress()` 結果を使用

```python
# 圧縮コンテキスト生成
compressed = await context_pipeline.compress(project_id, episodes=range(start_ep, current_ep + 1))
await self._save_checkpoint(project_id, current_ep, compressed)
```

---

### Step 9: 再開時のコンテキスト復元ロジック追加
**ファイル**: `src/backend/workflows/easy_mode_workflow.py`  
**操作**: `execute()` 冒頭で、チェックポイント存在時は `compressed_context` を読み込み、次回生成の `input_data` またはパイプラインに注入  
**変更箇所**: 1箇所（Step 6 の直後）  
**確認**: `WritingGenerator.generate_episodes_pipeline(compressed_context=...)` へ渡せる形式か

---

### Step 10: 簡易リポジトリ/ストレージ実装
**ファイル**: `src/backend/database/repositories/checkpoint.py` （新規作成可）  
**操作**: `save_checkpoint()`, `load_checkpoint(project_id)`, `delete_checkpoint(project_id)` の3メソッドのみ実装  
**ストレージ**: JSONファイル（`data/checkpoints/{project_id}.json`）で十分  
**変更箇所**: 新規ファイル1つ（50行程度）  
**確認**: 非同期I/O (`aiofiles`) 使用、ディレクトリ自動作成

---

### Step 11: 単体テスト作成
**ファイル**: `tests/unit/test_easy_mode_batch_resume.py` （新規）  
**テストケース3つ**:
1. `start_ep=1, end_ep=5` で 1-5話のみ生成されること
2. `start_ep=6, end_ep=10` で 6-10話のみ生成され、前回コンテキストが引き継がれること
3. チェックポイント保存・読み込みが正しく動作すること  
**モック**: `EpisodePipeline.run`, `ContextCompressionPipeline.compress`, チェックポイントリポジトリ  
**実行**: `pytest tests/unit/test_easy_mode_batch_resume.py -v`

---

### Step 12: 手動統合テスト・動作確認手順書
**ファイル**: `docs/TEST_EASY_MODE_BATCH.md` （新規）  
**内容**:
```markdown
## 手動確認手順
1. サーバ起動: `uvicorn src.backend.main:app --reload`
2. 初回生成（1-10話）:
   POST /api/easy_mode/generate {"target_episodes": 50, "words_per_episode": 2000, "start_ep": 1, "end_ep": 10}
3. 進捗確認: チェックポイントファイル `data/checkpoints/{project_id}.json` 存在確認
4. 再開生成（11-20話）:
   POST /api/easy_mode/generate {"target_episodes": 50, "words_per_episode": 2000, "start_ep": 11, "end_ep": 20}
5. 全50話完走まで 3-4 を繰り返し
6. 最終成果物の整合性確認（話数・文字数・コンテキスト継続性）
```
**確認項目**: エラーなく完走、重複生成なし、前話参照が自然

---

## 実装順序の依存関係

```
Step 1 → Step 2 → Step 3 → Step 4 → Step 5 → Step 6
                                    ↓
                              Step 10 (並行可)
                                    ↓
                              Step 7 → Step 8 → Step 9
                                    ↓
                              Step 11 → Step 12
```

- Step 1-5 までで **最小動作（手動指定でバッチ実行）** が完成
- Step 6-9 で **自動再開・コンテキスト継承** が完成
- Step 10 は Step 7 より前でも後でも可（独立）
- Step 11-12 は全機能完成後

---

## 低性能LLM向け Tips

1. **1ステップ = 1ファイル1操作** を厳守。複数ファイル同時編集しない
2. 各ステップ完了後に「動作確認用ワンライナー」を実行してから次へ進む
3. エラーが出たらそのステップに戻り、エラーメッセージを貼り付けて修正指示する
4. インポート忘れ（`Query`, `Field`, `aiofiles` 等）が最大の失敗源 → 追加時に必ず import 確認
5. 非同期/同期の混在に注意：リポジトリは全て `async def` で統一

---

## 完了定義

- [ ] Step 1-5: `curl` で `start_ep`/`end_ep` 指定してバッチ生成が動く
- [ ] Step 6-9: パラメータ省略時に自動で続きから始まり、前話コンテキストが反映される
- [ ] Step 10: チェックポイントファイルが正しく作成・読み込みされる
- [ ] Step 11: 単体テスト全パス
- [ ] Step 12: 手動確認手順書通りに 50話完走できる