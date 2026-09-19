# PLAN_B3: プロンプト注入アプローチ（最小・最速・LLM任せ）

**目標**: 既存コード・モデル・エージェントを**一切変更せず**、プロンプトテンプレートのみで「3話ごとの裏切り指示」を LLM に与える。実装コスト最小・即日検証可能。

**トレードオフ**: 
- ✅ 実装1ファイル・数行
- ✅ 既存テスト全通過（変更なし）
- ⚠️ LLMが指示を無視・誤解するリスクあり
- ⚠️ 決定論的でない（同一プロンプトでも出力揺れ）
- ⚠️ 検証・制御が後からできない

**適用場面**: PoC・スパイク・編集会議用デモ・LLM能力検証

---

## Step 1: プロンプトテンプレート特定・現状確認

**作業内容**
- `src/prompts/` 配下（または `PromptManager` 内部）で `arc_generation.j2` / `beat_sheet_generation.j2` を特定
- 現在のプロンプト構造・変数・制御フローを読解
- どこに「話数ループ」「アークごと指示」が入っているか確認

**受け入れ基準**: テンプレートファイルパスと、注入すべきブロック位置を特定できている

**テスト作成**: なし（調査ステップ）

---

## Step 2: 「裏切りプロトコル」プロンプト断片作成

**作業内容**
- `prompts/fragments/subversion_protocol.j2` 新規作成
- 内容:
```jinja2
{% if subversion_enabled and (ep_num % subversion_interval == 0) %}
## ⚠️ 裏切りプロトコル（第{{ ep_num }}話：必須適用）
以下の3パターンから**必ず1つ**選び、この話の核心的展開として組み込んでください。
選択基準: 作品ID「{{ work_id }}」と話数「{{ ep_num }}」のハッシュ値で決定論的に選ぶこと。

### パターンA：予期せぬ代償
- チート能力・覚醒・パワーアップを得る**代わりに**、人間性の一部（感情・記憶・倫理・共感）を永久に失う。
- 代償の具体例: 「喜びを感じられなくなる」「仲間の顔を認識できなくなる」「嘘がつけなくなる」
- この代償は**後で回収不能**。最終話まで尾を引く悲劇の伏線となる。

### パターンB：悪役の想定外の矜持
- ざまぁされる側の小悪党・雑魚敵が、卑劣な手段で主人公を追い詰めた**直後に**、
- 「わが一族/部下/大切な者を守るため」自ら囮となり、命を投げ出す覚悟を見せる。
- 読者の「ざまぁ待ち」感情を裏切り、敵キャラへの共感・再評価を強制する。
- 残された遺言・アイテム・血統が、後の主人公の真の力を引き出す鍵になる。

### パターンC：第三勢力の乱入
- 復讐完遂・ざまぁ達成の**クライマックス瞬間**に、
- 主人公・敵対者の双方を無力化する「より凶悪な共通の脅威」（古代兵器・外宇宙存在・概念的崩壊・神の代行者）が出現。
- 復讐は中断・無期限延期。主人公と元敵が「生存/世界救済」という共通目的で強制連携させられる。
- この第三勢力の正体＝主人公の力の源泉（因果律ループ）という伏線を埋め込む。

**適用ルール**:
- この話の `thematic_milestone` / `mission` / `summary` に必ず「【裏切り-A/B/C】」プレフィクスを付ける。
- `tension_target` は基準値+0.3（上限1.0）に引き上げる。
- 代償・矜持・第三勢力の**具体的描写**を `detailed_blueprint` / `visual_scene_focus` に最低3文以上書く。
{% endif %}
```

**受け入れ基準**: ファイル作成完了。Jinja2構文エラーなし。

---

## Step 3: `arc_generation.j2` への注入

