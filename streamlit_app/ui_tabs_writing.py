"""
src/streamlit_app/ui_tabs_writing.py — 小説生成タブコンポーネント（Streamlit セッション状態統一版）
"""
import streamlit as st
import httpx
import json
import time
import uuid
from typing import Dict, Any

from streamlit_app.state import UIStateStore

# ----------------------------------------------------------------------
# UIStateStore ヘルパー
# ----------------------------------------------------------------------
def get_ui(key: str, default: Any = None) -> Any:
    return UIStateStore().get_ui_state_value(key, default)

def set_ui(**kwargs) -> None:
    UIStateStore().update_ui_state(**kwargs)

# ----------------------------------------------------------------------
# 状態の初期化（UIStateStore経由）
# ----------------------------------------------------------------------
if get_ui("commercial_task_id", None) is None:
    set_ui(commercial_task_id=None)
if get_ui("report_generated", None) is None:
    set_ui(report_generated=False)
if get_ui("api_retry_state", None) is None:
    set_ui(api_retry_state={"attempts": 0, "max_attempts": 3, "backoff": 1})
if get_ui("poll_interval", None) is None:
    set_ui(poll_interval=1)

# ----------------------------------------------------------------------
# ユーティリティ：指数バックオフ付きリトライデコレータ
# ----------------------------------------------------------------------
def retry_api(func):
    """API呼び出しを行う際のリトライラッパー"""
    def wrapper(*args, **kwargs):
        state = get_ui("api_retry_state", {"attempts": 0, "max_attempts": 3, "backoff": 1})
        state["attempts"] += 1
        max_attempts = state["max_attempts"]
        backoff = state["backoff"]
        
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if state["attempts"] >= state["max_attempts"]:
                st.error(f"API呼び出しに失敗しました after {state['attempts']} 回の試行: {e}")
                raise
            # 指数バックオフで待機
            time.sleep(backoff)
            state["backoff"] *= 2  # 指数的に増加
            set_ui(api_retry_state=state)
            st.warning(f"API呼び出し失敗（試行 {state['attempts']}/{state['max_attempts']}）。{backoff}s 後のリトライ...")
            return func(*args, **kwargs)
    return wrapper

