from fastapi import APIRouter, Depends

from src.backend.auth import get_current_user, validate_api_key_sync
from src.backend.database.models import User
from src.backend.database.uow import UnitOfWork
from src.backend.engine_helpers import get_engine as resolve_engine
from src.backend.security.owner_guard import verify_book_ownership
from src.backend.task_helpers import create_task as _create_task
from src.backend.database.models_foreshadowing import ForeshadowingModel
from src.core.container import AppContainer
from src.core.exceptions import AppError
from src.core.observability import TraceContext
from src.core.llm_gateway import LLMGateway
from src.models.api_schemas import (
    AuditPlanRequest,
    PlanGenerationRequest,
    PlotExpandCandidatesRequest,
    PlotExpandRequest,
    PlotRebuildRequest,
    ReversePlotGenerateRequest,
    ExpandBeatsRequest,
    BeatItemSchema,
)

# 商業ビート生成用システム指示
PLANNER_SYSTEM_INSTRUCTION = """あなたは商業Web小説の構成プロデューサーです。
企画パラメータに基づき、読者を引き込む12ステップのビートシート（五感フォーカス・クリフハンガー種別付き）を生成してください。
Save the Cat!のビートシート構成に準拠し、日本のWeb小説市場でヒットする構成を意識してください。"""

router = APIRouter(
    prefix="/api/plots",
    tags=["plots"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/{book_id}")
async def get_plots(book_id: int, current_user: User = Depends(get_current_user)):
    async with UnitOfWork(AppContainer.db()) as uow:
        await verify_book_ownership(book_id, current_user, uow)
        plots = await uow.plots.get_all_plots(book_id)
    return [
        {
            "ep_num": p.ep_num,
            "title": p.title,
            "summary": p.summary,
            "detailed_blueprint": p.detailed_blueprint,
            "tension": p.tension,
            "is_catharsis": p.is_catharsis,
            "status": p.status,
        }
        for p in plots
    ]


def generate_task_id(prefix: str) -> str:
    import uuid

    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@router.post("/plan_generation")
async def plan_generation(
    req: PlanGenerationRequest,
    current_user: User = Depends(get_current_user),
):
    if req.api_key:
        validate_api_key_sync(req.api_key)
    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("plan_gen")
    await _create_task(task_id, "企画作成を開始中...", total_steps=1)
    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="plan_generation_workflow",
        kwargs={"params": req.params},
        trace_id=TraceContext.get_trace_id(),
    )
    return {"task_id": task_id}


@router.post("/expand")
async def expand_plots(
    req: PlotExpandRequest,
    current_user: User = Depends(get_current_user),
):
    if req.api_key:
        validate_api_key_sync(req.api_key)
    await verify_book_ownership(req.book_id, current_user, AppContainer.db())
    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("plot_expand")
    await _create_task(
        task_id, "プロット作成を開始中...", total_steps=req.gen_to - req.gen_from + 1
    )
    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="plot_expansion_workflow",
        kwargs={
            "book_id": req.book_id,
            "gen_from": req.gen_from,
            "gen_to": req.gen_to,
            "mode": "final",
        },
        trace_id=TraceContext.get_trace_id(),
    )
    return {"task_id": task_id}


@router.post("/expand_candidates")
async def expand_plots_candidates(
    req: PlotExpandCandidatesRequest,
    current_user: User = Depends(get_current_user),
):
    if req.api_key:
        validate_api_key_sync(req.api_key)
    await verify_book_ownership(req.book_id, current_user, AppContainer.db())
    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("plot_candidates")
    await _create_task(
        task_id, "プロット候補案を生成中...", total_steps=req.gen_to - req.gen_from + 1
    )
    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="plot_expansion_workflow",
        kwargs={
            "book_id": req.book_id,
            "gen_from": req.gen_from,
            "gen_to": req.gen_to,
            "mode": "candidates",
        },
        trace_id=TraceContext.get_trace_id(),
    )
    return {"task_id": task_id}


