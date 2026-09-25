# AutoNovel 実装計画書 P3: 商業構成・1巻完結（40話）ビートシート＆コミカライズ見せ場 (全24ステップ)

**対象領域**: Phase 3 (Commercial Structure, 40-Episode Beat Sheet & Manga Key Scenes)  
**目的**: 出版社編集者の商業書籍化スカウト基準である「1巻分（約10万字・40話前後）で破綻なくストーリーが着地する構成力」を担保する40話商業ビートシートを導入。さらにコミカライズ化を意識した「決めゴマ・ビジュアルシーン」強制プロンプト、短期/長期の伏線階層化、および商業用1巻まとめ納品エクスポーターを実装する。  
**前提条件**: 各ステップは単一ファイル・単一責任で完結し、低性能なLLMでも1ステップずつ順番に適用・検証可能。

---

## 📋 ステップ一覧マトリクス

| ステップ | レイヤー | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Config | `src/config/commercial_beat_sheet.py` | [NEW] Web小説特化40話商業ビートシート（起承転結・山場・中だるみ防止）定義 |
| **Step 2** | Schema | `src/models/beat_sheet.py` | [NEW] 40話ビートシートおよび各話ミッションのPydanticスキーマ定義 |
| **Step 3** | Test | `tests/unit/planning/test_beat_sheet_rules.py` | [NEW] ビートシート定義の整合性・話数境界テスト作成 |
| **Step 4** | Prompt | `prompts/templates/narrative/beat_sheet_generation.j2` | [NEW] 企画概要から40話分の商業ビートシートを一括生成するプロンプト作成 |
| **Step 5** | Agent | `src/agents/planning.py` | [MODIFY] `PlanningAgent` に40話ビートシート生成・同期メソッド追加 |
| **Step 6** | Test | `tests/unit/agents/test_planning_beat_sheet.py` | [NEW] ビートシート生成エージェントの単体テスト作成 |
| **Step 7** | Status | `src/models/foreshadowing_status.py` | [MODIFY] 伏線スコープ（`SHORT_TERM` 即時快感用 / `LONG_TERM` 1巻伏線）列挙値追加 |
| **Step 8** | Migration | `alembic/versions/0029_add_foreshadowing_scope.py` | [NEW] `foreshadowings` テーブルに `scope` カラムを追加するマイグレーション |
| **Step 9** | Repo | `src/infrastructure/repositories/foreshadowing_repo.py` | [MODIFY] 短期・長期スコープ別の未回収伏線取得クエリを実装 |
| **Step 10** | Service | `src/services/foreshadowing_service.py` | [MODIFY] 話数進捗に応じた「短期（2〜3話以内）」と「長期」のプロンプト注入分離 |
| **Step 11** | Test | `tests/unit/services/test_foreshadowing_scope.py` | [NEW] 伏線スコープ別の取得・自動回収単体テスト作成 |
| **Step 12** | Schema | `src/models/visual_key_scene.py` | [NEW] コミカライズ用決めゴマ・ビジュアルシーンスキーマ定義 |
| **Step 13** | Prompt | `prompts/templates/narrative/visual_key_scene_instruction.j2` | [NEW] 各話に最低1箇所の大ゴマ・見開き級描写を強制するプロンプト作成 |
| **Step 14** | Prompt | `prompts/templates/narrative/final_writing_prompt.j2` | [MODIFY] 決めゴマ指示文を執筆プロンプトへ組み込み |
| **Step 15** | Refiner | `src/agents/writing/prose_refiner_agent.py` | [MODIFY] 決めゴマ箇所の五感・情景描写の密度を高める推敲ルール追加 |
| **Step 16** | Test | `tests/unit/agents/test_visual_key_scene_prompt.py` | [NEW] ビジュアルシーン指示を含むプロンプト構築の単体テスト作成 |
| **Step 17** | Exporter | `src/services/exporters/commercial_manuscript_exporter.py` | [NEW] 出版社持ち込み・電書用「1巻まとめ（10万字）」テキスト結合エクスポーター作成 |
| **Step 18** | Exporter | `src/services/exporters/epub_builder.py` | [MODIFY] 縦書きEPUB 3の目次・扉絵・中扉・挿絵レイアウトを商業水準へ強化 |
| **Step 19** | Test | `tests/unit/exporters/test_commercial_manuscript_exporter.py` | [NEW] 1巻まとめ納品ファイル（目次・本文・あとがき・キャラ表）出力テスト |
| **Step 20** | Router | `src/backend/routers/commercial_planning.py` | [NEW] 40話ビートシート取得・編集APIエンドポイント新設 |
| **Step 21** | Component | `frontend/src/components/planning/BeatSheetViewer.tsx` | [NEW] 40話の進捗・テンション曲線・山場を可視化するUIコンポーネント |
| **Step 22** | Component | `frontend/src/components/planning/ForeshadowingScopeBadge.tsx`| [NEW] 短期（⚡即回収）/ 長期（🎯1巻クライマックス）の伏線識別バッジ |
| **Step 23** | View | `frontend/src/components/ExportPanel.tsx` | [MODIFY] 「📚 商業用1巻まとめ（10万字）納品」ボタンを追加 |
| **Step 24** | E2E | `tests/integration/test_40ep_commercial_lifecycle.py` | [NEW] 40話ビートシート策定から10万字商業EPUB納品までのE2E結合テスト |

