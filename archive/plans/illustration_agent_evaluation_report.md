# イラスト作成サブエージェント 評価レポート

## 1. 評価対象

| 種別 | ファイル | 主要クラス/関数 |
|---|---|---|
| エージェント | [`src/agents/illustration_agent.py`](src/agents/illustration_agent.py:22) | [`IllustrationAgent`](src/agents/illustration_agent.py:22) |
| 画像サービス | [`src/services/image_service.py`](src/services/image_service.py:15) | [`ImageService`](src/services/image_service.py:15) |
| 表紙 | [`src/services/illustration/cover_service.py`](src/services/illustration/cover_service.py:14) | [`CoverGenerator`](src/services/illustration/cover_service.py:14) |
| キャラクター | [`src/services/illustration/character_service.py`](src/services/illustration/character_service.py:14) | [`CharacterIllustrator`](src/services/illustration/character_service.py:14) |
| シーン | [`src/services/illustration/scene_service.py`](src/services/illustration/scene_service.py:21) | [`SceneExtractor`](src/services/illustration/scene_service.py:21) / [`SceneIllustrator`](src/services/illustration/scene_service.py:72) / [`SceneIllustrationService`](src/services/illustration/scene_service.py:101) |
| モデル解決 | [`src/services/illustration/model_selector.py`](src/services/illustration/model_selector.py:1) | [`resolve_model_id`](src/services/illustration/model_selector.py:39) / [`resolve_request_model`](src/services/illustration/model_selector.py:48) / [`is_r15`](src/services/illustration/model_selector.py:34) |
| プロンプト | [`src/services/illustration/prompts.py`](src/services/illustration/prompts.py:1) | [`build_cover_prompt`](src/services/illustration/prompts.py:38) / [`build_scene_prompt`](src/services/illustration/prompts.py:65) / [`build_character_prompt`](src/services/illustration/prompts.py:83) / [`apply_safety_modifier`](src/services/illustration/prompts.py:109) |
| モデル定義 | [`src/models/illustration.py`](src/models/illustration.py:6) | [`IllustrationModel`](src/models/illustration.py:12) / [`SafetyLevel`](src/models/illustration.py:19) / [`IllustrationRequest`](src/models/illustration.py:27) |
| モデルSSOT | [`config/imagen_models.py`](config/imagen_models.py:1) | [`IMAGEN_MODEL_CATALOG`](config/imagen_models.py:32) / [`get_imagen_model_id`](config/imagen_models.py:47) / [`select_imagen_model`](config/imagen_models.py:55) |
| ワークフロー | [`src/backend/workflows/illustration_workflow.py`](src/backend/workflows/illustration_workflow.py:17) | [`IllustrationWorkflow`](src/backend/workflows/illustration_workflow.py:17) |
| ルーター | [`src/backend/routers/illustrations.py`](src/backend/routers/illustrations.py:15) | `/generate` `/batch` |
| DI | [`src/core/container/app.py`](src/core/container/app.py:182) | `image_service` / `illustration_agent` / `illustration_workflow` |
| サーバー | [`src/backend/server.py`](src/backend/server.py:191) | `router_modules` |
| テスト | [`tests/test_illustration_features.py`](tests/test_illustration_features.py:1) / [`tests/test_illustration_agent.py`](tests/test_illustration_agent.py:1) | 全テスト |

---

## 2. 良い点（評価できる点）

### 2.1 モデルID の SSOT 化
[`config/imagen_models.py`](config/imagen_models.py:1) で Imagen のモデルIDを一元管理。コード側は tier キー（`fast` / `quality` / `ultra`）だけを扱い、必ず [`get_imagen_model_id()`](config/imagen_models.py:47) を経由する設計は適切。

### 2.2 AUTO の自動選択ロジック
[`select_imagen_model()`](config/imagen_models.py:55) は `illustration_type` × `safety_level` のコンテキストから tier を選択。
- `cover` / `character` → `ultra`（品質重視）
- `episode` → `fast`（速度・大量生成重視）
- R15 では `fast` を `quality` に引き上げ

という設計は妥当。

### 2.3 モデル解決チェーンの統一
[`resolve_request_model()`](src/services/illustration/model_selector.py:48) で `AUTO` → 自動選択、それ以外 → tier キー → 実モデルID、を一元化。
[`CoverGenerator`](src/services/illustration/cover_service.py:14) / [`CharacterIllustrator`](src/services/illustration/character_service.py:14) / [`SceneIllustrator`](src/services/illustration/scene_service.py:72) / [`IllustrationAgent._generate_episode()`](src/agents/illustration_agent.py:77) で共通利用されており、連鎖は機能している。

