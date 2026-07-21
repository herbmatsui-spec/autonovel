"""
streamlit_app/ui_tabs_writing_helpers.py — 小説生成タブのサブ関数群
"""
from __future__ import annotations

import json
import uuid
from typing import Any

import streamlit as st

from streamlit_app import api_client
from streamlit_app.state import UIStateStore


def get_ui(key: str, default: Any = None) -> Any:
    return UIStateStore().get_ui_state_value(key, default)


def set_ui(**kwargs) -> None:
    UIStateStore().update_ui_state(**kwargs)


def _render_series_config_form() -> dict[str, Any]:
    """作品設定フォームを描画し、入力値を返す"""
    with st.expander("作品設定", expanded=True):
        st.subheader("基本情報")
        title = st.text_input("タイトル", "覇者の帰還")
        genre = st.selectbox("ジャンル", ["fantasy", "slice_of_life", "mystery", "drama", "comedy"])
        synopsis = st.text_area("概要", "かつて最強とされた戦士が10年の眠りから覚醒し、", height=100)
        keywords = st.text_input("キーワード（カンマ区切り）", "戦士,覇権,転生")

        target_episodes = st.slider("話数", 1, 20, 10)
        target_word_count = st.slider("1話あたり文字数", 1000, 5000, 3000)
        book_id = st.number_input("Book ID", value=get_ui("current_book_id", 1), min_value=1)

        st.text_input("API Key", "your_api_key_here", key="api_key_input")

        if st.button("🚀 執筆開始", key="btn_write_start"):
            try:
                task_result = api_client.trigger_writing(
                    book_id=book_id,
                    start_ep=1,
                    end_ep=target_episodes,
                    passion=0.5,
                )
                task_id = task_result.get("task_id") or task_result.get("trace_id")
                if task_id:
                    set_ui(active_task_id=task_id)
                    set_ui(writing_progress={
                        "current_ep": 1,
                        "total": target_episodes,
                        "status": "running",
                    })
                    st.success(f"執筆タスク開始 (task_id={task_id})")
                else:
                    st.warning("タスクIDが取得できませんでした")
            except Exception as e:
                st.error(f"執筆開始エラー: {e}")

    return {
        "title": title,
        "genre": genre,
        "synopsis": synopsis,
        "keywords": keywords,
        "target_episodes": target_episodes,
        "target_word_count": target_word_count,
        "book_id": book_id,
    }


def _render_commercial_pipeline(form_data: dict[str, Any]) -> None:
    """商用化実行ボタンと結果表示を描画"""
    if get_ui("commercial_task_id", None) is not None:
        return

    if not st.button("商用化実行"):
        return

    if not form_data["keywords"].strip():
        st.error("キーワードを入力してください")
        return

    book_id = form_data.get("book_id", get_ui("current_book_id", 1))
    commercial_config = {
        "series_config": {
            "book_id": book_id,
            "title": form_data["title"],
            "genre": form_data["genre"],
            "concept": form_data["synopsis"],
            "keywords": [kw.strip() for kw in form_data["keywords"].split(",") if kw.strip()],
            "target_eps": form_data["target_episodes"],
            "target_word_count": form_data["target_word_count"],
        },
        "samples": [],
        "platforms": ["kakuyomu", "naru"],
    }

    try:
        result = api_client.commercial_run(commercial_config)

        task_id = result.get("trace_id") or result.get("task_id") or str(uuid.uuid4())
        set_ui(commercial_task_id=task_id)

        st.success("商用化パイプラインが実行されました")
        _render_pipeline_result(result)
        _poll_pipeline_status(task_id)

    except Exception as e:
        st.error(f"通信エラー: {e}")


def _render_pipeline_result(result: dict[str, Any]) -> None:
    """パイプライン実行結果（Bible/エピソード）を表示"""
    st.subheader("パイプライン実行結果")

    data = result.get("data", {})
    bible = data.get("bible")
    if bible:
        st.write("**Bible概要:**")
        st.write(f"概念: {bible.get('concept', '未定義')}")
        st.write(f"ジャンル: {bible.get('genre', '未定義')}")
        st.write(f"キーワード: {', '.join(bible.get('keywords', []))}")
        st.write(f"対象プラットフォーム: {', '.join(bible.get('target_platforms', []))}")
        st.write(f"一意のSELLING POINTS: {', '.join(bible.get('unique_selling_points', []))}")

        bible_json = json.dumps(bible, ensure_ascii=False, indent=2)
        st.download_button(
            label="Bible(JSON)をダウンロード",
            data=bible_json,
            file_name="bible.json",
            mime="application/json",
        )

    selected = data.get("selected")
    if selected:
        st.write(f"**生成エピソード数**: {len(selected)}")
        if selected:
            for ep in selected[:3]:
                with st.expander(f"話{ep['ep_num']}: {ep['title']}"):
                    st.write(f"概要: {ep.get('summary', '内容なし')}")

            if st.button("全エピソード一覧を表示"):
                for ep in selected:
                    with st.expander(f"話{ep['ep_num']}: {ep['title']}"):
                        st.write(f"概要: {ep.get('summary', '内容なし')}")

                if "schedule_csv" in data:
                    csv_path = data["schedule_csv"]
                    st.write(f"**CSVスケジュール**: `{csv_path}`")
                    with open(csv_path, "rb") as f:
                        st.download_button(
                            label="CSVをダウンロード",
                            data=f.read(),
                            file_name="schedule.csv",
                            mime="text/csv",
                        )


