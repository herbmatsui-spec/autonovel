import streamlit as st
import time
from typing import Any, Dict, List
from config import (
    STORY_ARCHETYPES, EASY_MODE_KEYWORDS_MAP, EASY_GENRES, 
    WIZARD_GENRE_OPTIONS, WIZARD_ARCHETYPE_LABELS, STYLE_DEFINITIONS,
    CHEAT_DESCRIPTIONS, COST_DESCRIPTIONS, COST_INPUT_FLASH, COST_OUTPUT_FLASH
)
from engine import UltimateHegemonyEngine, safe_run_async
from engine_service import HegemonyService
from background import run_in_background

def render_easy_mode(engine: UltimateHegemonyEngine) -> None:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                padding: 2rem; border-radius: 16px; margin-bottom: 1.5rem; text-align: center;">
        <h1 style="color: #e94560; font-size: 2.2rem; margin: 0;">⚔️ 覇権小説エンジン</h1>
        <p style="color: #a8b2c1; margin: 0.5rem 0 0 0; font-size: 1.1rem;">
            ジャンルを選んでボタンを押すだけ。AIが初心者でもカクヨムランキング上位を狙える作品を自動生成します。
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("① どんなジャンルの小説を書きますか？")
    selected_genre_key = st.session_state.get("easy_genre_key", list(EASY_GENRES.keys())[0])

    # 提案1: 強化されたアーキタイプ選択と詳細プレビュー
    archetype_options = list(EASY_GENRES.keys())
    selected_archetype_index = archetype_options.index(selected_genre_key)
    
    # 選択ボックスでアーキタイプを選択
    selected_genre_key = st.selectbox(
        "物語の方向性（アーキタイプ）を選択してください",
        options=archetype_options,
        index=selected_archetype_index,
        format_func=lambda x: f"{x} - {EASY_GENRES[x]['desc']}",
        key="easy_archetype_selector"
    )
    
    # 選択が変更されたらセッション状態を更新し、再実行
    if st.session_state.get("easy_genre_key") != selected_genre_key:
        st.session_state["easy_genre_key"] = selected_genre_key
        st.rerun()

    genre_info = EASY_GENRES[selected_genre_key]
    archetype_preset = STORY_ARCHETYPES.get(genre_info["archetype"], {})

    with st.expander("⚙️ 細かい設定"):
        # 提案5: スマートデフォルト設定
        default_target_eps = archetype_preset.get("default_target_eps", 50)
        default_word_count = archetype_preset.get("default_word_count", 2500)

        target_eps = st.number_input("目標話数", 10, 200, value=default_target_eps, step=5)
        # initial_limit は target_eps と同期させるため、UIからは隠すか、説明を明確にする
        # initial_limit = st.number_input("最初に生成するプロット数", 5, 50, 25)
        word_count = st.number_input("1話あたりの目標文字数", 1000, 5000, value=default_word_count, step=100)
        
        # 提案2: オプションの「コアアイデア」テキスト入力
        core_idea = st.text_area("あなたのアイデア（例: 主人公は実は猫だった）", 
                                 placeholder="ここに物語の核となるユニークなアイデアを書いてください（オプション）",
                                 height=100)

        # 提案6: ユーザーフレンドリーな「物語の雰囲気」スライダー
        tone_vibe_slider = st.slider("物語の雰囲気", -5, 5, 0, help="-5: 極めてシリアス/重厚, 0: 標準, +5: 極めてコミカル/軽快")
        # 内部のpassionパラメータにマッピング (例: -5 -> 0.2, 0 -> 0.6, +5 -> 1.0)
        passion_value = 0.6 + (tone_vibe_slider / 5) * 0.4 # 0.2 to 1.0

    # 提案4: 事前コスト＆時間見積もり表示
    estimated_tokens = (target_eps * word_count * 2) / 0.7 # ざっくりプロンプトと生成で2倍、日本語1文字0.7トークン
    estimated_cost_usd = (estimated_tokens * COST_INPUT_FLASH) + (estimated_tokens * COST_OUTPUT_FLASH)
    estimated_time_min = (target_eps * 60) / 60 # 1話あたり平均60秒と仮定
    st.info(f"💡 **推定コスト:** 約 ${estimated_cost_usd:.4f} | **推定時間:** 約 {estimated_time_min:.0f} 分")

    if st.button("🚀 全自動で覇権作品を生成する！", type="primary", use_container_width=True):
        service = HegemonyService(engine)
        # initial_limit を target_eps と同期させて、執筆中のプロット欠落を防ぐ
        job = run_in_background(
            service.full_auto_workflow, 
            genre=genre_info["genre"], 
            keywords=EASY_MODE_KEYWORDS_MAP.get(selected_genre_key, "チート"),
            archetype_key=genre_info["archetype"], 
            target_eps=target_eps, 
            initial_limit=target_eps, 
            word_count=word_count,
            concept=core_idea, # 提案2: コアアイデアを渡す
            tone_vibe=passion_value, # 提案6: 新しいスライダー値を渡す
        )
        st.session_state.active_job = job
        st.rerun()