---

## 🛠️ 各ステップ詳細手順（1〜24）

### Step 1: Web小説特化40話商業ビートシートの定義
- **対象ファイル**: `src/config/commercial_beat_sheet.py` (新規作成)
- **目的**: 単行本1巻分（約10万字・40話）を読ませ切るための黄金構成比率（開幕・導入・急展開・谷間・決戦・後日談）を定義。
- **実装内容**:
  ```python
  COMMERCIAL_40EP_BEATS = [
      {"range": (1, 3), "phase": "開幕フック", "directive": "理不尽な侮蔑・追放からの規格外覚醒と圧倒的引き"},
      {"range": (4, 10), "phase": "初期成功・拠点確立", "directive": "新天地での能力証明、ヒロイン/相棒との出会い、小ざまぁ"},
      {"range": (11, 18), "phase": "第1の試練・勢力拡大", "directive": "街やギルドでの名声拡大、旧勢力の焦燥、中規模ボスの撃破"},
      {"range": (19, 25), "phase": "Midpoint・大転換", "directive": "世界観の秘密・黒幕の示唆、主人公の新たな目標の確立"},
      {"range": (26, 32), "phase": "最大の危機・包囲網", "directive": "旧勢力や強大敵の本格侵攻、一時的な孤立（中だるみ防止の谷間）"},
      {"range": (33, 38), "phase": "クライマックス決戦", "directive": "伏線全回収、圧倒的カタルシス（特大ざまぁ・完全勝利）"},
      {"range": (39, 40), "phase": "凱旋・第1巻結び", "directive": "圧倒的称賛・地位の確立、第2巻への壮大な予告引き"},
  ]
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.config.commercial_beat_sheet import COMMERCIAL_40EP_BEATS; assert len(COMMERCIAL_40EP_BEATS) == 7; print('OK')"
  ```

---

### Step 2: 40話ビートシートスキーマ定義
- **対象ファイル**: `src/models/beat_sheet.py` (新規作成)
- **目的**: `EpisodeBeat(ep_num: int, phase: str, mission: str, tension_target: float, visual_scene_focus: str)` をPydantic定義。
- **検証コマンド**:
  ```powershell
  python -c "from src.models.beat_sheet import EpisodeBeat; print('Beat Schema OK')"
  ```

---

### Step 3: ビートシート規則単体テスト
- **対象ファイル**: `tests/unit/planning/test_beat_sheet_rules.py` (新規作成)
- **目的**: 1話から40話まで抜け漏れなくフェーズが割り振られていることを検証。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/planning/test_beat_sheet_rules.py -v
  ```

---

### Step 4: 40話ビートシート一括生成プロンプト作成
- **対象ファイル**: `prompts/templates/narrative/beat_sheet_generation.j2` (新規作成)
- **目的**: タイトル・あらすじ・キャラクター設定から、40話分の各話ミッションとテンション数値を一括生成するプロンプト。
- **検証コマンド**:
  ```powershell
  python -c "import jinja2; jinja2.Template(open('prompts/templates/narrative/beat_sheet_generation.j2', encoding='utf-8').read()); print('Template OK')"
  ```

---

### Step 5: `PlanningAgent` にビートシート生成追加
- **対象ファイル**: `src/agents/planning.py`
- **目的**: `generate_commercial_beat_sheet` メソッドを新設し、DBに40話のプロット設計図を一括保存。
- **検証コマンド**:
  ```powershell
  python -c "from src.agents.planning import PlanningAgent; print(hasattr(PlanningAgent, 'generate_commercial_beat_sheet'))"
  ```

---

### Step 6: ビートシート生成エージェント単体テスト
- **対象ファイル**: `tests/unit/agents/test_planning_beat_sheet.py` (新規作成)
- **目的**: LLMモックを用いて40話分のビートシートが正しくパース・返却されることを検証。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/agents/test_planning_beat_sheet.py -v
  ```

