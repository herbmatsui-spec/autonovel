# バランス調整 実LLM検証レポート

**作成日**: 2026-07-09
**対象**: cR15 覇権小説自動生成エンジン v3.0
**検証手法**: 実際の Gemini API（`gemini-2.5-flash`）を呼び出し、3改善案のパイプラインで実作品を生成・検証
**関連計画**: `plans/quality_entertainment_balance_72steps.md`

---

## 1. 検証の目的と方法

バランス調整（3改善案・全72ステップ）の後、**「実際に作品を作って」** 各機構が想定通りに機能するかを確認する。
テスト（モック）だけでなく、実LLMを通した生成・検証を行い、調整後の挙動を客観的に記録する。

### 検証スクリプト
`balance_verify.py` — `GeminiApiClient` の壊れた非同期メソッド（`generate_content_async` は現行SDKに未実装）を迂回するため、同期 GenAI クライアントをスレッド越しに呼び出す薄いアダプタ `RealLLM` を実装し、各エージェントに接続。

### 検証フロー
1. **フェーズA 感情設計先行**: `EmotionalHookSpec(catharsis)` を構築 → `select_curve_by_hook` で `zamaa_heavy` 曲線を選択 → プロンプトに注入。
2. **実作品生成**: 上記フックを軸に、Gemini で約500文字の小説冒頭を生成。
3. **フェーズB 尖り保全**: `PromptManager.build_sharp_edge_proposal_prompt` で3つの尖りを提案 → `DeAIAuditor.audit` で尖り保全をチェック。
4. **フェーズC 早期面白さ検証**: `EarlyEntertainmentChecker.check` で `interest_score` を取得 → ゲート（>=60）判定。

---

## 2. 実行結果

### フェーズA：感情設計先行 ✅
| 項目 | 値 |
|------|----|
| 感情起点 | `catharsis`（長い苦悩の末に訪れる解放と浄化） |
| 目標Tension | 85/100 |
| 選択された曲線 | `zamaa_heavy` |
| プロンプト注入 | `本話の刺さり: 長い苦悩の末に訪れる解放と浄化（目標tensionピーク: 85/100、品質はこの感情に従属させること）` |

→ 改善案Aの「感情起点 → 曲線選択 → プロンプト注入」が正しく連動している。

### 実作品生成（実LLM呼び出し）
サンプル: `generated_sample_novel.md`
追放された主人公が圧倒的な力で仇敵（国王ゼノン）を消滅させる、いきなり復讐クライマックスから始まる冒頭。
文面から `zamaa_heavy`（急激な絶望→カタルシス爆発→完全な平穏）の構造が明確に読み取れる。

### フェーズB：尖り保全 ⚠️（機構は動くが実運用で課題）
提案された尖り（3件すべて正常に取得）:
| edge_type | 内容 |
|-----------|------|
| `protagonist_flaw` | 主人公が人間性を失い、復讐の鬼と化した側面 |
| `abnormal_dialogue` | 感情を伴わない、世界の法則を語るような冷徹なセリフ |
| `ending_pullback` | 復讐の達成が必ずしも救済ではない、不可逆な変化をもたらす結末 |

`DeAIAuditor.audit` の結果:
```
尖り保持時: passed=False / msg='以下の角が削られました: protagonist_flaw, abnormal_dialogue, ending_pullback'
尖り削除時: passed=False / msg='以下の角が削られました: protagonist_flaw, abnormal_dialogue, ending_pullback'
```

→ **【重要な発見】** 尖りを「保持した場合」でも `passed=False` になる。原因は `src/backend/sharp_edge_preserver.py:36` で、`check_edges_preserved` が `edge.description[:20]`（先頭20文字）をキーフレーズとして本文に含まれるかを判定しているため。実LLMが生成する `description` は「〜という記述から示唆される…」といった**説明文**であり、本文の字面を含まない。そのため、たとえ尖りが本文に残っていても常に「削除された」と誤検出（false positive）される。

