# Phase 3: コア軽量化とEasy Mode研ぎ澄まし（Pragmatic Streamlining & UX） - 詳細実装計画書

**作成日**: 2026-09-24  
**ベースライン**: `plans/PHASE_ROADMAP_MASTER.md` Phase 3 セクション + Phase 2 完了済み（身軽化・構造一本化）  
**ゴール**: 1話あたり数十円以内・1分以内での生成完走と、最も価値の高いユーザー体験（Easy Mode）の実現  
**前提**: Phase 2 が完了し、重複コードが削除され、単一アーキテクチャが確立されていること

---

## 全24ステップ 概要

| Step | カテゴリ | 作業内容 | 成果物 | テスト/検証 |
|------|----------|----------|--------|-------------|
| 1 | ブランチ | 作業ブランチ `phase3-easymode` 作成・切替（Phase 2 完了ベースラインから） | ブランチ | `git status` |
| 2 | ブランチ | Phase 2 完了ベースラインから開始 (`git checkout phase2-done`) | ベースライン確認 | `git log --oneline -1` |
| 3 | オーディター集約設計 | 静的ルールチェックコンポーネントと統合LLMオーディターのインターフェース設計 | `docs/OPTIMIZED_AUDITOR_DESIGN.md` | レビュー承認 |
| 4 | 静的ルールオーディター実装 | 文字数・禁則など形式チェックを高速静的ルールで実装（既存ルールの統合・最適化） | `src/audit/static_rules.py` | ユニットテスト PASS |
| 5 | 統合LLMオーディター実装 | 8専門オーディターの定性監査を1回の一括LLMコールに再編（プロンプトエンジニアリング） | `src/audit/unified_llm_auditor.py` | ユニットテスト PASS |
| 6 | オーディターパイプライン統合 | 静的ルール → 統合LLMオーディター → （必要なら局所パッチ）のパイプライン構築 | `src/audit/pipeline.py` | 統合テスト PASS |
| 7 | PDCAサイクル修正 | 全文再生成ループ禁止ロジックの実装（設定可能な最大再生成回数=0）および局所パッチ機構（最大1回）の実装 | `src/generation/pdca_controller.py` | ユニットテスト PASS |
| 8 | 局所パッチ（Single-shot Polish）実装 | 指摘された特定シーンのみの再生成ロジック（範囲指定・プロンプトローカライズ） | `src/generation/local_polish.py` | ユニットテスト PASS |
| 9 | Easy Mode フローデザイン | ブラウザからのシームレスなフロー（入力→生成→レビュー→納品）のワイヤーフレーム・仕様書 | `docs/EASY_MODE_FLOW.md` | ステークホルダーレビュー |
| 10 | Easy Mode フロントエンド実装 | シンプルなウェブインターフェース（HTML/CSS/JS または既存フレームワークコンポーネント） | `web/easy_mode/` ディレクトリ | 手動動作確認・ブラウザテスト |
| 11 | Easy Mode バックエンドAPI | フロントエンドと連携する生成・納品エンドポイント（`/generate`, `/download` 等） | `src/api/easy_mode.py` | インテグレーションテスト PASS |
| 12 | Easy Mode エラーハンドリング | ユーザーに優しいエラーメッセージ・再試行案内・サポート連絡導線の実装 | 同上 | テスト PASS |
| 13 | ベンチマークスクリプト作成 | トークン消費・生成速度を測定するスクリプト（標準プロンプト・バッチサイズ） | `scripts/benchmark_generation.py` | スクリプト単体テスト PASS |
| 14 | ベンチマークベースライン測定 | 現在の実装（最適化前）でのベンチマーク測定・記録 | `artifacts/benchmark_baseline.json` | 測定完了・妥当な値 |
| 15 | ベンチマーク最適化後測定 | 最適化実装後のベンチマーク測定・記録・改善率計算 | `artifacts/benchmark_after.json` | 目標達成確認（コスト1/8・時間1/8 以上の改善） |
| 16 | プロンプトテンプレート標準化 | `prompts/` ディレクトリ構造設計・ベーステンプレート作成・バージョン管理方針 | `docs/PROMPT_VERSIONING.md` + `prompts/` ディレクトリ | レビュー承認・テンプレート構文 valid |
| 17 | プロンプトローダー実装 | バージョン指定・フォールバック・キャッシュを考慮したプロンプト取得ロジック | `src/prompts/loader.py` | ユニットテスト PASS |
| 18 | フォールバック機構実装 | LLM API エラー/タイムアウト時の静的ルールベース代替ストーリージェネレーター | `src/generation/fallback_generator.py` | ユニットテスト PASS・フォールバック発生シナリオテスト |
| 19 | キャッシュレイヤー導入 | 同一プロンプト・パラメータの結果キャッシュ（メモリ/Redis またはファイルベース） | `src/generation/cache.py` | キャッシュヒット率測定テスト PASS |
| 20 | セマンティックキャッシュ検討（オプション） | 類似意味プロンプトのベクトル検索ベースキャッシュのプロトタイプ（Phase 4 以降に持ち越すか判断） | `docs/SEMANTIC_CACHE_FEASIBILITY.md` | 調査完了・推奨事項 |
| 21 | リグレッション防止テスト | オーディター集約のリグレッションテスト（静的ルール＋LLM が元の8専門オーディターと同等品質を保つか） | `tests/audit/test_unified_auditor_equivalence.py` | `pytest` PASS |
| 22 | リグレッション防止テスト | PDCAスリム化のリグレッションテスト（全文再生成ループ禁止・局所パッチ最大1回 の振る舞い保証） | `tests/generation/test_pdca_limitation.py` | `pytest` PASS |
| 23 | リグレッション防止テスト | Easy Mode フローのエンドツーエンドテスト（入力からZIP/EPUB出力まで） | `tests/e2e/test_easy_mode_flow.py` | `pytest` PASS |
| 24 | 完了確認 | 全テスト GREEN 確認・ベンチマーク目標達成確認・PR 作成 | PR #xxx | 全テスト PASS・ベンチマーク改善率達成・マルチブラウザ動作確認 |

