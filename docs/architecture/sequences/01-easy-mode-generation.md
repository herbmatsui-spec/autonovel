# シーケンス図 - かんたんモード生成フロー

## 概要
ジャンル選択のみで、企画から完結まで全自動生成する「かんたんモード」のエンドツーエンドフロー。

```mermaid
sequenceDiagram
    autonumber
    actor User as ユーザー
    participant API as APIサーバー\n(FastAPI)
    participant Pipeline as EasyModePipeline
    participant BibleGen as BibleGenerator
    participant PlotGen as PlotGenerator
    participant EpWriter as EpisodeWriter
    participant EpAuditor as EpisodeAuditor
    participant EpRewriter as EpisodeRewriter
    participant Finalizer as SeriesFinalizer
    participant LLM as LLMゲートウェイ
    participant LLMClient as LLMクライアント\n(Gemini/OpenAI)
    participant SpiceGuard as SpiceGuard
    participant DB as データベース
    participant Redis as Redis
    participant ChromaDB as ChromaDB

    User->>API: POST /api/easy_mode/generate\n{genre: "zarma", target_eps: 8}
    API->>API: 認証・レート制限・トレースID設定
    API->>Pipeline: create_series(engine, "zarma", 8).run()
    
    Note over Pipeline: === Step 1: Bible生成 ===
    Pipeline->>BibleGen: generate(target_episodes=8)
    BibleGen->>BibleGen: プリセットから変数構築\n(episode_structure, style, hooks等)
    BibleGen->>LLM: generate_json(purpose="bible", prompt, variables)
    LLM->>LLMClient: get_client("gemini")
    LLMClient->>GeminiAPI: HTTPS generateContent
    GeminiAPI-->>LLMClient: JSON レスポンス
    LLMClient-->>LLM: 正規化済みレスポンス
    LLM-->>BibleGen: GenerateResult
    alt パース成功
        BibleGen->>BibleGen: JSON.parse() → Dict
    else パース失敗
        BibleGen->>BibleGen: fallback(variables) → Dict
    end
    BibleGen-->>Pipeline: Bible Dict
    
    Note over Pipeline: === Step 2: プロット生成 ===
    Pipeline->>PlotGen: generate(bible)
    PlotGen->>PlotGen: テンション曲線から補間\n展開パターン選択 (opening/catharsis/development/climax/resolution)
    PlotGen-->>Pipeline: List[PlotDict] (8話分)
    
    Note over Pipeline: === Step 3: 各話生成ループ (1〜8話) ===
    loop 8回 (ep_num: 1..8)
        Pipeline->>Pipeline: _build_prev_context()\n直近3話の要約構築
        
        Note over Pipeline,EpWriter: --- 執筆 ---
        Pipeline->>EpWriter: write(ep_num, bible, plot, prev_context)
        EpWriter->>EpWriter: プロンプト構築\n(Style DNA, Hooks, Erotic Rules 注入)
        EpWriter->>LLM: generate_text(purpose="writing", prompt)
        LLM->>LLMClient: get_client(model)
        LLMClient->>GeminiAPI: HTTPS generateContent
        GeminiAPI-->>LLMClient: テキストレスポンス
        LLMClient-->>LLM: 正規化済みレスポンス
        LLM-->>EpWriter: コンテンツ文字列
        EpWriter-->>Pipeline: コンテンツ
        
        Note over Pipeline,EpAuditor: --- 監査 ---
        Pipeline->>EpAuditor: audit(content, bible, plot, ep_num, genre)
        EpAuditor->>Engine: engine.auditor.audit()
        Engine-->>EpAuditor: 監査結果 (score, issues, improvements)
        EpAuditor->>EpAuditor: スコア正規化 (1000点→100点)
        EpAuditor-->>Pipeline: AuditResult
        
        Note over Pipeline,EpRewriter: --- リライト (SpiceGuard付き) ---
        alt スコア < target_audit_score かつ max_rewrite未達
            Pipeline->>EpRewriter: extract_spice(content)
            EpRewriter->>SpiceGuard: extract_spice(content)
            SpiceGuard->>SpiceGuard: 普遍/ジャンル/キャラクター パターンで抽出
            SpiceGuard-->>EpRewriter: List[SpiceElement]
            EpRewriter->>EpRewriter: inject_markers() で SPICEマーカー注入
            EpRewriter->>EpRewriter: リライトプロンプト構築\n(改善指示 + SPICEマーカー付き原文)
            EpRewriter->>LLM: generate_text(purpose="rewrite", prompt)
            LLM->>LLMClient: get_client(model)
            LLMClient->>GeminiAPI: HTTPS generateContent
            GeminiAPI-->>LLMClient: 改善済みテキスト
            LLMClient-->>LLM: 正規化済みレスポンス
            LLM-->>EpRewriter: リライト済みコンテンツ
            EpRewriter->>EpRewriter: clean_markers() で SPICEマーカー除去
            EpRewriter-->>Pipeline: 最終コンテンツ
            Pipeline->>EpAuditor: 再監査 (ループ)
        end
        
        Pipeline->>DB: EpisodeResult 保存
    end
    
    Note over Pipeline,Finalizer: === Step 4: 完結処理 ===
    Pipeline->>Finalizer: finalize(bible, plot_outline, episodes)
    Finalizer->>Finalizer: 総文字数・平均スコア・タイトル・あらすじ生成
    Finalizer-->>Pipeline: メタデータ Dict
    
    Pipeline->>DB: SeriesResult 保存
    Pipeline-->>API: SeriesResult
    API-->>User: 200 OK\n{title, concept, episodes[], metadata}
```

## 主要メッセージフロー

| Step | Actor | Action | 同期/非同期 |
|------|-------|--------|-------------|
| 1 | User → API | 生成リクエスト | 同期 (HTTP) |
| 2 | API → Pipeline | パイプライン起動 | 同期 (インプロセス) |
| 3 | Pipeline → BibleGen | Bible生成 | 同期 |
| 4 | BibleGen → LLM → LLMClient → Gemini | LLM生成 | 同期 (タイムアウト付き) |
| 5 | Pipeline → PlotGen | プロット生成 | 同期 (テンプレートベース) |
| 6 | Loop: Pipeline → EpWriter → LLM → Gemini | 執筆 | 同期 |
| 7 | Pipeline → EpAuditor → Engine.auditor | 監査 | 同期 |
| 8 | Pipeline → EpRewriter → SpiceGuard → LLM | リライト | 同期 (最大3回) |
| 9 | Pipeline → Finalizer | 完結処理 | 同期 |
| 10 | Pipeline → DB | 結果永続化 | 同期 (トランザクション) |
| 11 | API → User | 結果返却 | 同期 (HTTP) |

## エラーハンドリング・リトライ

- **LLM生成失敗**: 指数バックオフで最大3回リトライ (`RetryConfig`)
- **Bible生成失敗**: フォールバックBibleで継続 (メタデータに失敗理由記録)
- **監査エラー**: デフォルトスコア85で継続
- **リライト失敗**: 元コンテンツで継続
- **キャンセル**: `_cancelled` フラグで即座に中断、空 SeriesResult 返却

## 並行制御

- `concurrency_semaphore` (Factory で遅延生成) で全 LLM 呼び出しをグローバル制御
- `max_concurrent_api_calls` (設定値、デフォルト5) で同時実行数制限