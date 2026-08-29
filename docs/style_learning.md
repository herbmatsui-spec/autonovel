# スタイル学習機能

## 概要
章生成ごとに、本文から文体特徴（頻出語、平均文長、助詞傾向、禁則語）を抽出し、
ワークスペースの `STYLE_LEARNED.md` に蓄積します。
次章生成時に、学習済み文体をプロンプトに注入して、文体のブレを低減します。

## 仕組み
1. 章が完了すると、`src/backend/database/repositories/chapter.py` の `create_chapter`
   内で `update_style_learned` が呼び出されます。
2. `update_style_learned` は `src/services/style_learning.py` の関数で、
   本文を解析して `STYLE_LEARNED.md` の各セクションを更新します。
3. 執筆時に `src/services/writing_services.py` の `_phase_prepare_context`
   で `build_style_injection` が呼ばれ、`STYLE_LEARNED.md` を読み取って
   `[学習済み文体]` ブロックを生成し、システムプロンプトに注入します。

## ファイル
- `src/services/style_learning.py`: 文体分析とファイル更新
- `src/services/style_prompt.py`: ファイル読み取りとプロンプト整形
- `src/backend/database/repositories/chapter.py`: 章完了時のフック
- `src/services/writing_services.py`: プロンプト注入ポイント

## 設定
- フラグ `style_learning_enabled` (デフォルト: `True`) でオン/オフ切替。
  `config/settings.py` の `Settings` クラスに定義。

## API
- 手動トリガー: `POST /api/workspace/{book_id}/learn_style`
  本文と章番号を JSON で送信すると、強制的に学習を実行します。

## 出力例
`STYLE_LEARNED.md` 内容：
```
# 学習済み文体: タイトル
## 頻出語（上位N）
吾輩, 猫, ですから
## 平均文長
25.6 文字
## 助詞傾向
は:10, が:5, を:8
## 禁則語（検出履歴）
雨, 雪
## 直近サンプル文
吾輩は猫である。名前はまだ無い。
```