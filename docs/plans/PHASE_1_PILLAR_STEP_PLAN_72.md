# 第1の柱: 小説表現・文章品質の極致化 72ステップ詳細実装計画書
## （エンリッチメントLLM完遂・五感構文保全・8専門オーディター窓枠評価）

- **策定日**: 2026年9月7日
- **対象ドキュメント**: [`docs/FUTURE_IMPROVEMENT_GUIDELINES.md`](file:///e:/hhh/autonovel/docs/FUTURE_IMPROVEMENT_GUIDELINES.md)
- **設計方針**: 低性能なLLMでも迷わず1ステップずつ確実に実装・検証できるよう、最小単位の作業に分割。12ステップごとに動作検証ゲートを設置。
- **総ステップ数**: 全72ステップ（6パート × 12ステップ）

---

## 📋 パート別構成概要

| パート | ステップ | テーマ | 主な対象ファイル | ステータス |
|---|---|---|---|---|
| **Part 1** | Step 1〜12 | トリビア文脈統合のLLMリライト完遂とトークン予算制御 | `src/agents/enrichment_agent.py`<br>`prompts/enrichment/` | ✅ **完了 (PASS)** |
| **Part 2** | Step 13〜24 | 五感拡充モジュールの完全非同期化とイベントループ健全化 | `src/agents/enrichment/sensory.py`<br>`src/agents/enrichment_agent.py` | ✅ **完了 (PASS)** |
| **Part 3** | Step 25〜36 | 五感拡充の構文破壊解消（文単位リライト・係り受け保護） | `src/agents/enrichment/sensory.py`<br>`src/prompts/enrichment/` | ✅ **完了 (PASS)** |
| **Part 4** | Step 37〜48 | 8専門オーディターの4000字打ち切り解消とセクション別窓枠機構 | `src/agents/specialists/windowing.py`<br>`src/agents/specialists/reader_hook_auditor.py` 等 | ⏳ **次期実装** |
| **Part 5** | Step 49〜60 | 全8専門オーディター窓枠適用と具体的改善差分(Actionable Diff) | `src/agents/specialists/`<br>`src/agents/specialist_auditor_base.py` | 未着手 |
| **Part 6** | Step 61〜72 | 特化再生成ディレクティブ統合、E2Eパイプライン導通、回帰検証 | `src/agents/specialists/adapter.py`<br>`src/agents/writing_agent.py`<br>`tests/` | 未着手 |

---

## 🚀 Part 1: トリビア文脈統合のLLMリライト完遂とトークン予算制御 (Step 1〜12)

### Step 1: `prompts/enrichment/trivia_insertion.py` のプロンプト定義拡張
- **目的**: 生のトリビアを文脈に自然に溶け込ませる1〜2文生成専用プロンプト定数 `TRIVIA_INLINE_REWRITE_PROMPT` を追加する。
- **対象ファイル**: `prompts/enrichment/trivia_insertion.py`
- **変更内容**:
  ```python
  TRIVIA_INLINE_REWRITE_PROMPT = """以下の小説シーン周辺の文脈に合わせて、指定の世界観トリビアを自然な地の文またはセリフ（1〜2文）に書き換えてください。
  【周辺文脈】
  {surrounding_text}
  【トリビア情報】
  {trivia_fact}
  【視点】{pov}
  【対象エンティティ】{entity}
  【制約】
  - 説明調（「実は〜」「歴史的には〜」）を避け、シーンの臨場感を損なわないようにすること。
  - 文体と視点（一人称/三人称）を厳格に維持すること。
  - 1〜2文の日本語テキストのみを出力してください。
  """
  ```
- **確認コマンド**: `python -c "from prompts.enrichment.trivia_insertion import TRIVIA_INLINE_REWRITE_PROMPT; assert '{trivia_fact}' in TRIVIA_INLINE_REWRITE_PROMPT; print('OK')"`
- **完了条件**: プロンプト文字列がインポートでき、プレースホルダーが存在すること。

### Step 2: Jinja2テンプレート `src/prompts/enrichment/trivia_rewrite.jinja2` の新設
- **目的**: PromptManager経由でカスタマイズ可能なトリビアリライト用テンプレートを作成する。
- **対象ファイル**: `src/prompts/enrichment/trivia_rewrite.jinja2`
- **変更内容**: 新規ファイル作成。周辺文脈、トリビア情報、視点、対象エンティティを受け取り、自然な描写へのリライトを促すJinja2テンプレートを記述。
- **確認コマンド**: `python -c "from pathlib import Path; assert Path('src/prompts/enrichment/trivia_rewrite.jinja2').exists(); print('OK')"`
- **完了条件**: ファイルが作成されUTF-8で読み込めること。

### Step 3: `EnrichmentAgent._rewrite_trivia_for_context` のスタブ解除とLLM呼び出し
- **目的**: `return trivia_fact` となっていた未呼び出しスタブを解消し、実際にLLMでリライトさせる。
- **対象ファイル**: `src/agents/enrichment_agent.py` の `_rewrite_trivia_for_context`
- **変更内容**:
  ```python
  # 修正前:
  # prompt = TRIVIA_INSERTION_PROMPT.format(...)
  # return trivia_fact

  # 修正後:
  prompt = TRIVIA_INLINE_REWRITE_PROMPT.format(
      surrounding_text=surrounding_text[:400],
      trivia_fact=trivia_fact,
      pov=pov,
      entity=entity or "世界観",
  )
  raw_res = self.llm.ainvoke(prompt) if hasattr(self.llm, "ainvoke") else self.llm(prompt)
  if inspect.isawaitable(raw_res):
      raw_res = await raw_res
  rewritten = str(getattr(raw_res, "content", raw_res)).strip()
  return rewritten if rewritten and len(rewritten) >= 5 else trivia_fact
  ```
- **確認コマンド**: `python -m py_compile src/agents/enrichment_agent.py`
- **完了条件**: 構文エラーがなく、`await` を伴うLLM呼び出しロジックが実装されていること。

### Step 4: `_rewrite_trivia_for_context` の例外ハンドリングとフォールバック保護
- **目的**: LLM呼び出し失敗時やタイムアウト時、例外でプロセスを落とさず安全に元の `trivia_fact` または空文字を返すようにする。
- **対象ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: `try...except Exception as e:` 内で `logger.warning` を出力し、`trivia_fact` をフォールバック返却。
- **確認コマンド**: `pytest tests/unit/test_enrichment_agent.py -k test_trivia -q`
- **完了条件**: LLM呼び出し例外が発生しても関数が安全に復帰すること。

### Step 5: `_find_insertion_points` のセリフ内誤挿入防止ガード
- **目的**: かぎ括弧「……」の途中にトリビアが挿入されて会話が分断されるのを防ぐ。
- **対象ファイル**: `src/agents/enrichment_agent.py` の `_find_insertion_points`
- **変更内容**: 挿入候補位置がセリフ内（開いた「」の中）にある場合、直後の閉じかぎ括弧（」）の後、または直前の文末へ補正するロジックを追加。
- **確認コマンド**: `python -c "from src.agents.enrichment_agent import EnrichmentAgent; agent = EnrichmentAgent(); pts = agent._find_insertion_points('「おい、あぶない！」と叫んだ。', 1); assert pts[0] > 0; print('OK')"`
- **完了条件**: かぎ括弧の内部に挿入インデックスが指定されないこと。

### Step 6: 視点（三人称/一人称）によるトリビア語尾の自動調整
- **目的**: 一人称作品で三人称的な解説口調（「〜であった」）が混入するのを防ぐ。
- **対象ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: `pov == "first_person"` の場合、末尾が「〜だった。」「〜と聞いたことがある。」など語り手の認識に合致するようプロンプト指示およびフォールバック補正を適用。
- **確認コマンド**: `python -m py_compile src/agents/enrichment_agent.py`
- **完了条件**: 一人称指定時に語尾が自然に整えられること。

### Step 7: `config/enrichment.yaml` にトリビアリライト設定項目を追加
- **目的**: リライト時のLLMパラメータ（temperature, max_tokens）を設定ファイルで管理可能にする。
- **対象ファイル**: `config/enrichment.yaml`
- **変更内容**:
  ```yaml
  trivia_insertion:
    enabled: true
    relevance_threshold: 0.7
    max_insertions_per_chapter: 3
    temperature: 0.5
    max_rewrite_tokens: 120
  ```
- **確認コマンド**: `python -c "import yaml; c = yaml.safe_load(open('config/enrichment.yaml'))['enrichment']['trivia_insertion']; assert 'temperature' in c; print('OK')"`
- **完了条件**: YAMLファイルが正常にロードされ、新規パラメータが取得できること。

### Step 8: `_enrich_with_trivia` のトークン予算制御の精緻化
- **目的**: 概算文字数だけでなく、挿入テキストの合計トークン数が予算を超えないよう厳格にガードする。
- **対象ファイル**: `src/agents/enrichment_agent.py` の `_enrich_with_trivia`
- **変更内容**: 累積挿入文字数・トークン数が `trivia_budget_chars` を超えた時点で後続の挿入を安全に break する。
- **確認コマンド**: `python -m py_compile src/agents/enrichment_agent.py`
- **完了条件**: 予算超過時にそれ以上の挿入が行われないこと。

### Step 9: トリビア挿入メタデータの Before / After 差分追跡
- **目的**: どの位置にどのトリビアがどのようにリライトされて挿入されたかをメタデータに記録する。
- **対象ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: `insertions_metadata` に `raw_trivia`, `rewritten_text`, `entity`, `target_position` を完全記録。
- **確認コマンド**: `python -m py_compile src/agents/enrichment_agent.py`
- **完了条件**: 実行後の `enrichment_metadata["trivia"]` に詳細情報が含まれること。

### Step 10: トリビアリライト機能の単体テスト作成
- **目的**: モックLLMを用いてリライトとフォールバックの挙動を検証する。
- **対象ファイル**: `tests/unit/test_trivia_rewrite.py` (新規作成)
- **変更内容**: 正常系（LLM成功時）、異常系（LLM失敗時のフォールバック）、セリフガードのテストを記述。
- **確認コマンド**: `pytest tests/unit/test_trivia_rewrite.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 11: EnrichmentAgent 全体におけるトリビア結合テスト
- **目的**: ドラフト本文を入力し、トリビアが自然に挿入されて出力されるパイプラインをテスト。
- **対象ファイル**: `tests/integration/test_enrichment_trivia.py` (新規作成)
- **変更内容**: `EnrichmentAgent.execute` を通じた統合テスト。
- **確認コマンド**: `pytest tests/integration/test_enrichment_trivia.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 12: 【Check Point 1】Part 1 動作検証と回帰テスト
- **目的**: Part 1 の修正によって既存のテストが壊れていないか確認する。
- **確認コマンド**: `pytest tests/unit/test_trivia_rewrite.py tests/integration/test_enrichment_trivia.py tests/integration/test_regression_phase4.py -v`
- **完了条件**: すべてのテストがオールグリーン（ALL GREEN）であること。

---

## ⚡ Part 2: 五感拡充モジュールの完全非同期化とイベントループ健全化 (Step 13〜24)

### Step 13: `src/agents/enrichment/sensory.py` の `generate_sensory_details` 非同期化
- **目的**: `def generate_sensory_details` を `async def generate_sensory_details` に変更し、非同期化の基盤を作る。
- **対象ファイル**: `src/agents/enrichment/sensory.py`
- **変更内容**: 関数定義に `async` を付与し、型アノテーションを更新。
- **確認コマンド**: `python -m py_compile src/agents/enrichment/sensory.py`
- **完了条件**: 構文エラーなく非同期関数として定義されていること。

### Step 14: `sensory.py` 内の `run_until_complete` の完全撤廃
- **目的**: 実行中イベントループ下でのクラッシュ（`RuntimeError: This event loop is already running`）を根絶する。
- **対象ファイル**: `src/agents/enrichment/sensory.py` (行212〜214付近)
- **変更内容**:
  ```python
  # 削除前:
  # if inspect.isawaitable(raw_output):
  #     import asyncio
  #     raw_output = asyncio.get_event_loop().run_until_complete(raw_output)

  # 修正後:
  if inspect.isawaitable(raw_output):
      raw_output = await raw_output
  ```
- **確認コマンド**: `grep -rn "run_until_complete" src/agents/enrichment/` でヒット件数が 0件 であること。
- **完了条件**: `run_until_complete` が完全に排除され `await` に置き換わっていること。

### Step 15: LLM呼び出しインターフェースの非同期統一ディスパッチ
- **目的**: `ainvoke`, `generate`, コルーチン callable など多様な LLM クライアントを統一的に `await` で呼び出す。
- **対象ファイル**: `src/agents/enrichment/sensory.py`
- **変更内容**:
  ```python
  if hasattr(llm, "ainvoke"):
      raw_output = await llm.ainvoke(prompt)
  elif hasattr(llm, "generate"):
      raw_output = llm.generate(prompt)
      if inspect.isawaitable(raw_output):
          raw_output = await raw_output
  elif callable(llm):
      raw_output = llm(prompt)
      if inspect.isawaitable(raw_output):
          raw_output = await raw_output
  ```
- **確認コマンド**: `python -m py_compile src/agents/enrichment/sensory.py`
- **完了条件**: 構文エラーなく、すべての呼び出しパスが非同期対応していること。

### Step 16: `expand_sensory_details_pipeline` の `async def` 化
- **目的**: パイプラインのエントリーポイントを非同期化し、`await generate_sensory_details` を呼べるようにする。
- **対象ファイル**: `src/agents/enrichment/sensory.py`
- **変更内容**: `async def expand_sensory_details_pipeline(...)` に変更。
- **確認コマンド**: `python -c "import inspect; from src.agents.enrichment.sensory import expand_sensory_details_pipeline; assert inspect.iscoroutinefunction(expand_sensory_details_pipeline); print('OK')"`
- **完了条件**: `expand_sensory_details_pipeline` がコルーチン関数であること。

### Step 17: `replace_with_sensory_expansion` のシグネチャと処理の整理
- **目的**: 置換処理関数が非同期パイプラインから正しくデータを受け取れるように引数と戻り値を整える。
- **対象ファイル**: `src/agents/enrichment/sensory.py`
- **変更内容**: 引数型の整理と、空配列ガード、位置逆順ソート処理の安定化。
- **確認コマンド**: `python -m py_compile src/agents/enrichment/sensory.py`
- **完了条件**: 構文エラーがないこと。

### Step 18: `EnrichmentAgent._expand_sensory_details` からの `await` 呼び出し更新
- **目的**: 呼び出し元の `EnrichmentAgent` 側で `await expand_sensory_details_pipeline` を呼ぶように同期呼び出しを改修。
- **対象ファイル**: `src/agents/enrichment_agent.py` の `_expand_sensory_details`
- **変更内容**:
  ```python
  # 修正前:
  # enriched_text, sensory_meta = expand_sensory_details_pipeline(...)
  # 修正後:
  enriched_text, sensory_meta = await expand_sensory_details_pipeline(...)
  ```
- **確認コマンド**: `python -m py_compile src/agents/enrichment_agent.py`
- **完了条件**: コルーチンオブジェクトがそのまま渡されるバグを防ぎ、正しく `await` されていること。

### Step 19: 個別感覚生成に対する非同期タイムアウト設定
- **目的**: 外部LLMのAPI遅延でパイプライン全体が無制限にハングするのを防ぐ。
- **対象ファイル**: `src/agents/enrichment/sensory.py`
- **変更内容**: `asyncio.wait_for(..., timeout=5.0)` でラップし、タイムアウト時は自動的に辞書フォールバックへ移行。
- **確認コマンド**: `python -m py_compile src/agents/enrichment/sensory.py`
- **完了条件**: タイムアウト処理が正しく実装されていること。

### Step 20: 複数感情スパンの並列LLM生成 (`asyncio.gather`)
- **目的**: 1エピソード中に複数箇所の感情スパンがある場合、直列実行ではなく `asyncio.gather` で並列生成し処理時間を半減させる。
- **対象ファイル**: `src/agents/enrichment/sensory.py`
- **変更内容**:
  ```python
  tasks = [generate_sensory_details(span, scene_context, pov, llm, prompt_manager) for span in emotion_spans]
  all_sensory_details = await asyncio.gather(*tasks, return_exceptions=True)
  ```
- **確認コマンド**: `python -m py_compile src/agents/enrichment/sensory.py`
- **完了条件**: 例外発生時もフォールバック結果に置き換わる安全な並列処理になっていること。

### Step 21: 非同期フォールバックのシームレス切り替え保証
- **目的**: LLM未設定時や全タスク例外時に、即座に同期辞書ベースの感覚描写が返ることを保証する。
- **対象ファイル**: `src/agents/enrichment/sensory.py`
- **変更内容**: `return_exceptions=True` の結果を走査し、例外要素を `_fallback_sensory_details` で置換。
- **確認コマンド**: `python -m py_compile src/agents/enrichment/sensory.py`
- **完了条件**: 例外が上位に漏れ出さずフォールバックされること。

### Step 22: 実行中イベントループ下での非同期単体テスト作成
- **目的**: FastAPIやasyncio環境と同じ「イベントループ稼働中」の状態でクラッシュしないことをテストする。
- **対象ファイル**: `tests/unit/test_sensory_async.py` (新規作成)
- **変更内容**: `@pytest.mark.asyncio` を使用した単体テスト。
- **確認コマンド**: `pytest tests/unit/test_sensory_async.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 23: `EnrichmentAgent` との非同期結合テスト
- **目的**: `EnrichmentAgent.execute` 全体を通した五感拡充の非同期フローをテスト。
- **対象ファイル**: `tests/integration/test_enrichment_sensory_async.py` (新規作成)
- **変更内容**: モックLLMおよび実コンテキストを用いた結合テスト。
- **確認コマンド**: `pytest tests/integration/test_enrichment_sensory_async.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 24: 【Check Point 2】Part 2 動作検証と回帰テスト
- **目的**: 非同期化による既存機能の回帰がないか全スイートを実行。
- **確認コマンド**: `pytest tests/unit/test_sensory_async.py tests/integration/test_enrichment_sensory_async.py tests/unit/test_enrichment_agent.py -v`
- **完了条件**: すべて PASS すること。

---

## ✍️ Part 3: 五感拡充の構文破壊解消（文単位リライト・係り受け保護） (Step 25〜36)

### Step 25: 感情語を含む文（Sentence）境界抽出関数 `extract_sentence_span` の新設
- **目的**: 単語単位ではなく、前後の句読点（。！？\n）までの文境界を取得する。
- **対象ファイル**: `src/agents/enrichment/sensory.py`
- **変更内容**:
  ```python
  def extract_sentence_span(text: str, match_start: int, match_end: int) -> tuple[int, int, str]:
      """感情語を含む文全体の開始位置、終了位置、文テキストを抽出する。"""
      # 直前の句読点または文頭を探す
      start = 0
      for delim in ["。", "！", "？", "\n"]:
          pos = text.rfind(delim, 0, match_start)
          if pos != -1 and pos + 1 > start:
              start = pos + 1
      # 直後の句読点または文末を探す
      end = len(text)
      for delim in ["。", "！", "？", "\n"]:
          pos = text.find(delim, match_end)
          if pos != -1 and (pos + 1) < end:
              end = pos + 1
      return start, end, text[start:end].strip()
  ```
- **確認コマンド**: `python -c "from src.agents.enrichment.sensory import extract_sentence_span; s, e, t = extract_sentence_span('彼は悲しかったが耐えた。', 2, 6); assert t == '彼は悲しかったが耐えた。'; print('OK')"`
- **完了条件**: 感情語を含む文全体が正しく切り出せること。

### Step 26: 接続助詞（「〜だが」「〜ものの」「〜ので」等）の検知ロジック
- **目的**: 感情語の直後に続く接続助詞を検出し、文末置換時に「涙がこぼれる。が」のような分裂を防ぐ。
- **対象ファイル**: `src/agents/enrichment/sensory.py`
- **変更内容**: `CONJUNCTION_PATTERNS = [r"^(?:だが|けれど|ものの|ので|から|ため|ながら|が、|が)"]` を定義し、後続助詞を検知して保持。
- **確認コマンド**: `python -m py_compile src/agents/enrichment/sensory.py`
- **完了条件**: 後続助詞が判定できること。

### Step 27: `src/prompts/enrichment/sensory_expansion.jinja2` を文単位リライトへ改訂
- **目的**: LLMに対して単語の言い換えではなく、「文全体の自然な五感描写リライト」を指示するプロンプトへ刷新。
- **対象ファイル**: `src/prompts/enrichment/sensory_expansion.jinja2`
- **変更内容**:
  ```jinja2
  あなたは小説の情景・身体感覚描写（Show, Don't Tell）を極めたプロの文芸編集者です。
  以下の「元の文」に含まれる抽象的な感情表現を、前後の文脈に調和する具体的な五感描写・身体反応に富んだ自然な文（1〜2文）にリライトしてください。
  【元の文】
  {{ original_sentence }}
  【検出された感情】{{ emotion }}
  【優先感覚】{{ preferred_senses | join(', ') }}
  【シーン状況】{{ scene_context }}
  【視点】{{ pov }}
  【制約】
  - 「[visual]」などのタグや解説文は一切出力せず、リライト後の本文のみを出力すること。
  - 後続の文脈との接続（接続助詞や因果関係）を壊さないこと。
  ```
- **確認コマンド**: `python -c "from jinja2 import Template; t = Template(open('src/prompts/enrichment/sensory_expansion.jinja2', encoding='utf-8').read()); print('Template OK')"`
- **完了条件**: Jinja2テンプレートとして正しくパースできること。

### Step 28: `EmotionSpan` データ構造の拡張
- **目的**: 文単位リライトに必要な `sentence_start`, `sentence_end`, `sentence_text` を保持できるように拡張。
- **対象ファイル**: `src/agents/enrichment/sensory.py` の `EmotionSpan`
- **変更内容**:
  ```python
  @dataclass
  class EmotionSpan:
      start: int
      end: int
      emotion: str
      intensity: float
      abstract_phrase: str
      sentence_start: int = 0
      sentence_end: int = 0
      sentence_text: str = ""
  ```
- **確認コマンド**: `python -c "from src.agents.enrichment.sensory import EmotionSpan; span = EmotionSpan(0, 5, 'sadness', 0.8, '悲しかった', 0, 10, '彼は悲しかった。'); assert span.sentence_text != ''; print('OK')"`
- **完了条件**: 新規フィールドが安全に初期化できること。

### Step 29: 単語置換から文置換へのリプレイスメントアルゴリズム刷新
- **目的**: `replace_with_sensory_expansion` を単語置換から `sentence_start:sentence_end` の文置換へ全面刷新する。
- **対象ファイル**: `src/agents/enrichment/sensory.py` の `replace_with_sensory_expansion`
- **変更内容**:
  ```python
  # 単語単位 span.start:span.end ではなく、文単位 span.sentence_start:span.sentence_end を置換
  enriched_text = enriched_text[:span.sentence_start] + expanded_sentence + enriched_text[span.sentence_end:]
  ```
- **確認コマンド**: `python -m py_compile src/agents/enrichment/sensory.py`
- **完了条件**: 文単位で正しく置換が行われること。

### Step 30: 句読点サニタイズ処理関数 `sanitize_punctuation` の実装
- **目的**: 置換後に万一生じた「。。」「、。」「。が」などの不正な記号並びを自動清掃する。
- **対象ファイル**: `src/agents/enrichment/sensory.py`
- **変更内容**:
  ```python
  def sanitize_punctuation(text: str) -> str:
      text = re.sub(r'。+', '。', text)
      text = re.sub(r'、+', '、', text)
      text = re.sub(r'。、', '、', text)
      text = re.sub(r'、。', '。', text)
      text = re.sub(r'。(が|けれど|だが)', r'\1', text)
      return text
  ```
- **確認コマンド**: `python -c "from src.agents.enrichment.sensory import sanitize_punctuation; assert sanitize_punctuation('悲しかった。が、') == '悲しかったが、'; print('OK')"`
- **完了条件**: 不正な句読点が自然に補正されること。

### Step 31: ルールベースフォールバック用の文型テンプレート整備
- **目的**: LLM未設定時でも「涙がこぼれる。が」にならないよう、文型に応じた自然なフォールバック文を生成する。
- **対象ファイル**: `src/agents/enrichment/sensory.py`
- **変更内容**: 主語や接続詞を保持したまま「〜という感情が押し寄せ、胸が締め付けられた」などの自然な定型文結合を実装。
- **確認コマンド**: `python -m py_compile src/agents/enrichment/sensory.py`
- **完了条件**: フォールバック時でも文法が破壊されないこと。

### Step 32: 会話文（セリフ）内部の保護ガード
- **目的**: 登場人物のセリフ内の感情表現（「俺は悔しいんだ！」）を勝手に地の文の五感描写に置換しないよう保護。
- **対象ファイル**: `src/agents/enrichment/sensory.py` の `detect_abstract_emotions`
- **変更内容**: 検出位置がかぎ括弧内部（セリフ）である場合、置換対象から除外するか、セリフ専用の軽微な感嘆表現にとどめるガードを追加。
- **確認コマンド**: `python -c "from src.agents.enrichment.sensory import detect_abstract_emotions; spans = detect_abstract_emotions('「悲しいよ」と彼は言った。'); assert all('言った' in s.sentence_text or not s.sentence_text.startswith('「') for s in spans); print('OK')"`
- **完了条件**: 会話文が不自然に破壊されないこと。

### Step 33: 文法整合性チェッカー（自動ロールバック機構）
- **目的**: リライト後の文が短すぎる、または記号だらけで破損している場合、自動的に元の文を維持するフェイルセーフを実装。
- **対象ファイル**: `src/agents/enrichment/sensory.py`
- **変更内容**: リライト文の長さ、末尾の完結性を検証し、異常時は置換をキャンセル（ロールバック）。
- **確認コマンド**: `python -m py_compile src/agents/enrichment/sensory.py`
- **完了条件**: 破損文が本文に混入しないこと。

### Step 34: 構文破壊防止の単体テスト作成
- **目的**: 「悲しかったが」「嬉しかったのに」「怒り狂った末に」等の典型的な係り受けパターンで構文が壊れないかを網羅検証。
- **対象ファイル**: `tests/unit/test_sensory_grammar_preservation.py` (新規作成)
- **変更内容**: 10パターン以上の接続助詞文に対するテストケース記述。
- **確認コマンド**: `pytest tests/unit/test_sensory_grammar_preservation.py -v`
- **完了条件**: 全パターンでテストが PASS すること。

### Step 35: 長文ドラフトにおける感覚拡充の整合性結合テスト
- **目的**: 実際の小説本文（3000文字超）に対して感覚拡充を適用し、文法の破綻がないことを検証。
- **対象ファイル**: `tests/integration/test_sensory_full_text.py` (新規作成)
- **変更内容**: 複数段落のドラフトを用いた結合テスト。
- **確認コマンド**: `pytest tests/integration/test_sensory_full_text.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 36: 【Check Point 3】Part 3 動作検証と回帰テスト
- **目的**: Part 1〜Part 3 の全エンリッチメント機能の回帰テストを実施。
- **確認コマンド**: `pytest tests/unit/test_sensory_grammar_preservation.py tests/integration/test_sensory_full_text.py tests/unit/test_trivia_rewrite.py -v`
- **完了条件**: すべて PASS すること。

---

## 🔍 Part 4: 8専門オーディターの4000字打ち切り解消とセクション別窓枠機構 (Step 37〜48)

### Step 37: `src/agents/specialists/windowing.py` の新設（窓枠抽出基盤）
- **目的**: 長編テキストから冒頭、中盤、クライマックス、結末などを安全に切り出す汎用窓枠モジュールを作成する。
- **対象ファイル**: `src/agents/specialists/windowing.py`
- **変更内容**: クラス `NovelSectionExtractor` を定義し、空実装と型定義を作成。
- **確認コマンド**: `python -c "import src.agents.specialists.windowing; print('OK')"`
- **完了条件**: モジュールがインポートできること。

### Step 38: `NovelSectionExtractor` に冒頭・末尾抽出メソッドを実装
- **目的**: 指定文字数（例: 各1,500字）で冒頭部と末尾（結末）部を句切れ良く抽出する。
- **対象ファイル**: `src/agents/specialists/windowing.py`
- **変更内容**: `extract_opening(text, max_chars=1500)`, `extract_ending(text, max_chars=1500)` の実装。文の途中で切れず句点（。）でスナップする。
- **確認コマンド**: `python -c "from src.agents.specialists.windowing import NovelSectionExtractor; ext = NovelSectionExtractor(); op = ext.extract_opening('あ'*3000, 1000); assert len(op) <= 1000; print('OK')"`
- **完了条件**: 指定文字数以内で文末スナップされた抽出ができること。

### Step 39: `NovelSectionExtractor` に起承転結・均等サンプリング窓枠メソッドを実装
- **目的**: 本文全体から4等分（導入、展開、山場、結び）の代表セクションをサンプリングする。
- **対象ファイル**: `src/agents/specialists/windowing.py`
- **変更内容**: `extract_four_sections(text, section_chars=800)` の実装。
- **確認コマンド**: `python -c "from src.agents.specialists.windowing import NovelSectionExtractor; ext = NovelSectionExtractor(); s = ext.extract_four_sections('テスト文'*1000, 500); assert len(s) == 4; print('OK')"`
- **完了条件**: 4つのセクションが正しく返ること。

### Step 40: `SpecialistAuditor` 基底クラスへの窓枠抽出ヘルパー統合
- **目的**: 全8オーディターから共通して `self.extractor` を使えるように基底クラスで初期化する。
- **対象ファイル**: `src/agents/specialist_auditor_base.py`
- **変更内容**: `self.section_extractor = NovelSectionExtractor()` を `__init__` に追加。
- **確認コマンド**: `python -c "from src.agents.specialists.reader_hook_auditor import ReaderHookAuditor; a = ReaderHookAuditor(); assert hasattr(a, 'section_extractor'); print('OK')"`
- **完了条件**: オーディターインスタンスから窓枠抽出器が参照できること。

### Step 41: `reader_hook_auditor.py` の `draft[:4000]` 撤廃
- **目的**: 本文が何万文字あっても、冒頭フックと真の末尾（次回への引き・クリフハンガー）を確実に供給する。
- **対象ファイル**: `src/agents/specialists/reader_hook_auditor.py`
- **変更内容**:
  ```python
  # 修正前:
  # prompt = READER_HOOK_USER_PROMPT.format(draft_text=draft[:4000])

  # 修正後:
  opening = self.section_extractor.extract_opening(draft, max_chars=1800)
  ending = self.section_extractor.extract_ending(draft, max_chars=1800)
  prompt = READER_HOOK_WINDOWED_USER_PROMPT.format(
      opening_text=opening,
      ending_text=ending,
      total_chars=len(draft),
  )
  ```
- **確認コマンド**: `python -m py_compile src/agents/specialists/reader_hook_auditor.py`
- **完了条件**: `draft[:4000]` が削除され、冒頭と末尾が独立して渡されること。

### Step 42: `READER_HOOK_WINDOWED_USER_PROMPT` のプロンプト改訂
- **目的**: LLMに対して冒頭と末尾を明確に区別して審査・採点させるプロンプトを定義。
- **対象ファイル**: `src/agents/specialists/reader_hook_auditor.py`
- **変更内容**:
  ```python
  READER_HOOK_WINDOWED_USER_PROMPT = """【総文字数】{total_chars}文字
  【冒頭セクション（つかみ・オープニングフック）】
  {opening_text}

  【末尾セクション（クリフハンガー・次回への引き）】
  {ending_text}

  上記文章の「冒頭の引きの強さ（謎・違和感・危機）」と「末尾のクリフハンガー度」を厳格に審査し、0〜100で採点してください。
  """
  ```
- **確認コマンド**: `python -m py_compile src/agents/specialists/reader_hook_auditor.py`
- **完了条件**: プロンプト定義が正常に反映されていること。

### Step 43: `structure_auditor.py` の `draft[:4000]` 撤廃
- **目的**: 4000文字で切られて「転・結」が判定不能になる問題を解消する。
- **対象ファイル**: `src/agents/specialists/structure_auditor.py`
- **変更内容**: `self.section_extractor.extract_four_sections(draft, 800)` を使用し、起承転結のサマリー窓枠を生成してプロンプトへ注入。
- **確認コマンド**: `python -m py_compile src/agents/specialists/structure_auditor.py`
- **完了条件**: `structure_auditor.py` から `[:4000]` が完全に排除されていること。

### Step 44: `STRUCTURE_USER_PROMPT` のプロンプト改訂
- **目的**: 4つのセクション（起・承・転・結）とプロット概要を対比させて構成を評価させるプロンプトへ更新。
- **対象ファイル**: `src/agents/specialists/structure_auditor.py`
- **変更内容**: 起承転結の各パートがプロットに沿って正しく機能しているかを審査するプロンプト定義。
- **確認コマンド**: `python -m py_compile src/agents/specialists/structure_auditor.py`
- **完了条件**: 新規プロンプトが適用されていること。

### Step 45: `multimodal_auditor.py` の `draft[:3000]` 撤廃
- **目的**: 挿絵対象シーンが本文後半にある場合に、挿絵プロンプトとの整合性が判定できない問題を解消。
- **対象ファイル**: `src/agents/specialists/multimodal_auditor.py`
- **変更内容**: 挿絵プロンプトに含まれるキーワード（キャラクター名、場所名など）が出現する本文段落を窓枠抽出して優先的にLLMへ渡す。
- **確認コマンド**: `python -m py_compile src/agents/specialists/multimodal_auditor.py`
- **完了条件**: `draft[:3000]` が撤廃され、挿絵文脈マッチング窓枠が渡されること。

### Step 46: ルールベースフォールバック側（`fallback_utils.py` 等）の全文・末尾対応
- **目的**: LLM未設定時の正規表現判定においても、末尾300文字を確実に末尾から取得するように修正。
- **対象ファイル**: `src/agents/specialists/reader_hook_auditor.py` の `_fallback`
- **変更内容**: `ending = draft[-500:] if len(draft) > 500 else draft` とし、4000文字目ではなく真の末尾から取得。
- **確認コマンド**: `python -c "from src.agents.specialists.reader_hook_auditor import ReaderHookAuditor; a = ReaderHookAuditor(); res = a._fallback({'draft_text': 'あ'*5000 + 'どうなる！？'}); assert res.score > 20; print('OK')"`
- **完了条件**: 5000文字超のドラフトの末尾フックがフォールバックでも検出できること。

### Step 47: 窓枠抽出器およびフック・構成オーディターの単体テスト作成
- **目的**: 8000文字の長編ダミードラフトを用い、末尾のクリフハンガーが正しく認識されるか検証。
- **対象ファイル**: `tests/unit/test_windowed_auditors.py` (新規作成)
- **変更内容**: 8000文字の冒頭、末尾、起承転結を切り出すテストケース。
- **確認コマンド**: `pytest tests/unit/test_windowed_auditors.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 48: 【Check Point 4】Part 4 動作検証と回帰テスト
- **目的**: 窓枠化による既存オーディターテストの整合性確認。
- **確認コマンド**: `pytest tests/unit/test_windowed_auditors.py tests/unit/test_specialist_auditors.py -v`
- **完了条件**: すべて PASS すること。

---

## 🎯 Part 5: 全8専門オーディター窓枠適用と具体的改善差分(Actionable Diff) (Step 49〜60)

### Step 49: `consistency_auditor.py` の窓枠適用
- **目的**: 主要キャラクターの初登場・再登場シーンや重要設定言及箇所を全文からサンプリングして渡す。
- **対象ファイル**: `src/agents/specialists/consistency_auditor.py`
- **変更内容**: `draft[:4000]` を撤廃し、World Bible主要エンティティの登場箇所周辺窓枠を抽出して結合。
- **確認コマンド**: `python -m py_compile src/agents/specialists/consistency_auditor.py`
- **完了条件**: `draft[:4000]` が削除されていること。

### Step 50: `creativity_auditor.py` の窓枠適用
- **目的**: 全文から等間隔（均等スライディングウィンドウ）で3〜4箇所の表現サンプルを抽出して渡し、表現の多様性を評価。
- **対象ファイル**: `src/agents/specialists/creativity_auditor.py`
- **変更内容**: `draft[:4000]` を撤廃し、均等サンプリング窓枠を適用。
- **確認コマンド**: `python -m py_compile src/agents/specialists/creativity_auditor.py`
- **完了条件**: `draft[:4000]` が削除されていること。

### Step 51: `emotion_curve_auditor.py` の窓枠適用
- **目的**: 感情の起伏（カタルシス、ピンチ、安堵）が章全体でどう遷移したかを評価するため、等間隔サンプリングを適用。
- **対象ファイル**: `src/agents/specialists/emotion_curve_auditor.py`
- **変更内容**: `draft[:4000]` を撤廃し、感情変化セクション群を抽出。
- **確認コマンド**: `python -m py_compile src/agents/specialists/emotion_curve_auditor.py`
- **完了条件**: `draft[:4000]` が削除されていること。

### Step 52: `style_auditor.py` の窓枠適用
- **目的**: 冒頭・中盤・結末でキャラクターの口調や文体DNAがブレていないかを均等窓枠で審査。
- **対象ファイル**: `src/agents/specialists/style_auditor.py`
- **変更内容**: `draft[:4000]` を撤廃し、セリフと地の文のバランスサンプルを抽出。
- **確認コマンド**: `python -m py_compile src/agents/specialists/style_auditor.py`
- **完了条件**: `draft[:4000]` が削除されていること。

### Step 53: `factual_auditor.py` の窓枠適用
- **目的**: 設定資料（GraphRAG/World Bible）の専門用語が出現する箇所を全文検索してピンポイント抽出。
- **対象ファイル**: `src/agents/specialists/factual_auditor.py`
- **変更内容**: `draft[:4000]` を撤廃し、用語出現窓枠を抽出。
- **確認コマンド**: `grep -rn "draft\[:4000\]" src/agents/specialists/` でヒット件数が 0件 であること。
- **完了条件**: 全8オーディターから `draft[:4000]` が完全に根絶されていること。

### Step 54: `ActionableDiff` データクラスの定義と `SpecialistAuditResult` への追加
- **目的**: 「どの行をどう直せばよいか」のBefore/After差分を格納する型を定義。
- **対象ファイル**: `src/agents/specialist_auditor_base.py`
- **変更内容**:
  ```python
  @dataclass
  class ActionableDiff:
      location: str  # 例: "冒頭3段落目", "末尾2文"
      original_quote: str  # 問題のある原文引用
      improved_suggestion: str  # 改善後の書き換え例
      rationale: str  # なぜ直すべきか

  @dataclass
  class SpecialistAuditResult:
      ...
      actionable_diffs: list[ActionableDiff] = field(default_factory=list)
  ```
- **確認コマンド**: `python -c "from src.agents.specialist_auditor_base import ActionableDiff, SpecialistAuditResult; r = SpecialistAuditResult('consistency', 80.0, actionable_diffs=[ActionableDiff('冒頭', 'A', 'B', 'C')]); assert len(r.actionable_diffs) == 1; print('OK')"`
- **完了条件**: 新規データ構造が定義され、`to_dict()` でもシリアライズできること。

### Step 55: `_judge_with_llm` の共通JSONフォーマット指示拡張
- **目的**: LLMに対して、点数や講評だけでなく `actionable_diffs` 配列の出力を必須化する。
- **対象ファイル**: `src/agents/specialist_auditor_base.py` の `_judge_with_llm`
- **変更内容**:
  ```json
  "actionable_diffs": [
    {
      "location": "該当箇所",
      "original_quote": "元の文の引用",
      "improved_suggestion": "こう書き換えるべきという具体例",
      "rationale": "改善理由"
    }
  ]
  ```
- **確認コマンド**: `python -m py_compile src/agents/specialist_auditor_base.py`
- **完了条件**: プロンプト指示に `actionable_diffs` が追加されていること。

### Step 56: `_judge_with_llm` の JSONパース処理拡張
- **目的**: LLMが返した `actionable_diffs` をパースし、`ActionableDiff` オブジェクトのリストとして復元する。
- **対象ファイル**: `src/agents/specialist_auditor_base.py`
- **変更内容**: 辞書から `ActionableDiff` への安全なマッピング（フィールド欠損時のフォールバック処理含む）。
- **確認コマンド**: `python -m py_compile src/agents/specialist_auditor_base.py`
- **完了条件**: パースエラーを起こさずオブジェクト化できること。

### Step 57: ルールベースフォールバック時における定型 `actionable_diffs` 生成
- **目的**: LLM未設定時でも、検出された問題（例: 死亡キャラ登場、フック不足）に応じた Before/After 例を生成する。
- **対象ファイル**: `src/agents/specialists/fallback_utils.py`
- **変更内容**: ルールベース検出結果から `ActionableDiff` を構築して返却。
- **確認コマンド**: `python -m py_compile src/agents/specialists/fallback_utils.py`
- **完了条件**: フォールバック時でも `actionable_diffs` が空にならないこと。

### Step 58: `AuditAggregator` における Actionable Diff 集約
- **目的**: 8専門家が出力した全 `actionable_diffs` を集約し、重複排除と優先度ソートを行う。
- **対象ファイル**: `src/services/audit_aggregator.py`
- **変更内容**: `BookScoreResult` に `all_actionable_diffs: list[ActionableDiff]` を追加し、集約メソッドを実装。
- **確認コマンド**: `python -m py_compile src/services/audit_aggregator.py`
- **完了条件**: 集約結果から全体の改善差分が取得できること。

### Step 59: 全8オーディター窓枠 & Actionable Diff 単体テスト作成
- **目的**: 8名すべての専門家が窓枠入力を受け取り、Actionable Diff を出力することをテスト。
- **対象ファイル**: `tests/unit/test_specialist_actionable_diffs.py` (新規作成)
- **変更内容**: モックLLMを用いた各オーディターの出力アサーション。
- **確認コマンド**: `pytest tests/unit/test_specialist_actionable_diffs.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 60: 【Check Point 5】Part 5 動作検証と回帰テスト
- **目的**: 全8オーディターの窓枠評価と Actionable Diff の総合検証。
- **確認コマンド**: `pytest tests/unit/test_specialist_actionable_diffs.py tests/unit/test_specialist_auditors.py -v`
- **完了条件**: すべて PASS すること。

---

## 🔄 Part 6: 特化再生成ディレクティブ統合、E2Eパイプライン導通、回帰検証 (Step 61〜72)

### Step 61: `AuditAggregatorNode.to_agent_result` の Actionable Diff 反映
- **目的**: BookScore 70点未満時の再生成ディレクティブに、具体的な Before / After 書き換え差分を注入する。
- **対象ファイル**: `src/agents/specialists/adapter.py` の `to_agent_result`
- **変更内容**:
  ```python
  # 最低スコア次元の Actionable Diff を抽出してディレクティブに追加
  diff_texts = []
  for diff in score_result.get_actionable_diffs_for(lowest_dim):
      diff_texts.append(f"- 【該当】{diff.location}\n  【現状】{diff.original_quote}\n  【改稿案】{diff.improved_suggestion}")
  regeneration_directive += "\n【具体的改稿サンプル】\n" + "\n".join(diff_texts[:3])
  ```
- **確認コマンド**: `python -m py_compile src/agents/specialists/adapter.py`
- **完了条件**: 再生成指示テキストに Before/After サンプルが含まれること。

### Step 62: 再生成フォーカス（`regeneration_focus`）との連携強化
- **目的**: 再生成時にどの専門オーディターが低スコアだったかをコンテキストに明示し、後続エージェントが参照可能にする。
- **対象ファイル**: `src/agents/specialists/adapter.py`
- **変更内容**: `artifacts["regeneration_focus"] = [lowest_dim]` をセット。
- **確認コマンド**: `python -m py_compile src/agents/specialists/adapter.py`
- **完了条件**: `AgentResult.artifacts` に正しいフォーカスが含まれること。

### Step 63: `WritingAgent` における `regeneration_directive` 優先注入
- **目的**: 執筆プロンプトの最上部に「最優先改稿指示」として Actionable Diff を配置し、LLMに確実に反映させる。
- **対象ファイル**: `src/agents/writing_agent.py`
- **変更内容**: プロンプト生成時に `ctx.artifacts.get("regeneration_directive")` がある場合、システム指示の直後に強調枠で注入。
- **確認コマンド**: `python -m py_compile src/agents/writing_agent.py`
- **完了条件**: 再生成時に指示がプロンプトに組み込まれること。

### Step 64: 再生成時の文脈圧縮（`FourLayerCompressor`）連携確認
- **目的**: 再生成時、フォーカス項目（例: structure）に応じたコンテキストが保護されて圧縮されていることを確認。
- **対象ファイル**: `src/agents/context_builder_agent.py`
- **変更内容**: `regeneration_focus` に応じた必須カテゴリの動的ピン留め。
- **確認コマンド**: `python -m py_compile src/agents/context_builder_agent.py`
- **完了条件**: 圧縮処理時にフォーカス情報が失われないこと。

### Step 65: エンリッチメントの再生成耐性確認
- **目的**: 再生成された本文に対しても、トリビアリライトと五感拡充が重複せずクリーンに適用されることを確認。
- **対象ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: 既にエンリッチメントされた形跡がある場合の二重置換防止フラグ処理。
- **確認コマンド**: `python -m py_compile src/agents/enrichment_agent.py`
- **完了条件**: 再生成テキストへの二重エンリッチメントが防止されること。

### Step 66: DBテーブル `audit_specialist_results` への Actionable Diff 永続化
- **目的**: データベースに保存される講評JSONに `actionable_diffs` を含め、後から履歴参照できるようにする。
- **対象ファイル**: `src/agents/specialists/adapter.py` の `save_specialist_results`
- **変更内容**: `diffs_json = json.dumps([d.__dict__ for d in res.actionable_diffs])` をフィードバックJSONに統合。
- **確認コマンド**: `python -m py_compile src/agents/specialists/adapter.py`
- **完了条件**: DB永続化ペイロードに差分情報が含まれること。

### Step 67: Admin API (`/admin/audit/*`) のレスポンス更新
- **目的**: 管理画面やStudio UIから Actionable Diff を一覧取得できるようにAPIレスポンスを整える。
- **対象ファイル**: `src/backend/api/admin_audit.py` (または相当エンドポイント)
- **変更内容**: スコア詳細エンドポイントに `actionable_diffs` を含めて返却。
- **確認コマンド**: `python -m py_compile src/backend/api/`
- **完了条件**: APIモデル定義に不整合がないこと。

### Step 68: 長編シナリオ（8000文字超）の E2E 結合テスト作成
- **目的**: 8000文字の本文を生成し、トリビアリライト → 五感拡充 → 8専門家窓枠監査 → 特化再生成ディレクティブ発行までの完全フローをテスト。
- **対象ファイル**: `tests/e2e/test_pillar1_pipeline_e2e.py` (新規作成)
- **変更内容**: モックLLMを用いた完全パイプラインE2Eシナリオ。
- **確認コマンド**: `pytest tests/e2e/test_pillar1_pipeline_e2e.py -v`
- **完了条件**: E2Eテストがエラーなく完走すること。

### Step 69: 品質指標アサーションの自動検証テスト
- **目的**: 文法破損ゼロ、末尾クリフハンガー検知、再生成ディレクティブ包含を自動アサート。
- **対象ファイル**: `tests/e2e/test_pillar1_pipeline_e2e.py`
- **変更内容**: 「。が」などの破損表現がないこと、末尾スコアが正しく反映されていることのアサーション。
- **確認コマンド**: `pytest tests/e2e/test_pillar1_pipeline_e2e.py -k test_quality_assertions -v`
- **完了条件**: すべてのアサーションがパスすること。

### Step 70: 低性能LLM / ルールベースフォールバック混在耐障害性テスト
- **目的**: LLMが一部でダウン、あるいは低品質な出力を返した場合でも、パイプラインが停止せず安全に完走することを検証。
- **対象ファイル**: `tests/e2e/test_pillar1_fault_tolerance.py` (新規作成)
- **変更内容**: 意図的に例外を投げるモックを用いた耐障害性テスト。
- **確認コマンド**: `pytest tests/e2e/test_pillar1_fault_tolerance.py -v`
- **完了条件**: 全フォールバックが正常稼働しクラッシュしないこと。

### Step 71: ドキュメントの作成と更新
- **目的**: 第1の柱の実装仕様と運用ガイドをドキュメント化する。
- **対象ファイル**: `docs/features/pillar1_expression_and_windowing.md` (新規作成), `CHANGELOG.md`
- **変更内容**: 窓枠評価アルゴリズム、文単位五感拡充、Actionable Diff仕様の記録。
- **確認コマンド**: `python -c "from pathlib import Path; assert Path('docs/features/pillar1_expression_and_windowing.md').exists(); print('OK')"`
- **完了条件**: ドキュメントが作成されリンクが有効であること。

### Step 72: 【Check Point 6 / 最終ゲート】全72ステップ総合テスト合格・プロダクションレディ検証
- **目的**: 本実装計画の全変更がAutoNovel既存テストスイート全体と調和し、オールグリーンであることを確認。
- **確認コマンド**: `pytest tests/unit/ tests/integration/ tests/e2e/ -v --tb=short`
- **完了条件**: **ALL TESTS PASSED & 0 FAILURES**（完全合格）
