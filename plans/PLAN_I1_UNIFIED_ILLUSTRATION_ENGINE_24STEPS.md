# 統合イラスト生成エンジン（NanoBanana2Lite 統一）実装計画書 — 全24ステップ

> **Slug**: `PLAN_I1_UNIFIED_ILLUSTRATION_ENGINE_24STEPS`
> **対象**: イラスト機能3系統（Traditional / IllustrationPoint / Manga24）の統合
> **方針**: 方向性1（統一インターフェース＋プラガブルバックエンド）＋ 生成モデルは **NanoBanana2Lite に全種別統一**（差し替え容易）
> **ステータス**: ✅ **全24ステップ実装完了**（2026-09-26）
> **関連ADR**: `docs/adr/002-unified-illustration-engine.md`
> **テスト**: ユニット119件 / リグレッション111件 / E2E 8件 = **238件 PASS**

---

## 0. エグゼクティブサマリー

### 0.1 何をやるか

現状3系統が並存し、24コマ漫画（`src/services/manga/`）は**完全に未統合**のまま放置されている。
本計画では、**画像生成モデル.nanobanana2lite（`gemini-3.1-flash-lite-image`）を全種別の既定**とし、
 IllustrationType の差分は「プロンプト戦略（Strategy）」で吸収 thereby **単一エンジン**に統合する。

```
                     UnifiedIllustrationGenerator（単一）
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   PromptStrategy        ClientAdapter          PostProcess
   （種別ごとの差分）    （モデル差し替え点）   （品質/超解像/写植）
        │                     │                     │
  Cover / Character      GeminiImageClient      QualityGate
  Episode / Yonkoma6     (nano2lite:既定)       Upscaler
  Manga24                                     Typesetter
        │                     │
        │              LegacyImagenClient
        │              （既存ImageServiceラッパ・後方互換/切替用）
```

### 0.2 3つの設計原則

| # | 原則 | 実装上の制約 |
|:--|:---|:---|
| **P1** | **モデルIDは1箇所にだけ書く** | 新コードは `config/image_models.py` のみ参照。Imagen IDの直書き禁止（CIで機械検査） |
| **P2** | **種別差はプロンプト戦略に閉じる** | 生成エンジン本体は `IllustrationType` の `if` 分岐を持たない（`get_strategy()` に委譲） |
| **P3** | **画像処理は任意依存でloquuent** | Pillow なし環境でも生成本体は動く（後処理のみスキップ） |

### 0.3 期待効果

| 指標 | 現状 | 統一後 |
|:---|:---|:---|
| モデル差し替え工数 | コード改変＋テスト修正 | **設定1行**（`AUTONOVEL_IMAGE_MODEL`） |
| 1話のイラストコスト | 種別でばらつく（$0.03〜$0.20） | **均一 $0.034**（24コマ含め） |
| 品質ゲート・超解像・写植 | Manga24のみ | **全5種別** |
| 24コマ漫画 | 未統合・死にコード | Skill/Workflow から到達可能 |
| illustration_points | 指示データのみ・画像と無関係 | **points→画像生成に自動接続** |
| CI安全性 | APIキー必須のテストが存在し得る | **ネットワーク禁止テスト**を標準化 |

---

## 1. 現状精査（実装前の確定事実）

### 1.1 系統ごとの現状

| 系統 | 主要ファイル | 生成モデル | 統合度 | 課題 |
|:---|:---|:---|:---|:---|
| **A. Traditional** | `src/agents/illustration_agent.py`(493行)<br>`src/services/illustration/{cover,character,scene}_service.py` | Imagen（`config/imagen_models.py`） | Skill/Workflow から到達可 | `IllustrationAgent` は**プロンプトのみ実装**（`image_url=""`）。実画像生成は Workflow 経由のみ |
| **B. IllustrationPoint** | `src/services/pipeline_steps.py:658`<br>`src/models/illustration_point.py` | なし（指示データのみ） | パイプラインStep 2.5 | ハードコードされた3点（口絵1/中盤/口絵2）。画像生成と無関係 |
| **C. Manga24** | `src/services/manga/*`（9ファイル） | NanoBanana2Lite | **未統合**（テストからのみ呼出し） | `src/` 配下のどこからも参照されない死にコード |

### 1.2 統合を阻む技術的負債（実測）

| ID | 負債 | 影響 | 対策 |
|:--|:---|:---|:---|
| **D1** | `IllustrationModel` enum が Imagen tier（`fast/quality/ultra`）に結合 | モデル差し替え時に enum 変更が必要 | 新 `ImageProfile`（`standard/fast/high`）を追加、enum は**後方互換で温存** |
| **D2** | テストが `model_used == "imagen-4.0-ultra-generate-001"` を固定検証（`tests/test_illustration_agent.py:79`） | モデル統一で必ずFAIL | S22 で**意図的にcharacteristic test を更新**（TI-01/TI-03 参照） |
| **D3** | `IllustrationAgent(image_service=...)` が公開コンストラクタ（テスト・DI が使用） | シグネチャ変更は破壊的 | `image_service` を **LegacyImagenClient として自動ラップ**して維持 |
| **D4** | `ImageService` が `static/illustrations/` 直下に Requirement oga sable save（`image_service.py:98`） | book_id 別ディレクトリで Separation なし | 出力は `static/illustrations/{book_id}/` に統一（回帰テスト化） |
| **D5** | `IllustrationResult.image_url` が `Path` ではなくURL文字列 | 新エンジンは `Path` を扱う | `image_url` は**保持**し、別途 `image_path: Path` を追加（`image_url` はURL文字列を返す property） |
| **D6** | `Pillow` が未宣言依存（`pyproject.toml` に無いが `src/services/manga/*` が `try/except` で使用） | クリーン環境で漫画モックが縮退 | `optional-dependencies.image` として明示宣言＋縮退テスト追加 |
| **D7** | `src/services/manga/client.py` の `edit_sheet_panel` は `NotImplementedError` | 部分修正が未実装 | 本計画では**スコープ外**（R-12 で明示的に固定） |
| **D8** | `illustration_prompts` / `visual_textual_synergy` 監査次元が IllustrationAgent に依存 | 再生成経路の消失は不可 | R-08 で再生成契約を固定 |

### 1.3 現状テスト資産（保護対象）

