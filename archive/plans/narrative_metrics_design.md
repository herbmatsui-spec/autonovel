# Narrative Metrics (定量的指標) 設計ドキュメント

## 1. 概要
物語の「質」を定量化し、データに基づいた編集（Narrative Direction）を可能にするための指標システム。
シーンごとの数値をグラフ化し、緊張感の波やカタルシスの配置を客観的に分析する。

## 2. 指標定義（ルーブリック）

### 2.1 緊張感 (Tension)
物語の心理的・物理的なプレッシャー、対立、危機のレベル。
- **0**: 完全な平穏。日常的な会話、休息。
- **20-40**: 緩やかな不穏感。小さな違和感。
- **50-70**: 明確な対立や競争。精神的な負荷。
- **80-90**: 危機的状況。絶体絶命、激しい衝突。
- **100**: クライマックス。極限状態。

### 2.2 感情的充足度 (Emotional Satisfaction)
読者がキャラクターに共感し、カタルシスや期待したシーンが得られた度合い。
- **0**: 虚無感。冗長、期待の裏切り（悪い意味で）。
- **20-40**: わずかな進展。盛り上がりは少ない。
- **50-70**: 心地よい展開。成長、小さな成功、納得感のある対話。
- **80-90**: 強いカタルシス。伏線回収、関係性の進展。
- **100**: 完璧な充足。感情の最大化、深い感動。

### 2.3 謎の提示量 (Mystery Density)
物語への好奇心を牽引する「問い」や「未知の情報」の投入量。
- **0**: 全てが明確。整理のみ。
- **20-40**: 小さな疑問の提示。些細な違和感。
- **50-70**: 明確な謎の提示。主軸に関わる問い。
- **80-90**: 衝撃的な新事実の提示。前提を覆す謎。
- **100**: 根源的な謎の提示。物語全体の前提を揺るがす最大級のミステリー。

## 3. データモデル設計

### 3.1 DBスキーマ (`narrative_metrics`)
| Column | Type | Description |
|---|---|---|
| id | Integer (PK) | ユニークID |
| book_id | Integer (FK) | 作品ID |
| branch_id | Integer (FK) | ルート/枝ID |
| episode_num | Integer | エピソード番号 |
| scene_num | Integer | シーン番号（エピソード内順序） |
| metric_name | String | 指標名 (`tension`, `satisfaction`, `mystery` 等) |
| score | Integer | 0-100の数値 |
| reasoning | Text | LLMによるスコア根拠 |
| created_at | DateTime | 作成日時 |
| updated_at | DateTime | 更新日時 |

### 3.2 Pydanticモデル (`NarrativeMetricScore`)
```python
class NarrativeMetricScore(BaseModel):
    metric_name: str = Field(..., description="指標名")
    score: int = Field(..., ge=0, le=100, description="0-100のスコア")
    reasoning: str = Field(..., description="スコアを付けた具体的な根拠")
```