---

## ステップ詳細

### Step 1-2: ブランチ作成・ベースライン確認
```bash
git checkout -b phase3-easymode phase2-done
git push -u origin phase3-easymode
```
**Done**: `git branch --show-current` → `phase3-easymode`

### Step 3: オーディター集約設計
**ファイル**: `docs/OPTIMIZED_AUDITOR_DESIGN.md`
```markdown
# 最適化オーディター設計

## 目的
8専門オーディターによる重複LLMコールを排除し、コストと遅延を1/8に削減

## アーキテクチャ
```
入力テキスト
    ↓
[静的ルールオーディター]  ← 文字数・禁則・フォーマット等の高速チェック
    ↓
[統合LLMオーディター]    ← 1回のLLMコールで以下を評価：
                           - プロットの一貫性
                           - キャラクターの魅力
                           - 文体の適切さ
                           - 感情の起伏
                           - オリジナリティ
                           - ジャンル適合性
                           - 読みやすさ
                           - 総合エンターテインメント性
    ↓
[必要なら局所パッチ]      ← PDCAコントローラーが指示（最大1回）
    ↓
最終出力
```

## インターフェース契約
- `StaticRuleAuditor.audit(text) -> List[Issue]`
- `UnifiedLLMAuditor.audit(text, context=None) -> List[Issue]`
- `AuditPipeline.run(text) -> List[Issue]`（静的 → LLM → 必要なら局所パッチ）
```

### Step 4: 静的ルールオーディター実装
**ファイル**: `src/audit/static_rules.py`
- 既存の形式チェックルール（文字数、章タイトルフォーマット、禁則語句等）を統合
- 高速実装のために正規表現またはシンプルな文字列操作を使用
- プラグイン方式でルールを追加可能にするかどうかは検討
**テスト例**: `tests/audit/test_static_rules.py`
```python
def test_too_long_chapter_detected():
    text = "あ" * 5001  # 仮の上限5000字
    issues = StaticRuleAuditor().audit(text)
    assert any(issue.type == "length_exceeded" for issue in issues)
```

