# AutoNovel 実装計画書 P1: カクヨム直撃マーケティング＆スマホ最適化 (全24ステップ)

**対象領域**: Phase 1 (Marketing & Typography Optimization for Kakuyomu)  
**目的**: カクヨムの作品カードで最も目立つ「キャッチコピー（最大35文字）」の自動生成＆CTRスコアリングエンジンを新設し、スマホ縦スクロールに特化した「字下げ制御・段落行数最適化」を実装。さらに架空API（`kakuyomu.py`）を完全撤廃してワンクリック整形コピーへ一本化する。  
**前提条件**: 各ステップは単一ファイル・単一責任で完結し、低性能なLLMでも1ステップずつ順番に適用・検証可能。

---

## 📋 ステップ一覧マトリクス

| ステップ | レイヤー | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Config | `src/config/kakuyomu_syntax_patterns.py` | [MODIFY] 35文字キャッチコピー構文テンプレート＆パワーワード辞書追加 |
| **Step 2** | Service | `src/services/marketing/catchphrase_scorer.py` | [NEW] カクヨム特化キャッチコピーCTRスコアリングエンジン（0〜100点）実装 |
| **Step 3** | Test | `tests/unit/marketing/test_catchphrase_scorer.py` | [NEW] キャッチコピーCTRスコアラーの単体テスト作成＆検証 |
| **Step 4** | Prompt | `prompts/templates/marketing/viral_catchphrase_generation.j2` | [NEW] 悪魔的CTRを誇る35文字キャッチコピー生成Jinja2プロンプト作成 |
| **Step 5** | Manager | `prompts/manager.py` | [MODIFY] `build_viral_catchphrase_prompt` レンダリングメソッド追加 |
| **Step 6** | Agent | `src/agents/marketing.py` | [MODIFY] `MarketingAgent` に `generate_viral_catchphrases` メソッド追加 |
| **Step 7** | Schema | `src/domain/schemas/marketing.py` | [MODIFY] `CatchphraseCandidate` およびレスポンススキーマ追加 |
| **Step 8** | Router | `src/backend/routers/marketing.py` | [MODIFY] `POST /api/marketing/catchphrases` エンドポイント新設 |
| **Step 9** | Test | `tests/unit/api/test_marketing_catchphrase_api.py` | [NEW] キャッチコピー生成APIの単体テスト作成＆検証 |
| **Step 10** | Formatter | `src/services/formatters/platform_copy_formatter.py` | [MODIFY] `indent_enabled: bool` 引数を追加し全角字下げのON/OFF制御 |
| **Step 11** | Formatter | `src/services/formatters/platform_copy_formatter.py` | [MODIFY] カクヨム専用の空行リズム（字下げなし・改行維持）処理を実装 |
| **Step 12** | Formatter | `src/services/formatters/platform_copy_formatter.py` | [MODIFY] スマホ読書用「3行超の段落自動分割（空行挿入）」機能を追加 |
| **Step 13** | Test | `tests/unit/services/formatters/test_platform_copy_formatter.py` | [MODIFY] カクヨムスマホ最適化（字下げなし・段落分割）の単体テスト拡充 |
| **Step 14** | Router | `src/backend/routers/platform_export.py` | [MODIFY] `POST /api/export/copy/` に `indent_enabled` クエリパラメータ対応 |
| **Step 15** | Test | `tests/unit/api/test_platform_export.py` | [MODIFY] プラットフォーム整形APIテストにカクヨム字下げ制御テスト追加 |
| **Step 16** | Cleanup | `src/services/publishers/kakuyomu.py` | [MODIFY] 架空の外部API（`api.kakuyomu.jp`）リクエスト処理を完全撤廃 |
| **Step 17** | Publisher | `src/services/publishers/kakuyomu.py` | [MODIFY] カクヨム新規エピソード投稿画面URL生成とクリップボード補助に置換 |
| **Step 18** | Test | `tests/unit/publishers/test_kakuyomu_publisher.py` | [NEW] カクヨムURL生成とペイロード検証テスト作成 |
| **Step 19** | Component | `frontend/src/components/common/PlatformCopyButton.tsx` | [MODIFY] 「字下げON/OFF」切り替えトグルスイッチを追加 |
| **Step 20** | Component | `frontend/src/components/marketing/CatchphraseCard.tsx` | [NEW] 35文字キャッチコピー候補表示＆ワンクリックコピーUIコンポーネント |
| **Step 21** | View | `frontend/src/components/commercial/CommercialPublishPanel.tsx` | [MODIFY] カクヨムエピソード作成画面を直接開く外部リンクボタン追加 |
| **Step 22** | View | `frontend/src/components/marketing/MarketingPanel.tsx` | [MODIFY] タイトル生成横に「キャッチコピー生成」タブ/セクションを統合 |
| **Step 23** | FrontendTest| `frontend/tests/components/PlatformCopyButton.test.tsx` | [MODIFY] 字下げトグルとコピー動作のVitest単体テスト実行 |
| **Step 24** | Integration | `tests/integration/test_p1_kakuyomu_flow.py` | [NEW] キャッチコピー生成からスマホ最適化コピーまでの結合テスト |

