# テストカバレッジ改善 実装計画書

## 1. 現在の状況

| 指標 | 値 |
|------|-----|
| 現在のカバレッジ | **25.83%** |
| 目標カバレッジ | 80% |
| ギャップ | **54.17%** |
| 総ソースファイル数 | 385 |
| テストファイル数 | 69 |
| 0%カバレッジファイル | 約90ファイル |
| 80%未満カバレッジサービス | 多数 |

## 2. カバレッジ内訳（モジュール別）

| カテゴリ | カバレッジ | 主な未テストファイル |
|----------|-----------|-------------------|
| `src/shared` | 54% | event_bus, network (0%) |
| `src/services` | ~10-17% | reproducibility, resilience, state_manager (0%) |
| `src/agents` | ~0-10% | debate, diversity_scorer, writing_scheduler (0%) |
| `src/backend` | ~0-17% | routers全て, workflows全て (0%) |
| `src/core` | ~0% | 全ファイル未テスト |
| `src/kernels` | ~0% | 全ファイル未テスト |
| `src/domain` | ~0% | 全ファイル未テスト |

## 3. 戦略：Tiered Approach（段階的アプローチ）

### Phase 1: 基盤整備（優先度: 高）
**目標: 40%達成**

1. **テストインフラ修正**
   - `conftest.py`のSQLite/JSONB問題修正
   - PostgreSQL用テストフィクスチャ追加
   - `real_db_manager`をJSONB対応に改良

2. **高価値ファイル優先テスト作成**
   - `src/services/writing_services.py` (10%→70%)
   - `src/services/vector_store.py` (17%→60%)
   - `src/services/semantic_cache.py` (10%→60%)
   - `src/services/llm_service.py` (既存テストを拡張)

3. **0%カバレッジのクリティカルサービス対応**
   - `src/services/state_manager.py` (0→80%)
   - `src/services/resilience.py` (0→80%)
   - `src/services/reproducibility.py` (0→80%)

### Phase 2: 拡張（優先度: 中）
**目標: 60%達成**

1. **Backend/Workflows カバレッジ**
   - `src/backend/workflows/`配下の主要ワークフロー
   - `src/backend/routers/`配下のAPIエンドポイント

2. **Agents カバレッジ**
   - `src/agents/`配下の主要エージェント

3. **Domain Models カバレッジ**
   - `src/domain/models/`のモデルクラス

### Phase 3: 完成（優先度: 低）
**目標: 80%達成**

1. **Kernel/Core カバレッジ**
2. ** Peripheral Services カバレッジ**

## 4. 優先度別アクショ план

### Priority 1: 即座対応（2-3日）

| ファイル | 現在 | 目標 | テスト種 |
|----------|------|------|----------|
| `src/services/state_manager.py` | 0% | 80% | Unit |
| `src/services/resilience.py` | 0% | 80% | Unit |
| `src/services/reproducibility.py` | 0% | 80% | Unit |
| `src/shared/event_bus.py` | 0% | 80% | Unit |
| `src/shared/network.py` | 0% | 80% | Unit |
| `conftest.py` | N/A | 修正 | Fixtures |

### Priority 2: 高価値ファイル（1-2週）

| ファイル | 現在 | 目標 | テスト種 |
|----------|------|------|----------|
| `src/services/writing_services.py` | 10% | 70% | Unit |
| `src/services/vector_store.py` | 17% | 60% | Unit |
| `src/services/semantic_cache.py` | 10% | 60% | Unit |
| `src/services/promotion_service.py` | 低% | 70% | Unit |
| `src/services/digest_service.py` | 低% | 70% | Unit |

### Priority 3: Backend APIs（2-3週）

| カテゴリ | 現在 | 目標 | テスト種 |
|----------|------|------|----------|
| `src/backend/routers/*` | 0% | 50% | Integration |
| `src/backend/workflows/*` | 0% | 50% | Integration |
| `src/backend/database/*` | 0% | 50% | Unit |

### Priority 4: Agents（3-4週）

| ファイル | 現在 | 目標 | テスト種 |
|----------|------|------|----------|
| `src/agents/erotic_integrity.py` | 既存 | 80% | Unit |
| `src/agents/illustration_agent.py` | 既存 | 80% | Unit |
| `src/agents/plot.py` | 0% | 60% | Unit |
| `src/agents/bible.py` | 0% | 60% | Unit |

### Priority 5: Domain/Core（4-6週）

| カテゴリ | 目標 | テスト種 |
|----------|------|----------|
| `src/domain/models/*` | 50% | Unit |
| `src/core/*` | 40% | Unit |
| `src/kernels/*` | 30% | Unit |

## 5. テスト技法ガイドライン

### Unit Test（ユニットテスト）
```python
# 純粋関数・ビジネスロジック向け
# モック活用：mock_llm, mock_repo
# 例: src/services/state_manager.py
```

### Integration Test（統合テスト）
```python
# APIエンドポイント・DB操作向け
# FastAPI TestClient活用
# fixtures: client, db_session
```

### Property-Based Test
```python
# 入力バリエーションテスト
# 例: text_chunker, safe_replace
```

## 6. カバレッジ目標達成に向けて

### 現在の状態から80%へ
- 総statements: 22,612
- 現在coverage: 5,963 statements (26%)
- 目標coverage: 18,090 statements (80%)
- 追加必要: **12,127 statements**

### 優先度別追加statement数試算

| Phase | 追加statement | 累積 | 達成% |
|-------|---------------|------|-------|
| Phase 1完了時 | ~3,000 | ~8,963 | ~40% |
| Phase 2完了時 | ~5,000 | ~13,963 | ~62% |
| Phase 3完了時 | ~4,000 | ~17,963 | ~80% |

## 7. リスクと対策

| リスク | 対策 |
|--------|------|
| JSONB/SQLite非互換 | PostgreSQLテストDB用意 or 型モック |
| 外部API依存 | mock_llmadapter完全化 |
| テスト実行時間増大 | pytest-xdist並列化 |
| 既存の壊れたテスト | skip/or/xfailで一時対応 |

## 8. 成功指標

- [ ] Phase 1完了: カバレッジ40%達成
- [ ] Phase 2完了: カバレッジ60%達成
- [ ] 全フェーズ完了: カバレッジ80%達成
- [ ] CIでカバレッジチェックがパス

## 9. 次のアクション

1. **即座**: `conftest.py`のJSONB問題を修正
2. **今週**: `tests/unit/test_state_manager.py`作成
3. **今週**: `tests/unit/test_resilience.py`作成
4. **2週間以内**: Phase 1優先ファイルのカバレッジ改善
5. **月次**: Phase 2進行状況レビュー
