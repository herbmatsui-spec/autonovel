from typing import Any, Dict

from streamlit_app.proxy import UltimateHegemonyEngineProxy as UltimateHegemonyEngine


def render_promo_tab(state: Dict[str, Any], engine: UltimateHegemonyEngine, book_id: int) -> None:
    """
    📢 宣伝・納品マネージャー タブ
    カクヨム用の宣伝文生成と、作品データのパッケージングを担当。
    """
    from streamlit_app.ui.icons import ICON_MARKETING
    st.header(f"{ICON_MARKETING} 宣伝・納品マネージャー")

    chapters = state.get("book_chapters", [])
    if not chapters:
        st.info("執筆済みエピソードがありません。")
        return

    last_ep = chapters[-1].ep_num
    st.info(f"最新話: 第{last_ep}話")

    from streamlit_app.ui.components.widgets import (
        render_primary_button,
        render_secondary_button,
        render_section_header,
    )
    from streamlit_app.ui.icons import ICON_PACKAGE, ICON_STAR

    # Step 1: 宣伝文生成フロー
    render_section_header("1. プロモーション準備", "読者を惹きつける宣伝文とキャッチコピーをAIが生成します", ICON_STAR)
    with st.container(border=True):
        st.write(f"最新話（第{last_ep}話）までの内容に基づいた宣伝パックを構築します。")
        if render_primary_button("宣伝パックを生成する", key="gen_marketing", icon=ICON_STAR):
            import streamlit_app.actions as actions
            with st.spinner("マーケティングAIが最適なコピーを考案中..."):
                actions.generate_marketing_pack(engine, book_id, last_ep)
                st.rerun()

    st.write("") # Spacer

    # Step 2: 納品/エクスポートフロー
    render_section_header("2. 最終納品パッケージ", "作品の全データをパッケージングし、一括ダウンロード可能にします", ICON_PACKAGE)
    with st.container(border=True):
        if not state.get("download_zip_data"):
            st.write("作品の全エピソード、設定資料、プロットをZIP形式でまとめます。")
            if render_primary_button("納品パッケージを作成する", key="prep_export", icon=ICON_PACKAGE):
                import streamlit_app.actions as actions
                with st.spinner("パッケージを構築中..."):
                    actions.create_export_package(engine, book_id)
                    st.rerun()
        else:
            st.success("✅ 納品パッケージの準備が完了しました。")
            st.download_button(
                label=f"{ICON_PACKAGE} ZIPファイルをダウンロード",
                data=state.get("download_zip_data"),
                file_name=state.get("download_zip_name", "export.zip"),
                mime="application/zip",
                use_container_width=True
            )
            if render_secondary_button("パッケージを再作成する", key="reprep_export", icon="♻️"):
                import streamlit_app.actions as actions
                actions.create_export_package(engine, book_id)
                st.rerun()