---

### Step 7: 伏線スコープ列挙値の追加
- **対象ファイル**: `src/models/foreshadowing_status.py`
- **目的**: `ForeshadowingScope(SHORT_TERM="short_term", LONG_TERM="long_term")` を追加。
- **検証コマンド**:
  ```powershell
  python -c "from src.models.foreshadowing_status import ForeshadowingScope; assert ForeshadowingScope.SHORT_TERM == 'short_term'; print('OK')"
  ```

---

### Step 8: 伏線テーブルマイグレーション追加
- **対象ファイル**: `alembic/versions/0029_add_foreshadowing_scope.py` (新規作成)
- **目的**: `foreshadowings` テーブルに `scope VARCHAR(32) DEFAULT 'short_term'` を追加。
- **検証コマンド**:
  ```powershell
  python -c "import importlib; importlib.import_module('alembic.versions.0029_add_foreshadowing_scope'); print('Migration OK')"
  ```

---

### Step 9: 伏線リポジトリのスコープクエリ拡張
- **対象ファイル**: `src/infrastructure/repositories/foreshadowing_repo.py`
- **目的**: `get_unresolved_by_scope(book_id: int, scope: ForeshadowingScope)` メソッドを追加。
- **検証コマンド**:
  ```powershell
  python -c "from src.infrastructure.repositories.foreshadowing_repo import DbForeshadowingRepository; print('Repo OK')"
  ```

---

### Step 10: `ForeshadowingService` のスコープ注入分離
- **対象ファイル**: `src/services/foreshadowing_service.py`
- **目的**: 通常回には直近の「短期伏線（即時回収用）」を、クライマックス（33話以降）には「長期伏線（大ネタ回収用）」をプロンプトへ優先注入。
- **検証コマンド**:
  ```powershell
  python -c "from src.services.foreshadowing_service import ForeshadowingService; print('Service OK')"
  ```

---

### Step 11: 伏線スコープ単体テスト
- **対象ファイル**: `tests/unit/services/test_foreshadowing_scope.py` (新規作成)
- **目的**: 短期・長期伏線の分類取得と回収判定をテスト。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/services/test_foreshadowing_scope.py -v
  ```

---

### Step 12: コミカライズ用決めゴマスキーマ定義
- **対象ファイル**: `src/models/visual_key_scene.py` (新規作成)
- **目的**: `VisualKeyScene(scene_type: str, focus_subject: str, visual_cue: str, atmosphere: str)` を定義。
- **検証コマンド**:
  ```powershell
  python -c "from src.models.visual_key_scene import VisualKeyScene; print('VisualKeyScene OK')"
  ```

---

### Step 13: 決めゴマ描写プロンプト作成
- **対象ファイル**: `prompts/templates/narrative/visual_key_scene_instruction.j2` (新規作成)
- **目的**: 「この話の見開き・大ゴマに相当する決定的瞬間（主人公の眼光、必殺技の閃光、ヒロインの赤面など）を、漫画のコマ割りが想起される濃密な筆致で描け」という指示文を作成。
- **検証コマンド**:
  ```powershell
  python -c "import jinja2; jinja2.Template(open('prompts/templates/narrative/visual_key_scene_instruction.j2', encoding='utf-8').read()); print('Template OK')"
  ```

---

### Step 14: `final_writing_prompt.j2` への決めゴマ指示組み込み
- **対象ファイル**: `prompts/templates/narrative/final_writing_prompt.j2`
- **目的**: 執筆プロンプトに `{% include "visual_key_scene_instruction.j2" %}` を追加。
- **検証コマンド**:
  ```powershell
  python -c "import jinja2; jinja2.Template(open('prompts/templates/narrative/final_writing_prompt.j2', encoding='utf-8').read()); print('Writing Template OK')"
  ```

---

### Step 15: 推敲エージェントのケレン味強化
- **対象ファイル**: `src/agents/writing/prose_refiner_agent.py`
- **目的**: 決めゴマシーン周辺の擬音・視覚描写・比喩表現をシャープに研磨するFew-Shotを追加。
- **検証コマンド**:
  ```powershell
  python -c "from src.agents.writing.prose_refiner_agent import ProseRefinerAgent; print('Refiner OK')"
  ```

---

### Step 16: ビジュアルシーンプロンプト単体テスト
- **対象ファイル**: `tests/unit/agents/test_visual_key_scene_prompt.py` (新規作成)
- **目的**: 決めゴマ指示が執筆プロンプトに正しく挿入されることを検証。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/agents/test_visual_key_scene_prompt.py -v
  ```

