"""
かんたんモード - ジャンル選択のみでシリーズ作成から完結まで全自動
"""

from __future__ import annotations

import streamlit as st

from src.presets.loader import list_available_genres
from streamlit_app.easy_mode_runner import start_easy_mode_generation
from streamlit_app.state import UIStateStore

GENRE_LABELS = {
    "zarma": "🗡️ ざまぁ・追放・無双",
    "aku_reijo": "👑 悪役令嬢・断罪回避",
    "cheat_tensei": "⚡ チート転生・即最強",
    "slow_life": "🌿 スローライフ・ほのぼの",
    "dungeon_admin": "🏰 ダンジョン運営・経営",
    "modern_cheat": "📱 現代チート・都市伝説",
    "ts_tensei": "🎀 TS転生・百合・性別反転",
    "vrmmo": "🎮 VRMMO・ゲーム世界",
    "loop": "🔄 ループ・時間逆行・真エンド",
}


def render_easy_mode(state, engine) -> None:
    """かんたんモードのメインUI"""

    st.markdown(
        """
        <div class="hero-section" style="margin-bottom: 2rem;">
            <h1 class="hero-title">⚡ かんたんモード</h1>
            <p style="font-size: 1.1rem; color: #cbd5e1; margin-top: 0.5rem;">
                ジャンルを選ぶだけで、企画から完結まで全自動生成
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info("🎯 **使い方**: ジャンルを選んで「シリーズ作成開始」を押すだけ。AIが企画・プロット・本文・監査まで全自動で行います。")

    # ジャンル選択
    st.markdown("### 🎭 ジャンルを選択")

    # セッション状態から現在のジャンルを取得
    runtime = UIStateStore.get_runtime()
    if not hasattr(runtime, 'easy_mode_genre'):
        runtime.easy_mode_genre = "zarma"

    # ジャンル選択UI（カード形式）
    cols = st.columns(3)
    genres = list_available_genres()

    for i, genre in enumerate(genres):
        with cols[i % 3]:
            label = GENRE_LABELS.get(genre, genre)
            is_selected = runtime.easy_mode_genre == genre

            # カードスタイルのボタン
            button_type = "primary" if is_selected else "secondary"
            if st.button(
                label,
                key=f"genre_{genre}",
                use_container_width=True,
                type=button_type,
            ):
                runtime.easy_mode_genre = genre
                st.rerun()

    # 選択中のジャンル表示
    current_genre = runtime.easy_mode_genre
    current_label = GENRE_LABELS.get(current_genre, current_genre)
    st.success(f"✅ 選択中: **{current_label}**")

    # ジャンルの説明表示
    _show_genre_description(current_genre)

    st.divider()

    # シリーズ作成ボタン
    st.markdown("### 🚀 シリーズ作成")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "🎬 シリーズ作成開始",
            type="primary",
            use_container_width=True,
        ):
            _start_series_creation(current_genre, engine)

    # 進行状況表示
    _render_progress_section()


def _show_genre_description(genre: str) -> None:
    """ジャンルの詳細説明を表示"""
    descriptions = {
        "zarma": "「追放された最強がチートで無双し、裏切り者をざまぁする」王道カタルシスジャンル。ストレス→カタルシスの波が最も激しい。",
        "aku_reijo": "「悪役令嬢に転生し、断罪フラグをへし折り、隠しキャラと溺愛ルートへ」乙女ゲーム攻略ジャンル。知的カタルシスと百合要素。",
        "cheat_tensei": "「転生即チート（ステータス∞/全スキル習得）で、レベル1から魔王を秒殺」効率厨ゲーマーの無双ジャンル。即時カタルシス連発。",
        "slow_life": "「前世は社畜、今は異世界で農業・料理・クラフトを楽しむ」究極の癒やしジャンル。バトル少なめ、日常の積み重ねでカタルシス。",
        "dungeon_admin": "「ダンジョンコアを手に入れ、モンスター育成・ギミック設計で冒険者を全滅させる」経営・タワーディフェンスジャンル。",
        "modern_cheat": "「現代日本でチート能力『管理者権限』を獲得し、裏社会・警察・企業を『バグ修正』感覚で処理する」都市伝説・配信者ジャンル。",
        "ts_tensei": "「女神に『少女』にされチート貰ったら、騎士も聖女もドラゴンも全部『嫁』にした」TS×百合×ハーレムの尊いジャンル。",
        "vrmmo": "「VRMMOでバグスキル入手、配信しながらソロでレイドボス秒殺、現実にアイテム実体化」ゲーム=現実統合ジャンル。",
        "loop": "「{{loop_count}}回死んでやっと真エンド到達」試行錯誤・データ蓄積・最適解探索で確率0を1にする完全攻略ジャンル。",
    }

    desc = descriptions.get(genre, "")
    if desc:
        st.info(f"📖 **ジャンル解説**: {desc}")


def _start_series_creation(genre: str, engine) -> None:
    """シリーズ作成を開始"""
    runtime = UIStateStore.get_runtime()
    runtime.easy_mode_active = True
    runtime.easy_mode_genre = genre
    runtime.easy_mode_step = "initializing"
    runtime.easy_mode_progress = 0
    runtime.easy_mode_logs = []
    runtime.easy_mode_current_episode = 0
    runtime.easy_mode_total_episodes = 8
    runtime.easy_mode_status = "running"

    # バックグラウンドランナーで実行開始
    start_easy_mode_generation(engine, genre, target_episodes=8)

    st.success(f"🎬 シリーズ作成を開始しました！（ジャンル: {GENRE_LABELS.get(genre, genre)}）")
    st.info("📋 進行状況は下部のプログレスバーで確認できます。完了まで少々お待ちください。")
    st.rerun()


def _render_progress_section() -> None:
    """進行状況セクションを表示"""
    runtime = UIStateStore.get_runtime()

    if not getattr(runtime, 'easy_mode_active', False):
        return

    # monitored_jobs からランナーを取得
    runner = UIStateStore.get_monitored_jobs().get("easy_job")

    st.divider()
    st.markdown("### 📊 進行状況")

    # プログレスバー - ランナーから取得、フォールバックで runtime
    if runner:
        progress = min(100, int((runner.current_step / max(runner.total_steps, 1)) * 100))
        step = runtime.easy_mode_step  # ステップ名は runtime から
        current_ep = runner.current_step if runner.current_step <= runner.total_steps else runtime.easy_mode_current_episode
        total_ep = runtime.easy_mode_total_episodes
        status = "completed" if not runner.is_running and runner.result_data else ("error" if runner.error else "running")
    else:
        progress = getattr(runtime, 'easy_mode_progress', 0)
        step = getattr(runtime, 'easy_mode_step', 'waiting')
        current_ep = getattr(runtime, 'easy_mode_current_episode', 0)
        total_ep = getattr(runtime, 'easy_mode_total_episodes', 8)
        status = getattr(runtime, 'easy_mode_status', 'running')

    # ステップ表示
    step_labels = {
        "initializing": "🔧 初期化中...",
        "bible": "📖 Bible生成中...",
        "plot": "📝 プロット生成中...",
        "writing": "✍️ 本文執筆中...",
        "audit": "⚖️ 監査・リライト中...",
        "finalizing": "📦 完結処理中...",
        "completed": "✅ 完了！",
        "error": "❌ エラー発生",
    }

    st.info(step_labels.get(step, f"⏳ {step}"))

    # プログレスバー
    st.progress(progress / 100 if progress <= 100 else 1.0)

    # エピソード進捗
    if current_ep > 0:
        st.caption(f"エピソード: {current_ep} / {total_ep} 話完了")
    
    # 人間レビュー必要な話数があるかチェック（完了時のみ）
    needs_review = []
    if runner and runner.result_data and hasattr(runner, 'pipeline') and runner.pipeline:
        # パイプラインから直接取得（存在すれば）
        pass
    
    # ログ表示 - ランナーから取得
    logs = runner.logs if runner else getattr(runtime, 'easy_mode_logs', [])
    if logs:
        with st.expander("📋 詳細ログ", expanded=False):
            for log in logs[-10:]:  # 最新10件
                st.text(log)
    
    # 人間レビュー必要な話がある場合の表示
    if runner and runner.pipeline and runner.pipeline.series_result:
        series = runner.pipeline.series_result
        needs_review = [ep for ep in series.episodes if getattr(ep, 'needs_human_review', False)]
        if needs_review:
            st.warning(f"⚠️ {len(needs_review)}話が監査基準未達のため人間レビューが必要です")
            with st.expander("📝 レビュー必要エピソード", expanded=True):
                for ep in needs_review:
                    st.markdown(f"**第{ep.episode_num}話: {ep.title}**")
                    st.caption(f"監査スコア: {ep.audit_score:.1f} / 目標: 95.0 | リライト回数: {ep.rewrite_count}")
                    if ep.metadata.get('audit_details', {}).get('improvements'):
                        st.caption(f"改善指示: {', '.join(ep.metadata['audit_details']['improvements'][:3])}")
                    st.text_area(f"本文確認 (ep{ep.episode_num})", ep.content[:500] + "...", height=100, key=f"review_ep{ep.episode_num}")
    
    # 完了時のアクション
    if status == "completed":
        st.success("🎉 シリーズ完結！")
        if runner and runner.result_data:
            res = runner.result_data
            st.info(f"📖 タイトル: {res.get('title', '無題')}")
            st.info(f"📝 総文字数: {res.get('total_words', 0):,}字")
            st.info(f"⚖️ 平均監査スコア: {res.get('average_audit_score', 0):.1f}")
        
        # レビュー必要フラグがある場合の特別なアクション
        if needs_review:
            st.info("💡 レビュー後に再生成する場合は、上級者モードで該当話を編集・再生成してください。")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📖 生成された小説を読む", use_container_width=True):
                st.info("小説閲覧機能は実装中です")
        with col2:
            if st.button("📦 資産化パック生成", use_container_width=True):
                st.info("資産化パック生成機能は実装中です")
        
        if st.button("🔄 新しいシリーズを作成", use_container_width=True):
            runtime.easy_mode_active = False
            UIStateStore.clear_active_job(run_key="easy_job")
            st.rerun()

    elif status == "error":
        st.error("❌ エラーが発生しました。ログを確認してください。")
        if runner and runner.error:
            st.code(runner.error)
        if st.button("🔄 リトライ", use_container_width=True):
            runtime.easy_mode_status = "running"
            st.rerun()


# ページエントリーポイント用ラッパー
def render_easy_mode_page() -> None:
    """ページ用ラッパー"""
    state = UIStateStore.get_runtime_state()
    from src.engine_service import EngineService
    engine = EngineService()
    render_easy_mode(state, engine)
