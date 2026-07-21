import streamlit as st
from streamlit_app.state import UIStateStore


@st.dialog("⚠️ NSFWコンテンツに関する同意確認", width="medium")
def _show_nsfw_dialog(store):
    st.warning("このモードでは、成人向けの官能的な描写を含むコンテンツが生成されます。")
    st.markdown("""
    **利用規約および注意事項:**
    1. **年齢制限**: 18歳未満の方の利用を禁止します。
    2. **自己責任**: 生成される内容はAIによる自動生成であり、倫理的・法的な判断はユーザー自身の責任で行ってください。
    3. **表現の強度**: 設定により描写の強度が変動します。不快に感じた場合は直ちにNSFWモードをOFFにしてください。

    上記内容に同意し、官能特化型機能を利用しますか？
    """)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("同意して有効にする", type="primary"):
            store.set_form_data("nsfw_consented", True)
            st.rerun()
    with col2:
        if st.button("同意せず戻る"):
            st.rerun()


def render_nsfw_disclaimer() -> bool:
    """
    NSFWモード有効時の免責事項表示コンポーネント。
    同意が得られた場合に True を返す。
    """
    store = UIStateStore()
    if store.get_form_data("nsfw_consented", False):
        return True

    _show_nsfw_dialog(store)
    return False
