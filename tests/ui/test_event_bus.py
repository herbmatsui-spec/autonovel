from typing import Any, Dict, Optional

from streamlit_app.event_bus import UIEvent, UIEventBus, UIEventType


class MockEventHandler:
    def __init__(self):
        self.handled_events = []

    def handle_event(self, event: UIEvent) -> Optional[Dict[str, Any]]:
        self.handled_events.append(event)
        return {"status": "success", "payload": event.payload}

def test_event_bus_subscription_and_emission():
    bus = UIEventBus()
    handler = MockEventHandler()

    # Subscribe handler to a specific event type
    bus.subscribe(UIEventType.REQUEST_GENERATE_PLAN, handler)

    payload = {"genre": "test_genre", "target_eps": 50}
    event = UIEvent(type=UIEventType.REQUEST_GENERATE_PLAN, payload=payload)

    # Emit event
    result = bus.emit(event)

    assert result == {"status": "success", "payload": payload}
    assert len(handler.handled_events) == 1
    assert handler.handled_events[0].type == UIEventType.REQUEST_GENERATE_PLAN
    assert handler.handled_events[0].payload == payload

def test_event_bus_no_handler():
    bus = UIEventBus()
    # Emit event with no subscribers
    event = UIEvent(type=UIEventType.REQUEST_AUDIT_PLAN, payload={})
    result = bus.emit(event)

    assert result is None
