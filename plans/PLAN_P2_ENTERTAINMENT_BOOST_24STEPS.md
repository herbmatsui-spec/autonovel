# AutoNovel 実装計画書 P2: エンタメ演出強化・マルチジャンル＆配信・掲示板演出 (全24ステップ)

**対象領域**: Phase 2 (Entertainment Boost, Multi-Genre Expansion & Anti-Recursion)  
**目的**: 追放ざまぁ一辺倒だったオープニング構成を「現代ダンジョン配信」「悪役令嬢・溺愛」「スローライフ」等へ拡張し、読者を熱狂させる「配信コメント・掲示板演出」生成器を追加。さらに `generator.py` と `episode_pipeline.py` の危険な循環呼び出しを解消し、テストスイートを健全化する。  
**前提条件**: 各ステップは単一ファイル・単一責任で完結し、低性能なLLMでも1ステップずつ順番に適用・検証可能。

---

## 📋 ステップ一覧マトリクス

| ステップ | レイヤー | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Config | `src/config/opening_rules.py` | [MODIFY] `OPENING_EPISODE_TARGETS` をジャンル別辞書へ拡張 |
| **Step 2** | Config | `src/config/opening_rules.py` | [MODIFY] 現代ダンジョン・悪役令嬢特有のクリフハンガー辞書追加 |
| **Step 3** | Prompt | `prompts/templates/narrative/opening_ep01_dungeon.j2` | [NEW] 現代ダンジョン配信特化の第1話開幕プロンプト作成 |
| **Step 4** | Prompt | `prompts/templates/narrative/opening_ep01_villainess.j2` | [NEW] 悪役令嬢・断罪回避特化の第1話開幕プロンプト作成 |
| **Step 5** | Agent | `src/agents/writing/opening_booster.py` | [MODIFY] ジャンル名に応じたテンプレート動的ロード処理を実装 |
| **Step 6** | Test | `tests/unit/agents/test_opening_booster_multigenre.py` | [NEW] ジャンル別開幕エピソード生成プロンプトの単体テスト作成 |
| **Step 7** | Schema | `src/models/social_reaction.py` | [NEW] 配信コメント・掲示板演出のデータスキーマ定義 |
| **Step 8** | Prompt | `prompts/templates/narrative/stream_comment_generation.j2` | [NEW] 同接・リスナーの草生え・驚愕コメント生成プロンプト作成 |
| **Step 9** | Prompt | `prompts/templates/narrative/forum_thread_generation.j2` | [NEW] 5ちゃんねる/まとめ風掲示板スレッド生成プロンプト作成 |
| **Step 10** | Service | `src/services/prose/social_reaction_generator.py` | [NEW] 本文のハイライトに応じた演出ブロック生成器を実装 |
| **Step 11** | Test | `tests/unit/services/test_social_reaction_generator.py` | [NEW] 配信コメント・掲示板生成エンジンの単体テスト作成 |
| **Step 12** | Agent | `src/agents/writing/episode_writer.py` | [MODIFY] 本文の山場直後に演出ブロックを自動注入するオプション追加 |
| **Step 13** | Pipeline | `src/agents/writing/generator.py` | [MODIFY] 循環呼び出しを解体し単発執筆関数 `_write_single_episode_core` 新設 |
| **Step 14** | Pipeline | `src/agents/writing/generator.py` | [MODIFY] `generate_episodes` がパイプラインを経由せず単発関数を呼ぶよう改修 |
| **Step 15** | Pipeline | `src/agents/episode_pipeline.py` | [MODIFY] ループ内で `self.agent._write_single_episode_core` を直接呼出 |
| **Step 16** | Test | `tests/unit/agents/test_episode_pipeline_no_recursion.py` | [NEW] 無限再帰が発生しないことを保証するモック単体テスト作成 |
| **Step 17** | TestFix | `tests/unit/marketing/test_marketing_ctr_router.py` | [MODIFY] P1スキーマに同期してルーターテストをALL GREEN復旧 |
| **Step 18** | TestFix | `tests/unit/services/test_editor_autosave.py` | [MODIFY] チェックポイント保存ロジックの非同期モックを修正しテスト復旧 |
| **Step 19** | TestFix | `tests/unit/agents/test_erotic_pipeline.py` | [MODIFY] 破損したエロティック整合性テストをv5基準に更新/モック化 |
| **Step 20** | TestFix | `tests/unit/services/test_stripe_payment.py` | [MODIFY] Stripe Webhookの署名検証モックを修正しテスト復旧 |
| **Step 21** | Component | `frontend/src/components/editor/SocialReactionModal.tsx` | [NEW] 配信コメント・掲示板演出のプレビュー＆手動挿入モーダル作成 |
| **Step 22** | Toolbar | `frontend/src/components/editor/EditorToolbar.tsx` | [MODIFY] 「💬 配信/掲示板演出挿入」ボタンをツールバーへ追加 |
| **Step 23** | E2E | `tests/integration/test_multigenre_dungeon_stream.py` | [NEW] 現代ダンジョン配信作品の企画からコメント付き執筆までの結合テスト |
| **Step 24** | Verify | CI / 全テスト実行 (`pytest`) | `fail_now.txt` のエラー全件解消を確認 |

