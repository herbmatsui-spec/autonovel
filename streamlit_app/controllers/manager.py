from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit_app.actions as actions
from streamlit_app.event_bus import UIEvent, UIEventBus, UIEventType
from streamlit_app.proxy import UltimateHegemonyEngineProxy
from streamlit_app.state import UIStateStore


class BaseController:
    """
    コントローラーの基底クラス。
    EventBusからイベントを受け取り、ビジネスロジック(actions)を呼び出す。
    """
    def __init__(self, engine: UltimateHegemonyEngineProxy, stream_display: Optional[Any] = None):
        self.engine = engine
        self.stream_display = stream_display

    def handle_event(self, event: UIEvent) -> Optional[Dict[str, Any]]:
        raise NotImplementedError("Subclasses must implement handle_event")

class PlanningController(BaseController):
    """企画立案に関するイベントを処理するコントローラー"""
    def handle_event(self, event: UIEvent) -> Optional[Dict[str, Any]]:
        payload = event.payload

        if event.type == UIEventType.REQUEST_GENERATE_PLAN:
            # UIから渡されたパラメータで企画生成を実行
            # ストリーミング表示がある場合は、バックグラウンド処理側で
            # stream_display インターフェースを介して更新することを期待する
            actions.generate_plan(self.engine, payload)
            return {"status": "started", "message": "企画生成を開始しました"}

        if event.type == UIEventType.REQUEST_AUDIT_PLAN:
            # AI診断の実行
            audit_res = self.engine.audit_producer_plan(
                genre=payload.get("genre", "ファンタジー"),
                keywords=payload.get("keywords", ""),
                trend_memo=payload.get("concept", ""),
                sanctuary=payload.get("sanctuary", ""),
                originality_score=payload.get("originality_score", 50),
                platform=payload.get("platform", "カクヨム/なろう")
            )
            return {"status": "completed", "data": audit_res}

        return None

class WritingController(BaseController):
    """プロット・執筆に関するイベントを処理するコントローラー"""
    def handle_event(self, event: UIEvent) -> Optional[Dict[str, Any]]:
        payload = event.payload

        if event.type == UIEventType.REQUEST_EXPAND_PLOT:
            actions.expand_plot(
                self.engine,
                book_id=payload["book_id"],
                gen_from=payload["gen_from"],
                gen_to=payload["gen_to"]
            )
            return {"status": "started"}

        if event.type == UIEventType.REQUEST_WRITE_EPISODE:
            actions.write_episode(
                engine=self.engine,
                book_id=payload["book_id"],
                write_from=payload["write_from"],
                write_to=payload["write_to"],
                passion=payload["passion"],
                word_count=payload["word_count"],
                do_refine=payload["do_refine"],
                env_state=payload["env_state"],
                pipeline_mode=payload["pipeline_mode"]
            )
            return {"status": "started"}

        if event.type == UIEventType.REQUEST_IMPORT_CHAPTER:
            res = actions.import_chapter(
                engine=self.engine,
                book_id=payload["book_id"],
                ep_num=payload["ep_num"],
                text=payload["text"],
                do_refine=payload["do_refine"]
            )
            return {"status": "completed", "data": res}

        if event.type == UIEventType.REQUEST_DELETE_CHAPTER:
            actions.delete_chapter(
                engine=self.engine,
                book_id=payload["book_id"],
                ep_num=payload["ep_num"]
            )
            return {"status": "completed"}

        return None

class SystemController(BaseController):
    """システム・作品管理に関するイベントを処理するコントローラー"""
    def handle_event(self, event: UIEvent) -> Optional[Dict[str, Any]]:
        payload = event.payload

        if event.type == UIEventType.REQUEST_DELETE_BOOK:
            from src.engine_service import EngineService
            service = EngineService.get_instance()
            service.delete_book(payload["book_id"])

            # 状態の更新
            UIStateStore.update(lambda s: setattr(s, "current_book_id", None), notify_keys=["current_book_id"])
            return {"status": "completed"}

        if event.type == UIEventType.REQUEST_REBUILD_PLOT:
            actions.rebuild_plot(self.engine, params=payload)
            return {"status": "started"}

        return None

class UIControllerManager:
    """
    すべてのコントローラーを管理し、EventBusに登録する。
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(UIControllerManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, engine: UltimateHegemonyEngineProxy, stream_display: Optional[Any] = None):
        if hasattr(self, "_initialized"): return

        self.engine = engine
        self.bus = UIEventBus()
        self.stream_display = stream_display

        # コントローラーの初期化 (stream_display を注入)
        self.planning_ctrl = PlanningController(engine, stream_display)
        self.writing_ctrl = WritingController(engine, stream_display)
        self.system_ctrl = SystemController(engine, stream_display)

        # イベントの購読設定
        self._setup_subscriptions()
        self._initialized = True

    def _setup_subscriptions(self):
        # Planning
        self.bus.subscribe(UIEventType.REQUEST_GENERATE_PLAN, self.planning_ctrl)
        self.bus.subscribe(UIEventType.REQUEST_AUDIT_PLAN, self.planning_ctrl)

        # Writing
        self.bus.subscribe(UIEventType.REQUEST_EXPAND_PLOT, self.writing_ctrl)
        self.bus.subscribe(UIEventType.REQUEST_WRITE_EPISODE, self.writing_ctrl)
        self.bus.subscribe(UIEventType.REQUEST_IMPORT_CHAPTER, self.writing_ctrl)
        self.bus.subscribe(UIEventType.REQUEST_DELETE_CHAPTER, self.writing_ctrl)

        # System
        self.bus.subscribe(UIEventType.REQUEST_DELETE_BOOK, self.system_ctrl)
        self.bus.subscribe(UIEventType.REQUEST_REBUILD_PLOT, self.system_ctrl)

    def emit(self, event_type: UIEventType, payload: Dict[str, Any], stream_display: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """UIからイベントを発行するためのエントリーポイント"""
        # 呼び出し時に stream_display が渡された場合は、一時的にコントローラーの display を更新
        # (本来はDIコンテナで管理すべきだが、現状のシングルトン構造での暫定対応)
        if stream_display:
            self.planning_ctrl.stream_display = stream_display
            self.writing_ctrl.stream_display = stream_display
            self.system_ctrl.stream_display = stream_display

        event = UIEvent(type=event_type, payload=payload)
        return self.bus.emit(event)