def _poll_pipeline_status(task_id: str) -> None:
    """パイプライン完了までポーリング"""
    if not task_id:
        return

    st.info("パイプラインの実行中です（最大30秒待機）")
    progress_bar = st.progress(0)
    max_wait_seconds = 30
    elapsed = 0
    poll_interval = get_ui("poll_interval", 1)
    status = "running"

    while elapsed < max_wait_seconds:
        elapsed += poll_interval

        try:
            status_data = api_client.get_task_status(task_id, timeout=5.0)
            if status_data:
                status = status_data.get("status", "running")
                progress = status_data.get("progress", 0)
                progress_bar.progress(progress)

                if status == "completed":
                    st.success("パイプラインが完了しました")
                    if status_data.get("book_id"):
                        set_ui(current_book_id=status_data["book_id"])
                    history = get_ui("generation_history", [])
                    history.append({
                        "ep_num": status_data.get("ep_num", "?"),
                        "status": "completed",
                        "timestamp": "完了",
                        "word_count": status_data.get("word_count", "N/A"),
                    })
                    set_ui(generation_history=history)
                    _fetch_and_display_report()
                    break
                elif status == "failed":
                    err_msg = status_data.get("message", "不明なエラー")
                    st.error(f"パイプラインが失敗しました: {err_msg}")
                    return
            else:
                st.warning("ステータス取得に失敗（空レスポンス）")
        except Exception as e:
            st.error(f"ステータス取得エラー: {e}")

        set_ui(poll_interval=poll_interval)

    if status != "completed":
        st.error("パイプラインが指定時間以内に完了しませんでした。")


def _poll_writing_status(task_id: str, max_wait: int = 300) -> None:
    """執筆完了までポーリング"""
    if not task_id:
        return

    elapsed = 0
    interval = 2
    status = "running"

    while elapsed < max_wait:
        try:
            status_data = api_client.get_task_status(task_id, timeout=5.0)
            if status_data:
                status = status_data.get("status", "running")
                current_ep = status_data.get("current_ep", 1)
                total_eps = status_data.get("total_eps", 1)
                set_ui(writing_progress={
                    "current_ep": current_ep,
                    "total": total_eps,
                    "status": status,
                })

                if status == "completed":
                    st.success("全エピソード生成完了！")
                    set_ui(writing_progress={
                        "current_ep": total_eps,
                        "total": total_eps,
                        "status": "completed",
                    })
                    set_ui(active_task_id=None)
                    history = get_ui("generation_history", [])
                    history.append({
                        "ep_num": total_eps,
                        "status": "completed",
                        "timestamp": "完了",
                        "word_count": status_data.get("word_count", "N/A"),
                    })
                    set_ui(generation_history=history)
                    break
                elif status == "failed":
                    err_msg = status_data.get("message", "不明なエラー")
                    st.error(f"執筆が失敗しました: {err_msg}")
                    set_ui(active_task_id=None)
                    set_ui(writing_progress={"current_ep": 0, "total": 0, "status": "failed"})
                    break
            else:
                st.warning("ステータス取得に失敗（空レスポンス）")
        except Exception as e:
            st.error(f"ステータス取得エラー: {e}")

        elapsed += interval
        import time
        time.sleep(interval)

    if status not in ("completed", "failed"):
        st.warning("執筆がタイムアウトしました")
        set_ui(active_task_id=None)
        set_ui(writing_progress={"current_ep": 0, "total": 0, "status": "timeout"})


def _fetch_and_display_report() -> None:
    """制作レポートを取得して表示・ダウンロード"""
    try:
        book_id = get_ui("current_book_id", 1)
        report_data = api_client.get_novel_report(book_id=book_id, timeout=30.0)
        if not report_data:
            st.error("レポート取得失敗: 空レスポンス")
            return

        report_json = json.dumps(report_data, ensure_ascii=False, indent=2)
        st.subheader("制作レポート")
        st.download_button(
            label="制作レポートをダウンロード",
            data=report_json,
            file_name="production_report.json",
            mime="application/json",
        )
        set_ui(report_generated=True)
    except Exception as e:
        st.error(f"レポート取得エラー: {e}")