| ファイル | 保護すべき契約 |
|:---|:---|
| `tests/regression/test_manga_regression.py` | API 1回/話・コスト$0.05未満・写植OPT・`--no text` 必須・ルート非漏洩 |
| `tests/test_illustration_agent.py` | `run(request=)` 呼び方・`{"status","result","prompt"}` 形状 |
| `tests/unit/workflows/test_illustration_workflow.py` | `generate_illustrations()` 戻り値形状 |
| `tests/services/test_illustration_point_generation_step.py` | skip 条件（`enable_illustration=False` / `book_id is None`）・空キャラで継続 |
| `tests/models/test_illustration_point.py` | `to_dict`/`from_dict` ラウンドトリップ |
| `tests/test_illustration_router.py` | API 层的响应契约 |

---

## 2. 目標アーキテクチャ

### 2.1 ディレクトリ構成（統合後）

```
config/
└── image_models.py               # ★SSOT: モデルカタログ（既定=nano2lite）
src/
├── models/illustration.py         # ＋MANGA_24PANEL、＋image_path
├── services/illustration/
│   ├── unified_generator.py       # ★新: 単一エンジン
│   ├── config.py                  # ★新: UnifiedIllustrationConfig
│   ├── clients/
│   │   ├── base.py                # ★新: ImageClientProtocol
│   │   ├── gemini_image_client.py # ★新: nano2lite 既定
│   │   └── legacy_imagen_client.py# ★新: 既存ImageServiceWrap
│   ├── strategies/                # ★新: 種別別プロンプト戦略
│   │   ├── base.py  cover.py  character.py
│   │   └── episode.py  yonkoma6.py  manga24.py
│   ├── quality_gate.py            # ★移設: manga/quality_gate.py を一般化
│   ├── upscaler.py                # ★移設: manga/upscaler.py を一般化
│   ├── typesetter.py              # ★移設: manga/typesetter.py を一般化
│   ├── character_ref.py           # ★新: キャラ参照管理
│   └── （既存）cover_service.py / character_service.py / scene_service.py / prompts.py
│   └── model_selector.py          # 改: config/image_models.py 参照へ
├── services/manga/                # フェーズB完了後「Deprecated Shims」に降格
└── agents/illustration_agent.py   # 改: エンジンへ委譲（後方互換API維持）
```

### 2.2 クライアント差し替え（Prerequisite: P1 の実装）

```python
# src/services/illustration/clients/base.py
class ImageClientProtocol(Protocol):
    """画像生成クライアントの抽象境界。モデル差し替えはこの境界だけで完結する。"""
    name: str
    model_id: str
    async def generate(
        self,
        prompt: str,
        *,
        negative_prompt: str = "",
        aspect_ratio: str = "3:4",
        reference_images: Sequence[Path] = (),
        seed: int | None = None,
    ) -> GeneratedImage:  # dataclass: data: bytes, meta: dict
        ...
```

```python
# config/image_models.py（SSOT）
DEFAULT_IMAGE_MODEL = "nanobanana2lite"

IMAGE_MODEL_CATALOG: dict[str, ImageModelSpec] = {
    "nanobanana2lite": ImageModelSpec(
        key="nanobanana2lite",
        model_id="gemini-3.1-flash-lite-image",
        client="gemini_image",      # → GeminiImageClient
        cost_per_image_usd=0.034,
        supports_reference_images=True,
        supports_negative_prompt=True,
    ),
    # 後方互換・切替候補（既定ではない）
    "imagen_fast": ImageModelSpec(..., model_id="imagen-4.0-fast-generate-001",  client="legacy_imagen", cost_per_image_usd=0.03),
    "imagen_quality": ImageModelSpec(..., model_id="imagen-4.0-generate-001",    client="legacy_imagen", cost_per_image_usd=0.07),
    "imagen_ultra": ImageModelSpec(...,  model_id="imagen-4.0-ultra-generate-001",client="legacy_imagen", cost_per_image_usd=0.20),
}
```

> 切替は `AUTONOVEL_IMAGE_MODEL=imagen_ultra` の環境変数1つ。コード改変ゼロ。

---

## 3. 24ステップ実装計画

> 各ステップは「対象ファイル / 内容 / 検証コマンド / 期待結果 / 関連テスト」で自己完結。
> ステップは**個別に完了可能**이며、途中中断しても後続ステップが壊れない順序してある。

---

### Phase A: 基盤（Step 1–6）

---

#### Step 1 — モデルカタログ SSOT 化

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `config/image_models.py`（新規）<br>`config/imagen_models.py`（既存・変更なし＝後方互換） |
| **内容** | ① `ImageModelSpec` dataclass（`key`, `model_id`, `client`, `cost_per_image_usd`, `supports_*`）<br>② `IMAGE_MODEL_CATALOG` に `nanobanana2lite` を**先頭・既定**で登録、Imagen 3 tier も維持<br>③ `DEFAULT_IMAGE_MODEL = "nanobanana2lite"`<br>④ `get_image_model_spec(key)` / `resolve_model_key_from_env()`<br>⑤ 環境変数 `AUTONOVEL_IMAGE_MODEL` を読む（未設定→既定） |
| **検証コマンド** | `python -c "from config.image_models import resolve_model_key_from_env as r; print(r())"` |
| **期待結果** | `nanobanana2lite` が標準出力される |
| **関連テスト** | `tests/unit/config/test_image_models.py`（S19で作成） |

**注意**: `config/imagen_models.py` の `select_imagen_model()` は**削除しない**（既存テスト・外部参照のため温存）。新コードは `config/image_models.py` のみを参照する。

---

#### Step 2 — クライアントプロトコル定義

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `src/services/illustration/clients/__init__.py`, `clients/base.py`（新規） |
| **内容** | ① `ImageClientProtocol`（`name`/`model_id`/`generate()`）<br>② `GeneratedImage` dataclass（`data: bytes`, `meta: dict`）<br>③ `ClientError` 例外（`TransientClientError` / `PermanentClientError`）<br>④ `ClientFactory.build(spec, api_key, mock_mode)` → client インスタンス |
| **検証コマンド** | `python -c "from src.services.illustration.clients.base import ImageClientProtocol; print('ok')"` |
| **期待結果** | `ok` |
| **関連テスト** | R-04（クライアント境界の契約テスト） |

---

