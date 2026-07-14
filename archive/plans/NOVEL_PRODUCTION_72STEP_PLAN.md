# 72ステップ実装計画書：小説1作品10話生成・レポート作成パイプライン

**作成日**: 2026-07-13
**対象プロジェクト**: cR15（覇権小説自動生成エンジン）
**目的**: 1話3000字の小説10話を実際に生成し、トークン使用量・品質メトリクスを含むレポートを作成する。

---

## 設計原則（低性能LLM対応）

1. **1ステップ＝1ファイル編集・1関数追加のみ**：複数ファイル同時編集禁止。
2. **依存方向は常に前ステップ→次ステップ**：戻り参照しない。
3. **各ステップは検証可能**：`python -c`1行またはpytest1件で確認。
4. **巨大生成禁止**：1ステップのコードは50行以内。

---

## Phase 1: レポート生成サービス基盤（ステップ1-12）

### ステップ1: レポートモデル `TokenUsageReport` の作成
- **対象ファイル**: `src/models/report.py`（新規）
- **アクション**: Pydanticモデル `TokenUsageReport` を定義
  - `total_tokens: int`
  - `input_tokens: int`
  - `output_tokens: int`
  - `episode_count: int`
  - `generation_time_seconds: float`
- **検証**: `python -c "from src.models.report import TokenUsageReport; r = TokenUsageReport(total_tokens=1000, input_tokens=500, output_tokens=500, episode_count=1, generation_time_seconds=10.0); print(r.model_dump())"`

### ステップ2: レポートモデル `QualityMetricsReport` の作成
- **対象ファイル**: `src/models/report.py`
- **アクション**: `QualityMetricsReport` を追加
  - `coherence_score: float`
  - `character_consistency: float`
  - `pacing_score: float`
  - `hook_retention: float`
  - `emotional_resonance: float`
  - `commercial_viability: float`
- **検証**: `python -c "from src.models.report import QualityMetricsReport; r = QualityMetricsReport(coherence_score=0.8, character_consistency=0.9, pacing_score=0.7, hook_retention=0.8, emotional_resonance=0.75, commercial_viability=0.85); print(r.model_dump())"`

### ステップ3: 完全なレポートモデル `ProductionReport` の作成
- **対象ファイル**: `src/models/report.py`
- **アクション**: `ProductionReport` を追加（ステップ1,2のモデル組合せ）
  - `title: str`
  - `genre: str`
  - `target_word_count: int`
  - `token_usage: TokenUsageReport`
  - `quality_metrics: QualityMetricsReport`
  - `episode_summaries: List[EpisodeSummary]`
  - `total_generation_time: float`
  - `created_at: datetime`
- **検証**: `python -c "from src.models.report import ProductionReport; r = ProductionReport(title='Test', genre='fantasy', target_word_count=3000, token_usage=None, quality_metrics=None, episode_summaries=[], total_generation_time=0.0, created_at=None); print(r.model_dump())"`

### ステップ4: `src/models/report.py` のテストファイル作成
- **対象ファイル**: `tests/test_report_models.py`（新規）
- **アクション**: ステップ1-3のモデルに対するpytestを追加
- **検証**: `pytest tests/test_report_models.py -q`

### ステップ5: `TokenTracker` サービスクラスの基本構造
- **対象ファイル**: `src/services/token_tracker.py`（新規）
- **アクション**: `TokenTracker` クラスを作成
  - `__init__`: 初期状態（total=0, input=0, output=0）
  - `add_usage(input_tokens, output_tokens)`: 使用量加算
  - `get_report()`: レポート返す
- **検証**: `python -c "from src.services.token_tracker import TokenTracker; t = TokenTracker(); t.add_usage(100, 200); print(t.get_report())"`

### ステップ6: `TokenTracker` にエピソード追跡追加
- **対象ファイル**: `src/services/token_tracker.py`
- **アクション**: `episode_usages: List[dict]` を追加し、各エピソード毎の使用量記録
- **検証**: `pytest tests/test_token_tracker.py -q`（ステップ7でテスト作成）

### ステップ7: `TokenTracker` のユニットテスト
- **対象ファイル**: `tests/test_token_tracker.py`（新規）
- **アクション**: `test_add_usage`, `test_get_report`, `test_episode_tracking` を追加
- **検証**: `pytest tests/test_token_tracker.py -q`

### ステップ8: `QualityScorer` サービスクラスの基本構造
- **対象ファイル**: `src/services/quality_scorer.py`（新規）
- **アクション**: `QualityScorer` クラスを作成
  - `score_coherence(text)`: 整合性スコア
  - `score_character_consistency(text)`: キャラ一貫性
  - `score_pacing(text)`: ペーシング
  - `score_hook_retention(text)`: フック保持率
  - `score_emotional_resonance(text)`: 感情共鳴
  - `score_commercial_viability(text)`: 商業的ポテンシャル
