# P0 実装メリット・デメリット分析

## P0-1: 二重 LLM 抽象化の統合

### 現状の問題
[`services/llm/base.py`](autonovel/src/services/llm/base.py:12) の `BaseLLMAdapter`（`generate_text` / `stream_text`）と [`core/spi/llm/interface.py`](autonovel/src/core/spi/llm/interface.py:9) の `ILLMProvider`（`generate` / `agenerate`）がメソッドシグネチャ・命名・同期/非同期の扱いで全く異なる契約を持つ。

### メリット

| # | 内容 |
|---|------|
| 1 | 契約の明確化：リフレクション判定が消え、抽象メソッド経由の明示的な実装強制により LLMUnavailableError 発生条件が静的に検証可能 |
| 2 | 新LLMプロバイダ追加コストの低下：1インターフェース実装で済み、オンボーディングドキュメントも1系統 |
| 3 | モックの標準化：MockLLMProvider と MockLLMAdapter の二重実装解消、テスト差し替え単純化 |
| 4 | 型ヒント厳密化：Any / type: ignore 削減、mypy strict 警告削減 |
| 5 | デバッグ容易性向上：リフレクション分岐はスタックトレースが読みづらく、統一なら通常のトレースで原因特定が速い |
| 6 | テスト戦略統一：SPI層1本化で pytest fixture 注入経路が1つに定まる |

### デメリット

| # | 内容 | 影響度 |
|---|------|--------|
| 1 | 後方互換性破壊リスク：既存呼び出しが両方の型に依存する場合、DeprecationWarning 期間が必要 | 中 |
| 2 | マージ作業コスト：6プロバイダ（Gemini/OpenAI/Claude/Ollama/vLLM/Mock）すべて新インターフェース適合 | 中 |
| 3 | 呼び出しパターン再設計：stream_text を持つ側と generate のみの側で機能差、寄せると機能縮小or拡張 | 低〜中 |
| 4 | テスト再構築：リフレクション判定分岐パスのテストケース書き換え | 低 |
| 5 | ドキュメント更新工数：SPI と services/llm の役割分担明文化、docs/ 全面改訂 | 低 |
| 6 | 暗黙知の喪失：現状の宽容性（任意の型でも動く）を失いレガシー呼び出しが動かなくなる可能性 | 中 |

### 推奨アプローチ
段階的移行：
1. 新インターフェース定義：BaseLLMAdapter を ILLMProvider のスーパーセット（generate_text / agenerate / stream_text）に拡張
2. 旧 ILLMProvider を非推奨化：DeprecationWarning 付きで1リリース警告期間
3. 呼び出し側順次移行：SpecialistAuditor → audit_service → factory の順
4. 旧 ILLMProvider 削除：3リリース後

---

## P0-2: `import re` をモジュールトップへ移動

### 現状の問題
5箇所の関数内 import（[`specialist_auditor_base.py:75`](autonovel/src/agents/specialist_auditor_base.py:75)、[`specialist_auditor_base.py:167-170`](autonovel/src/agents/specialist_auditor_base.py:167)、[`consistency_auditor.py:62`](autonovel/src/agents/specialists/consistency_auditor.py:62)、[`factual_auditor.py:59`](autonovel/src/agents/specialists/factual_auditor.py:59)、[`multimodal_auditor.py:61`](autonovel/src/agents/specialists/multimodal_auditor.py:61)）。

### メリット

| # | 内容 |
|---|------|
| 1 | 実行速度改善：ホットパス（_judge_with_llm は監査ごと呼ばれる）で名前検索コスト回避 |
| 2 | 依存関係の可視化：モジュールトップの import を見れば外部依存が一覧可能 |
| 3 | 循環インポート早期発見：関数内 import は循環参照を隠蔽、トップなら起動時に顕在化 |
| 4 | モック可能性向上：unittest.mock.patch の対象が明確 |
| 5 | ruff/flake8 ルール準拠：E402 等のリンター警告解消 |
| 6 | 静的解析精度向上：mypy/pyright が完全に通る |

### デメリット

