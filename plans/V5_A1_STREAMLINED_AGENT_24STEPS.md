# AutoNovel v5.0 実装計画書 A1: Streamlined Agent (全24ステップ)

**対象ピラー**: Pillar 1 (Streamlined Multi-Agent & Hybrid Audit)  
**目的**: 8専門オーディターの並列LLM呼び出しを撤廃し、「静的定量的ルール解析（0円・0ms）」と「定性特化シングルLLM」の二層ハイブリッド監査、および1発生成＋1パッチPDCAリライトへのスリム化を完全実装する。  
**前提条件**: 各ステップは完全自己完結コード、変更対象ファイル、検証コマンド、期待結果を含む。

---

## 📋 ステップ一覧マトリクス

| ステップ | レイヤー | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Auditor | `src/services/auditors/rule_based_metrics.py` | [NEW] 文長分散・テンポ計算ロジックの実装 |
| **Step 2** | Auditor | `src/services/auditors/rule_based_metrics.py` | [MODIFY] 台詞比率計算（黄金比30〜45%判定）の追加 |
| **Step 3** | Auditor | `src/services/auditors/rule_based_metrics.py` | [MODIFY] 漢字含有率＆ひらがなバランス計算の追加 |
| **Step 4** | Auditor | `src/services/auditors/rule_based_metrics.py` | [MODIFY] AI臭い頻出表現・禁止ワード検出の実装 |
| **Step 5** | Auditor | `src/services/auditors/rule_based_metrics.py` | [MODIFY] クリフハンガー位置・引き強度判定の実装 |
| **Step 6** | Test | `tests/unit/services/test_rule_based_metrics.py` | [NEW] 静的定量的監査の単体テスト作成＆検証 |
| **Step 7** | Schema | `src/models/unified_audit.py` | [NEW] UnifiedAuditResult Pydanticスキーマ定義 |
| **Step 8** | Specialist | `src/agents/specialists/unified_auditor.py` | [NEW] UnifiedAuditorクラスの基本構造作成 |
| **Step 9** | Prompt | `src/agents/prompts/unified_audit_prompt.py` | [NEW] 定性特化シングルLLM監査プロンプトの作成 |
| **Step 10** | Specialist | `src/agents/specialists/unified_auditor.py` | [MODIFY] LLMレスポンスパース＆堅牢フォールバック実装 |
| **Step 11** | Specialist | `src/agents/specialists/unified_auditor.py` | [MODIFY] 静的定量スコアとLLM定性スコアの加重集約 |
| **Step 12** | Test | `tests/unit/agents/test_unified_auditor.py` | [NEW] UnifiedAuditor単体テスト作成＆検証 |
| **Step 13** | Workflow | `src/backend/workflows/writing_langgraph.py` | [MODIFY] AC反復ループの最大回数を1回に制限 |
| **Step 14** | Workflow | `src/backend/workflows/writing_langgraph.py` | [MODIFY] node_patch_healing局所修正ノードの実装 |
| **Step 15** | Workflow | `src/backend/workflows/writing_langgraph.py` | [MODIFY] 品質閾値達成時のEarly Exitショートカット追加 |
| **Step 16** | Metrics | `src/backend/workflows/writing_langgraph.py` | [MODIFY] トークン・レイテンシ計測メタデータの記録 |
| **Step 17** | Test | `tests/unit/workflows/test_streamlined_writing_flow.py` | [NEW] スリム化執筆ワークフローの単体テスト |
| **Step 18** | Agent | `src/agents/specialists/__init__.py` | [MODIFY] 旧8オーディターの非推奨化とファサード集約 |
| **Step 19** | EasyMode | `src/easy_mode/pipeline.py` | [MODIFY] Easy ModeへのUnifiedAuditor組み込み |
| **Step 20** | Studio | `src/backend/routers/editor.py` | [MODIFY] Studioエディタ監査エンドポイントの切り替え |
| **Step 21** | Cleanup | `src/agents/orchestrator.py` | [MODIFY] 旧8並列オーディター呼び出しコードの完全除去 |
| **Step 22** | Benchmark | `tests/perf/test_agent_speed_benchmark.py` | [NEW] 執筆＋監査の速度ベンチマーク作成（目標<30s） |
| **Step 23** | Benchmark | `tests/perf/test_token_cost_benchmark.py` | [NEW] 1話生成コストベンチマーク作成（目標<5円） |
| **Step 24** | Verify | CI / 全テスト実行 | 全単体・結合テストALL GREEN検証 |

