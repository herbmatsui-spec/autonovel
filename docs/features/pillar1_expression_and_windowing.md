# 第1の柱: 表現力・エンリッチメントの高度化と8専門オーディター窓枠評価

## 概要
本機能群は、AutoNovelの「第1の柱（Pillar 1）」として、商業小説水準の表現力向上および長編原稿に対する正確な監査・改善フィードバックループを実現したものです。

## 主要アーキテクチャ

### 1. 文単位・文法整合性保護五感拡充 (`src/agents/enrichment/sensory.py`)
- **完全非同期ディスパッチ**: `run_until_complete` を完全排除し、`asyncio.gather` による感情スパン並列生成と、タイムアウト（5秒）自動フォールバックを実装。
- **文構造・接続助詞保護**: 「〜悲しかったが、」「〜悔しいので」等の接続助詞文において、文末記号が破損したり係り受けが破綻する問題を「文全体スパン抽出（`sentence_span`）」により解消。
- **会話文保護ガード**: かぎ括弧内部のセリフが勝手に地の文の五感描写に置換されることを防止。
- **句読点サニタイズ**: 「。。」「、。」「。が」等の不正記号の自動清掃および破損時自動ロールバック。

### 2. トリビアリライト・注釈自然統合 (`src/agents/enrichment/trivia_rewrite.py`)
- **文脈適応リライト**: `[注: ...]` のような無機質な機械的タグを本文に埋め込むのではなく、キャラクターの視点（POV）・口調・シーンテンポに調和した自然な描写文としてインライン統合。
- **Jinja2 プロンプトテンプレート**: `prompts/enrichment/trivia_rewrite.jinja2` による厳密なトークン予算管理とメタデータ追跡。

### 3. 長編小説窓枠抽出器 (`src/agents/specialists/windowing.py`)
- **`NovelSectionExtractor`**:
  - `extract_opening(text, max_chars)`: 冒頭のつかみ（謎・違和感・危機）を文末（句点）スナップで抽出。
  - `extract_ending(text, max_chars)`: 末尾のクリフハンガーや次回への引きを文頭スナップで抽出。
  - `extract_four_sections(text, section_chars)`: 全文から起・承・転・結（導入・展開・山場・結び）の4代表セクションを等間隔サンプリング。
  - `extract_relevant_context(text, keywords, max_chars)`: 漢字熟語・カタカナ語に基づく重要シーン周辺段落のピンポイント抽出（挿絵・世界観整合性・時代考証用）。
- **`draft[:4000]` ハードコード打ち切りの完全根絶**: 全8専門オーディターから単純4000文字切り捨てを完全排除。

### 4. 具体的改稿差分（`ActionableDiff`）と再生成フィードバックループ
- **`ActionableDiff`**:
  - `location`: 指摘箇所の具体的な位置
  - `original_quote`: 問題のある原文引用
  - `improved_suggestion`: 改善後の具体的リライト文例
  - `rationale`: 改稿理由・根拠
- **再生成ディレクティブ自動注入 (`AuditAggregatorNode` & `PromptComposer`)**:
  - BookScore 70点未満時に、最低スコア次元の Actionable Diffs を抽出して再執筆プロンプトの最上部に【最優先・再生成修正ディレクティブ】として強制注入。