# ----------------------------------------------------------------------
# ページレイアウト
# ----------------------------------------------------------------------
def render_novel_production_tab():
    """小説生成タブを表示"""
    st.title("小説生成")
    
    # 作品設定フォーム
    with st.expander("作品設定", expanded=True):
        st.subheader("基本情報")
        title = st.text_input("タイトル", "覇者の帰還")
        genre = st.selectbox("ジャンル", ["fantasy", "slice_of_life", "mystery", "drama", "comedy"])
        synopsis = st.text_area("概要", "かつて最強とされた戦士が10年の眠りから覚醒し、", height=100)
        keywords = st.text_input("キーワード（カンマ区切り）", "戦士,覇権,転生")
        
        target_episodes = st.slider("話数", 1, 20, 10)
        target_word_count = st.slider("1話あたり文字数", 1000, 5000, 3000)
        
        # APIキー入力（デモ用固定値でも可）
        api_key = st.text_input("API Key", "your_api_key_here", key="api_key_input")
        
        # ==== 生成開始ボタン ==== #
        if get_ui("gen_task_id", None) is None:
            if st.button("生成開始"):
                # 現状は単なるプレースホル; 実際の実装は別ルートへ委譲
                st.info("「生成開始」は将来的なバックエンド連携用です")
        
        # ==== 商用化実行ボタン ==== #
        if get_ui("commercial_task_id", None) is None:
            if st.button("商用化実行"):
                # -------- 入力チェック --------
                if not keywords.strip():
                    st.error("キーワードを入力してください")
                    return
                
                # -------- 商用化設定作成 --------
                commercial_config = {
                    "series_config": {
                        "title": title,
                        "genre": genre,
                        "concept": synopsis,
                        "keywords": [kw.strip() for kw in keywords.split(",") if kw.strip()],
                        "target_eps": target_episodes,
                        "target_word_count": target_word_count
                    },
                    "samples": [],  # 将来的にサンプル取得ロジックを組み込み
                    "platforms": ["kakuyomu", "naru"]
                }
                
                # -------- API呼び出し（リトライ対応） --------
                try:
                    @retry_api
                    def call_commercial_api():
                        return httpx.post(
                            "http://localhost:8000/api/commercial/run",
                            json=commercial_config,
                            timeout=180.0
                        )
                    
                    response = call_commercial_api()
                    if response.status_code != 200:
                        st.error(f"API応答エラー {response.status_code}: {response.text}")
                        return
                    
                    result = response.json()
                    # トレースID／タスクIDを取得（バックエンドが提供していれば利用）
                    task_id = result.get("trace_id") or result.get("task_id") or str(uuid.uuid4())
                    set_ui(commercial_task_id=task_id)
                    
                    st.success("商用化パイプラインが実行されました")
                    
                    # ---------- 実行結果の表示 ----------
                    st.subheader("パイプライン実行結果")
                    
                    # Bible表示
                    if "data" in result and "bible" in result["data"]:
                        bible = result["data"]["bible"]
                        st.write("**Bible概要:**")
                        st.write(f"概念: {bible.get('concept', '未定義')}")
                        st.write(f"ジャンル: {bible.get('genre', '未定義')}")
                        st.write(f"キーワード: {', '.join(bible.get('keywords', []))}")
                        st.write(f"対象プラットフォーム: {', '.join(bible.get('target_platforms', []))}")
                        st.write(f"一意のSELLING POINTS: {', '.join(bible.get('unique_selling_points', []))}")
                        
                        # Bibleダウンロード
                        bible_json = json.dumps(bible, ensure_ascii=False, indent=2)
                        st.download_button(
                            label="Bible(JSON)をダウンロード",
                            data=bible_json,
                            file_name="bible.json",
                            mime="application/json"
                        )
                    
                    # エピソード一覧表示
                    if "data" in result and "selected" in result["data"]:
                        selected = result["data"]["selected"]
                        st.write(f"**生成エピソード数**: {len(selected)}")
                        if selected:
                            # 上位3話までプレビュー
                            for ep in selected[:3]:
                                with st.expander(f"話{ep['ep_num']}: {ep['title']}"):
                                    st.write(f"概要: {ep.get('summary', '内容なし')}")
                            
                            # 全エピソード一覧表示ボタン
                            if st.button("全エピソード一覧を表示"):
                                st.write("全エピソード一覧:")
                                for ep in selected:
                                    with st.expander(f"話{ep['ep_num']}: {ep['title']}"):
                                        st.write(f"概要: {ep.get('summary', '内容なし')}")
                                
                                # CSV出力パスとダウンロード
                                if "schedule_csv" in result["data"]:
                                    csv_path = result["data"]["schedule_csv"]
                                    st.write(f"**CSVスケジュール**: `{csv_path}`")
                                    
                                    # CSVダウンロードボタン
                                    with open(csv_path, "rb") as f:
                                        st.download_button(
                                            label="CSVをダウンロード",
                                            data=f.read(),
                                            file_name="schedule.csv",
                                            mime="text/csv"
                                        )
                    
                    # -------------------------------------------------
                    # ---------------  進捗ポーリング ----------
                    # -------------------------------------------------
                    if get_ui("commercial_task_id"):
                        st.info("パイプラインの実行中です（最大30秒待機）")
                        progress_bar = st.progress(0)
                        max_wait_seconds = 30
                        elapsed = 0
                        poll_interval = get_ui("poll_interval", 1)
                        
                        while elapsed < max_wait_seconds:
                            elapsed += poll_interval
                            
                            try:
                                status_resp = httpx.get(
                                    f"http://localhost:8000/api/tasks/{get_ui('commercial_task_id')}/status",
                                    timeout=5.0
                                )
                                if status_resp.status_code == 200:
                                    status_data = status_resp.json()
                                    status = status_data.get("status", "running")
                                    progress = status_data.get("progress", 0)
                                    progress_bar.progress(progress)
                                    
                                    if status == "completed":
                                        st.success("パイプラインが完了しました")
                                        # ---------- 完了時処理 ----------
                                        # レポート取得
                                        try:
                                            @retry_api
                                            def call_report_api():
                                                return httpx.get(
                                                    "http://localhost:8000/api/novel/1/report",
                                                    timeout=30.0
                                                )
                                            
                                            report_resp = call_report_api()
                                            if report_resp.status_code == 200:
                                                report_data = report_resp.json()
                                                # JSON文字列化してダウンロードボタンへ提供
                                                report_json = json.dumps(report_data, ensure_ascii=False, indent=2)
                                                st.subheader("制作レポート")
                                                st.download_button(
                                                    label="制作レポートをダウンロード",
                                                    data=report_json,
                                                    file_name="production_report.json",
                                                    mime="application/json"
                                                )
                                                set_ui(report_generated=True)
                                            else:
                                                st.error(f"レポート取得失敗 {report_resp.status_code}: {report_resp.text}")
                                        except Exception as e:
                                            st.error(f"レポート取得エラー: {e}")
                                        break
                                    elif status == "failed":
                                        err_msg = status_data.get("message", "不明なエラー")
                                        st.error(f"パイプラインが失敗しました: {err_msg}")
                                        return
                                    # それ以外はそのままループ継続
                                else:
                                    st.warning(f"ステータス取得に失敗（status code: {status_resp.status_code}）")
                            except Exception as e:
                                st.error(f"ステータス取得エラー: {e}")
                            
                            # ポーリング間隔の調整（ユーザーが変更可能に）
                            set_ui(poll_interval=poll_interval)
                            time.sleep(poll_interval)
                        
                        # -------------------------------------------------
                        # ----------  失敗時ハンドリング ----------
                        # -------------------------------------------------
                        if status != "completed":
                            st.error("パイプラインが指定時間以内に完了しませんでした。")
                        
                except Exception as e:
                    st.error(f"通信エラー: {e}")
    
    # ----------------------------------------------------------------------
    # 生成結果・レポート表示エリア（生成完了時のみ顕示）
    # ----------------------------------------------------------------------
    st.subheader("生成結果")
    st.info("生成が完了したら上記の「商用化実行」からレポートを取得してください")
    
    # レポート表示 / ダウンロード（既に生成済みフラグで制御）
    if get_ui("report_generated"):
        st.subheader("生成レポート（サマリ）")
        st.write("トークン使用量、品質スコア、エピソードサマリーなどを表示します")
        # 実際の内容はサーバー側で生成された JSON をそのまま利用
        # （ここではプレースホルダーとして簡易表示）
        st.text("レポート内容は JSON で提供されています。必要に応じてダウンロードしてください。")
    
    # ----------------------------------------------------------------------
    # 生成履歴・フィードバック
    # ----------------------------------------------------------------------
    st.subheader("生成履歴")
    st.write("生成履歴は将来的に実装予定です")
    
    st.subheader("フィードバック")
    st.write("生成結果に対するフィードバックを提供できます")
    
    # ----------------------------------------------------------------------
    # 停止ボタン（生成中のみ表示）
    # ----------------------------------------------------------------------
    if get_ui("gen_task_id", None) is not None:
        if st.button("生成停止"):
            try:
                stop_resp = httpx.post(
                    f"http://localhost:8000/api/tasks/{get_ui('gen_task_id')}/stop",
                    timeout=10.0
                )
                if stop_resp.status_code == 200:
                    st.warning("停止リクエストを送信しました")
                else:
                    st.error("停止に失敗しました")
                    st.text("ステータスコード:", stop_resp.status_code)
                    st.text("レスポンス:", stop_resp.text)
            except Exception as e:
                st.error(f"停止通信エラー: {e}")
            finally:
                set_ui(gen_task_id=None)
    
    # ----------------------------------------------------------------------
    # エピソード一覧表示（生成完了時のみ）
    # ----------------------------------------------------------------------
    if get_ui("gen_task_id", None) is not None:
        if st.button("エピソード一覧を表示"):
            try:
                episodes_resp = httpx.get(
                    "http://localhost:8000/api/novel/1/episodes",
                    timeout=10.0
                )
                if episodes_resp.status_code == 200:
                    episodes_data = episodes_resp.json()
                    st.subheader("エピソード一覧")
                    for episode in episodes_data.get("episodes", []):
                        with st.expander(f"話{episode['ep_num']}: {episode['title']}"):
                            st.write(f"概要: {episode['summary']}")
                            st.write(f"文字数: {episode['word_count']}")
                            st.write(f"品質スコア: {episode['quality_score']}")
                            
                            # エピソード内容表示（簡易版）
                            if st.button(f"話{episode['ep_num']}内容を表示", key=f"btn_{episode['ep_num']}"):
                                episode_detail_resp = httpx.get(
                                    f"http://localhost:8000/api/novel/1/episodes/{episode['ep_num']}",
                                    timeout=10.0
                                )
                                if episode_detail_resp.status_code == 200:
                                    detail_data = episode_detail_resp.json()
                                    st.write("内容:")
                                    st.write(detail_data.get("content", "内容取得エラー"))
                                    if "killer_phrase" in detail_data:
                                        st.write(f"キラーフレーズ: {detail_data['killer_phrase']}")
                                else:
                                    st.error("エピソード内容取得に失敗しました")
                                    st.text("ステータス:", episode_detail_resp.status_code)
                                    st.text("レスポンス:", episode_detail_resp.text)
                                break
                        st.success("エピソード一覧の取得に成功しました")
                else:
                    st.error("エピソード一覧取得に失敗しました")
                    st.text("ステータス:", episodes_resp.status_code)
                    st.text("レスポンス:", episodes_resp.text)
            except Exception as e:
                st.error(f"通信エラー: {e}")

# ----------------------------------------------------------------------
# エントリーポイント
# ----------------------------------------------------------------------
if __name__ == "__main__":
    render_novel_production_tab()