def _render_generation_status() -> None:
    """生成結果・レポート表示エリア"""
    progress = get_ui("writing_progress", {"current_ep": 0, "total": 0, "status": "idle"})
    active = get_ui("active_task_id")
    if active and progress.get("status") == "running":
        total = progress.get("total", 1)
        current = progress.get("current_ep", 1)
        pct = int((current / total) * 100) if total > 0 else 0
        st.progress(pct / 100, text=f"第{current}話を生成中... ({pct}%)")

        if st.button("⏹️ 生成停止", key="btn_stop_writing"):
            try:
                api_client.stop_task(active)
                st.warning("停止リクエストを送信しました")
            except Exception as e:
                st.error(f"停止通信エラー: {e}")
            finally:
                set_ui(active_task_id=None)
                set_ui(writing_progress={"current_ep": 0, "total": 0, "status": "stopped"})

        _poll_writing_status(active)

    st.subheader("生成結果")
    st.info("生成が完了したら上記の「商用化実行」からレポートを取得してください")

    if get_ui("report_generated"):
        st.subheader("生成レポート（サマリ）")
        st.write("トークン使用量、品質スコア、エピソードサマリーなどを表示します")
        st.text("レポート内容は JSON で提供されています。必要に応じてダウンロードしてください。")
        try:
            book_id = get_ui("current_book_id", 1)
            report_data = api_client.get_novel_report(book_id=book_id, timeout=10.0)
            if report_data:
                st.subheader("📊 品質スコア")
                quality = report_data.get("quality_score", 0)
                st.progress(quality, text=f"統合品質スコア: {int(quality * 100)}%")
                st.write(f"トークン使用量: {report_data.get('token_usage', 'N/A')}")
        except Exception:
            st.caption("レポート詳細の取得に失敗しました")

    st.subheader("生成履歴")
    history = get_ui("generation_history", [])
    if history:
        for item in reversed(history[-10:]):
            with st.expander(f"第{item.get('ep_num', '?')}話 - {item.get('timestamp', '時刻不明')}"):
                st.write(f"ステータス: {item.get('status', '不明')}")
                st.write(f"文字数: {item.get('word_count', 'N/A')}")
    else:
        st.write("生成履歴は将来的に実装予定です")

    st.subheader("フィードバック")
    with st.form("feedback_form"):
        fb_ep = st.number_input("話数", min_value=1, value=1, key="fb_ep")
        fb_text = st.text_area("フィードバック内容", key="fb_text")
        submitted = st.form_submit_button("フィードバックを送信")
        if submitted and fb_text.strip():
            history = get_ui("generation_history", [])
            history.append({
                "ep_num": fb_ep,
                "status": "feedback",
                "timestamp": "未定",
                "word_count": "N/A",
                "feedback": fb_text.strip(),
            })
            set_ui(generation_history=history)
            st.success("フィードバックを記録しました")
        elif submitted:
            st.warning("フィードバック内容を入力してください")


def _render_episode_viewer() -> None:
    """停止ボタンとエピソード一覧表示"""
    gen_task_id = get_ui("gen_task_id", None)

    if gen_task_id is not None:
        if st.button("生成停止"):
            try:
                api_client.stop_task(gen_task_id)
                st.warning("停止リクエストを送信しました")
            except Exception as e:
                st.error(f"停止通信エラー: {e}")
            finally:
                set_ui(gen_task_id=None)

    if gen_task_id is not None and st.button("エピソード一覧を表示"):
        try:
            book_id = get_ui("current_book_id", 1)
            episodes_data = api_client.get_episodes(book_id)
            episodes = episodes_data.get("episodes", [])
            if episodes:
                st.subheader("エピソード一覧")
                for episode in episodes:
                    with st.expander(f"話{episode['ep_num']}: {episode['title']}"):
                        st.write(f"概要: {episode.get('summary', '')}")
                        st.write(f"文字数: {episode.get('word_count', '不明')}")
                        st.write(f"品質スコア: {episode.get('quality_score', '不明')}")

                                if st.button(f"話{episode['ep_num']}内容を表示", key=f"btn_{episode['ep_num']}"):
                                    try:
                                        book_id = get_ui("current_book_id", 1)
                                        detail_data = api_client.get_episode_detail(book_id, episode["ep_num"])
                                st.write("内容:")
                                st.write(detail_data.get("content", "内容取得エラー"))
                                if "killer_phrase" in detail_data:
                                    st.write(f"キラーフレーズ: {detail_data['killer_phrase']}")
                            except Exception as e:
                                st.error(f"エピソード内容取得エラー: {e}")
                            break
                st.success("エピソード一覧の取得に成功しました")
            else:
                st.error("エピソード一覧取得に失敗しました")
        except Exception as e:
            st.error(f"通信エラー: {e}")
