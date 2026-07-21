import time
from typing import Any, Dict

import streamlit as st

from config import (
    COST_INPUT_FLASH,
    COST_OUTPUT_FLASH,
    EASY_GENRES,
    EASY_MODE_KEYWORDS_MAP,
    STORY_ARCHETYPES,
    STYLE_DEFINITIONS,
)
from src.core.plugin_loader import PluginLoader
from streamlit_app.controllers.manager import UIControllerManager
from streamlit_app.event_bus import UIEventType
from streamlit_app.proxy import UltimateHegemonyEngineProxy as UltimateHegemonyEngine
from streamlit_app.state import UIStateStore


def render_easy_mode(state: Any, engine: UltimateHegemonyEngine) -> None:
    # スケルトンローディングのシミュレーション
    if not UIStateStore().ui_state.form_data.get("easy_mode_loaded", False):
        with st.container():
            st.markdown('<div class="skeleton-header skeleton-fade-in"></div>', unsafe_allow_html=True)
            st.markdown('<div class="skeleton-text skeleton-fade-in"></div>', unsafe_allow_html=True)
            st.markdown('<div class="skeleton-card skeleton-fade-in"></div>', unsafe_allow_html=True)
        UIStateStore().update_ui_state(easy_mode_loaded=True)
        st.rerun()

    st.markdown("""
    <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #1a1a2e 100%);
                padding: 2rem; border-radius: 16px; margin-bottom: 1.5rem; text-align: center;">
        <h1 style="color: #e94560; font-size: 2.5rem; margin: 0; letter-spacing: 2px;">QUEST START</h1>
        <p style="color: #a8b2c1; margin: 0.5rem 0 0 0; font-size: 1.1rem;">
            ジャンルを選択し、あなたの物語の「核」をAIに伝えてください。
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("① どんなジャンルの小説を書きますか？")
    from streamlit_app.state import get_session
    session = get_session()
    nsfw_enabled = session.config.get("enable_nsfw", False)

    # NSFWが無効な場合は 'nsfw_only' のジャンルを除外
    archetype_options = [
        k for k, v in EASY_GENRES.items()
        if not v.get("nsfw_only", False) or nsfw_enabled
    ]

    selected_genre_key = getattr(state, "easy_genre_key", None) or archetype_options[0]
    if selected_genre_key not in archetype_options:
        selected_genre_key = archetype_options[0]

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
    if UIStateStore.get_runtime().easy_genre_key != selected_genre_key:
        UIStateStore.set_easy_genre(selected_genre_key)
        # L2: ジャンル変更はプリセットに影響するため、Fragment内再実行で十分（@st.fragment導入済みのため）

    genre_info = EASY_GENRES[selected_genre_key]
    # STORY_ARCHETYPESはconfig.pyの互換レイヤー経由でPluginLoaderから取得される
    archetype_preset = STORY_ARCHETYPES.get(genre_info["archetype"], {})

    from streamlit_app.ui.icons import ICON_SETTINGS
    with st.expander(f"{ICON_SETTINGS} 細かい設定"):
        # 提案5: スマートデフォルト設定
        default_target_eps = archetype_preset.get("default_target_eps", 50)
        default_word_count = archetype_preset.get("default_word_count", 2500)

        target_eps = st.number_input("目標話数", 10, 200, value=default_target_eps, step=5)
        initial_limit = st.number_input("最初に生成するプロット数", 5, 50, value=min(target_eps, 25))
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
    # 日本語1文字 ≒ 0.7トークン, 生成量はプロット+本文で概算2倍とする
    estimated_tokens = (target_eps * word_count * 2) / 0.7
    estimated_cost_usd = (estimated_tokens * COST_INPUT_FLASH) + (estimated_tokens * COST_OUTPUT_FLASH)
    estimated_time_min = (target_eps * 60) / 60 # 1話あたり平均60秒と仮定

    with st.container(border=True):
        st.markdown("#### 💰 生成コスト・時間の目安")
        col_c, col_t = st.columns(2)
        col_c.metric("推定コスト", f"${estimated_cost_usd:.4f}", help="Gemini 1.5 Flash の料金体系に基づいた概算です。")
        col_t.metric("推定時間", f"{estimated_time_min:.0f} 分", help="APIの生成速度に基づく概算です。")
        st.caption("※これはあくまで目安であり、実際の消費トークン量によって変動します。")

    if st.button("🚀 全自動で覇権作品を生成する！", type="primary", use_container_width=True):
        params = {
            "genre": genre_info["genre"],
            "keywords": EASY_MODE_KEYWORDS_MAP.get(selected_genre_key, "チート"),
            "archetype_key": genre_info["archetype"],
            "target_eps": target_eps,
            "initial_limit": initial_limit,
            "word_count": word_count,
            "concept": core_idea,
            "tone_vibe": passion_value,
        }
        UIControllerManager(engine).emit(UIEventType.REQUEST_GENERATE_PLAN, params)
        # L3: 生成開始は全域的な状態変更であり、プログレス表示への遷移が必要なため rerun
        st.rerun()

def _wizard_step_indicator(current: int, total: int = 4) -> None:
    # ステップインジケータをよりモダンな「進捗バー」スタイルに変更
    cols = st.columns(total)
    labels = ["ジャンル", "主人公", "物語設計", "生成開始"]

    for i, (col, label) in enumerate(zip(cols, labels)):
        step_num = i + 1
        if step_num < current:
            # 完了ステップ
            col.markdown(
                f"""<div style="text-align:center; color:#4caf50; font-weight:bold; font-size:0.9rem;">
                    <div style="margin-bottom:4px;">✅</div>{label}
                </div>""",
                unsafe_allow_html=True
            )
        elif step_num == current:
            # 現在のステップ（強調）
            col.markdown(
                f"""<div style="text-align:center; color:#e94560; font-weight:bold; font-size:1rem; border-bottom:3px solid #e94560; padding-bottom:4px;">
                    <div style="margin-bottom:4px;">🚀</div>{label}
                </div>""",
                unsafe_allow_html=True
            )
        else:
            # 未到達ステップ
            col.markdown(
                f"""<div style="text-align:center; color:#666; font-size:0.9rem;">
                    <div style="margin-bottom:4px; color:#444;">○</div>{label}
                </div>""",
                unsafe_allow_html=True
            )
    st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)
    st.divider()

    st.header("📋 企画ウィザード")

    # stateからwizard_stateを抽出（AppStateModel相当の辞書を想定）
    wizard_state = state.get("wizard", {})
    step = wizard_state.get("step", 1)
    w = wizard_state.get("data", {})

    if step == 1 and not w:
        w = {
            "genre": "ファンタジー", "archetype": "王道ざまぁ（爽快感最大）",
            "keywords": "追放, チート, ざまぁ", "style_key": "style_web_standard",
            "cheat_scale": 4, "cost_severity": 2, "system_assist": 70,
            "target_eps": 50, "initial_limit": 25, "concept": "", "mc_concept": "", "villain_concept": "",
            "audit_result": None,
            "sanctuary": "", "originality_score": 50, "platform": "カクヨム/なろう",
            "step": 1
        }
        UIStateStore.get().wizard.data = w
    _wizard_step_indicator(step)

    if w["step"] == 1:
        col1, col2 = st.columns(2)
        # プラグインから動的にジャンルとアーキタイプを取得する
        plugin = PluginLoader.get_instance().get_active_plugin()
        genre_options = [plugin.genre] if plugin else ["ファンタジー"]
        with col1:
            w["genre"] = st.selectbox("📚 ジャンル", genre_options, help="物語のベースとなるジャンルを選択してください。")
            w["keywords"] = st.text_area(
                "🔑 キーワード",
                value=w["keywords"],
                height=100,
                placeholder="例: 追放, チート, ざまぁ, 聖女, 辺境, スローライフ",
                help="AIに盛り込んでほしい要素をカンマ区切りで入力してください。"
            )
        with col2:
            st.write("**📦 物語の型 (アーキタイプ)**")

            # 提案: ビジュアルカード選択UIの実装
            plugin = PluginLoader.get_instance().get_active_plugin()
            archetypes_data = plugin.archetypes if plugin else {}

            # Lucide iconsの簡略化マッピング（実際はより広範な辞書が必要）
            icon_map = {
                "sword": "⚔️", "shield-alert": "🛡️", "history": "⏳", "coffee": "☕",
                "crown": "👑", "laugh": "😂", "paw-print": "🐾", "flask-conical": "🧪",
                "lightbulb": "💡", "chef-hat": "👨‍🍳", "zap": "⚡", "radio": "📻",
                "heart": "💖", "wrench": "🔧", "school": "🏫", "map": "🗺️",
                "cup-soda": "🥤", "sprout": "🌱", "plus-circle": "➕", "shopping-basket": "🧺",
                "user-check": "👤", "infinite": "♾️", "smile": "😎", "land-plot": "🚜",
                "dragon": "🐉", "shield": "🛡️", "skull": "💀", "book-open": "📖",
                "dices": "🎲", "music": "🎶", "moon": "🌙", "hammer": "🔨",
                "swords": "⚔️", "eye": "👁️", "fan": "🪭", "settings": "⚙️"
            }

            # 横3列でカードを表示
            cols = st.columns(3)
            selected_archetype = w["archetype"]

            for idx, (name, preset) in enumerate(archetypes_data.items()):
                with cols[idx % 3]:
                    # 選択されているかを確認
                    is_selected = (name == selected_archetype)
                    border_style = "2px solid #e94560" if is_selected else "1px solid #333"
                    bg_color = "#1a1a2e" if is_selected else "#0f0f1a"
                    icon_name = preset.visual_icon or '📝'
                    emoji = icon_map.get(icon_name, '📝')

                    # カードをボタンとして実装するために、st.buttonのラベルに情報を盛り込むか、
                    # またはボタンをカードの直下に配置する。
                    # StreamlitではHTML要素自体にクリックイベントを持たせることができないため、
                    # カード風の見た目のボタンを作成する。

                    # カードの外見を定義したHTML
                    st.markdown(f"""
                    <div style="border: {border_style}; border-radius: 8px; padding: 10px; background-color: {bg_color}; height: 180px; margin-bottom: -45px; pointer-events: none;">
                        <div style="text-align: center; font-size: 2.5rem; margin-bottom: 5px;">{emoji}</div>
                        <div style="font-weight: bold; text-align: center; margin-bottom: 5px; color: white;">{name}</div>
                        <div style="font-size: 0.8rem; color: #aaa; margin-bottom: 5px; height: 50px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">{preset.summary or ''}</div>
                        <div style="font-size: 0.7rem; color: #4caf50; text-align: center;">#{preset.trend_tag or ''}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    if st.button(f"✨ {name} を選択", key=f"select_arch_{name}", use_container_width=True):
                        w["archetype"] = name
                        w.update({k: getattr(preset, k) for k in ["style_key", "cheat_scale", "cost_severity", "system_assist"] if getattr(preset, k) is not None})
                        UIStateStore.update_wizard_data(w)

            selected_label = w["archetype"]
        if st.button("次へ → STEP 2", type="primary", use_container_width=True):
            UIStateStore.set_wizard_step(2)
            # L3: ステップ遷移は画面構成が大きく変わるため rerun
            st.rerun()

    elif w["step"] == 2:
        st.subheader("STEP 2: キャラクター設定")
        col1, col2 = st.columns(2)
        with col1:
            w["mc_concept"] = st.text_area(
                "🦸 主人公像",
                value=w["mc_concept"],
                height=150,
                placeholder="例: 追放されたが実は最強の魔導具師。控えめだが怒ると恐ろしい性格...",
                help="主人公の能力、性格、外見、目的などを具体的に記入してください。"
            )
            w["concept"] = st.text_area(
                "📖 コアコンセプト",
                value=w["concept"],
                height=100,
                placeholder="例: 主人公は実は猫だった / 100年後の世界に転生した",
                help="物語全体の「売り」となる、ユニークな設定やひねりを記入してください。"
            )
        with col2:
            w["villain_concept"] = st.text_area(
                "😈 敵対者像",
                value=w["villain_concept"],
                height=150,
                placeholder="例: 主人公を裏切った傲慢な勇者。権力に溺れ、真の価値が見えなくなっている...",
                help="主人公と対立する人物や勢力の特徴、および「なぜ対立するのか」を記入してください。"
            )
            w["sanctuary"] = st.text_area(
                "🔒 絶対に譲れないコア設定 (聖域)",
                value=w.get("sanctuary", ""),
                height=100,
                placeholder="例: 主人公の武器は折れた古びた剣で固定する、ヒロインは一切登場させない、等。",
                help="AIが絶対に改変してはいけない設定を記入してください。物語の整合性を守るための最優先事項となります。"
            )
        c1, c2 = st.columns(2)
        if c1.button("⬅️ 戻る"):
            UIStateStore.set_wizard_step(1)
            # L3: ステップ遷移は画面構成が大きく変わるため rerun
            st.rerun()
        if c2.button("次へ → STEP 3", type="primary"):
            UIStateStore.set_wizard_step(3)
            # L3: ステップ遷移は画面構成が大きく変わるため rerun
            st.rerun()

    elif w["step"] == 3:
        from streamlit_app.ui.icons import ICON_PLANNING
        st.subheader(f"{ICON_PLANNING} STEP 3: 物語の詳細設計")
        col1, col2 = st.columns(2)
        with col1:
            w["target_eps"] = st.number_input(
                "目標話数", 10, 200, w["target_eps"],
                help="完結までに見込むおおよその話数です。"
            )
            w["initial_limit"] = st.number_input(
                "初期プロット数", 1, 50, w["initial_limit"],
                help="最初にAIに生成させるプロット（エピソード案）の数です。多いほど選択肢が増えます。"
            )
            # STYLE_DEFINITIONSの構造に合わせて-descriptionなどを表示
            w["style_key"] = st.selectbox(
                "文体スタイル",
                list(STYLE_DEFINITIONS.keys()),
                format_func=lambda k: STYLE_DEFINITIONS[k].get("description", k),
                help="物語の語り口（一人称/三人称、硬め/柔らかめ等）を選択してください。"
            )

            from config.domain_profile_manager import DomainProfileService
            platforms = DomainProfileService.get_supported_platforms()
            w["platform"] = st.selectbox(
                "🎯 ターゲットプラットフォーム",
                platforms,
                index=platforms.index(w.get("platform", "カクヨム/なろう")) if w.get("platform", "カクヨム/なろう") in platforms else 0
            )
        with col2:
            # --- パラメータプリセットカード (提案6) ---
            from config.constants import PLANNING_PRESETS
            st.markdown("### ⚡ おすすめ設定プリセット")

            # プリセットを2列のカード形式で表示
            preset_cols = st.columns(2)
            for idx, (p_name, p_val) in enumerate(PLANNING_PRESETS.items()):
                with preset_cols[idx % 2]:
                    # カード風のデザインを再現するためのボタン
                    if st.button(f"{p_name}\n({p_val['desc']})", key=f"preset_{p_name}", use_container_width=True):
                        w["cheat_scale"] = p_val["cheat_scale"]
                        w["cost_severity"] = p_val["cost_severity"]
                        w["system_assist"] = p_val["system_assist"]
                        UIStateStore.update_wizard_data(w)
                        st.toast(f"✅ {p_name} 設定を適用しました")
                        # L2: プリセット適用はFragment内更新で十分

            st.divider()
            st.markdown(f"**{ICON_SETTINGS} 個別微調整**")
            w["cheat_scale"] = st.slider("チート強度", 0, 5, w["cheat_scale"])
            w["cost_severity"] = st.slider("能力の代償", 0, 5, w["cost_severity"])
            w["system_assist"] = st.slider("システム補助率 (%)", 0, 100, w["system_assist"])
            w["originality_score"] = st.slider(
                f"{ICON_AUDIT} 王道 ⇔ 独創性スライダー",
                0, 100,
                w.get("originality_score", 50),
                help="0%: 完全テンプレ(王道重視), 50%: ハイブリッド, 100%: 前衛的(芸術性/独自性重視)"
            )
        c1, c2 = st.columns(2)
        if c1.button("⬅️ 戻る"):
            UIStateStore.set_wizard_step(2)
            # L3: ステップ遷移は画面構成が大きく変わるため rerun
            st.rerun()
        if c2.button("次へ → STEP 4", type="primary"):
            UIStateStore.set_wizard_step(4)
            # L3: ステップ遷移は画面構成が大きく変わるため rerun
            st.rerun()

    elif w["step"] == 4:
        st.subheader("STEP 4: 最終確認とAI診断")
        if st.button("🧐 AIプロデューサー診断を実行"):
            with st.spinner("AIプロデューサー診断を実行中..."):
                payload = {
                    "genre": w.get("genre", "ファンタジー"),
                    "keywords": w.get("keywords", ""),
                    "concept": w.get("concept", ""),
                    "sanctuary": w.get("sanctuary", ""),
                    "originality_score": w.get("originality_score", 50),
                    "platform": w.get("platform", "カクヨム/なろう")
                }
                res = UIControllerManager(engine).emit(UIEventType.REQUEST_AUDIT_PLAN, payload)
                if res and res.get("data"):
                    w["audit_result"] = res["data"]
                    UIStateStore.get().wizard.data = w
                    st.toast("✅ AI診断結果をロードしました")
                else:
                    st.error("AI診断の実行に失敗しました。")
            # L3: 診断結果の反映はUI構造に影響するため rerun
            st.rerun()

        if w["audit_result"]:
            audit = w["audit_result"]
            with st.container(border=True):
                st.markdown("""
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 1rem;">
                        <div style="font-size: 1.5rem;">🎯</div>
                        <div style="font-weight: bold; font-size: 1.2rem; color: #4caf50;">AIプロデューサーによる診断結果</div>
                    </div>
                """, unsafe_allow_html=True)

                candidates = getattr(audit, "candidates", [])
                if candidates:
                    tab_names = []
                    for idx, c in enumerate(candidates):
                        ptype_label = {
                            "Trope": "王道",
                            "Hybrid": "ハイブリッド",
                            "Anti-Trope": "逆張り"
                        }.get(c.plan_type, "提案")
                        tab_names.append(f"{c.plan_name} ({ptype_label})")

                    tabs = st.tabs(tab_names)
                    for idx, tab in enumerate(tabs):
                        c = candidates[idx]
                        with tab:
                            # 提案のサマリーをカード風に表示
                            st.markdown(f"""
                                <div style="background-color: #1a1a2e; border: 1px solid #333; border-radius: 8px; padding: 15px; margin-bottom: 1.5rem;">
                                    <div style="font-size: 0.9rem; color: #aaa; margin-bottom: 5px;">プランタイプ: {ptype_label}</div>
                                    <div style="font-weight: bold; color: white; font-size: 1.1rem;">{c.plan_name}</div>
                                </div>
                            """, unsafe_allow_html=True)

                            if c.hybrid_idea:
                                with st.container(border=True):
                                    st.markdown(f"**💡 ハイブリッドアイデア**\n\n{c.hybrid_idea}")
                            if c.anti_tropes:
                                with st.container(border=True):
                                    st.markdown(f"**⚠️ 避けるべき定石 (アンチトロープ)**\n\n{', '.join(c.anti_tropes)}")

                            st.markdown("---")
                            st.markdown("#### 🛠️ 具体的改善案の反映")

                            # 反映セクションをグリッド形式に整理
                            ref_items = [
                                ("🔑 推奨キーワード", c.refined_keywords, "keywords", "キーワードを反映"),
                                ("📖 コンセプト案", c.refined_concept, "concept", "コンセプトを反映"),
                                ("🦸 主人公像案", c.refined_mc_suggestion, "mc_concept", "主人公像を反映"),
                                ("😈 敵対者像案", c.refined_villain_suggestion, "villain_concept", "敵対者像を反映"),
                            ]

                            for label, value, key, btn_text in ref_items:
                                with st.container(border=True):
                                    col_text, col_btn = st.columns([4, 1])
                                    col_text.markdown(f"**{label}**\n\n{value}")
                                    if col_btn.button(btn_text, key=f"ref_{key}_{idx}", use_container_width=True):
                                        w[key] = value
                                        UIStateStore.get().wizard.data = w
                                        st.toast(f"✅ {label}を反映しました")
                                        st.rerun()

                            st.markdown(f"**推奨トロープ:** {', '.join(c.recommended_tropes)}")
                else:
                    c1, c2 = st.columns([4, 1])
                    c1.markdown(f"**推奨キーワード:** {audit.refined_keywords}")
                    if c2.button("反映", key="ref_kws"):
                        w["keywords"] = audit.refined_keywords
                        UIStateStore.get().wizard.data = w
                        st.rerun()

                    c1, c2 = st.columns([4, 1])
                    c1.markdown(f"**ブラッシュアップ案:** {audit.refined_concept}")
                    if c2.button("反映", key="ref_concept"):
                        w["concept"] = audit.refined_concept
                        UIStateStore.get().wizard.data = w
                        st.toast("✅ コアコンセプトに反映しました")
                        st.rerun()

                    c1, c2 = st.columns([4, 1])
                    c1.markdown(f"**主人公像の提案:** {audit.refined_mc_suggestion}")
                    if c2.button("反映", key="ref_mc"):
                        w["mc_concept"] = audit.refined_mc_suggestion
                        UIStateStore.get().wizard.data = w
                        st.rerun()

                    st.markdown(f"**推奨トロープ:** {', '.join(audit.recommended_tropes)}")

        if st.button("🚀 覇権企画を生成開始！", type="primary", use_container_width=True):
            UIControllerManager(engine).emit(UIEventType.REQUEST_GENERATE_PLAN, w)
            st.rerun()

def render_planning_tab(state: Dict[str, Any], engine: UltimateHegemonyEngine) -> None:
    from streamlit_app.ui.components.widgets import render_section_header
    from streamlit_app.ui.icons import ICON_PLANNING, ICON_SETTINGS

    # スケルトンローディングのシミュレーション
    if not UIStateStore().ui_state.form_data.get("planning_tab_loaded", False):
        with st.container():
            st.markdown('<div class="skeleton-header skeleton-fade-in"></div>', unsafe_allow_html=True)
            st.markdown('<div class="skeleton-card skeleton-fade-in"></div>', unsafe_allow_html=True)
        UIStateStore().update_ui_state(planning_tab_loaded=True)
        st.rerun()

    mode = st.radio("入力モード", [f"{ICON_PLANNING} ウィザード", f"{ICON_SETTINGS} 詳細設定"], horizontal=True)

    if "ウィザード" in mode:
        render_planning_wizard(state, engine)
    else:
        render_section_header("企画詳細設定", "高度なパラメータを直接指定して企画を生成します", ICON_SETTINGS)

        with st.form("detail_plan_form"):
            col1, col2 = st.columns(2)
            with col1:
                plugin = PluginLoader.get_instance().get_active_plugin()
                genre_options = [plugin.genre] if plugin else ["ファンタジー"]
                genre = st.selectbox("ジャンル", genre_options, help="作品の基本ジャンルを選択してください")
                keywords = st.text_area("キーワード", "追放, チート, ざまぁ", placeholder="カンマ区切りで入力してください", help="物語の核となるキーワードを記述します")
                target_eps = st.number_input("目標話数", 10, 200, 50, help="完結までに想定している総話数です")
            with col2:
                archetype = st.selectbox("アーキタイプ", list(STORY_ARCHETYPES.keys()), help="物語の構造的な型を選択してください")
                style_key = st.selectbox("文体スタイル", list(STYLE_DEFINITIONS.keys()),
                                        format_func=lambda k: STYLE_DEFINITIONS[k].get("description", k),
                                        help="AIが採用する文章のトーンを選択してください")
                initial_limit = st.number_input("初期生成話数", 1, 50, 25, help="最初に一括生成するプロットの数です")

            st.markdown("---")
            # Advanced parameters as expander inside form
            with st.expander("🛠️ 高度なエンジンスペック設定"):
                e_col1, e_col2, e_col3 = st.columns(3)
                with e_col1:
                    cheat_scale = st.slider("チート強度", 1, 10, 4, help="主人公の能力の突出度合いを調整します")
                with e_col2:
                    system_assist = st.slider("システム支援率", 0, 100, 70, help="AIによる構成支援の介入度合いです")
                with e_col3:
                    cost_severity = st.slider("コスト厳格度", 1, 5, 2, help="トークン消費の最適化レベルを調整します")

                e_col1, e_col2, e_col3 = st.columns(3)
                with e_col1:
                    from config.constants import CATHARSIS_DENSITY_PRESETS
                    catharsis_label_options = {v["label"]: k for k, v in CATHARSIS_DENSITY_PRESETS.items()}
                    catharsis_label_selected = st.selectbox(
                        "カタルシス密度",
                        options=list(catharsis_label_options.keys()),
                        index=2,
                        help="カタルシス爆発の発生頻度をプリセットから選択してください"
                    )
                    catharsis_density_preset_index = catharsis_label_options[catharsis_label_selected]
                with e_col2:
                    min_immersion = st.slider("最低没入スコア", 0.0, 100.0, 0.0, 1.0, help="品質ゲート用の最小没入スコア")

            if st.form_submit_button("🚀 企画生成開始", type="primary", use_container_width=True):
                params = {
                    "genre": genre, "keywords": keywords, "style_key": style_key,
                    "target_eps": target_eps, "initial_limit": initial_limit,
                    "cheat_scale": cheat_scale, "system_assist": system_assist, "cost_severity": cost_severity,
                    "catharsis_density_preset_index": catharsis_density_preset_index,
                    "min_immersion_score": min_immersion,
                }
                UIControllerManager(engine).emit(UIEventType.REQUEST_GENERATE_PLAN, params)
                st.rerun()
