# AutoNovel v5.2.0 C3 Baseline (Part 1)

- **Date**: 2026-09-26
- **Commit/State**: Post C1 & C2, clean tree

## 1. 現行エンドポイントとテストカバレッジ調査 (Step 1)
- `tests/` 内の `commercial/planning` / `commercial_planning` 参照テスト: 0件 (カバレッジなし)
- 現行ルーター `src/backend/routers/commercial_planning.py` にテストが存在しないことを確認。

## 2. 外部・フロントエンド呼び出し元の調査 (Step 2)
- `frontend/`, `web/`, `streamlit_app/` からの `/commercial/planning` 呼び出し: 0件
- 契約破壊なしに API 改善（`EpisodeBeat` 統一、タスク発行化、所有者検証導入）可能。

## 3. SSOT の確認 (Step 3)
- `src/config/commercial_beat_sheet.py`: `COMMERCIAL_40EP_BEATS`, `get_beat_for_episode`
- `src/models/beat_sheet.py`: `EpisodeBeat`
- `src/agents/planning.py`: `PlanningAgent.generate_commercial_beat_sheet` (line 243)

## 4. ルーター側の重複定義特定 (Step 4)
- `BeatSheetItem`, `BeatSheetResponse`, `BeatSheetGenerateRequest` が `commercial_planning.py` に重複定義されている。

## 5. Plot tension セマンティクス (Step 5)
- `Plot.target_tension` (Float, 0.0-1.0): `EpisodeBeat.tension_target` をそのまま格納。
- `Plot.tension` (Integer, 0-100): `int(round(tension_target * 100))` で補完。