**作業内容**
- アーク生成プロンプト内の「各話生成ループ」または「アークサマリー生成部」に `{% include 'fragments/subversion_protocol.j2' %}` を挿入
- 必要変数（`subversion_enabled`, `subversion_interval`, `work_id`, `ep_num`）がテンプレートコンテキストに渡されるよう `PromptManager.build_arc_generation_prompt()` を確認・必要なら拡張

**受け入れ基準**: `PromptManager.build_arc_generation_prompt(...)` 実行時にプロンプト内に裏切り指示が含まれる

**テスト作成**: `tests/test_prompt_injection.py::test_arc_prompt_contains_subversion`

---

## Step 4: `beat_sheet_generation.j2` への注入

**作業内容**
- 商業ビートシート生成プロンプト（CSV出力指示部）にも同一フラグメントを `include`
- `EpisodeBeat` の各フィールド（`mission`, `visual_scene_focus`, `tension_target`）への反映指示を追記
- CSVパーサー側（`generate_commercial_beat_sheet()`）は変更不要（LLMが正しいCSVを出せばよい）

**受け入れ基準**: ビートシート生成プロンプトにも裏切り指示が含まれる

**テスト作成**: `tests/test_prompt_injection.py::test_beat_prompt_contains_subversion`

---

## Step 5: 設定変数のデフォルト値・渡し方確立

**作業内容**
- `PlanningAgent.generate_arcs()` / `generate_commercial_beat_sheet()` の呼び出し元（`execute()` / `run()`）で `ctx.artifacts` に以下をセット:
```python
ctx.artifacts.setdefault("subversion", {
    "enabled": True,
    "interval": 3,
    "work_id": ctx.book_id,  # または title hash
})
```
- `PromptManager` が `artifacts` 全体をテンプレートコンテキストに渡すなら追加作業不要。渡さないなら `build_*_prompt` 引数に追加

**受け入れ基準**: テンプレート内で `subversion_enabled` / `subversion_interval` / `work_id` が参照可能

**テスト作成**: `tests/test_prompt_injection.py::test_context_variables_passed`

---

## Step 6: 決定論的パターン選択指示の強化

**作業内容**
- プロンプト断片に「選択アルゴリズム」を明記（低性能LLMでも従いやすい形式）:
```
選択アルゴリズム（思考過程で実行し、結果のみ出力）:
1. seed = "{{ work_id }}_{{ ep_num }}"
2. hash_val = MD5(seed) の最初の2桁を16進数→10進数変換 (0-255)
3. ratio = hash_val / 255
4. if ratio < 0.4: パターンA
   elif ratio < 0.7: パターンB
   else: パターンC
```
- 「思考過程は出力しない。最終JSON/CSVに結果のみ反映せよ」と明記

**受け入れ基準**: 同一 `work_id`・同一 `ep_num` で複数回生成しても同一パターンが選ばれやすくなる

**テスト作成**: `tests/test_prompt_injection.py::test_deterministic_prompt_instruction`

---

## Step 7: 実地検証・サンプル生成

**作業内容**
- 実際に `PlanningAgent.execute()` を実行（モックLLMまたは実LLM）
- 生成された `ArcList` / `EpisodeBeat` で:
  - 3,6,9...話に「【裏切り-」プレフィクスがあるか
  - `tension_target` がスパイクしているか
  - 代償・矜持・第三勢力の具体描写が3文以上あるか
- 目視確認チェックリスト作成

**受け入れ基準**: 目視で「裏切りらしき展開」が3話ごとに入っている

**テスト作成**: `tests/test_prompt_injection.py::test_generated_output_inspection`（目視補助用・アサーションは緩め）

---

## Step 8: 失敗パターン収集・プロンプト改善ループ

**作業内容**
- 5〜10回生成し、以下の失敗パターンを記録:
  - 指示無視（裏切りなし）
  - パターン表記なし（プレフィクス欠落）
  - 代償描写が薄い（1文のみ）
  - パターン混在（AとB両方書く）
  - CSVフォーマット崩壊（ビートシート）