### Step 5: 統合LLMオーディター実装
**ファイル**: `src/audit/unified_llm_auditor.py`
- プロンプトエンジニアリングにより、1回のLLMコールで複数観点を評価
- 出力フォーマットを統一（例: JSON リスト）
- エラーハンドリング・フォールバック（Step 18 参照）を考慮
**テスト例**: `tests/audit/test_unified_llm_auditor.py`
```python
@patch("src.audit.unified_llm_auditor.call_llm_api")
def test_audit_returns_issues(mock_call):
    mock_call.return_value = '[{"type": "plot_inconsistency", "message": "..."}]'
    auditor = UnifiedLLMAuditor()
    issues = auditor.audit("Sample text")
    assert len(issues) == 1
    assert issues[0].type == "plot_inconsistency"
```

### Step 6: オーディターパイプライン統合
**ファイル**: `src/audit/pipeline.py`
- 静的ルールオーディターを最初に実行
- 重大な問題がない場合のみLLMオーディターへ（最適化の余地）
- LLMオーディターの結果に基づいて局所パッチが必要か判定
- PDCAコントローラーと連携
**テスト**: 静的ルールのみで済むケース・LLMが必要なケース・両方必要なケース

### Step 7: PDCAサイクル修正
**ファイル**: `src/generation/pdca_controller.py`
- 設定可能な`max_regenerations`（デフォルト 0 で全文再生成禁止）
- 局所パッチの許容回数`max_local_patches`（デフォルト 1）
- フィードバックループの実装ではなく、一括生成後のIssueベースの局所修正に限定
**テスト例**: `tests/generation/test_pdca_controller.py`
```python
def test_no_full_regeneration_when_max_zero():
    controller = PDCAController(max_regenerations=0)
    assert controller.should_regenerate_full_text() == False

def test_local_patch_limited_to_once():
    controller = PDCAController(max_local_patches=1)
    controller.record_local_patch()
    assert controller.can_do_local_patch() == False
```

### Step 8: 局所パッチ実装
**ファイル**: `src/generation/local_polish.py`
- Issue に位置情報（開始インデックス・終了インデックスまたは章・段落番号）を含める前提
- 指定範囲のテキストのみを取り出し、その前後文脈も含めたプロンプトで再生成
- 生成結果を元テキストに組み込む
**テスト例**: `tests/generation/test_local_polish.py`
```python
def test_polish_preserves_context():
    original = "最初の文。対象シーン。最後の文。"
    # 対象シーンのみを「改善された対象シーン」に置換することを期待
    polished = LocalPolisher().polish(
        original,
        target_range=(4, 10),  # 「対象シーン」の位置
        improvement_instruction="より感情豊かに書き直して"
    )
    assert polished.startswith("最初の文。")
    assert polished.endswith("最後の文。")
    assert "改善された対象シーン" in polished
```

### Step 9: Easy Mode フローデザイン
**ファイル**: `docs/EASY_MODE_FLOW.md`
- ユーザーストーリー形式でフローを記述
- 画面遷移図（Mermaid 推奨）
- 各ステップでのユーザーアクションとシステムレスポンス
**例**:
```
1. ユーザーがサイトにアクセス
2. 「簡単モード」ボタンをクリック（またはデフォルトで簡単モード）
3. ストーリーのジャンル・長さ・キーワードを入力
4. 「生成開始」ボタンをクリック
5. 生成進行状況バーと中間プレビューが表示
6. 生成完了後、レビュー画面で全文閲覧・章ごとのダウンロードオプション
7. ZIP または EPUB 形式で一括ダウンロード選択
8. ダウンロード完了メッセージ表示
```

### Step 10: Easy Mode フロントエンド実装
**技術選択**: 既存スタイルに合わせて（例: Vanilla JS、または既に使っているReact/Vue等）
**ディレクトリ**: `web/easy_mode/`
- `index.html`: メインページ
- `style.css`: シンプルなスタイル
- `app.js`: フロントエンドロジック
**実装ポイント**:
- フォーム入力バリデーション
- 生成中のスピナーまたはプログレスバー
- Server-Sent Events または Polling でバックエンドから進行状況取得
- 生成結果のプレビュー表示（テキストエリアまたは読みやすいフォーマット）
- ZIP/EPUB ダウンロードボタン

### Step 11: Easy Mode バックエンドAPI
**ファイル**: `src/api/easy_mode.py`
- エンドポイント例:
  - `POST /api/easy_mode/generate`: 生成リクエスト受付・ジョブID返却
  - `GET /api/easy_mode/status/{job_id}`: 進行状況・中間結果取得
  - `GET /api/easy_mode/result/{job_id}`: 生成結果取得またはダウンロードURL
  - `GET /api/easy_mode/download/{job_id}`: ZIP/EPUB ファイル直接配信