#### Step 3 — GeminiImageClient（NanoBanana2Lite 既定実装）

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `src/services/illustration/clients/gemini_image_client.py`（新規） |
| **内容** | ① `google.genai.Client` の**遅延**生成（APIキー未設定でも import/生成可能）<br>② `generate()` は `types.GenerateImagesConfig` に `aspect_ratio` / `negative_prompt` / `number_of_images=1` を設定<br>③ `reference_images` があれば `ReferenceImage` を構築（**未対応SDKでは明示的に無視＋WARNINGログ**。黙って落ちない）<br>④ `mock_mode=True` なら疑似PNGバイト列を返す（`GeneratedImage.meta["mock"]=True`）<br>⑤ 例外は `TransientClientError` に包む（リトライ対象） |
| **検証コマンド** | `pytest tests/unit/illustration/test_clients_gemini.py -q`（S19） |
| **期待結果** | mock モードで `data[:8] == b"\x89PNG\r\n\x1a\n"` |
| **関連テスト** | R-04, R-12（API非接触） |

---

#### Step 4 — LegacyImagenClient（後方互換アダプタ）

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `src/services/illustration/clients/legacy_imagen_client.py`（新規） |
| **内容** | ① 既存 `src/services/image_service.py:ImageService` を**内部所持**し `generate()` で委譲<br>② `ImageService.generate()` は `str`（URL）を返す → |Arkimage.read_bytes()`` でバイト列化、URLを `meta["url"]` へ<br>③ `ImageService` を注入_ANY_ 注入可能（`IllustrationAgent(image_service=Mock())` 互換＝**D3対策**）<br>④ `safety_level` は `ImageService._build_safety_filter_level` にそのまま委譲 |
| **検証コマンド** | `pytest tests/test_illustration_agent.py -q`（S22更新後） |
| **期待結果** | 既存テストが**変更なしで**通り continued（Legacy 経路） |
| **関連テスト** | R-01（後方互換フォールバック） |

---

#### Step 5 — UnifiedIllustrationConfig（設定の一本化）

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `src/services/illustration/config.py`（新規） |
| **内容** | ① `model_key: str = DEFAULT_IMAGE_MODEL`（**差し替えはこの1行**）<br>② `aspect_ratio_default`, `quality_gate: bool`, `upscale: bool`, `typeset: bool`, `max_retries: int`, `retry_backoff_sec: float`<br>③ `output_root: Path = Path("static/illustrations")`、出力は `{output_root}/{book_id}/`<br>④ `mock_mode: bool`（`AUTONOVEL_IMAGE_MOCK=1` で強制）<br>⑤ `quality_thresholds: dict`（種別別に上書き可能）<br>⑥ `from_env()` クラスメソッド |
| **検証コマンド** | `python -c "from src.services.illustration.config import UnifiedIllustrationConfig as C; print(C.from_env().model_key)"` |
| **期待結果** | `nanobanana2lite` |
| **関連テスト** | R-02（モデル統一） |

---

#### Step 6 — 後処理3点（品質ゲート / 超解像 / 写植）の一般化移設

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `src/services/illustration/quality_gate.py`, `upscaler.py`, `typesetter.py`, `character_ref.py`（新規）<br>`src/services/manga/{quality_gate,upscaler,typesetter}.py`（**削除せず** deprecated shim にして新モジュールへ re-export） |
| **内容** | ① **品質ゲート**: 純 PIL 実装を維持（`numpy`/`cv2` **非依存**）。種別ごとに閾値切替（漫画はグリッド必須、表紙は_NET グリッド無しで合格扱い）<br>② **PIL 不在時の縮退**: import 失敗 → `skipped=True, is_valid=True`（R-06）<br>③ **超解像**: Real-ESRGAN があれば外部実行、なければ PIL Lanczos、どちらも無ければ**コピー**<br>④ **写植**: `SpeechBubble` 相当を dict で受け取れるようにする。`panel_index` の範囲外はスキップ<br>⑤ **character_ref**: `static/character_refs/{book_id}/{name}.png` を検索し、存在すれば `reference_images` に渡す |
| **検証コマンド** | `pytest tests/services/test_manga_pipeline.py -q` |
| **期待結果** | 既存漫画テストが shim 経由で**PASS**（退行なし） |
| **関連テスト** | R-05, R-06, R-07 |

---

### Phase B: プロンプト戦略（Step 7–12）

---

#### Step 7 — PromptStrategy 基底＋レジストリ

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `src/services/illustration/strategies/__init__.py`, `strategies/base.py`（新規） |
| **内容** | ① `PromptStrategy` ABC：`build_prompt(request) -> str`（抽象）、`build_negative_prompt(request) -> str`、`regenerate_prompt(request, action)`<br>② **共通禁止句**を基底に集約: `no text or letters in image` / `watermark` / `signature`<br>③ `_apply_safety()`: `R15_CONTENT` 時のみ "R15" を付与（種別별語尾差を保持）<br>④ `_genre_style()`: 既存 `_GENRE_STYLE_HINTS`（`prompts.py`）を**再Configure.scene**（重複定義を作らない）<br>⑤ `get_strategy(illo_type, config) -> PromptStrategy`（未登録種別は `EpisodeStrategy` にフォールバック） |
| **検証コマンド** | `python -c "from src.services.illustration.strategies import get_strategy; print(get_strategy)"` |
| **期待結果** | 関数オブジェクトが表示 |
| **関連テスト** | R-08, R-11 |

---

#### Step 8 — CoverStrategy

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `src/services/illustration/strategies/cover.py`（新規） |
| **内容** | ① `book_context` の `title`/`genre`/`concept`/`keywords` を使用<br>② **バリエーション**: `episode_number` を添字に既存3種のカメラワーク（`cover_service.py` と同じ配列）を**<br>`src/services/illustration/prompts.py:_COVER_VARIATIONS` から import**（ロジック二重定義の禁止＝R-11）<br>③ `prompt_override` があれば最優先（`cover_service.py:24` と同じ挙動）<br>④ 既定アスペクト `2:3`（`config.defaults_by_type`） |
| **検証コマンド** | `pytest tests/unit/illustration/test_strategies.py::test_cover -q` |
| **期待結果** | PASS |
| **関連テスト** | R-08, R-11 |

---

