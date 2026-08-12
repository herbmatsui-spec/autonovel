# Frontend Consolidation (Streamlit 廃止判定)

## 判定
**Streamlit を廃止し、React (frontend/) を正規フロントエンドとする。**

## 根拠
- ステップ49: `plans/STREAMLIT_TO_REACT_MIGRATION_STATUS.md` が存在し、移行状況が記録されている。
- ステップ50: `src/`, `tests/` からの `streamlit_app` 参照を排除し、同等機能を `src/core/state` 等に統合済み。
- ステップ51: `frontend/package.json` の `dev` (vite, 5173) / `preview` (vite preview, 3000) が正規ポートで動作。
- ステップ52: CI (`.github/workflows/ci.yml`) から `streamlit_app/` 参照を削除済み。
- ステップ53: `pytest.ini` の `pythonpath` を `pythonpath = . src` に修正済み。

## 今後の方針
- `streamlit_app/` は legacy として残置または削除対象。新規コードは React + `src/` バックエンド API を使用する。
- 移行後に `streamlit_app/` を完全削除することを推奨（ただし本ステップでは判定のみ）。