- バックグラウンドジョブ処理（Celery、RQ、またはシンプルなスレッドプール）
- ジョブ結果の一時保存（ファイルシステムまたはキャッシュ）
**テスト**: `tests/api/test_easy_mode.py`
```python
def test_generate_endpoint_returns_job_id():
    response = client.post("/api/easy_mode/generate", json=test_request)
    assert response.status_code == 202
    data = response.get_json()
    assert "job_id" in data

def test_status_endpoint_returns_progress():
    job_id = "test-job-123"
    # ジョブを模擬またはモック
    response = client.get(f"/api/easy_mode/status/{job_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert "progress" in data  # 0-100 の数値または文字列
```

### Step 12: Easy Mode エラーハンドリング
- エラータイプ別のユーザーメッセージ（入力エラー・サービスエラー・タイムアウト等）
- エラー発生時の再試行案内（ボタン表示）
- サポート連絡先または FAQ への導線
- 開発者向けには詳細ログを出すが、ユーザーには技術詳細を晒さない

### Step 13-15: ベンチマーク測定
**スクリプト**: `scripts/benchmark_generation.py`
- 標準プロンプトセットを用意（複数ジャンル・長さ）
- トークン消費量の概算（`tiktoken` または概算ルール）
- 生成速度（ウォールクロック時間）
- 結果を JSON で出力
**ベースライン測定（Step 14）**: 最適化前のコードで実行（可能なら一時的にブランチを切るか、フラグで切替）
**最適化後測定（Step 15）**: 最適化実装後で実行
**目標**: コスト 1/8 以下・速度 1/8 以上（すなわち 8倍速く・8分の1コスト）

### Step 16: プロンプトテンプレート標準化
**ディレクトリ構造**:
```
prompts/
├── base/
│   ├── system.yaml           # システムプロンプトベース
│   ├── auditor_unified.yaml  # 統合オーディタープロンプトベース
│   └── local_polish.yaml     # 局所推敲プロンプトベース
├── v1.0/
│   ├── system.yaml
│   ├── auditor_unified.yaml
│   └── local_polish.yaml
└── latest/ -> v1.0/          # シンボリックリンクまたは環境変数で参照
```
**ファイルフォーマット**: YAML（コメント可能・階層構造）
**例**: `prompts/base/system.yaml`
```yaml
# システムプロンプトのベーステンプレート
role: |
  あなたはプロのライトノベル編集者です。
  以下の制約に従ってストーリーを評価・改善してください。

constraints:
  - 文字数: {min_chars}-{max_chars} 文字
  - ジャンル: {genre}
  - 必須キーワード: {keywords}
  - トーン: {tone}
```

### Step 17: プロンプトローダー実装
**ファイル**: `src/prompts/loader.py`
- バージョン指定機能（デフォルトは `latest`）
- フォールバック（指定バージョンが見つからない場合はベースまたは別バージョンを試す）
- キャッシュオプション（ファイルシステムベースで十分）
- 変数置換（`{genre}` 等を実際の値で置換）
**テスト例**: `tests/prompts/test_loader.py`
```python
def test_load_system_prompt():
    loader = PromptLoader()
    prompt = loader.load("system", version="v1.0")
    assert "プロのライトノベル編集者" in prompt
    assert "{genre}" in prompt  # 変数は未置換の状態で返すか、別メソッドで置換

def test_render_prompt():
    loader = PromptLoader()
    rendered = loader.render(
        "system",
        version="v1.0",
        genre="ファンタジー",
        min_chars=1000,
        max_chars=5000,
        keywords=["ドラゴン", "魔法"],
        tone="壮大"
    )
    assert "ジャンル: ファンタジー" in rendered
    assert "必須キーワード: ドラゴン, 魔法" in rendered
```