- 単体テスト（`test_deai_auditor_edges.py` 等）は短いリテラル説明（例: 「余韻のある終わり方」）を使っているため通過するが、実運用のLLM出力では常に没戻し（rejected_edge_loss）になる可能性がある。
- **推奨修正**: 尖り提案プロンプトで `description` に「本文からそのまま抜粋した短いキーフレーズ（20文字以内）」を別フィールドとして要求する、あるいは意味的類似度（埋め込み）で判定するよう拡張する。

### フェーズC：早期面白さ検証 ✅
| 項目 | 値 |
|------|----|
| `interest_score` | **92/100** |
| `physiological_reaction` | カタルシス |
| `would_continue_reading` | True |
| `feedback` | 「冒頭からいきなり復讐のクライマックス…生理的な爽快感とカタルシスを覚えます…続きを読まずにはいられません」 |
| 面白さゲート(>=60) | **合格 → 本文執筆へ進行** |

→ 改善案Cの「品質整備前の面白さ検証」が実際に高スコアを返し、ゲートを通過した。

---

## 3. テストスイート結果（前回からの再掲・最新）

バランス関連21ファイル: **104/105 通過 (99.0%)**
- 失敗1件: `tests/test_zamaa_generation.py::test_zamaa_plot_generation` — `@pytest.mark.asyncio` デコレータ不足（バランス実装とは無関係のテストフレームワーク問題）。

---

## 4. 総合判定

| 改善案 | 実LLM検証結果 | 判定 |
|--------|--------------|------|
| A 感情設計先行 | hook=catharsis → zamaa_heavy に正しくマッピング、プロンプト注入を確認 | ✅ 想定通り |
| B 尖り保全 | 3件の尖り提案は成功。監査は**常に損失と誤検出**する課題を発見 | ⚠️ 機構は動くが実運用で要修正 |
| C 早期面白さ検証 | interest_score=92、カタルシスの生理反応、ゲート合格 | ✅ 想定通り |

### 結論
バランス調整の**設計意図（A・C）は実作品生成でも正しく機能している**。
- 感情起点からtension曲線への自動選択とプロンプト注入が機能し、生成された冒頭は `zamaa_heavy` らしい強いカタルシス構造を持つ。
- 早期面白さ検証が実際に高い興味スコア（92）を返し、面白さ先行のゲートが正常に通過する。

一方、**尖り保全（B）には実運用上の弱点**がある。`check_edges_preserved` が尖りの `description` 先頭20文字を字面一致で判定するため、実LLMが生成する説明的な長文 description では本文に一致せず、尖りを保持していても「削除された」と誤報告する。これは単体テストの「短いリテラル説明」では顕在化しない、実運用特有の false positive である。次フェーズでは尖り提案プロンプトでキーフレーズ抜粋を別フィールド化するか、意味的類似度判定へ拡張することを推奨する。

---

## 5. 実行時に発見・修正した環境課題（検証のためのминимал対応）

| 課題 | 内容 | 対応 |
|------|------|------|
| コンテナ配線エラー | `AppContainer` が `streamlit_app.pages_config` を配線し、`render_import_tab` 未定義で失敗 | 検証用に `src` のみを配線する `DemoAppContainer` で回避（本修正は未実施） |
| 未インストール依存 | `src/backend/checkpoint_saver.py` が `langgraph.checkpoint.sqlite` を要求 | フルDI経由の起動を断念し、直接 GenAI クライアントを利用 |
| 非同期メソッド不在 | `GeminiApiClient.generate_content_async` は現行 google-genai SDK に未実装 | 同期 `generate_content` をスレッド越しに呼び出す薄いアダプタで回避 |
| モデル枠 | `gemini-2.0-flash` は無料枠 limit=0、`gemini-1.5-flash` は未登録 | 利用可能な `gemini-2.5-flash` を使用 |
| 一時的503 | 高負荷による UNAVAILABLE | アダプタに指数バックオフ再試行（最大5回）を追加 |

> 上記は cR15 本体のバランス実装とは無関係な環境・配線の不備。本番の Streamlit 起動経路では別途 `render_import_tab` 未定義・`langgraph` 依存の解消が必要。

---

## 6. 成果物

- `balance_verify.py` — 実LLM検証スクリプト（再実行可能）
- `balance_verify_result.json` — 検証結果の構造化データ
- `generated_sample_novel.md` — 生成された実作品サンプル
- 本レポート