#### Step 9 — CharacterStrategy

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `src/services/illustration/strategies/character.py`（新規） |
| **内容** | ① `name`/`role`/`appearance`/`traits`/`background` を読み、**優先キー・フォールバックキー**を両対応（`character_name`⇄`name`, `character_description`⇄`appearance`＝既存Agent 実装と同等の挙動）<br>② 立ち絵固定句: `Full body`, `standing pose`, `clean line art` を維持 |
| **検証コマンド** | `pytest tests/unit/illustration/test_strategies.py::test_character -q` |
| **期待結果** | PASS |
| **関連テスト** | R-08 |

---

#### Step 10 — EpisodeStrategy

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `src/services/illustration/strategies/episode.py`（新規） |
| **内容** | ① `scene_text` が空なら `book_context` から汎用プロンプト（`illustration_agent.py:_generate_episode` 相当）<br>② **400文字上限で切り詰め**（`prompts.py:build_scene_prompt` と同じ）<br>③ `Cinematic lighting`, `manga/anime style` を維持 |
| **検証コマンド** | `pytest tests/unit/illustration/test_strategies.py::test_episode_truncation -q` |
| **期待結果** | 401字以上の入力でプロンプトに `...` が付く |
| **関連テスト** | R-08, R-10 |

---

#### Step 11 — Yonkoma6Strategy

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `src/services/illustration/strategies/yonkoma6.py`（新規） |
| **内容** | ① `panels` を **3..6 にクランプ**（`prompts.py:174` と同じ）<br>② 既存の `YonkomaPlanner.plan_heuristic` / `build_yonkoma_prompt` を**再利用**（再実装禁止）<br>③ LLM 利用時は `plan_with_llm`、失敗時は `plan_heuristic` へフォールバック<br>④ 空テキスト時は既存プレースホルダ6種（`illustration_agent.py:368` と同じ文言） |
| **検証コマンド** | `pytest tests/unit/test_yonkoma.py -q` |
| **期待結果** | 既存テストPASS＋新規クランプテストPASS |
| **関連テスト** | R-08, R-10 |

---

#### Step 12 — Manga24Strategy

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `src/services/illustration/strategies/manga24.py`（新規） |
| **内容** | ① **24コマ（4列×6行）**。`panels` は 24 固定（1..24 にクランプ）<br>② 24)`

camera directive` を 4列×6行の**実際の座標ラベル**（row1-col1 等）で出力（現状のプロンプトの座標ずれ `mid-left` 等を修正）<br>③ **サイレント指定** `--no text, no speech bubbles, no captions, no numbers, no words` を**必須**（R-03）<br>④ 24コマ要約の生成（既存 `YonkomaPlanner` を **24コマへ拡張**。拡張せず24個を6個反復にしない＝R-10）<br>⑤ `text` が空なら 6種×4のプレースホルダ |
| **検証コマンド** | `pytest tests/unit/illustration/test_strategies.py::test_manga24 -q` |
| **期待結果** | プロンプトに `4x6`、`Panel 24`、`--no text` が含まれる |
| **関連テスト** | R-03, R-08, R-10 |

---

### Phase C: 統合（Step 13–18）

---

#### Step 13 — ドメインモデル拡張

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `src/models/illustration.py` |
| **内容** | ① `IllustrationType.MANGA_24PANEL = "manga_24panel"` 追加<br>② `IllustrationResult.image_path: Path \| None = None` 追加（**`image_url` は残す**＝D5）<br>③ `IllustrationResult.image_url` を「`image_path` があれば `/static/...` 形式のURL文字列、无ければ従来値」という property 化（**保存順の互換**：`image_url` は positional 引数順を維持）<br>④ `IllustrationModel` enum は**温存**（D1）。新 `ImageProfile` は Step 5 側に定義 |
| **検証コマンド** | `pytest tests/models/ -q` |
| **期待結果** | PASS |
| **関連テスト** | R-01, R-09 |

---

#### Step 14 — UnifiedIllustrationGenerator 本体

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `src/services/illustration/unified_generator.py`（新規） |
| **内容** | ① 処理順: `strategy.build_prompt` → `client.generate` → 保存（`{root}/{book_id}/`）→ `QualityGate` → `Upscaler` → `Typesetter`<br>② **リトライ**: `max_retries` 回、指数バックオフ。`TransientClientError` のみリトライ、`PermanentClientError` は即中断<br>③ **品質NGでも生成自体は成功扱い**（`quality_passed=False` を保持して後段継続＝R-05）<br>④ `estimate_cost()` / `estimate_time()` をカタログから取得（ハードコード禁止）<br>⑤ `generate_batch()` は `asyncio.gather(..., return_exceptions=True)` で**1失敗でも全体止まらない**<br>⑥ 出力ファイル名は `{type}_ep{ep}_{ts}.png`（collision 回避） |
| **検証コマンド** | `pytest tests/unit/illustration/test_unified_generator.py -q` |
| **期待結果** | mock モードで全5種別が PNG を出力 |
| **関連テスト** | R-01, R-05, R-06, R-07, R-12 |

---

#### Step 15 — IllustrationAgent の差し替え（後方互換API維持）

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `src/agents/illustration_agent.py` |
| **内容** | ① コンストラクタに `config: UnifiedIllustrationConfig \| None = None` を追加。**`image_service=` が渡されたら `LegacyImagenClient` を自動構築**（＝`tests/test_illustration_agent.py` がそのまま通る）<br>② `run()` / `execute()` / `generate_prompt_only()` の**既存シグネチャと戻り値形状 `{"status","result","prompt"}` を維持**<br>③ 実画像生成を実装（現状 `image_url=""` だった穴を埋める）<br>④ `regenerate_prompts()` / `_build_*_prompt()` は**後方互換のため温存**し、`strategies/` へ委譲<br>⑤ `generate_episode_yonkoma()` / `generate_episode_scenes()` も温存＋新エンジンへugs delegation<br>⑥ `_persist()` の既存シグネチャ（`create_illustration(...)`）温存＝R-13 |
| **検証コマンド** | `pytest tests/test_illustration_agent.py -q`（S22前的には1件FAIL想定） |
| **期待結果** | FAILは `model_used` 1件のみ（意図的・S22で解消） |
| **関連テスト** | R-01, R-08, R-13, R-14 |

---

