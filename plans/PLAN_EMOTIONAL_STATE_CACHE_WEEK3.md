# PLAN: 感情状態キャッシュ Week 3 - 構造化アノテーション＋エディタ統合
**目標**: 執筆時に人間が感情ビートを明示的に記述 → 即座に Vector/Graph/Log 反映 → 次話プロンプトに最高優先度で注入
**前提**: Week 1-2 のストア層完成済み。エディタは VS Code 拡張または独自 Web エディタを想定。

---

## Step 1-24 実装タスク

### Phase 1: アノテーションデータモデル・パーサー (Steps 1-6)

**Step 1: 感情ビートデータクラス定義**
- ファイル: `src/annotations/beat.py` (新規)
- Dataclass: `EmotionalBeat` (episode, scene, beat_id, source, target, emotion: EmotionType, delta: float, cause: str, confidence: float=1.0, hidden: bool=False, metadata: Dict)
- バリデーション: `delta` -1.0~1.0, `confidence` 0.0~1.0
- メソッド: `to_signal() -> EmotionalSignal` (Week 1 互換変換)
- テスト: `tests/unit/annotations/test_beat.py::test_beat_validation`

**Step 2: インラインタグパーサー実装**
- ファイル: `src/annotations/parser.py` (新規)
- パターン: `\[beat:(\w+)([+-]\d+\.?\d*)\s*(?:cause="([^"]*)")?\s*(?:hidden)?\]`
- 例: `[beat:fear+0.6 cause="ep14 betrayal" hidden]`
- 関数: `parse_beats(text: str, episode: int, scene: int) -> Tuple[str, List[EmotionalBeat]]`
- 戻り値: (クリーンテキスト, 抽出ビートリスト)
- 発言者推定: 直前のキャラ名行またはセリフ行から推定 (簡易ヒューリスティック)
- テスト: `tests/unit/annotations/test_parser.py::test_parse_inline_beat`

**Step 3: フロントマター形式パーサー (代替・併用)**
- ファイル: `src/annotations/frontmatter.py` (新規)
- 形式: YAML フロントマター (`---` で囲まれたブロック)
- スキーマ: `beats: List[EmotionalBeat]` (インラインと同等フィールド)
- 関数: `parse_frontmatter(text: str) -> Tuple[str, List[EmotionalBeat]]`
- 利点: 一括記述・レビュー容易・エディタで折りたたみ可能
- テスト: `tests/unit/annotations/test_frontmatter.py::test_parse_yaml_frontmatter`

**Step 4: 統合パーサー・優先順位**
- ファイル: `src/annotations/integrated_parser.py` (新規)
- クラス: `BeatParser`
- メソッド: `parse_script(script: str, episode: int) -> ParsedScript`
- `ParsedScript`: `clean_text, beats: List[EmotionalBeat], frontmatter_beats, inline_beats`
- 優先順位: フロントマター > インライン (重複時はフロントマター優先、警告ログ)
- テスト: `tests/unit/annotations/test_integrated_parser.py::test_priority_frontmatter_over_inline`

**Step 5: ビート検証・整合性チェック**
- ファイル: `src/annotations/validator.py` (新規)
- クラス: `BeatValidator`
- チェック項目:
  - キャラ名が辞書に存在するか
  - delta 範囲内か
  - 同一シーンで同一ペア・同一感情の重複がないか
  - hidden=true の場合、表向きビートと矛盾しないか (警告のみ)
- メソッド: `validate(beats: List[EmotionalBeat], character_dict: Set[str]) -> ValidationResult`
- `ValidationResult`: `is_valid, errors: List[str], warnings: List[str]`
- テスト: `tests/unit/annotations/test_validator.py::test_validate_unknown_character`

**Step 6: アノテーション永続化アダプター**
- ファイル: `src/annotations/persistence.py` (新規)
- クラス: `AnnotationPersistence`
- 依存: `VectorStore`, `GraphStore`, `EventLogStore` (Week 1-2 インターフェース)
- メソッド: `persist_beats(beats: List[EmotionalBeat], episode: int)`
- 書き込み:
  - Vector: `namespace="annotation"`, key=`ep{episode}:{source}->{target}` (即時反映、TTLなし/長期)
  - Graph: エッジ更新 (cause に `annotation:{beat_id}` 記録)
  - Log: `source_type="annotation"` タグ付きで追記
- テスト: `tests/integration/annotations/test_persistence.py::test_persist_to_all_stores`

---

### Phase 2: エディタ統合・UI (Steps 7-14)

**Step 7: VS Code 拡張スケルトン (package.json)**
- ファイル: `editor/vscode/package.json` (新規)
- 機能:
  - 言語設定: `novel-script` (Markdown 拡張)
  - スニペット: `beat` → `[beat:$1$2 cause="$3"]`
  - コマンド: `extension.insertBeat`, `extension.showEmotionGraph`, `extension.validateBeats`
  - ビュー: サイドバー「感情ビートパレット」