---

## 🛠️ 各ステップ詳細手順（1〜24）

### Step 1: キャッチコピー構文テンプレート＆辞書追加
- **対象ファイル**: `src/config/kakuyomu_syntax_patterns.py`
- **目的**: カクヨムの作品一覧カードでタイトルの上に最も大きく表示される「キャッチコピー（最大35文字）」の構文テンプレートと高CTRワードを定義。
- **実装内容**:
  ```python
  # キャッチコピー最大文字数（カクヨム公式規定: 35文字）
  CATCHPHRASE_MAX_LENGTH: int = 35
  CATCHPHRASE_OPTIMAL_MIN: int = 15
  CATCHPHRASE_OPTIMAL_MAX: int = 32

  # カクヨムキャッチコピー高CTR構文
  KAKUYOMU_CATCHPHRASE_TEMPLATES: list[str] = [
      "「{dialogue}」――そう言った元仲間が翌日全滅していた件。",
      "追放された元無能、実は世界で唯一の【{unique_cheat}】でした。",
      "今更戻ってこい？ もう世界最強の美少女たちと暮らしてますが？",
      "処刑されたはずの元英雄、気ままなスローライフ始めます。",
      "ただの{job}ですが、なぜか周囲が神だと勘違いして崇めてきます。",
  ]

  # キャッチコピー直撃パワーワード
  CATCHPHRASE_POWER_WORDS: list[str] = [
      "そう言った", "全滅", "翌日", "今更", "もう遅い", "唯一の",
      "勘違い", "神", "実は", "スローライフ", "無双", "溺愛", "クビ",
  ]
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.config.kakuyomu_syntax_patterns import CATCHPHRASE_MAX_LENGTH; assert CATCHPHRASE_MAX_LENGTH == 35; print('OK')"
  ```

---

### Step 2: キャッチコピーCTRスコアラーの実装
- **対象ファイル**: `src/services/marketing/catchphrase_scorer.py` (新規作成)
- **目的**: 提示されたキャッチコピーがカクヨムで読者のタップを誘発するかを0〜100点で採点する。
- **実装内容**:
  - 35文字以内厳守（36字以上は0点判定）
  - スマホ視認性（15〜32字で満点加算）
  - パワーワード含有判定
  - カギ括弧「」や記号（――、！？）のフック判定
- **検証コマンド**:
  ```powershell
  python -c "from src.services.marketing.catchphrase_scorer import score_catchphrase_ctr; print(score_catchphrase_ctr('「お前はクビだ」――そう言った元パーティが翌日全滅していた件。'))"
  ```

---

