# ADR-002: 統合イラスト生成エンジン（生成モデルは NanoBanana2Lite に統一）

- **状態**: Accepted
- **日付**: 2026-09-26
- **関連計画書**: `plans/PLAN_I1_UNIFIED_ILLUSTRATION_ENGINE_24STEPS.md`

---

## 背景

従来は3つのイラスト系統が並存していた。

| 系統 | 場所 | 状態 |
|:---|:---|:---|
| Traditional（表紙/挿絵/立ち絵/6コマ） | `src/services/illustration/` | Imagen。Skill/Workflow から到達可 |
| IllustrationPoint（挿絵指示） | `src/services/pipeline_steps.py` | 画像生成と無関係の指示データのみ |
| Manga24（24コマ1枚シート） | `src/services/manga/` | **完全未統合**（テストからのみ到達） |

この状態は次の問題を生んでいた。

1. 24コマ漫画機能が製品フローから到達不能（死にコード）
2. 品質ゲート・超解像・写植が 24コマ限定で、他のない種別には使えない
3. 生成モデルが Imagen tier（fast/quality/ultra）に結合し、差し替えにコード改変が必要
4. プロンプトロジックが `prompts.py` / `illustration_agent.py` / `manga/prompt_generator.py` に
   三重に散らばり、仕様乖離している
5. `image_service` に依存するテストと依存しないテストが混在し、外部 API 前提が漏れる

---

## 決定

### 1. 単一エンジン + プロンプト戦略

`UnifiedIllustrationGenerator` を唯一の生成器とし、種別差分は
`PromptStrategy` の派生クラス（`CoverStrategy` / `CharacterStrategy` /
`EpisodeStrategy` / `Yonkoma6Strategy` / `Manga24Strategy`）に閉じる。
エンジン本体は `IllustrationType` に対する分岐を持たない。

### 2. 生成モデルは NanoBanana2Lite に統一

- 既定モデル: `gemini-3.1-flash-lite-image`（`nanobanana2lite`）
- モデルIDの**唯一の情報源**は `config/image_models.py`
- Imagen 3 tier は**切替候補としてカタログに残す**（削除しない）

### 3. 差し替えは設定1行

環境変数 `AUTONOVEL_IMAGE_MODEL` を変えるだけで全種別のモデルが変わる。
コード改変・テスト修正は不要。

```bash
# NanoBanana2Lite（既定）
AUTONOVEL_IMAGE_MODEL=nanobanana2lite

# 高品質IMIENTOが必要なら
AUTONOVEL_IMAGE_MODEL=imagen_ultra
```

併せて `AUTONOVEL_IMAGE_MOCK=1`（疑似生成）/ `AUTONOVEL_ILLUSTRATION_LEGACY=1`
（旧 `ImageService` 経路へのロールバック）を用意する。

### 4. クライアント境界（`ImageClientProtocol`）

モデル差分は `src/services/illustration/clients/` の境界に閉じ込める。

| 実装 | 役割 |
|:---|:---|
| `GeminiImageClient` | NanoBanana2Lite（既定） |
| `LegacyImagenClient` | 既存 `ImageService` へのアダプタ（後方互換） |
| `MockImageClient` | CI / オフライン検証 |

### 5. 後処理の共用と縮退

品質ゲート・超解像・写植を `src/services/illustration/` へ移設し全種別で共用する。
`src/services/manga/` 側は**削除せず shim**（既存テスト無変更 PASS を維持）。

Pillow は optional 依存（`pip install -e ".[image]"`）。未導入でも
**生成自体は成功**し、後処理のみ縮退する（`skipped=True, is_valid=True`）。

---

## 後方互換の維持

| 対象 | 方針 |
|:---|:---|
| `IllustrationAgent(image_service=...)` | 維持。渡されたら Legacy クライアントを自動構築 |
| `IllustrationAgent.run()/generate_prompt_only()` | 戻り値形状 `{"status","result","prompt"}` を維持 |
| `IllustrationResult.image_url` | 維持（`image_path` / `final_path` を追加） |
| `IllustrationPointGenerationStep` | 既存 skip 条件・3点生成ロジック据え置き。画像生成は `enable_illustration_generation`（既定 False） |
| `tests/regression/test_manga_regression.py` | **無変更で PASS** |

---

## 検証

リグレッション防止テスト `tests/regression/test_unified_illustration_regression.py`
（R-01〜R-18）が以下を固定する。

- 全種別が既定モデルを使う / Legacy は `image_service` 注入時のみ
- 全戦略プロンプトが文字描画を禁止（漫画系はフキダシも）
- 品質ゲートは「記録」であって「生成失敗」ではない
- Pillow なしでも生成は成功する
- 出力は `{root}/{book_id}/` 配下。ルート非漏洩
- 環境変数1つでモデルが差し替えられる
- Imagen モデルIDがカタログ以外に出ない（統一サブシステム范围内）
- 生成処理が外部ネットワークへ接続しない

---

## 補足: 未統合の第4系統（既知の残課題）

本 ADR の対象に加えて、`src/services/illustration/` には
**別のクライアント抽象**が既に存在していた（本計画の実装前に見落とし）。

| ファイル | 内容 |
|:---|:---|
| `base.py` | `ImageGenerationRequest` / `ImageGenerationResult`（独自 DTO） |
| `factory.py` | `get_image_client()` / `get_image_adapter()` |
| `dalle_client.py` / `sd_client.py` / `mock_client.py` | DALL-E3 / SD WebUI / Mock |
| `adapters/` | DALL-E3 / Fal AI / Mock アダプタ |

今回新設した `clients/` はこの系統とは別レイヤであり、`MockImageClient` が
両方に存在する（モジュールが異なるため衝突しないが、名称が紛らわしい）。

**方針**: 本 ADR は「統合生成エンジン」の境界を確定시키는 に焦点を置き、
クライアント抽象の統合は別計画で
`factory.py` + `adapters/`（既存のクライアント抽象SSOT）へ
`clients/` を寄せる形で行う。

---

## 影響と移行

| 段階 | 内容 | 判定 |
|:---|:---|:---|
| S0 | 新エンジン実装・既存経路温存 | R-01〜R-18 PASS |
| S1 | 新エンジンへ切替（mock / 実API で eyeball） | 5種別生成確認 |
| S2 | nano2lite を既定化 | 回帰 + E2E 緑 |
| S3 | `src/services/manga/` 依存の段階削除、`ImageService` 縮小 | 別計画 |

ロールバック: `AUTONOVEL_ILLUSTRATION_LEGACY=1`

---

## 代替案（不採用）

| 案 | 不採用理由 |
|:---|:---|
| 複数バックエンド（Imagen + NanoBanana2Lite を并存） | 能力差吸収の複雑さと、モデル別テスト 조합の維持コストに対し Unified の方が単純 |
| 24コマを既存 IllustrationAgent に直接実装 | プロンプト構築が agent に肥大化し、統合テストが困難 |
| モデルIDを `config/imagen_models.py` に追記して流用 | SSOT が分散し、「1行で差し替え」が成立しない |
