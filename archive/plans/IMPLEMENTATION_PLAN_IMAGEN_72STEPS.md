# Imagen-4.0-fast-generate-001 画像生成機能 実装計画（72ステップ）

対象: 表紙生成(機能1) / 挿絵シーン抽出(機能2) / キャラクター立ち絵(機能3)
方針: 各ステップを小さく保ち、低性能なLLMでも1つずつ実装・テスト可能にする。
デフォルトモデルは `imagen-4.0-fast-generate-001`（FAST）とし、必要に応じ
`imagen-4.0-generate-001`（QUALITY）も選択できる。

---

## Phase A. 基盤モデル（ステップ 1〜9）

1. `src/models/illustration.py` に `IllustrationType` を定義（COVER / EPISODE / CHARACTER）。
2. 同ファイルに `IllustrationModel` を定義（FAST=`imagen-4.0-fast-generate-001`, QUALITY=`imagen-4.0-generate-001`）。
3. `SafetyLevel` を定義（BLOCK_MOST / BLOCK_SOME / BLOCK_FEW / R15_CONTENT）。
4. `IllustrationRequest` dataclass に `book_id` / `illustration_type` を追加。
5. 同 dataclass に `episode_number` / `character_id` を追加。
6. 同 dataclass に `scene_text` / `book_context(dict)` を追加（表紙・キャラの入力用）。
7. 同 dataclass に `model` / `safety_level` / `aspect_ratio` / `prompt_override` を追加。
8. `IllustrationResult` dataclass を定義（request / image_url / prompt / model_used / generation_time_ms / illustration_id）。
9. 上記モデルを `pytest` で import できることを確認。

## Phase B. 画像生成サービス（ステップ 10〜18）

10. `src/services/image_service.py` の `ImageService` を作成（google.genai クライアント）。
11. コンストラクタで `api_key` と `storage_dir`、`default_model` を受け取るようにする。
12. `default_model` の既定値を `imagen-4.0-fast-generate-001` にする。
13. `generate()` の引数に `aspect_ratio` を追加（表紙=3:4、挿絵=16:9）。
14. 同引数に `negative_prompt` を追加。
15. `types.GenerateImagesConfig` を組み立てる（`number_of_images=1`, `aspect_ratio` 等）。
16. `SafetyLevel` を `types.SafetySetting` リストへ変換するヘルパ `_build_safety_settings` を実装（値ベース比較）。
17. 生成結果バイトを `_save_image` で `static/illustrations/` へ保存し相対パスを返す。
18. 生成時間を計測して返却する。

## Phase C. プロンプト構築（ステップ 19〜27）

19. `src/services/illustration/__init__.py` を作成。
20. `prompts.py` にジャンル別スタイルヒント `_GENRE_STYLE_HINTS` を定義。
21. `build_cover_prompt(book_context, variation)` を実装（タイトル/ジャンル/コンセプト/キーワード）。
22. 表紙バリエーション用カメラワーク `_COVER_VARIATIONS` を定義。
23. `build_scene_prompt(scene_text, book_context)` を実装（400文字截断）。
24. `build_character_prompt(character_data)` を実装（名前/役割/外見/性格/背景）。
25. `apply_safety_modifier(prompt, safety_level, illo_type)` を実装（R15で修飾語を付与、値ベース比較）。
26. 各ビルダの単体テストを作成（タイトル含む / ジャンル英訳 / R15キーワード）。
27. `prompts.py` の ruff チェックを通す。

## Phase D. 機能1 表紙生成（ステップ 28〜36）

28. `cover_service.py` に `CoverGenerator` を作成（ImageService を受取）。
29. `CoverGenerator.generate(request)` でプロンプト構築→生成→`IllustrationResult` を返す。
30. 表紙は `build_cover_prompt` の `variation` に `episode_number` を流用。
31. R15 等の安全修飾を適用する。
32. `generate_variations(request, count=3)` で複数バリエーション生成を実装。
33. `CoverGenerator` のテストを作成（fake ImageService で image_url を確認）。
34. 表紙プロンプトに「画像内に文字を含めない」指示を含める。
35. 出力アスペクト比 3:4 を既定とする。
36. 機能1 の単体テストを `pytest` で通す。

## Phase E. 機能2 挿絵シーン抽出（ステップ 37〜47）

37. `scene_service.py` に `SceneExtractor` を作成。
38. ヒューリスティック `extract_scenes(text, max_scenes)` を実装（段落分割＋視覚手がかりスコア）。
39. 視覚手がかりリスト `_VISUAL_CUES` を定義（空/海/剣/炎 等）。
40. 短い文（<15文字）を除外する閾値を設ける。
41. `SceneIllustrator.generate_for_scene(scene_text, request)` を実装（単一シーン描画）。
42. `extract_scenes_with_llm(text, llm, max_scenes)` を実装（JSON配列抽出、失敗時ヒューリスティックへフォールバック）。
43. `SceneIllustrationService` を作成（extractor + illustrator をまとめる）。
44. `SceneIllustrationService.generate(request)` で「抽出→各シーン生成」のリストを返す。
45. 抽出ロジックの単体テスト（視覚段落が選ばれること）を作成。
46. `SceneIllustrator` のテスト（fake ImageService）を作成。
47. 機能2 のテストを `pytest` で通す。