def _wizard_step_indicator(current: int, total: int = 4) -> None:
    cols = st.columns(total)
    labels = ["① ジャンル", "② 主人公", "③ 物語設計", "④ 生成開始"]
    for i, (col, label) in enumerate(zip(cols, labels)):
        step_num = i + 1
        if step_num < current: col.markdown(f"<div style='text-align:center;color:#4caf50;font-weight:bold;'>✅ {label}</div>", unsafe_allow_html=True)
        elif step_num == current: col.markdown(f"<div style='text-align:center;color:#e94560;font-weight:bold;border-bottom:2px solid #e94560;'>▶ {label}</div>", unsafe_allow_html=True)
        else: col.markdown(f"<div style='text-align:center;color:#555;'>○ {label}</div>", unsafe_allow_html=True)
    st.divider()

def render_planning_wizard(engine: UltimateHegemonyEngine) -> None:
    st.header("📋 企画ウィザード")
    if "wizard" not in st.session_state:
        st.session_state.wizard = {
            "step": 1, "genre": "ファンタジー", "archetype": "王道ざまぁ（爽快感最大）", 
            "keywords": "追放, チート, ざまぁ", "style_key": "style_web_standard", 
            "cheat_scale": 4, "cost_severity": 2, "system_assist": 70,
            "target_eps": 50, "initial_limit": 25, "mc_concept": "", "villain_concept": "",
            "audit_result": None
        }
    w = st.session_state.wizard
    _wizard_step_indicator(w["step"])

    if w["step"] == 1:
        col1, col2 = st.columns(2)
        with col1:
            w["genre"] = st.selectbox("📚 ジャンル", WIZARD_GENRE_OPTIONS, index=WIZARD_GENRE_OPTIONS.index(w["genre"]))
            w["keywords"] = st.text_area("🔑 キーワード", value=w["keywords"], height=100)
        with col2:
            st.write("**📦 物語の型**")
            selected_label = st.selectbox(
                "作品の方向性（アーキタイプ）を選択",
                options=list(WIZARD_ARCHETYPE_LABELS.values()),
                index=list(WIZARD_ARCHETYPE_LABELS.keys()).index(w["archetype"]) if w["archetype"] in WIZARD_ARCHETYPE_LABELS else 0
            )
            new_key = [k for k, v in WIZARD_ARCHETYPE_LABELS.items() if v == selected_label][0]
            if new_key != w["archetype"]:
                w["archetype"] = new_key
                preset = STORY_ARCHETYPES.get(new_key, {})
                w.update({k: preset[k] for k in ["style_key", "cheat_scale", "cost_severity", "system_assist"] if k in preset})
                st.rerun()
        if st.button("次へ → STEP 2", type="primary", use_container_width=True):
            w["step"] = 2; st.rerun()

    elif w["step"] == 2:
        st.subheader("STEP 2: キャラクター設定")
        col1, col2 = st.columns(2)
        with col1: w["mc_concept"] = st.text_area("🦸 主人公像", value=w["mc_concept"], height=200, placeholder="例: 追放されたが実は最強の魔導具師...")
        with col2: w["villain_concept"] = st.text_area("😈 敵対者像", value=w["villain_concept"], height=200, placeholder="例: 主人公を裏切った傲慢な勇者...")
        c1, c2 = st.columns(2)
        if c1.button("⬅️ 戻る"): w["step"] = 1; st.rerun()
        if c2.button("次へ → STEP 3", type="primary"): w["step"] = 3; st.rerun()

    elif w["step"] == 3:
        st.subheader("STEP 3: 物語の詳細設計")
        col1, col2 = st.columns(2)
        with col1:
            w["target_eps"] = st.number_input("目標話数", 10, 200, w["target_eps"])
            w["initial_limit"] = st.number_input("初期プロット数", 1, 50, w["initial_limit"])
            w["style_key"] = st.selectbox("文体スタイル", list(STYLE_DEFINITIONS.keys()), format_func=lambda k: STYLE_DEFINITIONS[k]["name"])
        with col2:
            w["cheat_scale"] = st.slider("チート強度", 0, 5, w["cheat_scale"])
            w["cost_severity"] = st.slider("能力の代償", 0, 5, w["cost_severity"])
            w["system_assist"] = st.slider("システム補助率 (%)", 0, 100, w["system_assist"])
        c1, c2 = st.columns(2)
        if c1.button("⬅️ 戻る"): w["step"] = 2; st.rerun()
        if c2.button("次へ → STEP 4", type="primary"): w["step"] = 4; st.rerun()

    elif w["step"] == 4:
        st.subheader("STEP 4: 最終確認とAI診断")
        if st.button("🧐 AIプロデューサー診断を実行"):
            with st.spinner("診断中..."):
                w["audit_result"] = safe_run_async(engine.audit_producer_plan(w["genre"], w["keywords"], f"{w['mc_concept']}\n{w['villain_concept']}"))
                st.rerun()
        
        if w["audit_result"]:
            audit = w["audit_result"]
            with st.container(border=True):
                st.success("🎯 AI診断完了")
                
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"**推奨キーワード:** {audit.refined_keywords}")
                if c2.button("反映", key="ref_kws"):
                    w["keywords"] = audit.refined_keywords; st.rerun()

                c1, c2 = st.columns([4, 1])
                c1.markdown(f"**ブラッシュアップ案:** {audit.refined_concept}")
                if c2.button("反映", key="ref_concept"):
                    w["concept"] = audit.refined_concept; st.rerun()

                c1, c2 = st.columns([4, 1])
                c1.markdown(f"**主人公像の提案:** {audit.refined_mc_suggestion}")
                if c2.button("反映", key="ref_mc"):
                    w["mc_concept"] = audit.refined_mc_suggestion; st.rerun()
                
                st.markdown(f"**推奨トロープ:** {', '.join(audit.recommended_tropes)}")

        if st.button("🚀 覇権企画を生成開始！", type="primary", use_container_width=True):
            _launch_plan_generation(engine, w)