- 依存: `@vscode/vsce` でパッケージ化
- テスト: `tests/unit/editor/test_package_json.py::test_package_json_valid`

**Step 8: 感情ビート挿入コマンド実装**
- ファイル: `editor/vscode/src/commands/insertBeat.ts` (新規)
- 機能:
  - カーソル位置にスニペット挿入
  - クイックピックで感情タイプ選択 (affection/tension/fear/trust/intimacy)
  - 入力ボックスで delta (-1.0~1.0), cause, hidden チェックボックス
  - 自動で `[beat:...]` 生成して挿入
- テスト: 手動確認 (VS Code で F5 デバッグ)

**Step 9: サイドバー「感情ビートパレット」実装**
- ファイル: `editor/vscode/src/views/beatPalette.ts` (新規)
- TreeView: 現在エピソードのビート一覧 (フロントマター+インライン合算)
- ノード: ペアごとグループ化 (A→B: fear+0.6, tension+0.8...)
- アクション: クリックで該当行ジャンプ、右クリックで編集/削除
- リアルタイム更新: `onDidChangeTextDocument` で再パース
- テスト: 手動確認

**Step 10: 感情推移グラフ Webview**
- ファイル: `editor/vscode/src/views/emotionGraph.ts` (新規)
- ライブラリ: Chart.js (Webview 内読み込み)
- 表示: X軸=エピソード, Y軸=感情値 (-1~1), 系列=感情タイプ×ペア
- データ取得: `VectorStore.get_all("annotation")` + `VectorStore.get_all("rule_engine")` をマージ
- インタラクション: 系列クリックでハイライト、ホバーで詳細
- テスト: 手動確認

**Step 11: リアルタイム検証・診断表示**
- ファイル: `editor/vscode/src/diagnostics/beatDiagnostics.ts` (新規)
- `vscode.languages.createDiagnosticCollection('emotional-beats')`
- `onDidChangeTextDocument` → パース → 検証 → 診断セット
- エラー: 不明キャラ, delta範囲外, 重複
- ワーニング: hidden矛盾, cause未記入
- 表示: 問題パネル + エディタインライン波線
- テスト: `tests/unit/editor/test_diagnostics.py::test_diagnostic_unknown_character`

**Step 12: フロントマター編集支援**
- ファイル: `editor/vscode/src/commands/editFrontmatter.ts` (新規)
- コマンド: `extension.editBeatFrontmatter`
- 動作: 現在ファイルのフロントマターをフォーム形式で編集 (Webview パネル)
- フィールド: 追加/削除/編集、キャラ名オートコンプリート (辞書から)
- 保存時: YAML 整形して書き戻し
- テスト: 手動確認

**Step 13: 自動保存時フック・即時永続化**
- ファイル: `editor/vscode/src/autoPersist.ts` (新規)
- `onDidSaveTextDocument` → パース → `AnnotationPersistence.persist_beats()` 呼び出し
- バックエンド API: `POST /api/annotations/persist` (Week 3 Step 18 で実装)
- 非同期・エラー時は通知のみ (執筆ブロックしない)
- テスト: `tests/integration/editor/test_auto_persist.py::test_persist_on_save`

**Step 14: エディタ統合テスト (E2E)**
- ファイル: `tests/e2e/editor/test_beat_workflow.py` (新規, Playwright)
- シナリオ:
  1. 新規脚本ファイル作成
  2. インラインタグ挿入 → サイドバーに反映確認
  3. フロントマター編集 → グラフ更新確認
  4. 検証エラー発生確認 (不明キャラ)
  5. 保存 → バックエンド API 呼び出し確認 (モック)

---

### Phase 3: バックエンド API・パイプライン統合 (Steps 15-20)

**Step 15: アノテーション受信 API エンドポイント**
- ファイル: `src/api/annotations.py` (新規, FastAPI/Flask 等既存FWに追加)
- エンドポイント: `POST /api/annotations/persist`
- リクエスト: `{episode: int, script_path: str, beats: List[BeatDTO]}`
- レスポンス: `{persisted: int, errors: List[str]}`
- 認証: 既存ミドルウェア流用
- テスト: `tests/unit/api/test_annotations.py::test_persist_endpoint`

**Step 16: スクリプトファイル監視サービス (代替: ポーリング)**
- ファイル: `src/services/script_watcher.py` (新規)
- 方式: ファイルシステム監視 (`watchdog`) または定期ポーリング (30秒)
- 対象: `scripts/episode_{n}.md` パターン
- 変更検知 → パース → 検証 → 永続化 (AnnotationPersistence 再利用)
- 重複防止: ファイルハッシュ (SHA256) で前回と同じならスキップ
- テスト: `tests/unit/services/test_script_watcher.py::test_detect_change_and_persist`

