from typing import Any, Dict

import streamlit as st


def render_audit_tab(state: Dict[str, Any], engine: Any, book_id: int) -> None:
    from streamlit_app.ui.icons import ICON_AUDIT
    st.header(f"{ICON_AUDIT} 監査・チケット管理ダッシュボード")
    st.write(
        "物語の論理矛盾（生死、所持品、位置、時系列、能力など）や世界観設定のズレを、"
        "チケット形式の『Issue』として一覧管理します。作者（ユーザー）の指示に従ってAIが解決アクションを実行します。"
    )

    issues = getattr(state, "book_issues", [])

    if not issues:
        st.success("🎉 現在、未解決の論理矛盾や指摘はありません。整合性は良好です！")
        return

    # 未解決と解決済みでフィルタリング
    open_issues = [i for i in issues if i.get("status") == "open"]
    other_issues = [i for i in issues if i.get("status") != "open"]

    st.subheader(f"未解決のIssue ({len(open_issues)})")

    if not open_issues:
        st.info("未解決のIssueはありません。")
    else:
        from streamlit_app.ui.components.widgets import (
            render_primary_button,
            render_secondary_button,
        )
        for iss in open_issues:
            with st.container(border=True):
                # Severity-based badge color
                sev = iss.get('severity', 'Medium')
                sev_color = "🔴" if sev == "High" else "🟡" if sev == "Medium" else "🔵"

                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"### {sev_color} Issue #{iss.get('id')} : `{iss.get('category')}`")
                    st.caption(f"重要度: {sev} | 対象話数: 第{iss.get('ep_num')}話 | 起票: {iss.get('created_at')}")
                    st.markdown(f"**矛盾の内容:**\n{iss.get('description')}")

                    with st.expander("🔍 根拠・制約の詳細を確認"):
                        if iss.get("evidence_past"):
                            st.info(f"**過去の根拠:**\n{iss.get('evidence_past')}")
                        if iss.get("evidence_current"):
                            st.warning(f"**今話の矛盾箇所:**\n{iss.get('evidence_current')}")
                        if iss.get("constraint_for_next_ep"):
                            st.error(f"**次回への回収制約:**\n{iss.get('constraint_for_next_ep')}")

                with col2:
                    st.markdown("#### 🛠️ 解決アクション")
                    if render_primary_button("🪄 AIクイック修正", key=f"autofix_{iss.get('id')}", icon="🪄"):
                        import streamlit_app.actions as actions
                        with st.spinner("AIが最適な修正案を構築中..."):
                            actions.resolve_issue(engine, iss.get('id'), "Auto-Fix")
                            st.rerun()

                    if render_secondary_button("🔮 伏線として登録", key=f"foreshadow_{iss.get('id')}", icon="🔮"):
                        import streamlit_app.actions as actions
                        actions.resolve_issue(engine, iss.get('id'), "Foreshadowing")
                        st.rerun()

                    if render_secondary_button("😎 無視する", key=f"ignore_{iss.get('id')}", icon="😎"):
                        import streamlit_app.actions as actions
                        actions.resolve_issue(engine, iss.get('id'), "Ignore")
                        st.rerun()

    if other_issues:
        st.write("---")
        with st.expander(f"解決済み・適用済みの過去Issue一覧 ({len(other_issues)})"):
            for iss in other_issues:
                st.markdown(
                    f"**Issue #{iss.get('id')}** [`{iss.get('category')}`] - **ステータス: {iss.get('status')}**"
                )
                st.write(f"内容: {iss.get('description')}")
                if iss.get("resolved_note"):
                    st.caption(f"解決メモ: {iss.get('resolved_note')}")
                st.divider()