### Step 3: キャッチコピーCTRスコアラーの単体テスト
- **対象ファイル**: `tests/unit/marketing/test_catchphrase_scorer.py` (新規作成)
- **目的**: 35文字超過ペナルティ、最適文字数加点、記号フック加点を検証。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/marketing/test_catchphrase_scorer.py -v
  ```

---

### Step 4: キャッチコピー生成Jinja2テンプレート作成
- **対象ファイル**: `prompts/templates/marketing/viral_catchphrase_generation.j2` (新規作成)
- **目的**: 企画設定からカクヨム規定（最大35文字厳守）の悪魔的キャッチコピーを20件一挙生成するプロンプト。
- **実装内容**:
  - 35文字超過を厳格に禁止する制約
  - セリフ型・衝撃告白型・地位反転型の3分類で生成
  - JSON配列 `[{"catchphrase": "...", "type": "..."}]` のみを出力
- **検証コマンド**:
  ```powershell
  python -c "import jinja2; t = jinja2.Template(open('prompts/templates/marketing/viral_catchphrase_generation.j2', encoding='utf-8').read()); print('Template OK')"
  ```

---

### Step 5: `PromptManager` にキャッチコピーメソッド追加
- **対象ファイル**: `prompts/manager.py`
- **目的**: `build_viral_catchphrase_prompt` メソッドを実装し、テンプレートを非同期レンダリング。
- **検証コマンド**:
  ```powershell
  python -c "from prompts.manager import PromptManager; pm = PromptManager(); print(hasattr(pm, 'build_viral_catchphrase_prompt'))"
  ```

---

### Step 6: `MarketingAgent` にキャッチコピー生成追加
- **対象ファイル**: `src/agents/marketing.py`
- **目的**: LLMを呼び出してキャッチコピーを生成し、`catchphrase_scorer` でスコアリングして上位候補を返す。
- **検証コマンド**:
  ```powershell
  python -c "from src.agents.marketing import MarketingAgent; print(hasattr(MarketingAgent, 'generate_viral_catchphrases'))"
  ```

---

### Step 7: キャッチコピースキーマ追加
- **対象ファイル**: `src/domain/schemas/marketing.py`
- **目的**: `CatchphraseItem(catchphrase: str, score: float, char_count: int, type: str)` を定義。
- **検証コマンド**:
  ```powershell
  python -c "from src.domain.schemas.marketing import CatchphraseItem; print(CatchphraseItem(catchphrase='テスト', score=80.0, char_count=3, type='dialogue'))"
  ```

---

### Step 8: キャッチコピー生成ルーター追加
- **対象ファイル**: `src/backend/routers/marketing.py`
- **目的**: `POST /api/marketing/catchphrases` を新設し、フロントエンドから即座に呼べるようにする。
- **検証コマンド**:
  ```powershell
  python -c "from src.backend.routers.marketing import router; print([r.path for r in router.routes])"
  ```

---

### Step 9: キャッチコピーAPI単体テスト
- **対象ファイル**: `tests/unit/api/test_marketing_catchphrase_api.py` (新規作成)
- **目的**: FastAPI TestClient でキャッチコピー生成エンドポイントの正常応答をテスト。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/api/test_marketing_catchphrase_api.py -v
  ```

---

### Step 10: `PlatformCopyFormatter` に字下げ制御引数追加
- **対象ファイル**: `src/services/formatters/platform_copy_formatter.py`
- **目的**: `format_for_platform` に `indent_enabled: bool = True` を追加し、カクヨム向けに字下げを無効化できるようにする。
- **検証コマンド**:
  ```powershell
  python -c "from src.services.formatters.platform_copy_formatter import PlatformCopyFormatter; res = PlatformCopyFormatter.format_for_platform('タイトル', '本文', platform='kakuyomu', indent_enabled=False); assert not res.body.startswith('　'); print('OK')"
  ```

---

### Step 11: カクヨム用空行リズム最適化の実装
- **対象ファイル**: `src/services/formatters/platform_copy_formatter.py`
- **目的**: `platform="kakuyomu"` かつ `indent_enabled=False` の場合、行頭字下げを行わず、段落間に自然な1行空行を配置する。
- **検証コマンド**:
  ```powershell
  python -c "from src.services.formatters.platform_copy_formatter import PlatformCopyFormatter; res = PlatformCopyFormatter.format_for_platform('T', '文1\n文2', platform='kakuyomu', indent_enabled=False); print(repr(res.body))"
  ```

---

### Step 12: スマホ用「3行超段落の自動分割」機能追加
- **対象ファイル**: `src/services/formatters/platform_copy_formatter.py`
- **目的**: スマホ画面で1段落が4行以上連続すると読者が圧迫感で離脱するため、句点（。）を基準に自動で改行＋空行を挟む。
- **検証コマンド**:
  ```powershell
  python -c "from src.services.formatters.platform_copy_formatter import PlatformCopyFormatter; res = PlatformCopyFormatter.split_dense_paragraphs('長い文。長い文。長い文。長い文。'); assert '\n\n' in res; print('OK')"
  ```

---

### Step 13: フォーマッタ単体テスト拡充
- **対象ファイル**: `tests/unit/services/formatters/test_platform_copy_formatter.py`
- **目的**: カクヨム字下げ無効化、段落自動分割、ルビ変換（`|漢字《ルビ》`、`《《傍点》》`）の正常性をテスト。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/services/formatters/test_platform_copy_formatter.py -v
  ```

---

### Step 14: 整形エクスポートルーター改修
- **対象ファイル**: `src/backend/routers/platform_export.py`
- **目的**: `indent_enabled` パラメータを受け取り、`PlatformCopyFormatter` に渡す。
- **検証コマンド**:
  ```powershell
  python -c "from src.backend.routers.platform_export import router; print('Router OK')"
  ```

---

### Step 15: 整形API単体テストの更新
- **対象ファイル**: `tests/unit/api/test_platform_export.py`
- **目的**: `POST /api/export/copy/` に対する `indent_enabled=false` のテストケースを追加。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/api/test_platform_export.py -v
  ```