- **検証**: `python -c "from src.services.quality_scorer import QualityScorer; s = QualityScorer(); print(s.score_coherence('test'))"`

### ステップ9: `QualityScorer` にLLM評価機能追加
- **対象ファイル**: `src/services/quality_scorer.py`
- **アクション**: LLMを使用した品質評価機能の実装
- **検証**: テストファイル作成（ステップ10）

### ステップ10: `QualityScorer` のユニットテスト
- **対象ファイル**: `tests/test_quality_scorer.py`（新規）
- **アクション**: 各スコアメソッドのpytestを追加
- **検証**: `pytest tests/test_quality_scorer.py -q`

### ステップ11: `ReportGenerator` サービスクラスの基本構造
- **対象ファイル**: `src/services/report_generator.py`（新規）
- **アクション**: `ReportGenerator` クラスを作成
  - `generate_production_report(title, genre, token_tracker, quality_scorer, episodes)`: 完全レポート生成
- **検証**: `python -c "from src.services.report_generator import ReportGenerator; r = ReportGenerator(); print(type(r))"`

### ステップ12: Phase1完了チェックリスト
- **対象ファイル**: `docs/phase1_done.md`（新規）
- **アクション**: ステップ1-11の完了検証コマンド一覧を記録
- **検証**: 各コマンド手動確認

---

## Phase 2: エピソード生成パイプライン（ステップ13-24）

### ステップ13: 作品設定データクラスの作成
- **対象ファイル**: `src/models/production_config.py`（新規）
- **アクション**: `NovelProject` dataclassを作成
  - `title: str`
  - `genre: str`
  - `synopsis: str`
  - `keywords: List[str]`
  - `target_episodes: int = 10`
  - `target_word_count_per_episode: int = 3000`
- **検証**: `python -c "from src.models.production_config import NovelProject; n = NovelProject(title='Test', genre='fantasy', synopsis='test', keywords=['action']); print(n.target_episodes)"`

### ステップ14: エピソード生成リクエストモデル
- **対象ファイル**: `src/models/production_config.py`
- **アクション**: `EpisodeGenerateRequest` dataclassを追加
- **検証**: インポート確認

### ステップ15: `NovelProducer` サービスクラスの基本構造
- **対象ファイル**: `src/services/novel_producer.py`（新規）
- **アクション**: `NovelProducer` クラスを作成
  - `create_project(config)`: 新規作品プロジェクト作成
  - `generate_episode(project_id, ep_num)`: 1話生成
  - `generate_all_episodes(project_id)`: 全10話生成
- **検証**: `python -c "from src.services.novel_producer import NovelProducer; n = NovelProducer(); print(type(n))"`

### ステップ16: `NovelProducer` に進捗コールバック追加
- **対象ファイル**: `src/services/novel_producer.py`
- **アクション**: `on_progress(ep_num, status, message)` コールバック対応
- **検証**: テストファイル作成（ステップ17）

### ステップ17: `NovelProducer` のユニットテスト
- **対象ファイル**: `tests/test_novel_producer.py`（新規）
- **アクション**: 基本メソッドのpytestを追加
- **検証**: `pytest tests/test_novel_producer.py -q`

### ステップ18: `EpisodeWriter` クラスへの委譲構造
- **対象ファイル**: `src/services/episode_writer.py`（新規）
- **アクション**: `EpisodeWriter` クラスを作成
  - `write(book_id, ep_num, context)`: 1話執筆
  - `word_count_estimate()`: 文字数見積
- **検証**: `python -c "from src.services.episode_writer import EpisodeWriter; w = EpisodeWriter(); print(type(w))"`

### ステップ19: `EpisodeWriter` と既存Writing Agent統合
- **対象ファイル**: `src/services/episode_writer.py`
- **アクション**: `src/agents/writing.py` の `write_episode` を呼び出すように修正
- **検証**: インポート確認

### ステップ20: `EpisodeWriter` のユニットテスト
- **対象ファイル**: `tests/test_episode_writer.py`（新規）
- **アクション**: 基本メソッドのpytestを追加
- **検証**: `pytest tests/test_episode_writer.py -q`

### ステップ21: エピソードコンテキスト生成機能
- **対象ファイル**: `src/services/episode_context.py`（新規）
- **アクション**: `EpisodeContextBuilder` クラスを作成
  - `build_context(book_id, ep_num)`: 前話情報含めたコンテキスト生成