## Phase F. 機能3 キャラクター立ち絵（ステップ 48〜54）

48. `character_service.py` に `CharacterIllustrator` を作成。
49. `generate(request)` で `build_character_prompt` を呼ぶ。
50. `book_context` から `name/role/appearance/traits/background` を取り出す。
51. R15 修飾はキャラクター向け表現を使う（`apply_safety_modifier` で分岐済み）。
52. アスペクト比 3:4 を既定とする。
53. `CharacterIllustrator` のテスト（名前がプロンプトに含まれる）を作成。
54. 機能3 のテストを `pytest` で通す。

## Phase G. 永続化（ステップ 55〜63）

55. `src/backend/database/models.py` に `Illustration` ORM モデルを追加（book_id FK, type, episode, character, model, prompt, image_url 等）。
56. インデックス `idx_illustrations_book_id` / `idx_illustrations_book_type` を追加。
57. `src/backend/database/repositories/illustration.py` に `IllustrationRepository` を作成。
58. `create_illustration(...)` を実装（挿絵保存、id を返す）。
59. `list_illustrations(book_id, type=None)` を実装（新しい順）。
60. `repositories/__init__.py` に `IllustrationRepository` を登録。
61. `uow.py` に `illustrations` プロパティを追加。
62. `repository.py`（ファサード）の UoW/Auto 両ループに `illustrations` を追加。
63. リポジトリのテスト（create→list/type絞り込み）を作成。

## Phase H. エージェント統合（ステップ 64〜68）

64. `src/agents/illustration_agent.py` を既存 `BaseAgent` を継承して再構成。
65. コンストラクタで3サービスを初期化（image_service + llm）。
66. `run()` で `IllustrationType` に応じ COVER/CHARACTER/EPISODE を振り分け（値ベース比較）。
67. request を属性ベースで受け入れ（`src`/`autonovel.src` の差を吸収）。
68. 生成結果を `_persist()` でDBへ保存（repo がなければスキップ）。

## Phase I. CLI（ステップ 69〜72）

69. `src/cli/illustration_cli.py` を作成（`cover`/`scene`/`character` サブコマンド）。
70. `GOOGLE_API_KEY` 環境変数から ImageService を構築。
71. `scene --extract` で複数シーン抽出モードを呼び出し。
72. 全テスト（`test_illustration_agent.py` + `test_illustration_features.py`）を `pytest` で通す。

---

## 実装済みファイル

- `src/models/illustration.py` … データモデル（ステップ1〜9）
- `src/services/image_service.py` … Imagen FAST 呼び出し（ステップ10〜18）
- `src/services/illustration/prompts.py` … プロンプト構築（ステップ19〜27）
- `src/services/illustration/cover_service.py` … 機能1（ステップ28〜36）
- `src/services/illustration/scene_service.py` … 機能2（ステップ37〜47）
- `src/services/illustration/character_service.py` … 機能3（ステップ48〜54）
- `src/backend/database/models.py` + `repositories/illustration.py` + `uow.py` + `repository.py` … 永続化（ステップ55〜63）
- `src/agents/illustration_agent.py` … 統合（ステップ64〜68）
- `src/cli/illustration_cli.py` … CLI（ステップ69〜72）
- `tests/test_illustration_features.py` … 機能テスト（全ステップの検証）

## モデルカタログ（config 一元管理）

モデルIDはコードに散在させず `config/imagen_models.py` の `IMAGEN_MODEL_CATALOG` にのみ定義する。
`IllustrationModel` 列挙は `auto/fast/quality/ultra` のtierキーを持ち、実IDへの変換は必ず
`config.imagen_models.get_imagen_model_id` / `select_imagen_model` を経由する。

自動選択ルール（`select_imagen_model`）：
- 表紙 / キャラクター → `ultra`（最高品質）
- 挿絵（通常） → `fast`（高速・大量生成）
- 挿絵（R15等機微表現） → `quality`（品質・安全性確保）
- リクエストで `model` を明示した場合はそれを優先。未指定（AUTO）時のみ上記で自動決定。

## 実行例

```bash
export GOOGLE_API_KEY=xxxx
python -m src.cli.illustration_cli cover --book-id 1 --title "天空の城" --genre ファンタジー
python -m src.cli.illustration_cli scene --book-id 1 --episode 3 --extract --text "$(cat chapter.txt)"
python -m src.cli.illustration_cli character --book-id 1 --name アヤ --appearance "銀髪の剣士"
```

## テスト

```bash
python -m pytest tests/test_illustration_agent.py tests/test_illustration_features.py -q
```
