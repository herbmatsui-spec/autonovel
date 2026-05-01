import streamlit as st
from engine import UltimateHegemonyEngine, safe_run_async
import os

def render_promo_tab(engine: UltimateHegemonyEngine, book_id: int) -> None:
    """
    📢 宣伝・納品マネージャー タブ
    カクヨム用の宣伝文生成と、作品データのパッケージングを担当。
    """
    st.header("📢 宣伝・納品マネージャー")

    chapters = safe_run_async(engine.repo.get_all_non_anchor_chapters(book_id, order_by="ep_num"))
    if not chapters:
        st.info("執筆済みエピソードがありません。")
        return

    last_ep = chapters[-1].ep_num
    st.info(f"最新話: 第{last_ep}話")

    if st.button("✨ 宣伝パック生成"):
        with st.spinner("マーケティングAIが思考中..."):
            pack = safe_run_async(engine.generate_marketing_pack(book_id, last_ep))
            if pack:
                st.subheader("💡 カクヨム用キャッチコピー")
                st.code(pack.get("catchphrase", "（生成されませんでした）"), language="text")
                st.subheader("📝 カクヨム近況ノート")
                st.text_area("Note", pack.get("kakuyomu_notes", ""), height=200)
                st.write("推奨タグ:", pack.get("tags", []))

    st.divider()
    st.subheader("📦 一括納品 (ZIPダウンロード)")
    if st.button("作品データ一括ダウンロード準備"):
        with st.spinner("パッケージ作成中..."):
            # エージェント側のパッケージ化ロジックを呼び出し
            zip_data, zip_filename = safe_run_async(engine.marketing.create_export_package(book_id))

            temp_path = os.path.join("temp", zip_filename)
            os.makedirs("temp", exist_ok=True)
            with open(temp_path, "wb") as f:
                f.write(zip_data)
            st.session_state["download_zip_path"] = temp_path
            st.session_state["download_zip_name"] = zip_filename
            st.success("パッケージ作成完了！下のボタンからダウンロードしてください。")

    if "download_zip_data" in st.session_state:
        st.download_button(
            label="📦 ZIPファイルをダウンロード",
            data=st.session_state["download_zip_data"],
            file_name=st.session_state["download_zip_name"],
            mime="application/zip",
        )