### 2.4 DI コンテナ登録
[`src/core/container/app.py`](src/core/container/app.py:182) で `image_service` / `illustration_agent` / `illustration_workflow` の3プロバイダが登録済み。

### 2.5 ルーター登録
[`src/backend/server.py`](src/backend/server.py:191) の `router_modules` に `"src.backend.routers.illustrations"` が含まれており、ルーティングは有効。

### 2.6 プロンプト構築の分離
[`src/services/illustration/prompts.py`](src/services/illustration/prompts.py:1) で [`build_cover_prompt`](src/services/illustration/prompts.py:38) / [`build_scene_prompt`](src/services/illustration/prompts.py:65) / [`build_character_prompt`](src/services/illustration/prompts.py:83) / [`apply_safety_modifier`](src/services/illustration/prompts.py:109) を分離。ジャンル別スタイルヒント・表紙の3バリエーション・R15修飾を実装済み。

### 2.7 シーン抽出のフォールバック設計
[`SceneExtractor.extract_scenes_with_llm()`](src/services/illustration/scene_service.py:47) は LLM 失敗時にヒューリスティックの [`extract_scenes()`](src/services/illustration/scene_service.py:30) にフォールバックする堅牢な実装。

### 2.8 テストの網羅性
[`tests/test_illustration_features.py`](tests/test_illustration_features.py:1) は
- 各サービス（cover / character / scene）
- エージェント全分岐（cover / character / episode / R15 / 不正リクエスト）
- モデル解決（fast / quality / ultra / auto / unknown）
- AUTO × illustration_type × R15 の組み合わせ
- DB 永続化（sqlite 実機）
まで網羅。

---

## 3. 課題・修正が必要な点

### 3.1 テスト import パス不整合（重大・CI影響）

[`tests/test_illustration_agent.py`](tests/test_illustration_agent.py:4) は `autonovel.src.*` から import しているが、[`tests/test_illustration_features.py`](tests/test_illustration_features.py:5) は `src.*` から import している。プロジェクト全体で [`src.*`](src/) 経路が正であり、`test_illustration_agent.py` の `autonovel.src.*` は **PYTHONPATH によっては NameError** で CI が落ちる。

```python
# tests/test_illustration_agent.py:4
from autonovel.src.agents.illustration_agent import IllustrationAgent  # ← 誤り
```

→ `from src.agents.illustration_agent import IllustrationAgent` に統一すべき。

### 3.2 テストのデッドコード・未使用モック

[`tests/test_illustration_agent.py`](tests/test_illustration_agent.py:15-20) では [`mock_llm = mock.AsyncMock()`](tests/test_illustration_agent.py:15) と [`mock_llm.generate.return_value = ...`](tests/test_illustration_agent.py:16) を設定しているが、現在の [`IllustrationAgent.run()`](src/agents/illustration_agent.py:48) は LLM を直接呼ばない（[`SceneIllustrationService`](src/services/illustration/scene_service.py:101) も `llm is not None` でない限り LLM を使わない）。したがって `mock_llm` は完全に未使用。

また [`mock_service.generate.return_value`](tests/test_illustration_agent.py:19) は設定されているが、[`test_illustration_agent_erotic_mode_modifier`](tests/test_illustration_agent.py:40) では `return_value` 未設定のためアサーションが曖昧。

### 3.3 ルーターの `AppContainer` 未 import（バグ）

[`src/backend/routers/illustrations.py`](src/backend/routers/illustrations.py:18-20) は [`AppContainer`](src/core/container/app.py) を使うが、import 文がない。

```python
def get_illustration_workflow():
    container = AppContainer(api_key=os.getenv("GOOGLE_GENAI_API_KEY", ""))
    return container.illustration_workflow()
```

→ 実行時に `NameError: name 'AppContainer' is not defined` になる可能性が高い。
[`make_container()`](src/core/container/app.py) を使う設計と整合させるか、明示的に `from src.core.container.app import AppContainer` を追加する必要がある。

### 3.4 `apply_safety_modifier` の重複 try/except

[`src/services/illustration/prompts.py`](src/services/illustration/prompts.py:115-118) は `safety_level.value == SafetyLevel.R15_CONTENT.value` を try/except で独自に判定している。
一方 [`src/services/illustration/model_selector.py`](src/services/illustration/model_selector.py:34) に [`is_r15()`](src/services/illustration/model_selector.py:34) が既に存在。

→ [`apply_safety_modifier()`](src/services/illustration/prompts.py:109) も `is_r15()` を使うよう統一し、重複を排除すべき（計画書 ステップ18と整合）。

### 3.5 `_save_image()` の URL パス返却バグ（中程度）