@router.post("/rebuild")
async def rebuild_plots(
    req: PlotRebuildRequest,
    current_user: User = Depends(get_current_user),
):
    if req.api_key:
        validate_api_key_sync(req.api_key)
    import json
    import time

    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("plot_rebuild")
    db = AppContainer.db()
    initial_state = {
        "is_running": True,
        "current_step": 0,
        "total_steps": 1,
        "message": "プロット再構築を開始中...",
        "sub_message": "キューの待機中",
        "streaming_text": "",
        "logs": [f"[{time.strftime('%H:%M:%S')}] 🚀 プロット再構築タスクを登録しました。"],
        "error": None,
        "result_data": None,
        "token_usage": {"prompt": 0, "completion": 0, "calls": 0},
        "start_time": time.time(),
        "last_updated": time.time(),
    }
    await db.save_internal_state(
        f"task_status:{task_id}", json.dumps(initial_state), time.strftime("%Y-%m-%d %H:%M:%S")
    )
    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="plot_rebuild_workflow",
        kwargs={"params": req.params},
        trace_id=TraceContext.get_trace_id(),
    )
    return {"task_id": task_id}


@router.post("/audit")
async def audit_plan(
    req: AuditPlanRequest,
    current_user: User = Depends(get_current_user),
):
    if req.api_key:
        validate_api_key_sync(req.api_key)
    engine = resolve_engine(req.api_key)
    res = await engine.planner.audit_producer_plan(
        req.genre,
        req.keywords,
        req.trend_memo,
        sanctuary=req.sanctuary,
        originality_score=req.originality_score,
        platform=req.platform,
    )
    if not res:
        raise AppError("Audit failed")
    return {
        "refined_keywords": res.refined_keywords,
        "refined_concept": res.refined_concept,
        "refined_mc_suggestion": res.refined_mc_suggestion,
        "recommended_tropes": res.recommended_tropes,
        "candidates": [c.model_dump() for c in res.candidates],
    }


@router.post("/reverse-generate")
async def reverse_generate_plot(
    req: ReversePlotGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """逆算プロットビルダーからの回答を受け、プロット構造を生成"""
    if req.api_key:
        validate_api_key_sync(req.api_key)
    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("reverse_plot")
    await _create_task(task_id, "逆算プロット構造を生成中...", total_steps=3)
    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="reverse_plot_generation_workflow",
        kwargs={
            "answers": req.answers,
            "target_episodes": req.target_episodes,
            "genre": req.genre,
        },
        trace_id=TraceContext.get_trace_id(),
    )
    return {"task_id": task_id}


@router.post("/wizard-save")
async def wizard_save(
    req: ExpandBeatsRequest,
    current_user: User = Depends(get_current_user),
):
    """ウィザードで作成した企画とビートシートをDBに保存する"""
    if req.api_key:
        validate_api_key_sync(req.api_key)

    from src.backend.database.models import Book

    async with UnitOfWork(AppContainer.db()) as uow:
        # 新規Bookを作成
        book = Book(
            user_id=getattr(current_user, "id", None),
            title=req.title,
            genre=req.genre,
            concept="",
            synopsis=req.synopsis,
            target_eps=req.target_chapters,
        )
        uow.session.add(book)
        await uow.session.flush()
        book_id = book.id

        # ビートシートをPlotとして保存
        beats = req.beats if req.beats else []
        for i, beat in enumerate(beats, start=1):
            ep_num = beat.episode if beat.episode else i
            await uow.plots.create_or_replace_plot(
                book_id=book_id,
                ep_num=ep_num,
                thought_process="wizard_creation_funnel",
                title=beat.title,
                summary=beat.outline,
                # detailed_blueprint は各話ブループリント用のカラム。伏線メモは専用カラムへ.
detailed_blueprint="",
foreshadowing_notes=beat.foreshadowing_notes or "",
                next_hook=beat.cliffhanger_type or "New Crisis",
                tension=50,
                status="open",
            )

            # 伏線メモが存在する場合は伏線ステートマシンテーブル（foreshadowings）へ登録
            if beat.foreshadowing_notes and beat.foreshadowing_notes.strip():
                fs = ForeshadowingModel(
                    book_id=book_id,
                    title=f"第{ep_num}話: {beat.title or '伏線'}",
                    description=beat.foreshadowing_notes.strip(),
                    planted_episode=ep_num,
                    status="planted",
                    scope="short_term" if ep_num <= 5 else "long_term",
                )
                uow.session.add(fs)

    return {"book_id": book_id, "branch_id": 1, "success": True}