### Step 18: フォールバック機構実装
**ファイル**: `src/generation/fallback_generator.py`
- LLM API からの例外またはタイムアウトを捕捉
- 静的ルールベースのジェネレーターにフォールバック（テンプレート＋ランダム要素・文法ルール）
- 品質は保証しないが「生成されない」よりはマシという商用判断
- フォールバック発生時に監視・アラートを発信（Step 24 のベンチマークに失敗率を含めるか）
**テスト例**: `tests/generation/test_fallback_generator.py`
```python
@patch("src.generation.fallback_generator.call_primary_generator")
def test_fallback_on_exception(mock_call):
    mock_call.side_effect = Exception("API Error")
    generator = FallbackGenerator()
    result = generator.generate("ファンタジー", 1000)
    assert result is not None
    assert len(result) >= 800  # 最低限の長さは保証
    # 静的ルールベースであることの簡易チェック（例: 特定パターンの存在）
```

### Step 19: キャッシュレイヤー導入
**ファイル**: `src/generation/cache.py`
- シンプルなキー値ストア（ファイルベースまたはメモリベース）
- キー: プロンプトハッシュ + パラメータハッシュ + シード（もしあれば）
- 値: 生成結果テキスト
- TTL（Time To Live）機能オプション
- キャッシュヒット率を測定するメトリクス
**テスト例**: `tests/generation/test_cache.py`
```python
def test_cache_hit_miss():
    cache = GenerationCache()
    key = ("prompt_hash", "param_hash")
    value = "Generated text"
    
    # 初回はミス
    assert cache.get(key) is None
    
    # 保存後はヒット
    cache.set(key, value)
    assert cache.get(key) == value
    
    # 別キーはミス
    assert cache.get(("other", "hash")) is None
```

### Step 20: セマンティックキャッシュ検討（オプション）
**注**: Phase 3 では必須ではないが、今後の方向性を検討
**ファイル**: `docs/SEMANTIC_CACHE_FEASIBILITY.md`
- アプローチ: プロンプトをベクトル化し、類似度検索で過去の結果を再利用
- 課題: 類似度閾値の設定・ベクトルストアのコスト・遅延増加
- 推奨: Phase 4 またはオプション機能として検討中

### Step 21-23: リグレッション防止テスト

**ファイル**: `tests/audit/test_unified_auditor_equivalence.py`
```python
"""統合オーディターが元の8専門オーディターと同等の品質を保つかのテスト"""
# 実際の実装では:
# 1. 元の8専門オーディターの実装を参照（または過去のコードから抽出）
# 2. 同一入力に対するIssueリストを比較
# 3. 完全一致を求めず、「重要な見逃しがないか」をチェック
import pytest

def test_unified_auditor_no_critical_omissions():
    # プレースホルダー：実際の等価性テストに置き換える
    assert True, "Replace with actual equivalence test using golden issue sets"
```

**ファイル**: `tests/generation/test_pdca_limitation.py`
```python
"""PDCA スリム化の振る舞い（全文再生成禁止・局所パッチ最大1回）をテスト"""
from src.generation.pdca_controller import PDCAController

def test_full_regeneration_disabled_by_default():
    """Phase 3 ではデフォルトで全文再生成は禁止される"""
    controller = PDCAController()  # デフォルトコンストラクタ
    assert controller.max_regenerations == 0
    assert controller.should_regenerate_full_text() == False

def test_local_patch_limited_to_one():
    """局所パッチは最大1回まで許容される"""
    controller = PDCAController(max_local_patches=1)
    assert controller.can_do_local_patch() == True
    controller.record_local_patch()
    assert controller.can_do_local_patch() == False
```

**ファイル**: `tests/e2e/test_easy_mode_flow.py`
```python
"""Easy Mode フローのエンドツーエンドテスト"""
from unittest.mock import patch, MagicMock
import pytest
from src.api.easy_mode import generate_story_job  # 例: バックエンドジョブ関数

@patch("src.api.easy_mode.call_generation_pipeline")
def test_easy_mode_generate_job_creates_result(mock_pipeline):
    """ジョブ開始から結果取得までのフロー"""
    # モックの設定
    mock_pipeline.return_value = iter([
        {"progress": 25, "preview": "序章..."},
        {"progress": 50, "preview": "序章... 中盤..."},
        {"progress": 100, "preview": "完成稿"},
        {"result": "全文テキスト"}  # 最終的に結果を返す
    ])
    
    # ジョブ開始
    job_id = generate_story_job(
        genre="ファンタジー",
        length_medium=3000,
        keywords=["魔法", "剣"],
        tone="王道"
    )
    assert job_id is not None
    
    # ステータス確認（簡易版）
    # 実際にはポーリングまたは WebSocket で取得するが、ここでは直接関数コールを模擬
    # 結果取得
    result = get_job_result(job_id)  # 実装に合わせる
    assert result is not None
    assert len(result) > 1000  # 最低限の長さ
```