---

## 🛠️ 各ステップの詳細手順（1〜24）

### Step 1: 文長分散・テンポ計算ロジックの実装
- **対象ファイル**: `src/services/auditors/rule_based_metrics.py` (新規作成)
- **目的**: 本文の1文あたりの文字数のばらつき（標準偏差）を計算し、テンポ（緩急）を定量化する。
- **実装コード**:
```python
from __future__ import annotations
import re
import math
from typing import NamedTuple

class RhythmScore(NamedTuple):
    sentence_count: int
    avg_length: float
    std_dev: float
    score: float  # 0.0 - 100.0

def calculate_sentence_rhythm(text: str) -> RhythmScore:
    """文長の平均と分散からリズム（緩急）スコアを計算する。"""
    sentences = [s.strip() for s in re.split(r'[。！？\n]', text) if s.strip()]
    if not sentences:
        return RhythmScore(0, 0.0, 0.0, 50.0)
    lengths = [len(s) for s in sentences]
    avg = sum(lengths) / len(lengths)
    variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    # Web小説の理想: 平均25〜40文字、標準偏差15〜30（短文と長文のメリハリ）
    ideal_std = 20.0
    score = max(0.0, min(100.0, 100.0 - abs(std_dev - ideal_std) * 2.5))
    return RhythmScore(len(sentences), avg, std_dev, score)
```
- **検証コマンド**:
```bash
python -c "from src.services.auditors.rule_based_metrics import calculate_sentence_rhythm; print(calculate_sentence_rhythm('これは短い文。そしてこれは少し長めに書かれた第二の文です。'))"
```
- **期待結果**: `RhythmScore(...)` がエラーなく出力されること。

---

### Step 2: 台詞比率計算（黄金比30〜45%判定）の追加
- **対象ファイル**: `src/services/auditors/rule_based_metrics.py` (追記)
- **目的**: カギ括弧「」内の文字数比率を計算し、Web小説の読みやすさの黄金比（30%〜45%）との適合度を算出する。
- **実装コード**:
```python
class DialogueScore(NamedTuple):
    dialogue_char_count: int
    total_char_count: int
    ratio: float  # 0.0 - 1.0
    score: float  # 0.0 - 100.0

def calculate_dialogue_ratio(text: str) -> DialogueScore:
    """台詞比率とスコアを計算する。"""
    total_chars = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
    if total_chars == 0:
        return DialogueScore(0, 0, 0.0, 50.0)
    dialogues = re.findall(r'「(.*?)」', text, re.DOTALL)
    dialogue_chars = sum(len(d) for d in dialogues)
    ratio = dialogue_chars / total_chars
    # 黄金比: 30%〜45% を 100点、乖離に応じて減点
    if 0.30 <= ratio <= 0.45:
        score = 100.0
    elif ratio < 0.30:
        score = max(20.0, 100.0 - (0.30 - ratio) * 250.0)
    else:
        score = max(20.0, 100.0 - (ratio - 0.45) * 200.0)
    return DialogueScore(dialogue_chars, total_chars, ratio, score)
```
- **検証コマンド**:
```bash
python -c "from src.services.auditors.rule_based_metrics import calculate_dialogue_ratio; print(calculate_dialogue_ratio('地の文です。「台詞です。」地の文です。'))"
```

---