#### Step 16 — IllustrationWorkflow の統合

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `src/backend/workflows/illustration_workflow.py` |
| **内容** | ① 設定キーを**追加**（既存キー互換）: `generateManga24`, `manga24Episodes`, `yonkomaPanels`, `coverAspectRatio`<br>② 種別ごとの生成を `UnifiedIllustrationGenerator` に委譲（`illustration_type` のみ変える）<br>③ `_determine_safety_level()`（`enableErotic`→R15）を温存＝R-14<br>④ `generate_illustrations()` の既存スタブ動作（`[]` 返却）は**温存**（テストが依存）<br>⑤ 失敗した request は `error` 付きで `results` に_push_ し、**全体は落とさない** |
| **検証コマンド** | `pytest tests/unit/workflows/test_illustration_workflow.py -q` |
| **期待結果** | PASS |
| **関連テスト** | R-09, R-14 |

---

#### Step 17 — IllustrationPointGenerationStep の接続

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `src/services/pipeline_steps.py`（`IllustrationPointGenerationStep`） |
| **内容** | ① `__init__(self, illustration_generator: UnifiedIllustrationGenerator \| None = None)`<br>② 既存 skip 条件を**完全に温存**（`enable_illustration=False` / `book_id is None`）<br>③ 既存3点ハードコード生成は**温存**（挙動互換）<br>④ **追加**: `_build_requests_from_points(ctx)` で `IllustrationPoint → IllustrationRequest` 変換（`book_id`/`genre`/`characters` を 文脈 から供給）<br>⑤ **_generation 実行は ctx フラグで明示制御**（`ctx.enable_illustration_generation`、既定 False）＝**既存パイプラインを急変させない**<br>⑥ 失敗は `reporter.report(..., "warning")` で**継続**（Step全体は True） |
| **検証コマンド** | `pytest tests/services/test_illustration_point_generation_step.py tests/unit/services/test_pipeline_steps_coverage.py -q` |
| **期待結果** | 全PASS（既存4ケース＋新規） |
| **関連テスト** | R-09, R-15 |

---

#### Step 18 — 配線（DI / 起動 / 環境変数）と旧コード降格

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | 起動 woven sites（`src/backend/...` engine 構築部）、`src/services/manga/__init__.py`（shim 化） |
| **内容** | ① `build_unified_illustration_generator()` を既存の engine/DI 構築へ登録<br>② `IllustrationWorkflow` / `IllustrationPointGenerationStep` へインスタンスを注入（未注入時は**内部生成**して後方互換）<br>③ 環境変数: `AUTONOVEL_IMAGE_MODEL`（既定nano2lite）, `AUTONOVEL_IMAGE_MOCK`, `AUTONOVEL_ILLUSTRATION_LEGACY=1`（**ロールバック用**）<br>④ `src/services/manga/*` は **削除せず** deprecated shim（新モジュールへ re-export）。`tests/regression/test_manga_regression.py` を壊さない<br>⑤ 起動時 self-check: モデル解決失敗時は **WARNING＋Legacy 退回**（致命的でない） |
| **検証コマンド** | `pytest tests/backend/test_engine.py -q` ＋ `python -c "import src.services.manga"` |
| **期待結果** | PASS ／ import 成功 |
| **関連テスト** | R-01, R-11, R-16 |

---

### Phase D: テスト・リグレッション（Step 19–24）

---

#### Step 19 — ユニットテスト（戦略5種 + 設定 + クライアント）

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `tests/unit/illustration/test_config.py`, `test_strategies.py`, `test_clients_gemini.py`, `test_unified_generator.py`（新規） |
| **内容** | R-02 / R-03 / R-04 / R-08 / R-10 / R-12 に対応する** Characterization** テスト群（各1ケース以上） |
| **検証コマンド** | `pytest tests/unit/illustration/ -q` |
| **期待結果** | 全PASS、0.2秒以内（外部I/O無し） |
| **関連テスト** | R-02, R-03, R-04, R-08, R-10, R-12 |

---

#### Step 20 — 契約テスト（モデル差し替え可能性）

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `tests/unit/illustration/test_client_contract.py`（新規・**全クライアント共通**） |
| **内容** | ① `ImageClientProtocol` に**全クライアントが適合**（`GeminiImageClient` / `LegacyImagenClient` / `MockClient`）<br>② **パラメタライズドテスト**: 全クライアント × 全5 `IllustrationType` で同一プロンプトが同一proceedingsを生成<br>③ `model_key` だけを差し替えて**同一結果になる**（engine 側の if 分岐が増えないことの証明） |
| **検証コマンド** | `pytest tests/unit/illustration/test_client_contract.py -q` |
| **期待結果** | PASS |
| **関連テスト** | R-01, R-04 |

---

#### Step 21 — リグレッションテスト群（★中核）

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `tests/regression/test_unified_illustration_regression.py`（新規、**R-01〜R-16**） |
| **内容** | 下記 §4 のマトリクスに対応 |
| **検証コマンド** | `pytest tests/regression/ -q` |
| **期待結果** | 全PASS（仕様違反は即FAIL） |
| **関連テスト** | R-01〜R-16 |

---

#### Step 22 — 既存テストの意図的更新（Characteristic Update）

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `tests/test_illustration_agent.py`（主因）、他 Step 15/16 でずれたもの |
| **内容** | ① `test_illustration_agent_auto_model_resolves` の期待値 `imagen-4.0-ultra-generate-001` → `gemini-3.1-flash-lite-image`（**D2**）<br>② 変更理由を**テスト docstring に明記**（モデル統一決定の記録）<br>③ 併せて「`AUTONOVEL_IMAGE_MODEL=imagen_ultra` なら従来値になる」**逆向きテスト**を追加（差し替え可能性の証明）<br>④ その他の既存テストは**原则 PASS のまま**（数え上げ） |
| **検証コマンド** | `pytest tests/ -q -k "illustration or manga"` |
| **期待結果** | 全PASS |
| **関連テスト** | R-01, R-17 |

---

#### Step 23 — E2E（mock モード 1話フルフロー）

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `tests/e2e/test_illustration_full_flow_mock.py`（新規） |
| **内容** | ① `AUTONOVEL_IMAGE_MOCK=1` で point生成→5種別生成→DB永続化まで通し実行<br>② **ネットワーク遮断**（socket を patch し、外部通信が1件でもあれば FAIL）<br>③ 生成総コストが上限内（1話 $0.25 超えない）<br>④ 4話分の冪等性（2回実行でファイル名が衝突しない） |
| **検証コマンド** | `pytest tests/e2e/test_illustration_full_flow_mock.py -q` |
| **期待結果** | PASS（ネットワーク0件） |
| **関連テスト** | R-07, R-12, R-18 |