---

### Step 17: 商業用1巻まとめエクスポーター作成
- **対象ファイル**: `src/services/exporters/commercial_manuscript_exporter.py` (新規作成)
- **目的**: 40話分のエピソードを1本の完成原稿（目次、各話タイトル、区切り線、あとがき、登場人物紹介）に結合出力するサービス。
- **検証コマンド**:
  ```powershell
  python -c "from src.services.exporters.commercial_manuscript_exporter import CommercialManuscriptExporter; print('ManuscriptExporter OK')"
  ```

---

### Step 18: EPUB 3レイアウトの商業水準強化
- **対象ファイル**: `src/services/exporters/epub_builder.py`
- **目的**: 縦書きCSS（フォント、ルビ行間、見出しスタイル、中扉ページ）を商用電子書籍クオリティへ刷新。
- **検証コマンド**:
  ```powershell
  python -c "from src.services.exporters.epub_builder import EPUBBuilder; print('EPUBBuilder OK')"
  ```

---

### Step 19: 1巻まとめエクスポーター単体テスト
- **対象ファイル**: `tests/unit/exporters/test_commercial_manuscript_exporter.py` (新規作成)
- **目的**: 40話分のダミーエピソードから約10万字の結合テキストおよび縦書きEPUBが正しく生成されることを検証。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/exporters/test_commercial_manuscript_exporter.py -v
  ```

---

### Step 20: 商業プランニングAPIルーター新設
- **対象ファイル**: `src/backend/routers/commercial_planning.py` (新規作成)
- **目的**: `GET /api/commercial/beat-sheet/{book_id}` および `POST /api/commercial/beat-sheet/generate` を実装。
- **検証コマンド**:
  ```powershell
  python -c "from src.backend.routers.commercial_planning import router; print('Router OK')"
  ```

---

### Step 21: 40話ビートシートビューアUI作成
- **対象ファイル**: `frontend/src/components/planning/BeatSheetViewer.tsx` (新規作成)
- **目的**: 1〜40話の進捗、各話の山場ミッション、テンション曲線をグラフとカードで直感的に表示・編集するUI。
- **検証コマンド**:
  ```powershell
  cd frontend; npx tsc --noEmit; cd ..
  ```

---

### Step 22: 短期/長期伏線バッジUI作成
- **対象ファイル**: `frontend/src/components/planning/ForeshadowingScopeBadge.tsx` (新規作成)
- **目的**: 伏線管理画面で「⚡ 短期伏線」「🎯 1巻回収伏線」を色分けバッジで可視化。
- **検証コマンド**:
  ```powershell
  cd frontend; npx tsc --noEmit; cd ..
  ```

---

### Step 23: エクスポートパネルに商業納品ボタン追加
- **対象ファイル**: `frontend/src/components/ExportPanel.tsx`
- **目的**: 「📚 商業用1巻まとめ納品（TXT/EPUB）」ボタンを追加し、1クリックで10万字原稿をダウンロード可能にする。
- **検証コマンド**:
  ```powershell
  cd frontend; npm run build; cd ..
  ```

---

### Step 24: 40話商業ライフサイクルE2E結合テスト
- **対象ファイル**: `tests/integration/test_40ep_commercial_lifecycle.py` (新規作成)
- **目的**: 40話ビートシート生成 → 伏線配置（短期/長期） → 決めゴマ付き執筆 → 商業1巻まとめ原稿出力の一連のライフサイクルを自動検証。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/integration/test_40ep_commercial_lifecycle.py -v
  ```
