# 50話小説 夜間バッチ生成・自動運用ガイド (ステップ43)

低性能LLM（ローカルOllamaやAPI制限環境）で50話（約15万文字）を安定して夜間バッチ実行するための手順書です。

---

## 1. 概要と特徴
- **進捗の自動保存**: 1話ごとに `progress.txt` に記録されるため、途中で中断しても次回は中断箇所から即座に再開（resume）します。
- **リトライガード**: 短いパートや検証不合格パートのみを自動再生成し、無駄な呼び出しを最小化します。
- **ログ記録**: 全話の機械判定結果が `log/epNN.log` に保存されます。

---

## 2. コマンドライン実行方法

### 2.1 標準実行（全50話・再開可能）
```bash
python novel_50ep/batch_runner.py
```

### 2.2 範囲指定実行（例: 第1話〜第10話のみ）
```bash
python novel_50ep/batch_runner.py --start 1 --end 10
```

### 2.3 生成状況と品質の整合性チェック
```bash
python novel_50ep/batch_runner.py --check-only
```

### 2.4 4コマ漫画プロンプト生成（オプトイン）
`--manga` フラグを付けると、各話生成時に `manga_prompts/epNN_manga_prompt.txt`（Gemini等へそのまま入力できる結合プロンプト）と `manga_prompts/epNN_manga_panels.jsonl`（コマ別JSON）を出力します。付けない限り小説生成には一切影響しません。
```bash
python novel_50ep/batch_runner.py --manga
python novel_50ep/batch_runner.py --start 1 --end 3 --manga
```

### 2.5 ドライラン（サンプル1話だけ確認）
`--manga-dry-run` は `--manga` の動作確認用で、第1話だけ漫画プロンプトを生成して終了します。
```bash
python novel_50ep/batch_runner.py --manga-dry-run
```
- 画風・トーンは `novel_50ep/illust_style.yaml` で外部管理（画風・色調・比率・フォント等）。未設定時はデフォルトが適用されます。
- 安全性: `config.py` の `ILLUST_SAFETY` に列挙したNG表現は自動的に「（自主規制）」へ置換されます。
- キャラの外見統一: `world.yaml` の各キャラ `appearance` が `character_ref` として各コマに付与されます。

---

## 3. バックグラウンド / 夜間実行手順

### Windows 環境 (PowerShell バックグラウンド実行)
```powershell
Start-Process python -ArgumentList "novel_50ep/batch_runner.py" -RedirectStandardOutput "novel_50ep/log/batch_stdout.log" -RedirectStandardError "novel_50ep/log/batch_stderr.log" -NoNewWindow
```

### Windows タスクスケジューラ登録 (夜間 02:00 自動実行)
1. `Win + R` → `taskschd.msc` を起動
2. 「タスクの作成」を選択
3. **全般**: 「最上位の特権で実行する」にチェック
4. **トリガー**: 「毎日」午前 02:00
5. **操作**:
   - プログラム/スクリプト: `python.exe` のフルパス
   - 引数の追加: `novel_50ep/batch_runner.py`
   - 開始 (オプション): `E:\sda`
6. 「OK」で登録完了

### Linux / WSL / Mac 環境 (nohup 実行)
```bash
nohup python3 novel_50ep/batch_runner.py > novel_50ep/log/batch_stdout.log 2>&1 &
echo $! > novel_50ep/batch.pid
```

---

## 4. 障害復旧・トラブルシューティング
- **プロセスが途中で停止した場合**: 再び同じコマンドを実行するだけで、未生成の話数から自動継続されます。
- **特定の話数を一からやり直したい場合**: `progress.txt` から該当話番号を削除し、`output/epNN.md` を削除して再実行してください。