### Step 24: 完了確認・PR 作成
```bash
# 全テスト実行（カバレッジ付き・フェーズ2ベースライン維持）
pytest --cov=src --cov-fail-under=55 --tb=short -q

# リンター・型チェック
ruff check .
mypy src/

# ベンチマーク目標達成確認
python scripts/check_benchmark_improvement.py  # 基準値と比較し、目標達成か判定

# Easy Mode 動作確認（手動または自動ブラウザテスト）
# 例: playwright テストがあるなら実行
# npx playwright test tests/e2e/easy_mode.spec.js

# PR 作成
gh pr create --title "Phase 3: コア軽量化とEasy Mode研ぎ澄まし (Pragmatic Streamlining & UX)" \
             --body-file plans/PHASE_3_IMPLEMENTATION_PLAN.md \
             --base main \
             --head phase3-easymode
```

---

## 依存関係・並列化ガイド

```
Step 1-2 → 
Step 3-6 → (Step 7-8 並列) → 
Step 9-12 → 
Step 13-15 → 
Step 16-18 → 
Step 19 → 
Step 20 (オプション/並列可能) → 
Step 21-23 → 
Step 24
```

- **並列可能**: 
  - オーディター実装(3-6)、PDCA制御(7-8)、Easy Mode フロントエンド/バックエンド(9-12)は比較的独立
  - ベンチマーク測定(13-15)は別ブランチまたはフラグ切替で並列実行可能
  - プロンプト標準化(16-18)、キャッシュ(19)はオーディター・生成パイプラインと連携点があるため、ある程度の順序あり
  - セマンティックキャッシュ検討(20)は調査タスクなので他と並列可能
- **順序必須**: 
  - 設計(3) → 実装(4-8) 
  - フローエンド(9) → フロントエンド/バックエンド実装(10-11) → エラーハンドリング(12)
  - ベンチベースライン(14) → 最適化実装 → ベンチ後測定(15)

---

## 完了判定基準 (Definition of Done)

- [ ] 全 24 ステップのチェックボックス完了
- [ ] `pytest --cov-fail-under=55` PASS
- [ ] `ruff check .` / `mypy src/` PASS
- [ ] オーディター集約が実装済み（静的ルール + 統合LLMオーディター + パイプライン）
- [ ] PDCAサイクルがスリム化済み（全文再生成ループ禁止・局所パッチ最大1回）
- [ ] Easy Mode フローが完成済み（ブラウザからシームレスな入力→生成→レビュー→納品）
- [ ] トークン消費・生成速度のベンチマークが実装済みかつ測定可能
- [ ] プロンプトテンプレートが標準化・バージョン管理済み
- [ ] フォールバック機構が実装済み（LLM失敗時の静的ルールベース代替）
- [ ] キャッシュレイヤーが導入済み（同一プロンプト結果のキャッシュ）
- [ ] セマンティックキャッシュの可否調査が完了し、Phase 4 以降の方向性が示されている（オプション）
- [ ] 新規テスト 3 本（Step 21-23）全 PASS
- [ ] ベンチマーク改善目標達成：
    - トークン消費量: 元の実装の 1/8 以下（コスト削減 87.5% 以上）
    - 生成速度: 元の実装の 1/8 以下（すなわち 8倍以上速くなる）
    - または「コストと速度の積」で 1/64 以上の改善（どちらか一方が大きく改善してもよいが、両方とも目標に向かう進展があること）
- [ ] Easy Mode が主要ブラウザ（Chrome/Firefox/Safari）で動作確認済み
- [ ] PR 作成・レビュー承認・マージ完了
- [ ] `main` ブランチで `git tag phase3-done` 打刻
- [ ] ドキュメント更新完了：
    - `docs/OPTIMIZED_AUDITOR_DESIGN.md`
    - `docs/EASY_MODE_FLOW.md`
    - `docs/PROMPT_VERSIONING.md`
    - `docs/SEMANTIC_CACHE_FEASIBILITY.md` （作成した場合）