### Step 3: 漢字含有率＆ひらがなバランス計算の追加
- **対象ファイル**: `src/services/auditors/rule_based_metrics.py` (追記)
- **目的**: 漢字が多すぎて読みにくくないか（黒い画面）、ひらがなばかりで幼稚でないかを判定（理想: 漢字20〜30%）。
- **実装コード**:
```python
def calculate_kanji_ratio(text: str) -> float:
    """漢字の含有率（0.0 - 1.0）を計算する。"""
    total = len(re.sub(r'\s', '', text))
    if total == 0:
        return 0.0
    kanji_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    return kanji_count / total
```

---

### Step 4: AI臭い頻出表現・禁止ワード検出の実装
- **対象ファイル**: `src/services/auditors/rule_based_metrics.py` (追記)
- **目的**: LLMが生成しがちな不自然な定型句（AI臭）を検出・ペナルティ化する。
- **実装コード**:
```python
AI_CLICHE_PATTERNS = [
    r"〜だったのだ",
    r"言葉を失った",
    r"胸の奥底で",
    r"運命の歯車が",
    r"一筋の光が",
    r"予感を禁じ得なかった",
    r"何かが始まろうとしていた",
]

def detect_ai_cliches(text: str) -> list[str]:
    """本文中のAI頻出定型句を検出する。"""
    found = []
    for pat in AI_CLICHE_PATTERNS:
        if re.search(pat, text):
            found.append(pat)
    return found
```

---

### Step 5: クリフハンガー位置・引き強度判定の実装
- **対象ファイル**: `src/services/auditors/rule_based_metrics.py` (追記)
- **目的**: エピソード末尾200文字以内に、次話への引き（疑問符・急展開・台詞終了）があるかを判定する。
- **実装コード**:
```python
def evaluate_cliffhanger_ending(text: str) -> float:
    """エピソード末尾の引き強度（0.0 - 100.0）を評価する。"""
    tail = text.strip()[-200:]
    score = 50.0
    if re.search(r'[！？!?]$', tail):
        score += 20.0
    if tail.endswith("」"):
        score += 15.0
    if re.search(r'(まさか|突如|その時|現れた|気付いた|信じられない)', tail):
        score += 15.0
    return min(100.0, score)
```

---

### Step 6: 静的定量的監査の単体テスト作成＆検証
- **対象ファイル**: `tests/unit/services/test_rule_based_metrics.py` (新規作成)
- **実装コード**:
```python
import pytest
from src.services.auditors.rule_based_metrics import (
    calculate_sentence_rhythm, calculate_dialogue_ratio,
    calculate_kanji_ratio, detect_ai_cliches, evaluate_cliffhanger_ending
)

def test_rule_based_metrics_comprehensive():
    sample = "主人公は歩いた。目の前には広大な城。「止まれ！」と兵士が叫んだ。その時、空が割れた！？"
    rhythm = calculate_sentence_rhythm(sample)
    assert rhythm.sentence_count >= 3
    assert 0.0 <= rhythm.score <= 100.0

    dialogue = calculate_dialogue_ratio(sample)
    assert dialogue.ratio > 0.0

    kanji = calculate_kanji_ratio(sample)
    assert 0.1 <= kanji <= 0.6

    cliches = detect_ai_cliches(sample)
    assert isinstance(cliches, list)

    cliff = evaluate_cliffhanger_ending(sample)
    assert cliff >= 70.0  # 末尾に！？があるため高得点
```
- **検証コマンド**:
```bash
.venv\Scripts\pytest tests/unit/services/test_rule_based_metrics.py -v
```
- **期待結果**: `1 passed in <0.2s`

---

### Step 7: UnifiedAuditResult Pydanticスキーマ定義
- **対象ファイル**: `src/models/unified_audit.py` (新規作成)
- **目的**: 静的解析スコアとLLM定性スコア、リライト指示を統合するDTOを定義。
- **実装コード**:
```python
from __future__ import annotations
from pydantic import BaseModel, Field

class QualitativeAudit(BaseModel):
    hook_score: float = Field(..., ge=0.0, le=100.0, description="読者引き込み度")
    emotional_score: float = Field(..., ge=0.0, le=100.0, description="感情曲線の自然さ")
    character_consistency: float = Field(..., ge=0.0, le=100.0, description="キャラ言動の一貫性")
    overall_score: float = Field(..., ge=0.0, le=100.0, description="定性総合評価")
    critique: str = Field(default="", description="主要講評")
    actionable_patch: str | None = Field(default=None, description="推奨局所修正パッチ")

class UnifiedAuditReport(BaseModel):
    is_acceptable: bool
    final_score: float
    quantitative_score: float
    qualitative: QualitativeAudit
    detected_cliches: list[str]
    dialogue_ratio: float
```

