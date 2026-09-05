# 残りのタスク実装計画（12ステップ）

## ステップ 1: フルテストスイートの実行と失敗の収集
- コマンド: `cd /home/herbmatsui/autonovel && python -m pytest tests/ --tb=short 2>&1 | grep -E "(FAILED|ERROR|passed|failed)" | head -30`
- 目的: 現在のテスト失敗を特定する（カバレッジ以外の失敗）
- 確認: テスト失敗のリストを取得し、各失敗のテスト名とエラーメッセージを記録

## ステップ 2: テスト失敗の個別修正
- 各失敗について:
  - テストファイルを特定し、エラーメッセージを分析
  - シンプルなバグ（インポートミス、タイポなど）であれば即座に修正
  - 複雑な問題については、 issue を作成して後で対応することを検討
- 修正後は該当テストを個別に実行し、パスすることを確認
- 目的: すべてのテストがパスするか、または既知の問題のみ残す

## ステップ 3: テストスイートの再実行（失敗修正後）
- コマンド: `cd /home/herbmatsui/autonovel && python -m pytest tests/ --tb=short 2>&1 | tail -20`
- 目的: ステップ2の修正によりテスト失敗が解消されたことを確認
- 確認: テスト失敗がゼロまたは既知の問題のみになったことを確認

## ステップ 4: コード品質チェック（ruff）
- コマンド: `cd /home/herbmatsui/autonovel && ruff check src/ 2>&1 | head -30`
- 目的: ruff によって報告されるコードスタイル・潜在的バグを特定
- 確認: 報告された issue のリストを取得

## ステップ 5: ruff の問題を修正
- 報告された各 issue について:
  - ファイルを開き、指摘された問題を修正
  - 自動修正可能なものは `ruff check --fix src/` を試す
  - 手動修正が必要なものは個別に対応
- 修正後は該当ファイルに関連するテストを実行し、破壊がないことを確認
- 目的: すべての ruff 警告を解決するか、意図的に無視するものについてはコメントで説明

## ステップ 6: タイプチェック（mypy）
- コマンド: `cd /home/herbmatsui/autonovel && mypy src/ 2>&1 | head -30`
- 目的: mypy によって報告される型エラーを特定
- 確認: 報告されたエラーのリストを取得

## ステップ 7: mypy の問題を修正
- 報告された各エラーについて:
  - 型注釈を追加または修正
  - 必要に応じて、型ヒントのインポートを調整
  - 無視すべき場合は `# type: ignore` コメントを追加（理由を記載）
- 修正後は該当ファイルに関連するテストを実行し、破壊がないことを確認
- 目的: すべての mypy エラーを解決するか、意図的に無視するものについてはコメントで説明

## ステップ 8: コード品質修正後のテストスイート再実行
- コマンド: `cd /home/herbmatsui/autonovel && python -m pytest tests/ --tb=short 2>&1 | tail -20`
- 目的: ステップ4-7の修正によりテストが壊れていないことを確認
- 確認: テスト失敗が増えていないことを確認

## ステップ 9: マニュアル API テスト
- FullAuto エンドポイント:
  ```bash
  curl -X POST "http://localhost:8200/api/full-auto/start" \
    -H "Content-Type: application/json" \
    -d '{"genre":"ファンタジー","keywords":"チート,無双","archetype_key":"王道ざまぁ（爽快感最大）","target_eps":3,"initial_limit":3,"word_count":2000,"concept":"テスト","tone_vibe":0.6}'
  ```
  - タスクIDを取得し、ポーリングで完了を確認
  - 結果に `title`, `chars_count`, `status: "success"` が含まれることを確認
- EasyMode エンドポイント:
  ```bash
  curl -X POST "http://localhost:8200/api/easy-mode/start" \
    -H "Content-Type: application/json" \
    -d '{"genre":"ファンタジー","keywords":["主人公","剣術"],"protagonist_type":"チート主人公","target_episodes":3,"words_per_episode":2000,"enable_audit":true,"max_rewrites":2}'
  ```
  - 同様にポーリングで完了を確認
  - 結果に `episodes` 配列に3話分含まれることを確認
- 目的: API エンドポイントが正常に動作し、統合パイプラインを経由していることを確認

## ステップ 10: マニュアル CLI テスト
- FullAuto CLI:
  ```bash
  python -m src.cli full-auto --genre ファンタジー --keywords "チート,無双" --archetype_key "王道ざまぁ" --target_eps 3 --word_count 2000
  ```
  - 正常完了し結果が表示されることを確認
- EasyMode CLI:
  ```bash
  python -m src.cli easy-mode --genre ファンタジー --keywords 主人公,剣術 --protagonist_type チート主人公 --target_episodes 3 --words_per_episode 2000
  ```
  - 同様に正常完了し結果が表示されることを確認
- 目的: CLI コマンドが正常に動作し、統合パイプラインを経由していることを確認

## ステップ 11: フィーチャーフラグの動作確認
- 一時的に `USE_UNIFIED_PIPELINE=0` を設定し、API/CLI を実行
  - 旧実装が存在しない場合は適切なエラー（またはフォールバック警告）が出ることを確認
  - `USE_UNIFIED_PIPELINE=1`（デフォルト）に戻し、正常動作することを確認
- 目的: フィーチャーフラグによる切り替えが機能していることを確認

## ステップ 12: ドキュメント更新と最終確認
- `AGENTS.md` / `CLAUDE.md` などのアーキテクチャ文書を更新し、統合パイプラインの構成を反映
- `CHANGELOG.md` に統合完了と主な変更点を記録
- `PIPELINE_UNIFICATION_PLAN.md` に完了マークを付与し、実施したステップを示す
- 変更点のサマリーを作成し、チームに共有
- 目的: ドキュメントが実装内容と一致し、今後のメンテナンスが容易になることを確認

## 完了条件
- すべてのテストがパスする（カバレッジ要件を満たすか、またはカバレッジ未達成の理由が明確かつ受け入れ可能）
- コード品質チェック（ruff, mypy）で重大な問題が残っていない
- API と CLI のマニュアルテストが成功
- フィーチャーフラグが期待通りに動作
- ドキュメントが最新状態に更新されている

## 注意点
- 各ステップは 1 つのファイルまたは 1 つの関数の変更にとどめる
- 1 ステップ完了ごとに動作確認コマンドを実行し、成功してから次へ進む
- 失敗したら前のステップに戻り、修正してから再試行