"""Event Listener for Social Narrative Modeling (Step 52).

Subscribes to 'writing.completed' events emitted on the EventBus,
and automatically invokes SocialInteractionManager.process_scene()
in the background to simulate character journals, reactions, and relationship updates.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional
from src.agents.event_bus import AgentEvent, EventBus
from src.agents.social.manager import SocialInteractionManager

logger = logging.getLogger(__name__)


class SocialEventListener:
    """Listens for novel writing lifecycle events and coordinates social dynamics."""

    def __init__(
        self,
        manager: SocialInteractionManager,
        session_factory: Optional[Callable[[], Any]] = None,
        graph_name: str = "novel_graph",
    ) -> None:
        self.manager = manager
        self.session_factory = session_factory
        self.graph_name = graph_name

    async def on_writing_completed(self, event: AgentEvent) -> None:
        """Handle 'writing.completed' event and run social processing."""
        try:
            payload = event.payload or {}
            book_id = payload.get("book_id", 1)
            ep_num = payload.get("ep_num", 1)
            scene_text = payload.get("drafted_text") or payload.get("scene_text") or ""
            characters = payload.get("characters")

            logger.info(
                "SocialEventListener: Received writing.completed for book_id=%s, ep_num=%s. Starting social processing...",
                book_id, ep_num
            )

            session = None
            if self.session_factory:
                try:
                    session = self.session_factory()
                except Exception as ex:
                    logger.warning("Failed to obtain DB session for social listener: %s", ex)

            try:
                # Run sync/heavy process_scene safely in worker thread if in async loop
                result = await asyncio.to_thread(
                    self.manager.process_scene,
                    book_id=book_id,
                    ep_num=ep_num,
                    scene_text=scene_text,
                    characters=characters,
                    session=session,
                    graph_name=self.graph_name,
                )
                logger.info(
                    "SocialEventListener: Successfully processed social scene. Generated %d journals, %d comments.",
                    len(result.get("journals", [])),
                    len(result.get("comments", [])),
                )
            finally:
                if session and hasattr(session, "close"):
                    session.close()

        except Exception as e:
            logger.error("Error in SocialEventListener while handling writing.completed: %s", e, exc_info=True)


def register_social_listener(
    event_bus: EventBus,
    manager: SocialInteractionManager,
    session_factory: Optional[Callable[[], Any]] = None,
    graph_name: str = "novel_graph",
) -> SocialEventListener:
    """Register the social event listener on the EventBus for 'writing.completed'."""
    listener = SocialEventListener(manager=manager, session_factory=session_factory, graph_name=graph_name)
    event_bus.subscribe("writing.completed", listener.on_writing_completed)
    logger.info("Registered SocialEventListener for 'writing.completed' events.")
    return listener


__all__ = ["SocialEventListener", "register_social_listener"]