| # | 内容 | 影響度 |
|---|------|--------|
| 1 | 起動時間への影響：import re は標準ライブラリで極軽量（~0.1ms） | 極小 |
| 2 | 条件付き import の喪失：try/except ImportError で optional 依存を扱う場合、トップで明示 try ブロックが必要 | 低 |
| 3 | リファクタリング工数：5箇所の単純修正 | 低 |
| 4 | 一部条件で関数内 import が正当な場合：import コストが大きい重いライブラリの遅延ロード（re/json には該当しない） | なし |

### 推奨アプローチ
即時対応推奨。リスクが極めて低く、メリットが明確。ruff の --fix で自動修正可能。

---

## P0-3: 監査スコア算出のヒューリスティック依存脱却

### 現状の問題
[`structure_auditor.py:125-138`](autonovel/src/agents/specialists/structure_auditor.py:125) で `re.split(r"[→→、。,\n・]+", ...)` 単純分割、[`check_semantic_consistency()`](autonovel/src/agents/specialists/fallback_utils.py:136) で部分文字列マッチ、[`analyze_pacing()`](autonovel/src/agents/specialists/fallback_utils.py:265) はセグメント長CVのみ。

### メリット

| # | 内容 |
|---|------|
| 1 | スコア精度の大幅向上：プロット解析がプロットツリー構造を理解した上で各フェーズ評価、現在50点近辺で分散するフォールバックスコアが実用レベルに |
| 2 | LLM不使用時の品質底上げ：LLM障害時のデグレが「使える品質」に近づきパイプライン全体信頼性向上 |
| 3 | 誤検出削減：「死亡キャラクター検出」のような部分文字列マッチは "生き生きとした表情" 等で誤検出、構文解析で回避 |
| 4 | マルチジャンル対応：和風/中華/ファンタジー/SF 等ジャンルごとに異なるプロット形式を吸収 |
| 5 | デバッグ容易性：ヒューリスティック正規表現は理由説明困難、構造化プロット解析なら追跡可能 |

### デメリット

| # | 内容 | 影響度 |
|---|------|--------|
| 1 | 実装コストが他に比べ高い：構造化プロット解析、ワールドビルディングDSL策定、構文解析器実装が必要。P0-1/2 と比較して桁違いの工数 | 高 |
| 2 | データモデル変更の波及：World Bible / Plot Tree スキーマ拡張、DB マイグレーション（alembic）と API 破壊 | 中〜高 |
| 3 | 精度検証の難しさ：LLM出力と人間判断スコアのペアを大量に用意、ゴールデンセット構築に時間 | 中 |
| 4 | 過剰設計リスク：LLM-first 設計では LLM が真の正解を出す前提のためフォールバック過剰投資しても本番未使用の可能性 | 中 |
| 5 | テスト工数増大：構造化プロット解析の境界値テスト（malformed plot / empty plot / multi-format plot） | 中 |
| 6 | 既存フォールバックとの二重実装期間：新旧方式共存で保守負荷一時増大 | 低 |

### 推奨アプローチ
段階的導入：
1. Phase A：プロット解析スキーマ（Pydantic model）定義
2. Phase B：パーサー（parsers/plot_parser.py）に変換層実装
3. Phase C：新しい analyze_plot_structure() を _fallback() から呼び出し、旧は --legacy-fallback フラグで切替
4. Phase D：A/B テストで新方式スコアと LLM スコアの相関検証
5. Phase E：旧方式削除

---

## P0 全体の比較まとめ

| 項目 | 工数 | リスク | 効果 | 推奨タイミング |
|------|------|--------|------|----------------|
| P0-1 LLM抽象化統合 | 中 | 中（後方互換性） | 高（契約明確化） | スプリント1〜2 |
| P0-2 import最適化 | 極小 | 極小 | 中（速度・lint） | 即時（1 PR） |
| P0-3 ヒューリスティック脱却 | 高 | 高 | 高（品質） | スプリント3〜（設計段階から） |

## 総合的な投資判断

P0-2 のみ即時着手、P0-1 は計画的に段階移行、P0-3 は別プロジェクトとして設計検討 が現実的。

P0-3 は「フォールバックパスの精度向上」と「LLM障害時のサービス継続性」のトレードオフがあり、ビジネス要件（LLM可用性のSLO）によって優先度が変わる。LLM障害が許容できないシステムなら最優先、そうでなければLLMコスト削減（プロンプトキャッシュ等）の方が高いROIの可能性。