**Step 17: パイプラインへのアノテーションステージ統合**
- ファイル: `src/pipeline/compression_pipeline.py` (既存編集)
- 追加: `annotation_parser: BeatParser`, `annotation_persistence: AnnotationPersistence`
- 実行タイミング: エピソード執筆完了判定時 (既存フック流用) または手動トリガー
- 設定: `pipeline.yaml` に `annotation: {enabled: true, watch_mode: true}`
- テスト: `tests/integration/pipeline/test_annotation_stage.py::test_annotation_stage_on_complete`

**Step 18: 次話プロンプト用アノテーション優先取得**
- ファイル: `src/pipeline/prompt_builder.py` (Week 1 既存編集)
- 修正: `build_emotional_context_prompt` で namespace 優先順位実装
- 順序: `annotation` → `rule_engine` → `pipeline` (信頼度順)
- 取得: `vector_store.get_latest(namespace, pair)` を順に試行、最初に見つかったもの採用
- テスト: `tests/unit/pipeline/test_prompt_builder_priority.py::test_annotation_priority_over_rule_engine`

**Step 19: アノテーション履歴・ロールバック API**
- ファイル: `src/api/annotations.py` (追加)
- エンドポイント:
  - `GET /api/annotations/history?episode=15&pair=A,B` → 過去ビート一覧
  - `POST /api/annotations/rollback` `{episode, beat_id}` → 指定ビート削除・再計算
- ロールバック実装: LogStore から該当レコード論理削除 → 再計算トリガー
- テスト: `tests/integration/api/test_annotation_rollback.py::test_rollback_removes_beat`

**Step 20: 統合テスト (エディタ→API→ストア→プロンプト)**
- ファイル: `tests/integration/annotations/test_full_flow.py` (新規)
- フロー:
  1. テスト用脚本ファイル作成 (インライン+フロントマター)
  2. `script_watcher` または API 直接呼び出しで永続化
  3. VectorStore `annotation` namespace に値確認
  4. `build_emotional_context_prompt` で注入文言確認 (アノテーション優先)
  5. Graph/Log にも同内容記録確認

---

### Phase 4: 設定・ドキュメント・リグレッション (Steps 21-24)

**Step 21: エディタ拡張インストール手順書**
- ファイル: `docs/editor_setup.md` (新規)
- 手順: `cd editor/vscode && npm install && npm run compile && code --install-extension .`
- 設定: `novel-script.scriptRoot` (脚本フォルダパス), `novel-script.apiEndpoint` (バックエンドURL)

**Step 22: アノテーション記述ガイド (作者向け)**
- ファイル: `docs/beat_annotation_guide.md` (新規)
- 内容:
  - インライン vs フロントマター 使い分け
  - 感情タイプ定義・使い分け例
  - `hidden` の意味・活用法 (表向き/内心)
  - `cause` 記述のコツ (プロットイベントID参照推奨)
  - よくあるミス・FAQ

**Step 23: リグレッションテスト追加**
- ファイル: `tests/regression/test_week3_regression.py` (新規)
- ケース:
  - `test_annotation_overrides_rule_engine`: アノテーション値がプロンプトに反映
  - `test_inline_and_frontmatter_merge`: 両形式混在時の正しいマージ
  - `test_validation_catches_errors`: 不明キャラ・範囲外検知
  - `test_auto_persist_on_save`: 保存で API 呼び出し発火
  - `test_rollback_restores_previous_state`: ロールバックで前状態復元

**Step 24: Week 3 完了チェックリスト・ドキュメント**
- ファイル: `docs/emotional_state_cache_week3.md` (新規)
- 内容:
  - エディタ拡張インストール・動作確認手順
  - アノテーション記述ルール
  - バックエンド API 仕様
  - Week 1-2 との統合動作確認手順
  - トラブルシューティング (よくあるエラー)

---

## 完了基準 (Definition of Done)

- [ ] 全 Step 1-24 テストパス (CI グリーン、E2E 含む)
- [ ] VS Code 拡張で: インライン挿入/フロントマター編集/グラフ表示/検証エラー表示 が動作
- [ ] 保存時に自動永続化 → Vector(annotation) に即反映確認
- [ ] 次話プロンプトでアノテーション値が最優先で注入される
- [ ] Graph/Log にも `source_type=annotation` で記録
- [ ] ロールバック API で指定ビート削除・状態復元確認
- [ ] Week 1-2 機能にリグレッションなし (全リグレッションテストパス)
- [ ] 作者向けガイドに従い非エンジニアがアノテーション記述可能