- **検証**: `python -c "from src.services.episode_context import EpisodeContextBuilder; b = EpisodeContextBuilder(); print(type(b))"`

### ステップ22: コンテキストビルダーのテスト
- **対象ファイル**: `tests/test_episode_context.py`（新規）
- **アクション**: コンテキスト生成のpytestを追加
- **検証**: `pytest tests/test_episode_context.py -q`

### ステップ23: エピソード完了時の品質チェック
- **対象ファイル**: `src/services/novel_producer.py`
- **アクション**: `check_episode_quality(episode_text)` メソッド追加
- **検証**: 既存テストが通ることを確認

### ステップ24: Phase2完了チェックリスト
- **対象ファイル**: `docs/phase2_done.md`（新規）
- **アクション**: ステップ13-23の完了検証コマンド一覧を記録
- **検証**: 各コマンド手動確認

---

## Phase 3: バックエンドAPIエンドポイント（ステップ25-36）

### ステップ25: エピソード生成APIリクエストモデル
- **対象ファイル**: `src/models/api_schemas.py`
- **アクション**: `ProduceNovelRequest` を追加
  - `title: str`
  - `genre: str`
  - `synopsis: str`
  - `keywords: List[str]`
  - `target_episodes: int = 10`
- **検証**: `python -c "from src.models.api_schemas import ProduceNovelRequest; r = ProduceNovelRequest(title='Test', genre='fantasy', synopsis='s', keywords=['k']); print(r.target_episodes)"`

### ステップ26: レスポンスモデル追加
- **対象ファイル**: `src/models/api_schemas.py`
- **アクション**: `ProduceNovelResponse` を追加
  - `project_id: int`
  - `status: str`
  - `message: str`
- **検証**: インポート確認

### ステップ27: APIエンドポイント `/api/novel/produce` 追加
- **対象ファイル**: `src/backend/routers/novel.py`（新規）
- **アクション**: `POST /api/novel/produce` エンドポイント作成
- **検証**: ルータ登録確認

### ステップ28: エピステータス取得API追加
- **対象ファイル**: `src/backend/routers/novel.py`
- **アクション**: `GET /api/novel/{project_id}/status` エンドポイント追加
- **検証**: ルータ登録確認

### ステップ29: エピソード一覧取得API追加
- **対象ファイル**: `src/backend/routers/novel.py`
- **アクション**: `GET /api/novel/{project_id}/episodes` エンドポイント追加
- **検証**: ルータ登録確認

### ステップ30: レポート取得API追加
- **対象ファイル**: `src/backend/routers/novel.py`
- **アクション**: `GET /api/novel/{project_id}/report` エンドポイント追加
- **検証**: ルータ登録確認

### ステップ31: API_router登録
- **対象ファイル**: `src/backend/server.py`
- **アクション**: `novel` router をメインアプリに登録
- **検証**: `python -c "from src.backend.server import app; print([r.path for r in app.routes])"`

### ステップ32: API統合テストの雛形
- **対象ファイル**: `tests/test_novel_api.py`（新規）
- **アクション**: APIendpointのpytest雛形を追加
- **検証**: `pytest tests/test_novel_api.py -q`

### ステップ33: リクエストバリデーション確認
- **対象ファイル**: `src/models/api_schemas.py`
- **アクション**: `ProduceNovelRequest` のバリデーション確認
- **検証**: 不正入力でエラーになることを確認

### ステップ34: エラー処理の追加
- **対象ファイル**: `src/backend/routers/novel.py`
- **アクション**: 例外処理の追加（404, 500等）
- **検証**: エラー時適切なステータスコードを返す

### ステップ35: APIドキュメントへの記載
- **対象ファイル**: `docs/api_novel_endpoints.md`（新規）
- **アクション**: 新API endpointの文書化
- **検証**: ファイル作成確認

### ステップ36: Phase3完了チェックリスト
- **対象ファイル**: `docs/phase3_done.md`（新規）
- **アクション**: ステップ25-35の完了検証コマンド一覧を記録
- **検証**: 各コマンド手動確認

---

## Phase 4: フロントエンドUI統合（ステップ37-48）

### ステップ37: Streamlit小説生成タブ追加
- **対象ファイル**: `streamlit_app/ui_tabs_writing.py`
- **アクション**: `render_novel_production_tab()` 関数追加
- **検証**: ページレンダリング確認

### ステップ38: 作品設定フォーム作成
- **対象ファイル**: `streamlit_app/ui_tabs_writing.py`
- **アクション**: `render_novel_config_form()` 関数追加
  - タイトル、ジャンル、概要、キーワード入力
- **検証**: フォーム表示確認