---

### Step 16: 架空APIリクエストの完全撤廃
- **対象ファイル**: `src/services/publishers/kakuyomu.py`
- **目的**: `API_BASE = "https://api.kakuyomu.jp/v1"` や `client.post` による存在しないAPIへのHTTPリクエストを完全削除。
- **検証コマンド**:
  ```powershell
  python -c "from src.services.publishers.kakuyomu import KakuyomuPublisher; pub = KakuyomuPublisher(); assert not hasattr(pub, 'API_BASE') or pub.API_BASE is None; print('OK')"
  ```

---

### Step 17: カクヨム投稿画面URL生成＆クリップボード補助への置換
- **対象ファイル**: `src/services/publishers/kakuyomu.py`
- **目的**: 作品ID（`work_id`）を指定した「エピソード新規作成URL（`https://kakuyomu.jp/works/{work_id}/episodes/new`）」を生成し、整形済み本文とともに返却する安全な仕様へ変更。
- **検証コマンド**:
  ```powershell
  python -c "from src.services.publishers.kakuyomu import KakuyomuPublisher; pub = KakuyomuPublisher(); url = pub.get_episode_creation_url('123456'); assert 'episodes/new' in url; print(url)"
  ```

---

### Step 18: カクヨムPublisher単体テスト作成
- **対象ファイル**: `tests/unit/publishers/test_kakuyomu_publisher.py` (新規作成)
- **目的**: 架空APIエラーが出ないこと、正しい投稿URLと整形テキストが返ることを検証。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/publishers/test_kakuyomu_publisher.py -v
  ```

---

### Step 19: フロントエンド `PlatformCopyButton.tsx` に字下げトグル追加
- **対象ファイル**: `frontend/src/components/common/PlatformCopyButton.tsx`
- **目的**: 「全角字下げ（なろう推奨）」と「字下げなし（カクヨム推奨）」の切り替えチェックボックスを配置。
- **検証コマンド**:
  ```powershell
  cd frontend; npx tsc --noEmit; cd ..
  ```

---

### Step 20: キャッチコピー表示・コピーコンポーネント新設
- **対象ファイル**: `frontend/src/components/marketing/CatchphraseCard.tsx` (新規作成)
- **目的**: 35文字の文字数インジケーター（緑: 32文字以内、赤: 35文字超）とワンクリックコピーボタンを備えたUIを作成。
- **検証コマンド**:
  ```powershell
  cd frontend; npx tsc --noEmit; cd ..
  ```

---

### Step 21: カクヨム投稿画面直行リンクボタン追加
- **対象ファイル**: `frontend/src/components/commercial/CommercialPublishPanel.tsx`
- **目的**: コピー成功トースト通知内に「🔗 カクヨム投稿画面を開く」ボタンを表示し、別タブで投稿画面を直接開けるようにする。
- **検証コマンド**:
  ```powershell
  cd frontend; npx tsc --noEmit; cd ..
  ```

---

### Step 22: マーケティングダッシュボードにキャッチコピー統合
- **対象ファイル**: `frontend/src/components/marketing/MarketingPanel.tsx`
- **目的**: タイトル候補生成の下に「✨ カクヨム用35文字キャッチコピー生成」タブを追加。
- **検証コマンド**:
  ```powershell
  cd frontend; npm run build; cd ..
  ```

---

### Step 23: フロントエンド単体テスト実行
- **対象ファイル**: `frontend/tests/components/PlatformCopyButton.test.tsx`
- **目的**: 字下げトグル切り替え時のAPIリクエストパラメータとクリップボードコピーを検証。
- **検証コマンド**:
  ```powershell
  cd frontend; npm test src/components/common/PlatformCopyButton.test.tsx; cd ..
  ```

---

### Step 24: P1全結合検証
- **対象ファイル**: `tests/integration/test_p1_kakuyomu_flow.py` (新規作成)
- **目的**: 企画情報入力 → 35文字キャッチコピー生成 → 本文整形（カクヨム字下げなし＋段落分割） → 投稿用ペイロード出力の一連のフローが完全動作することを検証。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/integration/test_p1_kakuyomu_flow.py -v
  ```
