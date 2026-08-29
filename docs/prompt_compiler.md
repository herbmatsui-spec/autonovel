# プロンプトコンパイラ 仕様書

## 概要
ユーザーが UI 上で選択した各軸（出力モード、テーマ、ジャンル、世界観、読者層、時代、結末、語り口、登場人物、万能インプット、補足メモ）を統合し、LLM に送信するための構造化プロンプトを生成する。

## アーキテクチャ
- **フロントエンド**: `AxisSelector`, `OutputModeSelector` コンポーネントで各軸の値・ロック状態を管理（Zustand `useBookStore`）。
- **バックエンド**: `POST /api/prompt/compile` エンドポイントがリクエストを受け取り、`PromptCompilerService.compile_prompt` を呼び出し Jinja2 テンプレートでレンダリング。
- **テンプレート**: `prompts/templates/compiler/<output_mode>.j2` に各出力モード専用のプロンプト雛形を配置。

## API
### `POST /api/prompt/compile`
Request body:
```json
{
  "output_mode": "novel",
  "axes": {
    "theme": { "value": "冒険", "locked": false, "default": null },
    "genre": { "value": ["ファンタジー"], "locked": false, "default": null },
    ...
  }
}
```
Response:
```json
{ "compiled": "...." }
```

### `GET /api/prompt/randomize/{axis}`
ランダムプリセットから値を返す。
Response:
```json
{ "axis": "theme", "value": "恋愛" }
```

## テンプレート変数
Jinja2 コンテキストには `axis` オブジェクトが渡される。
```
axis.theme.value
axis.genre.value
...
```
各軸は `{value, locked, default}` の構造。

## ロック・ランダム化
- 各軸にロックボタン（🔒/🔓）を配置。ロック中は値変更・ランダム化を無効化。
- ロック状態は `localStorage` に永続化され、次回起動時に復元。
- `AllRandomButton` は未ロック軸のみ一括ランダム化。

## 拡張方法
1. 新しい出力モードを追加する場合、`prompts/templates/compiler/<mode>.j2` を作成。
2. `RANDOM_PRESETS` 辞書に軸ごとの候補を追加。
3. フロントエンドの `OutputModeSelector.MODES` にラベルを追加。

## テスト
- `tests/unit/test_prompt_compiler.py` で各モードのレンダリング確認。
- `tests/e2e/prompt_compile.spec.ts` で E2E 検証。