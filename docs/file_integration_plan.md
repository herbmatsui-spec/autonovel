# ファイル統合および構造整理方針書

## 1. 現状分析結果
調査の結果、当初懸念されていた `src/` と `streamlit_app/` 間での同一機能ファイルの重複（例: `workflow_types.py` の二重存在）は確認されませんでした。

### 確認済み事実:
- **UI層 (`streamlit_app/`)**: `workflow_types.py`, `utils/async_helper.py`, `utils/async_manager.py`, `progress.py`, `proxy.py` など、UI制御およびAPIプロキシ機能が集中している。
- **ビジネスロジック層 (`src/`)**: `engine_service.py`, `api/client.py`, `agents/`, `services/` など、実際の処理ロジックが集中している。
- **依存関係**: `streamlit_app` -> `src` の単方向依存となっており、構造的に整理されている。

## 2. 統合・整理方針

重複ファイルが存在しないため、「物理的な統合」ではなく「役割の明確化とクリーンアップ」にシフトします。

### 2.1 役割の定義
- **`streamlit_app/`**: 
    - Streamlitの状態管理 (`state.py`)
    - 非同期タスクのUI側管理 (`progress.py`, `background.py`)
    - バックエンドAPIへの型安全なアクセス (`proxy.py`)
    - UI定義 (`ui_tabs_*.py`, `ui_components.py`)
- **`src/`**:
    - コアビジネスロジック (`services/`, `agents/`)
    - 外部API通信の低レイヤー実装 (`infrastructure/api/api_client.py`)
    - データモデル定義 (`models/`)

### 2.2 修正・最適化ポイント
1. **インポートパスの正規化**:
   - `streamlit_app/` 内での相互参照を `streamlit_app.xxx` 形式に統一し、一貫性を保つ。
2. **プロキシ層の最適化**:
   - `streamlit_app/proxy.py` が `UltimateHegemonyEngineProxy` として振る舞っているが、これが `src/backend/engine.py` の責任をUI側で模倣している。リファクタリングPhase（Phase 6-7）にて、このプロキシと実際のEngineのインターフェースを同期させる。
3. **不要なスタブの削除**:
   - `src/` 内にUI層の模倣ファイル（`progress.py` 等）が万が一残っている場合は削除する（現状は存在しないことを確認済み）。

## 3. 結論
**物理的なファイル統合は不要。** 

現在の分離構造を維持しつつ、次のフェーズである「テストカバレッジ強化」および「UltimateHegemonyEngineのリファクタリング」に移行することで、複雑性を根本的に解決する。