---

## 🛠️ 各ステップ詳細手順（1〜24）

### Step 1: `OPENING_EPISODE_TARGETS` のマルチジャンル拡張
- **対象ファイル**: `src/config/opening_rules.py`
- **目的**: 追放ざまぁ専用だった開幕ターゲットを、現代ダンジョン・悪役令嬢・スローライフへ拡張。
- **実装内容**:
  ```python
  GENRE_OPENING_TARGETS: dict[str, dict[int, str]] = {
      "banish_fantasy": {
          1: "理不尽な追放・虐げの提示 → どん底の中で手に入れた未知の力/転機 → 絶叫または冷笑で引く",
          2: "旧勢力の手の届かない場所への到達 → チート能力の初発現 → 驚くヒロイン/観察者で引く",
          3: "追放者側の困窮の描写（ざまぁの萌芽） → 主人公の圧倒的活躍 → 評価の急上昇で引く",
      },
      "dungeon_stream": {
          1: "底辺配信者・同接1人の絶望 → 未知の隠し部屋/ユニークスキル覚醒 → 配信切り忘れで引く",
          2: "同接急増・コメント欄の阿鼻叫喚 → ありえないボス瞬殺 → トレンド1位突入で引く",
          3: "大手配信者/ギルドの接触・スカウト → マイペースな無自覚配信 → 衝撃の次回予告で引く",
      },
      "villainess": {
          1: "婚約破棄・断罪イベントの開幕 → 前世記憶/破滅フラグの完全自覚 → 華麗な逆転論破で引く",
          2: "王都離脱・新天地での実力発揮 → 冷酷だった隣国貴族/王子の急接近で引く",
          3: "元婚約者側の領地没落・焦燥 → 主人公の事業大成功・溺愛確定で引く",
      },
  }
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.config.opening_rules import GENRE_OPENING_TARGETS; assert 'dungeon_stream' in GENRE_OPENING_TARGETS; print('OK')"
  ```

---

### Step 2: ジャンル別クリフハンガー辞書追加
- **対象ファイル**: `src/config/opening_rules.py`
- **目的**: 配信系（「同接」「バズ」「切り忘れ」）や悪役令嬢系（「婚約破棄」「冷徹な視線」）の引きキーワードを追加。
- **検証コマンド**:
  ```powershell
  python -c "from src.config.opening_rules import CLIFFHANGER_TRIUMPH_KEYWORDS; assert '同接' in CLIFFHANGER_TRIUMPH_KEYWORDS or 'バズ' in CLIFFHANGER_TRIUMPH_KEYWORDS; print('OK')"
  ```

---

### Step 3: 現代ダンジョン配信特化の第1話プロンプト作成
- **対象ファイル**: `prompts/templates/narrative/opening_ep01_dungeon.j2` (新規作成)
- **目的**: 同接1人・最下層での孤立、隠しスキル覚醒、配信の枠閉じ忘れというカクヨム現代ファンタジーの鉄板導入を強制。
- **検証コマンド**:
  ```powershell
  python -c "import jinja2; jinja2.Template(open('prompts/templates/narrative/opening_ep01_dungeon.j2', encoding='utf-8').read()); print('Template OK')"
  ```

---

### Step 4: 悪役令嬢特化の第1話プロンプト作成
- **対象ファイル**: `prompts/templates/narrative/opening_ep01_villainess.j2` (新規作成)
- **目的**: 舞踏会での理不尽な断罪、記憶覚醒、ヒロインと王子の浅薄さの見抜き、爽快な退場を演出。
- **検証コマンド**:
  ```powershell
  python -c "import jinja2; jinja2.Template(open('prompts/templates/narrative/opening_ep01_villainess.j2', encoding='utf-8').read()); print('Template OK')"
  ```