[`src/services/image_service.py`](src/services/image_service.py:106) の `return f"/{filepath}"` は、`storage_dir="static/illustrations"` のとき `filepath="static/illustrations/img_xxx.png"` となり、返却値は `"/static/illustrations/img_xxx.png"` でなく `//static/illustrations/img_xxx.png` 相当（Python の `f"/{filepath}"` は `filepath` の先頭に `/` が無ければ結果も `"/"` 始まりで連結されるため、コード上は `"/static/illustrations/img_xxx.png"` にはなる）。

ただし **`save_dir` が絶対パスや先頭 `/` 付きの場合に URL が壊れる** リスクがある（Windows や `/var/...` のようなパスでは `//var/...` になる）。

→ `return f"/{save_dir.strip('/')}/{filename}"` のように正規化すべき（計画書 ステップ21と整合）。

### 3.6 `_generate_episode()` のフォールバックプロンプト脆弱

[`IllustrationAgent._generate_episode()`](src/agents/illustration_agent.py:77-119) は `scene_text` が無く `book_context` にも `title/genre/concept` がない場合、`"Scene illustration for episode None."` というほぼ無意味なプロンプトで生成される。

→ 最低限の generic 視覚要素（"cinematic, atmospheric, no text" 等）を補完するか、`book_context` も `scene_text` も空なら `raise ValueError` して上流で明示的に扱うべき。

### 3.7 `enableErotic` / `enable_r15` のフラグ名不統一

- [`illustration_workflow.py`](src/backend/workflows/illustration_workflow.py:93-97) は `settings.get("enableErotic", False)` を見る
- [`routers/illustrations.py`](src/backend/routers/illustrations.py:35-37) は `request.get("enable_r15")` を見る

→ Easy Mode 経由と API 経由のフラグ命名が統一されておらず、API 単体呼び出し時の R15 が効かない可能性がある。

### 3.8 `_coerce_request` の挙動

[`IllustrationAgent._coerce_request()`](src/agents/illustration_agent.py:40-46) は dict→モデル変換するが、`illustration_type` が文字列で来た場合の `Enum` 化は行わない（[`_type_value()`](src/services/illustration/model_selector.py:13) で後段吸収）。
ルーター経由で呼ばれる場合は既に [`IllustrationRequest`](src/backend/routers/illustrations.py:30) が構築済みなので dict 経由は到達しない。**外部から dict を直接渡す経路がないなら、メソッド自体を削除** する方がシンプル。

### 3.9 `_fake_image_service` の戻り値の固定文字列とテスト現実性

[`tests/test_illustration_features.py`](tests/test_illustration_features.py:117) の `_fake_image_service()` は `"/static/illustrations/fake.png"` を返すが、実 [`ImageService._save_image()`](src/services/image_service.py:95-106) の `f"/{filepath}"` 動作は固定モックでは検証されない（3.5の修正で実 URL が壊れていないか別途テストが必要）。

### 3.10 `illustration_workflow.execute()` の進捗分母

[`src/backend/workflows/illustration_workflow.py`](src/backend/workflows/illustration_workflow.py:46) の `reporter.update_progress(0, 1, ...)` は表紙のみで `0/1`、挿絵生成が有効な場合は複数ステップあるのに分母が `1` 固定。

→ `total_steps` を計算して動的に設定すべき（表紙=1 + 挿絵=n）。

### 3.11 `model_used` アサーション不足

[`tests/test_illustration_features.py`](tests/test_illustration_features.py:148) は `model_used == "imagen-4.0-fast-generate-001"` をアサートしているが、[`tests/test_illustration_agent.py`](tests/test_illustration_agent.py:14) は `model_used` をアサートしていない。
→ AUTO 解決の回帰検知のため、全テストで `model_used` を検証すべき（計画書 ステップ3-4と整合）。

### 3.12 ドキュメント不足

- [`IllustrationAgent`](src/agents/illustration_agent.py:22) は `BaseAgent` が `repo` を持つ前提（[`_persist()`](src/agents/illustration_agent.py:130-148) で `self.repo` 参照）だが、docstring に明記なし。
- [`ImageService.__init__()`](src/services/image_service.py:22) の `api_key` 必須性は docstring にない。

### 3.13 `ImageService.default_model` の二重解決

[`__init__()`](src/services/image_service.py:30) で `get_imagen_model_id(default_model)` に変換済みだが、[`generate()`](src/services/image_service.py:42) 内で再度 `get_imagen_model_id(model or self.default_model)` を呼ぶ。害はないが冗長。

### 3.14 動的解析による呼び出し整合性