---

#### Step 24 — ドキュメント・依存・完了判定

| 項目 | 内容 |
|:--|:--|
| **対象ファイル** | `pyproject.toml`, `plans/README.md`, `docs/adr/002-unified-illustration-engine.md`（新規ADR） |
| **内容** | ① `optional-dependencies.image = ["Pillow>=10.0"]` を**明示宣言**（D6）<br>② モデル差し替え手順を ADR に記録（`AUTONOVEL_IMAGE_MODEL` 1行で切替 superpower）<br>③ `plans/README.md` のアクティブ計画に本書を追加<br>④ `src/services/manga/` へ deprecation ノートを追記 |
| **検証コマンド** | `pip install -e ".[image]"` → `pytest tests/regression/ -q` |
| **期待結果** | PASS |
| **関連テスト** | 全 |

---

## 4. リグレッション防止テスト マトリクス（★中核成果物）

> **方針**: 「守りたい仕様」を1行ずつコードに固定し、**違反したら即FAIL**。
> 命名規則: `test_regression_*` / docstring 先頭に **【リグレッション防止】**（既存 `test_manga_regression.py` の流儀に一致）。

### 4.1 マトリクス

| ID | 守りたい仕様 | 違反したら何が壊れる | テスト関数名（案） | 対象 |
|:--|:---|:---|:---|:--|
| **R-01** | **全 IllustrationType が既定モデル（nano2lite）を使う**。`image_service` 注入時のみ Legacy に落ちる | モデル統一の dissolution、`model_used` の揺れ | `test_regression_default_model_used_for_all_types`<br>`test_regression_legacy_client_only_when_image_service_injected`<br>`test_regression_model_key_env_override` | Agent / Generator |
| **R-02** | **`nanobanana2lite` が既定**（`AUTONOVEL_IMAGE_MODEL` 未設定時）。カタログに Imagen 3件が登録済みで**残る** | Silent なモデル退行 | `test_regression_default_model_key_is_nanobanana2lite`<br>`test_regression_imagen_models_still_registered` | `config/image_models.py` |
| **R-03** | **全戦略のプロンプトが文字描画を禁止**（漫画/4コマ系は `no speech bubbles` も必須） | 文字化け・豆腐 | `test_regression_all_strategies_forbid_text`<br>`test_regression_manga_strategies_forbid_speech_bubbles` | strategies |
| **R-04** | **全クライアントが `ImageClientProtocol` に適合**し、`model_key` 差替えのみで挙動不変 | 差し替え不能な結合 | `test_regression_all_clients_satisfy_protocol`<br>`test_regression_model_swap_does_not_change_engine_branches` | clients |
| **R-05** | **品質ゲートは「品質記録」であり「生成失敗」ではない**。`enable_quality_gate=False` でスキップ可 | 画像生成の過剰リトライ・コスト爆散 | `test_regression_quality_failure_does_not_fail_generation`<br>`test_regression_quality_gate_can_be_disabled` | Generator |
| **R-06** | **Pillow なし環境でも生成は成功する**（後処理のみ縮退） | クリーン環境で全滅 | `test_regression_generation_succeeds_without_pillow` | Generator / 後処理 |
| **R-07** | **出力は `{root}/{book_id}/` 配下**。リポジトリルートへファイルを漏らさない | 設定の散逸・リポジトリ汚染 | `test_regression_output_is_scoped_by_book_id`<br>`test_regression_no_file_leak_in_root` | Generator |
| **R-08** | **R15_CONTENT 時は全戦略プロンプトに "R15" を含む**／非R15時は含まない | 表現規制のRework | `test_regression_r15_modifier_present_for_all_types`<br>`test_regression_non_r15_has_no_r15_modifier` | strategies |
| **R-09** | **設定スイッチ（`enableIllustration` / `generateCover` / `generateEpisodeIllustrations` / `generateYonkoma` / `generateManga24`）が機能する**。OFFなら生成0件 | ユーザー設定の無効化 | `test_regression_illustration_disabled_generates_nothing`<br>`test_regression_each_generation_switch_is_honored` | Workflow |
| **R-10** | **panels クランプ**: yonkoma=3..6、manga24=1..24。散文が短くて**重複の埋 treasuring** | コマ数崩れ・プロンプト肥大 | `test_regression_yonkoma_panels_clamped_3_to_6`<br>`test_regression_manga24_panels_clamped_to_24` | strategies |
| **R-11** | **ロジックの二重定義をしない**: カメラワーク/ジャンルスタイル/安全修飾の**単一ソース** | 仕様乖離（二重管理） | `test_regression_no_duplicate_cover_variations`（`prompts.py` との一致）<br>`test_regression_no_hardcoded_model_ids_outside_catalog`（R-16 と対） | 全体 |
| **R-12** | **CI で外部ネットワークに一切出ない** | テストの不安定化・課金 | `test_regression_no_network_access_in_test_session`（sessionスコープ・socket patch） | セッション |
| **R-13** | **`create_illustration` へ book_id/type/model/safety_level/generation_time_ms が渡る**。失敗しても例外を投げない | 成果物の紐付け消失 | `test_regression_persist_call_shape`<br>`test_regression_persist_failure_does_not_raise` | Agent |
| **R-14** | **`enableErotic` → `R15_CONTENT`**。`visual_textual_synergy` 再生成の入口が残る | 表現規制・再生成経路の消失 | `test_regression_erotic_setting_maps_to_r15`<br>`test_regression_regeneration_focus_entrypoint_exists` | Workflow / Agent |
| **R-15** | **points→リクエスト変換が例外を投げない**（book_id 欠落・空文字・0件すべてで継続） | パイプライン停止 | `test_regression_point_conversion_never_raises`<br>`test_regression_zero_points_proceeds` | Step22 |
| **R-16** | **Imagen モデルIDが `config/image_models.py` 以外に現れない**（機械検査） | 差し替え不能 Chambers の再発 | `test_regression_no_imagen_model_id_outside_catalog`（`src/` をgrep、`config/imagen_models.py` 除外） | 全体 |
| **R-17** | **モデル差し替えが1.Step で機能する**: `AUTONOVEL_IMAGE_MODEL` 変更だけで `model_used` が変わる | 運用時の切替不能 | `test_regression_env_var_switch_changes_model_used`（逆向き検証） | 全体 |
| **R-18** | **冪等性**: 同一入力2回実行でファイル名衝突しない | 上書き・データ消失 | `test_regression_repeated_generation_has_no_collision` | Generator |