---

### Step 5: `OpeningBoosterAgent` のジャンル動的切り替え
- **対象ファイル**: `src/agents/writing/opening_booster.py`
- **目的**: `genre` 引数に基づき、対応するテンプレート（`opening_ep01_dungeon.j2` 等）を自動選択してレンダリング。
- **検証コマンド**:
  ```powershell
  python -c "from src.agents.writing.opening_booster import OpeningBoosterAgent; agent = OpeningBoosterAgent(); print('Booster OK')"
  ```

---

### Step 6: マルチジャンル開幕エージェント単体テスト
- **対象ファイル**: `tests/unit/agents/test_opening_booster_multigenre.py` (新規作成)
- **目的**: ジャンルごとに適切なプロンプトが構築され、クリフハンガー評価が正しく走るかを検証。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/agents/test_opening_booster_multigenre.py -v
  ```

---

### Step 7: 配信コメント・掲示板スキーマ定義
- **対象ファイル**: `src/models/social_reaction.py` (新規作成)
- **目的**: `StreamComment(user: str, text: str, timestamp: str)` および `ForumPost(res_num: int, name: str, body: str)` をPydantic定義。
- **検証コマンド**:
  ```powershell
  python -c "from src.models.social_reaction import StreamComment, ForumPost; print('Schema OK')"
  ```

---

### Step 8: 配信リスナーコメント生成プロンプト作成
- **対象ファイル**: `prompts/templates/narrative/stream_comment_generation.j2` (新規作成)
- **目的**: 直前の主人公の規格外アクションに対する視聴者のリアルタイムな草生え（「ｗｗｗ」「！？」「おい待て」「何だこれ」）を20〜30件生成。
- **検証コマンド**:
  ```powershell
  python -c "import jinja2; jinja2.Template(open('prompts/templates/narrative/stream_comment_generation.j2', encoding='utf-8').read()); print('Template OK')"
  ```

---

### Step 9: 5ch風掲示板スレッド生成プロンプト作成
- **対象ファイル**: `prompts/templates/narrative/forum_thread_generation.j2` (新規作成)
- **目的**: 「【悲報】初心者配信者さん、ソロでドラゴンをボコってしまう」といったスレタイとレスを自動生成。
- **検証コマンド**:
  ```powershell
  python -c "import jinja2; jinja2.Template(open('prompts/templates/narrative/forum_thread_generation.j2', encoding='utf-8').read()); print('Template OK')"
  ```

---

### Step 10: 演出ブロック生成器の実装
- **対象ファイル**: `src/services/prose/social_reaction_generator.py` (新規作成)
- **目的**: LLMを呼び出して配信コメントまたは掲示板スレを生成し、テキスト形式にフォーマットするサービス。
- **検証コマンド**:
  ```powershell
  python -c "from src.services.prose.social_reaction_generator import SocialReactionGenerator; print('Generator OK')"
  ```

---

### Step 11: 演出ブロック生成器の単体テスト
- **対象ファイル**: `tests/unit/services/test_social_reaction_generator.py` (新規作成)
- **目的**: LLMモックを用いて配信コメントブロックの文字列整形（`【配信コメント】\n: ｗｗｗ`）が正しく返ることを検証。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/services/test_social_reaction_generator.py -v
  ```

---

### Step 12: `EpisodeWriter` への演出挿入フック追加
- **対象ファイル**: `src/agents/writing/episode_writer.py`
- **目的**: ダンジョン配信ジャンル等の場合、戦闘クライマックス後に自動で配信コメントブロックを本文へ結合する。
- **検証コマンド**:
  ```powershell
  python -c "from src.agents.writing.episode_writer import EpisodeWriter; print('Writer Hook OK')"
  ```

---

### Step 13: `WritingGenerator` の単発執筆コア関数の新設
- **対象ファイル**: `src/agents/writing/generator.py`
- **目的**: 循環呼び出しを断ち切るため、1話分の執筆実処理を行う `_write_single_episode_core` を独立して実装。
- **実装方針**:
  - `OpeningBoosterAgent`（1〜3話）または `EpisodeWriter`（4話以降）を直接呼び出し、本文をDBに保存して文字数を返す。