@router.post("/expand-beats", response_model=list[BeatItemSchema])
async def expand_commercial_beats(
    req: ExpandBeatsRequest,
    current_user: User = Depends(get_current_user),
):
    """企画パラメータから商業12ステップビートシートを生成"""
    if req.api_key:
        validate_api_key_sync(req.api_key)

    llm = LLMGateway()
    prompt = f"""【作品タイトル】{req.title}
【ジャンル】{req.genre}
【あらすじ】{req.synopsis}
【目標話数】{req.target_chapters}
【チート度 (1-5)】{req.cheat_scale}
【成長曲線】{req.growth_curve}
【システム支援度 (0-100)】{req.system_assist}
【代償・リスク過酷度 (1-5)】{req.cost_severity}

上記の企画パラメータに基づき、商業Web小説として最適な「12ステップのビートシート（五感フォーカス・クリフハンガー種別付き）」を生成してください。
各ステップは以下の構造で出力してください：

```json
[
  {{
    "episode": 1,
    "title": "エピソードタイトル",
    "outline": "このエピソードで起こる出来事の詳細（3-5行）",
    "cliffhanger_type": "New Crisis | Shocking Truth | Quiet Foreshadowing",
    "sensory_focus": ["visual", "auditory", "olfactory", "tactile", "gustatory", "metaphor"],
    "foreshadowing_notes": "伏線メモ（あれば）"
  }},
  ...
]
```

クリフハンガー種別の使い分け:
- New Crisis: 新たな危機・敵の出現・予期せぬトラブル（アクション・サスペンス向き）
- Shocking Truth: 衝撃の真実・正体発覚・裏切り（ミステリー・どんでん返し向き）
- Quiet Foreshadowing: 静かな伏線・感情の変化・小さな違和感（心情・日常・伏線回収向き）

五感フォーカスは各話2-3種類をバランスよく配分してください。
12ステップ構成（Save the Cat準拠）:
1. Opening Image / 日常の提示
2. Theme Stated / テーマの提示
3. Set-Up / 主要キャラ・世界観の導入
4. Catalyst / 発端・きっかけ
5. Debate / 迷い・葛藤
6. Break into Two / 決意・旅立ち
7. B Story / サブプロット・仲間との出会い
8. Fun and Games / 約束された楽しみ・能力発揮
9. Midpoint / 中間地点・大きな転換
10. Bad Guys Close In / 逆境・追い詰められる
11. All Is Lost / 絶望・全てを失う
12. Dark Night of the Soul / 闇夜・内面の葛藤
（13話以降はクライマックス・決着へ）"""

    try:
        res = await llm.generate_text(
            purpose_or_request="planning",
            prompt=prompt,
            system_instruction=PLANNER_SYSTEM_INSTRUCTION,
            temp=0.7,
        )
        raw_text = getattr(res, "story_content", "") or getattr(res, "content", "") or ""
        import json

        try:
            cleaned = str(raw_text).strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()
            beats_data = json.loads(cleaned)
            # 12ステップに制限、空配列の場合はフォールバック
            if not beats_data:
                pass  # フォールバックへ
            else:
                return beats_data[:12]
        except Exception:
            # JSONパースエラーの場合はフォールバック
            pass
    except Exception:
        # LLM呼び出しエラーの場合はフォールバック
        pass

    # フォールバック: デフォルトの12ステップを返す
    default_beats = [
        {
            "episode": 1,
            "title": "日常の崩壊",
            "outline": f"主人公の平穏な日常が、突如として現れた異変によって崩れ去る。{req.genre}世界の日常風景の中で、運命の歯車が回り始める。",
            "cliffhanger_type": "New Crisis",
            "sensory_focus": ["visual", "auditory"],
            "foreshadowing_notes": "不穏な予兆",
        },
        {
            "episode": 2,
            "title": "運命の告知",
            "outline": "異変の正体が明かされ、主人公に使命が課せられる。拒否することもできるが、代償は大きい。",
            "cliffhanger_type": "Shocking Truth",
            "sensory_focus": ["tactile", "metaphor"],
            "foreshadowing_notes": "古い予言",
        },
        {
            "episode": 3,
            "title": "覚悟の決意",
            "outline": "葛藤の末、主人公は立ち向かうことを決意する。仲間との出会い、最初の装備・スキル獲得。",
            "cliffhanger_type": "Quiet Foreshadowing",
            "sensory_focus": ["visual", "gustatory"],
            "foreshadowing_notes": "師匠の言葉",
        },
        {
            "episode": 4,
            "title": "最初の試練",
            "outline": "旅立ち早々、予想以上の強敵と遭遇。チート能力（レベル{req.cheat_scale}）が初めて試される瞬間。",
            "cliffhanger_type": "New Crisis",
            "sensory_focus": ["auditory", "olfactory"],
            "foreshadowing_notes": "敵の弱点",
        },
        {
            "episode": 5,
            "title": "力の代償",
            "outline": "圧倒的な力を振るうほど、主人公の肉体・精神に負荷がかかる。{req.cost_severity}段階のリスクが顕在化。",
            "cliffhanger_type": "Shocking Truth",
            "sensory_focus": ["tactile", "metaphor"],
            "foreshadowing_notes": "禁忌の存在",
        },
        {
            "episode": 6,
            "title": "仲間との絆",
            "outline": "個性豊かな仲間たちと共に、最初の拠点を確保。サブプロット（恋愛・友情・因縁）が動き出す。",
            "cliffhanger_type": "Quiet Foreshadowing",
            "sensory_focus": ["visual", "auditory"],
            "foreshadowing_notes": "仲間の秘密",
        },
        {
            "episode": 7,
            "title": "無双の快進撃",
            "outline": f"{req.growth_curve}の真価を発揮し、次々と強敵を薙ぎ倒す。読者に爽快感を与える『約束された楽しみ』のフェーズ。",
            "cliffhanger_type": "New Crisis",
            "sensory_focus": ["visual", "gustatory"],
            "foreshadowing_notes": "影の黒幕",
        },
        {
            "episode": 8,
            "title": "中間地点の真実",
            "outline": "勝利の裏で、世界の根幹に関わる衝撃の事実が判明。主人公の存在意義が揺らぐ。",
            "cliffhanger_type": "Shocking Truth",
            "sensory_focus": ["olfactory", "metaphor"],
            "foreshadowing_notes": "世界の秘密",
        },
        {
            "episode": 9,
            "title": "追い詰められる",
            "outline": "黒幕の本格的な逆襲が始まる。仲間が離脱、拠点喪失、能力封印…絶体絶命のピンチ。",
            "cliffhanger_type": "New Crisis",
            "sensory_focus": ["auditory", "tactile"],
            "foreshadowing_notes": "最後の切り札",
        },
        {
            "episode": 10,
            "title": "全てを失って",
            "outline": "最愛のものを失い、主人公は奈落の底へ。チート能力さえ通用しない、真の絶望。",
            "cliffhanger_type": "Quiet Foreshadowing",
            "sensory_focus": ["visual", "metaphor"],
            "foreshadowing_notes": "過去の伏線回収",
        },
        {
            "episode": 11,
            "title": "闇夜の決意",
            "outline": "絶望の中で、主人公は真の強さ（{req.growth_curve}の完成形）に目覚める。内面の葛藤を乗り越え、最終決戦へ。",
            "cliffhanger_type": "Shocking Truth",
            "sensory_focus": ["tactile", "gustatory"],
            "foreshadowing_notes": "真の敵",
        },
        {
            "episode": 12,
            "title": "決戦の夜明け",
            "outline": "全ての伏線が回収され、クライマックスへ向かうラストスパート。読者の期待を超えるカタルシスを約束する。",
            "cliffhanger_type": "Quiet Foreshadowing",
            "sensory_focus": ["visual", "auditory", "metaphor"],
            "foreshadowing_notes": "エピローグへ",
        },
    ]
    return default_beats