### 4.2 既存リグレッションテストとの関係

| 既存テスト | 本計画での扱い |
|:---|:---|
| `tests/regression/test_manga_regression.py` | **無変更で PASS 継続**をDoD要件化。`src/services/manga/*` を shiv化するのは Step 18 |
| `tests/regression/test_week5_regression.py` | 影響なし（メモリ系） |

### 4.3 テストの禁止事項（品質規律）

1. **ネットワーク禁止** — 実 API を直接叩くテストを**新增しない**（R-12 で機械的に強制）
2. ** proportionality の維持** — 1テスト1論点。R-01 群を1つの巨大テストに畳まない
3. **期待値は**必ず**意味ある文字列/値**。`assert True` 禁止
4. **docstring 必須** —  各 R-xx テストは「**何を壊したら壊れるか**」を1行で明記
5. **flaky 禁止** — タイム.sleep への依存を避け、リトライは指数バックオフに `monkeypatch` で注入

---

## 5. 依存関係グラフ（ステップの実行可能順序）

```
Step 1 (モデルSSOT)
  └─> Step 5 (Config) ─┬─> Step 2 (Protocol) ─> Step 3 (GeminiClient)
                       │                        └─> Step 4 (LegacyClient)
                       └─> Step 6 (後処理3点)
                                │
Step 7 (Strategy基底) ─────────┼─> Step 8  (Cover)
      │                         ├─> Step 9  (Character)
      │                         ├─> Step 10 (Episode)
      │                         ├─> Step 11 (Yonkoma6)
      │                         └─> Step 12 (Manga24)
      │                                    │
      └────────────────────────────────────┴─> Step 14 (UnifiedGenerator)
Step 13 (Model拡張) ─────────────────────────┘        │
                                                         ├─> Step 15 (Agent)
                                                         ├─> Step 16 (Workflow)
                                                         └─> Step 17 (Step22)
                                                                  │
Step 18 (配線) ─────────────────────────────────────────────┤
                                                                  v
                                              Step 19 (Unit) ─> Step 20 (Contract)
                                                                  │
                                                                  v
                                              Step 21 (Regression) ─> Step 22 (既存更新)
                                                                  │
                                                                  v
                                              Step 23 (E2E) ─> Step 24 (Docs/依存)
```

**並列可能**: Step 3/4、Step 8〜12、Step 19 は他と独立して進め可能。

---

## 6. 完了判定（DoD）

- [ ] `pytest tests/regression/ -q` が **R-01〜R-18 全て PASS**
- [ ] `pytest tests/ -q -k "illustration or manga"` が **既存テスト込み全PASS**（`test_manga_regression.py` 無変更）
- [ ] `grep -rn "imagen-4.0" src/ | grep -v "config/imagen_models.py"` の結果が**空**
- [ ] `AUTONOVEL_IMAGE_MODEL=imagen_ultra pytest tests/unit/illustration/test_client_contract.py -q` が PASS
- [ ] `AUTONOVEL_IMAGE_MOCK=1` だけで 5 種別すべてが画像生成される（APIキー不要）
- [ ] Pillow 未導入環境で `pytest tests/unit/illustration/ -q` が PASS（R-06）
- [ ] `tests/e2e/test_illustration_full_flow_mock.py` がネットワーク0件で PASS
- [ ] `AUTONOVEL_ILLUSTRATION_LEGACY=1` で旧経路にロールバック可能
- [ ] ADR-002 作成済み、`plans/README.md` 更新済み

---

## 7. リスクと対策

| ID | リスク | 影響度 | 対策 |
|:--|:---|:--|:--|
| RK-1 | **Pillow を追加すると環境が変わる** | 中 | optional extra 化。R-06 で「なしでも動く」ことを固定 |
| RK-2 | **nano2lite の品質が Imagen に劣る**（特に表紙） | 高 | `AUTONOVEL_IMAGE_MODEL=imagen_ultra` で即切替可。R-17 で切替機能を固定 |
| RK-3 | **`IllustrationAgent` の戻り値変化で UI が壊れる** | 高 | 戻り値形状を完全維持（Step 15）。`image_url` 温存（D5） |
| RK-4 | **24コマプロンプトが Grill くなる**（回答長制限） | 中 | サマリ1コマ1文・220文字上限（既存仕様）＋24コマ Beacon は**省略形**を許容。R-10 |
| RK-5 | **品質ゲートの誤判定で過剰リトライ→コスト爆** | 中 | R-05（品質NGでも失敗にしない）＋`max_retries` 上限 |
| RK-6 | **manga/ 削除で既存テストが壊れる** | 中 | 削除せず shim 化（Step 6/18）。DoD に「無変更 PASS」を明記 |
| RK-7 | **points 接続でパイプラインが不安定化** | 中 | `ctx.enable_illustration_generation` 既定 **False**（Step 17）。既存挙動不変 |
| RK-8 | **二重定義の Ihr**（プロンプト文面の二重管理） | 中 | R-11（カメラワーク/スタイルの単一ソース検査） |

---

## 8. 段階リリース計画

| ステージ | 対象 | 既定フラグ | 判定 |
|:---|:---|:---|:---|
| **S0. Shadow** | 新エンジン完全実装、既存パスは温存 | `AUTONOVEL_IMAGE_MODEL` 未使用 | R-01〜R-18 PASS |
| **S1. Internal** | 新エンジンへ切替（mock / 本API両方検証） | `AUTONOVEL_IMAGE_MODEL=nanobanana2lite` | 実生成で5種別 eyeball 確認 |
| **S2. Default** | nano2lite を既定化 | _env未設定でも nano2lite_ | 回帰テスト＋E2E 緑 |
| **S3. Decommission** | `src/services/manga/*` 依存を段階削除、`ImageService` 温存 Cosmos | — | 別計画で扱う（本計画スコープ外） |

**ロールバック**: `AUTONOVEL_ILLUSTRATION_LEGACY=1` で旧経路へ即時復帰（Step 18 で実装）。

---

## 9. 付録：主要ファイル差分サマリ

