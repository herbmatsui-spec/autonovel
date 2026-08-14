# リファクタリングチケットリスト

| 優先度 | ����� ��� ��� � ��� � � 項目 | 詳細 | 対応ステップ番号 |
|--------|------|------|------------------|
| Critical (即時対応) | 1. `writing.py` 分割 | 2,400行単一クラスは保守不能 | 19-20 (完了)-28 |
| Critical (即時対応) | 2. `erotic_integrity.py` 分割 | 99,091行は論外 | 29-38 |
| Critical (即時対応) | 3. ���� ��環依存解消 | `engine.py` の `_legacy_dep` パターン���������������������������������������������������������������� | 11-18 |
| Critical (即時対応) | 4. グローバルDBシングルトン���������������������������������������������������������������� | DIコンテナ一本化 | 5-10 |
| High (1-2スプリント) | 5. リトライデコレータ クラス化 | `RetryPolicy` クラスへリファクタ | 45-50 |
| High (1-2スプリント) | 6. LLMゲートウェイ分割 | `GeminiClient`, `OpenAIClient`, `SchemaValidator` 等 | 39-44 |
| High (1-2スプリント) | 7. ���� ���� ���� �� �� �� �� 型ヒント `Any` �������� �������� ������ ������ ������ ���� | Protocol / 具象型で置���������������� | 51-56 |
| High (1-2スプリント) | 8. 設定一元化 | `ConfigManager` 単一エントリポイントへ統合 | 57-60 |
| Medium (技術的負��������返済) | 9. テストインフラ整備 | カバレッジ����������������定、モック統一、Property-based testing導入 | 61-65 |
| Medium (技術的負��������返済) | 10. ワークフロー基盤統一 | $BaseWorkflow$ テンプレートメソッド化 | 66 |
| Medium (技術的負��������返済) | 11. 非同期最適化 | $asyncio.TaskGroup$、$asyncio.to_thread$ ��������� ������� ������� ������� ������� ����� ������� ����� ����� ����� ����� ���用 | 67-68 |
| Medium (技術的負��������返済) | 12. ログ構造化完成 | $StructuredLogger$ 全����������������所適用 | 69 |
| Low (品質向上) | 13. ドキュメント同期 | コード変更時の README/ADR 更新ルール化 | 70（一部） |
| Low (品質向上) | 14. 依存関係バージョン����������������定 | $pip-tools$ / $uv$ 導入 | 71 |
| Low (品質向上) | 15. パフォーマンスベンチマーク | �������� ������ ���� ������ ���� ��続的����������������定環境構���������������� | 72 |

## 詳細情報

### チケット 4: グローバルDBシングルトンの呼び出し���箇所
```
src/core/container.py:12:from src.backend.database.core import get_db_manager
src/core/container.py:29:    db = providers.Singleton(get_db_manager)
src/backend/database/__init__.py:21:    get_db_manager,
src/backend/database/core.py:296:_GLOBAL_DB_MANAGER: Optional[DatabaseManager] = None
src/backend/database/core.py:329:def get_db_manager() -> DatabaseManager:
src/backend/database/core.py:333:    global _GLOBAL_DB_MANAGER
src/backend/database/core.py:334:    if _GLOBAL_DB_MANAGER is not None:
src/backend/database/core.py:335:        return _GLOBAL_DB_MANAGER
src/backend/database/core.py:346:    _GLOBAL_DB_MANAGER = manager
src/backend/database/core.py:372:    global _GLOBAL_DB_MANAGER
src/backend/database/core.py:373:    _GLOBAL_DB_MANAGER = manager
```

### チケット 3: ���� ��環依存解消
エンジンの _legacy_dep パターンによるランタイム依存の���洗い出し:

- src/backend/engine.py:49: def _legacy_dep(self, name: str) -> Any:
- 以下のプロパティが _legacy_dep を使用して依存性を���遅延解決:
  - planner (line 59)
  - planning_agent (line 63)
  - writer (line 67)
  - pm (line 71)
  - ctx_mgr (line 75)
  - formatter (line 79)
  - validator (line 83)
  - auditor (line 87)
  - narrative (line 91)
  - critique (line 95)
  - marketing (line 99)
  - bible_agent (line 103)
  - plot_agent (line 107)
  - style_rag (line 111)

これにより、エンジンはエージェントクラスを直接インポートせず、ランタイムで依存性を解決することで���循環依存を回���避しているが、完全な解決ではない。

### �� 補足情報: チケット 3 (環依存解消) の詳細
エンジンの _legacy_dep パターン:
- メソッド定義: src/backend/engine.py:49
- 使用�箇所: 14プロパティ (planner, planning_agent, writer, pm, ctx_mgr, formatter, validator, auditor, narrative, critique, marketing, bible_agent, plot_agent, style_rag)
- パターン: コンストラクタで **legacy � 辞書を受け取り、プロパティ経由で�遅延解決
- � 問題点: これによりコンパイル時の環依存チェックを回�避し、ランタイムエラーになるまで依存関係の問題が見えにくくなる
