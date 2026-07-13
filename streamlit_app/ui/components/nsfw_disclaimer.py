import streamlit as st


def render_nsfw_disclaimer() -> bool:
    """
    NSFWモード有効時の免責事項表示コンポーネント。
    同意が得られた場合に True を返す。
    """
    from streamlit_app.state_keys import NSFW_CONSENTED_KEY
    if NSFW_CONSENTED_KEY in st.session_state and st.session_state[NSFW_CONSENTED_KEY]:
        return True

    # モーダル形式で表示
    with st.dialog("⚠️ NSFWコンテンツに関する同意確認", width="medium"):
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
                st.session_state[NSFW_CONSENTED_KEY] = True
                st.rerun()
        with col2:
            if st.button("同意せず戻る"):
                # サイドバーのトグルを強制的にOFFにする処理は呼び出し元で制御
                st.rerun()

    return False