- **検証コマンド**:
  ```powershell
  python -c "from src.agents.writing.generator import WritingGenerator; print(hasattr(WritingGenerator, '_write_single_episode_core'))"
  ```

---

### Step 14: `WritingGenerator.generate_episodes` の改修
- **対象ファイル**: `src/agents/writing/generator.py`
- **目的**: `generate_episodes` 内で `EpisodePipeline` を呼ばず、`_write_single_episode_core` を直接呼ぶように変更。
- **検証コマンド**:
  ```powershell
  python -c "from src.agents.writing.generator import WritingGenerator; print('Generator generate_episodes OK')"
  ```

---

### Step 15: `EpisodePipeline.run` の呼び出し先更新
- **対象ファイル**: `src/agents/episode_pipeline.py`
- **目的**: ループ内で `self.agent.generate_episodes` ではなく `self.agent._write_single_episode_core` を呼び出す。
- **検証コマンド**:
  ```powershell
  python -c "from src.agents.episode_pipeline import EpisodePipeline; print('Pipeline OK')"
  ```

---

### Step 16: 無限再帰防止の単体テスト
- **対象ファイル**: `tests/unit/agents/test_episode_pipeline_no_recursion.py` (新規作成)
- **目的**: `start_ep=1, end_ep=2` を実行した際に、再帰呼び出しが発生せず2回のみ実行されることを検証。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/agents/test_episode_pipeline_no_recursion.py -v
  ```

---

### Step 17: マーケティングルーターテストの復旧
- **対象ファイル**: `tests/unit/marketing/test_marketing_ctr_router.py`
- **目的**: P1で変更されたスキーマにテストの入力・アサーションを合わせ、`test_generate_viral_titles_endpoint` を通過させる。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/marketing/test_marketing_ctr_router.py -v
  ```

---

### Step 18: エディタオートセーブテストの復旧
- **対象ファイル**: `tests/unit/services/test_editor_autosave.py`
- **目的**: `test_writing_manager_saves_checkpoint` のセッション管理モックを修正し、テストを通過させる。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/services/test_editor_autosave.py -v
  ```

---

### Step 19: エロティックパイプラインテストの整理・復旧
- **対象ファイル**: `tests/unit/agents/test_erotic_pipeline.py`
- **目的**: v5のモデル変更に伴い不整合を起こしていたアサーションを修復し、テストを通過させる。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/agents/test_erotic_pipeline.py -v
  ```

---

### Step 20: Stripe Webhookテストの復旧
- **対象ファイル**: `tests/unit/services/test_stripe_payment.py`
- **目的**: `test_stripe_webhook_grants_credits` のイベントペイロードとクレジットサービスのモックを同期して復旧。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/services/test_stripe_payment.py -v
  ```

---

### Step 21: 配信コメント・掲示板挿入モーダル作成
- **対象ファイル**: `frontend/src/components/editor/SocialReactionModal.tsx` (新規作成)
- **目的**: 生成されたコメント一覧を編集・プレビューし、現在のカーソル位置へワンクリック挿入するUI。
- **検証コマンド**:
  ```powershell
  cd frontend; npx tsc --noEmit; cd ..
  ```

---

### Step 22: エディタツールバーに演出ボタン配置
- **対象ファイル**: `frontend/src/components/editor/EditorToolbar.tsx`
- **目的**: ツールバーに「💬 配信/掲示板演出」ボタンを追加し、モーダルを起動可能にする。
- **検証コマンド**:
  ```powershell
  cd frontend; npx tsc --noEmit; cd ..
  ```

---

### Step 23: 現代ダンジョン配信E2E結合テスト
- **対象ファイル**: `tests/integration/test_multigenre_dungeon_stream.py` (新規作成)
- **目的**: 現代ダンジョンジャンルでの企画 → 開幕1話執筆 → 配信コメント演出結合 → カクヨム整形コピーまでをE2E検証。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/integration/test_multigenre_dungeon_stream.py -v
  ```

---

### Step 24: CI全テスト実行確認
- **対象ファイル**: ワークスペース全体
- **目的**: `pytest` を実行し、`fail_now.txt` に記録されていたエラーが解消され、主要テストがパスすることを確認。
- **検証コマンド**:
  ```powershell
  python -m pytest tests/unit/ -q
  ```
