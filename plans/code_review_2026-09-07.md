# AutoNovel v4.5.0 コードレビュー報告書

**実施日**: 2026-09-07
**対象**: `e:/hhh/autonovel/`（小説生成AIエンジン）
**レビュー範囲**: agents/specialists/*, services/llm/*, core/spi/llm/*, tests/unit/*

---

## 1. プロジェクト概要

AutoNovel は日本語小説生成AIエンジン。FastAPI + React + Huey + SQLAlchemy をベースとし、LLM統合により8つの specialist auditor で多角的な品質審査を行う構成。

主な構成要素：
- 8 specialist auditors（consistency / creativity / reader_hook / emotion_curve / style / factual / structure / multimodal）
- [`NovelSectionExtractor`](autonovel/src/agents/specialists/windowing.py:44) による長文ウィンドウ分割
- LLMアダプタ 6種（Gemini / OpenAI / Claude / Ollama / vLLM / Mock）

---

## 2. アーキテクチャ全体評価

### 良い点
- 関心の分離が明確：`agents/specialists/`（専門審査員）、`services/`（業務ロジック）、`core/spi/`（インターフェース）、`shared/`（横断基盤）が綺麗に分かれている
- [`SpecialistAuditor`](autonovel/src/agents/specialist_auditor_base.py:50) 抽象基底クラスによる8監査員の統一契約
- [`_safe_audit()`](autonovel/src/agents/specialist_auditor_base.py:89) による `LLMUnavailableError` → ルールベースフォールバックの二段防御
- [`_judge_with_llm()`](autonovel/src/agents/specialist_auditor_base.py:136) のマルチサンプル＋分散チェック（`LLM_MAX_SCORE_STDEV=15.0`）
- 文末スナップ（。！？\n）による意味的境界を保持したウィンドウ分割
- pytest 設定：[`pyproject.toml`](autonovel/pyproject.toml:59) で `asyncio_mode = "auto"`、`--cov-fail-under=35`

---

## 3. 主要な問題点とリスク

### P0（Critical・早急対応）

#### 3.1 二重 LLM 抽象化による不整合
- [`src/services/llm/base.py`](autonovel/src/services/llm/base.py:12) の `BaseLLMAdapter`（`generate_text` / `stream_text`）
- [`src/core/spi/llm/interface.py`](autonovel/src/core/spi/llm/interface.py:9) の `ILLMProvider`（`generate` / `agenerate`）

両者でメソッドシグネチャが全く異なる。[`specialist_auditor_base.py:175-184`](autonovel/src/agents/specialist_auditor_base.py:175) では `ainvoke` / `generate` / `invoke` / `callable` をリフレクションで使い分けており、契約が曖昧。

**改善案**：SPI 層を一つに統合するか、`BaseLLMAdapter` を `ILLMProvider` のインターフェースに適合させる Adapter を1つ定義する。

#### 3.2 `import re` が関数内に散在
- [`consistency_auditor.py:62`](autonovel/src/agents/specialists/consistency_auditor.py:62)
- [`factual_auditor.py:59`](autonovel/src/agents/specialists/factual_auditor.py:59)
- [`multimodal_auditor.py:61`](autonovel/src/agents/specialists/multimodal_auditor.py:61)
- [`specialist_auditor_base.py:75`](autonovel/src/agents/specialist_auditor_base.py:75)
- [`specialist_auditor_base.py:167-170`](autonovel/src/agents/specialist_auditor_base.py:167)

ホットパスで毎回 `import re` を実行するとパフォーマンスが劣化する。モジュールトップへ移動すべき。

#### 3.3 監査スコア算出のヒューリスティック依存
[`structure_auditor.py:125-138`](autonovel/src/agents/specialists/structure_auditor.py:125) でプロット文字列を `re.split(r"[→→、。,\n・]+", ...)` で分割し、最初4要素を「導入・展開・転換・結び」に強制マップ。プロット形式が固定されていない場合、誤った評価になる可能性が高い。

[`check_semantic_consistency()`](autonovel/src/agents/specialists/fallback_utils.py:136) も部分文字列マッチに依存し、偽陽性・偽陰性の懸念が大きい。

---

### P1（High・中期改善）

#### 3.4 `_safe_audit` の `safe_audit = _safe_audit` エイリアス
[`specialist_auditor_base.py:121`](autonovel/src/agents/specialist_auditor_base.py:121) のエイリアスは `_` プレフィックス命名規約を実質的に無効化している。意図がコメントで説明されておらず可読性を損なう。

#### 3.5 `StreamText` で `yield ""` が到達不能コード
[`base.py:38-39`](autonovel/src/services/llm/base.py:38) で `raise NotImplementedError` の直後に `yield ""` がある。静的解析ツールに警告される可能性が高い。

#### 3.6 環境変数の上書きが `__init__` 限定
[`specialist_auditor_base.py:75-81`](autonovel/src/agents/specialist_auditor_base.py:75) で `AUDIT_LLM_SAMPLES` を読むが、`settings` から読むべき。`pydantic-settings>=2.2` が既に依存関係にある。

#### 3.7 例外処理で `LLMUnavailableError` が二重に再送出
[`specialist_auditor_base.py:230-233`](autonovel/src/agents/specialist_auditor_base.py:230) でマルチサンプルモード（line 247-263）の `LLM_MAX_SCORE_STDEV` 超過時、`LLMUnavailableError` を再送出しているが、`CONFIDENCE_THRESHOLD` との整合性が不明確。

#### 3.8 型ヒントの不徹底
- [`specialist_auditor_base.py:189`](autonovel/src/agents/specialist_auditor_base.py:189): `text_resp` が `Any | str` のまま
- [`openai_adapter.py:88`](autonovel/src/services/llm/openai_adapter.py:88): `response` が `# type: ignore` 頻出

`mypy>=1.8` が依存関係にあるのに型安全性が低い。

---

### P2（Medium・継続改善）

#### 3.9 [`_split_by_emotional_shifts()`](autonovel/src/agents/specialists/emotion_curve_auditor.py:198) の密度差判定が粗い
`abs(density - current_density) > max_density * 0.5` という単純な閾値で、テキスト全体の感情語彙量に過敏。テキスト長に応じた正規化が必要。

#### 3.10 `analyze_pacing()` がセグメント長のみ評価
[`fallback_utils.py:265-299`](autonovel/src/agents/specialists/fallback_utils.py:265) はセグメント長のCVのみ。実際のプロット進行に応じた評価ではない。

#### 3.11 [POS判定の正規表現が誤判定](autonovel/src/agents/specialists/creativity_auditor.py:21)
`ADJ_PATTERN` / `ADV_PATTERN` は動詞語尾（ます、たい等）も誤カウント。Sudachi等の形態素解析器の導入を検討（`pyproject.toml` の `nlp` extra に `sudachipy` は既にある）。

#### 3.12 プロンプト文字列がPythonソースに埋め込み
各auditorの `*_SYSTEM_PROMPT` 定数は外部YAML/Jinja2に分離すべき。プロンプト改善のたびにPythonコード変更が必要になる。

#### 3.13 テストカバレッジ目標が35%
[`pyproject.toml:62`](autonovel/pyproject.toml:62) で `--cov-fail-under=35` は低すぎる。`services/`、`core/`、`shared/` 配下のテストカバレッジが不明。

---

### P3（Low・リファクタリング）

#### 3.14 `audit_service.py` のインポートパス不統一
[`audit_service.py:3`](autonovel/src/services/audit_service.py:3) で `config.erotic_thresholds` を参照、他モジュールは `src.config.*` で統一されていない。

#### 3.15 `LLMProviderFactory.get_client()` のロジック
[`llm_gateway.py:33-42`](autonovel/src/core/llm_gateway.py:33) で `provider.split("-")[0]` の単純分割と `is_openai_compatible()` の判定が重複している。

#### 3.16 `_snap_backward()` のエッジケース
[`windowing.py:79`](autonovel/src/agents/specialists/windowing.py:79) で `target_idx` 自体が文末を含む場合、その次の文末を返してしまうケースがある。

---

## 4. テスト品質

### 良い点
- [`test_windowed_auditors.py`](autonovel/tests/unit/test_windowed_auditors.py:73) で8000字超の長文統合テスト
- `MagicMock` による LLM 差し替えが全テストで徹底
- `pytest.mark.asyncio` で非同期テストを統一

### 改善点
- `_safe_audit()` の例外パス（`LLMUnavailableError` 発生時）に対するテストがない
- マルチサンプリングモード（`AUDIT_LLM_SAMPLES > 1`）のテストがない
- `_fallback()` の境界値テストがない（空draft、巨大draft、LLM異常時）

---

## 5. セキュリティ・パフォーマンス

### セキュリティ
- APIキー管理は環境変数・`settings` 経由で適切
- [`factory.py:33`](autonovel/src/services/llm/factory.py:33) の `APP_ENV == "testing"` 判定は環境変数のみ。`settings.ENV` を経由すべき
- `llm_raw_response` がデバッグ目的で feedback に含まれる設計はPII漏洩リスクがあり、本番モードでは無効化すべき

### パフォーマンス
- `_judge_with_llm()` マルチサンプルモードでLLM呼び出しが直列：`asyncio.gather()` 並列化可能
- [`style_auditor.py:159`](autonovel/src/agents/specialists/style_auditor.py:159) の `BM25Okapi([sample_tokens])` 毎回生成：style_dna が変わらないならキャッシュすべき
- [`fallback_utils.py:136`](autonovel/src/agents/specialists/fallback_utils.py:136) の `check_semantic_consistency()` は O(N×M) 正規表現スキャン：長いテキストで線形時間劣化

---

## 6. 改善提案の優先順位

| 優先度 | 項目 | 影響範囲 | 推奨対応 |
|--------|------|----------|----------|
| P0 | 二重 LLM 抽象化の統合 | 全LLM呼び出し | SPI Adapter 1本化 |
| P0 | `import` のモジュールトップ移動 | 8 auditors全体 | lint設定追加 |
| P1 | `_safe_audit` 命名統一 | specialist base | リネーム |
| P1 | 環境変数→settings統合 | テスト容易性 | 設定クラス統一 |
| P1 | 型ヒント厳密化 | 全モジュール | mypy strict化 |
| P2 | プロンプト外部化 | 全auditors | YAML/Jinja2化 |
| P2 | テストカバレッジ目標 70% へ | 全モジュール | テスト追加 |
| P2 | POS解析の精度向上 | creativity_auditor | Sudachi統合 |
| P3 | マルチサンプル並列化 | specialist base | asyncio並列化 |
| P3 | `analyze_pacing` の高度化 | structure_auditor | グラフベース評価 |

---

## 7. 総評

AutoNovel v4.5.0 は、**日本語小説生成というドメイン特化型の複雑なタスクに対し、8 specialist auditor の統一インターフェース、ウィンドウ分割による長文対応、ルールベースフォールバック**という優れた設計思想が貫かれている。

一方で、**LLM抽象化の二重化、import文の散在、テストカバレッジ目標の低さ**という技術的負債を抱えている。

当面は **P0（LLM抽象化統合とimport最適化）** に集中投資することで、保守性と拡張性が大きく向上すると考えられる。
