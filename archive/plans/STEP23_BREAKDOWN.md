# ステップ23: 修正 - 型安全性の穴修正（`llm_gateway.py`）

## 目的
`Any` 型を排除して型安全性を向上
**作業内容**:
- `src/core/llm_gateway.py` の `purpose_or_request: Any` を `Union[str, LLMRequestOptions]` に修正
- `generate()` メソッドは削除（既に `NotImplementedError` なので完全削除）
- `overload` デコレータで `generate_json`/`generate_text` の型シグネチャを明示
- mypy で確認

## 完了基準
`mypy --strict src/core/llm_gateway.py` でエラー 0 件

## マイクロステップ

#### ステップ23-1: バックアップを作成する
- **アクション**: `src/core/llm_gateway.py` のバックアップを取る
- **確認**: バックアップファイルが存在すること
- **ツール**: `cp` コマンド
- **出力**: バックアップファイルのパスを表示
- **完了": ☐

#### ステップ23-2: `generate()` メソッドを削除する
- **アクション**: `src/core/llm_gateway.py` から `generate()` メソッドを削除する
- **確認**: メソッドが削除されていること
- **ツール**: `edit` コマンド
- **出力": 削除後のメソッドリストを表示
- **完了": ☐

#### ステップ23-3: `purpose_or_request: Any` を `Union[str, LLMRequestOptions]` に修正する
- **アクション**: `src/core/llm_gateway.py` の `generate_json` と `generate_text` メソッドの `purpose_or_request` 引数の型注釈を修正する
- **確認**: 型注釈が修正されていること
- **ツール**: `edit` コマンド
- **出力": 修正後の型注釈を表示
- **完了": ☐

#### ステップ23-4: `overload` デコレータを使用して `generate_json`/`generate_text` の型シグネチャを明示する
- **アクション**: `src/core/llm_gateway.py` の `generate_json` と `generate_text` メソッドに `@overload` デコレータを追加し、具体的な型シグネチャを定義する
- **確認**: オーバーロードが正しく定義されていること
- **ツール**: `edit` コマンド
- **出力": オーバーロードの内容を表示
- **完了": ☐

#### ステップ23-5: 残りの `Any` 型を適切な型に置き換える
- **アクション**: `src/core/llm_gateway.py` の残りの `Any` 型を調査し、適切な型に置き換える（例えば、`genai.Client` の返り値タイプ、`cooldown` のタイプなど）
- **確認**: すべての `Any` 型が適切な型に置き換えられていること
- **ツール**: `edit` コマンド
- **出力": 修正後の型注釈を表示
- **完了": ☐

#### ステップ23-6: `mypy --strict` を実行し、エラーがゼロであることを確認する
- **アクション**: `mypy --strict src/core/llm_gateway.py` を実行し、エラーがゼロであることを確認する
- **確認": エラーがゼロであること
- **ツール": `mypy` コマンド
- **出力": mypy の出力を表示
- **完了": ☐

#### ステップ23-7: 一時ファイルをクリーンアップする
- **アクション": 作業中に作成した一時ファイルを削除する
- **確認": 一時ファイルが残っていないこと
- **ツール": `rm -f` など
- **出力": クリーンアップ完了
- **完了": ☐