- 失敗率が高い指示をプロンプト断片で言い換え・強調・例示追加

**受け入れ基準**: 失敗率が許容範囲（例: <20%）まで低下

**テスト作成**: なし（手動・反復）

---

## Step 9: 無効化スイッチ・切り替え確認

**作業内容**
- `subversion.enabled = False` の場合、プロンプト断片が**完全に出力されない**ことを確認（`{% if %}` ブロックで囲まれていれば自動）
- 既存動作（裏切りなし通常生成）に戻ることを確認

**受け入れ基準**: `enabled=False` で従来通りの平坦な生成結果になる

**テスト作成**: `tests/test_prompt_injection.py::test_disabled_mode`

---

## Step 10: ドキュメント・運用ガイド作成

**作業内容**
- `docs/guides/subversion_prompt_injection.md` 作成:
  - 仕組み図（プロンプト→LLM→出力）
  - 設定項目・デフォルト値
  - プロンプト断片のカスタマイズ方法（文言変更・パターン追加）
  - 失敗時のトラブルシューティング
  - **限界と注意点**（決定論的でない、検証できない、LLM依存）

**受け入れ基準**: ドキュメント存在。運用チームが読んでON/OFF切り替え可能。

---

## Step 11: 既存テストスイート全実行・リグレッション確認

**作業内容**
- `pytest tests/ -x --tb=short` 実行
- プロンプト変更のみのため、**全テストが無修正で通過すること**を確認
- もしテストが落ちたら、プロンプト変更が出力形式（JSON/CSV構造）を壊していないか確認・修正

**受け入れ基準**: 全テスト通過（リグレッション・ゼロ）

---

## Step 12: 本番投入判断基準・移行計画メモ

**作業内容**
- 本番投入可否の判断基準をドキュメント化:
  - ✅ 成功率 > 80%（手動評価）
  - ✅ 既存テスト全通過
  - ✅ 無効化スイッチ動作確認済み
  - ❌ 失敗時のフォールバック手順（手動修正・再生成）
- 将来的に B1/B2 へ移行する際のインターフェース互換性メモ（`artifacts["subversion"]` 構造を共通化しておく等）

**受け入れ基準**: 判断基準ドキュメント存在。移行パスが明記されている。

---

## 依存関係グラフ

```
Step 1 → Step 2
Step 2 → Step 3,4
Step 3,4 → Step 5
Step 5 → Step 6
Step 6 → Step 7
Step 7 → Step 8 (反復)
Step 5 → Step 9
Step 9 → Step 10
Step 10 → Step 11
Step 11 → Step 12
```

## 並行実行可能グループ
- Group A: Step 1, 2 (順序)
- Group B: Step 3, 4 (Step 2 後、独立)
- Group C: Step 5 (Step 3,4 後)
- Group D: Step 6, 9 (Step 5 後、独立)
- Group E: Step 7, 8 (Step 6 後、反復)
- Group F: Step 10, 11, 12 (順次)

---

## ⚠️ 重要な制約事項（低性能LLM実装者へ）

1. **テンプレート変更のみ**。Pythonコード（`planning.py` / `models/plot.py` / `agents/`）には**一切手を入れない**。
2. `PromptManager` が `artifacts` をそのままテンプレート変数として渡す実装なら、Step 5 は「`ctx.artifacts` に dict を足すだけ」で完了。
3. もし `PromptManager` が明示的な引数しか渡さない実装なら、`build_arc_generation_prompt(**kwargs)` に `subversion_enabled` 等を追加する**最小限の Python 変更**が発生する（それでも 1-2 行）。
4. **出力形式（JSON/CSV）を壊さないよう**、プロンプト断片の最後には必ず「出力形式は従来通り厳守せよ」と明記すること。
5. テストは「プロンプトに文字列が含まれるか」の単純アサーションで十分。生成品質テストは手動・目視でよい。