`illustration_workflow.execute()` で `chapters = await self.repo.get_chapters(book_id)` を呼んでいるが、**`repo` の型未確認**。`BaseWorkflow` の `self.repo` が `get_chapters` を持っている前提で書かれており、DI 経由で注入される具象クラスに依存する。

---

## 4. 既存改善計画書 ([`plans/illustration_agent_evaluation_fix_plan_24steps.md`](plans/illustration_agent_evaluation_fix_plan_24steps.md:1)) との整合

| 既存ステップ | 評価 | 追加・修正すべき内容 |
|---|---|---|
| 1-4: テスト修正 | OK | **テスト import パスを `autonovel.src.*` → `src.*` に統一**（3.1） |
| 5-12: モデル解決統合 | OK | （追加項目なし、現状計画で十分） |
| 13-16: ルーター/DI | OK | **`AppContainer` import 欠落の修正を追加**（3.3） |
| 17-20: コード品質 | OK | **`apply_safety_modifier` を `is_r15()` 利用に統一**（3.4） |
| 21-24: 軽微修正 | OK | **`_save_image()` の URL 正規化**（3.5）/ **`_generate_episode()` フォールバック改善**（3.6）/ **`enableErotic`/`enable_r15` 統一**（3.7） / **`illustration_workflow` 進捗分母動的化**（3.10） |

---

## 5. 総合スコア（10点満点）

| 観点 | スコア | コメント |
|---|---|---|
| アーキテクチャ設計 | 8/10 | SSOT化・サービス分離・DI登録・モデル解決チェーンが良好。`AppContainer` import 欠落等の一貫性問題あり |
| コード品質 | 7/10 | `_type_value` の重複は解消済みだが `apply_safety_modifier` の try/except が残る。`_save_image` のパス正規化不足 |
| テストカバレッジ | 7/10 | モデル解決・DB永続化・フォールバックまで網羅。ただし import パス不整合で CI 落ちの可能性。`model_used` アサーション不足 |
| 堅牢性 | 7/10 | LLM失敗時フォールバック・AUTO 解決・R15修飾実装済み。`_persist` の例外握り潰しは妥当だが可視性低い |
| ドキュメント | 6/10 | docstring はあるが、`BaseAgent` 前提・API key 必須性等の説明不足 |
| **総合** | **7.0/10** | 設計は健全。バグ・不整合を24ステップ計画通り修正すれば 8.5 まで上がる |

---

## 6. 推奨アクション（即時対応）

1. **`tests/test_illustration_agent.py` の import パスを `autonovel.src.*` → `src.*` に修正**（CIが落ちるため最優先）（3.1）
2. **[`src/backend/routers/illustrations.py`](src/backend/routers/illustrations.py:18) に `from src.core.container.app import AppContainer` を追加**（3.3）
3. **[`src/services/image_service.py`](src/services/image_service.py:106) の `_save_image()` を `f"/{save_dir.strip('/')}/{filename}"` に正規化**（3.5）
4. **[`src/services/illustration/prompts.py`](src/services/illustration/prompts.py:115-118) を `is_r15()` 経由に統一**（3.4）
5. **改善計画書 24 ステップの消化とテスト/Lint/TypeCheck 通過確認**

## 7. 推奨アクション（中期）

- [`_generate_episode()`](src/agents/illustration_agent.py:77) のフォールバックプロンプトで `book_context` が空の場合に generic なシーン指示を返すか、明示的にエラーを送出（3.6）
- `enableErotic` / `enable_r15` のフラグ名を統一し、API/Workflow 双方で同じキーを見るよう修正（3.7）
- [`illustration_workflow.execute()`](src/backend/workflows/illustration_workflow.py:46) の進捗レポート分母を動的に算出（3.10）
- 全テストに `model_used` アサーションを追加し AUTO 解決の回帰検知を強化（3.11）
- `BaseAgent` の `repo` 前提・`ImageService` の `api_key` 必須性を docstring に明記（3.12）

---

## 8. 結論

イラスト作成サブエージェントは **アーキテクチャ・機能としては十分な品質** に達している。

- **達成済み**: モデルID SSOT / AUTO 解像度チェーン / R15 修飾 / LLM フォールバック / DB 永続化 / DI 登録 / ルーター登録 / ジャンル別プロンプト構築

- **残存課題（軽微〜中程度）**: テスト import パス不整合 / `AppContainer` import 欠落 / `_save_image` の URL 正規化不足 / `apply_safety_modifier` の重複コード / フラグ名不統一 / フォールバックプロンプト脆弱

既存の 24 ステップ改善計画は妥当であり、上記の追加修正と合わせれば **CI グリーン & プロダクション品質** を確保できる。総合スコアは現状 **7.0/10**、計画完遂で **8.5/10** を見込む。
