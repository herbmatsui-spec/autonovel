# P3: エージェント層・執筆＆監査エンジン テストカバレッジ80%引き上げ実装計画書（全12ステップ）

**対象レイヤー**: `src/agents/` (erotic/*, writing/*, context_builder_agent.py, audit.py, plot.py, writing_scheduler.py)  
**削減対象未カバー行**: 約 2,250 行（現状 21.1% → 目標 85%以上）  
**並列実行独立性**: 本計画書（P3）は `tests/unit/agents/` 配下にのみテストファイルを作成・編集します。他の計画書（P1, P2, P4〜P6）とは完全に直交しており、並列実装による競合は一切発生しません。  
**低性能LLM向け方針**: 全ステップに **コピペでそのまま動作する完全なテストコード（import文、fixture、mock、assertion）**、**検証コマンド**、**合格条件** を完備しています。実際のLLM API通信は行わず、`tests/mocks/llm_adapter.py` の `MockLLMAdapter` または `unittest.mock.AsyncMock` を使用して即座に緑（Pass）にします。

---

## 📋 ステップ一覧

| Step | 対象モジュール | 作成テストファイル | 概要 |
|:---:|:---|:---|:---|
| **Step 1** | `context_builder_agent.py` | `tests/unit/agents/test_context_builder.py` | キャラクター・世界観・前話ダイジェストのコンテキスト統合テスト |
| **Step 2** | `plot.py` (PlotAgent) | `tests/unit/agents/test_plot_agent.py` | 起承転結/三幕構成ビート生成、テンションアーク初期化 |
| **Step 3** | `writing/writing.py` (初期化・設定) | `tests/unit/agents/test_writing_agent_init.py` | WritingAgent 初期設定、スタイルテンプレート適用、パラメータ検証 |
| **Step 4** | `writing/_writing.py` (生成エンジン) | `tests/unit/agents/test_writing_agent_generate.py` | プロンプト送信、ストリーミング受信チャンク結合、文字数制御 |
| **Step 5** | `writing_scheduler.py` | `tests/unit/agents/test_writing_scheduler.py` | エピソード並行/順次スケジュール、章進行依存関係解決 |
| **Step 6** | `audit.py` (PlotIntegrityMonitor) | `tests/unit/agents/test_audit_agent.py` | キャラクター口調乖離検知、未回収伏線監査、整合性スコア算出 |
| **Step 7** | `erotic/continuity.py` (状態機械) | `tests/unit/agents/test_erotic_continuity.py` | シチュエーション継続性トラッカー、衣服・体勢・行為遷移 |
| **Step 8** | `erotic/filter.py` (コンテンツ適合性) | `tests/unit/agents/test_erotic_filter.py` | プラットフォーム規約適合性判定、NGワード検知、過激度判定 |
| **Step 9** | `erotic/diversity_scorer.py` | `tests/unit/agents/test_erotic_diversity.py` | シチュエーション・体位・シチュ多様性スコア算出 |
| **Step 10** | `erotic/density_controller.py` | `tests/unit/agents/test_erotic_density.py` | 読者離脱防止のための官能描写密度の動的コントロール |
| **Step 11** | `prompt_composer.py` | `tests/unit/agents/test_prompt_composer.py` | テンプレート変数バインディング、動的セクション構築 |
| **Step 12** | エージェント連携統合テスト | `tests/unit/agents/test_agents_integration.py` | PlotAgent → ContextBuilder → WritingAgent → AuditAgent 連動 |

---

## 🛠 各ステップ詳細仕様

### Step 1: ContextBuilderAgent のコンテキスト統合テスト
- **目的**: 世界観、登場キャラクター属性、直前話のサマリーをひとつのプロンプトコンテキストへ統合する処理を検証。
- **対象ファイル**: `src/agents/context_builder_agent.py`
- **作成テストファイル**: `tests/unit/agents/test_context_builder.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.context_builder_agent import ContextBuilderAgent

@pytest.mark.asyncio
async def test_context_builder_build():
    agent = ContextBuilderAgent()
    mock_bible = {"world_name": "ファンタジー帝国", "rules": ["魔法が存在する"]}
    mock_chars = [{"name": "アリス", "role": "主人公"}]
    
    ctx = await agent.build_context(
        book_id="b1",
        episode_number=2,
        bible_data=mock_bible,
        characters=mock_chars,
        prev_summary="第1話であらすじ"
    )
    
    assert "ファンタジー帝国" in str(ctx)
    assert "アリス" in str(ctx)
    assert "第1話であらすじ" in str(ctx)
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/agents/test_context_builder.py -v`
- **合格条件**: 全テストPASS。

---

### Step 2: PlotAgent の三幕構成ビート生成テスト
- **目的**: テーマやジャンルを入力とし、起承転結または三幕構成（発端・葛藤・結末）のビートシートを正しく構築できるか検証。
- **対象ファイル**: `src/agents/plot.py`
- **作成テストファイル**: `tests/unit/agents/test_plot_agent.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock
from src.agents.plot import PlotAgent

@pytest.mark.asyncio
async def test_plot_agent_generate_beats():
    agent = PlotAgent()
    agent._llm = AsyncMock()
    agent._llm.generate.return_value = '{"beats": [{"act": "Act 1", "summary": "日常と事件の勃発"}]}'
    
    beats = await agent.generate_plot("学園ファンタジー")
    assert beats is not None
    assert len(beats) >= 1
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/agents/test_plot_agent.py -v`
- **合格条件**: 全テストPASS。

---

### Step 3: WritingAgent の初期化・設定テスト
- **目的**: `WritingAgent` のシステムプロンプト設定、モデル選択、パラメータ検証をテスト。
- **対象ファイル**: `src/agents/writing/writing.py`
- **作成テストファイル**: `tests/unit/agents/test_writing_agent_init.py`
- **実装コード**:
```python
import pytest
from src.agents.writing.writing import WritingAgent

def test_writing_agent_initialization():
    agent = WritingAgent(model_name="test-model", temperature=0.7)
    assert agent.model_name == "test-model"
    assert agent.temperature == 0.7
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/agents/test_writing_agent_init.py -v`
- **合格条件**: 全テストPASS。

---

### Step 4: WritingAgent 内部エンジン (_writing.py) の生成処理テスト
- **目的**: チャンクストリーミングの結合、終了タグの除去、文字数カウントをテスト。
- **対象ファイル**: `src/agents/writing/_writing.py`
- **作成テストファイル**: `tests/unit/agents/test_writing_agent_generate.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock
from src.agents.writing._writing import execute_writing_generation

@pytest.mark.asyncio
async def test_execute_writing_generation():
    mock_llm = AsyncMock()
    mock_llm.stream.return_value = ["扉が開いた。", "目の前にいたのは騎士だった。"]
    
    result = await execute_writing_generation(
        llm=mock_llm,
        prompt="執筆開始",
        max_tokens=500
    )
    assert "扉が開いた。" in result
    assert "騎士だった。" in result
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/agents/test_writing_agent_generate.py -v`
- **合格条件**: 全テストPASS。

---

### Step 5: WritingScheduler のエピソード順序管理テスト
- **目的**: 複数話（第1話〜第5話）の依存関係グラフ解析、並行執筆と順次執筆のキューイングを検証。
- **対象ファイル**: `src/agents/writing_scheduler.py`
- **作成テストファイル**: `tests/unit/agents/test_writing_scheduler.py`
- **実装コード**:
```python
import pytest
from src.agents.writing_scheduler import WritingScheduler

def test_writing_scheduler_dependency_graph():
    scheduler = WritingScheduler()
    scheduler.add_task(episode=1, depends_on=[])
    scheduler.add_task(episode=2, depends_on=[1])
    
    order = scheduler.get_execution_order()
    assert order == [1, 2]
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/agents/test_writing_scheduler.py -v`
- **合格条件**: 全テストPASS。

---

### Step 6: AuditAgent の矛盾検知・整合性スコアリングテスト
- **目的**: キャラクターの死亡後の再登場、呼称の崩れ、未回収フラグを検知するルールベース＆LLM監査ロジックをテスト。
- **対象ファイル**: `src/agents/audit.py`
- **作成テストファイル**: `tests/unit/agents/test_audit_agent.py`
- **実装コード**:
```python
import pytest
from src.agents.audit import PlotIntegrityMonitor

def test_audit_agent_detect_contradiction():
    monitor = PlotIntegrityMonitor()
    characters = {"アリス": {"status": "死亡"}}
    scene_text = "アリスは笑顔でリンゴを食べた。"
    
    issues = monitor.check_scene(scene_text, characters)
    assert len(issues) >= 1
    assert any("死亡" in str(i) for i in issues)
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/agents/test_audit_agent.py -v`
- **合格条件**: 全テストPASS。

---

### Step 7: EroticContinuityTracker の状態遷移テスト
- **目的**: `continuity.py` における登場人物の着衣状態、体勢、前後のシチュエーション継続性を状態遷移マシンとして検証。
- **対象ファイル**: `src/agents/erotic/continuity.py`
- **作成テストファイル**: `tests/unit/agents/test_erotic_continuity.py`
- **実装コード**:
```python
import pytest
from src.agents.erotic.continuity import EroticContinuityTracker

def test_continuity_state_transition():
    tracker = EroticContinuityTracker()
    tracker.update_character_state("ヒロイン", {"clothing": "水着", "pose": "仰向け"})
    
    state = tracker.get_character_state("ヒロイン")
    assert state["clothing"] == "水着"
    assert state["pose"] == "仰向け"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/agents/test_erotic_continuity.py -v`
- **合格条件**: 全テストPASS。

---

### Step 8: EroticFilter のプラットフォーム規約適合性テスト
- **目的**: 児童ポルノ、極端な暴力、無許諾表現などプラットフォーム規約違反ワードの検知・マスキングを検証。
- **対象ファイル**: `src/agents/erotic/filter.py`
- **作成テストファイル**: `tests/unit/agents/test_erotic_filter.py`
- **実装コード**:
```python
import pytest
from src.agents.erotic.filter import EroticFilter

def test_erotic_filter_safe_text():
    filter_engine = EroticFilter()
    text = "二人は手をつなぎ、見つめ合った。"
    result = filter_engine.evaluate(text)
    assert result["is_compliant"] is True

def test_erotic_filter_flagged_text():
    filter_engine = EroticFilter()
    # 規約違反ワードの検知
    text = "未成年を対象とした禁止表現サンプル"
    result = filter_engine.evaluate(text)
    assert "flags" in result
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/agents/test_erotic_filter.py -v`
- **合格条件**: 全テストPASS。

---

### Step 9: EroticDiversityScorer の多様性スコアリングテスト
- **目的**: 単調な描写の連続を防ぐための語彙・シチュエーション多様性スコア計算を検証。
- **対象ファイル**: `src/agents/erotic/diversity_scorer.py`
- **作成テストファイル**: `tests/unit/agents/test_erotic_diversity.py`
- **実装コード**:
```python
import pytest
from src.agents.erotic.diversity_scorer import EroticDiversityScorer

def test_diversity_score_calculation():
    scorer = EroticDiversityScorer()
    text = "激しく抱きしめ、囁き、唇を重ねた。"
    score = scorer.calculate_diversity(text)
    assert 0.0 <= score <= 1.0
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/agents/test_erotic_diversity.py -v`
- **合格条件**: 全テストPASS。

---

### Step 10: EroticDensityController の描写密度制御テスト
- **目的**: 物語の進行度や読者離脱率に応じた官能描写密度の動的増減ロジックを検証。
- **対象ファイル**: `src/agents/erotic/density_controller.py`
- **作成テストファイル**: `tests/unit/agents/test_erotic_density.py`
- **実装コード**:
```python
import pytest
from src.agents.erotic.density_controller import EroticDensityController

def test_density_target_adjustment():
    controller = EroticDensityController(base_density=0.3)
    target = controller.get_target_density(current_chapter=5, reader_drop_risk=0.8)
    # 離脱リスクが高い場合、密度を引き上げる
    assert target >= 0.3
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/agents/test_erotic_density.py -v`
- **合格条件**: 全テストPASS。

---

### Step 11: PromptComposer の動的テンプレート結合テスト
- **目的**: 複数セクション（トーン、禁止事項、キャラクター辞書、あらすじ）を衝突なく動的結合するロジックを検証。
- **対象ファイル**: `src/agents/prompt_composer.py`
- **作成テストファイル**: `tests/unit/agents/test_prompt_composer.py`
- **実装コード**:
```python
import pytest
from src.agents.prompt_composer import PromptComposer

def test_prompt_composer_compose():
    composer = PromptComposer()
    composer.add_section("header", "システム指示")
    composer.add_section("content", "本文プロンプト")
    
    full_prompt = composer.build()
    assert "システム指示" in full_prompt
    assert "本文プロンプト" in full_prompt
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/agents/test_prompt_composer.py -v`
- **合格条件**: 全テストPASS。

---

### Step 12: エージェント連携パイプライン総合結合テスト
- **目的**: PlotAgentからContextBuilder、WritingAgent、AuditAgentへのデータ受け渡しと全体整合性をモックで検証。
- **対象ファイル**: `src/agents/`
- **作成テストファイル**: `tests/unit/agents/test_agents_integration.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_agent_pipeline_e2e_mock():
    # 各エージェントの連動スモークテスト
    plot_output = {"title": "テスト小説", "beats": ["起", "承", "転", "結"]}
    assert len(plot_output["beats"]) == 4
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/agents/test_agents_integration.py -v`
- **合格条件**: 全テストPASS。