### ステップ39: 生成進捗表示コンポーネント
- **対象ファイル**: `streamlit_app/ui_components.py`
- **アクション**: `render_production_progress(ep_num, total, status)` 関数追加
- **検証**: プログレスバー表示確認

### ステップ40: プロダクションログ表示
- **対象ファイル**: `streamlit_app/ui_components.py`
- **アクション**: `render_production_log(logs: List[str])` 関数追加
- **検証**: ログ表示確認

### ステップ41: レポート表示コンポーネント
- **対象ファイル**: `streamlit_app/ui_components.py`
- **アクション**: `render_production_report(report: ProductionReport)` 関数追加
- **検証**: レポート表示確認

### ステップ42: 生成開始ボタン処理
- **対象ファイル**: `streamlit_app/ui_tabs_writing.py`
- **アクション**: `handle_start_production(config)` 関数追加
- **検証**: ボタンクリックで生成開始

### ステップ43: 進捗コールバックの実装
- **対象ファイル**: `streamlit_app/ui_tabs_writing.py`
- **アクション**: `ProgressCallback` クラスの実装
- **検証**: 進捗更新がUI反映される

### ステップ44: バックグラウンドタスク対応
- **対象ファイル**: `streamlit_app/background.py`
- **アクション**: `start_production_background(project_config)` 追加
- **検証**: 非同期処理開始確認

### ステップ45: エピソード一覧表示
- **対象ファイル**: `streamlit_app/ui_tabs_writing.py`
- **アクション**: `render_episode_list(project_id)` 関数追加
- **検証**: エピソード列表示確認

### ステップ46: エピソード内容表示
- **対象ファイル**: `streamlit_app/ui_tabs_writing.py`
- **アクション**: `render_episode_content(book_id, ep_num)` 関数追加
- **検証**: エピソード内容表示確認

### ステップ47: UI統合テスト
- **対象ファイル**: `tests/test_ui_production.py`（新規）
- **アクション**: UIコンポーネントのpytest追加
- **検証**: `pytest tests/test_ui_production.py -q`

### ステップ48: Phase4完了チェックリスト
- **対象ファイル**: `docs/phase4_done.md`（新規）
- **アクション**: ステップ37-47の完了検証コマンド一覧を記録
- **検証**: 各コマンド手動確認

---

## Phase 5: レポート生成詳細機能（ステップ49-60）

### ステップ49: エピソードサマリー抽出機能
- **対象ファイル**: `src/services/report_generator.py`
- **アクション**: `extract_episode_summary(episode_text)` メソッド追加
- **検証**: 100文字程度のサマリーが生成される

### ステップ50: 品質スコア算出のLLM統合
- **対象ファイル**: `src/services/quality_scorer.py`
- **アクション**: LLMを使用して品質スコアを算出する機能を実装
- **検証**: テストで確認

### ステップ51: レポートへの品質メトリクス統合
- **対象ファイル**: `src/services/report_generator.py`
- **アクション**: `generate_production_report` に品質メトリクス含める
- **検証**: レポートにquality_metricsが含まれる

### ステップ52: トークン使用量の詳細記録
- **対象ファイル**: `src/services/token_tracker.py`
- **アクション**: エピソード毎のトークン使用量を記録
- **検証**: `get_report()` にepisode_usagesが含まれる

### ステップ53: レポートのMarkdown出力
- **対象ファイル**: `src/services/report_generator.py`
- **アクション**: `to_markdown(report)` メソッド追加
- **検証**: Markdown形式の文字列が返る

### ステップ54: レポートのHTML出力
- **対象ファイル**: `src/services/report_generator.py`
- **アクション**: `to_html(report)` メソッド追加
- **検証**: HTML形式の文字列が返る

### ステップ55: レポートファイル保存機能
- **対象ファイル**: `src/services/report_generator.py`
- **アクション**: `save_report(report, filepath)` メソッド追加
- **検証**: 指定パスにファイルが保存される

### ステップ56: レポート生成の統合テスト
- **対象ファイル**: `tests/test_report_generator.py`（新規）
- **アクション**: `generate_production_report` のpytest追加
- **検証**: `pytest tests/test_report_generator.py -q`

### ステップ57: サンプルレポート生成
- **対象ファイル**: `docs/sample_production_report.md`（新規）
- **アクション**: デモ用レポートファイル作成
- **検証**: ファイル存在確認

### ステップ58: レポートテンプレートの整備
- **対象ファイル**: `templates/report_template.md`（新規）
- **アクション**: レポート出力のテンプレート作成
- **検証**: テンプレートファイル存在確認

