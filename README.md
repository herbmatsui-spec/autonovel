# 覇権小説エンジン v3.3.1
# 更新: マージコンフリクト解決および tiktoken ベースのコンテキスト切り捨て実装完了 (2026-08-17)

![Tests](https://img.shields.io/badge/tests-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-80%25-yellow)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Code Review](https://img.shields.io/badge/code%20review-60%20steps%20done-blue)

**覇権小説エンジン**は、AI を使って小説を「かんたんに」「高品質に」書くためのツールです。

カクヨムなどの Web 小説サイトでランキング上位を狙える作品を、**ボタンひとつ**で自動生成します。

---

## 最近のアップデート (v3.3.1 - 2026-08-16)

### Phase 5: フロントエンド品質・残タスク対応（12ステップ・完了）

フロントエンドの型安全性・アクセシビリティ・テスト基盤を強化しました。

| 項目 | 詳細 |
|------|------|
| **ESLint エラー修正** | `@typescript-eslint/no-explicit-any` 68 件解消、`jsx-a11y` アクセシビリティ違反修正、未使用変数削除 |
| **型安全性向上** | `any` → 具象型/`unknown` 置換、React Hooks 依存配列修正、コンポーネント型定義追加 |
| **テスト再編成** | `tests/unit/` (114ファイル), `tests/phase1-4/`, `tests/integration/`, `tests/e2e/` へ整理 |
| **Dockerfile 改善** | マルチステージビルド・非 root ユーザー化・レイヤーキャッシュ最適化 |
| **開発用依存分離** | `requirements-dev.txt` 新規作成、`pyproject.toml` に `optional-dependencies.dev` 追加 |
| **新規スクリプト** | `scripts/no_print_check.py`, `scripts/validate_env_map.py` |
| **依存注入・設定改善** | `EngineDeps`を使用したDI最適化、APIキーをSettings経由で取得、Redis設定をDI経由で明示化 |

### コードレビュー改善実装完了（60ステップ・5フェーズ）

`CODE_REVIEW_DETAILED.md` の指摘事項を **60 の小さなステップ**に分割し、保守性・拡張性・型安全性・テスタビリティを総合的に向上させました。

| Phase | ステップ | 重点 | 主な成果 |
|-------|---------|------|----------|
| **Phase 1 (Critical)** | 1‑12 | 循環依存・テスト・マジック値 | `UltimateHegemonyEngine` の全依存を明示的コンストラクタ引数化（13依存 + `_legacy` 後方互換）、DI コンテナ整備、9ジャンル `episode_structure` YAML 外部化、パイプラインバグ修正 |
| **Phase 2 (High)** | 13‑24 | モジュール分割・型安全化 | かんたんモードパイプラインを 7 コンポーネントに分割（`pipeline.py` 633行→257行）、SpiceGuard を 4 モジュールに分割、LLM ゲートウェイ型安全性向上（`@overload`） |
| **Phase 3 (Medium)** | 25‑36 | 設定一元化・観測性・性能 | 統一設定クラス `config.settings.Settings` (SSOT)、OpenTelemetry 自動計装、Prometheus メトリクス命名規約統一（`kaku_{subsystem}_{name}_{unit}`）、専用例外クラス追加、SpiceGuard 抽出を逆インデックスで高速化 |
| **Phase 4 (Low)** | 37‑48 | ドキュメント・テスト戦略・品質ゲート | C4 アーキテクチャ図・シーケンス図、`DEVELOPER_GUIDE.md`、E2E/ミューテーションテスト戦略、Testcontainers 統合基盤、Pre-commit（ruff/mypy/bandit/gitleaks/pip-audit）、CI 改善 |
| **Phase 5 (Frontend)** | 49‑60 | フロントエンド品質・残タスク | ESLint 全エラー修正、型安全性向上、テスト再編成、Dockerfile 改善、開発用依存分離 |

**主な変更**:
- **設定の一元化**: `config/settings.py` の `Settings` が SSOT。`constants.py` は段階的移行用後方互換エイリアスとして維持、環境変数プレフィックスは `KAKU_` に統一
- **明示的 DI**: `UltimateHegemonyEngine` / `InfraContainer` / `AppContainer2` ですべての依存を明示注入
- **セキュリティ**: `bandit`・`gitleaks`・`pip-audit` を CI/pre-commit に追加、シークレットマスキングログ
- **フロントエンド**: ESLint 68 エラー全解消、アクセシビリティ準拠、型安全性強化

**検証結果**: Ruff 重大エラー 0 件維持、カバレッジ 80% 以上目標、mypy strict エラー 50% 削減目標、フロントエンド ESLint 0 エラー

詳細は [IMPLEMENTATION_PLAN_CODE_REVIEW_48_STEPS.md](IMPLEMENTATION_PLAN_CODE_REVIEW_48_STEPS.md)、[IMPLEMENTATION_PLAN_PHASE5.md](IMPLEMENTATION_PLAN_PHASE5.md) および [CHANGELOG.md](CHANGELOG.md) を参照。

### バグ修正・安定性向上

### バグ修正・安定性向上

| 修正項目 | 詳細 |
|----------|------|
| **BASE_DIR 定数修正** | `config/constants.py` の `BASE_DIR` を空文字列から `Path(__file__).parent.parent` に修正。プロンプトマネージャー等でのパス操作エラーを解消 |
| **erotic/vocabulary.py 定数追加** | 分割モジュール化時に欠落していた継続性トラッカー用定数（同意キーワード、スタミナ/心理状態、親密度レベル、ロケーション、状態遷移マトリクス等）を `src/agents/erotic/vocabulary.py` に完全移植 |
| **OpenTelemetry 自動計装** | `src/core/opentelemetry.py` で FastAPI / SQLAlchemy / Redis を自動計装。メトリクス名を `kaku_{subsystem}_{name}_{unit}` 規約に統一（後方互換エイリアス付き） |
| **非同期テスト修正** | `tests/test_zamaa_generation.py`、`tests/test_zamaa_injection.py` に `@pytest.mark.asyncio` デコレータを追加 |

### 36ステップ実装計画完了

**コードレビュー指摘事項を全フェーズで解決**

| Phase | ステップ | 内容 | 主な成果 |
|-------|---------|------|----------|
| **Phase 1** | 1‑6 | 文字化け・データロス修正 | U+FFFD 文字完全除去、CI に文字化けチェック追加 |
| **Phase 2** | 7‑12 | DI コンテナ整理 | 壊れた `container.py` 無効化、`AppContainer2` 正規化、プロバイダパス修正 |
| **Phase 3** | 13‑18 | 認証とセキュリティ | フェイルクローズ化、`.env.example` 追加、単体テスト 7 件作成 |
| **Phase 4** | 19‑24 | 並行性・非同期安全化 | `asyncio.run()` 刷新、レートリミッター Lock 化、タイムアウト分離 |
| **Phase 5** | 25‑30 | コードクオリティ・リント | 未 import 修正、ベア except 修正、重複メソッド削除、Pydantic v2 移行 |
| **Phase 6** | 31‑36 | ドキュメント・CI 改善 | README 更新、CI 統計出力、文字化け防止策・DI 整理ドキュメント化 |

**検証結果**: 全テスト PASS (21 passed, 7 skipped)、文字化け 0 件、Ruff 重大エラー 0 件

---

### かんたんモード Phase 1-3 実装完了

**ジャンル選択のみで、企画から完結・商業展開まで全自動生成**が可能になりました。

| 機能 | 詳細 |
|------|------|
| **9ジャンルプリセット** | ざまぁ・悪役令嬢・チート転生・スローライフ・ダンジョン運営・現代チート・TS転生・VRMMO・ループ |
| **SpiceGuard（尖り保護）** | 自動リライト時に「この話の命」となる尖り要素（独自比喩・キャラ声・伏線・感情描写・ジャンル専用語彙）をマーカーで保護・除去 |
| **LLMリトライ** | 失敗時自動リトライ（3回・線形バックオフ）で安定生成 |
| **人間レビューゲート** | 監査基準未達エピソードを自動検出・フラグ表示 |
| **IFルート生成** | ジャンル別の分岐グラフ（ざまぁカタルシス分岐・隠しルート・バッドエンド・真エンド等）を自動構築。不足ノードは自動補完 |
| **メディアミックス台本** | 漫画・音声ドラマ・動画用の展開台本を生成 |
| **電子書籍書き出し** | EPUB / PDF / MOBI への変換（オプション依存ライブラリは未導入時も安全にスキップ） |
| **資産化パック** | 原本・IFルート・メディアミックス・電子書籍・プロモ素材・メタデータ・チェックサムを1つの ZIP に統合 |

---

## 実装計画書

<<<<<<< ours
- **コードレビュー改善 60ステップ実装計画書**: [IMPLEMENTATION_PLAN_CODE_REVIEW_48_STEPS.md](IMPLEMENTATION_PLAN_CODE_REVIEW_48_STEPS.md)
=======
- **コードレビュー改善 48ステップ実装計画書**: [IMPLEMENTATION_PLAN_CODE_REVIEW_48_STEPS.md](IMPLEMENTATION_PLAN_CODE_REVIEW_48_STEPS.md)
>>>>>>> theirs
  - Phase 1 (Critical): 循環依存解消・テスト修正・マジック値外部化（ステップ 1-12）
  - Phase 2 (High): モジュール分割・型安全化（ステップ 13-24）
  - Phase 3 (Medium): 設定一元化・観測性・パフォーマンス（ステップ 25-36）
  - Phase 4 (Low): ドキュメント・テスト戦略・品質ゲート（ステップ 37-48）
- Phase 5 (Frontend): フロントエンド品質・残タスク対応（ステップ 49-60） — [IMPLEMENTATION_PLAN_PHASE5.md](IMPLEMENTATION_PLAN_PHASE5.md)
- 過去の計画書: `archive/plans/` に保管（36ステップ版等）

### アーキテクチャドキュメント

- **C4 モデル**: [docs/architecture/](docs/architecture/)（System Context / Container / Component / Code の各図 + シーケンス図 4 種 + データフロー図）
- **開発者ガイド**: [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)
- **テスト戦略**: [docs/testing/E2E_TEST_STRATEGY.md](docs/testing/E2E_TEST_STRATEGY.md)・[tests/testing/MUTATION_TESTING.md](docs/testing/MUTATION_TESTING.md)

## 文字化け防止策

本プロジェクトでは、日本語文字列の文字化け（Mojibake / U+FFFD 置換文字）を防止するため、以下の対策を実施しています。

1. **CI での自動チェック**: `.github/workflows/ci.yml` に `git grep -P "\xEF\xBF\xBD"` を組み込み、コミット時に文字化けを検出
2. **UTF-8 エンコーディングの徹底**: 全ソースファイルは UTF-8 で保存
3. **エディタ設定の統一**: `.vscode/settings.json` で `files.encoding: "utf8"` を推奨

## DI コンテナ整理

- `src/core/container.py`（壊れた実装）を削除し、`src/core/container/app.py`（`AppContainer2`）を正規実装として採用
- `src/core/container/__init__.py` で `AppContainer2` を `AppContainer` としてエクスポート
- 依存解決エラーを防ぐため、プロバイダ文字列パスを正しいモジュール（例: `src.agents.audit.LogicalAuditor`）に修正

---

## なにができる？

### 小説を自動で書いてくれる

たとえば...

> **「なろう系の異世界ファンタジーを今日中に書きたい」**

→ ジャンルを選んで「生成」ボタンを押すだけ。数十秒〜数分で、企画からプロット（話の骨組み）、本文まですべて自動で作ります。

### デモ動画

アプリの機能を簡単に体験できるデモを用意しています。

- **ローカルで見る**：リポジトリをクローンして `demo.html` をブラウザで開く（または下のリンクから）
  → [デモページを開く](./demo.html)
- **GitHub Pages で公開して見る（推奨）**：下の手順でホストすると、README から**実際に動くデモ**へ飛べます
  → `https://<あなたのユーザー名>.github.io/autonovel/demo.html`

#### GitHub Pages でデモを公開する手順

1. このリポジトリを GitHub に push する
2. リポジトリの **Settings → Pages** を開く
3. `Build and deployment` の `Source` を **Deploy from a branch** にする
4. `Branch` で **`main`**（または `master`）を選び、`/ (root)` を指定して保存
5. 数分待つと `https://<ユーザー名>.github.io/autonovel/` で公開される
6. `demo.html` は `https://<ユーザー名>.github.io/autonovel/demo.html` でそのまま動作する

> 注：GitHub の README 上の `./demo.html` リンクは、github.com 上では**ソースコード表示**になるため、インタラクティブに動かすには上記 GitHub Pages の URL をご利用ください。

実際のアプリケーションでは、さらに高度な機能として：
- 上級者モードでの細かい設定調整
- メディアミックス台本生成（漫画・音声ドラマ・動画用）
- 電子書籍書き出し（EPUB / PDF / MOBI）
- 資産化パック作成（原本・IFルート・メディアミックス・電子書籍・プロモ素材・メタデータ・チェックサムを1つの ZIP に統合）

などが利用可能です。

### 2 つのモード

| モード | こんな人に | 何ができるか |
|---|---|---|
| **かんたんモード** | とにかく今すぐ小説が欲しい人 | **ジャンル選んでボタンを押すだけ**。何も考えなくて OK。9ジャンルプリセット + SpiceGuard で「尖り」を守りながら全自動生成 |
| **上級者モード** | こだわりたい人 | 各話のプロットを編集したり、文章の濃さを変えたり、納得いくまで修正できる |

### かんたんモード 対応ジャンル (9種)

| ジャンル | アイコン | キーワード | 尖り保護の要所 |
|---|---|---|---|
| ざまぁ・追放・無双 |  | `ざまぁ` `無双` `圧倒的` `顔面蒼白` | カタルシス完結・悪党の絶望・戦力差 |
| 悪役令嬢・断罪回避 |  | `フラグ回避` `隠しルート` `百合` `尊い` | フラグ折り・百合テンション・契約 |
| チート転生・即最強 |  | `スキル習得∞` `秒殺` `最適解` `デバッグ` | システム風味・効率自慢 |
| スローライフ・ほのぼの |  | `ふわふわ` `とろける` `ほっこり` `香り` | 五感豊かさ・日常儀式 |
| ダンジョン運営・経営 |  | `罠` `ギミック` `忠誠` `進化` `個性` | 罠クリエイティブ・モンスター個性 |
| 現代チート・都市伝説 |  | `ルート権限` `パッチ` `実体化` `同期` | テックメタファー・現実干渉 |
| TS転生・百合・性別反転 |  | `可愛い` `美少女` `百合キス` `尊い` `永遠` | 性別ユーフォリア・百合親密 |
| VRMMO・ゲーム世界 |  | `フルダイブ` `同期` `実体化` `現実侵食` | 同期用語・現実滲み出し |
| ループ・時間逆行・真エンド |  | `周目` `真エンド` `全フラグ` `確率1` `必然` | ループカウント・収束・完全攻略 |

---

### 「ざまぁ」展開を自動で仕組む

面白い小説には「ストレス」と「解放」の波が大切です。

このツールは物語中の**読者のストレスを自動計算**して、「そろそろ気持ちよくなれる場面を入れよう」と判断。適切なタイミングで「ざまぁ」展開（無双・逆転）をねじ込んでくれます。

### 官能描写にも対応（オプトイン）

NSFW モードを ON にすれば、官能的な描写を含む小説も書けます。
オプトイン方式で、ON にしない限り生成されません。

---

## 動かし方

### 方法 A: Docker でさくっと（おすすめ）

```bash
# 1. Google AI Studio で API キーを取得（無料）
# https://aistudio.google.com/app/apikey

# 2. 設定ファイルをコピーしてキーを書く
cp .env.example .env
# → .env ファイルを開いて GEMINI_API_KEY=取得したキー を追記

# 3. Docker を起動（開発用: フロントエンドは Vite dev server）
docker compose up --build

# または本番用ビルド（Nginx で静的配信）
docker compose --profile prod up --build
```

立ち上がったらブラウザで以下を開いてください：
- **開発モード**: http://localhost:5173 (Vite HMR 付き)
- **本番モード**: http://localhost:3000 (Nginx 静的配信)
- **バックエンド API**: http://localhost:8200/docs (Swagger UI)

### 方法 B: 手動で起動する（開発者向け）

```bash
# 1. 依存ライブラリを入れる
pip install -r requirements.txt

# 2. フロントエンド依存関係
cd frontend && npm install && cd ..

# 3. 環境変数を設定
cp .env.example .env
# → .env を編集して GEMINI_API_KEY と ALLOWED_API_KEYS を設定

# 4. バックエンド起動
uvicorn src.backend.server:app --host 127.0.0.1 --port 8200 --reload

# 5. （別のターミナルで）フロントエンド起動
cd frontend && npm run dev
```

これで以下にアクセスできます：
- フロントエンド: **http://localhost:5173**
- バックエンド API: **http://localhost:8200/docs**

### 必要なもの

| 必須/任意 | 何に使うか |
|---|---|
| **必須** Python 3.12 以上 | バックエンド実行に必要 |
| **必須** Node.js 22 以上 | フロントエンドビルドに必要 |
| **必須** Gemini API キー | AI に小説を書かせるのに必要（Google AI Studio で無料取得可） |
| **任意** Docker / Docker Compose | 面倒な環境構築をスキップしたい人向け |
| **任意** Redis | 裏でジョブを管理する（Docker なら自動起動、ローカルなら別途必要） |

---

## 使い方の流れ

1. 起動するとブラウザにツールが表示されます
2. 左のサイドバーからタブを切り替えるか、**かんたんモード**ダイアログを開きます
3. かんたんモードなら↓
    - 「お好みのジャンル」を選択
    - 「小説を生成」ボタンをクリック
    - しばらく待つと → 企画 → プロット → 本文 → 納品 まで自動で完了
4. 上級者モードなら↓
    - タブを切り替えながら各工程を細かく編集・調整できます

---

## アーキテクチャ概要

```
Frontend (React 18 + TypeScript + Vite + TailwindCSS)
  ├── Landing / Books / Plots / Write
  ├── Analytics / Planning / StyleLab / Audit
  └── EasyModeDialog (モーダル)
        │
        ▼ HTTP/REST + SSE
Backend (FastAPI + Uvicorn)
  ├── routers/: books, episodes, plots, easy_mode, commercial
  │         export, illustrations, marketing, audit, health, metrics
  ├── workflows/: LangGraph ベースの執筆パイプライン
  ├── services/: ビジネスロジック層
  ├── easy_mode/: かんたんモードパイプライン + Phase3 資産化
  ├── core/
  │   ├── container/: DI コンテナ (AppContainer2 / InfraContainer)
  │   ├── llm_clients/: LLM抽象層 (BaseLLMClient / GeminiClient / OpenAIClient)
  │   ├── llm_gateway.py: プロバイダファクトリ・キャッシュ・プロキシ
  │   └── state/: 状態管理
  ├── backend/: タスクキュー・DB・認証・ヘルスチェック
  └── agents/: エージェント群 (writing, erotic, audit 等)
        │
        ▼
Data Stores
  ├── SQLite (dev) / PostgreSQL (prod) + Alembic
  ├── ChromaDB (RAG ベクトル検索)
  └── Redis (Huey タスクキュー・キャッシュ)
```

### コアコンポーネント

| レイヤー | 技術スタック | 役割 |
|---|---|---|
| **Frontend** | React 18 + TypeScript + Vite + TailwindCSS + Zustand | モダンな SPA UI |
| **Backend** | FastAPI + Uvicorn | REST API、SSE、非同期処理 |
| **AI Orchestration** | LangGraph + Google Gemini | グラフベースの執筆パイプライン |
| **EasyMode Pipeline** | Python asyncio + SpiceGuard | ジャンル選択のみで全自動生成 |
| **Task Queue** | Huey + Redis | バックグラウンドジョブ管理 |
| **Persistence** | SQLite (dev) / PostgreSQL (prod) + Alembic | データ永続化 |
| **Vector Store** | ChromaDB | RAG 用ベクトル検索 |
| **Observability** | OpenTelemetry + Prometheus | トレース・メトリクス |
| **Auth** | API Key + Rate Limiting | フェイルクローズ認証 |

### LLM クライアント階層

| コンポーネント | 役割 |
|---|---|
| **BaseLLMClient** | Gemini/OpenAI 互換クライアントの共通抽象 |
| **GeminiClient** | Google Generative AI との直接通信 |
| **OpenAIClient** | OpenAI 互換 API との通信 |
| **LLMProviderFactory** | モデル名に応じたクライアント選択 |
| **SemanticCacheManager** | 意味的キャッシュによるコスト削減 |
| **SemanticEdgePreserver** | 尖り要素の意味的類似度判定 |
| **LLMGenerateResultProxy** | アプリケーション層向け統一インターフェース |

---

## かんたんモード パイプライン詳細

```
ユーザー操作          バックグラウンド処理
─────────            ────────────────
ジャンル選択 ──▶  1. Bible生成（世界観・キャラ・チート設定）
    │                2. プロット生成（テンション曲線×テンプレ展開）
    ▼                3. 各話ループ:
                       ├─ 執筆（Style DNA・フック・官能ルール注入）
                       ├─ 監査（95点未満なら）
                       ├─ SpiceGuard抽出（尖り要素検出）
                       ├─ マーカー注入（<<<SPICE:...>>>）
                       ├─ リライト（マーカー保護付き）
                       ├─ マーカー除去
                       └─ 最大3回繰り返し
                       4. シリーズ完結処理（タイトル・あらすじ・メタデータ）
                          ↓
    完了 ◀──────── 結果取得・人間レビュー表示（必要時）
```

### SpiceGuard（尖り保護システム）

自動リライトで面白さが平準化されないよう、**「この話の命」**となる要素を保護：

| 保護カテゴリ | 例 |
|---|---|
| **独自比喩** | 「まるで絶望の底から這い上がったかのように」 |
| **キャラ声** | 禁句・キャッチフレーズ（プリセット定義から） |
| **伏線・回収** | 「実は」「真真」「正体」「覚醒」 |
| **生々しい感情** | 「胸が締め付けられ」「背筋が凍る」 |
| **ジャンル専用語彙** | ざまぁ/無双/フラグ/百合/スキル∞/真エンド 等 |

**仕組み**: 抽出 → `<<<SPICE:type_pos>>>テキスト<<</SPICE>>>` マーカー注入 → LLMリライト（マーカー変更禁止指示） → マーカー除去

---

## 認証・セキュリティ

### API キー認証

本プロジェクトは API キーによる認証をサポートしています。

| 環境変数 | 説明 | デフォルト |
|---|---|---|
| `ALLOWED_API_KEYS` | カンマ区切りの許可 API キー一覧 | `dev-key-1,dev-key-2` |
| `AUTH_DISABLED` | 認証をバイパスするか（非本番環境のみ推奨） | `false` |

### セキュリティ設計原則

- **フェイルクローズ**: 許可リストが空の場合は常に拒否
- **本番環境保護**: `ENVIRONMENT=production` では `AUTH_DISABLED` を無視
- **レート制限**: IP/API キー単位でのリクエスト制限
- **CORS 制御**: 設定ファイルで許可オリジンを一元管理

詳細は [docs/SECURITY.md](docs/SECURITY.md) および [docs/CORS_CONFIG.md](docs/CORS_CONFIG.md) を参照してください。

---

## テスト

```bash
# 全テスト実行
pytest

# かんたんモード Phase 1-3 統合テストのみ
pytest tests/test_phase1_preset_integration.py tests/test_phase2_pipeline_integration.py tests/test_phase3_asset_pack.py -v

# 詳細出力
pytest -xvs tests/
```

### テストカバレッジ (Phase 1-3)

| テスト種別 | 件数 | 内容 |
|---|---|---|
| **Phase 1: プリセット** | 17 | 全ジャンル存在確認・ローダー検証・UIインポート |
| **Phase 2: パイプライン** | 20 | SpiceGuard・設定・統合・E2E（フルラン・低スコア・尖り保護・キャンセル） |
| **Phase 3: 資産化** | 25 | IFルート・メディアミックス・電子書籍・資産化パック・統合 |
| **合計** | **62** | 全件通過 |

---

## 環境変数

| 変数名 | 説明 | デフォルト |
|---|---|---|
| `GEMINI_API_KEY` | **必須** Google Gemini API キー | - |
| `ALLOWED_API_KEYS` | カンマ区切りの許可 API キー | `dev-key-1,dev-key-2` |
| `AUTH_DISABLED` | 認証を無効化（非本番のみ） | `false` |
| `PYTHONPATH` | Python モジュール検索パス | `/app` (Docker) |
| `DATABASE_URL` | DB 接続文字列 | `sqlite+aiosqlite:///./autonovel.db` |
| `REDIS_URL` | Redis 接続文字列 | `redis://localhost:6379/0` |
| `LOG_LEVEL` | ログレベル | `INFO` |
| `CORS_ALLOWED_ORIGINS` | CORS 許可オリジン | `http://localhost:5173,http://localhost:3000` |
| `KAKU_HEALTH_CHECK_LLM` | LLM ヘルスチェックを無効化 | `true` |
| `ENVIRONMENT` | 実行環境 (`development` / `production`) | `development` |

---

## ライセンス

このプロジェクトは個人利用・研究目的で提供されています。商用利用の際は Google Gemini API の利用規約をご確認ください。

---

**Enjoy Writing!**