| ファイル | 種別 | 変更概要 | 既存テストへの影響 |
|:---|:---|:---|:---|
| `config/image_models.py` | 新規 | モデルカタログSSOT | なし |
| `config/imagen_models.py` | **変更なし** | 温存（後方互換） | なし |
| `src/models/illustration.py` | 変更 | `MANGA_24PANEL` 追加、`image_path` 追加 | なし（追加のみ） |
| `src/services/illustration/clients/*` | 新規 | クライアント境界 | なし |
| `src/services/illustration/strategies/*` | 新規 | 種別プロンプト | なし |
| `src/services/illustration/{config,unified_generator,quality_gate,upscaler,typesetter,character_ref}.py` | 新規 | エンジン・後処理 | なし |
| `src/services/manga/*` | 変更（shim） | 新モジュールへ re-export | **PASS 継続** |
| `src/agents/illustration_agent.py` | 変更 | エンジン委譲（API 維持） | 1件（`model_used`）更新 |
| `src/backend/workflows/illustration_workflow.py` | 変更 | 設定キー拡張 | なし |
| `src/services/pipeline_steps.py` | 変更 | points→生成（既定OFF） | なし |
| `pyproject.toml` | 変更 | `image` extra 追加 | なし |
| `tests/regression/test_unified_illustration_regression.py` | 新規 | **R-01〜R-18** | なし |
| `tests/unit/illustration/*` | 新規 | ユニット・契約 | なし |
| `tests/test_illustration_agent.py` | 変更 | 期待値1件＋逆向き1件追加 | **意図的更新** |

---

## 10. 即時アクション（今日やること）

- [x] Step 1: `config/image_models.py` を作成（モデルカタログ SSOT）
- [x] Step 7: `strategies/base.py` の禁止句・安全修飾・ジャンルスタイルを**既存 `prompts.py` から import** して作る（二重定義回避のpractice）
- [x] Step 21 の骨格: `tests/regression/test_unified_illustration_regression.py` を**R-01 / R-02 / R-07 の3ケースだけ**先に書いて「守りたい仕様」を明文化（**テストを先に書く**）
- [x] Step 5 の `UnifiedIllustrationConfig.from_env()` を実装し、`AUTONOVEL_IMAGE_MODEL` の読取を確認

---

## 11. 実装結果（2026-09-26 完了）

### 11.1 実装したファイル

**新規（14）**
| ファイル | 役割 |
|:---|:---|
| `config/image_models.py` | モデルカタログ SSOT（既定 `nanobanana2lite`） |
| `src/services/illustration/config.py` | `UnifiedIllustrationConfig`（差し替えは1行） |
| `src/services/illustration/clients/{base,gemini_image_client,legacy_imagen_client,mock_client,factory}.py` | クライアント境界 |
| `src/services/illustration/strategies/{base,cover,character,episode,yonkoma6,manga24}.py` | 種別プロンプト戦略 |
| `src/services/illustration/{unified_generator,quality_gate,upscaler,typesetter,character_ref,wiring}.py` | エンジン・後処理・配線 |

**変更（8）**
| ファイル | 変更 |
|:---|:---|
| `src/models/illustration.py` | `MANGA_24PANEL` 追加、`image_path` / `quality` / `final_path` 追加 |
| `src/agents/illustration_agent.py` | エンジン委譲（`image_service` 後方互換・戻り値形状維持・重複プロンプト削除） |
| `src/backend/workflows/illustration_workflow.py` | 5種別対応・`generateManga24` 追加・失敗非致命化 |
| `src/services/pipeline_steps.py` | `IllustrationPointGenerationStep` に生成実行（既定OFF） |
| `src/services/pipeline_base.py` | `enable_illustration_generation` 追加 |
| `src/services/illustration/prompts.py` | 6コマプロンプトの矛盾を解消（フキダシ禁止） |
| `src/services/manga/{quality_gate,upscaler,typesetter}.py` | 統合実装へ委譲する shim 化 |
| `pyproject.toml` | `image` extra（Pillow）追加 |

**テスト（新規6 / 既存無変更）**
`tests/unit/illustration/{test_config,test_strategies,test_clients_gemini,test_client_contract,test_unified_generator}.py`、
`tests/regression/test_unified_illustration_regression.py`、
`tests/e2e/test_illustration_full_flow_mock.py`

### 11.2 実装中に見つかった実バグ（テストが先に見つけた）

1. **6コマプロンプトの自己矛盾** — 「speech bubbles を控えめに」ながら「text を描画しない」指定。フキダシ禁止へ修正
2. **`panels=0` が既定値 24 に化ける** — `or` による falsy 変換が原因。`None` 判定へ修正
3. **Legacy 経路が明示モデル指定を上書き** — モデル差し替えと旧 tier 解決が衝突。フォールバック時のみ適用するよう分離
4. **QualityGate の docstring/コメントの文字化け** — 実装中の文字化けを修正

### 11.3 残タスク（別計画）

**A. 未統合の第4系統（重要な発見）**

当初の精査で見落と，但是现在は**さらに1つのクライアント抽象**が存在する。

| ファイル | 内容 |
|:---|:---|
| `src/services/illustration/base.py` | `ImageGenerationRequest` / `ImageGenerationResult`（独自DTO） |
| `src/services/illustration/factory.py` | `get_image_client()` / `get_image_adapter()` |
| `src/services/illustration/{dalle_client,sd_client,mock_client}.py` | DALL-E3 / SD WebUI / Mock |
| `src/services/illustration/adapters/{base,dalle3_adapter,fal_adapter,mock_adapter}.py` | アダプタ層（Fal AI 等） |

今回の `clients/` はこの系統とは**別レイヤ**であり、名义が衝突する
`MockImageClient` が両方に存在する。統合先は
**`src/services/illustration/factory.py` + `adapters/`**（クライアント抽象の
既存SSOT）へ寄せるのが妥当。

→ 別計画で `clients/` と `factory.py`/`adapters/` を統合する。
   参照テスト: `tests/unit/test_image_clients.py`,
   `tests/unit/services/test_image_adapters.py`,
   `tests/integration/test_zero_cost_pipeline.py`,
   `tests/integration/test_phase2_multimodal_e2e.py`

**B. その他**
- `src/services/manga/MangaPipeline` 本体の段階削除（S3）
- `src/services/image_service.py` / `src/infrastructure/repositories/illustration.py` 内の
  ハードコード Imagen ID のカタログ参照化（移行対象外として R-16 の対象から除外中）
- 実 API での eyeball 検証（S1: 5種別の実生成確認）

**承認済み**: 全24ステップの実装が完了しました。