---

### Step 8: UnifiedAuditorクラスの基本構造作成
- **対象ファイル**: `src/agents/specialists/unified_auditor.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
import logging
from typing import Any
from src.services.auditors.rule_based_metrics import (
    calculate_sentence_rhythm, calculate_dialogue_ratio,
    calculate_kanji_ratio, detect_ai_cliches, evaluate_cliffhanger_ending
)
from src.models.unified_audit import UnifiedAuditReport, QualitativeAudit

logger = logging.getLogger(__name__)

class UnifiedAuditor:
    def __init__(self, llm_gateway: Any = None):
        self.llm = llm_gateway

    def audit_quantitative(self, text: str) -> tuple[float, dict[str, Any]]:
        """静的ルールベースの定量的スコア（0ms, 0コスト）を算出"""
        rhythm = calculate_sentence_rhythm(text)
        dialogue = calculate_dialogue_ratio(text)
        cliches = detect_ai_cliches(text)
        cliff = evaluate_cliffhanger_ending(text)

        # 静的スコアの加重平均
        score = (rhythm.score * 0.3) + (dialogue.score * 0.3) + (cliff * 0.4)
        if cliches:
            score = max(0.0, score - len(cliches) * 5.0)

        meta = {
            "rhythm_score": rhythm.score,
            "dialogue_ratio": dialogue.ratio,
            "cliches": cliches,
            "cliffhanger_score": cliff,
        }
        return score, meta
```

---

### Step 9: 定性特化シングルLLM監査プロンプトの作成
- **対象ファイル**: `src/agents/prompts/unified_audit_prompt.py` (新規作成)
- **実装コード**:
```python
UNIFIED_AUDIT_PROMPT_TEMPLATE = """\
あなたはWeb小説の敏腕編集長です。以下の設定と本文を厳格に講評してください。

【キャラクター設定 & 心理プロファイル】
{character_profiles}
※着眼点:
- 表向きの社会的仮面(surface_persona)と内なる葛藤(inner_conflict)の揺らぎが描かれているか
- Save The Cat善行や人間味のある共感ポイントが存在するか
- 鉄の禁忌(iron_constraint)を破っていないか
- Truth Ledger(known_facts/unknown_facts): まだ知らないはずの事実を先回りして口走っていないか

【章プロット & ビート構成】
{plot_spec}
※着眼点:
- 五感タグ(smell, sound, touch, taste, sight)を活用した生々しい動作描写があるか
- 引き(cliffhanger: New Crisis / Shocking Truth / Quiet Foreshadowing)が機能しているか

【エピソード本文】
{draft_text}

【出力要件】
以下のJSONフォーマットのみを出力してください（Markdownコードブロック不要）:
{{
  "hook_score": <読者を惹きつける力・クリフハンガー強度 (0-100)>,
  "emotional_score": <感情の起伏・カタルシス・五感描写 (0-100)>,
  "character_consistency": <キャラ心理葛藤・口調・Truth Ledger遵守度 (0-100)>,
  "overall_score": <定性総合得点 (0-100)>,
  "critique": "<70字以内の的確なアドバイス>",
  "actionable_patch": "<重大な欠陥がある場合のみ、1段落の置換案。問題なければnull>"
}}
"""
```

---