def render_planning_tab(engine: UltimateHegemonyEngine) -> None:
    mode = st.radio("入力モード", ["🧙 ウィザード", "⚙️ 詳細設定"], horizontal=True)
    if "ウィザード" in mode: render_planning_wizard(engine)
    else: render_planning_detail(engine)

def render_planning_detail(engine: UltimateHegemonyEngine) -> None:
    st.header("📋 企画詳細設定")
    with st.form("detail_plan_form"):
        col1, col2 = st.columns(2)
        with col1:
            genre = st.selectbox("ジャンル", WIZARD_GENRE_OPTIONS)
            keywords = st.text_area("キーワード", "追放, チート, ざまぁ")
            target_eps = st.number_input("目標話数", 10, 200, 50)
        with col2:
            archetype = st.selectbox("アーキタイプ", list(STORY_ARCHETYPES.keys()))
            style_key = st.selectbox("文体スタイル", list(STYLE_DEFINITIONS.keys()), format_func=lambda k: STYLE_DEFINITIONS[k]["name"])
            initial_limit = st.number_input("初期生成話数", 1, 50, 25)
        
        if st.form_submit_button("🚀 企画生成開始", type="primary", use_container_width=True):
            params = {
                "genre": genre, "keywords": keywords, "style_key": style_key, 
                "target_eps": target_eps, "initial_limit": initial_limit, "cheat_scale": 4, "system_assist": 70, "cost_severity": 2
            }
            _launch_plan_generation(engine, params)

def _launch_plan_generation(engine: UltimateHegemonyEngine, w: Dict[str, Any]) -> None:
    service = HegemonyService(engine)
    job = run_in_background(service.plan_generation_workflow, params=w)
    st.session_state.active_job = job
    if "wizard" in st.session_state: del st.session_state["wizard"]
    st.rerun()