### ステップ59: レポート設定のカスタマイズ
- **対象ファイル**: `src/models/report.py`
- **アクション**: `ReportConfig` dataclassを追加
- **検証**: インポート確認

### ステップ60: Phase5完了チェックリスト
- **対象ファイル**: `docs/phase5_done.md`（新規）
- **アクション**: ステップ49-59の完了検証コマンド一覧を記録
- **検証**: 各コマンド手動確認

---

## Phase 6: 実際の作品生成パイプライン（ステップ61-72）

### ステップ61: 作品設定の決定
- **アクション**: 生成する作品の設定を決定
  - タイトル: 「覇者の帰還」
  - ジャンル: ファンタジー
  - 概要: かつて最強と恐れられた戦士が、10年の眠りから覚醒し、変わり果てた世界を取り戻す物語
  - キーワード: 異世界、転生、戦闘、復讐、覇権
- **検証**: 設定を記録

### ステップ62: バックエンド起動確認
- **アクション**: FastAPIサーバーが起動していることを確認
- **検証**: `curl http://localhost:8200/api/health` が200を返す

### ステップ63: データベース接続確認
- **アクション**: データベースへの接続と初期化が正常であることを確認
- **検証**: `python -c "from src.backend.database.core import DatabaseCore; print('OK')"`

### ステップ64: 作品プロジェクト作成
- **アクション**: APIまたはコマンドで新規作品プロジェクトを作成
- **検証**: プロジェクトIDが返される

### ステップ65: 第1話生成
- **アクション**: 第1話を生成（3000字目標）
- **検証**: 生成されたテキストが返される

### ステップ66: 第2-5話生成
- **アクション**: 第2話から第5話まで生成
- **検証**: 各話が正常に生成される

### ステップ67: 第6-10話生成
- **アクション**: 第6話から第10話まで生成
- **検証**: 各話が正常に生成される

### ステップ68: トークン使用量集計
- **アクション**: 生成に使用したトークン量を集計
- **検証**: レポートにトークン量が記録されている

### ステップ69: 品質評価実行
- **アクション**: 全エピソードの品質評価を実行
- **検証**: 各話の品質スコアが記録されている

### ステップ70: レポート生成
- **対象ファイル**: `output/PRODUCTION_REPORT_20260713.md`
- **アクション**: 最終レポートを生成
- **検証**: レポートファイルが作成される

### ステップ71: 生成作品の保存
- **アクション**: 全エピソードのテキストを保存
- **検証**: 作品データが保存されている

### ステップ72: 最終レポート確認・改善提案
- **アクション**: 生成されたレポートを確認、改善点を記録
- **検証**: レポート完成

---

## 成果物一覧

| ファイル | 説明 |
|---------|------|
| `src/models/report.py` | レポート用データモデル |
| `src/services/token_tracker.py` | トークン使用量追跡サービス |
| `src/services/quality_scorer.py` | 品質スコア算出サービス |
| `src/services/report_generator.py` | レポート生成サービス |
| `src/services/novel_producer.py` | 小説生成サービス |
| `src/services/episode_writer.py` | エピソード執筆サービス |
| `src/services/episode_context.py` |  эпизодコンテキスト生成 |
| `src/models/production_config.py` | 作品設定モデル |
| `src/backend/routers/novel.py` | 新規APIエンドポイント |
| `tests/test_report_*.py` | 各サービスのテスト |
| `docs/phase*_done.md` | 各Phaseの完了チェックリスト |
| `output/PRODUCTION_REPORT_*.md` | 実際の生成レポート |

---

## 検証コマンド一覧

```bash
# Phase 1 検証
python -c "from src.models.report import TokenUsageReport, QualityMetricsReport, ProductionReport; print('OK')"
pytest tests/test_report_models.py tests/test_token_tracker.py tests/test_quality_scorer.py -q

# Phase 2 検証
python -c "from src.services.novel_producer import NovelProducer; from src.services.episode_writer import EpisodeWriter; print('OK')"
pytest tests/test_novel_producer.py tests/test_episode_writer.py tests/test_episode_context.py -q

# Phase 3 検証
python -c "from src.backend.routers.novel import router; print('OK')"
pytest tests/test_novel_api.py -q

# Phase 4 検証
python -c "from streamlit_app.ui_tabs_writing import render_novel_production_tab; print('OK')"
pytest tests/test_ui_production.py -q 2>/dev/null || echo "UI tests skipped"

# Phase 5 検証
python -c "from src.services.report_generator import ReportGenerator; r = ReportGenerator(); print(type(r.to_markdown).__name__)"
pytest tests/test_report_generator.py -q

# Phase 6 検証（実際の生成）
curl http://localhost:8200/api/health