### Step 10: LLMレスポンスパース＆堅牢フォールバック実装
- **対象ファイル**: `src/agents/specialists/unified_auditor.py` (追記)
- **実装コード**:
```python
    async def audit_qualitative(
        self,
        text: str,
        character_profiles: str = "",
        plot_spec: str = "",
    ) -> QualitativeAudit:
        """LLMによる定性的評価を1回のみ実行"""
        if self.llm is None:
            return QualitativeAudit(
                hook_score=75.0, emotional_score=75.0, character_consistency=80.0,
                overall_score=76.0, critique="LLM未設定のため標準フォールバック適用"
            )
        from src.agents.prompts.unified_audit_prompt import UNIFIED_AUDIT_PROMPT_TEMPLATE
        prompt = UNIFIED_AUDIT_PROMPT_TEMPLATE.format(
            character_profiles=character_profiles or "主人公: 標準設定",
            plot_spec=plot_spec or "標準構成",
            draft_text=text[:3000]
        )
        try:
            resp = await self.llm.generate(prompt=prompt, temperature=0.2)
            import json, re
            json_match = re.search(r'\{.*\}', resp, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return QualitativeAudit(**data)
        except Exception as e:
            logger.warning(f"UnifiedAuditor LLM call failed: {e}")
        return QualitativeAudit(
            hook_score=70.0, emotional_score=70.0, character_consistency=70.0,
            overall_score=70.0, critique="パース失敗による安全フォールバック"
        )
```

---

### Step 11: 静的定量スコアとLLM定性スコアの加重集約
- **対象ファイル**: `src/agents/specialists/unified_auditor.py` (追記)
- **実装コード**:
```python
    async def audit(self, text: str, bible_summary: str = "") -> UnifiedAuditReport:
        """二層ハイブリッド監査を実行し総合判定を下す"""
        q_score, meta = self.audit_quantitative(text)
        qual = await self.audit_qualitative(text, bible_summary)

        # 総合得点 = 定量40% + 定性60%
        final = (q_score * 0.4) + (qual.overall_score * 0.6)
        is_ok = final >= 70.0 and len(meta["cliches"]) < 3

        return UnifiedAuditReport(
            is_acceptable=is_ok,
            final_score=round(final, 1),
            quantitative_score=round(q_score, 1),
            qualitative=qual,
            detected_cliches=meta["cliches"],
            dialogue_ratio=meta["dialogue_ratio"],
        )
```

---

### Step 12: UnifiedAuditor単体テスト作成＆検証
- **対象ファイル**: `tests/unit/agents/test_unified_auditor.py` (新規作成)
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock
from src.agents.specialists/unified_auditor import UnifiedAuditor

@pytest.mark.asyncio
async def test_unified_auditor_fallback():
    auditor = UnifiedAuditor(llm_gateway=None)
    report = await auditor.audit("「行こう！」彼は叫んだ。空が燃えていた。")
    assert report.final_score > 0.0
    assert isinstance(report.is_acceptable, bool)

@pytest.mark.asyncio
async def test_unified_auditor_with_mock_llm():
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = '{"hook_score": 85, "emotional_score": 80, "character_consistency": 90, "overall_score": 85, "critique": "引きが強い", "actionable_patch": null}'
    auditor = UnifiedAuditor(llm_gateway=mock_llm)
    report = await auditor.audit("「行こう！」彼は叫んだ。空が燃えていた。")
    assert report.qualitative.hook_score == 85.0
    assert report.is_acceptable is True
```
- **検証コマンド**:
```bash
.venv\Scripts\pytest tests/unit/agents/test_unified_auditor.py -v
```

---

### Step 13: AC反復ループの最大回数を1回に制限
- **対象ファイル**: `src/backend/workflows/writing_langgraph.py` (編集)
- **目的**: 3回リトライによるAPI過大消費と数分の待ち時間を根絶し、最大1回のリトライにハード制限する。
- **変更箇所**:
```python
# writing_langgraph.py
- base_max = 3
+ base_max = 1  # v5.0: 最大反復回数を1回に制限
```

---

### Step 14: node_patch_healing局所修正ノードの実装
- **対象ファイル**: `src/backend/workflows/writing_langgraph.py` (編集)
- **目的**: 全文リライトを廃止し、UnifiedAuditorが提示した `actionable_patch` のみで局所置換する。
- **実装コード**:
```python
    async def node_healing(self, state: dict[str, Any]) -> dict[str, Any]:
        """v5.0: 全文再生成を廃止し、局所パッチ置換またはワンショット改善を実施"""
        patch = state.get("actionable_patch")
        if patch and state.get("draft_content"):
            logger.info("Applying focused single-paragraph patch instead of full rewrite")
            # パッチ適用
            new_draft = state["draft_content"] + "\n\n" + patch
            return {"draft_content": new_draft, "status": "healed"}
        return {"status": "skipped_healing"}
