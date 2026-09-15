# P6: APIルーター・認可ガード・ドメイン＆コア基盤 テストカバレッジ80%引き上げ実装計画書

詳細な12ステップの実装仕様書は以下を参照してください：
- [plans/P6_COVERAGE_ROUTERS_DOMAIN_12STEPS.md](file:///e:/hhh/plans/P6_COVERAGE_ROUTERS_DOMAIN_12STEPS.md)

**概要**:
- **対象**: `src/backend/routers/`, `src/domain/`, `src/core/`, `src/backend/sanitizer.py`, `src/backend/auth.py`, `src/backend/security/jwt.py`
- **テスト保存先**: `tests/unit/routers/`, `tests/unit/domain/`, `tests/unit/core/`
- **カバー追加見込み**: 約 5,500 行（現状 26.5% → 目標 85%以上）
- **ステップ数**: 全12ステップ (低性能LLM向け完全自己完結コード付属)