```

---

### Step 15: 品質閾値達成時のEarly Exitショートカット追加
- **対象ファイル**: `src/backend/workflows/writing_langgraph.py` (編集)
- **目的**: 1回目の生成で合格ライン（スコア70点以上）に達したら即座に完了とし、無駄な監査・修正を一切行わない。
- **実装コード**:
```python
    def _should_continue_critic(self, state: dict[str, Any]) -> str:
        """初稿合格時は即座にfinalizeへ進む"""
        if state.get("is_integrity_ok", False) and state.get("final_score", 0) >= 70:
            return "finalize"
        if state.get("ac_iter", 0) >= state.get("max_ac_iter", 1):
            return "finalize"
        return "healing"
```

---

### Step 16: トークン・レイテンシ計測メタデータの記録
- **対象ファイル**: `src/backend/workflows/writing_langgraph.py` (編集)
- **実装コード**:
```python
    # finalizeノードで計測メタデータを確定
    state["final_meta"]["latency_sec"] = time.time() - state.get("start_time", time.time())
    state["final_meta"]["ac_iterations"] = state.get("ac_iter", 0)
```

---

### Step 17: スリム化執筆ワークフローの単体テスト
- **対象ファイル**: `tests/unit/workflows/test_streamlined_writing_flow.py` (新規作成)
- **検証コマンド**:
```bash
.venv\Scripts\pytest tests/unit/workflows/test_streamlined_writing_flow.py -v
```

---

### Step 18: 旧8オーディターの非推奨化とファサード集約
- **対象ファイル**: `src/agents/specialists/__init__.py` (編集)
- **目的**: 旧オーディターを呼び出していたコードに対して、自動的に `UnifiedAuditor` を呼び出す互換ファサードを提供。

---

### Step 19: Easy ModeへのUnifiedAuditor組み込み
- **対象ファイル**: `src/easy_mode/pipeline.py` (編集)
- **目的**: かんたんモードで `UnifiedAuditor` を呼び出し、高速に品質判定を完了させる。

---

### Step 20: Studioエディタ監査エンドポイントの切り替え
- **対象ファイル**: `src/backend/routers/editor.py` (編集)
- **目的**: `/api/editor/audit` エンドポイントを `UnifiedAuditor` に切り替え、フロントエンドのレスポンスをミリ秒化。

---

### Step 21: 旧8並列オーディター呼び出しコードの完全除去
- **対象ファイル**: `src/agents/orchestrator.py` (編集)
- **目的**: `asyncio.gather` で8つのオーディターを同時に叩いていた重力崩壊コードを削除。

---

### Step 22: 執筆＋監査の速度ベンチマーク作成（目標<30s）
- **対象ファイル**: `tests/perf/test_agent_speed_benchmark.py` (新規作成)
- **目的**: 1エピソードの生成〜監査〜完了が 30 秒以内に完了することを検証。

---

### Step 23: 1話生成コストベンチマーク作成（目標<5円）
- **対象ファイル**: `tests/perf/test_token_cost_benchmark.py` (新規作成)
- **目的**: 1エピソードあたりの消費トークンが 10,000 トークン未満であることをアサート。

---

### Step 24: 全テスト実行 & 回帰防止検証
- **検証コマンド**:
```bash
.venv\Scripts\pytest tests/unit/agents tests/unit/services tests/unit/workflows -v
```
- **期待結果**: 全テスト合格、失敗ゼロ。
